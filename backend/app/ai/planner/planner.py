import re
import logging
from typing import List, Optional

from app.models import Base
from app.ai.planner.planner_schema import (
    ExecutionPlan, IntentEnum, Metric, Filter, HavingCondition, OrderCondition, WindowPlan, PlannerClarificationException
)
from app.ai.planner.planner_chain import PlannerChain
from app.ai.planner.planner_validator import PlannerValidator
from app.ai.planner.planner_utils import TimeReasoningUtils, JoinDetectionUtils, BusinessRuleUtils, QueryDecompositionUtils, RankingSemanticUtils, SYSTEM_TABLES

logger = logging.getLogger(__name__)


class AIQueryPlanner:
    """High-level AI Query Planner layer sitting before JSON Generation."""

    def __init__(self):
        self.chain = PlannerChain()
        self.validator = PlannerValidator()
        self.known_tables = [t for t in Base.metadata.tables.keys() if t not in SYSTEM_TABLES]

    async def plan(self, natural_language: str) -> ExecutionPlan:
        """Generates, validates, and enriches an ExecutionPlan from natural language."""
        logger.info(f"--- AI Query Planner Processing: '{natural_language}' ---")
        
        plan: Optional[ExecutionPlan] = None
        try:
            # Try LangChain LLM execution
            plan = await self.chain.generate_plan(natural_language)
            logger.info("LangChain LLM successfully generated execution plan.")
        except Exception as e:
            logger.warning(f"LLM execution unavailable or failed ({e}). Using deterministic heuristic planner fallback.")
            plan = self._create_heuristic_plan(natural_language)
            
        # Validate, enrich joins/time/rules/decomposition, and check < 0.70 confidence threshold
        validated_plan = self.validator.validate_and_enrich(plan, natural_language)
        logger.info(f"--- AI Query Planner Completed (Confidence: {validated_plan.confidence:.2f}) ---")
        return validated_plan

    def _create_heuristic_plan(self, query: str) -> ExecutionPlan:
        """Deterministic heuristic planner fallback for offline/test environments and robust rule-based parsing."""
        q_lower = query.lower().strip()
        
        table_keywords = {
            "employees": ["employ", "staff", "worker", "hire", "intern", "designation", "manager", "newest", "oldest", "earliest", "latest", "tenure"],
            "departments": ["department", "dept", "team"],
            "payroll": ["salary", "salaries", "pay", "bonus", "compensation", "payroll", "wage", "earning", "earner", "income", "paid"],
            "attendance": ["attend", "hours", "present", "absent"],
            "projects": ["project", "initiative"],
            "clients": ["client", "customer"],
            "offices": ["office", "location", "city", "country"],
            "performance_reviews": ["review", "performance", "score", "rating", "performer"],
            "leave_requests": ["leave", "vacation", "sick", "time off"],
            "skills": ["skill", "proficiency"]
        }

        # 1. Detect ambiguity or low confidence queries
        vague_phrases = ["vague", "unclear", "stuff", "what about", "tell me about", "just salary", "compare growth", "general info"]
        domain_keywords = [kw for kws in table_keywords.values() for kw in kws] + [
            "count", "average", "avg", "sum", "total", "max", "min", "top", "daily", "weekly", "monthly",
            "quarterly", "annual", "trend", "budget", "show", "list", "find", "all", "*"
        ]
        if any(vp in q_lower for vp in vague_phrases) or (len(q_lower.split()) <= 2 and not any(dk in q_lower for dk in domain_keywords)):
            logger.info("Heuristic planner detected ambiguous/vague query. Setting confidence < 0.70.")
            return ExecutionPlan(
                intent=IntentEnum.SEARCH,
                tables=["employees"],
                confidence=0.65,
                clarification_questions=[
                    "Did you mean Average Salary, Total Payroll, or Employee Count?",
                    "Please clarify which specific department or time period you would like to investigate."
                ]
            )

        # 2. Table Detection
        detected_tables = []
        for t_name, keywords in table_keywords.items():
            if any(kw in q_lower for kw in keywords):
                detected_tables.append(t_name)
        if not detected_tables:
            detected_tables = ["employees"]
        
        # Ensure join continuity if both department and payroll exist
        if "departments" in detected_tables and "payroll" in detected_tables and "employees" not in detected_tables:
            detected_tables.insert(1, "employees")
        if "payroll" in detected_tables and "employees" not in detected_tables:
            detected_tables.insert(0, "employees")

        # 3. Advanced ranking queries detection via generic semantic analyzer
        ranking_info = RankingSemanticUtils.analyze(query, detected_tables)
        if ranking_info:
            sal_field = ranking_info["metric_field"]
            dir_val = ranking_info["order"]
            limit_val = ranking_info["rank"]
            group_col = ranking_info["group"]
            tables = ranking_info["tables"]
            
            win_plan = WindowPlan(
                requires_window=True,
                function="DENSE_RANK" if ranking_info["nth_rank"] is not None else ("RANK" if "rank" in query.lower() else "ROW_NUMBER"),
                partition_by=ranking_info["partition_by"],
                order_by=[OrderCondition(field=sal_field, direction=dir_val)],
                alias="rank_num",
                ranking_type=ranking_info["ranking_type"]
            )
            
            return ExecutionPlan(
                intent=IntentEnum.RANKING,
                tables=tables,
                metrics=[Metric(field=sal_field, operation="", alias=sal_field)],
                group_by=[group_col] if group_col else None,
                order_by=[OrderCondition(field=sal_field, direction=dir_val)],
                limit=limit_val if ranking_info["scope"] == "global" else None,
                scope=ranking_info["scope"],
                ranking_type=ranking_info["ranking_type"],
                rank=limit_val,
                partition_by=ranking_info["partition_by"],
                order=dir_val,
                group=group_col,
                metric=sal_field,
                sort=dir_val.upper(),
                limit_per_group=limit_val if ranking_info["scope"] == "per_group" else None,
                nth_rank=ranking_info["nth_rank"],
                requires_window_function=ranking_info["requires_window_function"],
                window_plan=win_plan,
                requires_partition_ranking=ranking_info["requires_partition_ranking"],
                requires_correlated_subquery=ranking_info["requires_correlated_subquery"],
                confidence=0.95
            )

        # 4. Intent Detection
        intent = IntentEnum.FILTERING
        if any(w in q_lower for w in ["compare", "versus", "vs", "difference between"]):
            intent = IntentEnum.COMPARISON
        elif any(re.search(r'\b' + re.escape(w) + r'\b', q_lower) for w in ["top", "bottom", "highest", "lowest", "rank", "best", "worst", "largest", "smallest", "first", "last", "earliest", "latest", "newest", "oldest", "nth", "performer", "earner"]):
            intent = IntentEnum.RANKING
        elif any(w in q_lower for w in ["growth", "trend", "yoy", "mom", "year over year", "over time"]):
            intent = IntentEnum.TREND_ANALYSIS
        elif any(w in q_lower for w in ["average", "sum", "total", "count", "how many", "max", "min", "maximum", "minimum", "having", "with more than", "at least", "at most", "fewer than", "over ", "under "]):
            intent = IntentEnum.AGGREGATION

        # 5. Group By Detection & Time Granularity
        from app.ai.planner.planner_utils import SchemaColumnResolver, SchemaAggregationResolver, SemanticQueryParser
        group_by = SemanticQueryParser.extract_grouping(query, detected_tables)
        time_granularity = None
        time_units = {"month", "quarter", "year", "week", "day"}
        for gb in group_by:
            if gb in time_units:
                time_granularity = gb
                break

        # 6. Metric Extraction
        sal_field = SchemaAggregationResolver.resolve_numeric_metric(query, detected_tables)
        from sqlalchemy import Numeric, Integer, Float
        for t_name, t_obj in Base.metadata.tables.items():
            if t_name in SYSTEM_TABLES:
                continue
            if sal_field in t_obj.columns:
                col_obj = t_obj.columns[sal_field]
                if isinstance(col_obj.type, (Numeric, Integer, Float)) and t_name not in detected_tables:
                    detected_tables.append(t_name)
                    break
        metrics = SemanticQueryParser.extract_metrics(query, detected_tables, intent)

        # 7. Filter Extraction
        primary_table = detected_tables[0] if detected_tables else "employees"
        filters = TimeReasoningUtils.parse_time_phrase(query, table_name=primary_table)
        if "excluding intern" in q_lower or "exclude intern" in q_lower:
            filters.append(Filter(field="designation", operator="!=", value="Intern"))
        if "active" in q_lower:
            filters.append(Filter(field="status", operator="=", value="active"))
        if "it department" in q_lower or "department = it" in q_lower or "in it" in q_lower:
            filters.append(Filter(field="name", operator="=", value="IT"))
            if "departments" not in detected_tables:
                detected_tables.append("departments")
        comp_filters = SemanticQueryParser.extract_comparison_filters(query, group_by, detected_tables)
        for cf in comp_filters:
            if not any(f.field == cf.field and f.operator == cf.operator and f.value == cf.value for f in filters):
                filters.append(cf)

        # 8. Having Clause
        having = SemanticQueryParser.extract_having_conditions(query, metrics, group_by)

        # 9. Order By and Limit
        order_by = []
        limit_val = None
        limit_match = re.search(r"(?:top|first|last) (\d+)", q_lower)
        if limit_match:
            limit_val = int(limit_match.group(1))
        elif intent == IntentEnum.RANKING and not group_by and any(w in q_lower for w in ["highest", "lowest", "top", "best", "worst"]):
            limit_val = 1
            
        if time_granularity is not None or intent == IntentEnum.TREND_ANALYSIS:
            sort_field = time_granularity if time_granularity else (group_by[0] if group_by else "id")
            order_by.append(OrderCondition(field=sort_field, direction="asc"))
        elif "highest" in q_lower or "top" in q_lower or "desc" in q_lower or "newest" in q_lower:
            sort_field = metrics[0].alias if metrics else "salary"
            order_by.append(OrderCondition(field=sort_field, direction="desc"))
        elif "lowest" in q_lower or "bottom" in q_lower or "asc" in q_lower or "oldest" in q_lower:
            sort_field = metrics[0].alias if metrics else "salary"
            order_by.append(OrderCondition(field=sort_field, direction="asc"))

        win_plan = None
        if intent == IntentEnum.RANKING:
            r_type = "top" if order_by and order_by[0].direction == "desc" else "bottom"
            win_plan = WindowPlan(
                requires_window=True,
                function="RANK" if "rank" in q_lower else "ROW_NUMBER",
                partition_by=group_by if group_by else None,
                order_by=order_by if order_by else None,
                alias="rank_num",
                ranking_type=r_type
            )

        return ExecutionPlan(
            intent=intent,
            tables=detected_tables,
            metrics=metrics if metrics else None,
            filters=filters if filters else None,
            group_by=group_by if group_by else None,
            time_granularity=time_granularity,
            having=having if having else None,
            order_by=order_by if order_by else None,
            limit=limit_val,
            scope="global" if intent == IntentEnum.RANKING and not group_by else ("per_group" if group_by else None),
            ranking_type="top" if intent == IntentEnum.RANKING and order_by and order_by[0].direction == "desc" else ("bottom" if intent == IntentEnum.RANKING else None),
            rank=limit_val if intent == IntentEnum.RANKING else None,
            order=order_by[0].direction if order_by else None,
            requires_window_function=(intent == IntentEnum.RANKING),
            window_plan=win_plan,
            confidence=0.95
        )

