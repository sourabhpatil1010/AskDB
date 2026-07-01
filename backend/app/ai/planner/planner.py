import re
import logging
from typing import List, Optional

from app.models import Base
from app.ai.planner.planner_schema import (
    ExecutionPlan, IntentEnum, Metric, Filter, HavingCondition, OrderCondition, PlannerClarificationException
)
from app.ai.planner.planner_chain import PlannerChain
from app.ai.planner.planner_validator import PlannerValidator
from app.ai.planner.planner_utils import TimeReasoningUtils, JoinDetectionUtils, BusinessRuleUtils, QueryDecompositionUtils

logger = logging.getLogger(__name__)


class AIQueryPlanner:
    """High-level AI Query Planner layer sitting before JSON Generation."""

    def __init__(self):
        self.chain = PlannerChain()
        self.validator = PlannerValidator()
        self.known_tables = list(Base.metadata.tables.keys())

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
        
        # 1. Detect ambiguity or low confidence queries
        vague_phrases = ["vague", "unclear", "stuff", "what about", "tell me about", "just salary", "compare growth", "general info"]
        if any(vp in q_lower for vp in vague_phrases) or (len(q_lower.split()) <= 2 and "all" not in q_lower and "*" not in q_lower):
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

        # 2. Intent Detection
        intent = IntentEnum.FILTERING
        if any(w in q_lower for w in ["compare", "versus", "vs", "difference between"]):
            intent = IntentEnum.COMPARISON
        elif any(w in q_lower for w in ["top", "highest", "lowest", "rank", "best", "worst"]):
            intent = IntentEnum.RANKING
        elif any(w in q_lower for w in ["growth", "trend", "yoy", "mom", "year over year", "over time"]):
            intent = IntentEnum.TREND_ANALYSIS
        elif any(w in q_lower for w in ["average", "sum", "total", "count", "how many", "max", "min"]):
            intent = IntentEnum.AGGREGATION

        # 3. Table Detection
        detected_tables = []
        table_keywords = {
            "employees": ["employ", "staff", "worker", "hire", "intern", "designation", "manager"],
            "departments": ["department", "dept", "team"],
            "payroll": ["salary", "pay", "bonus", "compensation", "payroll", "wage"],
            "attendance": ["attend", "hours", "present", "absent"],
            "projects": ["project", "initiative"],
            "clients": ["client", "customer"],
            "offices": ["office", "location", "city", "country"],
            "performance_reviews": ["review", "performance", "score", "rating"],
            "leave_requests": ["leave", "vacation", "sick", "time off"],
            "skills": ["skill", "proficiency"]
        }
        for t_name, keywords in table_keywords.items():
            if any(kw in q_lower for kw in keywords):
                detected_tables.append(t_name)
        if not detected_tables:
            detected_tables = ["employees"]
        
        # Ensure join continuity if both department and payroll exist
        if "departments" in detected_tables and "payroll" in detected_tables and "employees" not in detected_tables:
            detected_tables.insert(1, "employees")

        # 4. Metric Extraction
        metrics = []
        if "avg" in q_lower or "average" in q_lower:
            if any(w in q_lower for w in ["salary", "pay", "payroll", "compensation"]):
                metrics.append(Metric(field="salary", operation="avg", alias="avg_salary"))
            elif "attendance" in q_lower or "hours" in q_lower:
                metrics.append(Metric(field="hours_worked", operation="avg", alias="avg_hours"))
            elif "budget" in q_lower:
                metrics.append(Metric(field="budget", operation="avg", alias="avg_budget"))
            else:
                metrics.append(Metric(field="salary", operation="avg", alias="avg_val"))
        elif "sum" in q_lower or "total" in q_lower:
            if any(w in q_lower for w in ["salary", "pay", "payroll"]):
                metrics.append(Metric(field="salary", operation="sum", alias="total_payroll"))
            elif "budget" in q_lower:
                metrics.append(Metric(field="budget", operation="sum", alias="total_budget"))
            elif "hours" in q_lower:
                metrics.append(Metric(field="hours_worked", operation="sum", alias="total_hours"))
            else:
                metrics.append(Metric(field="salary", operation="sum", alias="total_val"))
        elif "count" in q_lower or "number of" in q_lower or "how many" in q_lower or "more than" in q_lower:
            metrics.append(Metric(field="id", operation="count", alias="count"))
        elif "max" in q_lower or "maximum" in q_lower or "highest" in q_lower:
            field_name = "bonus" if "bonus" in q_lower else ("budget" if "budget" in q_lower else "salary")
            metrics.append(Metric(field=field_name, operation="max", alias=f"max_{field_name}"))
        elif "min" in q_lower or "minimum" in q_lower or "lowest" in q_lower:
            field_name = "budget" if "budget" in q_lower else "salary"
            metrics.append(Metric(field=field_name, operation="min", alias=f"min_{field_name}"))
        
        if not metrics and intent in [IntentEnum.AGGREGATION, IntentEnum.COMPARISON, IntentEnum.RANKING]:
            metrics.append(Metric(field="id", operation="count", alias="count"))

        # 5. Group By Detection & Time Granularity
        group_by = []
        time_granularity = None
        if "by department" in q_lower or "across department" in q_lower or "department" in q_lower:
            if "departments" in detected_tables or "department" in q_lower:
                group_by.append("department")
        elif "by project" in q_lower or "across project" in q_lower:
            group_by.append("project")
        elif "by month" in q_lower or "monthly" in q_lower or "month over month" in q_lower or "mom" in q_lower:
            group_by.append("month")
            time_granularity = "month"
        elif "by quarter" in q_lower or "quarterly" in q_lower or "by quarter" in q_lower:
            group_by.append("quarter")
            time_granularity = "quarter"
        elif "by week" in q_lower or "weekly" in q_lower or "week over week" in q_lower:
            group_by.append("week")
            time_granularity = "week"
        elif "by year" in q_lower or "yoy" in q_lower or "year over year" in q_lower or "annual" in q_lower:
            group_by.append("year")
            time_granularity = "year"
        elif "by day" in q_lower or "daily" in q_lower:
            group_by.append("day")
            time_granularity = "day"
        elif "by manager" in q_lower:
            group_by.append("manager")
        elif "by office" in q_lower or "by location" in q_lower:
            group_by.append("office")

        # 6. Filter Extraction
        filters = TimeReasoningUtils.parse_time_phrase(query)
        if "excluding intern" in q_lower or "exclude intern" in q_lower:
            filters.append(Filter(field="designation", operator="!=", value="Intern"))
        if "active" in q_lower:
            filters.append(Filter(field="status", operator="=", value="active"))
        if "it department" in q_lower or "department = it" in q_lower or "in it" in q_lower:
            filters.append(Filter(field="name", operator="=", value="IT"))
        
        # 7. Having Clause
        having = []
        having_match = re.search(r"more than (\d+) employ", q_lower)
        if having_match:
            having.append(HavingCondition(metric="count", operator=">", value=int(having_match.group(1))))
        having_sal = re.search(r"(?:above|greater than) (\d+0+)", q_lower)
        if having_sal and "average salary" in q_lower:
            having.append(HavingCondition(metric="avg_salary", operator=">", value=float(having_sal.group(1))))

        # 8. Order By and Limit
        order_by = []
        limit_val = None
        limit_match = re.search(r"(?:top|first|last) (\d+)", q_lower)
        if limit_match:
            limit_val = int(limit_match.group(1))
            
        if "highest" in q_lower or "top" in q_lower or "desc" in q_lower or "newest" in q_lower:
            sort_field = metrics[0].alias if metrics else "salary"
            order_by.append(OrderCondition(field=sort_field, direction="desc"))
        elif "lowest" in q_lower or "bottom" in q_lower or "asc" in q_lower or "oldest" in q_lower:
            sort_field = metrics[0].alias if metrics else "salary"
            order_by.append(OrderCondition(field=sort_field, direction="asc"))

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
            confidence=0.95
        )

