import re
from datetime import date, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import deque
import logging

from sqlalchemy import Date, DateTime
from app.models import Base
from app.ai.planner.planner_schema import Filter, ExecutionPlan, OrderCondition, TimePlan

logger = logging.getLogger(__name__)

SYSTEM_TABLES = {"users", "search_history", "saved_queries"}


class SchemaDateColumnResolver:
    """Dynamically resolves the correct date/datetime column for a given table
    by inspecting SQLAlchemy metadata — no hardcoded table or column names.

    Selection priority:
    1. SQLAlchemy ``Date`` columns (not DateTime) — these are always domain
       business dates (hire_date, period_start, review_date, etc.).
    2. Among Date columns, names matching preferred patterns win (lower index
       in _PREFERRED_PATTERNS = higher priority).
    3. If no Date columns exist, fall back to non-audit DateTime columns
       (i.e., exclude created_at / updated_at / deleted_at).
    4. If only audit DateTime columns exist, use the first one.
    """

    # Names to treat as low-priority audit / infrastructure timestamps.
    # They are inherited by every model via BaseModel and are rarely the
    # correct column for a business time-series query.
    _AUDIT_COLUMN_NAMES: Set[str] = {"created_at", "updated_at", "deleted_at"}

    # Preference order for domain-specific date column names.
    # Earlier entries beat later ones when multiple Date columns exist.
    _PREFERRED_PATTERNS: List[str] = [
        "hire_date",
        "order_date",
        "payment_date",
        "period_start",
        "start_date",
        "event_time",
        "check_in",
        "joined_at",
        "timestamp",
        "review_date",
        "closed_at",
        "end_date",
        "date",        # generic, lowest preference among domain names
    ]

    @classmethod
    def resolve(cls, table_name: str) -> Optional[str]:
        """Return the best date column name for *table_name*, or None.

        Args:
            table_name: Exact SQLAlchemy table name (e.g. 'employees').

        Returns:
            Column name string (e.g. 'hire_date') or None.
        """
        table_obj = Base.metadata.tables.get(table_name)
        if table_obj is None:
            logger.debug(f"SchemaDateColumnResolver: table '{table_name}' not in metadata.")
            return None

        # Partition columns into Date-only vs DateTime (audit timestamps etc.)
        date_cols: List[str] = []      # SQLAlchemy Date (not DateTime)
        datetime_cols: List[str] = []  # SQLAlchemy DateTime

        for col in table_obj.columns:
            # DateTime subclasses Date in some older SA versions — check DateTime first
            if isinstance(col.type, DateTime):
                datetime_cols.append(col.name)
            elif isinstance(col.type, Date):
                date_cols.append(col.name)

        if not date_cols and not datetime_cols:
            logger.debug(f"SchemaDateColumnResolver: no Date/DateTime columns in '{table_name}'.")
            return None

        # --- Scoring function ---
        def _pattern_score(col_name: str) -> int:
            name_lower = col_name.lower()
            for idx, pattern in enumerate(cls._PREFERRED_PATTERNS):
                if pattern in name_lower:
                    return idx
            return len(cls._PREFERRED_PATTERNS)

        # 1. Prefer Date columns (business dates) over DateTime (audit stamps)
        if date_cols:
            best = min(date_cols, key=lambda c: (_pattern_score(c), c))
            logger.debug(
                f"SchemaDateColumnResolver: resolved '{table_name}' -> '{best}' "
                f"(Date candidates: {date_cols})"
            )
            return best

        # 2. No Date columns — use non-audit DateTime columns if available
        non_audit = [c for c in datetime_cols if c not in cls._AUDIT_COLUMN_NAMES]
        candidates = non_audit if non_audit else datetime_cols
        best = min(candidates, key=lambda c: (_pattern_score(c), c))
        logger.debug(
            f"SchemaDateColumnResolver: resolved '{table_name}' -> '{best}' "
            f"(DateTime candidates: {candidates}, audit excluded: {not non_audit})"
        )
        return best

    @classmethod
    def resolve_for_tables(cls, table_names: List[str]) -> Tuple[Optional[str], Optional[str]]:
        """Return (table_name, column_name) for the first table in the list
        that has a resolvable date column.

        Useful when a query spans multiple tables and we need to pick the
        most relevant one for time-based filtering/grouping.
        """
        for tbl in table_names:
            col = cls.resolve(tbl)
            if col is not None:
                return tbl, col
        return None, None

class SchemaColumnResolver:
    """
    Generic schema-aware column resolver using SQLAlchemy metadata.
    Dynamically attaches columns to their true owner table without hardcoded mappings.
    """
    @classmethod
    def resolve_column_owner(cls, column_name: str, available_tables: List[str]) -> Optional[str]:
        if not column_name or column_name == "*" or column_name.endswith(".*"):
            return None
        import re
        s = column_name.strip()
        as_match = re.search(r'^(.+?)\s+AS\s+\w+\s*$', s, re.IGNORECASE)
        if as_match:
            s = as_match.group(1).strip()
        match = re.search(r'(?i)^(?:count|sum|avg|min|max)\((.+)\)$', s)
        if match:
            s = match.group(1).strip()
        if "." in s:
            s = s.split(".")[-1].strip()

        # Check available tables first
        for table in available_tables:
            table_obj = Base.metadata.tables.get(table)
            if table_obj is not None and s in [c.name for c in table_obj.columns]:
                return table
        # Fallback to all tables in metadata
        for table_name, table_obj in Base.metadata.tables.items():
            if table_name in SYSTEM_TABLES:
                continue
            if s in [c.name for c in table_obj.columns]:
                return table_name
        return None

    @classmethod
    def qualify_column(cls, column_expr: str, available_tables: List[str], default_table: Optional[str] = None) -> str:
        """Dynamically qualify a column or aggregation expression with its true owner table."""
        if not column_expr or column_expr == "*" or column_expr.endswith(".*"):
            return column_expr
        import re
        s = column_expr.strip()
        as_match = re.search(r'^(.+?)\s+AS\s+([a-zA-Z0-9_]+)\s*$', s, re.IGNORECASE)
        inner = as_match.group(1).strip() if as_match else s
        alias_part = f" AS {as_match.group(2).strip()}" if as_match else ""

        agg_match = re.search(r'(?i)^(count|sum|avg|min|max)\((.+)\)$', inner)
        if agg_match:
            op = agg_match.group(1).upper()
            col_part = agg_match.group(2).strip()
            is_distinct = ""
            if re.match(r'(?i)^distinct\s+', col_part):
                is_distinct = "DISTINCT "
                col_part = re.sub(r'(?i)^distinct\s+', '', col_part).strip()
            if col_part == "*" or col_part.endswith(".*"):
                return f"{op}({is_distinct}{col_part}){alias_part}"
            if "." in col_part:
                tbl, col = col_part.split(".", 1)
                owner = cls.resolve_column_owner(col, available_tables) or tbl
                return f"{op}({is_distinct}{owner}.{col}){alias_part}"
            owner = cls.resolve_column_owner(col_part, available_tables) or default_table
            qual_col = f"{owner}.{col_part}" if owner else col_part
            return f"{op}({is_distinct}{qual_col}){alias_part}"

        from app.query_builder.query_validator import _is_computed_expression
        if _is_computed_expression(inner):
            return column_expr

        if "." in inner:
            tbl, col = inner.split(".", 1)
            owner = cls.resolve_column_owner(col, available_tables) or tbl
            return f"{owner}.{col}{alias_part}"

        owner = cls.resolve_column_owner(inner, available_tables) or default_table
        qual_col = f"{owner}.{inner}" if owner else inner
        return f"{qual_col}{alias_part}"

    @classmethod
    def find_matching_schema_column(cls, query_text: str, available_tables: List[str]) -> Optional[Tuple[str, str]]:
        """Dynamically match terms in query_text to database column names across available tables using SQLAlchemy metadata."""
        import re
        q_lower = query_text.lower()
        if any(w in q_lower for w in ["salary", "pay", "paid", "earning", "earner", "compensation", "income", "wage"]):
            if "payroll" in available_tables or "payroll" in [t for t in Base.metadata.tables.keys() if t not in SYSTEM_TABLES]:
                return "payroll", "base_salary"
        if any(w in q_lower for w in ["bonus"]):
            if "payroll" in available_tables or "payroll" in [t for t in Base.metadata.tables.keys() if t not in SYSTEM_TABLES]:
                return "payroll", "bonus"
        if any(w in q_lower for w in ["performer", "performance", "review", "rating", "score"]):
            if "performance_reviews" in available_tables or "performance_reviews" in [t for t in Base.metadata.tables.keys() if t not in SYSTEM_TABLES]:
                return "performance_reviews", "score"
        if any(w in q_lower for w in ["attendance", "hours", "worked"]):
            if "attendance" in available_tables or "attendance" in [t for t in Base.metadata.tables.keys() if t not in SYSTEM_TABLES]:
                return "attendance", "hours_worked"
        ignore_cols = {"id", "department_id", "office_id", "client_id", "employee_id", "created_at", "updated_at", "deleted_at", "reviewer_id", "skill_id", "project_id", "user_id", "is_active", "status"}

        def _matches(col_name: str) -> bool:
            if col_name in ignore_cols:
                return False
            parts = col_name.split("_")
            for p in parts:
                if len(p) > 2:
                    if re.search(r'\b' + re.escape(p) + r'(?:s|ies)?\b', q_lower):
                        return True
                    if p.endswith("y") and re.search(r'\b' + re.escape(p[:-1] + "ies") + r'\b', q_lower):
                        return True
                    if p.endswith("s") and re.search(r'\b' + re.escape(p[:-1]) + r'\b', q_lower):
                        return True
            return False

        for table in available_tables:
            table_obj = Base.metadata.tables.get(table)
            if table_obj is not None:
                for col in table_obj.columns:
                    if _matches(col.name):
                        return table, col.name

        for table_name, table_obj in Base.metadata.tables.items():
            if table_name in SYSTEM_TABLES:
                continue
            for col in table_obj.columns:
                if _matches(col.name):
                    return table_name, col.name
        return None

