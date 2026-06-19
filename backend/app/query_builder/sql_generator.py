import logging
from typing import Tuple, Dict, Any
from app.ai.structured_output.schemas import StructuredQuery, OperatorEnum

logger = logging.getLogger(__name__)

class SQLGenerator:
    """
    Generates parameterized PostgreSQL queries from StructuredQuery objects.
    Uses SQLAlchemy's dialect for safe escaping or generates raw parameterized strings.
    We will generate raw parameterized strings with format :param_name for asyncpg.
    """
    def __init__(self):
        pass

    def generate(self, query: StructuredQuery) -> Tuple[str, Dict[str, Any]]:
        sql_parts = []
        parameters = {}
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
                elif op == "IN":
                    # For IN we need to dynamically generate parameters like (:param_1, :param_2)
                    in_params = []
                    for idx, val in enumerate(f.value):
                        p_name = f"{param_name}_{idx}"
                        in_params.append(f":{p_name}")
                        parameters[p_name] = val
                    in_str = ", ".join(in_params)
                    where_clauses.append(f"{qual_field} IN ({in_str})")
                else:
                    where_clauses.append(f"{qual_field} {op} :{param_name}")
                    parameters[param_name] = f.value
                
                param_counter += 1

            sql_parts.append("WHERE " + "\n  AND ".join(where_clauses))

        # GROUP BY
        if query.group_by:
            sql_parts.append("GROUP BY " + ", ".join(query.group_by))

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
        
        return final_sql, parameters
