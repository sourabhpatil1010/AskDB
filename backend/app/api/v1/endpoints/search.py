from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.services.ai.json_service import JSONService
from app.services.search.sql_service import SQLService
from app.services.search.query_service import QueryService
from app.services.search.search_pipeline import SearchPipeline

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Models ---
class SearchRequest(BaseModel):
    query: str

class SearchResponse(BaseModel):
    success: bool
    structured_json: dict | None = None
    error: str | None = None

class SQLRequest(BaseModel):
    structured_json: dict

class SQLResponse(BaseModel):
    success: bool
    sql: str | None = None
    parameters: dict | None = None
    error: str | None = None

class ExecuteRequest(BaseModel):
    sql: str
    parameters: dict

class ExecuteResponse(BaseModel):
    success: bool
    execution_time_ms: int = 0
    row_count: int = 0
    columns: list[str] = []
    rows: list[dict] = []
    error: str | None = None

class FullSearchRequest(BaseModel):
    query: str

class FullSearchResponse(BaseModel):
    success: bool
    question: str | None = None
    structured_json: dict | None = None
    generated_sql: str | None = None
    parameters: dict | None = None
    execution_time_ms: int = 0
    row_count: int = 0
    columns: list[str] = []
    rows: list[dict] = []
    error: str | None = None


# --- Dependencies ---
def get_json_service() -> JSONService:
    return JSONService()

def get_sql_service() -> SQLService:
    return SQLService()

def get_query_service() -> QueryService:
    return QueryService()

def get_search_pipeline() -> SearchPipeline:
    return SearchPipeline()


# --- Endpoints ---
@router.post("", response_model=FullSearchResponse)
async def full_search(
    request: FullSearchRequest,
    pipeline: SearchPipeline = Depends(get_search_pipeline),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await pipeline.run_pipeline(db, request.query)
        return FullSearchResponse(**result)
    except Exception as e:
        logger.exception(f"Search API Error (Full Pipeline): {str(e)}", exc_info=e)
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/json", response_model=SearchResponse)
async def generate_json(
    request: SearchRequest,
    service: JSONService = Depends(get_json_service)
):
    try:
        structured_query = await service.process_query(request.query)
        return SearchResponse(
            success=True,
            structured_json=structured_query.model_dump()
        )
    except Exception as e:
        logger.exception(f"Search API Error: {str(e)}", exc_info=e)
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/sql", response_model=SQLResponse)
async def generate_sql(
    request: SQLRequest,
    service: SQLService = Depends(get_sql_service)
):
    try:
        sql, parameters = service.build_sql(request.structured_json)
        return SQLResponse(
            success=True,
            sql=sql,
            parameters=parameters
        )
    except Exception as e:
        logger.exception(f"Search API Error (SQL Gen): {str(e)}", exc_info=e)
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/execute", response_model=ExecuteResponse)
async def execute_sql(
    request: ExecuteRequest,
    service: QueryService = Depends(get_query_service),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await service.execute_query(db, request.sql, request.parameters)
        return ExecuteResponse(**result)
    except ValueError as ve:
        logger.exception(f"Search API Error (SQL Execute Security): {str(ve)}", exc_info=ve)
        raise HTTPException(status_code=403, detail=str(ve))
    except Exception as e:
        logger.exception(f"Search API Error (SQL Execute): {str(e)}", exc_info=e)
        raise HTTPException(status_code=400, detail=str(e))