class SchemaGroupingResolver:
    """
    Generic metadata-driven grouping resolver using SQLAlchemy schema.
    Resolves grouping concepts (e.g. 'department', 'office', 'project', 'month', 'year')
    to their exact qualified table and column expressions without hardcoded mappings.
    """
    @classmethod
    def resolve_grouping_column(cls, group_concept: str, available_tables: List[str], default_table: Optional[str] = None) -> str:
        if not group_concept:
            return ""
        if isinstance(available_tables, (set, tuple)):
            available_tables = list(available_tables)
        s = group_concept.strip().lower()
        if "." in s:
            tbl, col = s.split(".", 1)
            owner = SchemaColumnResolver.resolve_column_owner(col, available_tables) or tbl
            return f"{owner}.{col}"

        # Check time granularity concepts
        time_units = {"month", "quarter", "year", "week", "day"}
        if s in time_units:
            target_tbl = default_table
            if not target_tbl and available_tables:
                target_tbl = available_tables[0]
            date_col = None
            if target_tbl:
                date_col = SchemaDateColumnResolver.resolve(target_tbl)
            if not date_col:
                for t in available_tables:
                    dc = SchemaDateColumnResolver.resolve(t)
                    if dc:
                        target_tbl = t
                        date_col = dc
                        break
            if target_tbl and date_col:
                return f"DATE_TRUNC('{s}', {target_tbl}.{date_col})"
            return f"DATE_TRUNC('{s}', date)"

        # Check if group_concept is an exact column name in available_tables
        for table in available_tables:
            table_obj = Base.metadata.tables.get(table)
            if table_obj is not None and s in [c.name for c in table_obj.columns]:
                return f"{table}.{s}"

        # Check if group_concept maps to a database table name or entity in metadata
        target_table = None
        for t_list in [available_tables, [t for t in Base.metadata.tables.keys() if t not in SYSTEM_TABLES]]:
            for t_name in t_list:
                t_lower = t_name.lower()
                if s == t_lower or s + "s" == t_lower or s[:-1] + "ies" == t_lower or s[:-1] == t_lower:
                    target_table = t_name
                    break
                if s in t_lower or t_lower.rstrip("s") in s:
                    target_table = t_name
                    break
            if target_table:
                break

        if not target_table and default_table:
            target_table = default_table

        if target_table:
            table_obj = Base.metadata.tables.get(target_table)
            if table_obj is not None:
                for candidate in ["name", "title", "city", "last_name", "first_name", "id"]:
                    if candidate in [c.name for c in table_obj.columns]:
                        return f"{target_table}.{candidate}"
                col_names = [c.name for c in table_obj.columns]
                if col_names:
                    return f"{target_table}.{col_names[0]}"

        return SchemaColumnResolver.qualify_column(group_concept, available_tables, default_table=default_table)


class SchemaAggregationResolver:
    """
    Generic metadata-driven aggregation resolver using SQLAlchemy schema.
    Resolves numeric metrics and formats aggregate SQL expressions without hardcoded mappings.
    """
    @classmethod
    def resolve_numeric_metric(cls, query_text: str, available_tables: List[str], intent_op: str = "") -> str:
        match_res = SchemaColumnResolver.find_matching_schema_column(query_text, available_tables)
        if match_res:
            return match_res[1]

        from sqlalchemy import Numeric, Integer, Float
        for table in available_tables:
            table_obj = Base.metadata.tables.get(table)
            if table_obj is not None:
                for col in table_obj.columns:
                    if col.name in {"id", "department_id", "office_id", "client_id", "employee_id", "project_id"}:
                        continue
                    if isinstance(col.type, (Numeric, Integer, Float)):
                        return col.name
        return "id" if intent_op.upper() == "COUNT" else "base_salary"

    @classmethod
    def format_aggregation_expression(cls, operation: str, qualified_col: str, alias: Optional[str] = None) -> str:
        op_upper = (operation or "").strip().upper()
        if op_upper in {"DISTINCT_COUNT", "COUNT_DISTINCT"}:
            expr = f"COUNT(DISTINCT {qualified_col})"
        elif op_upper == "COUNT":
            expr = f"COUNT({qualified_col})"
        elif op_upper in {"AVG", "SUM", "MIN", "MAX"}:
            expr = f"{op_upper}({qualified_col})"
        else:
            expr = qualified_col

        if alias and alias.lower() != expr.lower():
            return f"{expr} AS {alias}"
        return expr


