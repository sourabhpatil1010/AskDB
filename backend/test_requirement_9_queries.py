import pytest
import asyncio
from app.services.ai.json_service import JSONService
from app.query_builder.sql_generator import SQLGenerator
from app.query_builder.query_validator import QueryValidator
from app.models import Base

@pytest.mark.asyncio
async def test_requirement_9_all_queries():
    queries = [
        # Basic
        "Show all employees",
        "Show all departments",
        # Aggregation
        "Employee count",
        "Employee count by department",
        "Average salary",
        "Average salary by department",
        "Monthly hiring trend",
        # Ranking
        "Top 10 salaries",
        "Highest salary employee",
        "Second highest salary",
        "Highest salary employee in each department",
        "Top 3 salaries per department",
    ]
    
    json_service = JSONService()
    generator = SQLGenerator()
    validator = QueryValidator()
    
    print("\n" + "="*80)
    print("VERIFYING REQUIREMENT 9: REGRESSION & SCHEMA-AWARE RESOLUTION")
    print("="*80)
    
    for q in queries:
        print(f"\n--- Testing Query: '{q}' ---")
        structured_query = await json_service.process_query(q)
        print(f"StructuredQuery Table: {structured_query.table}")
        print(f"StructuredQuery Columns: {structured_query.columns}")
        
        # Validate query
        is_valid = validator.validate(structured_query)
        assert is_valid, f"Query validation failed for: {q}"
        
        # Generate SQL
        sql, params = generator.generate(structured_query)
        print(f"Generated SQL:\n{sql}")
        
        # Specific assertions for requirement checks
        if q == "Show all employees":
            assert "SELECT\n    employees.*" in sql or "SELECT\n    *" in sql
            assert "FROM employees" in sql
        elif q == "Show all departments":
            assert "SELECT\n    departments.*" in sql or "SELECT\n    *" in sql
            assert "FROM departments" in sql
        elif q == "Average salary":
            assert "AVG(payroll.base_salary)" in sql
            assert "employees.base_salary" not in sql
        elif q == "Top 10 salaries":
            assert "payroll.base_salary" in sql
            assert "employees.base_salary" not in sql
        elif q == "Highest salary employee":
            assert "payroll.base_salary" in sql
            assert "employees.base_salary" not in sql
        elif q == "Top 3 salaries per department":
            assert "payroll.base_salary" in sql
            assert "departments.base_salary" not in sql

if __name__ == "__main__":
    asyncio.run(test_requirement_9_all_queries())
