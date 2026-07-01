import re
from datetime import date, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import deque
import logging

from app.models import Base
from app.ai.planner.planner_schema import Filter, ExecutionPlan

logger = logging.getLogger(__name__)


class TimeReasoningUtils:
    """Provides deterministic conversion of natural language date expressions into structured Filter objects."""

    @staticmethod
    def parse_time_phrase(phrase: str, target_field: str = "date", ref_date: Optional[date] = None) -> List[Filter]:
        if ref_date is None:
            ref_date = date.today()

        p = phrase.lower().strip()
        year = ref_date.year
        month = ref_date.month
        day = ref_date.day

        # Today
        if "today" in p:
            return [Filter(field=target_field, operator="=", value=ref_date.isoformat(), time_reasoning="Today")]
        
        # Yesterday
        if "yesterday" in p:
            yest = ref_date - timedelta(days=1)
            return [Filter(field=target_field, operator="=", value=yest.isoformat(), time_reasoning="Yesterday")]

        # This Week (Monday to Sunday)
        if "this week" in p:
            start_week = ref_date - timedelta(days=ref_date.weekday())
            end_week = start_week + timedelta(days=6)
            return [Filter(field=target_field, operator="between", value=[start_week.isoformat(), end_week.isoformat()], time_reasoning="This Week")]

        # Last Week
        if "last week" in p:
            start_last_week = ref_date - timedelta(days=ref_date.weekday() + 7)
            end_last_week = start_last_week + timedelta(days=6)
            return [Filter(field=target_field, operator="between", value=[start_last_week.isoformat(), end_last_week.isoformat()], time_reasoning="Last Week")]

        # This Month
        if "this month" in p:
            start_month = date(year, month, 1)
            if month == 12:
                end_month = date(year, 12, 31)
            else:
                end_month = date(year, month + 1, 1) - timedelta(days=1)
            return [Filter(field=target_field, operator="between", value=[start_month.isoformat(), end_month.isoformat()], time_reasoning="This Month")]

        # Last Month
        if "last month" in p:
            if month == 1:
                start_month = date(year - 1, 12, 1)
                end_month = date(year - 1, 12, 31)
            else:
                start_month = date(year, month - 1, 1)
                end_month = date(year, month, 1) - timedelta(days=1)
            return [Filter(field=target_field, operator="between", value=[start_month.isoformat(), end_month.isoformat()], time_reasoning="Last Month")]

        # This Quarter
        if "this quarter" in p:
            q_idx = (month - 1) // 3
            start_m = q_idx * 3 + 1
            start_q = date(year, start_m, 1)
            if start_m == 10:
                end_q = date(year, 12, 31)
            else:
                end_q = date(year, start_m + 3, 1) - timedelta(days=1)
            return [Filter(field=target_field, operator="between", value=[start_q.isoformat(), end_q.isoformat()], time_reasoning="This Quarter")]

        # Last Quarter
        if "last quarter" in p:
            q_idx = (month - 1) // 3
            if q_idx == 0:
                start_q = date(year - 1, 10, 1)
                end_q = date(year - 1, 12, 31)
            else:
                start_m = (q_idx - 1) * 3 + 1
                start_q = date(year, start_m, 1)
                end_q = date(year, start_m + 3, 1) - timedelta(days=1)
            return [Filter(field=target_field, operator="between", value=[start_q.isoformat(), end_q.isoformat()], time_reasoning="Last Quarter")]

        # This Year
        if "this year" in p:
            return [Filter(field=target_field, operator="between", value=[f"{year}-01-01", f"{year}-12-31"], time_reasoning="This Year")]

        # Last Year
        if "last year" in p:
            return [Filter(field=target_field, operator="between", value=[f"{year - 1}-01-01", f"{year - 1}-12-31"], time_reasoning="Last Year")]

        # Last 3 Years
        if "last 3 years" in p or "last three years" in p or "last 3 financial years" in p:
            return [Filter(field=target_field, operator="between", value=[f"{year - 3}-01-01", f"{year}-12-31"], time_reasoning="Last 3 Years")]

        # Between January and June
        if "between january and june" in p:
            return [Filter(field=target_field, operator="between", value=[f"{year}-01-01", f"{year}-06-30"], time_reasoning="Between January and June")]

        # Before COVID
        if "before covid" in p:
            return [Filter(field=target_field, operator="<", value="2020-03-01", time_reasoning="Before COVID")]

        # After COVID
        if "after covid" in p:
            return [Filter(field=target_field, operator=">", value="2020-01-01", time_reasoning="After COVID")]

        # After Promotion
        if "after promotion" in p:
            return [Filter(field=target_field, operator=">=", value="2023-01-01", time_reasoning="After Promotion (Standard cutoff)")]

        # Current Financial Year (Apr 1 to Mar 31)
        if "current financial year" in p or "this financial year" in p:
            if month >= 4:
                fy_start = f"{year}-04-01"
                fy_end = f"{year + 1}-03-31"
            else:
                fy_start = f"{year - 1}-04-01"
                fy_end = f"{year}-03-31"
            return [Filter(field=target_field, operator="between", value=[fy_start, fy_end], time_reasoning="Current Financial Year")]

        # Previous Financial Year
        if "previous financial year" in p or "last financial year" in p:
            if month >= 4:
                fy_start = f"{year - 1}-04-01"
                fy_end = f"{year}-03-31"
            else:
                fy_start = f"{year - 2}-04-01"
                fy_end = f"{year - 1}-03-31"
            return [Filter(field=target_field, operator="between", value=[fy_start, fy_end], time_reasoning="Previous Financial Year")]

        # Generic Year extraction like "after 2021" or "in 2022"
        after_year_match = re.search(r"(?:after|since)\s+(\d{4})", p)
        if after_year_match:
            y = after_year_match.group(1)
            return [Filter(field=target_field, operator=">", value=f"{y}-12-31", time_reasoning=f"After {y}")]

        before_year_match = re.search(r"(?:before|prior to)\s+(\d{4})", p)
        if before_year_match:
            y = before_year_match.group(1)
            return [Filter(field=target_field, operator="<", value=f"{y}-01-01", time_reasoning=f"Before {y}")]

        in_year_match = re.search(r"(?:in|during)\s+(\d{4})", p)
        if in_year_match:
            y = in_year_match.group(1)
            return [Filter(field=target_field, operator="between", value=[f"{y}-01-01", f"{y}-12-31"], time_reasoning=f"Year {y}")]

        return []


