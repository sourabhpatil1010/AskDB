import pytest
import asyncio
from app.ai.planner.planner import AIQueryPlanner
from app.ai.chains.json_chain import JSONGenerationChain
from app.query_builder.sql_generator import SQLGenerator
from app.ai.planner.planner_schema import IntentEnum

@pytest.fixture
def planner():
    return AIQueryPlanner()

@pytest.fixture
def json_chain():
    return JSONGenerationChain()

@pytest.fixture
def sql_generator():
    return SQLGenerator()

# 18 Target Ranking Queries across the three strategies
TARGET_QUERIES = [
    # Global Top-N / Bottom-N
    ("Top 10 salaries", "global", "top", 10),
    ("Top 5 base salaries in payroll", "global", "top", 5),
    ("Lowest 5 attendance hours", "global", "bottom", 5),
    ("3 lowest salaries", "global", "bottom", 3),
    ("Top 5 salaries across all departments", "global", "top", 5),
    ("Top 10 Attendance records by hours worked", "global", "top", 10),
    
    # N-th Rank Queries
    ("2nd highest salary", "global", "nth", 2),
    ("Second highest salary per department", "per_group", "nth", 2),
    ("3rd highest base salary", "global", "nth", 3),
    ("4th highest earner overall", "global", "nth", 4),
    ("Second lowest attendance hours", "global", "nth", 2),
    ("3rd best performance review score", "global", "nth", 3),
    
    # Ranking Within Groups / Partitions
    ("Highest salary employee in each department", "per_group", "top", 1),
    ("Top 3 salaries per department", "per_group", "top", 3),
    ("Latest employee in every department", "per_group", "top", 1),
    ("Best employee in every department", "per_group", "top", 1),
    ("Latest payroll for each employee", "per_group", "top", 1),
    ("Top performer in each team", "per_group", "top", 1),
]

@pytest.mark.asyncio
@pytest.mark.parametrize("query_text, expected_scope, expected_type, expected_rank", TARGET_QUERIES)
async def test_ranking_pipeline_e2e(query_text, expected_scope, expected_type, expected_rank, planner, json_chain, sql_generator):
    print(f"\n--- Testing Ranking Query: '{query_text}' ---")
    
    # 1. AI Planner Stage
    plan = await planner.plan(query_text)
    print(f"  [Planner] Intent: {plan.intent.value}, Tables: {plan.tables}")
    print(f"  [Planner] Ranking - Type: {getattr(plan, 'ranking_type', None)}, Rank: {getattr(plan, 'rank', None)}, Scope: {getattr(plan, 'scope', None)}")
    
    assert plan.confidence >= 0.70, f"Confidence too low: {plan.confidence}"
    is_ranking_plan = (
        plan.intent == IntentEnum.RANKING
        or getattr(plan, "requires_window_function", False)
        or getattr(plan, "ranking_type", None)
        or getattr(plan, "nth_rank", None)
        or getattr(plan, "limit_per_group", None)
    )
    assert is_ranking_plan, f"Query '{query_text}' was not identified as a ranking plan!"

    # 2. Structured JSON Stage
    structured_query = await json_chain.generate(query_text)
    print(f"  [JSON] Table: {structured_query.table}, Columns: {structured_query.columns}")
    if structured_query.ranking:
        print(f"  [JSON] RankingConfig: {structured_query.ranking.model_dump()}")
    
    # Verify RankingConfig is present for N-th or per_group queries
    if expected_scope == "per_group" or expected_type == "nth":
        assert structured_query.ranking is not None, f"Expected RankingConfig for '{query_text}'"
        assert structured_query.ranking.type == expected_type or (expected_type == "nth" and structured_query.ranking.dense_rank)
        if expected_scope == "per_group":
            assert structured_query.ranking.scope == "per_group" or structured_query.ranking.partition_by
            
    # 3. SQL Generator Stage
    sql, params = sql_generator.generate(structured_query)
    print(f"  [SQL Generator] Generated SQL:\n{sql}")
    if params:
        print(f"  [SQL Generator] Params: {params}")
        
    assert sql and len(sql.strip()) > 0, "Generated SQL is empty!"
    
    # Verify SQL syntax structure based on strategy
    if expected_type == "nth":
        assert "DENSE_RANK()" in sql or "ROW_NUMBER()" in sql, f"Expected DENSE_RANK or ROW_NUMBER window function in SQL for N-th query: {sql}"
        assert "WITH ranked_data AS" in sql, f"Expected CTE wrapper for N-th rank query: {sql}"
        assert f"rank_num = {expected_rank}" in sql or f"rank_num <= {expected_rank}" in sql, f"Expected rank filter in SQL: {sql}"
    elif expected_scope == "per_group":
        assert "OVER (" in sql and "PARTITION BY" in sql, f"Expected PARTITION BY window function in SQL for grouped ranking: {sql}"
        assert "WITH ranked_data AS" in sql, f"Expected CTE wrapper for grouped ranking query: {sql}"
        assert f"rank_num <= {expected_rank}" in sql or f"rank_num = {expected_rank}" in sql, f"Expected rank limit in SQL: {sql}"
    else:
        # Global Top-N / Bottom-N
        assert "ORDER BY" in sql, f"Expected ORDER BY in global ranking query: {sql}"
        assert "LIMIT" in sql or "WITH ranked_data AS" in sql, f"Expected LIMIT or CTE in global ranking query: {sql}"
