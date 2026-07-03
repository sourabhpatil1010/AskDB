import pytest
from datetime import date
from app.ai.planner.planner import AIQueryPlanner
from app.ai.chains.json_chain import JSONGenerationChain
from app.query_builder.query_validator import QueryValidator
from app.query_builder.sql_generator import SQLGenerator, TimeRangeSQLUtils
from app.ai.structured_output.schemas import TimePlanConfig


@pytest.fixture
def planner():
    return AIQueryPlanner()


@pytest.fixture
def json_chain():
    return JSONGenerationChain()


@pytest.fixture
def validator():
    return QueryValidator()


@pytest.fixture
def sql_gen():
    return SQLGenerator()


def test_time_range_sql_utils_unit():
    """Verify generic helper methods in TimeRangeSQLUtils."""
    # 1. resolve_today
    sql_today = TimeRangeSQLUtils.resolve_today("employees.hire_date")
    assert sql_today == "employees.hire_date = CURRENT_DATE"

    # 2. resolve_yesterday
    sql_yest = TimeRangeSQLUtils.resolve_yesterday("employees.hire_date")
    assert sql_yest == "employees.hire_date = CURRENT_DATE - INTERVAL '1 day'"

    # 3. resolve_relative_days
    tp_30 = TimePlanConfig(date_field="attendance.date", operator="between", relative_period="last_30_days", relative_offset=-30, granularity="day")
    sql_rel = TimeRangeSQLUtils.resolve_relative_days("attendance.date", tp_30)
    assert sql_rel == "attendance.date >= CURRENT_DATE - INTERVAL '30 days'"

    # 4. resolve_last_month
    params = {}
    p_map = {}
    tp_month = TimePlanConfig(date_field="hire_date", operator="between", start_date="2025-04-01", end_date="2025-04-30", relative_period="last_month")
    sql_month = TimeRangeSQLUtils.resolve_last_month("employees.hire_date", tp_month, parameters=params, param_prefix="time_1", param_field_map=p_map, table="employees", field="hire_date")
    assert sql_month == "employees.hire_date BETWEEN :time_1_start AND :time_1_end"
    assert params["time_1_start"] == "2025-04-01"
    assert params["time_1_end"] == "2025-04-30"
    assert p_map["time_1_start"] == ("employees", "hire_date")

    # 5. resolve_last_week
    tp_week = TimePlanConfig(date_field="hire_date", operator="between", start_date="2025-05-05", end_date="2025-05-11", relative_period="last_week")
    sql_week = TimeRangeSQLUtils.resolve_last_week("employees.hire_date", tp_week, parameters=params, param_prefix="time_2", param_field_map=p_map, table="employees", field="hire_date")
    assert sql_week == "employees.hire_date BETWEEN :time_2_start AND :time_2_end"

    # 6. resolve_last_quarter
    tp_qtr = TimePlanConfig(date_field="period_start", operator="between", start_date="2025-01-01", end_date="2025-03-31", relative_period="last_quarter")
    sql_qtr = TimeRangeSQLUtils.resolve_last_quarter("payroll.period_start", tp_qtr, parameters=params, param_prefix="time_3", param_field_map=p_map, table="payroll", field="period_start")
    assert sql_qtr == "payroll.period_start BETWEEN :time_3_start AND :time_3_end"

    # 7. resolve_this_year
    tp_year = TimePlanConfig(date_field="hire_date", operator="between", start_date="2025-01-01", end_date="2025-12-31", relative_period="this_year")
    sql_year = TimeRangeSQLUtils.resolve_this_year("employees.hire_date", tp_year, parameters=params, param_prefix="time_4", param_field_map=p_map, table="employees", field="hire_date")
    assert sql_year == "employees.hire_date BETWEEN :time_4_start AND :time_4_end"

    # 8. resolve_custom_range
    tp_custom = TimePlanConfig(date_field="hire_date", operator="<", start_date="2024-01-01", relative_period="custom_range")
    sql_custom = TimeRangeSQLUtils.resolve_custom_range("employees.hire_date", tp_custom, parameters=params, param_prefix="time_5", param_field_map=p_map, table="employees", field="hire_date")
    assert sql_custom == "employees.hire_date < :time_5_val"
    assert params["time_5_val"] == "2024-01-01"


@pytest.mark.asyncio
@pytest.mark.parametrize("query,expected_keyword", [
    ("Employees hired yesterday", "- INTERVAL '1 day'"),
    ("Employees hired last week", "BETWEEN"),
    ("Employees hired last month", "BETWEEN"),
    ("Employees hired this year", "BETWEEN"),
    ("Payroll last quarter", "BETWEEN"),
    ("Attendance last 30 days", "- INTERVAL '30 days'"),
    ("Average salary this year", "BETWEEN"),
    ("Top salaries hired last year", "BETWEEN"),
    ("Running payroll this month", "BETWEEN"),
    ("Between January and March", "BETWEEN"),
    ("Before 2024", "<"),
    ("After 2022", ">"),
])
async def test_e2e_time_sql_generation_pipeline(planner, json_chain, validator, sql_gen, query, expected_keyword):
    """
    Verify full AskDB pipeline execution for Phase 5.2:
    Natural Language -> AI Planner -> ExecutionPlan -> JSON Generator -> StructuredQuery -> Query Validator -> SQL Generator -> Executable SQL
    """
    # Step 1: AI Planner -> ExecutionPlan
    plan = await planner.plan(query)
    assert plan is not None
    assert plan.time_plan is not None, f"Expected time_plan in ExecutionPlan for query: '{query}'"

    # Step 2: JSON Generator -> StructuredQuery
    sq = await json_chain.generate(query)
    assert sq is not None
    assert sq.time_plan is not None, f"Expected time_plan in StructuredQuery for query: '{query}'"

    # Step 3: Query Validator
    is_valid = validator.validate(sq)
    assert is_valid is True

    # Step 4: SQL Generator -> Executable Parameterized SQL
    sql, params = sql_gen.generate(sq)
    assert sql is not None, f"Expected SQL output for query: '{query}'"
    assert isinstance(sql, str)
    assert len(sql.strip()) > 0
    assert "WHERE" in sql or "where" in sql.lower(), f"Expected WHERE clause in generated SQL for query: '{query}'. Got:\n{sql}"
    assert expected_keyword in sql, f"Expected keyword '{expected_keyword}' in SQL for query: '{query}'. Got:\n{sql}"

    # Verify parameters coerced properly for BETWEEN / comparison filters
    if "BETWEEN" in expected_keyword or "<" in expected_keyword or ">" in expected_keyword:
        assert isinstance(params, dict)
        assert len(params) > 0, f"Expected bound parameters for query: '{query}'"
        for p_name, p_val in params.items():
            assert p_val is not None, f"Parameter '{p_name}' should not be None"
