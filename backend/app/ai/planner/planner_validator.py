import logging
from typing import List, Set, Dict

from app.models import Base
from app.ai.planner.planner_schema import ExecutionPlan, PlannerClarificationException
from app.ai.planner.planner_utils import JoinDetectionUtils, QueryDecompositionUtils, BusinessRuleUtils, TimeReasoningUtils, TimeSemanticUtils, SubquerySemanticUtils, SYSTEM_TABLES, SchemaColumnResolver

logger = logging.getLogger(__name__)


class PlannerValidator:
    """Validates ExecutionPlan against database schema and enforces confidence thresholds."""

    def __init__(self):
        self.valid_tables: Set[str] = {t for t in Base.metadata.tables.keys() if t not in SYSTEM_TABLES}
        self.table_columns: Dict[str, Set[str]] = {
            t_name: set(col.name for col in table.columns)
            for t_name, table in Base.metadata.tables.items()
            if t_name not in SYSTEM_TABLES
        }

    def validate_and_enrich(self, plan: ExecutionPlan, original_query: str) -> ExecutionPlan:
        """Validates schema references, enriches join paths/decomposition/rules, and checks confidence."""
        logger.info(f"Validating Execution Plan (Initial Confidence: {plan.confidence:.2f})")

        # 1. Check Confidence Threshold First
        if plan.confidence < 0.70:
            questions = plan.clarification_questions or self._generate_fallback_questions(original_query, plan)
            logger.warning(f"Planner confidence {plan.confidence:.2f} < 0.70. Raising clarification exception.")
            raise PlannerClarificationException(questions=questions, confidence=plan.confidence)

        # 2. Validate and clean Table names
        cleaned_tables = []
        for t in plan.tables:
            t_lower = t.lower().strip()
            if t_lower in self.valid_tables:
                cleaned_tables.append(t_lower)
            else:
                # Try singular/plural heuristics or log warning
                if t_lower + "s" in self.valid_tables:
                    cleaned_tables.append(t_lower + "s")
                elif t_lower.endswith("s") and t_lower[:-1] in self.valid_tables:
                    cleaned_tables.append(t_lower[:-1])
                else:
                    logger.warning(f"Table '{t}' not found in database schema metadata.")
                    # Keep it if LLM hallucinated, or let downstream catch/clarify
                    cleaned_tables.append(t_lower)
        
        if cleaned_tables:
            plan.tables = list(dict.fromkeys(cleaned_tables))

        # 3. Enrich Joins and Relationships if multiple tables are present
        if len(plan.tables) > 1 and not plan.relationships:
            detected_paths = JoinDetectionUtils.detect_join_paths(plan.tables)
            if detected_paths:
                plan.relationships = detected_paths
                logger.debug(f"Automatically enriched relationships: {plan.relationships}")

        # 4. Enrich Time Reasoning Filters
        primary_table = plan.tables[0] if plan.tables else None
        time_filters = TimeReasoningUtils.parse_time_phrase(original_query, table_name=primary_table)
        if time_filters:
            existing_filters = plan.filters or []
            # Merge without duplicates
            existing_fields = {f.field for f in existing_filters}
            for tf in time_filters:
                if tf.field not in existing_fields:
                    existing_filters.append(tf)
            plan.filters = existing_filters

        if not plan.time_plan:
            plan.time_plan = TimeSemanticUtils.analyze(original_query, plan.tables)

        if not getattr(plan, "subquery_plan", None):
            subq_plan = SubquerySemanticUtils.analyze(original_query, plan.tables)
            if subq_plan:
                plan.subquery_plan = subq_plan
                if subq_plan.target_table and subq_plan.target_table not in plan.tables and subq_plan.target_table in self.valid_tables:
                    plan.tables.append(subq_plan.target_table)

        # 5. Enrich Business Rules
        rules = BusinessRuleUtils.interpret_rules(original_query)
        if rules:
            existing_rules = set(plan.business_rules_applied or [])
            for r in rules:
                existing_rules.add(r)
            plan.business_rules_applied = list(existing_rules)

        # 6. Enrich Query Decomposition if empty
        if not plan.decomposition:
            plan.decomposition = QueryDecompositionUtils.decompose(plan)
            logger.debug(f"Automatically generated query decomposition: {plan.decomposition}")

        # 6.5. Enrich partition_by if scope is per_group or requires_partition_ranking
        if plan.scope == "per_group" or plan.requires_partition_ranking:
            if not plan.partition_by and plan.group:
                plan.partition_by = [plan.group]
            elif not plan.partition_by and plan.group_by:
                plan.partition_by = list(plan.group_by)
            if plan.partition_by:
                from app.ai.planner.planner_utils import SchemaGroupingResolver
                for p in plan.partition_by:
                    col_expr = SchemaGroupingResolver.resolve_grouping_column(p, self.valid_tables)
                    if col_expr and "." in col_expr:
                        tbl = col_expr.split(".")[0]
                        if tbl in self.valid_tables and tbl not in plan.tables:
                            plan.tables.append(tbl)

        # 6.6 Ensure domain tables required by filters and order_by are present in plan.tables
        all_fields = []
        if plan.filters:
            for f in plan.filters:
                all_fields.append(f.field)
        if plan.order_by:
            for o in plan.order_by:
                all_fields.append(o.field)
        for field in all_fields:
            owner = SchemaColumnResolver.resolve_column_owner(field, plan.tables)
            if owner and owner not in plan.tables and owner in self.valid_tables:
                plan.tables.append(owner)

        # 7. Check for Unsupported SQL Capabilities AFTER generating and enriching ExecutionPlan
        self._check_unsupported_capabilities(plan, original_query)

        return plan

    def _generate_fallback_questions(self, query: str, plan: ExecutionPlan) -> List[str]:
        """Generates contextual clarification questions when LLM confidence is low or query is ambiguous."""
        q_lower = query.lower()
        questions = []

        if "salary" in q_lower or "pay" in q_lower or "compensation" in q_lower:
            questions.append("Did you mean Average Salary, Total Payroll Salary, or Maximum/Minimum Salary?")
        if "attendance" in q_lower or "hours" in q_lower:
            questions.append("Are you asking for Total Hours Worked, Average Daily Hours, or Employee Count present?")
        if "growth" in q_lower or "increase" in q_lower:
            questions.append("Would you like Year-over-Year percentage growth, Month-over-Month growth, or absolute difference?")
        if "top" in q_lower or "highest" in q_lower or "best" in q_lower:
            questions.append("By which specific metric should we rank (e.g. Salary, Budget, Headcount, or Hours)?")
        
        if not questions:
            questions.append(f"Could you please clarify your exact filtering or grouping requirements for: '{query}'?")
            questions.append("Please specify which tables or date ranges you would like to investigate.")
            
        return questions

    def _check_unsupported_capabilities(self, plan: ExecutionPlan, query: str):
        """Detects unsupported SQL patterns (e.g. Recursive Queries, Unions, Moving Averages), failing gracefully."""
        q_lower = query.lower()
        unsupported_terms = [
            "recursive", "hierarchy tree", "org chart hierarchy",
            "chain of command", "union of", "intersect with", "except for"
        ]
        for term in unsupported_terms:
            if term in q_lower:
                raise PlannerClarificationException(
                    questions=[f"The query '{query}' involves '{term}', which requires advanced SQL capabilities (such as Recursive CTEs or Union) not currently supported."],
                    confidence=0.0
                )

