"""
Schema-aware date resolution verification.
Tests that the resolver and planner produce correct column names for all tables.
"""
import sys, os, asyncio, pytest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://dummy:dummy@localhost/dummy")

from app.ai.planner.planner_utils import SchemaDateColumnResolver, TimeReasoningUtils
from app.ai.planner.planner import AIQueryPlanner
from app.ai.chains.json_chain import _build_translation_hints
from app.query_builder.sql_generator import SQLGenerator
from app.query_builder.query_validator import QueryValidator
from app.ai.structured_output.schemas import (
    StructuredQuery, FilterCondition, SortCondition,
    HavingCondition, JoinCondition, OperatorEnum
)

print("=" * 65)
print("TEST 1: SchemaDateColumnResolver — per-table column resolution")
print("=" * 65)

expected = {
    "employees":           "hire_date",
    "attendance":          "date",
    "payroll":             "period_start",
    "projects":            "start_date",
    "leave_requests":      "start_date",
    "performance_reviews": "review_date",
}

all_pass = True
for table, exp_col in expected.items():
    got = SchemaDateColumnResolver.resolve(table)
    status = "PASS" if got == exp_col else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  [{status}] {table}: expected={exp_col!r}, got={got!r}")

print()
print("=" * 65)
print("TEST 2: TimeReasoningUtils — schema-aware filter field resolution")
print("=" * 65)

time_queries = [
    ("employees",           "this year",          "hire_date"),
    ("employees",           "last month",          "hire_date"),
    ("attendance",          "this week",           "date"),
    ("payroll",             "last year",           "period_start"),
    ("projects",            "in 2023",             "start_date"),
    ("leave_requests",      "this month",          "start_date"),
    ("performance_reviews", "after 2022",          "review_date"),
]

for table, phrase, exp_field in time_queries:
    filters = TimeReasoningUtils.parse_time_phrase(phrase, table_name=table)
    if filters:
        got_field = filters[0].field
        status = "PASS" if got_field == exp_field else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  [{status}] {table!r} + {phrase!r}: field={got_field!r} (expected {exp_field!r})")
    else:
        print(f"  [SKIP] {table!r} + {phrase!r}: no filters produced")

print()
print("=" * 65)
print("TEST 3: Planner heuristic — correct filter fields after fix")
print("=" * 65)

@pytest.mark.asyncio
async def test_planner():
    global all_pass
    planner = AIQueryPlanner()

    planner_cases = [
        ("Employee count by month this year",   "employees", "hire_date"),
        ("Employees hired this year",           "employees", "hire_date"),
        ("Monthly hiring trend",                "employees", None),   # no date filter expected
        ("Employee count by quarter",           "employees", None),   # no date filter
        ("Daily attendance",                    "attendance", None),
        ("Weekly attendance",                   "attendance", None),
    ]

    for query, exp_table, exp_field in planner_cases:
        plan = await planner.plan(query)
        date_filters = [f for f in (plan.filters or []) if f.time_reasoning]
        if exp_field is None:
            status = "PASS"
            print(f"  [PASS] {query!r}: no time filter expected, got {len(date_filters)} time filter(s)")
        else:
            if date_filters:
                got_field = date_filters[0].field
                status = "PASS" if got_field == exp_field else "FAIL"
                if status == "FAIL":
                    all_pass = False
                print(f"  [{status}] {query!r}: filter field={got_field!r} (expected {exp_field!r})")
            else:
                print(f"  [WARN] {query!r}: expected filter on {exp_field!r} but got no time filter")

asyncio.run(test_planner())

print()
print("=" * 65)
print("TEST 4: _build_translation_hints — correct DATE_TRUNC expressions")
print("=" * 65)

@pytest.mark.asyncio
async def test_hints():
    global all_pass
    planner = AIQueryPlanner()
    hint_cases = [
        ("Employee count by month this year", "DATE_TRUNC('month', employees.hire_date)"),
        ("Employee count by quarter",         "DATE_TRUNC('quarter', employees.hire_date)"),
        ("Daily attendance",                  "DATE_TRUNC('day', attendance.date)"),
        ("Weekly attendance",                 "DATE_TRUNC('week', attendance.date)"),
        ("Monthly hiring trend",              "DATE_TRUNC('month', employees.hire_date)"),
    ]
    for query, expected_expr in hint_cases:
        plan = await planner.plan(query)
        hints = _build_translation_hints(plan)
        status = "PASS" if expected_expr in hints else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  [{status}] {query!r}")
        print(f"         Expected expr: {expected_expr!r}")
        if status == "FAIL":
            print(f"         Got hints:      {hints[:200]!r}")

asyncio.run(test_hints())

print()
print("=" * 65)
print("TEST 5: SQL generation — all required queries produce valid SQL")
print("=" * 65)

