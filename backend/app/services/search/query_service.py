import time
import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.query_builder.query_executor import QueryExecutor

logger = logging.getLogger(__name__)

class QueryService:
    def __init__(self):
        self.executor = QueryExecutor()

    async def execute_query(self, session: AsyncSession, sql: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        logger.info(f"Executing SQL query. Parameters: {parameters}")
        
        try:
            rows = await self.executor.execute(session, sql, parameters)
            
            execution_time_ms = int((time.perf_counter() - start_time) * 1000)
            row_count = len(rows)
            
            columns = list(rows[0].keys()) if row_count > 0 else []
            
            logger.info(f"SQL execution completed in {execution_time_ms}ms. Rows returned: {row_count}")
            
            return {
                "success": True,
                "execution_time_ms": execution_time_ms,
                "row_count": row_count,
                "columns": columns,
                "rows": rows
            }
            
        except ValueError as e:
            execution_time_ms = int((time.perf_counter() - start_time) * 1000)
            logger.exception(f"Unsafe query error in {execution_time_ms}ms: {str(e)}", exc_info=e)
            raise
        except Exception as e:
            execution_time_ms = int((time.perf_counter() - start_time) * 1000)
            logger.exception(f"SQL execution error in {execution_time_ms}ms: {str(e)}", exc_info=e)
            raise
