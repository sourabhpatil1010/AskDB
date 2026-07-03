import pytest
from app.ai.structured_output.schemas import StructuredQuery, WindowFunctionConfig, SortCondition, FilterCondition, OperatorEnum, JoinCondition
from app.query_builder.sql_generator import SQLGenerator
from app.query_builder.query_validator import QueryValidator

@pytest.mark.asyncio
async def test_dynamic_ranking_window_functions():
    """Verify compilation of ranking window functions (ROW_NUMBER, RANK, DENSE_RANK)."""
    generator = SQLGenerator()
    available_tables = ["employees", "payroll", "departments"]
    
    for func in ("ROW_NUMBER", "RANK", "DENSE_RANK"):
        wf = WindowFunctionConfig(
            function=func,
            partition_by=["department_id"],
            order_by=[SortCondition(table=None, field="base_salary", direction="desc")],
            alias="rank_res"
        )
        expr = generator.compile_window_function(wf, available_tables=available_tables, default_table="employees")
        assert f"{func}() OVER (" in expr
        assert "PARTITION BY employees.department_id" in expr
        assert "ORDER BY payroll.base_salary DESC" in expr
        assert expr.endswith("AS rank_res")

@pytest.mark.asyncio
async def test_dynamic_analytical_window_functions():
    """Verify compilation of all analytical window functions with dynamic schema resolution."""
    generator = SQLGenerator()
    available_tables = ["employees", "payroll", "departments"]
    
    analytical_funcs = [
        ("SUM", "base_salary", "SUM(payroll.base_salary)"),
        ("AVG", "base_salary", "AVG(payroll.base_salary)"),
        ("COUNT", "id", "COUNT(employees.id)"),
        ("MIN", "base_salary", "MIN(payroll.base_salary)"),
        ("MAX", "base_salary", "MAX(payroll.base_salary)"),
        ("LAG", "base_salary", "LAG(payroll.base_salary)"),
        ("LEAD", "base_salary", "LEAD(payroll.base_salary)"),
        ("FIRST_VALUE", "base_salary", "FIRST_VALUE(payroll.base_salary)"),
        ("LAST_VALUE", "base_salary", "LAST_VALUE(payroll.base_salary)"),
    ]
    
    for func, col, expected_expr in analytical_funcs:
        # Test explicit column attribute
        wf_explicit = WindowFunctionConfig(
            function=func,
            column=col,
            partition_by=["department_id"],
            order_by=[SortCondition(table=None, field="id", direction="asc")],
            alias=f"{func.lower()}_res"
        )
        expr1 = generator.compile_window_function(wf_explicit, available_tables=available_tables, default_table="employees")
        assert expected_expr in expr1
        assert "PARTITION BY employees.department_id" in expr1
        assert "ORDER BY employees.id ASC" in expr1
        assert expr1.endswith(f"AS {func.lower()}_res")
        
        # Test embedded column syntax inside function string
        wf_embedded = WindowFunctionConfig(
            function=f"{func}({col})",
            partition_by=["department_id"],
            order_by=[SortCondition(table=None, field="id", direction="asc")],
            alias=f"{func.lower()}_res"
        )
        expr2 = generator.compile_window_function(wf_embedded, available_tables=available_tables, default_table="employees")
        assert expected_expr in expr2

@pytest.mark.asyncio
async def test_sql_generator_shared_builders():
    """Verify generating queries through SQL Generator uses shared helper methods cleanly without breaking syntax or coercion."""
    generator = SQLGenerator()
    validator = QueryValidator()
    
    sq = StructuredQuery(
        table="employees",
        columns=["employees.id", "employees.first_name", "payroll.base_salary"],
        joins=[JoinCondition(table="payroll", on="payroll.employee_id = employees.id")],
        filters=[
            FilterCondition(table="payroll", field="base_salary", operator=OperatorEnum.GTE, value=50000),
            FilterCondition(table="employees", field="first_name", operator=OperatorEnum.IN, value=["John", "Jane", "Alice"])
        ],
        sort=SortCondition(table="payroll", field="base_salary", direction="desc"),
        limit=10,
        offset=5
    )
    
    assert validator.validate(sq) is True
    sql, params = generator.generate(sq)
    
    assert "SELECT\n    employees.id, employees.first_name, payroll.base_salary" in sql
    assert "FROM employees" in sql
    assert "JOIN payroll ON payroll.employee_id = employees.id" in sql
    assert "WHERE payroll.base_salary >= :payroll_base_salary_1" in sql
    assert "AND employees.first_name IN (:employees_first_name_2_0, :employees_first_name_2_1, :employees_first_name_2_2)" in sql
    assert "ORDER BY payroll.base_salary DESC" in sql
    assert "LIMIT 10" in sql
    assert "OFFSET 5" in sql
    assert params["payroll_base_salary_1"] == 50000
    assert params["employees_first_name_2_0"] == "John"

@pytest.mark.asyncio
async def test_unqualified_schema_resolver_integration():
    """Verify schema resolvers work correctly when column names lack table qualification."""
    generator = SQLGenerator()
    
    wf = WindowFunctionConfig(
        function="AVG",
        column="base_salary",
        partition_by=["department_id"],
        order_by=[SortCondition(table=None, field="hire_date", direction="asc")],
        alias="dept_avg_sal"
    )
    
    expr = generator.compile_window_function(
        wf,
        available_tables=["employees", "payroll", "departments"],
        default_table="employees"
    )
    
    assert "AVG(payroll.base_salary)" in expr
    assert "PARTITION BY employees.department_id" in expr
    assert "ORDER BY employees.hire_date ASC" in expr
    assert expr.endswith("AS dept_avg_sal")
