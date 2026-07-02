import pytest
import asyncio
from app.services.ai.json_service import JSONService
from app.services.search.sql_service import SQLService
from app.query_builder.query_executor import QueryExecutor
from app.models import Base

@pytest.mark.asyncio
async def test_phase1_queries():
    queries = [
        # Basic
        "Show all employees",
        "Show all departments",
        "Show payroll",
        "Show attendance",
        # Aggregation
        "Employee count",
        "Employee count by department",
        "Average salary",
        "Average salary by department",
        "Maximum salary",
        "Minimum salary",
        # Sorting
        "Top 10 salaries",
        "Highest salary employee",
    ]
    
    json_service = JSONService()
    sql_service = SQLService()
    
    print("\n" + "="*80)
    print("VERIFYING PHASE 1 STABILIZATION QUERIES")
    print("="*80)
    
    for q in queries:
        print(f"\n--- Testing Query: '{q}' ---")
        structured_query = await json_service.process_query(q)
        structured_json = structured_query.model_dump()
        print(f"Structured JSON: {structured_json}")
        
        # Build SQL (will validate and run debug logging)
        sql, params = sql_service.build_sql(structured_json)
        print(f"Generated SQL:\n{sql}")
        
        # Specific checks for Phase 1 requirements
        if q == "Employee count by department":
            assert "departments.employee_id" not in sql, "Join Resolver invented departments.employee_id!"
            assert "employees.department_id = departments.id" in sql or "departments.id = employees.department_id" in sql, f"Incorrect join in SQL:\n{sql}"
        elif q in ("Average salary", "Top 10 salaries", "Highest salary employee"):
            assert "employees.base_salary" not in sql, "Column resolver resolved base_salary to employees table!"
            assert "payroll.base_salary" in sql, f"payroll.base_salary not found in SQL:\n{sql}"

def test_sql_safety_validator():
    executor = QueryExecutor()
    print("\n--- Testing SQL Safety Validator ---")
    
    # 1. Valid SELECT
    assert executor._is_safe("SELECT * FROM employees;") == True
    
    # 2. Valid CTE WITH ... SELECT
    cte_sql = """
    WITH ranked AS (
        SELECT payroll.base_salary, DENSE_RANK() OVER (ORDER BY payroll.base_salary DESC) as rank_num
        FROM employees JOIN payroll ON employees.id = payroll.employee_id
    )
    SELECT * FROM ranked WHERE rank_num = 1;
    """
    assert executor._is_safe(cte_sql) == True, "Validator rejected valid WITH ... SELECT query!"
    
    # 3. Unsafe queries
    unsafe_queries = [
        "INSERT INTO employees (id, first_name) VALUES ('123', 'John');",
        "UPDATE employees SET first_name = 'Hacked';",
        "DELETE FROM employees;",
        "DROP TABLE employees;",
        "ALTER TABLE employees ADD COLUMN hacked text;",
        "TRUNCATE TABLE employees;",
        "COPY employees TO '/tmp/data.csv';",
        "EXECUTE immediate 'DROP TABLE employees';",
        "WITH cte AS (DELETE FROM employees RETURNING *) SELECT * FROM cte;"
    ]
    
    for u_sql in unsafe_queries:
        assert executor._is_safe(u_sql) == False, f"Validator failed to reject unsafe SQL: {u_sql}"
        try:
            # Check execute raises ValueError
            import asyncio
            asyncio.run(executor.execute(None, u_sql, {}))
            raise AssertionError(f"execute() did not raise ValueError for: {u_sql}")
        except ValueError:
            pass

if __name__ == "__main__":
    asyncio.run(test_phase1_queries())
    test_sql_safety_validator()
