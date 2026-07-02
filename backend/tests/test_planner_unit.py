"""Unit tests for AI Query Planner components (Utils, Validator, Schema, Facade)."""
import pytest
from datetime import date
from app.ai.planner.planner_schema import (
    ExecutionPlan, IntentEnum, Metric, Filter, HavingCondition, OrderCondition, PlannerClarificationException
)
from app.ai.planner.planner_utils import (
    TimeReasoningUtils, JoinDetectionUtils, BusinessRuleUtils, QueryDecompositionUtils
)
from app.ai.planner.planner_validator import PlannerValidator
from app.ai.planner.planner import AIQueryPlanner


def test_time_reasoning_before_covid():
    filters = TimeReasoningUtils.parse_time_phrase("Employees hired before COVID", target_field="hire_date")
    assert len(filters) == 1
    assert filters[0].field == "hire_date"
    assert filters[0].operator == "<"
    assert filters[0].value == "2020-03-01"
    assert filters[0].time_reasoning == "Before COVID"


def test_time_reasoning_last_month():
    ref = date(2026, 7, 15)
    filters = TimeReasoningUtils.parse_time_phrase("Payroll last month", target_field="period_start", ref_date=ref)
    assert len(filters) == 1
    assert filters[0].operator == "between"
    assert filters[0].value == ["2026-06-01", "2026-06-30"]


def test_join_detection():
    # Departments and Payroll are connected via Employees
    paths = JoinDetectionUtils.detect_join_paths(["departments", "payroll"])
    assert len(paths) >= 1
    assert "departments -> employees -> payroll" in paths[0] or "payroll -> employees -> departments" in paths[0]


def test_business_rule_interpretation():
    rules = BusinessRuleUtils.interpret_rules("Compare salary year over year excluding interns and show above average")
    assert len(rules) >= 3
    assert any("Year over Year" in r for r in rules)
    assert any("excluding interns" in r for r in rules)
    assert any("Above Average" in r for r in rules)


def test_query_decomposition():
    plan = ExecutionPlan(
        intent=IntentEnum.COMPARISON,
        tables=["employees", "departments"],
        metrics=[Metric(field="salary", operation="avg", alias="avg_salary")],
        filters=[Filter(field="hire_date", operator=">", value="2020-01-01")],
        group_by=["department"],
        having=[HavingCondition(metric="count", operator=">", value=20)],
        order_by=[OrderCondition(field="avg_salary", direction="desc")]
    )
    tasks = QueryDecompositionUtils.decompose(plan)
    assert len(tasks) == 6
    assert "Task 1" in tasks[0] and "hire_date" in tasks[0]
    assert "Task 4" in tasks[3] and "department" in tasks[3]


def test_validator_low_confidence_exception():
    validator = PlannerValidator()
    low_plan = ExecutionPlan(
        intent=IntentEnum.SEARCH,
        tables=["employees"],
        confidence=0.60,
        clarification_questions=["Did you mean Average Salary or Total Salary?"]
    )
    with pytest.raises(PlannerClarificationException) as exc_info:
        validator.validate_and_enrich(low_plan, "salary stuff")
    assert exc_info.value.confidence == 0.60
    assert "Average Salary" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ai_query_planner_facade_ambiguous():
    planner = AIQueryPlanner()
    plan = await planner.plan("compare average salary by department")
    assert plan.intent == IntentEnum.COMPARISON
    assert "departments" in plan.tables or "department" in plan.tables
    assert plan.confidence >= 0.70
    
    with pytest.raises(PlannerClarificationException):
        await planner.plan("vague salary stuff")
