import time
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.services.ai.json_service import JSONService
from app.services.search.sql_service import SQLService
from app.services.search.query_service import QueryService

logger = logging.getLogger(__name__)

class SearchPipeline:
    def __init__(self):
        self.json_service = JSONService()
        self.sql_service = SQLService()
        self.query_service = QueryService()

    def _map_exception_to_status(self, e: Exception) -> str:
        name = type(e).__name__
        if "RateLimit" in name:
            return "RATE_LIMIT"
        if "Validation" in name or "Pydantic" in name:
            return "VALIDATION_ERROR"
        if "SQL" in name or "ProgrammingError" in name:
            return "SQL_ERROR"
        if "Database" in name or "OperationalError" in name or "InterfaceError" in name:
            return "DATABASE_ERROR"
        if "Timeout" in name:
            return "TIMEOUT"
        return "UNKNOWN_ERROR"

    async def run_pipeline(self, session: AsyncSession, natural_language: str) -> Dict[str, Any]:
        pipeline_start = time.perf_counter()
        logger.info(f"--- Starting Search Pipeline for: '{natural_language}' ---")
        
        structured_json = None
        sql = None
        parameters = None
        db_result = None
        status = "SUCCESS"
        error_message = None
        row_count = None
        execution_time_ms = 0
        
        from app.services.history.search_history_service import SearchHistoryService
        history_service = SearchHistoryService()
        
        try:
            # 1. Natural Language -> Structured JSON (includes JSON validation)
            structured_query = await self.json_service.process_query(natural_language)
            structured_json = structured_query.model_dump()
            
            # 2. Structured JSON -> Parameterized SQL (includes SQL validation & parameter generation)
            sql, parameters = self.sql_service.build_sql(structured_json)
            
            # 3. SQL Execution -> Results (includes execution time, safe execution check)
            db_result = await self.query_service.execute_query(session, sql, parameters)
            
            row_count = db_result["row_count"]
            execution_time_ms = db_result["execution_time_ms"]
            
            total_execution_time_ms = int((time.perf_counter() - pipeline_start) * 1000)
            logger.info(f"--- Pipeline Completed Successfully in {total_execution_time_ms}ms ---")
            
            # 5. Construct Final Response
            return {
                "success": True,
                "question": natural_language,
                "structured_json": structured_json,
                "generated_sql": sql,
                "parameters": parameters,
                "execution_time_ms": execution_time_ms,
                "row_count": row_count,
                "columns": db_result["columns"],
                "rows": db_result["rows"]
            }
            
        except Exception as e:
            total_execution_time_ms = int((time.perf_counter() - pipeline_start) * 1000)
            execution_time_ms = total_execution_time_ms
            logger.error(f"--- Pipeline Failed in {total_execution_time_ms}ms: {str(e)} ---")
            status = self._map_exception_to_status(e)
            error_message = str(e)
            raise
        finally:
            # 4. Auto-save search history
            try:
                if execution_time_ms == 0:
                    execution_time_ms = int((time.perf_counter() - pipeline_start) * 1000)
                await history_service.save_history(
                    session=session,
                    natural_language=natural_language,
                    structured_json=structured_json,
                    generated_sql=sql,
                    execution_time_ms=execution_time_ms,
                    status=status,
                    error_message=error_message,
                    row_count=row_count
                )
            except Exception as e:
                logger.error(f"Failed to save search history in finally block: {str(e)}")
