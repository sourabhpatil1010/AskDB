import time
import logging
from typing import Tuple, Dict, Any
from app.ai.structured_output.schemas import StructuredQuery
from app.query_builder.sql_generator import SQLGenerator
from app.query_builder.query_validator import QueryValidator

logger = logging.getLogger(__name__)

class SQLService:
    def __init__(self):
        self.generator = SQLGenerator()
        self.validator = QueryValidator()

    def build_sql(self, structured_json: dict) -> Tuple[str, Dict[str, Any]]:
        start_time = time.time()
        logger.info("Converting Structured JSON to SQL")
        
        try:
            # Parse dict back to Pydantic model
            query_obj = StructuredQuery(**structured_json)
            
            # Validate completely
            self.validator.validate(query_obj)
            
            # Generate Parameterized SQL
            sql_query, parameters = self.generator.generate(query_obj)
            
            from app.ai.planner.planner_utils import SchemaColumnResolver
            all_tables = [query_obj.table] + [j.table for j in (query_obj.joins or [])] if query_obj.table else []
            detected_cols = query_obj.columns or []
            resolved_owners = {col: SchemaColumnResolver.resolve_column_owner(col, all_tables) for col in detected_cols}
            qualified_cols = [SchemaColumnResolver.qualify_column(col, all_tables, default_table=query_obj.table) for col in detected_cols]
            join_path = [f"JOIN {j.table} ON {j.on}" for j in (query_obj.joins or [])]
            
            import re
            agg_types = []
            detected_metrics = []
            for col_expr in detected_cols:
                m = re.search(r'(?i)^(count|sum|avg|min|max)\((.+?)\)', col_expr.strip())
                if m:
                    op_name = m.group(1).upper()
                    if op_name not in agg_types:
                        agg_types.append(op_name)
                    inner_m = m.group(2).strip()
                    if inner_m not in detected_metrics:
                        detected_metrics.append(inner_m)
                else:
                    if col_expr.strip() not in detected_metrics:
                        detected_metrics.append(col_expr.strip())

            detected_intent = structured_json.get("intent", "AGGREGATION" if (query_obj.group_by or agg_types) else ("RANKING" if query_obj.ranking else "BASIC"))

            logger.info(
                f"\n=== DEBUG LOGGING ===\n"
                f"Detected intent: {detected_intent}\n"
                f"Aggregation type: {agg_types}\n"
                f"Detected metric: {detected_metrics}\n"
                f"Grouping field: {query_obj.group_by or []}\n"
                f"Resolved tables: {all_tables}\n"
                f"Resolved columns: {qualified_cols}\n"
                f"Join path: {join_path}\n"
                f"Validation result: VALID\n"
                f"Generated SQL:\n{sql_query}\n"
                f"====================="
            )
            
            execution_time = time.time() - start_time
            logger.info(f"SQL Generated in {execution_time:.4f}s")
            logger.debug(f"Generated SQL: {sql_query}")
            logger.debug(f"Parameters: {parameters}")
            
            return sql_query, parameters
            
        except ValueError as e:
            logger.exception(f"Validation error during SQL generation: {str(e)}", exc_info=e)
            raise
        except Exception as e:
            logger.exception(f"Failed to generate SQL: {str(e)}", exc_info=e)
            raise
