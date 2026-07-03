import pytest
import asyncio
from app.ai.planner.planner import AIQueryPlanner
from app.ai.chains.json_chain import JSONGenerationChain
from app.query_builder.query_validator import QueryValidator
from app.query_builder.sql_generator import SQLGenerator
from app.ai.structured_output.schemas import SubqueryPlanConfig


@pytest.mark.asyncio
@pytest.mark.parametrize("query,expected_subq_type,expected_op,expected_agg,expected_corr_cols", [
    ("Employees earning above their department average", "correlated", ">", "AVG", ["department_id"]),
    ("Employees with the highest salary in each department", "correlated", "=", "MAX", ["department_id"]),
    ("Employees with the lowest salary in each department", "correlated", "=", "MIN", ["department_id"]),
    ("Departments with more employees than company average", "scalar", ">", "AVG", None),
    ("Employees whose manager earns more than them", "correlated", "<", None, ["department_id"]),
    ("Employees with above-average performance in their department", "correlated", ">", "AVG", ["department_id"]),
    ("Projects with budget above department average", "correlated", ">", "AVG", ["id"]),
    ("Employees hired before their manager", "correlated", "<", None, ["department_id"]),
])
async def test_phase63_semantic_planning(query, expected_subq_type, expected_op, expected_agg, expected_corr_cols):
    planner = AIQueryPlanner()
    plan = await planner.plan(query)
    
    assert plan is not None
    assert plan.subquery_plan is not None, f"Expected subquery_plan for query: '{query}'"
    sp = plan.subquery_plan
    
    assert sp.subquery_type == expected_subq_type
    assert sp.comparison_operator == expected_op
    if expected_agg:
        assert sp.aggregate_function == expected_agg
    if expected_corr_cols:
        assert sp.correlation_columns == expected_corr_cols
        assert sp.outer_table is not None
        assert sp.outer_column is not None


def test_compile_correlated_scalar_unit():
    generator = SQLGenerator()
    config = SubqueryPlanConfig(
        subquery_type="correlated",
        target_table="payroll",
        target_column="base_salary",
        comparison_operator=">",
        aggregate_function="AVG",
        correlation_columns=["department_id"],
        alias="p2",
        outer_table="employees",
        outer_column="base_salary"
    )
    
    sql, counter = generator.compile_subquery(config, ["employees"], "employees", 1, {}, {})
    assert "SELECT AVG(p2.base_salary)" in sql
    assert "FROM payroll AS p2" in sql
    assert "WHERE p2.department_id = employees.department_id" in sql
    assert "employees.base_salary > (" in sql or "> (" in sql


@pytest.mark.asyncio
@pytest.mark.parametrize("query,expected_sql_snippets", [
    (
        "Employees earning above their department average",
        ["SELECT ", "FROM employees", " > (SELECT AVG(", "WHERE ", ".department_id = employees.department_id)"]
    ),
    (
        "Employees with the highest salary in each department",
        ["SELECT ", "FROM employees", " = (SELECT MAX(", "WHERE ", ".department_id = employees.department_id)"]
    ),
    (
        "Employees with the lowest salary in each department",
        ["SELECT ", "FROM employees", " = (SELECT MIN(", "WHERE ", ".department_id = employees.department_id)"]
    ),
    (
        "Employees whose manager earns more than them",
        ["SELECT ", "FROM employees", " < (SELECT ", "FROM payroll AS manager", "WHERE manager.department_id = employees.department_id"]
    ),
    (
        "Employees with above-average performance in their department",
        ["SELECT ", "FROM employees", " > (SELECT AVG(p2.score)", "FROM performance_reviews AS p2", "WHERE p2.department_id = employees.department_id)"]
    ),
    (
        "Projects with budget above department average",
        ["SELECT ", "FROM projects", " > (SELECT AVG(p2.id)", "FROM projects AS p2", "WHERE p2.id = projects.id)"]
    ),
    (
        "Employees hired before their manager",
        ["SELECT ", "FROM employees", " < (SELECT manager.hire_date", "FROM employees AS manager", "WHERE manager.department_id = employees.department_id"]
    ),
])
async def test_phase63_sql_generation_pipeline(query, expected_sql_snippets):
    planner = AIQueryPlanner()
    json_chain = JSONGenerationChain()
    validator = QueryValidator()
    generator = SQLGenerator()
    
    # 1. Natural Language -> Planner -> ExecutionPlan
    plan = await planner.plan(query)
    assert plan is not None
    assert plan.subquery_plan is not None
    
    # 2. ExecutionPlan -> JSON -> StructuredQuery
    structured_query = json_chain._create_heuristic_structured_query(plan)
    assert structured_query is not None
    assert structured_query.subquery_plan is not None
    
    # 3. StructuredQuery -> Validator
    is_valid = validator.validate(structured_query)
    assert is_valid is True
    
    # 4. StructuredQuery -> SQL Generator
    sql, params = generator.generate(structured_query)
    assert sql is not None
    assert isinstance(sql, str)
    assert len(sql) > 0
    
    # Verify expected snippets
    for snippet in expected_sql_snippets:
        assert snippet in sql, f"Expected snippet '{snippet}' not found in generated SQL:\n{sql}"
