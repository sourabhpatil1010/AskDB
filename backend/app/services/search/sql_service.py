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