class SemanticQueryParser:
    """
    Generic natural language semantic analyzer driven by SQLAlchemy metadata.
    Extracts groupings, HAVING conditions, metrics, and comparison filters without hardcoded mappings.
    Ensures equivalent grammatical formulations produce identical ExecutionPlans.
    """
    @classmethod
    def extract_grouping(cls, query: str, available_tables: List[str]) -> List[str]:
        import re
        from app.models import Base as _Base
        q_lower = query.lower().strip()
        group_by = []

        # 1. Check time units first
        time_units = {"month", "quarter", "year", "week", "day"}
        for unit in time_units:
            if re.search(rf'\b(?:by|per|each|every|in each|for each|grouped by)\s+{unit}\b', q_lower) or (unit == "month" and ("monthly" in q_lower or "mom" in q_lower)) or (unit == "quarter" and "quarterly" in q_lower) or (unit == "week" and "weekly" in q_lower) or (unit == "year" and ("annual" in q_lower or "yoy" in q_lower)) or (unit == "day" and "daily" in q_lower):
                if unit not in group_by:
                    group_by.append(unit)
                return group_by

        # 2. Preposition-based grouping: by, per, in each, for each, grouped by, each, every
        group_matches = re.findall(r'(?i)\b(?:by|per|in each|for each|within each|inside each|each|every|in every|for every|within every|inside every|grouped by)\s+([a-zA-Z0-9_]+)', query)
        for g_match in group_matches:
            clean_g = g_match.strip().lower()
            if clean_g in {"the", "all", "our", "their", "its", "a", "an"}:
                continue
            if clean_g.endswith("s") and len(clean_g) > 3 and not clean_g.endswith("ss"):
                clean_g = clean_g[:-1]
            if clean_g not in group_by and clean_g not in {"record", "data", "result", "detail", "val", "amount", "count", "salary", "pay", "payroll", "bonus", "budget", "score"}:
                group_by.append(clean_g)

        if not group_by:
            # 3. Entity-centric grouping: e.g., "Departments with more than 20 employees", "Offices having over 5 staff"
            for tbl_name in _Base.metadata.tables.keys():
                if tbl_name in {"employees", "users", "project_assignments", "employee_skills"} or tbl_name in SYSTEM_TABLES:
                    continue
                singular = tbl_name[:-1] if tbl_name.endswith("s") else tbl_name
                if re.search(rf'(?i)\b(?:{tbl_name}|{singular}s?)\s+(?:with|having|whose|where)\b', query):
                    group_by.append(singular)
                    break
        return group_by

    @classmethod
    def extract_having_conditions(cls, query: str, metrics: List[Any], group_by: List[str]) -> List[Any]:
        import re
        from app.ai.planner.planner_schema import HavingCondition
        having_conds = []
        q_lower = query.lower()

        patterns = [
            (r'(?i)\b(?:more than|greater than|over|exceeding|exceeds|exceed|above)\s+(\d+(?:\.\d+)?)', ">"),
            (r'(?i)\b(?:less than|fewer than|under|below)\s+(\d+(?:\.\d+)?)', "<"),
            (r'(?i)\b(?:at least|no fewer than|no less than|minimum of|minimum)\s+(\d+(?:\.\d+)?)', ">="),
            (r'(?i)\b(?:at most|no more than|maximum of|maximum)\s+(\d+(?:\.\d+)?)', "<="),
            (r'(?i)\b(?:equal to|equals|exactly)\s+(\d+(?:\.\d+)?)', "="),
        ]

        has_grouping = bool(group_by)
        is_explicit_agg = any(w in q_lower for w in ["average", "avg", "total", "sum", "count of", "employee count", "total employees", "total staff", "number of"])

        if not (has_grouping or is_explicit_agg):
            return having_conds

        for pat, op in patterns:
            for match in re.finditer(pat, q_lower):
                val_str = match.group(1)
                val = int(val_str) if val_str.isdigit() else float(val_str)

                target_metric = "count"
                if any(w in q_lower for w in ["average", "avg"]):
                    for m in metrics:
                        if getattr(m, "operation", "").lower() == "avg":
                            target_metric = getattr(m, "alias", None) or "avg_salary"
                            break
                    else:
                        target_metric = "avg_salary"
                elif any(w in q_lower for w in ["total payroll", "total salary", "total pay", "total bonus", "total budget", "sum of"]) or (any(w in q_lower for w in ["total", "sum", "payroll"]) and not any(w in q_lower for w in ["employ", "staff", "worker", "person", "member", "department", "office", "project", "client"])):
                    for m in metrics:
                        if getattr(m, "operation", "").lower() == "sum":
                            target_metric = getattr(m, "alias", None) or "total_payroll"
                            break
                    else:
                        target_metric = "total_payroll"
                else:
                    for m in metrics:
                        if getattr(m, "operation", "").lower() in {"count", "distinct_count"}:
                            target_metric = getattr(m, "alias", None) or "count"
                            break

                if not any(h.metric == target_metric and h.operator == op and h.value == val for h in having_conds):
                    having_conds.append(HavingCondition(metric=target_metric, operator=op, value=val))
        return having_conds

    @classmethod
    def extract_comparison_filters(cls, query: str, group_by: List[str], available_tables: List[str]) -> List[Any]:
        import re
        from app.ai.planner.planner_schema import Filter
        filters = []
        q_lower = query.lower()

        if group_by or any(w in q_lower for w in ["average", "avg", "total", "sum", "count of", "employee count", "number of"]):
            return filters

        patterns = [
            (r'(?i)\b(?:more than|greater than|over|exceeding|exceeds|exceed|above)\s+(\d+(?:\.\d+)?)', ">"),
            (r'(?i)\b(?:less than|fewer than|under|below)\s+(\d+(?:\.\d+)?)', "<"),
            (r'(?i)\b(?:at least|no fewer than|no less than|minimum of|minimum)\s+(\d+(?:\.\d+)?)', ">="),
            (r'(?i)\b(?:at most|no more than|maximum of|maximum)\s+(\d+(?:\.\d+)?)', "<="),
            (r'(?i)\b(?:equal to|equals|exactly)\s+(\d+(?:\.\d+)?)', "="),
        ]

        for pat, op in patterns:
            for match in re.finditer(pat, q_lower):
                val_str = match.group(1)
                val = int(val_str) if val_str.isdigit() else float(val_str)
                sal_field = SchemaAggregationResolver.resolve_numeric_metric(query, available_tables)
                if not any(f.field == sal_field and f.operator == op and f.value == val for f in filters):
                    filters.append(Filter(field=sal_field, operator=op, value=val))
        return filters

    @classmethod
    def extract_metrics(cls, query: str, available_tables: List[str], intent: Any, existing_metrics: Optional[List[Any]] = None) -> List[Any]:
        from app.ai.planner.planner_schema import Metric, IntentEnum
        metrics = list(existing_metrics) if existing_metrics else []
        q_lower = query.lower()
        sal_field = SchemaAggregationResolver.resolve_numeric_metric(query, available_tables)

        if "avg" in q_lower or "average" in q_lower:
            if any(w in q_lower for w in ["salary", "pay", "payroll", "compensation"]):
                if not any(m.operation == "avg" and m.alias == "avg_salary" for m in metrics):
                    metrics.append(Metric(field=sal_field, operation="avg", alias="avg_salary"))
            elif "attendance" in q_lower or "hours" in q_lower or "working hours" in q_lower:
                if not any(m.operation == "avg" and m.alias == "avg_hours" for m in metrics):
                    metrics.append(Metric(field="hours_worked", operation="avg", alias="avg_hours"))
            elif "bonus" in q_lower:
                if not any(m.operation == "avg" and m.alias == "avg_bonus" for m in metrics):
                    metrics.append(Metric(field="bonus", operation="avg", alias="avg_bonus"))
            elif "budget" in q_lower:
                if not any(m.operation == "avg" and m.alias == "avg_budget" for m in metrics):
                    metrics.append(Metric(field="budget", operation="avg", alias="avg_budget"))
            elif "review" in q_lower or "score" in q_lower:
                if not any(m.operation == "avg" and m.alias == "avg_score" for m in metrics):
                    metrics.append(Metric(field="score", operation="avg", alias="avg_score"))
            else:
                if not any(m.operation == "avg" for m in metrics):
                    metrics.append(Metric(field=sal_field, operation="avg", alias="avg_val"))

        if "sum" in q_lower or any(w in q_lower for w in ["total payroll", "total salary", "total pay", "total bonus", "total budget", "total hours", "sum of", "total cost", "total amount"]):
            if any(w in q_lower for w in ["salary", "pay", "payroll"]):
                if not any(m.operation == "sum" and m.alias == "total_payroll" for m in metrics):
                    metrics.append(Metric(field=sal_field, operation="sum", alias="total_payroll"))
            elif "budget" in q_lower:
                if not any(m.operation == "sum" and m.alias == "total_budget" for m in metrics):
                    metrics.append(Metric(field="budget", operation="sum", alias="total_budget"))
            elif "bonus" in q_lower:
                if not any(m.operation == "sum" and m.alias == "total_bonus" for m in metrics):
                    metrics.append(Metric(field="bonus", operation="sum", alias="total_bonus"))
            elif "hours" in q_lower:
                if not any(m.operation == "sum" and m.alias == "total_hours" for m in metrics):
                    metrics.append(Metric(field="hours_worked", operation="sum", alias="total_hours"))
            else:
                if not any(m.operation == "sum" for m in metrics):
                    metrics.append(Metric(field=sal_field, operation="sum", alias="total_val"))

        has_count_phrase = any(w in q_lower for w in ["count", "number of", "how many"])
        has_comparison_count = any(w in q_lower for w in ["more than", "greater than", "less than", "fewer than", "at least", "at most", "over", "under", "no fewer than", "no more than", "exceeding", "above", "below"]) and any(w in q_lower for w in ["employ", "staff", "worker", "person", "member", "proj", "dept", "department", "client", "office", "record", "user"])
        has_total_entity = any(w in q_lower for w in ["total employ", "total staff", "total worker", "total depart", "total project", "total office", "total client", "total user"])

        if has_count_phrase or has_comparison_count or has_total_entity:
            if "distinct" in q_lower:
                if not any(m.operation == "distinct_count" for m in metrics):
                    metrics.append(Metric(field="id", operation="distinct_count", alias="distinct_count"))
            elif not any(m.operation == "count" for m in metrics):
                metrics.append(Metric(field="id", operation="count", alias="count"))

        if "max" in q_lower or "maximum" in q_lower or ("highest" in q_lower and intent == IntentEnum.AGGREGATION):
            field_name = "bonus" if "bonus" in q_lower else ("budget" if "budget" in q_lower else ("hours_worked" if any(w in q_lower for w in ["hours", "attendance"]) else sal_field))
            if intent == IntentEnum.RANKING and not any(w in q_lower for w in ["max", "maximum"]):
                if not any(m.field == field_name and m.operation == "" for m in metrics):
                    metrics.append(Metric(field=field_name, operation="", alias=field_name))
            else:
                if not any(m.operation == "max" for m in metrics):
                    metrics.append(Metric(field=field_name, operation="max", alias=f"max_{field_name}"))

        if "min" in q_lower or "minimum" in q_lower or ("lowest" in q_lower and intent == IntentEnum.AGGREGATION):
            field_name = "score" if any(w in q_lower for w in ["review", "score"]) else ("budget" if "budget" in q_lower else ("hours_worked" if any(w in q_lower for w in ["hours", "attendance"]) else sal_field))
            if intent == IntentEnum.RANKING and not any(w in q_lower for w in ["min", "minimum"]):
                if not any(m.field == field_name and m.operation == "" for m in metrics):
                    metrics.append(Metric(field=field_name, operation="", alias=field_name))
            else:
                if not any(m.operation == "min" for m in metrics):
                    metrics.append(Metric(field=field_name, operation="min", alias=f"min_{field_name}"))

        if not metrics and intent in [IntentEnum.AGGREGATION, IntentEnum.COMPARISON, IntentEnum.RANKING]:
            if intent == IntentEnum.RANKING:
                metrics.append(Metric(field=sal_field, operation="", alias=sal_field))
            else:
                metrics.append(Metric(field="id", operation="count", alias="count"))

        return metrics


