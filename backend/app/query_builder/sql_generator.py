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
        sql_parts = []
        parameters = {}
        # Maps each parameter name -> (table, field) for type coercion
        param_field_map: Dict[str, tuple[str, str]] = {}
        param_counter = 1

        # SELECT
        columns_str = ", ".join(query.columns) if query.columns else "*"
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
                filter_table = f.table or query.table
                qual_field = f"{f.table}.{f.field}" if f.table else f.field
                param_name = f"{f.field.replace('(', '').replace(')', '')}_{param_counter}"
                if f.table:
                    param_name = f"{f.table}_{param_name}"
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
            sql_parts.append("GROUP BY " + ", ".join(query.group_by))

        # HAVING — aggregated condition filtering
        if query.having:
            having_clauses = []
            for h in query.having:
                op = h.operator.strip()
                # Validate operator to prevent injection
                if op not in (">", "<", ">=", "<=", "=", "!="):
                    logger.warning(f"Skipping HAVING with invalid operator: '{op}'")
                    continue
                # Value is always a numeric literal from the planner — safe to inline
                having_clauses.append(f"{h.column} {op} {h.value}")
            if having_clauses:
                sql_parts.append("HAVING " + "\n  AND ".join(having_clauses))

        # ORDER BY
        if query.sort:
            direction = query.sort.direction.upper()
            if direction not in ("ASC", "DESC"):
                direction = "ASC"
            qual_sort_field = f"{query.sort.table}.{query.sort.field}" if query.sort.table else query.sort.field
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
