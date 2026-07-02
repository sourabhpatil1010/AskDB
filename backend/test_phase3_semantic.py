import pytest
import asyncio
from app.services.ai.json_service import JSONService
from app.services.search.sql_service import SQLService

@pytest.mark.asyncio
async def test_equivalent_grouping_queries():
    queries = [
        "Employee count by department",
        "Employee count per department",
        "Employee count in each department",
        "Number of employees in every department",
        "Departments with employee count",
    ]
    json_service = JSONService()
    sql_service = SQLService()
    
    for q in queries:
        structured_query = await json_service.process_query(q)
        structured_json = structured_query.model_dump()
        sql, params = sql_service.build_sql(structured_json)
        assert "GROUP BY" in sql, f"Expected GROUP BY in SQL for query '{q}':\n{sql}"
        assert "departments" in sql.lower() or "department" in sql.lower(), f"Expected departments in SQL for query '{q}':\n{sql}"
        assert "COUNT(" in sql, f"Expected COUNT in SQL for query '{q}':\n{sql}"

@pytest.mark.asyncio
async def test_equivalent_having_queries():
    queries = [
        ("Departments with more than 20 employees", ["HAVING", "COUNT(", "> 20"]),
        ("Departments having at least 20 employees", ["HAVING", "COUNT(", ">= 20"]),
        ("Departments having over 20 employees", ["HAVING", "COUNT(", "> 20"]),
        ("Departments whose employee count exceeds 20", ["HAVING", "COUNT(", "> 20"]),
        ("Departments with fewer than 10 employees", ["HAVING", "COUNT(", "< 10"]),
    ]
    json_service = JSONService()
    sql_service = SQLService()
    
    for q, expected in queries:
        structured_query = await json_service.process_query(q)
        structured_json = structured_query.model_dump()
        sql, params = sql_service.build_sql(structured_json)
        for exp in expected:
            assert exp in sql, f"Expected substring '{exp}' not found in SQL for query '{q}':\n{sql}"

@pytest.mark.asyncio
async def test_having_semantic_phrases():
    queries = [
        ("Departments with greater than 15 employees", ["> 15"]),
        ("Departments with less than 5 employees", ["< 5"]),
        ("Departments with at most 50 employees", ["<= 50"]),
        ("Departments with under 12 employees", ["< 12"]),
        ("Departments with no fewer than 8 employees", [">= 8"]),
        ("Departments with no more than 25 employees", ["<= 25"]),
    ]
    json_service = JSONService()
    sql_service = SQLService()
    
    for q, expected in queries:
        structured_query = await json_service.process_query(q)
        structured_json = structured_query.model_dump()
        sql, params = sql_service.build_sql(structured_json)
        assert "HAVING" in sql, f"Expected HAVING in SQL for query '{q}':\n{sql}"
        for exp in expected:
            assert exp in sql, f"Expected substring '{exp}' not found in SQL for query '{q}':\n{sql}"

@pytest.mark.asyncio
async def test_grouping_semantic_phrases():
    queries = [
        "Total payroll by department",
        "Total payroll per department",
        "Total payroll for each department",
        "Total payroll in each department",
        "Total payroll grouped by department",
        "Total payroll each department",
        "Total payroll every department",
    ]
    json_service = JSONService()
    sql_service = SQLService()
    
    for q in queries:
        structured_query = await json_service.process_query(q)
        structured_json = structured_query.model_dump()
        sql, params = sql_service.build_sql(structured_json)
        assert "GROUP BY" in sql, f"Expected GROUP BY in SQL for query '{q}':\n{sql}"
        assert "SUM(" in sql, f"Expected SUM in SQL for query '{q}':\n{sql}"
        assert "departments" in sql.lower() or "department" in sql.lower(), f"Expected department table in SQL for query '{q}':\n{sql}"

@pytest.mark.asyncio
async def test_manual_validation_queries():
    queries = [
        # Basic
        ("Show all employees", ["SELECT", "FROM employees"]),
        ("Show all departments", ["SELECT", "FROM departments"]),
        # Aggregation
        ("Employee count per department", ["GROUP BY", "COUNT("]),
        ("Departments with more than 20 employees", ["HAVING", "COUNT(", "> 20"]),
        ("Departments having at least 30 employees", ["HAVING", "COUNT(", ">= 30"]),
        ("Average salary", ["AVG(", "base_salary"]),
        ("Total payroll", ["SUM(", "base_salary"]),
        ("Highest salary", ["base_salary"]),
        ("Lowest salary", ["base_salary"]),
        # Ranking
        ("Top 10 salaries", ["ORDER BY", "LIMIT 10"]),
        ("Highest salary employee", ["ORDER BY", "LIMIT 1"]),
        ("Highest salary employee in each department", ["departments", "base_salary"]),
        ("Second highest salary", ["DENSE_RANK()", "rank_num = 2"]),
        ("Top 3 salaries per department", ["departments", "base_salary"]),
        # Time
        ("Monthly hiring trend", ["DATE_TRUNC('month'", "GROUP BY"]),
        ("Employees hired this year", ["WHERE", "hire_date"]),
        ("Employees hired last month", ["WHERE", "hire_date"]),
        # Filtering
        ("Active employees", ["WHERE", "status", "active"]),
        ("Employees in IT", ["WHERE"]),
        ("Employees earning more than 60000", ["WHERE", ">", "60000", "base_salary"]),
        # Sorting
        ("Highest paid employees", ["ORDER BY", "base_salary DESC"]),
        ("Newest employees", ["ORDER BY", "hire_date DESC"]),
        ("Oldest employees", ["ORDER BY", "hire_date ASC"]),
    ]
    json_service = JSONService()
    sql_service = SQLService()
    
    for q, expected in queries:
        structured_query = await json_service.process_query(q)
        structured_json = structured_query.model_dump()
        sql, params = sql_service.build_sql(structured_json)
        for exp in expected:
            assert exp.lower() in sql.lower() or exp.lower() in str(params).lower(), f"Expected substring '{exp}' not found in SQL/params for query '{q}':\nSQL: {sql}\nParams: {params}"