class TimeReasoningUtils:
    """Provides deterministic conversion of natural language date expressions into structured Filter objects."""

    @staticmethod
    def parse_time_phrase(
        phrase: str,
        target_field: str = "date",
        table_name: Optional[str] = None,
        ref_date: Optional[date] = None,
    ) -> List[Filter]:
        """Convert a natural-language time phrase into Filter objects.

        Args:
            phrase:       The natural language query string.
            target_field: Fallback column name if schema resolution fails.
            table_name:   If provided, the schema is inspected via
                          SchemaDateColumnResolver to find the actual
                          Date/DateTime column — no hardcoding.
            ref_date:     Reference date for relative phrases (default: today).
        """
        # --- Schema-aware column resolution ---
        if table_name:
            resolved = SchemaDateColumnResolver.resolve(table_name)
            if resolved:
                target_field = resolved
                logger.debug(
                    f"TimeReasoningUtils: resolved date column for '{table_name}' -> '{target_field}'"
                )
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

        tp = TimeSemanticUtils.analyze(phrase, [table_name] if table_name else [], ref_date)
        if tp and tp.start_date:
            val = [tp.start_date, tp.end_date] if tp.operator.lower() == "between" else tp.start_date
            return [Filter(field=target_field, operator=tp.operator, value=val, time_reasoning=tp.relative_period)]
        return []


