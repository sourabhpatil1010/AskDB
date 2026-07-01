from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.database.session import get_db
from app.services.history.search_history_service import SearchHistoryService
from app.auth.dependencies import get_current_user
from app.models.auth.users import User

router = APIRouter()
logger = logging.getLogger(__name__)


def get_history_service():
    return SearchHistoryService()


@router.get("")
async def get_all_history(
    session: AsyncSession = Depends(get_db),
    service: SearchHistoryService = Depends(get_history_service),
    current_user: User = Depends(get_current_user),
):
    """Return all history entries for the authenticated user."""
    try:
        histories = await service.get_all_history(session, user_id=current_user.id)
        return {"success": True, "data": histories}
    except Exception as e:
        logger.exception(f"Error fetching history: {str(e)}", exc_info=e)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{id}")
async def get_history(
    id: str,
    session: AsyncSession = Depends(get_db),
    service: SearchHistoryService = Depends(get_history_service),
    current_user: User = Depends(get_current_user),
):
    """Return a single history entry owned by the authenticated user."""
    history = await service.get_history_by_id(session, id, user_id=current_user.id)
    if not history:
        raise HTTPException(status_code=404, detail="History not found")
    return {"success": True, "data": history}


@router.delete("")
async def delete_all_history(
    session: AsyncSession = Depends(get_db),
    service: SearchHistoryService = Depends(get_history_service),
    current_user: User = Depends(get_current_user),
):
    """Delete all history for the authenticated user."""
    await service.delete_all_history(session, user_id=current_user.id)
    return {"success": True}


@router.delete("/{id}")
async def delete_history(
    id: str,
    session: AsyncSession = Depends(get_db),
    service: SearchHistoryService = Depends(get_history_service),
    current_user: User = Depends(get_current_user),
):
    """Delete one history entry owned by the authenticated user."""
    await service.delete_history(session, id, user_id=current_user.id)
    return {"success": True}
