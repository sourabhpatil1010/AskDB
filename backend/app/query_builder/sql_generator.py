import logging
from typing import Tuple, Dict, Any
from app.ai.structured_output.schemas import StructuredQuery, OperatorEnum
from app.query_builder.param_coercion import coerce_parameters

logger = logging.getLogger(__name__)

class SQLGenerator:
    """
    Generates parameterized PostgreSQL queries from StructuredQuery objects.
    Supports:
    - SELECT with aggregation expressions (COUNT, SUM, AVG, MIN, MAX)
    - DATE_TRUNC / EXTRACT time granularity in GROUP BY and SELECT
    - HAVING clause conditions on aggregated results
    - JOINs, WHERE, ORDER BY, LIMIT, OFFSET
    - Parameterized filters via :param_name binding
    """
    def __init__(self):
        pass

    def _build_select_clause(self, columns: list[str] | None, all_tbls: list[str], default_table: str, win_expr: str | None = None) -> str:
        from app.ai.planner.planner_utils import SchemaColumnResolver
        if columns:
            qual_cols = [SchemaColumnResolver.qualify_column(c, all_tbls, default_table=default_table) for c in columns]
        else:
            qual_cols = ["*"]
        if win_expr and not any("OVER (" in c for c in qual_cols):
            qual_cols.append(win_expr)
        return f"SELECT\n    {', '.join(qual_cols)}"

    def _build_from_clause(self, table: str) -> str:
        return f"FROM {table}"

    def _build_join_clause(self, joins: Any) -> list[str]:
        if not joins:
            return []
        return [f"JOIN {join.table} ON {join.on}" for join in joins]

    def _build_where_clause(
        self,
        filters: Any,
        all_tbls: list[str],
        default_table: str,
        param_counter: int,
        parameters: Dict[str, Any],
        param_field_map: Dict[str, tuple[str, str]]
    ) -> Tuple[str | None, int]:
        if not filters:
            return None, param_counter
        from app.ai.planner.planner_utils import SchemaColumnResolver
        where_clauses = []
        for f in filters:
            filter_table = SchemaColumnResolver.resolve_column_owner(f.field, all_tbls) or f.table or default_table
            qual_field = SchemaColumnResolver.qualify_column(f.field, all_tbls, default_table=default_table)
            param_name = f"{f.field.replace('(', '').replace(')', '')}_{param_counter}"
            if filter_table:
                param_name = f"{filter_table}_{param_name}"
            op = f.operator.value
            
            if op in ("IS NULL", "IS NOT NULL"):
                where_clauses.append(f"{qual_field} {op}")
            elif op == "BETWEEN":
                param_name_1 = f"{param_name}_1"
                param_name_2 = f"{param_name}_2"
                where_clauses.append(f"{qual_field} BETWEEN :{param_name_1} AND :{param_name_2}")
                parameters[param_name_1] = f.value[0]
                parameters[param_name_2] = f.value[1]
                param_field_map[param_name_1] = (filter_table, f.field)
                param_field_map[param_name_2] = (filter_table, f.field)
            elif op == "IN":
                in_params = []
                for idx, val in enumerate(f.value):
                    p_name = f"{param_name}_{idx}"
                    in_params.append(f":{p_name}")
                    parameters[p_name] = val
                    param_field_map[p_name] = (filter_table, f.field)
                in_str = ", ".join(in_params)
                where_clauses.append(f"{qual_field} IN ({in_str})")
            else:
                where_clauses.append(f"{qual_field} {op} :{param_name}")
                parameters[param_name] = f.value
                param_field_map[param_name] = (filter_table, f.field)
            
            param_counter += 1
        return "WHERE " + "\n  AND ".join(where_clauses), param_counter

    def _build_order_clause(
        self,
        sort: Any,
        columns: list[str] | None,
        group_by: list[str] | None,
        all_tbls: list[str],
        default_table: str
    ) -> str | None:
        if not sort:
            return None
        from app.ai.planner.planner_utils import SchemaColumnResolver
        from app.query_builder.query_validator import _is_computed_expression
        import re
        
        direction = sort.direction.upper()
        if direction not in ("ASC", "DESC"):
            direction = "ASC"
        sort_field = sort.field.strip()
        
        is_alias = False
        for col_expr in (columns or []):
            as_match = re.search(r'\bAS\s+([a-zA-Z0-9_]+)\s*$', col_expr.strip(), re.IGNORECASE)
            if as_match and as_match.group(1).lower() == sort_field.lower():
                is_alias = True
                break
        
        if group_by and not is_alias:
            in_gb = any(sort_field.lower() == gb.lower() or sort_field.lower().endswith("." + gb.lower()) or gb.lower().endswith("." + sort_field.lower()) for gb in group_by)
            if not in_gb and not _is_computed_expression(sort_field):
                for expr in (columns or []):
                    as_m = re.search(r'^(.+?)(?:\s+AS\s+([a-zA-Z0-9_]+))?\s*$', expr.strip(), re.IGNORECASE)
                    full_expr = as_m.group(1).strip() if as_m else expr.strip()
                    alias = as_m.group(2).strip() if (as_m and as_m.group(2)) else None
                    if re.search(r'\b' + re.escape(sort_field) + r'\b', full_expr, re.IGNORECASE):
                        sort_field = alias if alias else full_expr
                        is_alias = bool(alias)
                        break

        is_table_col = False
        if sort.table:
            from app.models import Base as _Base
            tbl_obj = _Base.metadata.tables.get(sort.table)
            if tbl_obj is not None and sort_field in [c.name for c in tbl_obj.columns]:
                is_table_col = True
        
        if is_alias or _is_computed_expression(sort_field) or "." in sort_field or not is_table_col:
            qual_sort_field = sort_field
        elif sort.table:
            qual_sort_field = SchemaColumnResolver.qualify_column(sort_field, [sort.table] + all_tbls, default_table=sort.table)
        else:
            qual_sort_field = SchemaColumnResolver.qualify_column(sort_field, all_tbls, default_table=default_table)
            
        return f"ORDER BY {qual_sort_field} {direction}"

    def compile_window_function(self, wf: Any, available_tables: list[str], default_table: str | None = None) -> str:
        from app.ai.planner.planner_utils import SchemaColumnResolver, SchemaGroupingResolver
        from app.query_builder.query_validator import _is_computed_expression
        import re
        if not default_table and available_tables:
            default_table = available_tables[0]
            
        raw_func = getattr(wf, "function", "") or ""
        m = re.match(r'^(\w+)\((.*?)\)$', raw_func.strip(), re.IGNORECASE)
        if m:
            func_name = m.group(1).upper()
            embedded_col = m.group(2).strip()
        else:
            func_name = raw_func.strip().upper()
            embedded_col = None

        over_parts = []
        if wf.partition_by:
            qual_parts = []
            for p in wf.partition_by:
                res = SchemaGroupingResolver.resolve_grouping_column(p, available_tables, default_table=default_table)
                qual_parts.append(res or p)
            over_parts.append(f"PARTITION BY {', '.join(qual_parts)}")
        if wf.order_by:
            order_strs = []
            for o in wf.order_by:
                tbl = o.table
                fld = o.field
                if not tbl:
                    tbl = SchemaColumnResolver.resolve_column_owner(fld, available_tables) or default_table
                qual_f = f"{tbl}.{fld}" if tbl and not fld.startswith(f"{tbl}.") else fld
                order_strs.append(f"{qual_f} {o.direction.upper()}")
            over_parts.append(f"ORDER BY {', '.join(order_strs)}")
        if getattr(wf, "frame", None) and str(wf.frame).strip() and func_name not in {"ROW_NUMBER", "RANK", "DENSE_RANK", "LAG", "LEAD", "DIFFERENCE", "DIFF"}:
            over_parts.append(str(wf.frame).strip())
        over_clause = " ".join(over_parts)
        
        ranking_funcs = {"ROW_NUMBER", "RANK", "DENSE_RANK"}
        if func_name in ranking_funcs:
            func_expr = f"{func_name}()"
        else:
            target_col = embedded_col or getattr(wf, "column", None) or getattr(wf, "field", None) or getattr(wf, "target_column", None) or getattr(wf, "expression", None) or getattr(wf, "arg", None)
            if not target_col:
                target_col = "*"
            if target_col != "*" and not target_col.endswith(".*"):
                if not _is_computed_expression(target_col) and "." not in target_col:
                    owner = SchemaColumnResolver.resolve_column_owner(target_col, available_tables) or default_table
                    if owner:
                        target_col = f"{owner}.{target_col}"
            if func_name in {"DIFFERENCE", "DIFF"}:
                func_expr = f"{target_col} - LAG({target_col})"
            else:
                func_expr = f"{func_name}({target_col})"
            
        expr = f"{func_expr} OVER ({over_clause})"
        if wf.alias:
            expr += f" AS {wf.alias}"
        return expr

    def generate(self, query: StructuredQuery) -> Tuple[str, Dict[str, Any]]:
        from app.query_builder.query_validator import resolve_synthetic_columns
        resolve_synthetic_columns(query)

        # Handle ranking queries
        if query.ranking:
            if query.ranking.scope == "global" and query.ranking.type in ("top", "bottom") and not query.ranking.dense_rank and not query.ranking.partition_by:
                if query.ranking.order_by:
                    query.sort = query.ranking.order_by
                if query.ranking.rank:
                    query.limit = query.ranking.rank
            else:
                return self._generate_ranking_sql(query)


        from app.ai.planner.planner_utils import SchemaColumnResolver
        all_tbls = [query.table] + [j.table for j in (query.joins or [])]
        logger.info("--- DEBUG: BEFORE SQL GENERATION ---")
        logger.info(f"Tables: {all_tbls}")
        logger.info(f"Columns: {query.columns}")
        aggs = [c for c in (query.columns or []) if any(op in c.upper() for op in ("COUNT(", "SUM(", "AVG(", "MAX(", "MIN("))]
        logger.info(f"Aggregations: {aggs}")
        if query.columns:
            for col in query.columns:
                owner = SchemaColumnResolver.resolve_column_owner(col, all_tbls)
                qual = SchemaColumnResolver.qualify_column(col, all_tbls, default_table=query.table)
                logger.info(f"Resolved owner table for '{col}': {owner} -> Generated qualified column: '{qual}'")

        sql_parts = []
        parameters = {}
        # Maps each parameter name -> (table, field) for type coercion
        param_field_map: Dict[str, tuple[str, str]] = {}
        param_counter = 1

        # SELECT
        win_expr = None
        if query.window_function:
            win_expr = self.compile_window_function(query.window_function, all_tbls, default_table=query.table)
        sql_parts.append(self._build_select_clause(query.columns or [], all_tbls, query.table, win_expr=win_expr))

        # FROM
        sql_parts.append(self._build_from_clause(query.table))

        # JOINS
        sql_parts.extend(self._build_join_clause(query.joins))

        # WHERE
        where_str, param_counter = self._build_where_clause(
            query.filters, all_tbls, query.table, param_counter, parameters, param_field_map
        )
        if where_str:
            sql_parts.append(where_str)

        # GROUP BY
        if query.group_by and not (query.window_function and getattr(query.window_function, "function", "") not in {"ROW_NUMBER", "RANK", "DENSE_RANK", ""}):
            qual_gb = [SchemaColumnResolver.qualify_column(gb, all_tbls, default_table=query.table) for gb in query.group_by]
            sql_parts.append("GROUP BY " + ", ".join(qual_gb))

        # HAVING — aggregated condition filtering
        if query.having:
            import re
            alias_expr_map = {}
            for col_expr in query.columns:
                as_match = re.search(r'^(.+?)\s+AS\s+([a-zA-Z0-9_]+)\s*$', col_expr.strip(), re.IGNORECASE)
                if as_match:
                    alias_expr_map[as_match.group(2).strip().lower()] = as_match.group(1).strip()

            having_clauses = []
            for h in query.having:
                op = h.operator.strip()
                if op not in (">", "<", ">=", "<=", "=", "!="):
                    logger.warning(f"Skipping HAVING with invalid operator: '{op}'")
                    continue
                h_col = h.column.strip()
                as_m = re.search(r'^(.+?)\s+AS\s+\w+\s*$', h_col, re.IGNORECASE)
                clean_h_col = as_m.group(1).strip() if as_m else h_col
                if clean_h_col.lower() in alias_expr_map:
                    clean_h_col = alias_expr_map[clean_h_col.lower()]
                else:
                    if not re.search(r'(?i)^(count|sum|avg|min|max)\(', clean_h_col):
                        for alias_key, expr_val in alias_expr_map.items():
                            if clean_h_col.lower() in alias_key or alias_key in clean_h_col.lower():
                                clean_h_col = expr_val
                                break
                    if not re.search(r'(?i)^(count|sum|avg|min|max)\(', clean_h_col):
                        if "count" in clean_h_col.lower():
                            pk_col = "id"
                            tbl_obj = Base.metadata.tables.get(query.table)
                            if tbl_obj is not None and tbl_obj.primary_key.columns:
                                pk_col = list(tbl_obj.primary_key.columns)[0].name
                            clean_h_col = f"COUNT({query.table}.{pk_col})"
                        elif "avg" in clean_h_col.lower():
                            clean_h_col = f"AVG({query.table}.base_salary)"
                        elif "sum" in clean_h_col.lower() or "total" in clean_h_col.lower():
                            clean_h_col = f"SUM({query.table}.base_salary)"
                    else:
                        clean_h_col = SchemaColumnResolver.qualify_column(clean_h_col, all_tbls, default_table=query.table)
                having_clauses.append(f"{clean_h_col} {op} {h.value}")
            if having_clauses:
                sql_parts.append("HAVING " + "\n  AND ".join(having_clauses))

        # ORDER BY
        order_str = self._build_order_clause(query.sort, query.columns, query.group_by, all_tbls, query.table)
        if order_str:
            sql_parts.append(order_str)

        # LIMIT
        if query.limit is not None:
            sql_parts.append(f"LIMIT {query.limit}")

        # OFFSET
        if query.offset is not None and query.offset > 0:
            sql_parts.append(f"OFFSET {query.offset}")

        final_sql = "\n".join(sql_parts) + ";"

        # Coerce parameter types based on SQLAlchemy column metadata
        if parameters:
            parameters = coerce_parameters(query.table, parameters, param_field_map)

        logger.info(f"Generated SQL:\n{final_sql}")
        if parameters:
            logger.debug(f"Parameters: {parameters}")

        return final_sql, parameters

    def _generate_ranking_sql(self, query: StructuredQuery) -> Tuple[str, Dict[str, Any]]:
        """Generates window function CTE SQL for N-th rank or Grouped/Partitioned ranking."""
        from app.query_builder.query_validator import _is_computed_expression
        import re

        # Step 1: Sanitize columns if unaggregated
        if not query.group_by and query.columns:
            new_cols = []
            for col in query.columns:
                c = col.strip()
                m = re.match(r'(?i)^(?:max|min|avg|sum)\((.+?)\)(?:\s+AS\s+(.+))?$', c)
                if m:
                    inner_expr = m.group(1).strip()
                    alias = m.group(2).strip() if m.group(2) else None
                    if alias and alias != inner_expr:
                        new_cols.append(f"{inner_expr} AS {alias}")
                    else:
                        new_cols.append(inner_expr)
                else:
                    new_cols.append(c)
            query.columns = new_cols

        # Step 2: Determine ordering
        order_col = None
        order_dir = "DESC"
        if query.ranking and query.ranking.order_by and query.ranking.order_by.field:
            order_col = query.ranking.order_by.field
            order_dir = query.ranking.order_by.direction.upper() if query.ranking.order_by.direction else "DESC"
            if query.ranking.order_by.table and "." not in order_col and not _is_computed_expression(order_col):
                order_col = f"{query.ranking.order_by.table}.{order_col}"
        elif query.window_function and query.window_function.order_by and query.window_function.order_by[0].field:
            o = query.window_function.order_by[0]
            order_col = o.field
            order_dir = o.direction.upper() if o.direction else "DESC"
            if o.table and "." not in order_col and not _is_computed_expression(order_col):
                order_col = f"{o.table}.{order_col}"
        elif query.sort and query.sort.field:
            order_col = query.sort.field
            order_dir = query.sort.direction.upper() if query.sort.direction else "DESC"
            if query.sort.table and "." not in order_col and not _is_computed_expression(order_col):
                order_col = f"{query.sort.table}.{order_col}"
        elif query.columns and len(query.columns) > 1:
            last_col = query.columns[-1].strip()
            as_m = re.search(r'(?i)(?:.+?\s+AS\s+)?([a-zA-Z0-9_.]+)$', last_col)
            if as_m:
                order_col = as_m.group(1).strip()
        
        if not order_col:
            from app.models import Base as _Base
            from app.ai.planner.planner_utils import SchemaDateColumnResolver, SchemaColumnResolver
            all_tbls = [query.table] + [j.table for j in (query.joins or [])]
            for t in all_tbls:
                tbl_obj = _Base.metadata.tables.get(t)
                if tbl_obj is not None:
                    for col in tbl_obj.columns:
                        if col.name not in ("id", "department_id", "office_id", "client_id", "employee_id", "created_at", "updated_at", "deleted_at") and not isinstance(col.type, (Date, DateTime)):
                            order_col = f"{t}.{col.name}"
                            break
                if order_col:
                    break
            if not order_col:
                for t in all_tbls:
                    date_col = SchemaDateColumnResolver.resolve(t)
                    if date_col:
                        order_col = f"{t}.{date_col}" if "." not in date_col else date_col
                        break
            if not order_col:
                order_col = f"{query.table}.id"
        else:
            from app.ai.planner.planner_utils import SchemaColumnResolver
            all_tbls = [query.table] + [j.table for j in (query.joins or [])]
            order_col = SchemaColumnResolver.qualify_column(order_col, all_tbls, default_table=query.table)
        
        if query.ranking and query.ranking.type == "bottom":
            order_dir = "ASC"

        # Step 3: Determine partitioning
        part_str = ""
        if query.ranking and query.ranking.partition_by and len(query.ranking.partition_by) > 0:
            from app.ai.planner.planner_utils import SchemaColumnResolver
            all_tbls = [query.table] + [j.table for j in (query.joins or [])]
            q_parts = [SchemaColumnResolver.qualify_column(p, all_tbls, default_table=query.table) for p in query.ranking.partition_by]
            part_str = "PARTITION BY " + ", ".join(q_parts) + " "

        # Step 4: Determine window function
        win_alias = "rank_num"
        if query.window_function:
            if not query.window_function.order_by and order_col:
                from app.ai.structured_output.schemas import SortCondition
                tbl_part, col_part = order_col.split(".", 1) if "." in order_col else (query.table, order_col)
                query.window_function.order_by = [SortCondition(table=tbl_part, field=col_part, direction=order_dir)]
            if not query.window_function.partition_by and query.ranking and query.ranking.partition_by:
                query.window_function.partition_by = list(query.ranking.partition_by)
            all_tbls = [query.table] + [j.table for j in (query.joins or [])]
            win_expr = self.compile_window_function(query.window_function, all_tbls, default_table=query.table)
            if query.window_function.alias:
                win_alias = query.window_function.alias
        else:
            win_func = "DENSE_RANK()" if (query.ranking and (query.ranking.dense_rank or query.ranking.type == "nth")) else "ROW_NUMBER()"
            win_expr = f"{win_func} OVER ({part_str}ORDER BY {order_col} {order_dir}) AS rank_num"
            win_alias = "rank_num"

        # Step 5 & Step 6: Build inner query clauses using shared SQL builders
        sql_parts = []
        parameters = {}
        param_field_map: Dict[str, tuple[str, str]] = {}
        param_counter = 1

        all_tbls = [query.table] + [j.table for j in (query.joins or [])]
        sql_parts.append(self._build_select_clause(query.columns or [], all_tbls, query.table, win_expr=win_expr))
        sql_parts.append(self._build_from_clause(query.table))
        sql_parts.extend(self._build_join_clause(query.joins))
        
        where_str, param_counter = self._build_where_clause(
            query.filters, all_tbls, query.table, param_counter, parameters, param_field_map
        )
        if where_str:
            sql_parts.append(where_str)
        if query.group_by:
            sql_parts.append("GROUP BY " + ", ".join(query.group_by))
        if query.having:
            alias_expr_map = {}
            for col_expr in query.columns:
                as_match = re.search(r'^(.+?)\s+AS\s+([a-zA-Z0-9_]+)\s*$', col_expr.strip(), re.IGNORECASE)
                if as_match:
                    alias_expr_map[as_match.group(2).strip().lower()] = as_match.group(1).strip()
            having_clauses = []
            for h in query.having:
                op = h.operator.strip()
                if op not in (">", "<", ">=", "<=", "=", "!="):
                    continue
                h_col = h.column.strip()
                as_m = re.search(r'^(.+?)\s+AS\s+\w+\s*$', h_col, re.IGNORECASE)
                clean_h_col = as_m.group(1).strip() if as_m else h_col
                if clean_h_col.lower() in alias_expr_map:
                    clean_h_col = alias_expr_map[clean_h_col.lower()]
                having_clauses.append(f"{clean_h_col} {op} {h.value}")
            if having_clauses:
                sql_parts.append("HAVING " + "\n  AND ".join(having_clauses))

        # Step 7: Build CTE and outer query
        inner_sql = "\n".join(sql_parts)
        indented_inner_sql = "\n    ".join(inner_sql.split("\n"))
        
        if query.ranking and query.ranking.type == "nth":
            outer_where = f"WHERE {win_alias} = {query.ranking.rank}"
        elif query.ranking and query.ranking.rank is not None:
            outer_where = f"WHERE {win_alias} <= {query.ranking.rank}"
        elif query.limit is not None:
            outer_where = f"WHERE {win_alias} <= {query.limit}"
        else:
            outer_where = ""

        if outer_where:
            final_sql = f"WITH ranked_data AS (\n    {indented_inner_sql}\n)\nSELECT *\nFROM ranked_data\n{outer_where};"
        else:
            final_sql = f"WITH ranked_data AS (\n    {indented_inner_sql}\n)\nSELECT *\nFROM ranked_data;"

        if parameters:
            parameters = coerce_parameters(query.table, parameters, param_field_map)

        logger.info(f"Generated Ranking SQL:\n{final_sql}")
        if parameters:
            logger.debug(f"Parameters: {parameters}")

        return final_sql, parameters
