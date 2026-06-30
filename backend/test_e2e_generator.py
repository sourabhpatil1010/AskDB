"""End-to-end test: StructuredQuery -> SQL + coerced parameters."""
from datetime import date
from app.ai.structured_output.schemas import StructuredQuery, FilterCondition, OperatorEnum
from app.query_builder.sql_generator import SQLGenerator

gen = SQLGenerator()

# Test: Date filter (the exact failing scenario)
query = StructuredQuery(
    table="employees",
    columns=["first_name", "last_name", "hire_date"],
    filters=[
        FilterCondition(table="employees", field="hire_date", operator=OperatorEnum.GTE, value="2024-01-01"),
    ],
    limit=10,
)
sql, params = gen.generate(query)
print("=== GTE Date Filter ===")
print(f"SQL: {sql}")
print(f"Params: {params}")
assert isinstance(params["employees_hire_date_1"], date), f"Expected date, got {type(params['employees_hire_date_1'])}"
print("PASS: hire_date is datetime.date\n")

# Test: BETWEEN dates
query2 = StructuredQuery(
    table="employees",
    columns=["*"],
    filters=[
        FilterCondition(table="employees", field="hire_date", operator=OperatorEnum.BETWEEN, value=["2024-01-01", "2024-12-31"]),
    ],
    limit=50,
)
sql2, params2 = gen.generate(query2)
print("=== BETWEEN Date Filter ===")
print(f"SQL: {sql2}")
print(f"Params: {params2}")
assert isinstance(params2["employees_hire_date_1_1"], date)
assert isinstance(params2["employees_hire_date_1_2"], date)
print("PASS: both BETWEEN values are datetime.date\n")

# Test: IN with strings (should stay strings for name column)
query3 = StructuredQuery(
    table="employees",
    columns=["*"],
    filters=[
        FilterCondition(field="first_name", operator=OperatorEnum.IN, value=["Alice", "Bob"]),
    ],
    limit=50,
)
sql3, params3 = gen.generate(query3)
print("=== IN String Filter ===")
print(f"SQL: {sql3}")
print(f"Params: {params3}")
assert isinstance(params3["first_name_1_0"], str)
print("PASS: string values unchanged\n")

# Test: Numeric filter
query4 = StructuredQuery(
    table="departments",
    columns=["name", "budget"],
    filters=[
        FilterCondition(field="budget", operator=OperatorEnum.GT, value="100000"),
    ],
    limit=50,
)
sql4, params4 = gen.generate(query4)
print("=== Numeric Filter ===")
print(f"SQL: {sql4}")
print(f"Params: {params4}")
assert isinstance(params4["budget_1"], float)
print("PASS: budget coerced to float\n")

print("All end-to-end tests passed!")
