"""Test suite for AskDB Phase 6.1: Subquery Engine (Planning & Semantic Understanding).
Verifies complete pipeline: Natural Language -> Planner -> ExecutionPlan -> JSON -> StructuredQuery -> Validator.
"""
import pytest
from app.ai.planner.planner import AIQueryPlanner
from app.ai.chains.json_chain import JSONGenerationChain
from app.query_builder.query_validator import QueryValidator


@pytest.mark.asyncio
@pytest.mark.parametrize("query,expected_subq_type,expected_target_table,expected_op", [
    ("Employees earning above company average", "scalar", "employees", ">"),
    ("Employees earning above department average", "correlated", "employees", ">"),
    ("Departments without employees", "not_exists", "employees", "NOT EXISTS"),
    ("Departments with employees", "exists", "employees", "EXISTS"),
    ("Projects with managers", "exists", "project_assignments", "EXISTS"),
    ("Employees who never took leave", "not_in", "leave_requests", "NOT IN"),
    ("Employees working on projects with above average budget", "scalar", "projects", ">"),
    ("Projects having no manager", "not_in", "project_assignments", "NOT IN"),
    ("Employees in departments with more than 20 employees", "in", "employees", "IN"),
    ("Departments with highest average salary", "in", "employees", "IN"),
    ("Employees with salary greater than average bonus", "scalar", "payroll", ">"),
    ("Employees whose manager earns more than 100000", "in", "employees", "IN"),
])
async def test_subquery_planning_pipeline(query, expected_subq_type, expected_target_table, expected_op):
    planner = AIQueryPlanner()
    json_chain = JSONGenerationChain()
    validator = QueryValidator()

    # 1. Natural Language -> Planner -> ExecutionPlan
    plan = await planner.plan(query)
    assert plan is not None
    assert plan.subquery_plan is not None, f"Expected subquery_plan for query: '{query}'"
    
    sp = plan.subquery_plan
    assert sp.subquery_type == expected_subq_type
    assert sp.target_table == expected_target_table
    assert sp.comparison_operator == expected_op

    # 2. ExecutionPlan -> JSON -> StructuredQuery
    structured_query = json_chain._create_heuristic_structured_query(plan)
    assert structured_query is not None
    assert structured_query.subquery_plan is not None
    
    sq_sp = structured_query.subquery_plan
    assert sq_sp.subquery_type == expected_subq_type
    assert sq_sp.target_table == expected_target_table
    assert sq_sp.comparison_operator == expected_op

    # 3. StructuredQuery -> Validator
    is_valid = validator.validate(structured_query)
    assert is_valid is True
