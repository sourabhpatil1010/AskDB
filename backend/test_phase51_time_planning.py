import pytest
from datetime import date
from app.ai.planner.planner import AIQueryPlanner
from app.ai.planner.planner_utils import SchemaDateColumnResolver, TimeSemanticUtils
from app.ai.chains.json_chain import JSONGenerationChain
from app.query_builder.query_validator import QueryValidator


@pytest.fixture
def planner():
    return AIQueryPlanner()


@pytest.fixture
def json_chain():
    return JSONGenerationChain()


@pytest.fixture
def validator():
    return QueryValidator()


def test_schema_date_column_resolver():
    """Verify that SchemaDateColumnResolver dynamically resolves date columns from metadata without hardcoding."""
    assert SchemaDateColumnResolver.resolve("employees") == "hire_date"
    assert SchemaDateColumnResolver.resolve("payroll") == "period_start"
    assert SchemaDateColumnResolver.resolve("attendance") == "date"
    assert SchemaDateColumnResolver.resolve("projects") == "start_date"
    assert SchemaDateColumnResolver.resolve("performance_reviews") == "review_date"
    assert SchemaDateColumnResolver.resolve("leave_requests") == "start_date"

    # Test multi-table resolution
    tbl, col = SchemaDateColumnResolver.resolve_for_tables(["employees", "payroll"])
    assert tbl in ("employees", "payroll")
    assert col in ("hire_date", "period_start")


def test_time_semantic_utils_phrases():
    """Verify semantic time analysis for all required Phase 5.1 natural language expressions."""
    ref_d = date(2025, 5, 15)

    # 1. Employees hired yesterday
    tp1 = TimeSemanticUtils.analyze("Employees hired yesterday", ["employees"], ref_date=ref_d)
    assert tp1 is not None
    assert tp1.time_expression == "yesterday"
    assert tp1.date_field in ("hire_date", "employees.hire_date")
    assert tp1.operator == "="
    assert tp1.start_date == "2025-05-14"
    assert tp1.end_date == "2025-05-14"
    assert tp1.relative_period == "yesterday"
    assert tp1.granularity == "day"

    # 2. Employees hired today
    tp2 = TimeSemanticUtils.analyze("Employees hired today", ["employees"], ref_date=ref_d)
    assert tp2 is not None
    assert tp2.time_expression == "today"
    assert tp2.date_field in ("hire_date", "employees.hire_date")
    assert tp2.operator == "="
    assert tp2.start_date == "2025-05-15"
    assert tp2.end_date == "2025-05-15"
    assert tp2.relative_period == "today"
    assert tp2.granularity == "day"

    # 3. Employees hired last week
    tp3 = TimeSemanticUtils.analyze("Employees hired last week", ["employees"], ref_date=ref_d)
    assert tp3 is not None
    assert tp3.time_expression == "last week"
    assert tp3.operator == "between"
    assert tp3.relative_period == "last_week"
    assert tp3.granularity == "week"

    # 4. Employees hired this month
    tp4 = TimeSemanticUtils.analyze("Employees hired this month", ["employees"], ref_date=ref_d)
    assert tp4 is not None
    assert tp4.time_expression == "this month"
    assert tp4.operator == "between"
    assert tp4.start_date == "2025-05-01"
    assert tp4.end_date == "2025-05-31"
    assert tp4.relative_period == "this_month"
    assert tp4.granularity == "month"

    # 5. Employees hired last month
    tp5 = TimeSemanticUtils.analyze("Employees hired last month", ["employees"], ref_date=ref_d)
    assert tp5 is not None
    assert tp5.time_expression == "last month"
    assert tp5.operator == "between"
    assert tp5.start_date == "2025-04-01"
    assert tp5.end_date == "2025-04-30"
    assert tp5.relative_period == "last_month"
    assert tp5.granularity == "month"

    # 6. Employees hired this year
    tp6 = TimeSemanticUtils.analyze("Employees hired this year", ["employees"], ref_date=ref_d)
    assert tp6 is not None
    assert tp6.time_expression == "this year"
    assert tp6.operator == "between"
    assert tp6.start_date == "2025-01-01"
    assert tp6.end_date == "2025-12-31"
    assert tp6.relative_period == "this_year"
    assert tp6.granularity == "year"

    # 7. Payroll last quarter
    tp7 = TimeSemanticUtils.analyze("Payroll last quarter", ["payroll"], ref_date=ref_d)
    assert tp7 is not None
    assert tp7.time_expression == "last quarter"
    assert tp7.date_field in ("period_start", "payroll.period_start")
    assert tp7.operator == "between"
    assert tp7.start_date == "2025-01-01"
    assert tp7.end_date == "2025-03-31"
    assert tp7.relative_period == "last_quarter"
    assert tp7.granularity == "quarter"

    # 8. Attendance last 30 days
    tp8 = TimeSemanticUtils.analyze("Attendance last 30 days", ["attendance"], ref_date=ref_d)
    assert tp8 is not None
    assert "last 30 days" in tp8.time_expression
    assert tp8.date_field in ("date", "attendance.date")
    assert tp8.operator == "between"
    assert tp8.relative_period == "last_30_days"
    assert tp8.relative_offset == -30
    assert tp8.granularity == "day"

    # 9. Average salary this year
    tp9 = TimeSemanticUtils.analyze("Average salary this year", ["payroll"], ref_date=ref_d)
    assert tp9 is not None
    assert tp9.time_expression == "this year"
    assert tp9.operator == "between"
    assert tp9.start_date == "2025-01-01"
    assert tp9.end_date == "2025-12-31"
    assert tp9.relative_period == "this_year"
    assert tp9.granularity == "year"

    # 10. Between January and March
    tp10 = TimeSemanticUtils.analyze("Between January and March", ["employees"], ref_date=ref_d)
    assert tp10 is not None
    assert "between january and march" in tp10.time_expression.lower()
    assert tp10.operator == "between"
    assert tp10.start_date == "2025-01-01"
    assert tp10.end_date == "2025-03-31"
    assert tp10.relative_period == "custom_range"
    assert tp10.granularity == "month"


