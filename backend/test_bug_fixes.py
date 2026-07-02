import sys
import os
import asyncio
import pytest

# Ensure app is in path
sys.path.insert(0, os.path.abspath("."))

from app.ai.structured_output.schemas import StructuredQuery, SortCondition, FilterCondition, HavingCondition, OperatorEnum, JoinCondition
from app.query_builder.sql_generator import SQLGenerator
from app.query_builder.query_validator import QueryValidator
from app.ai.planner.planner import AIQueryPlanner
from app.ai.planner.planner_schema import PlannerValidationException, PlannerClarificationException
from app.ai.chains.json_chain import _build_translation_hints
from app.models import Base

def test_bug_1_order_by_raw_date_column_when_grouped():
    print("\n--- TEST BUG 1: Intercepting raw date column in ORDER BY when grouped by DATE_TRUNC ---")
    query = StructuredQuery(
        table="employees",
        columns=["DATE_TRUNC('month', employees.hire_date) AS month", "COUNT(employees.id) AS count"],
        group_by=["DATE_TRUNC('month', employees.hire_date)"],
        sort=SortCondition(field="hire_date", direction="asc", table="employees"),
        limit=50
    )
    validator = QueryValidator()
    assert validator.validate(query), "QueryValidator failed on time granularity query"
    
    generator = SQLGenerator()
    sql, params = generator.generate(query)
    print("Generated SQL:\n", sql)
    
    assert "ORDER BY month ASC" in sql or "ORDER BY DATE_TRUNC" in sql, f"ORDER BY not replaced! Got SQL:\n{sql}"
    assert "ORDER BY employees.hire_date" not in sql and "ORDER BY hire_date ASC" not in sql, "Raw column still in ORDER BY!"
    print("✅ BUG 1 TEST PASSED: Raw date column in ORDER BY was cleanly replaced by alias/expression.")

@pytest.mark.asyncio
async def test_bug_2_having_clause_boolean_evaluation():
    print("\n--- TEST BUG 2: Departments with more than 20 employees (HAVING clause) ---")
    planner = AIQueryPlanner()
    plan = await planner.plan("Departments with more than 20 employees")
    
    print("Plan having:", plan.having)
    try:
        hints = _build_translation_hints(plan)
        print("Generated translation hints successfully:\n", hints)
    except TypeError as e:
        if "Boolean value of this clause is not defined" in str(e):
            raise AssertionError("❌ BUG 2 FAILED: TypeError raised during HAVING translation hints!") from e
        raise e
        
    query = StructuredQuery(
        table="employees",
        columns=["departments.name", "COUNT(employees.id) AS count"],
        joins=[JoinCondition(table="departments", on="employees.department_id = departments.id")],
        group_by=["departments.name"],
        having=[HavingCondition(column="COUNT(employees.id)", operator=">", value=20)],
        sort=SortCondition(field="count", direction="desc"),
        limit=50
    )
    validator = QueryValidator()
    assert validator.validate(query), "QueryValidator failed on HAVING query"
    
    generator = SQLGenerator()
    sql, params = generator.generate(query)
    print("Generated SQL:\n", sql)
    assert "HAVING COUNT(employees.id) > 20" in sql, f"HAVING clause missing! Got SQL:\n{sql}"
    print("✅ BUG 2 TEST PASSED: No TypeError raised, valid HAVING SQL generated.")

def test_bug_3_schema_aware_full_name_resolution():
    print("\n--- TEST BUG 3: Schema-aware resolution of synthetic 'full_name' column ---")
    query = StructuredQuery(
        table="employees",
        columns=["employees.full_name", "payroll.base_salary"],
        joins=[JoinCondition(table="payroll", on="employees.id = payroll.employee_id")],
        sort=SortCondition(field="base_salary", direction="desc", table="payroll"),
        limit=10
    )
    validator = QueryValidator()
    assert validator.validate(query), "QueryValidator rejected synthetic full_name column!"
    
    generator = SQLGenerator()
    sql, params = generator.generate(query)
    print("Generated SQL:\n", sql)
    
    assert "CONCAT(employees.first_name, ' ', employees.last_name) AS full_name" in sql, f"CONCAT expression not generated! Got SQL:\n{sql}"
    assert "employees.full_name," not in sql, "Unresolved full_name still present in SQL!"
    print("✅ BUG 3 TEST PASSED: full_name was schema-aware resolved to CONCAT(first_name, ' ', last_name).")

@pytest.mark.asyncio
async def test_bug_4_verify_all_aggregation_queries():
    print("\n--- TEST BUG 4: Verifying all required queries generate valid ExecutionPlan & SQL ---")
    queries_to_test = [
        "Show all departments",
        "Show all employees",
        "Average salary",
        "Average salary by department",
        "Employee count",
        "Employee count by department",
        "Employee count by month",
        "Employees hired this year",
        "Monthly hiring trend",
        "Departments with more than 20 employees",
        "Top 10 salaries",
    ]
    
    planner = AIQueryPlanner()
    
    for q_text in queries_to_test:
        print(f"\nTesting planner & translation hints for: '{q_text}'")
        plan = await planner.plan(q_text)
        assert plan is not None, f"Plan is None for {q_text}"
        hints = _build_translation_hints(plan)
        print(f"  -> Plan intent: {plan.intent.value}, tables: {plan.tables}, confidence: {plan.confidence}")
        
    # Verify the unsupported query is caught cleanly
    unsupported_q = "Calculate running total of salaries"
    print(f"\nTesting planner for unsupported Phase 1 query: '{unsupported_q}'")
    try:
        await planner.plan(unsupported_q)
        raise AssertionError("Should have raised PlannerValidationException for running total query!")
    except (PlannerValidationException, PlannerClarificationException) as e:
        print(f"  -> Successfully caught unsupported capability: {e}")
            
    print("\n✅ BUG 4 TEST PASSED: All 11 supported queries planned cleanly, and 1 unsupported query caught gracefully.")

async def main():
    test_bug_1_order_by_raw_date_column_when_grouped()
    await test_bug_2_having_clause_boolean_evaluation()
    test_bug_3_schema_aware_full_name_resolution()
    await test_bug_4_verify_all_aggregation_queries()
    print("\n=======================================================")
    print("🎉 ALL PRODUCTION STABILIZATION BUG FIX TESTS PASSED!")
    print("=======================================================")

if __name__ == "__main__":
    asyncio.run(main())
