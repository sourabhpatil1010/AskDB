import pytest
import asyncio
from app.ai.planner.planner import AIQueryPlanner
from app.services.ai.json_service import JSONService
from app.query_builder.query_validator import QueryValidator
from app.query_builder.sql_generator import SQLGenerator

@pytest.mark.asyncio
async def test_executable_window_sql_generation_e2e():
    """
    Verify full pipeline: Planner -> ExecutionPlan -> JSON -> StructuredQuery -> Validator -> SQL Generator -> Generated SQL.
    Ensure generated SQL supports window CTEs and required features across various queries.
    """
    planner = AIQueryPlanner()
    json_service = JSONService()
    validator = QueryValidator()
    sql_generator = SQLGenerator()

    queries = [
        ("Top 3 salaries per department", ["WITH ranked_data AS (", "ROW_NUMBER() OVER (", "PARTITION BY departments.name", "WHERE rank_num <= 3"]),
        ("Highest salary employee in each department", ["WITH ranked_data AS (", "ROW_NUMBER() OVER (", "PARTITION BY departments.name", "WHERE rank_num <= 1"]),
        ("Lowest salary employee in each department", ["WITH ranked_data AS (", "ROW_NUMBER() OVER (", "PARTITION BY departments.name", "ORDER BY payroll.base_salary ASC", "WHERE rank_num <= 1"]),
        ("Second highest salary", ["WITH ranked_data AS (", "DENSE_RANK() OVER (", "WHERE rank_num = 2"]),
        ("Third highest salary", ["WITH ranked_data AS (", "DENSE_RANK() OVER (", "WHERE rank_num = 3"]),
        ("Bottom 5 salaries", ["ROW_NUMBER() OVER (", "ORDER BY payroll.base_salary ASC", "LIMIT 5"]),
        ("Top 5 bonuses", ["ROW_NUMBER() OVER (", "ORDER BY payroll.bonus DESC", "LIMIT 5"]),
        ("Rank employees by salary", ["RANK() OVER (", "ORDER BY payroll.base_salary DESC"]),
    ]

    all_sql_combined = ""

    for q, expected_substrings in queries:
        # Step 1: Planner -> ExecutionPlan
        plan = await planner.plan(q)
        assert plan is not None, f"Planner failed for query: {q}"

        # Step 2: JSON -> StructuredQuery
        structured_query = await json_service.process_query(q)
        assert structured_query is not None, f"JSONService failed for query: {q}"

        # Step 3: Validator
        is_valid = validator.validate(structured_query)
        assert is_valid is True, f"Validator failed for query: {q}"

        # Step 4: SQL Generator -> Generated SQL
        sql, params = sql_generator.generate(structured_query)
        assert sql is not None and len(sql) > 0, f"SQL Generator returned empty SQL for query: {q}"

        all_sql_combined += "\n" + sql

        for exp in expected_substrings:
            assert exp in sql, f"Expected substring '{exp}' not found in SQL for query '{q}':\nGenerated SQL:\n{sql}"

    # Ensure across the suite, all required Phase 4.2 SQL elements are present
    required_elements = [
        "WITH ranked_data",
        "ROW_NUMBER()",
        "RANK()",
        "DENSE_RANK()",
        "PARTITION BY",
        "WHERE rank_num <= ",
        "WHERE rank_num = ",
    ]
    for req in required_elements:
        assert req in all_sql_combined, f"Required SQL element '{req}' not generated across Phase 4.2 test suite."

if __name__ == "__main__":
    asyncio.run(test_executable_window_sql_generation_e2e())
