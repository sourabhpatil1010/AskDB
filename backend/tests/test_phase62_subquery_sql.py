"""Test suite for AskDB Phase 6.2: Executable Subquery SQL Generation.
Verifies complete pipeline: Natural Language -> Planner -> ExecutionPlan -> JSON -> StructuredQuery -> Validator -> SQL Generator -> Executable SQL.
"""
import pytest
from app.ai.planner.planner import AIQueryPlanner
from app.ai.chains.json_chain import JSONGenerationChain
from app.query_builder.query_validator import QueryValidator
from app.query_builder.sql_generator import SQLGenerator
from app.ai.structured_output.schemas import SubqueryPlanConfig, FilterCondition, HavingCondition, SortCondition


@pytest.mark.asyncio
@pytest.mark.parametrize("query,expected_sql_snippets,unexpected_sql_snippets", [
    (
        "Employees earning above company average",
        ["SELECT ", "FROM employees", " > (SELECT AVG(", "FROM employees"],
        []
    ),
    (
        "Employees in departments with more than 20 employees",
        ["SELECT ", "FROM employees", " IN (SELECT ", "FROM employees", "GROUP BY ", "HAVING COUNT("],
        []  # Outer query joins departments to select department name, which is valid
    ),
    (
        "Employees not assigned to any project",
        ["SELECT ", "FROM employees", " NOT IN (SELECT ", "FROM project_assignments"],
        ["JOIN project_assignments"]
    ),
    (
        "Departments without employees",
        ["SELECT ", "FROM departments", " NOT EXISTS (SELECT 1 FROM employees"],
        ["JOIN employees"]
    ),
    (
        "Departments with employees",
        ["SELECT ", "FROM departments", " EXISTS (SELECT 1 FROM employees"],
        ["JOIN employees"]
    ),
    (
        "Projects with managers",
        ["SELECT ", "FROM projects", " EXISTS (SELECT 1 FROM project_assignments"],
        ["JOIN project_assignments"]
    ),
    (
        "Employees with salary greater than average bonus",
        ["SELECT ", "FROM employees", " > (SELECT AVG(", "FROM payroll"],
        []
    ),
])
async def test_subquery_sql_generation_pipeline(query, expected_sql_snippets, unexpected_sql_snippets):
    planner = AIQueryPlanner()
    json_chain = JSONGenerationChain()
    validator = QueryValidator()
    generator = SQLGenerator()

    # 1. Natural Language -> Planner -> ExecutionPlan
    plan = await planner.plan(query)
    assert plan is not None
    assert plan.subquery_plan is not None, f"Expected subquery_plan for query: '{query}'"

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

    # Verify unexpected snippets
    for snippet in unexpected_sql_snippets:
        assert snippet not in sql, f"Unexpected snippet '{snippet}' found in generated SQL:\n{sql}"


def test_compile_scalar_subquery_unit():
    generator = SQLGenerator()
    sp = SubqueryPlanConfig(
        subquery_type="scalar",
        target_table="payroll",
        target_column="base_salary",
        comparison_operator=">",
        aggregate_function="AVG"
    )
    sql, counter = generator.compile_scalar_subquery(sp, ["employees"], "employees", 1, {}, {})
    assert sql == "payroll.base_salary > (SELECT AVG(payroll.base_salary) FROM payroll)"
    assert counter == 1


def test_compile_in_subquery_unit():
    generator = SQLGenerator()
    sp = SubqueryPlanConfig(
        subquery_type="in",
        target_table="employees",
        target_column="department_id",
        comparison_operator="IN",
        group_by=["department_id"],
        having=[HavingCondition(column="COUNT(*)", operator=">", value="20")]
    )
    sql, counter = generator.compile_in_subquery(sp, ["employees"], "employees", 1, {}, {})
    assert "employees.department_id IN (SELECT employees.department_id FROM employees GROUP BY employees.department_id HAVING COUNT(*) > 20)" in sql


def test_compile_not_in_subquery_unit():
    generator = SQLGenerator()
    sp = SubqueryPlanConfig(
        subquery_type="not_in",
        target_table="project_assignments",
        target_column="employee_id",
        comparison_operator="NOT IN"
    )
    sql, counter = generator.compile_not_in_subquery(sp, ["employees"], "employees", 1, {}, {})
    assert "employees.id NOT IN (SELECT project_assignments.employee_id FROM project_assignments)" in sql


def test_compile_exists_subquery_unit():
    generator = SQLGenerator()
    sp = SubqueryPlanConfig(
        subquery_type="exists",
        target_table="employees",
        comparison_operator="EXISTS"
    )
    sql, counter = generator.compile_exists_subquery(sp, ["departments"], "departments", 1, {}, {})
    assert "EXISTS (SELECT 1 FROM employees WHERE employees.department_id = departments.id)" in sql


def test_compile_not_exists_subquery_unit():
    generator = SQLGenerator()
    sp = SubqueryPlanConfig(
        subquery_type="not_exists",
        target_table="employees",
        comparison_operator="NOT EXISTS"
    )
    sql, counter = generator.compile_not_exists_subquery(sp, ["departments"], "departments", 1, {}, {})
    assert "NOT EXISTS (SELECT 1 FROM employees WHERE employees.department_id = departments.id)" in sql


def test_compile_table_subquery_unit():
    generator = SQLGenerator()
    sp = SubqueryPlanConfig(
        subquery_type="table",
        target_table="employees",
        alias="subq"
    )
    sql, counter = generator.compile_table_subquery(sp, ["employees"], "employees", 1, {}, {})
    assert sql == "(SELECT * FROM employees) AS subq"