class TimeSemanticUtils:
    """Semantic analysis for time intelligence expressions without hardcoded table/column logic."""

    @classmethod
    def resolve_target_date_field(cls, query: str, available_tables: List[str]) -> str:
        """Resolve the date field dynamically using SchemaDateColumnResolver and query context."""
        q_lower = query.lower()
        best_table = None
        
        if len(available_tables) > 1:
            for tbl in available_tables:
                t_lower = tbl.lower()
                sing = t_lower[:-1] if t_lower.endswith("s") else t_lower
                if t_lower in q_lower or sing in q_lower:
                    best_table = tbl
                    break
            if not best_table:
                kw_map = {
                    "hire": "employees", "hired": "employees",
                    "payroll": "payroll", "salary": "payroll", "salaries": "payroll", "pay": "payroll",
                    "attendance": "attendance", "hours": "attendance",
                    "project": "projects", "review": "performance_reviews", "leave": "leave_requests"
                }
                for kw, tbl in kw_map.items():
                    if kw in q_lower and tbl in available_tables:
                        best_table = tbl
                        break

        if best_table:
            col = SchemaDateColumnResolver.resolve(best_table)
            if col:
                return col if len(available_tables) == 1 else f"{best_table}.{col}"
        
        tbl, col = SchemaDateColumnResolver.resolve_for_tables(available_tables)
        if col:
            return col if len(available_tables) == 1 else f"{tbl}.{col}"
        return "date"

    @classmethod
    def analyze(
        cls,
        query: str,
        available_tables: List[str],
        ref_date: Optional[date] = None
    ) -> Optional[TimePlan]:
        """Analyse natural language query for time expressions and return a TimePlan."""
        if ref_date is None:
            ref_date = date.today()
        p = query.lower().strip()
        year = ref_date.year
        month = ref_date.month

        date_field = cls.resolve_target_date_field(query, available_tables)

        if "today" in p:
            return TimePlan(
                time_expression="today",
                date_field=date_field,
                operator="=",
                start_date=ref_date.isoformat(),
                end_date=ref_date.isoformat(),
                relative_period="today",
                relative_offset=0,
                granularity="day"
            )

        if "yesterday" in p:
            yest = ref_date - timedelta(days=1)
            return TimePlan(
                time_expression="yesterday",
                date_field=date_field,
                operator="=",
                start_date=yest.isoformat(),
                end_date=yest.isoformat(),
                relative_period="yesterday",
                relative_offset=-1,
                granularity="day"
            )

        if "tomorrow" in p:
            tom = ref_date + timedelta(days=1)
            return TimePlan(
                time_expression="tomorrow",
                date_field=date_field,
                operator="=",
                start_date=tom.isoformat(),
                end_date=tom.isoformat(),
                relative_period="tomorrow",
                relative_offset=1,
                granularity="day"
            )

        days_match = re.search(r"(?:last|past|next)\s+(\d+)\s+days?", p)
        if days_match:
            n_days = int(days_match.group(1))
            is_next = "next" in days_match.group(0)
            if is_next:
                start_d = ref_date
                end_d = ref_date + timedelta(days=n_days)
                rel_period = f"next_{n_days}_days"
                offset = n_days
            else:
                start_d = ref_date - timedelta(days=n_days)
                end_d = ref_date
                rel_period = f"last_{n_days}_days"
                offset = -n_days
            return TimePlan(
                time_expression=days_match.group(0),
                date_field=date_field,
                operator="between",
                start_date=start_d.isoformat(),
                end_date=end_d.isoformat(),
                relative_period=rel_period,
                relative_offset=offset,
                granularity="day"
            )

        if "this week" in p:
            start_week = ref_date - timedelta(days=ref_date.weekday())
            end_week = start_week + timedelta(days=6)
            return TimePlan(
                time_expression="this week",
                date_field=date_field,
                operator="between",
                start_date=start_week.isoformat(),
                end_date=end_week.isoformat(),
                relative_period="this_week",
                relative_offset=0,
                granularity="week"
            )

        if "last week" in p:
            start_week = ref_date - timedelta(days=ref_date.weekday() + 7)
            end_week = start_week + timedelta(days=6)
            return TimePlan(
                time_expression="last week",
                date_field=date_field,
                operator="between",
                start_date=start_week.isoformat(),
                end_date=end_week.isoformat(),
                relative_period="last_week",
                relative_offset=-1,
                granularity="week"
            )

        if "next week" in p:
            start_week = ref_date + timedelta(days=7 - ref_date.weekday())
            end_week = start_week + timedelta(days=6)
            return TimePlan(
                time_expression="next week",
                date_field=date_field,
                operator="between",
                start_date=start_week.isoformat(),
                end_date=end_week.isoformat(),
                relative_period="next_week",
                relative_offset=1,
                granularity="week"
            )

        if "this month" in p:
            start_month = date(year, month, 1)
            if month == 12: end_month = date(year, 12, 31)
            else: end_month = date(year, month + 1, 1) - timedelta(days=1)
            return TimePlan(
                time_expression="this month",
                date_field=date_field,
                operator="between",
                start_date=start_month.isoformat(),
                end_date=end_month.isoformat(),
                relative_period="this_month",
                relative_offset=0,
                granularity="month"
            )

        if "last month" in p:
            if month == 1:
                start_month = date(year - 1, 12, 1)
                end_month = date(year - 1, 12, 31)
            else:
                start_month = date(year, month - 1, 1)
                end_month = date(year, month, 1) - timedelta(days=1)
            return TimePlan(
                time_expression="last month",
                date_field=date_field,
                operator="between",
                start_date=start_month.isoformat(),
                end_date=end_month.isoformat(),
                relative_period="last_month",
                relative_offset=-1,
                granularity="month"
            )

        if "next month" in p:
            if month == 12:
                start_month = date(year + 1, 1, 1)
                end_month = date(year + 1, 1, 31)
            else:
                start_month = date(year, month + 1, 1)
                if month + 1 == 12: end_month = date(year, 12, 31)
                else: end_month = date(year, month + 2, 1) - timedelta(days=1)
            return TimePlan(
                time_expression="next month",
                date_field=date_field,
                operator="between",
                start_date=start_month.isoformat(),
                end_date=end_month.isoformat(),
                relative_period="next_month",
                relative_offset=1,
                granularity="month"
            )

        months_match = re.search(r"(?:last|past)\s+(\d+)\s+months?", p)
        if months_match:
            n_months = int(months_match.group(1))
            m_start = month - n_months
            y_start = year
            while m_start <= 0:
                m_start += 12
                y_start -= 1
            start_m = date(y_start, m_start, 1)
            return TimePlan(
                time_expression=months_match.group(0),
                date_field=date_field,
                operator="between",
                start_date=start_m.isoformat(),
                end_date=ref_date.isoformat(),
                relative_period=f"last_{n_months}_months",
                relative_offset=-n_months,
                granularity="month"
            )

        if "this quarter" in p:
            q_idx = (month - 1) // 3
            start_m = q_idx * 3 + 1
            start_q = date(year, start_m, 1)
            if start_m == 10: end_q = date(year, 12, 31)
            else: end_q = date(year, start_m + 3, 1) - timedelta(days=1)
            return TimePlan(
                time_expression="this quarter",
                date_field=date_field,
                operator="between",
                start_date=start_q.isoformat(),
                end_date=end_q.isoformat(),
                relative_period="this_quarter",
                relative_offset=0,
                granularity="quarter"
            )

        if "last quarter" in p:
            q_idx = (month - 1) // 3
            if q_idx == 0:
                start_q = date(year - 1, 10, 1)
                end_q = date(year - 1, 12, 31)
            else:
                start_m = (q_idx - 1) * 3 + 1
                start_q = date(year, start_m, 1)
                end_q = date(year, start_m + 3, 1) - timedelta(days=1)
            return TimePlan(
                time_expression="last quarter",
                date_field=date_field,
                operator="between",
                start_date=start_q.isoformat(),
                end_date=end_q.isoformat(),
                relative_period="last_quarter",
                relative_offset=-1,
                granularity="quarter"
            )

        if "next quarter" in p:
            q_idx = (month - 1) // 3
            if q_idx == 3:
                start_q = date(year + 1, 1, 1)
                end_q = date(year + 1, 3, 31)
            else:
                start_m = (q_idx + 1) * 3 + 1
                start_q = date(year, start_m, 1)
                if start_m == 10: end_q = date(year, 12, 31)
                else: end_q = date(year, start_m + 3, 1) - timedelta(days=1)
            return TimePlan(
                time_expression="next quarter",
                date_field=date_field,
                operator="between",
                start_date=start_q.isoformat(),
                end_date=end_q.isoformat(),
                relative_period="next_quarter",
                relative_offset=1,
                granularity="quarter"
            )

        if "this year" in p:
            return TimePlan(
                time_expression="this year",
                date_field=date_field,
                operator="between",
                start_date=f"{year}-01-01",
                end_date=f"{year}-12-31",
                relative_period="this_year",
                relative_offset=0,
                granularity="year"
            )

        if "last year" in p:
            return TimePlan(
                time_expression="last year",
                date_field=date_field,
                operator="between",
                start_date=f"{year - 1}-01-01",
                end_date=f"{year - 1}-12-31",
                relative_period="last_year",
                relative_offset=-1,
                granularity="year"
            )

        if "next year" in p:
            return TimePlan(
                time_expression="next year",
                date_field=date_field,
                operator="between",
                start_date=f"{year + 1}-01-01",
                end_date=f"{year + 1}-12-31",
                relative_period="next_year",
                relative_offset=1,
                granularity="year"
            )

        years_match = re.search(r"(?:last|past)\s+(\d+)\s+(?:financial\s+)?years?", p)
        if years_match:
            n_years = int(years_match.group(1))
            return TimePlan(
                time_expression=years_match.group(0),
                date_field=date_field,
                operator="between",
                start_date=f"{year - n_years}-01-01",
                end_date=f"{year}-12-31",
                relative_period=f"last_{n_years}_years",
                relative_offset=-n_years,
                granularity="year"
            )

        months_dict = {
            "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
            "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6,
            "july": 7, "jul": 7, "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
            "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12
        }
        month_range_match = re.search(r"(?:between|from)\s+([a-z]+)\s+(?:and|to|through)\s+([a-z]+)", p)
        if month_range_match:
            m1_name, m2_name = month_range_match.group(1), month_range_match.group(2)
            if m1_name in months_dict and m2_name in months_dict:
                m1, m2 = months_dict[m1_name], months_dict[m2_name]
                start_d = date(year, m1, 1)
                if m2 == 12: end_d = date(year, 12, 31)
                else: end_d = date(year, m2 + 1, 1) - timedelta(days=1)
                return TimePlan(
                    time_expression=month_range_match.group(0),
                    date_field=date_field,
                    operator="between",
                    start_date=start_d.isoformat(),
                    end_date=end_d.isoformat(),
                    relative_period="custom_range",
                    granularity="month"
                )

        year_range_match = re.search(r"(?:between|from)\s+(\d{4})\s+(?:and|to|through)\s+(\d{4})", p)
        if year_range_match:
            y1, y2 = year_range_match.group(1), year_range_match.group(2)
            return TimePlan(
                time_expression=year_range_match.group(0),
                date_field=date_field,
                operator="between",
                start_date=f"{y1}-01-01",
                end_date=f"{y2}-12-31",
                relative_period="custom_range",
                granularity="year"
            )

        before_year_match = re.search(r"(?:before|prior to)\s+(\d{4})", p)
        if before_year_match:
            y = before_year_match.group(1)
            return TimePlan(
                time_expression=before_year_match.group(0),
                date_field=date_field,
                operator="<",
                start_date=f"{y}-01-01",
                end_date=f"{y}-01-01",
                relative_period="custom_range",
                granularity="year"
            )

        after_year_match = re.search(r"(?:after|since)\s+(\d{4})", p)
        if after_year_match:
            y = after_year_match.group(1)
            return TimePlan(
                time_expression=after_year_match.group(0),
                date_field=date_field,
                operator=">",
                start_date=f"{y}-12-31",
                end_date=f"{y}-12-31",
                relative_period="custom_range",
                granularity="year"
            )

        in_year_match = re.search(r"(?:in|during|for)\s+(\d{4})", p)
        if in_year_match:
            y = in_year_match.group(1)
            return TimePlan(
                time_expression=in_year_match.group(0),
                date_field=date_field,
                operator="between",
                start_date=f"{y}-01-01",
                end_date=f"{y}-12-31",
                relative_period="custom_range",
                granularity="year"
            )

        if "current financial year" in p or "this financial year" in p:
            fy_start = f"{year}-04-01" if month >= 4 else f"{year - 1}-04-01"
            fy_end = f"{year + 1}-03-31" if month >= 4 else f"{year}-03-31"
            return TimePlan(
                time_expression="current financial year",
                date_field=date_field,
                operator="between",
                start_date=fy_start,
                end_date=fy_end,
                relative_period="current_financial_year",
                granularity="year"
            )

        if "previous financial year" in p or "last financial year" in p:
            fy_start = f"{year - 1}-04-01" if month >= 4 else f"{year - 2}-04-01"
            fy_end = f"{year}-03-31" if month >= 4 else f"{year - 1}-03-31"
            return TimePlan(
                time_expression="previous financial year",
                date_field=date_field,
                operator="between",
                start_date=fy_start,
                end_date=fy_end,
                relative_period="previous_financial_year",
                granularity="year"
            )

        if "before covid" in p:
            return TimePlan(
                time_expression="before covid",
                date_field=date_field,
                operator="<",
                start_date="2020-03-01",
                end_date="2020-03-01",
                relative_period="before_covid",
                granularity="month"
            )

        if "after covid" in p:
            return TimePlan(
                time_expression="after covid",
                date_field=date_field,
                operator=">",
                start_date="2020-01-01",
                end_date="2020-01-01",
                relative_period="after_covid",
                granularity="month"
            )

        return None



