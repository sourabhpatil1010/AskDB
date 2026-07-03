import logging
import re
from app.models import Base
from app.ai.structured_output.schemas import StructuredQuery

logger = logging.getLogger(__name__)

# Patterns for SQL expressions that bypass raw column validation
_COMPUTED_EXPR_PATTERN = re.compile(
    r'(?i)^('
    r'date_trunc\s*\('
    r'|extract\s*\('
    r'|to_char\s*\('
    r'|count\s*\('
    r'|sum\s*\('
    r'|avg\s*\('
    r'|min\s*\('
    r'|max\s*\('
    r'|coalesce\s*\('
    r'|cast\s*\('
    r'|concat\s*\('
    r'|round\s*\('
    r'|floor\s*\('
    r'|ceil\s*\('
    r'|\*'  # COUNT(*)
    r')'
)

def _is_computed_expression(expr: str) -> bool:
    """Returns True if the expression is a SQL function/computed expression that does not map to a raw column name."""
    stripped = expr.strip()
    # Has function call pattern
    if _COMPUTED_EXPR_PATTERN.match(stripped):
        return True
    # Contains AS alias (e.g. "DATE_TRUNC('month', employees.hire_date) AS month")
    if re.search(r'\bAS\b', stripped, re.IGNORECASE):
        return True
    return False


def resolve_synthetic_columns(query: StructuredQuery):
    """Schema-aware resolution of synthetic columns (e.g., converting 'full_name' or 'name' to CONCAT(first_name, ' ', last_name))."""
    from app.models import Base as _Base
    
    def _resolve_col(expr: str) -> str:
        stripped = expr.strip()
        if _is_computed_expression(stripped) or "CONCAT" in stripped.upper():
            return expr
        as_match = re.search(r'^(.+?)\s+AS\s+(\w+)\s*$', stripped, re.IGNORECASE)
        core_col = as_match.group(1).strip() if as_match else stripped
        
        parts = core_col.split(".")
        c_name = parts[-1].strip()
        from app.ai.planner.planner_utils import SchemaColumnResolver
        all_tbls = [query.table] + [j.table for j in (query.joins or [])]
        t_name = parts[0].strip() if len(parts) > 1 else (SchemaColumnResolver.resolve_column_owner(c_name, all_tbls) or query.table)
        
        tbl_obj = _Base.metadata.tables.get(t_name)
        if tbl_obj is not None:
            col_names = [c.name for c in tbl_obj.columns]
            if c_name not in col_names and any(kw in c_name.lower() for kw in ["name", "details", "info", "employee"]) and "first_name" in col_names and "last_name" in col_names:
                qual_prefix = f"{t_name}." if len(parts) > 1 else ""
                target_alias = as_match.group(2) if as_match else c_name
                return f"CONCAT({qual_prefix}first_name, ' ', {qual_prefix}last_name) AS {target_alias}"
        return expr

    if query.columns:
        query.columns = [_resolve_col(c) for c in query.columns]
    if query.sort and query.sort.field:
        resolved_sort = _resolve_col(query.sort.field)
        as_match = re.search(r'^(.+?)\s+AS\s+(\w+)\s*$', resolved_sort, re.IGNORECASE)
        query.sort.field = as_match.group(2) if as_match else resolved_sort
        if as_match and query.sort.table:
            query.sort.table = None
    if query.group_by:
        new_gb = []
        for gb in query.group_by:
            res_gb = _resolve_col(gb)
            as_m = re.search(r'^(.+?)\s+AS\s+(\w+)\s*$', res_gb, re.IGNORECASE)
            new_gb.append(as_m.group(1).strip() if as_m else res_gb)
        query.group_by = new_gb
    if query.ranking:
        if query.ranking.partition_by:
            new_part = []
            for p in query.ranking.partition_by:
                res_p = _resolve_col(p)
                as_m = re.search(r'^(.+?)\s+AS\s+(\w+)\s*$', res_p, re.IGNORECASE)
                new_part.append(as_m.group(1).strip() if as_m else res_p)
            query.ranking.partition_by = new_part
        if query.ranking.order_by and query.ranking.order_by.field:
            res_order = _resolve_col(query.ranking.order_by.field)
            as_m = re.search(r'^(.+?)\s+AS\s+(\w+)\s*$', res_order, re.IGNORECASE)
            query.ranking.order_by.field = as_m.group(2) if as_m else res_order
            if as_m and query.ranking.order_by.table:
                query.ranking.order_by.table = None
    if query.window_function:
        if query.window_function.partition_by:
            new_part = []
            for p in query.window_function.partition_by:
                res_p = _resolve_col(p)
                as_m = re.search(r'^(.+?)\s+AS\s+(\w+)\s*$', res_p, re.IGNORECASE)
                new_part.append(as_m.group(1).strip() if as_m else res_p)
            query.window_function.partition_by = new_part
        if query.window_function.order_by:
            for o in query.window_function.order_by:
                if o.field:
                    res_order = _resolve_col(o.field)
                    as_m = re.search(r'^(.+?)\s+AS\s+(\w+)\s*$', res_order, re.IGNORECASE)
                    o.field = as_m.group(2) if as_m else res_order
                    if as_m and o.table:
                        o.table = None


