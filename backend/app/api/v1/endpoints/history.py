from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any
import logging

from app.database.session import get_db
from app.services.history.search_history_service import SearchHistoryService

router = APIRouter()
logger = logging.getLogger(__name__)

def get_history_service():
    return SearchHistoryService()

@router.get("")
async def get_all_history(
    session: AsyncSession = Depends(get_db),
    service: SearchHistoryService = Depends(get_history_service)
):
    try:
        histories = await service.get_all_history(session)
        return {"success": True, "data": histories}
    except Exception as e:
        logger.exception(f"Error fetching history: {str(e)}", exc_info=e)
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{id}")
async def get_history(
    id: str,
    session: AsyncSession = Depends(get_db),
    service: SearchHistoryService = Depends(get_history_service)
):
    history = await service.get_history_by_id(session, id)
    if not history:
        raise HTTPException(status_code=404, detail="History not found")
    return {"success": True, "data": history}

@router.delete("")
async def delete_all_history(
    session: AsyncSession = Depends(get_db),
    service: SearchHistoryService = Depends(get_history_service)
):
    await service.delete_all_history(session)
    return {"success": True}

@router.delete("/{id}")
async def delete_history(
    id: str,
    session: AsyncSession = Depends(get_db),
    service: SearchHistoryService = Depends(get_history_service)
):
    await service.delete_history(session, id)
    return {"success": True}