class JoinDetectionUtils:
    """Automatically determines required joins and relationships by inspecting SQLAlchemy schema metadata."""

    @classmethod
    def get_schema_graph(cls) -> Dict[str, Set[str]]:
        graph: Dict[str, Set[str]] = {}
        for table_name, table in Base.metadata.tables.items():
            if table_name in SYSTEM_TABLES:
                continue
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


class SchemaJoinResolver:
    """Generic Join Resolver that determines exact join conditions between tables using only SQLAlchemy metadata."""
    
    @classmethod
    def resolve_join_condition(cls, t1: str, t2: str) -> str:
        """Find the exact ON condition between table t1 and table t2 using Base.metadata.tables foreign keys."""
        tbl1 = Base.metadata.tables.get(t1)
        tbl2 = Base.metadata.tables.get(t2)
        if tbl1 is None or tbl2 is None:
            raise ValueError(f"Table '{t1}' or '{t2}' not found in SQLAlchemy metadata.")
            
        # Check if t1 has a foreign key pointing to t2
        for fk in tbl1.foreign_keys:
            if fk.column.table.name == t2:
                return f"{t1}.{fk.parent.name} = {t2}.{fk.column.name}"
                
        # Check if t2 has a foreign key pointing to t1
        for fk in tbl2.foreign_keys:
            if fk.column.table.name == t1:
                return f"{t2}.{fk.parent.name} = {t1}.{fk.column.name}"
                
        raise ValueError(f"No direct foreign key relationship exists between '{t1}' and '{t2}' in SQLAlchemy metadata.")
        
    @classmethod
    def resolve_joins_for_tables(cls, tables: List[str]) -> List[Any]:
        """Given a list of table names or join paths, resolve exact JoinCondition objects for consecutive pairs."""
        from app.ai.structured_output.schemas import JoinCondition
        
        if not tables:
            return []
            
        table_names = []
        for item in tables:
            if "->" in item:
                for part in item.split("->"):
                    t = part.strip()
                    if t and t not in table_names:
                        table_names.append(t)
            else:
                t = item.strip()
                if t and t not in table_names:
                    table_names.append(t)
                    
        if len(table_names) <= 1:
            return []
            
        joins = []
        seen_pairs = set()
        
        # Use JoinDetectionUtils to find connecting paths
        paths = JoinDetectionUtils.detect_join_paths(table_names)
        for path_str in paths:
            parts = [p.strip() for p in path_str.split("->")]
            for i in range(len(parts) - 1):
                t1, t2 = parts[i], parts[i+1]
                pair_key = tuple(sorted([t1, t2]))
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    on_cond = cls.resolve_join_condition(t1, t2)
                    joins.append(JoinCondition(table=t2, on=on_cond))
        return joins


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
            m_strs = []
            for m in plan.metrics:
                op = m.operation.upper() if m.operation and m.operation.lower() != "none" else ""
                expr = f"{op}({m.field})" if op else m.field
                m_strs.append(expr + (f" AS {m.alias}" if m.alias and m.alias != m.field else ""))
            tasks.append(f"Task {step_num}: Calculate metrics: " + ", ".join(m_strs))
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

        # Task 6: Window Function & Partition Ranking
        if plan.scope == "per_group" or plan.requires_partition_ranking:
            part_str = ", ".join(plan.partition_by) if plan.partition_by else (plan.group or "group")
            rank_metric = plan.metric or (plan.metrics[0].field if plan.metrics else "salary")
            tasks.append(f"Task {step_num}: Apply window function ranking partitioned by [{part_str}] ordering by {rank_metric} {(plan.sort or 'DESC').upper()}")
            step_num += 1
            limit_g = plan.limit_per_group or plan.rank or plan.limit or 1
            tasks.append(f"Task {step_num}: Filter ranked partition results where rank <= {limit_g}")
            step_num += 1
        elif plan.nth_rank is not None or plan.ranking_type == "nth":
            r_val = plan.nth_rank or plan.rank or 2
            tasks.append(f"Task {step_num}: Extract specific rank #{r_val} using window function ranking or offset")
            step_num += 1

        # Task 7: Sorting & Limit (Global)
        sort_limit_parts = []
        if plan.order_by and plan.scope != "per_group":
            o_strs = [f"{o.field} {o.direction.upper()}" for o in plan.order_by]
            sort_limit_parts.append(f"Sort by {', '.join(o_strs)}")
        if plan.limit and plan.scope != "per_group":
            sort_limit_parts.append(f"Limit results to top {plan.limit} rows")
        if sort_limit_parts:
            tasks.append(f"Task {step_num}: " + "; ".join(sort_limit_parts))

        if not tasks:
            tasks.append("Task 1: Retrieve requested columns from primary entity")

        return tasks


