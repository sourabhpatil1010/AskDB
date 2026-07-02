import pytest
import asyncio
from app.services.ai.json_service import JSONService
from app.services.search.sql_service import SQLService
from app.ai.structured_output.schemas import StructuredQuery, HavingCondition
from app.query_builder.query_validator import QueryValidator

@pytest.mark.asyncio
async def test_all_23_phase2_queries():
    queries = [
        # 1. BASIC
        ("Show all departments", ["departments"]),
        ("Show all employees", ["employees"]),
        ("List all projects", ["projects"]),
        
        # 2. AGGREGATION
        ("Employee count", ["COUNT("]),
        ("Total employees", ["COUNT("]),
        ("Average salary", ["AVG(", "base_salary"]),
        ("Total payroll", ["SUM(", "base_salary"]),
        ("Maximum bonus", ["MAX(", "bonus"]),
        ("Minimum budget", ["MIN(", "budget"]),
        ("Distinct employee count", ["COUNT("]),
        
        # 3. GROUP BY
        ("Employee count by department", ["GROUP BY", "departments", "COUNT("]),
        ("Average salary by department", ["GROUP BY", "departments", "AVG("]),
        ("Employee count by office", ["GROUP BY", "offices", "COUNT("]),
        ("Average salary by office", ["GROUP BY", "offices", "AVG("]),
        
        # 4. HAVING
        ("Departments with more than 20 employees", ["HAVING", "COUNT(", "> 20"]),
        ("Departments with average salary above 100000", ["HAVING", "AVG(", "> 100000"]),
        ("Projects with more than 5 employees", ["HAVING", "COUNT(", "> 5"]),
        ("Managers with total payroll above 1000000", ["HAVING", "SUM(", "> 1000000"]),
        
        # 5. AGGREGATION + FILTER
        ("Average salary in IT department", ["AVG(", "WHERE"]),
        ("Total payroll for active employees", ["SUM(", "WHERE"]),
        
        # 6. AGGREGATION + TIME
        ("Employee count by month", ["DATE_TRUNC('month'", "GROUP BY"]),
        ("Average salary by year", ["DATE_TRUNC('year'", "GROUP BY"]),
        ("Monthly hiring trend", ["DATE_TRUNC('month'", "GROUP BY"]),
    ]
    
    json_service = JSONService()
    sql_service = SQLService()
    
    print("\n" + "="*80)
    print("VERIFYING ASKDB PHASE 2 AGGREGATION & ANALYTICS ENGINE (23 QUERIES)")
    print("="*80)
    
    for q, expected_substrings in queries:
        print(f"\n--- Testing Query: '{q}' ---")
        structured_query = await json_service.process_query(q)
        structured_json = structured_query.model_dump()
        print(f"Structured JSON: {structured_json}")
        
        sql, params = sql_service.build_sql(structured_json)
        print(f"Generated SQL:\n{sql}")
        if params:
            print(f"Parameters: {params}")
            
        for sub in expected_substrings:
            assert sub in sql, f"Expected substring '{sub}' not found in SQL for query '{q}':\n{sql}"

def test_validator_enforces_numeric_aggregations():
    validator = QueryValidator()
    
    # 1. Valid numeric aggregation should pass
    valid_query = StructuredQuery(
        table="payroll",
        columns=["AVG(payroll.base_salary) AS avg_sal", "SUM(payroll.bonus) AS total_bonus"]
    )
    assert validator.validate(valid_query) is True
    
    # 2. Invalid non-numeric aggregation should raise ValueError
    invalid_query = StructuredQuery(
        table="departments",
        columns=["AVG(departments.name) AS avg_name"]
    )
    with pytest.raises(ValueError, match="Validation failed: Aggregate function AVG requires a numeric column"):
        validator.validate(invalid_query)
        
    invalid_sum_query = StructuredQuery(
        table="employees",
        columns=["SUM(employees.first_name) AS sum_name"]
    )
    with pytest.raises(ValueError, match="Validation failed: Aggregate function SUM requires a numeric column"):
        validator.validate(invalid_sum_query)
        
    print("\n--- QueryValidator numeric aggregation enforcement tests passed! ---")