class JoinDetectionUtils:
    """Automatically determines required joins and relationships by inspecting SQLAlchemy schema metadata."""

    @classmethod
    def get_schema_graph(cls) -> Dict[str, Set[str]]:
        graph: Dict[str, Set[str]] = {}
        for table_name, table in Base.metadata.tables.items():
            if table_name not in graph:
                graph[table_name] = set()
            for fk in table.foreign_keys:
                parent_table = fk.column.table.name
                if parent_table not in graph:
                    graph[parent_table] = set()
                graph[table_name].add(parent_table)
                graph[parent_table].add(table_name)
        return graph

    @classmethod
    def detect_join_paths(cls, tables: List[str]) -> List[str]:
        if not tables or len(tables) <= 1:
            return []

        graph = cls.get_schema_graph()
        valid_tables = [t.lower() for t in tables if t.lower() in graph]
        if len(valid_tables) <= 1:
            return []

        # Find shortest connecting path using BFS across all requested tables
        # Start from the first table and iteratively connect remaining tables
        connected = [valid_tables[0]]
        remaining = set(valid_tables[1:])
        all_paths = []

        while remaining:
            best_path: Optional[List[str]] = None
            for start_node in connected:
                for target_node in remaining:
                    path = cls._bfs_shortest_path(graph, start_node, target_node)
                    if path and (best_path is None or len(path) < len(best_path)):
                        best_path = path

            if not best_path:
                # Disconnected component in schema or unknown table
                logger.warning(f"Could not find join path connecting {connected} to {remaining}")
                break

            # Add discovered path
            path_str = " -> ".join(best_path)
            if path_str not in all_paths and len(best_path) > 1:
                all_paths.append(path_str)

            for node in best_path:
                if node in remaining:
                    remaining.remove(node)
                if node not in connected:
                    connected.append(node)

        return all_paths

    @staticmethod
    def _bfs_shortest_path(graph: Dict[str, Set[str]], start: str, end: str) -> Optional[List[str]]:
        if start == end:
            return [start]
        visited = {start}
        queue = deque([[start]])
        while queue:
            path = queue.popleft()
            curr = path[-1]
            for neighbor in graph.get(curr, []):
                if neighbor == end:
                    return path + [end]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        return None