class QueryValidator:
    def __init__(self):
        self.schema = {}
        for table_name, table in Base.metadata.tables.items():
            self.schema[table_name] = [col.name for col in table.columns]

    def _extract_column(self, field_str: str) -> str:
        """Extract the raw column name from potential aggregation functions or AS aliases."""
        s = field_str.strip()
        as_match = re.search(r'^(.+?)\s+AS\s+\w+\s*$', s, re.IGNORECASE)
        if as_match:
            s = as_match.group(1).strip()
        match = re.search(r'(?i)^(?:count|sum|avg|min|max)\((.+)\)$', s.strip())
        if match:
            return match.group(1).strip()
        return s.strip()

    def validate(self, query: StructuredQuery) -> bool:
        resolve_synthetic_columns(query)
        if query.table not in self.schema:
            logger.error(f"Validation failed: Table '{query.table}' does not exist.")
            raise ValueError(f"Table '{query.table}' does not exist.")
            
        valid_tables = [query.table]
        if query.joins:
            for j in query.joins:
                if j.table not in self.schema:
                    raise ValueError(f"Joined table '{j.table}' does not exist.")
                valid_tables.append(j.table)
                
        def _validate_col(col_name: str, explicit_table: str = None):
            if not col_name:
                return
            from sqlalchemy import Numeric, Integer, Float
            s_val = col_name.strip()
            as_match_val = re.search(r'^(.+?)\s+AS\s+\w+\s*$', s_val, re.IGNORECASE)
            if as_match_val:
                s_val = as_match_val.group(1).strip()
            agg_num_match = re.search(r'(?i)^(sum|avg)\((.+)\)$', s_val)
            if agg_num_match:
                op_num = agg_num_match.group(1).upper()
                inner_num = agg_num_match.group(2).strip()
                if re.match(r'(?i)^distinct\s+', inner_num):
                    inner_num = re.sub(r'(?i)^distinct\s+', '', inner_num).strip()
                t_n, c_n = None, inner_num
                if "." in inner_num:
                    t_n, c_n = inner_num.split(".", 1)
                else:
                    for t in valid_tables:
                        if inner_num in self.schema.get(t, []):
                            t_n = t
                            break
                    if not t_n:
                        for t, cols in self.schema.items():
                            if inner_num in cols:
                                t_n = t
                                break
                if t_n and c_n and c_n != "*":
                    tbl_obj = Base.metadata.tables.get(t_n)
                    if tbl_obj is not None:
                        col_obj = tbl_obj.columns.get(c_n)
                        if col_obj is not None and not isinstance(col_obj.type, (Numeric, Integer, Float)):
                            raise ValueError(f"Validation failed: Aggregate function {op_num} requires a numeric column, but got non-numeric column '{c_n}' of type {col_obj.type} in table '{t_n}'.")

            if _is_computed_expression(col_name):
                return

            cleaned_col = self._extract_column(col_name)
            if _is_computed_expression(cleaned_col):
                return

            if cleaned_col == "*" or cleaned_col.endswith(".*") or col_name == "*" or col_name.endswith(".*"):
                return
                
            if "." in cleaned_col:
                parts = cleaned_col.split(".", 1)
                t_name, c_name = parts[0], parts[1]
                if c_name == "*":
                    return
                if t_name not in valid_tables:
                    raise ValueError(f"Table qualifier '{t_name}' not in query tables {valid_tables}")
                if c_name not in self.schema.get(t_name, []):
                    raise ValueError(f"Column '{c_name}' not found in '{t_name}'")
                return
                
            if explicit_table:
                if explicit_table not in valid_tables:
                    raise ValueError(f"Table qualifier '{explicit_table}' not in query tables {valid_tables}")
                if cleaned_col not in self.schema.get(explicit_table, []):
                    raise ValueError(f"Column '{cleaned_col}' not found in '{explicit_table}'")
                return
                
            found = False
            for t in valid_tables:
                if cleaned_col in self.schema[t]:
                    found = True
                    break
            if not found:
                for t_name, cols in self.schema.items():
                    if cleaned_col in cols:
                        logger.warning(f"Column '{cleaned_col}' found in '{t_name}', but '{t_name}' is not in valid_tables {valid_tables}. Allowing for dynamic schema resolution.")
                        return
                raise ValueError(f"Column '{cleaned_col}' not found in tables {valid_tables}")

        # Validate columns
        for col in query.columns:
            _validate_col(col)

        # Validate filters
        if query.filters:
            for f in query.filters:
                _validate_col(f.field, f.table)
                # Check value structure for IN and BETWEEN
                if f.operator.value == "BETWEEN" and not (isinstance(f.value, list) and len(f.value) == 2):
                    raise ValueError(f"Operator BETWEEN requires a list of 2 values for field '{f.field}'")
                if f.operator.value == "IN" and not isinstance(f.value, list):
                    raise ValueError(f"Operator IN requires a list of values for field '{f.field}'")

        # Validate sort
        if query.sort:
            # Sort field may be an alias (e.g. "avg_salary") or an expression — skip strict validation
            if not _is_computed_expression(query.sort.field) and "." not in query.sort.field:
                # It might be an alias from an aggregation — treat it permissively
                # Only raise if it looks like a raw column name that doesn't exist AND has no alias-like appearance
                pass
            else:
                _validate_col(query.sort.field, query.sort.table)

        # Validate group_by — allow computed expressions (DATE_TRUNC, EXTRACT, etc.)
        if query.group_by:
            for gb in query.group_by:
                _validate_col(gb)

        # Validate having
        if query.having:
            for h in query.having:
                _validate_col(h.column)

        # Validate ranking
        if query.ranking:
            if query.ranking.partition_by:
                for p in query.ranking.partition_by:
                    _validate_col(p)
            if query.ranking.order_by:
                if not _is_computed_expression(query.ranking.order_by.field) and "." not in query.ranking.order_by.field:
                    pass
                else:
                    _validate_col(query.ranking.order_by.field, query.ranking.order_by.table)

        # Validate window_function
        if query.window_function:
            supported_funcs = {"ROW_NUMBER", "RANK", "DENSE_RANK", "LAG", "LEAD", "SUM", "AVG", "MIN", "MAX", "COUNT", "FIRST_VALUE", "LAST_VALUE", "DIFFERENCE", "DIFF"}
            raw_func_name = query.window_function.function.split("(")[0].strip().upper()
            if raw_func_name not in supported_funcs:
                raise ValueError(f"Unsupported window function: '{query.window_function.function}'")
            if not query.window_function.alias or not isinstance(query.window_function.alias, str) or not query.window_function.alias.strip():
                raise ValueError("Window function alias must be a valid non-empty string")
            if query.window_function.partition_by:
                for p in query.window_function.partition_by:
                    _validate_col(p)
            if query.window_function.order_by:
                for o in query.window_function.order_by:
                    if not _is_computed_expression(o.field) and "." not in o.field:
                        pass
                    else:
                        _validate_col(o.field, o.table)
            target_col = getattr(query.window_function, "column", None) or getattr(query.window_function, "field", None) or getattr(query.window_function, "target_column", None)
            if target_col and target_col != "*" and not target_col.endswith(".*"):
                if not _is_computed_expression(target_col) and "." not in target_col:
                    pass
                else:
                    _validate_col(target_col)
            if getattr(query.window_function, "frame", None) is not None:
                if not isinstance(query.window_function.frame, str) or not query.window_function.frame.strip():
                    raise ValueError("Window frame specification must be a non-empty string")

        # Validate time_plan
        if getattr(query, "time_plan", None):
            tp = query.time_plan
            _validate_col(tp.date_field)
            valid_operators = {"=", "!=", ">", "<", ">=", "<=", "between", "before", "after", "in"}
            if tp.operator.lower() not in valid_operators:
                raise ValueError(f"Invalid temporal operator: '{tp.operator}'")
            if tp.operator.lower() in ("between",) and not (tp.start_date and tp.end_date):
                raise ValueError(f"Operator '{tp.operator}' in TimePlan requires both start_date and end_date")
            if tp.operator.lower() in (">", "<", ">=", "<=", "before", "after") and not (tp.start_date or tp.end_date or tp.relative_period or tp.time_expression):
                raise ValueError(f"Operator '{tp.operator}' in TimePlan requires a comparison date or expression")
            if tp.relative_period and not isinstance(tp.relative_period, str):
                raise ValueError("relative_period must be a string")

            def _validate_iso_date(d_str: str, label: str):
                if not d_str:
                    return
                if any(kw in str(d_str).lower() for kw in ("current", "now", "today", "yesterday", "tomorrow", "interval", "start", "end", "resolved")):
                    return
                try:
                    from datetime import date, datetime
                    if "T" in str(d_str) or " " in str(d_str):
                        datetime.fromisoformat(str(d_str))
                    else:
                        date.fromisoformat(str(d_str))
                except ValueError:
                    raise ValueError(f"Invalid {label} format in TimePlan: '{d_str}'. Expected ISO format YYYY-MM-DD.")

            _validate_iso_date(getattr(tp, "start_date", None), "start_date")
            _validate_iso_date(getattr(tp, "end_date", None), "end_date")

            if getattr(tp, "start_date", None) and getattr(tp, "end_date", None):
                try:
                    from datetime import date
                    s_d = date.fromisoformat(str(tp.start_date)[:10])
                    e_d = date.fromisoformat(str(tp.end_date)[:10])
                    if s_d > e_d:
                        raise ValueError(f"Invalid date range in TimePlan: start_date '{tp.start_date}' is after end_date '{tp.end_date}'")
                except ValueError as e:
                    if "Invalid date range" in str(e):
                        raise
                except Exception:
                    pass

        # Validate subquery_plan
        if getattr(query, "subquery_plan", None):
            sp = query.subquery_plan
            valid_subq_types = {"scalar", "in", "not_in", "exists", "not_exists", "correlated", "table"}
            if sp.subquery_type.lower() not in valid_subq_types:
                raise ValueError(f"Invalid subquery_type: '{sp.subquery_type}'")
            if sp.target_table:
                if sp.target_table not in self.schema:
                    raise ValueError(f"Target table '{sp.target_table}' in SubqueryPlan does not exist in schema.")
                if sp.target_table not in valid_tables:
                    valid_tables.append(sp.target_table)
            if sp.target_column:
                _validate_col(sp.target_column, sp.target_table if sp.target_table in valid_tables else None)
            if sp.comparison_operator:
                valid_ops = {"=", "!=", ">", "<", ">=", "<=", "in", "not in", "exists", "not exists", "like", "between"}
                if sp.comparison_operator.lower() not in valid_ops:
                    raise ValueError(f"Invalid comparison operator in SubqueryPlan: '{sp.comparison_operator}'")
            if sp.aggregate_function:
                valid_aggs = {"avg", "sum", "count", "min", "max"}
                if sp.aggregate_function.lower() not in valid_aggs:
                    raise ValueError(f"Invalid aggregate function in SubqueryPlan: '{sp.aggregate_function}'")
                if sp.subquery_type.lower() == "scalar" and sp.aggregate_function.lower() in ("avg", "sum") and sp.target_table and sp.target_column and sp.target_column != "id":
                    tbl_obj = Base.metadata.tables.get(sp.target_table)
                    if tbl_obj is not None and sp.target_column in tbl_obj.columns:
                        import sqlalchemy as sa
                        col_type = tbl_obj.columns[sp.target_column].type
                        if not isinstance(col_type, (sa.Numeric, sa.Integer, sa.Float, sa.BigInteger, sa.SmallInteger)):
                            raise ValueError(f"Aggregate function '{sp.aggregate_function}' cannot be applied to non-numeric column '{sp.target_table}.{sp.target_column}'")
            if sp.correlation_columns:
                for col in sp.correlation_columns:
                    _validate_col(col)

        return True