@pytest.mark.asyncio
@pytest.mark.parametrize("query,expected_rel_period", [
    ("Employees hired yesterday", "yesterday"),
    ("Employees hired today", "today"),
    ("Employees hired last week", "last_week"),
    ("Employees hired this month", "this_month"),
    ("Employees hired last month", "last_month"),
    ("Employees hired this year", "this_year"),
    ("Payroll last quarter", "last_quarter"),
    ("Attendance last 30 days", "last_30_days"),
    ("Average salary this year", "this_year"),
    ("Between January and March", "custom_range"),
])
async def test_e2e_time_planning_pipeline(planner, json_chain, validator, query, expected_rel_period):
    """Verify end-to-end planning and semantic understanding for time expressions without generating SQL."""
    # Step 1: AI Planner
    plan = await planner.plan(query)
    assert plan is not None
    assert plan.time_plan is not None, f"Expected time_plan in ExecutionPlan for query: '{query}'"
    assert plan.time_plan.relative_period == expected_rel_period
    assert plan.time_plan.date_field is not None

    # Step 2: JSON Generator -> StructuredQuery
    sq = await json_chain.generate(query)
    assert sq is not None
    assert sq.time_plan is not None, f"Expected time_plan in StructuredQuery for query: '{query}'"
    assert sq.time_plan.relative_period == expected_rel_period
    assert sq.time_plan.date_field == plan.time_plan.date_field
    assert sq.time_plan.operator == plan.time_plan.operator

    # Step 3: Query Validator
    is_valid = validator.validate(sq)
    assert is_valid is True

    # Note: Explicitly checking that we DO NOT implement SQL generation in Phase 5.1
    # The pipeline intentionally stops at Query Validator for Phase 5.1 time intelligence metadata.