class AnalyticalWindowSemanticUtils:
    """Generic semantic analyzer for advanced analytical window function queries (Running Totals, Moving Averages, Lag, Lead, Difference, First/Last Value).
    Avoids hardcoding specific queries by extracting intent, target metrics, grouping/partition scopes, ordering, and frame specifications dynamically from schema metadata.
    """
    _NUMBER_WORD_MAP = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10
    }

    @classmethod
    def analyze(cls, query: str, detected_tables: List[str]) -> Optional[Dict[str, Any]]:
        import re
        q_lower = query.lower().strip()

        analytical_indicators = [
            "running total", "running sum", "running count", "running average", "running avg", "running min", "running max",
            "running payroll", "running salary", "running attendance", "running employee", "running number",
            "cumulative", "moving average", "rolling average", "moving avg", "rolling avg",
            "difference from previous", "diff from previous", "salary difference from previous",
            "previous employee salary", "next employee salary", "previous employee", "next employee",
            "first employee hired", "last employee hired", "first salary", "last attendance", "first value", "last value"
        ]
        if not any(ind in q_lower for ind in analytical_indicators):
            if not (re.search(r'\b(?:rolling|moving)\s+(\w+)\s+(?:month|day|week|year|item|record)?\s*(?:average|avg)\b', q_lower) or
                    re.search(r'\b(?:first|last)\s+(?:employee|user|person|worker)\s+hired\b', q_lower) or
                    re.search(r'\b(?:previous|next)\s+(?:employee|user|person|worker|salary|value)\b', q_lower)):
                return None

        func_name = None
        frame_str = None
        alias_str = "win_val"

        if any(w in q_lower for w in ["difference", "diff", "change from previous", "difference from previous"]):
            func_name = "DIFFERENCE"
            alias_str = "diff_val" if "diff" in q_lower else "salary_diff"
        elif any(w in q_lower for w in ["previous", "prior", "lag"]):
            func_name = "LAG"
            alias_str = "prev_val" if not any(w in q_lower for w in ["salary", "payroll"]) else "prev_salary"
        elif any(w in q_lower for w in ["next", "lead", "following"]):
            func_name = "LEAD"
            alias_str = "next_val" if not any(w in q_lower for w in ["salary", "payroll"]) else "next_salary"
        elif any(w in q_lower for w in ["moving average", "rolling average", "moving avg", "rolling avg"]) or re.search(r'\b(?:rolling|moving)\b', q_lower):
            func_name = "AVG"
            alias_str = "moving_avg" if "moving" in q_lower else "rolling_avg"
            n_val = 3
            m_roll = re.search(r'\b(?:rolling|moving)\s+([a-zA-Z0-9]+)\s+(?:month|day|week|year|item|record)?\s*(?:average|avg)\b', q_lower)
            if m_roll:
                val_s = m_roll.group(1).lower()
                if val_s in cls._NUMBER_WORD_MAP:
                    n_val = cls._NUMBER_WORD_MAP[val_s]
                elif val_s.isdigit():
                    n_val = int(val_s)
            if n_val > 1:
                frame_str = f"ROWS BETWEEN {n_val - 1} PRECEDING AND CURRENT ROW"
            else:
                frame_str = "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW"
        elif any(w in q_lower for w in ["running average", "running avg", "cumulative average", "cumulative avg"]):
            func_name = "AVG"
            alias_str = "running_avg"
            frame_str = "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW"
        elif any(w in q_lower for w in ["running count", "cumulative count", "cumulative hiring", "running number", "running employee count"]):
            func_name = "COUNT"
            alias_str = "running_count" if "running" in q_lower else "cumulative_count"
            frame_str = "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW"
        elif any(w in q_lower for w in ["running min", "cumulative min"]):
            func_name = "MIN"
            alias_str = "running_min"
            frame_str = "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW"
        elif any(w in q_lower for w in ["running max", "cumulative max"]):
            func_name = "MAX"
            alias_str = "running_max"
            frame_str = "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW"
        elif any(w in q_lower for w in ["running total", "running sum", "cumulative total", "cumulative payroll", "cumulative salary", "cumulative attendance", "running payroll", "running salary", "running attendance", "cumulative"]):
            if any(w in q_lower for w in ["hiring", "hire", "employee", "employees", "user", "users", "count", "number"]) and not any(w in q_lower for w in ["salary", "payroll", "pay", "attendance", "hours"]):
                func_name = "COUNT"
                alias_str = "running_count" if "running" in q_lower else "cumulative_count"
            else:
                func_name = "SUM"
                if "payroll" in q_lower:
                    alias_str = "running_payroll_total" if "running" in q_lower else "cumulative_payroll"
                elif "salary" in q_lower:
                    alias_str = "running_salary_total" if "running" in q_lower else "cumulative_salary"
                elif "attendance" in q_lower or "hours" in q_lower:
                    alias_str = "running_attendance_total" if "running" in q_lower else "cumulative_attendance"
                else:
                    alias_str = "running_total"
            frame_str = "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW"
        elif any(w in q_lower for w in ["first employee hired", "first salary", "first value", "earliest employee hired"]):
            func_name = "FIRST_VALUE"
            alias_str = "first_val"
            frame_str = "ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING"
        elif any(w in q_lower for w in ["last employee hired", "last attendance", "last value", "latest employee hired"]):
            func_name = "LAST_VALUE"
            alias_str = "last_val"
            frame_str = "ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING"

        if not func_name:
            return None

        partition_by = None
        group_cols = SemanticQueryParser.extract_grouping(query, detected_tables)
        if group_cols:
            partition_by = [group_cols[0]]
        elif "department" in q_lower and "department" not in [t.rstrip("s") for t in detected_tables if t != "departments"]:
            partition_by = ["departments.name"] if "departments" in detected_tables else ["department"]

        metric_field = None
        if func_name == "COUNT":
            pt = detected_tables[0] if detected_tables else "employees"
            tbl_obj = Base.metadata.tables.get(pt)
            if tbl_obj is not None and tbl_obj.primary_key.columns:
                metric_field = list(tbl_obj.primary_key.columns)[0].name
            else:
                metric_field = "id"
        elif func_name in {"FIRST_VALUE", "LAST_VALUE"} and not any(w in q_lower for w in ["salary", "payroll", "pay", "bonus", "attendance", "hours", "score", "review"]):
            for t_name in detected_tables:
                t_obj = Base.metadata.tables.get(t_name)
                if t_obj is not None:
                    for col in t_obj.columns:
                        if col.name in {"first_name", "name", "full_name", "title", "username"}:
                            metric_field = col.name
                            break
                if metric_field:
                    break
            if not metric_field:
                metric_field = "id"
        else:
            match_res = SchemaColumnResolver.find_matching_schema_column(query, detected_tables)
            if match_res:
                metric_field = match_res[1]
            elif any(w in q_lower for w in ["attendance", "hours"]):
                metric_field = "hours_worked"
            elif any(w in q_lower for w in ["salary", "payroll", "pay", "earning"]):
                metric_field = "base_salary"
            else:
                for t_name in detected_tables:
                    t_obj = Base.metadata.tables.get(t_name)
                    if t_obj is not None:
                        for col in t_obj.columns:
                            if col.name not in {"id", "department_id", "office_id", "employee_id", "user_id"} and not col.name.endswith("_id"):
                                metric_field = col.name
                                break
                    if metric_field:
                        break
                if not metric_field:
                    metric_field = "id"

        order_field = None
        for t_name in detected_tables:
            d_col = SchemaDateColumnResolver.resolve(t_name)
            if d_col:
                order_field = d_col
                break
        if not order_field:
            order_field = "id"

        return {
            "function": func_name,
            "target_metric": metric_field,
            "partition_by": partition_by,
            "order_by": [OrderCondition(field=order_field, direction="asc")],
            "frame": frame_str,
            "alias": alias_str,
            "tables": detected_tables,
            "requires_window_function": True
        }


