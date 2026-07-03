import pytest
from app.ai.planner.planner import AIQueryPlanner
from app.ai.planner.planner_schema import IntentEnum
from app.ai.chains.json_chain import JSONGenerationChain
from app.query_builder.query_validator import QueryValidator
from app.query_builder.sql_generator import SQLGenerator


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
def generator():
    return SQLGenerator()


@pytest.mark.asyncio
@pytest.mark.parametrize("query,expected_func,expected_col_part,expected_frame_part", [
    ("Running payroll total", "SUM", "base_salary", "UNBOUNDED PRECEDING"),
    ("Running salary total", "SUM", "base_salary", "UNBOUNDED PRECEDING"),
    ("Running employee count", "COUNT", "id", "UNBOUNDED PRECEDING"),
    ("Running attendance total", "SUM", "hours_worked", "UNBOUNDED PRECEDING"),
    ("Department cumulative payroll", "SUM", "base_salary", "PARTITION BY"),
    ("Monthly cumulative hiring", "COUNT", "id", "UNBOUNDED PRECEDING"),
    ("Moving average salary", "AVG", "base_salary", "2 PRECEDING"),
    ("Rolling 3 month average salary", "AVG", "base_salary", "2 PRECEDING"),
    ("Previous employee salary", "LAG", "base_salary", "OVER ("),
    ("Next employee salary", "LEAD", "base_salary", "OVER ("),
    ("Salary difference from previous employee", "DIFFERENCE", "LAG(", "OVER ("),
    ("Difference from previous month", "DIFFERENCE", "LAG(", "OVER ("),
    ("First employee hired in each department", "FIRST_VALUE", "first_name", "UNBOUNDED FOLLOWING"),
    ("Last employee hired in each department", "LAST_VALUE", "first_name", "UNBOUNDED FOLLOWING"),
    ("First salary in department", "FIRST_VALUE", "base_salary", "UNBOUNDED FOLLOWING"),
    ("Last attendance record", "LAST_VALUE", "hours_worked", "UNBOUNDED FOLLOWING"),
])
async def test_phase43_analytical_window_pipeline_e2e(planner, json_chain, validator, generator, query, expected_func, expected_col_part, expected_frame_part):
    """
    Verifies that all 16 required natural language analytical window queries flow through
    the entire 6-layer architecture without bypassing Planner, JSON, or StructuredQuery.
    """
    # 1. AI Planner Layer
    plan = await planner.plan(query)
    assert plan.intent == IntentEnum.ANALYTICAL_WINDOW, f"Expected ANALYTICAL_WINDOW intent for query: {query}, got {plan.intent}"
    assert plan.requires_window_function is True
    win_plan = plan.window_plan or plan.analytical_window_plan
    assert win_plan is not None, "WindowPlan must be populated by planner"
    assert win_plan.function == expected_func, f"Expected function {expected_func}, got {win_plan.function}"

    # 2. JSON Generation Layer
    sq = await json_chain.generate(query)
    assert sq.window_function is not None, "StructuredQuery must contain WindowFunctionConfig"
    assert sq.window_function.function == expected_func
    assert sq.group_by is None, "Analytical window queries should not have standard GROUP BY aggregation"

    # 3. Query Validator Layer
    is_valid = validator.validate(sq)
    assert is_valid is True, "StructuredQuery must pass validation"

    # 4. SQL Generator Layer
    sql, params = generator.generate(sq)
    sql_upper = sql.upper()
    assert "OVER (" in sql_upper, f"Generated SQL must contain OVER clause: {sql}"
    assert expected_col_part.upper() in sql_upper, f"Expected column/expression part '{expected_col_part}' in SQL: {sql}"
    assert expected_frame_part.upper() in sql_upper, f"Expected frame/clause part '{expected_frame_part}' in SQL: {sql}"


def test_phase43_frame_clause_variations(generator):
    """
    Verifies that SQLGenerator compiles various frame specifications accurately
    and generates valid SQL for advanced analytical window expressions.
    """
    from app.ai.structured_output.schemas import StructuredQuery, WindowFunctionConfig, SortCondition
    
    # Test ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
    sq = StructuredQuery(
        table="payroll",
        columns=["payroll.payment_date", "payroll.base_salary"],
        window_function=WindowFunctionConfig(
            function="AVG",
            column="base_salary",
            order_by=[SortCondition(table="payroll", field="payment_date", direction="asc")],
            frame="ROWS BETWEEN 5 PRECEDING AND CURRENT ROW",
            alias="rolling_6_avg"
        )
    )
    sql, _ = generator.generate(sq)
    assert "AVG(payroll.base_salary) OVER (ORDER BY payroll.payment_date ASC ROWS BETWEEN 5 PRECEDING AND CURRENT ROW) AS rolling_6_avg" in sql

    # Test DIFFERENCE compilation
    sq_diff = StructuredQuery(
        table="payroll",
        columns=["payroll.payment_date", "payroll.base_salary"],
        window_function=WindowFunctionConfig(
            function="DIFFERENCE",
            column="base_salary",
            order_by=[SortCondition(table="payroll", field="payment_date", direction="asc")],
            alias="salary_diff"
        )
    )
    sql_diff, _ = generator.generate(sq_diff)
    assert "payroll.base_salary - LAG(payroll.base_salary) OVER (ORDER BY payroll.payment_date ASC) AS salary_diff" in sql_diff
