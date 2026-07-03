import pytest
import asyncio
from app.ai.planner.planner import AIQueryPlanner
from app.ai.planner.planner_schema import WindowPlan
from app.services.ai.json_service import JSONService
from app.ai.structured_output.schemas import StructuredQuery, WindowFunctionConfig, SortCondition
from app.query_builder.query_validator import QueryValidator
from app.query_builder.sql_generator import SQLGenerator

@pytest.mark.asyncio
async def test_nl_to_planner_window_plan():
    """Verify that AIQueryPlanner generates valid WindowPlan metadata."""
    planner = AIQueryPlanner()
    plan = await planner.plan("Rank employees by salary in each department")
    
    assert hasattr(plan, "window_plan"), "ExecutionPlan should have window_plan attribute"
    assert plan.window_plan is not None, "window_plan should not be None for ranking query"
    assert isinstance(plan.window_plan, WindowPlan), "window_plan must be an instance of WindowPlan"
    assert plan.window_plan.function in ("ROW_NUMBER", "RANK", "DENSE_RANK")
    assert plan.window_plan.partition_by is not None and len(plan.window_plan.partition_by) > 0
    assert plan.window_plan.order_by is not None and len(plan.window_plan.order_by) > 0
    assert plan.window_plan.alias == "rank_num"

@pytest.mark.asyncio
async def test_json_generator_window_config():
    """Verify that JSON Generator emits correct WindowFunctionConfig."""
    json_service = JSONService()
    sq = await json_service.process_query("Rank employees by salary in each department")
    
    assert hasattr(sq, "window_function"), "StructuredQuery should have window_function attribute"
    assert sq.window_function is not None, "window_function should not be None"
    assert isinstance(sq.window_function, WindowFunctionConfig)
    assert sq.window_function.function in ("ROW_NUMBER", "RANK", "DENSE_RANK")
    assert sq.window_function.partition_by is not None and len(sq.window_function.partition_by) > 0
    assert sq.window_function.order_by is not None and len(sq.window_function.order_by) > 0
    assert sq.window_function.alias == "rank_num"

@pytest.mark.asyncio
async def test_query_validator_window_config():
    """Verify Query Validator validates WindowFunctionConfig and rejects invalid configurations."""
    validator = QueryValidator()
    
    # Valid config
    valid_sq = StructuredQuery(
        table="employees",
        columns=["employees.id"],
        window_function=WindowFunctionConfig(
            function="ROW_NUMBER",
            partition_by=["employees.department_id"],
            order_by=[SortCondition(table="employees", field="id", direction="desc")],
            alias="rn"
        )
    )
    assert validator.validate(valid_sq) is True
    
    # Invalid function name
    invalid_sq = StructuredQuery(
        table="employees",
        columns=["employees.id"],
        window_function=WindowFunctionConfig(
            function="INVALID_FUNC",
            partition_by=["employees.department_id"],
            order_by=[SortCondition(table="employees", field="id", direction="desc")],
            alias="rn"
        )
    )
    with pytest.raises(ValueError, match="Unsupported window function"):
        validator.validate(invalid_sq)

@pytest.mark.asyncio
async def test_sql_generator_window_compilation():
    """Verify SQL Generator compiles WindowFunctionConfig without creating CTEs or WHERE filters."""
    generator = SQLGenerator()
    
    wf = WindowFunctionConfig(
        function="ROW_NUMBER",
        partition_by=["departments.name"],
        order_by=[SortCondition(table="payroll", field="base_salary", direction="desc")],
        alias="rank_num"
    )
    
    # Test compilation of window function expression
    expr = generator.compile_window_function(wf, available_tables=["employees", "payroll", "departments"], default_table="employees")
    assert "ROW_NUMBER() OVER (" in expr
    assert "PARTITION BY departments.name" in expr
    assert "ORDER BY payroll.base_salary DESC" in expr
    assert expr.endswith("AS rank_num")
    
    # Test generation from StructuredQuery with ONLY window_function (no ranking execution config)
    sq = StructuredQuery(
        table="employees",
        columns=["employees.id"],
        window_function=wf
    )
    
    sql, params = generator.generate(sq)
    assert "ROW_NUMBER() OVER (" in sql
    assert "WITH " not in sql, "Phase 4.1 must not generate CTEs"
    assert "WHERE rank_num" not in sql and "WHERE rank" not in sql, "Phase 4.1 must not perform row number filtering"