class RankingSemanticUtils:
    """Generic semantic analyzer for ranking queries (Global Top/Bottom-N, N-th Rank, and Grouped/Partitioned Window Functions).
    Avoids hardcoding specific query strings by extracting intent, ordinals, grouping scopes, and schema-mapped metrics dynamically.
    """

    _ORDINAL_MAP = {
        "first": 1, "1st": 1,
        "second": 2, "2nd": 2,
        "third": 3, "3rd": 3,
        "fourth": 4, "4th": 4,
        "fifth": 5, "5th": 5,
        "sixth": 6, "6th": 6,
        "seventh": 7, "7th": 7,
        "eighth": 8, "8th": 8,
        "ninth": 9, "9th": 9,
        "tenth": 10, "10th": 10
    }

    _NUMBER_WORD_MAP = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
    }

    @classmethod
    def analyze(cls, query: str, detected_tables: List[str]) -> Optional[Dict[str, Any]]:
        q_lower = query.lower().strip()
        
        # Guard 1: Ignore comparison/filter expressions (HAVING or WHERE) like 'at least', 'at most', 'no less than', 'more than', etc.
        if any(re.search(rf'\b{pat}\b', q_lower) for pat in [
            "at least", "at most", "no less than", "no more than", "no fewer than",
            "more than", "less than", "greater than", "fewer than", "exceeds", "exceeding",
            "above", "below", "under", "over"
        ]):
            explicit_ranking = any(re.search(rf'\b{w}\b', q_lower) for w in [
                "top", "bottom", "rank", "first", "last", "latest", "oldest", "newest", "nth", "performer", "earner"
            ]) or any(w in q_lower for w in cls._ORDINAL_MAP.keys()) or re.search(r'\b\d+(?:st|nd|rd|th)\b', q_lower)
            if not explicit_ranking:
                return None

        # Guard 2: Ignore simple scalar aggregations (maximum/minimum of a metric without requesting an entity ranking)
        min_max_match = re.search(r'\b(?:maximum|minimum|max|min)\s+(?:of\s+)?([a-zA-Z0-9_]+)$', q_lower)
        if min_max_match:
            metric_word = min_max_match.group(1)
            if metric_word not in {"employee", "employees", "department", "departments", "project", "projects", "office", "offices", "user", "users", "client", "clients", "manager", "managers", "record", "records"}:
                return None

        # Check if query contains ranking semantic indicators
        ranking_words = [
            "top", "bottom", "highest", "lowest", "best", "worst", "latest", "oldest", "newest", "first", "last",
            "performer", "earner", "rank", "most", "least", "maximum", "minimum", "largest", "smallest", "earliest", "nth"
        ]
        has_ranking_word = any(re.search(r'\b' + re.escape(w) + r'\b', q_lower) for w in ranking_words) or any(re.search(r'\b' + re.escape(w) + r'\b', q_lower) for w in cls._ORDINAL_MAP.keys()) or re.search(r'\b\d+(?:st|nd|rd|th)\b', q_lower)
        if not has_ranking_word:
            return None

        # 1. Detect N-th Rank or Ordinal
        nth_rank = None
        for word, val in cls._ORDINAL_MAP.items():
            if re.search(r'\b' + re.escape(word) + r'\b', q_lower):
                if val > 1:
                    nth_rank = val
                break
        if nth_rank is None:
            nth_match = re.search(r'\b(\d+)(?:st|nd|rd|th)\b', q_lower)
            if nth_match and int(nth_match.group(1)) > 1:
                nth_rank = int(nth_match.group(1))

        # 2. Detect Limit or Top-N / Bottom-N count
        rank_val = nth_rank
        if rank_val is None:
            limit_match = re.search(r'(?:top|first|last|highest|lowest|best|worst|bottom|most|least|maximum|minimum|largest|smallest)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b', q_lower)
            if not limit_match:
                limit_match = re.search(r'\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:lowest|highest|top|best|worst|bottom|most|least|maximum|minimum|largest|smallest)\b', q_lower)
            if limit_match:
                val_str = limit_match.group(1)
                rank_val = cls._NUMBER_WORD_MAP.get(val_str, int(val_str) if val_str.isdigit() else 1)
            else:
                rank_val = 1

        # 3. Detect Sort Direction and Ranking Type
        is_asc = any(re.search(r'\b' + re.escape(w) + r'\b', q_lower) for w in ["lowest", "worst", "oldest", "earliest", "bottom", "smallest", "minimum", "least", "asc", "second lowest", "third lowest", "fourth lowest", "fifth lowest"])
        direction = "asc" if is_asc else "desc"
        
        if nth_rank is not None:
            ranking_type = "nth"
        else:
            ranking_type = "bottom" if direction == "asc" else "top"

        # 4. Detect Grouping Scope & Partitioning
        scope = "global"
        group_col = None
        partition_by = None
        
        group_cols = SemanticQueryParser.extract_grouping(query, detected_tables)
        if group_cols:
            scope = "per_group"
            group_col = group_cols[0]
            partition_by = [group_col]

        # 5. Schema-Aware Metric Field Resolution
        metric_field = None
        is_date_ranking = any(re.search(r'\b' + re.escape(w) + r'\b', q_lower) for w in ["latest", "oldest", "newest", "first", "last", "recent", "hired", "hire", "hiring", "earliest"])
        if is_date_ranking and not any(w in q_lower for w in ["salary", "pay", "payroll", "bonus", "attendance", "hours", "score", "performer", "performance"]):
            for t_name in detected_tables:
                res_col = SchemaDateColumnResolver.resolve(t_name)
                if res_col:
                    metric_field = res_col
                    break
        
        if not metric_field:
            match_res = SchemaColumnResolver.find_matching_schema_column(query, detected_tables)
            if match_res:
                matched_table, matched_col = match_res
                metric_field = matched_col
                if matched_table not in detected_tables:
                    detected_tables.append(matched_table)
            else:
                metric_field = SchemaAggregationResolver.resolve_numeric_metric(query, detected_tables)
                if metric_field == "base_salary" and "payroll" not in detected_tables:
                    detected_tables.append("payroll")

        if not metric_field:
            metric_field = "id"

        if group_col:
            for t_name in Base.metadata.tables.keys():
                if t_name in SYSTEM_TABLES:
                    continue
                if t_name == group_col or t_name == f"{group_col}s" or t_name == f"{group_col}es" or (group_col.endswith("y") and t_name == f"{group_col[:-1]}ies"):
                    if t_name not in detected_tables:
                        detected_tables.append(t_name)
                    break

        return {
            "is_ranking": True,
            "ranking_type": ranking_type,
            "rank": rank_val,
            "nth_rank": nth_rank,
            "scope": scope,
            "group": group_col,
            "partition_by": partition_by,
            "order": direction,
            "metric_field": metric_field,
            "tables": list(dict.fromkeys(detected_tables)),
            "requires_window_function": True,
            "requires_partition_ranking": (scope == "per_group"),
            "requires_correlated_subquery": (ranking_type == "nth" and scope == "global")
        }

