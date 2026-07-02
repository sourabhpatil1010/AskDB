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
        if query.columns:
            qual_cols = [SchemaColumnResolver.qualify_column(c, all_tbls, default_table=query.table) for c in query.columns]
            columns_str = ", ".join(qual_cols)
        else:
            columns_str = "*"
        sql_parts.append(f"SELECT\n    {columns_str}")

        # FROM
        sql_parts.append(f"FROM {query.table}")

        # JOINS
        if query.joins:
            for join in query.joins:
                sql_parts.append(f"JOIN {join.table} ON {join.on}")

        # WHERE
        if query.filters:
            where_clauses = []
            for f in query.filters:
                filter_table = SchemaColumnResolver.resolve_column_owner(f.field, all_tbls) or f.table or query.table
                qual_field = SchemaColumnResolver.qualify_column(f.field, all_tbls, default_table=query.table)
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

            sql_parts.append("WHERE " + "\n  AND ".join(where_clauses))

        # GROUP BY
        if query.group_by:
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
        if query.sort:
            direction = query.sort.direction.upper()
            if direction not in ("ASC", "DESC"):
                direction = "ASC"
            sort_field = query.sort.field.strip()
            
            # Check if sort_field matches an alias defined in SELECT columns
            is_alias = False
            import re
            for col_expr in query.columns:
                as_match = re.search(r'\bAS\s+([a-zA-Z0-9_]+)\s*$', col_expr.strip(), re.IGNORECASE)
                if as_match and as_match.group(1).lower() == sort_field.lower():
                    is_alias = True
                    break
            
            # If query is grouping, prevent ordering by raw unaggregated/ungrouped columns
            if query.group_by and not is_alias:
                from app.query_builder.query_validator import _is_computed_expression
                # Check if sort_field is already in group_by
                in_gb = any(sort_field.lower() == gb.lower() or sort_field.lower().endswith("." + gb.lower()) or gb.lower().endswith("." + sort_field.lower()) for gb in query.group_by)
                if not in_gb and not _is_computed_expression(sort_field):
                    for expr in query.columns:
                        as_m = re.search(r'^(.+?)(?:\s+AS\s+([a-zA-Z0-9_]+))?\s*$', expr.strip(), re.IGNORECASE)
                        full_expr = as_m.group(1).strip() if as_m else expr.strip()
                        alias = as_m.group(2).strip() if (as_m and as_m.group(2)) else None
                        if re.search(r'\b' + re.escape(sort_field) + r'\b', full_expr, re.IGNORECASE):
                            sort_field = alias if alias else full_expr
                            is_alias = bool(alias)
                            break

            # Check if sort_field is a valid column name in query.sort.table
            is_table_col = False
            if query.sort.table:
                from app.models import Base as _Base
                tbl_obj = _Base.metadata.tables.get(query.sort.table)
                if tbl_obj is not None and sort_field in [c.name for c in tbl_obj.columns]:
                    is_table_col = True
            
            from app.query_builder.query_validator import _is_computed_expression
            if is_alias or _is_computed_expression(sort_field) or "." in sort_field or not is_table_col:
                qual_sort_field = sort_field
            elif query.sort.table:
                qual_sort_field = SchemaColumnResolver.qualify_column(sort_field, [query.sort.table] + all_tbls, default_table=query.sort.table)
            else:
                qual_sort_field = SchemaColumnResolver.qualify_column(sort_field, all_tbls, default_table=query.table)
                
            sql_parts.append(f"ORDER BY {qual_sort_field} {direction}")

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
        if query.ranking.order_by and query.ranking.order_by.field:
            order_col = query.ranking.order_by.field
            order_dir = query.ranking.order_by.direction.upper() if query.ranking.order_by.direction else "DESC"
            if query.ranking.order_by.table and "." not in order_col and not _is_computed_expression(order_col):
                order_col = f"{query.ranking.order_by.table}.{order_col}"
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
        
        if query.ranking.type == "bottom":
            order_dir = "ASC"

        # Step 3: Determine partitioning
        part_str = ""
        if query.ranking.partition_by and len(query.ranking.partition_by) > 0:
            from app.ai.planner.planner_utils import SchemaColumnResolver
            all_tbls = [query.table] + [j.table for j in (query.joins or [])]
            q_parts = [SchemaColumnResolver.qualify_column(p, all_tbls, default_table=query.table) for p in query.ranking.partition_by]
            part_str = "PARTITION BY " + ", ".join(q_parts) + " "

        # Step 4: Determine window function
        win_func = "DENSE_RANK()" if (query.ranking.dense_rank or query.ranking.type == "nth") else "ROW_NUMBER()"
        win_expr = f"{win_func} OVER ({part_str}ORDER BY {order_col} {order_dir}) AS rank_num"

        # Step 5: Build inner SELECT columns
        from app.ai.planner.planner_utils import SchemaColumnResolver
        all_tbls = [query.table] + [j.table for j in (query.joins or [])]
        inner_cols = [SchemaColumnResolver.qualify_column(c, all_tbls, default_table=query.table) for c in query.columns] if query.columns else ["*"]
        inner_cols.append(win_expr)
        columns_str = ", ".join(inner_cols)

        # Step 6: Build inner query clauses
        sql_parts = []
        parameters = {}
        param_field_map: Dict[str, tuple[str, str]] = {}
        param_counter = 1

        sql_parts.append(f"SELECT\n    {columns_str}")
        sql_parts.append(f"FROM {query.table}")
        if query.joins:
            for join in query.joins:
                sql_parts.append(f"JOIN {join.table} ON {join.on}")
        if query.filters:
            where_clauses = []
            for f in query.filters:
                from app.ai.planner.planner_utils import SchemaColumnResolver
                all_tbls = [query.table] + [j.table for j in (query.joins or [])]
                filter_table = SchemaColumnResolver.resolve_column_owner(f.field, all_tbls) or f.table or query.table
                qual_field = SchemaColumnResolver.qualify_column(f.field, all_tbls, default_table=query.table)
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
            sql_parts.append("WHERE " + "\n  AND ".join(where_clauses))
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
        
        if query.ranking.type == "nth":
            outer_where = f"WHERE rank_num = {query.ranking.rank}"
        else:
            outer_where = f"WHERE rank_num <= {query.ranking.rank}"

        final_sql = f"WITH ranked_data AS (\n    {indented_inner_sql}\n)\nSELECT *\nFROM ranked_data\n{outer_where};"

        if parameters:
            parameters = coerce_parameters(query.table, parameters, param_field_map)

        logger.info(f"Generated Ranking SQL:\n{final_sql}")
        if parameters:
            logger.debug(f"Parameters: {parameters}")

        return final_sql, parameters