class BusinessRuleUtils:
    """Interprets business domain phrases into explicit query rules and annotations."""

    @staticmethod
    def interpret_rules(query: str) -> List[str]:
        q = query.lower()
        rules = []

        if "above average" in q:
            rules.append("Interpreted 'Above Average' as filtering/having where metric > AVG(metric)")
        if "below average" in q:
            rules.append("Interpreted 'Below Average' as filtering/having where metric < AVG(metric)")
        if "highest growth" in q or "growth rate" in q or "fastest growing" in q:
            rules.append("Interpreted 'Growth Rate/Highest Growth' as calculating percentage change (Current - Previous) / Previous * 100 sorted descending")
        if "lowest growth" in q:
            rules.append("Interpreted 'Lowest Growth' as calculating percentage change sorted ascending")
        if "year over year" in q or "yoy" in q or "compared to last year" in q or "compared to previous year" in q:
            rules.append("Interpreted 'Year over Year / Compared to Last Year' as grouping by year and analyzing consecutive period variation")
        if "month over month" in q or "mom" in q:
            rules.append("Interpreted 'Month over Month' as grouping by month and calculating growth rate across consecutive months")
        if "percentage increase" in q or "percentage decrease" in q:
            rules.append("Interpreted 'Percentage Increase/Decrease' as (New Value - Old Value) / Old Value * 100")
        if "excluding interns" in q:
            rules.append("Interpreted 'excluding interns' as filtering out designation/role = 'Intern'")
        
        return rules


class QueryDecompositionUtils:
    """Breaks complex queries into structured step-by-step task execution chains."""

    @staticmethod
    def decompose(plan: ExecutionPlan) -> List[str]:
        tasks = []
        step_num = 1

        # Task 1: Filters
        if plan.filters:
            f_strs = [f"{f.field} {f.operator} {f.value}" for f in plan.filters]
            tasks.append(f"Task {step_num}: Filter rows where " + " and ".join(f_strs))
            step_num += 1

        # Task 2: Joins
        if plan.relationships or (plan.tables and len(plan.tables) > 1):
            rel_str = ", ".join(plan.relationships) if plan.relationships else " -> ".join(plan.tables)
            tasks.append(f"Task {step_num}: Join required entities across [{rel_str}]")
            step_num += 1

        # Task 3: Metrics & Aggregations
        if plan.metrics:
            m_strs = [f"{m.operation.upper()}({m.field})" + (f" AS {m.alias}" if m.alias else "") for m in plan.metrics]
            tasks.append(f"Task {step_num}: Calculate aggregated metrics: " + ", ".join(m_strs))
            step_num += 1

        # Task 4: Group By
        if plan.group_by:
            tasks.append(f"Task {step_num}: Group results by [{', '.join(plan.group_by)}]")
            step_num += 1

        # Task 5: Having Clause
        if plan.having:
            h_strs = [f"{h.metric} {h.operator} {h.value}" for h in plan.having]
            tasks.append(f"Task {step_num}: Filter grouped aggregations where " + " and ".join(h_strs))
            step_num += 1

        # Task 6: Sorting & Limit
        sort_limit_parts = []
        if plan.order_by:
            o_strs = [f"{o.field} {o.direction.upper()}" for o in plan.order_by]
            sort_limit_parts.append(f"Sort by {', '.join(o_strs)}")
        if plan.limit:
            sort_limit_parts.append(f"Limit results to top {plan.limit} rows")
        if sort_limit_parts:
            tasks.append(f"Task {step_num}: " + "; ".join(sort_limit_parts))

        if not tasks:
            tasks.append("Task 1: Retrieve requested columns from primary entity")

        return tasks