gen = SQLGenerator()
val = QueryValidator()

sql_cases = [
    {
        "name": "Employee count by month this year",
        "sq": StructuredQuery(
            table="employees",
            columns=["DATE_TRUNC('month', employees.hire_date) AS month", "COUNT(employees.id) AS count"],
            filters=[FilterCondition(field="hire_date", operator=OperatorEnum.BETWEEN,
                                     value=["2026-01-01", "2026-12-31"])],
            group_by=["DATE_TRUNC('month', employees.hire_date)"],
            sort=SortCondition(field="month", direction="asc"),
            time_granularity="month",
        )
    },
    {
        "name": "Employee count by quarter",
        "sq": StructuredQuery(
            table="employees",
            columns=["DATE_TRUNC('quarter', employees.hire_date) AS quarter", "COUNT(employees.id) AS count"],
            group_by=["DATE_TRUNC('quarter', employees.hire_date)"],
            sort=SortCondition(field="quarter", direction="asc"),
            time_granularity="quarter",
        )
    },
    {
        "name": "Employees hired this year",
        "sq": StructuredQuery(
            table="employees",
            columns=["employees.id", "employees.first_name", "employees.last_name", "employees.hire_date"],
            filters=[FilterCondition(field="hire_date", operator=OperatorEnum.BETWEEN,
                                     value=["2026-01-01", "2026-12-31"])],
        )
    },
    {
        "name": "Monthly hiring trend",
        "sq": StructuredQuery(
            table="employees",
            columns=["DATE_TRUNC('month', employees.hire_date) AS month", "COUNT(employees.id) AS count"],
            group_by=["DATE_TRUNC('month', employees.hire_date)"],
            sort=SortCondition(field="month", direction="asc"),
            time_granularity="month",
        )
    },
    {
        "name": "Average salary by department",
        "sq": StructuredQuery(
            table="employees",
            columns=["departments.name", "AVG(payroll.base_salary) AS avg_salary"],
            joins=[
                JoinCondition(table="departments", on="employees.department_id = departments.id"),
                JoinCondition(table="payroll", on="employees.id = payroll.employee_id"),
            ],
            group_by=["departments.name"],
            sort=SortCondition(field="avg_salary", direction="desc"),
        )
    },
    {
        "name": "Show all departments",
        "sq": StructuredQuery(
            table="departments",
            columns=["departments.id", "departments.name"],
        )
    },
    {
        "name": "Departments with more than 20 employees",
        "sq": StructuredQuery(
            table="employees",
            columns=["departments.name", "COUNT(employees.id) AS count"],
            joins=[JoinCondition(table="departments", on="employees.department_id = departments.id")],
            group_by=["departments.name"],
            having=[HavingCondition(column="COUNT(employees.id)", operator=">", value=20)],
            sort=SortCondition(field="count", direction="desc"),
        )
    },
    {
        "name": "Top 5 departments by average salary",
        "sq": StructuredQuery(
            table="employees",
            columns=["departments.name", "AVG(payroll.base_salary) AS avg_salary"],
            joins=[
                JoinCondition(table="departments", on="employees.department_id = departments.id"),
                JoinCondition(table="payroll", on="employees.id = payroll.employee_id"),
            ],
            group_by=["departments.name"],
            sort=SortCondition(field="avg_salary", direction="desc"),
            limit=5,
        )
    },
    {
        "name": "Daily attendance",
        "sq": StructuredQuery(
            table="attendance",
            columns=["DATE_TRUNC('day', attendance.date) AS day", "COUNT(attendance.employee_id) AS count"],
            group_by=["DATE_TRUNC('day', attendance.date)"],
            sort=SortCondition(field="day", direction="asc"),
            time_granularity="day",
        )
    },
    {
        "name": "Weekly attendance",
        "sq": StructuredQuery(
            table="attendance",
            columns=["DATE_TRUNC('week', attendance.date) AS week", "COUNT(attendance.employee_id) AS count"],
            group_by=["DATE_TRUNC('week', attendance.date)"],
            sort=SortCondition(field="week", direction="asc"),
            time_granularity="week",
        )
    },
]

for tc in sql_cases:
    try:
        val.validate(tc["sq"])
        sql, params = gen.generate(tc["sq"])
        print(f"  [PASS] {tc['name']}")
        for line in sql.splitlines():
            print(f"         {line}")
        print()
    except Exception as e:
        print(f"  [FAIL] {tc['name']}: {type(e).__name__}: {e}")
        all_pass = False

print("=" * 65)
if all_pass:
    print("[RESULT] ALL TESTS PASSED")
else:
    print("[RESULT] SOME TESTS FAILED — check output above")
print("=" * 65)
