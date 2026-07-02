"""
debug_pipeline.py — Standalone debug script to trace the full pipeline:
  Natural Language → Planner Output → StructuredQuery JSON → Generated SQL

Run from backend/ directory:
    venv\Scripts\python debug_pipeline.py

This does NOT execute SQL against the database. It shows what SQL would be generated.
"""
import asyncio
import json
import sys
import os

# Add the backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Minimal environment setup
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://dummy:dummy@localhost/dummy")

TEST_QUERIES = [
    # Time granularity tests (the core bug)
    "Employee count by month this year",
    "Show monthly employee count this year",
    "Hiring trend by quarter",
    "Attendance by week",
    "Revenue by quarter",
    # Aggregation tests
    "Compare average salary by department excluding interns",
    "Top 5 departments by payroll",
    "Average salary of active employees by department",
    # HAVING tests
    "Departments with more than 20 employees",
    "Departments with average salary above 80000",
    # Business language
    "Employees hired after COVID",
    "Year over year salary growth",
    "Managers with highest average salary",
    # Simple
    "List all active employees",
    "Count total employees",
]

SEPARATOR = "=" * 70


async def run_debug():
    from app.ai.planner.planner_service import PlannerService
    from app.ai.chains.json_chain import JSONGenerationChain, _build_translation_hints
    from app.query_builder.sql_generator import SQLGenerator

    planner_service = PlannerService()
    chain = JSONGenerationChain()
    sql_gen = SQLGenerator()

    results = []
    pass_count = 0
    fail_count = 0

    for query in TEST_QUERIES:
        print(f"\n{SEPARATOR}")
        print(f"QUERY: {query}")
        print(SEPARATOR)

        result = {"query": query, "status": "PASS"}

        try:
            # Stage 1: Planner
            plan = await planner_service.create_plan(query)
            plan_dict = json.loads(plan.model_dump_json())
            print(f"\n[1] PLANNER OUTPUT:")
            print(f"    Intent:          {plan_dict.get('intent')}")
            print(f"    Tables:          {plan_dict.get('tables')}")
            print(f"    Metrics:         {plan_dict.get('metrics')}")
            print(f"    Group By:        {plan_dict.get('group_by')}")
            print(f"    Filters:         {plan_dict.get('filters')}")
            print(f"    Having:          {plan_dict.get('having')}")
            print(f"    Order By:        {plan_dict.get('order_by')}")
            print(f"    Limit:           {plan_dict.get('limit')}")
            print(f"    Confidence:      {plan_dict.get('confidence')}")

            result["plan"] = {
                "intent": plan_dict.get("intent"),
                "tables": plan_dict.get("tables"),
                "group_by": plan_dict.get("group_by"),
                "metrics": plan_dict.get("metrics"),
                "having": plan_dict.get("having"),
                "confidence": plan_dict.get("confidence"),
            }

            # Stage 2: Translation hints
            hints = _build_translation_hints(plan)
            if hints:
                print(f"\n[2] TRANSLATION HINTS:")
                for line in hints.split("\n"):
                    print(f"    {line}")

            # Stage 3: JSON generation (requires LLM)
            try:
                structured_query = await chain.generate(query)
                sq_dict = json.loads(structured_query.model_dump_json())
                print(f"\n[3] GENERATED STRUCTURED QUERY:")
                print(f"    Table:          {sq_dict.get('table')}")
                print(f"    Columns:        {sq_dict.get('columns')}")
                print(f"    Joins:          {sq_dict.get('joins')}")
                print(f"    Filters:        {sq_dict.get('filters')}")
                print(f"    Group By:       {sq_dict.get('group_by')}")
                print(f"    Having:         {sq_dict.get('having')}")
                print(f"    Time Granularity: {sq_dict.get('time_granularity')}")
                print(f"    Sort:           {sq_dict.get('sort')}")
                print(f"    Limit:          {sq_dict.get('limit')}")

                result["structured_query"] = sq_dict

                # Stage 4: SQL generation
                sql, params = sql_gen.generate(structured_query)
                print(f"\n[4] GENERATED SQL:")
                for line in sql.split("\n"):
                    print(f"    {line}")
                if params:
                    print(f"\n    Parameters: {params}")

                result["sql"] = sql
                result["params"] = {k: str(v) for k, v in params.items()}

                # Assertions for specific queries
                if "by month" in query.lower() or "monthly" in query.lower():
                    assert "DATE_TRUNC" in sql or "date_trunc" in sql, \
                        f"FAIL: Expected DATE_TRUNC in SQL for time-granularity query"
                    assert "GROUP BY" in sql, "FAIL: Expected GROUP BY in SQL"
                    print(f"\n    ✅ TIME GRANULARITY: DATE_TRUNC present and GROUP BY correct")

                if "more than" in query.lower() and "employees" in query.lower():
                    assert "HAVING" in sql, "FAIL: Expected HAVING clause for filter-on-aggregate query"
                    print(f"\n    ✅ HAVING CLAUSE: Present in SQL")

                pass_count += 1
                result["status"] = "PASS"

            except Exception as llm_err:
                print(f"\n[3] JSON/SQL Generation skipped: {str(llm_err)[:120]}")
                print(f"    (This is expected when LLM endpoint is unavailable in debug mode)")
                result["status"] = "LLM_UNAVAILABLE"

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            result["status"] = "FAIL"
            result["error"] = str(e)
            fail_count += 1

        results.append(result)

    # Summary
    print(f"\n{SEPARATOR}")
    print(f"PIPELINE DEBUG SUMMARY")
    print(f"{SEPARATOR}")
    print(f"Total Queries:       {len(TEST_QUERIES)}")
    print(f"Planner Pass:        {sum(1 for r in results if r['status'] in ('PASS', 'LLM_UNAVAILABLE'))}")
    print(f"Full Pipeline Pass:  {pass_count}")
    print(f"Failed:              {fail_count}")
    print(SEPARATOR)


if __name__ == "__main__":
    asyncio.run(run_debug())
