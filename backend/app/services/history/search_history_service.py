import uuid
import logging
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.history.search_history import SearchHistory

logger = logging.getLogger(__name__)


class SearchHistoryService:
    """History CRUD scoped to the authenticated user.

    All write/read/delete operations require an explicit ``user_id`` so
    that no user can access another user's history.  The old
    ``get_default_user_id()`` helper has been removed.
    """

    async def save_history(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        natural_language: str,
        structured_json: dict | None,
        generated_sql: str | None,
        execution_time_ms: int,
        status: str = "SUCCESS",
        error_message: str | None = None,
        row_count: int | None = None,
    ) -> None:
        """Persist a search history entry for the given user."""
        try:
            history = SearchHistory(
                user_id=user_id,
                natural_language=natural_language,
                structured_json=structured_json,
                generated_sql=generated_sql,
                execution_time_ms=execution_time_ms,
                status=status,
                error_message=error_message,
                row_count=row_count,
            )
            session.add(history)
            await session.commit()
            await session.refresh(history)
            logger.info(f"Saved search history {history.id} for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to save search history: {str(e)}")
            await session.rollback()

    async def get_all_history(self, session: AsyncSession, user_id: uuid.UUID):
        """Return all history entries belonging to ``user_id``, newest first."""
        stmt = (
            select(SearchHistory)
            .where(SearchHistory.user_id == user_id)
            .order_by(SearchHistory.created_at.desc())
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    async def get_history_by_id(
        self, session: AsyncSession, history_id: str, user_id: uuid.UUID
    ):
        """Fetch a single history entry, enforcing ownership."""
        stmt = select(SearchHistory).where(
            SearchHistory.id == history_id,
            SearchHistory.user_id == user_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_history(
        self, session: AsyncSession, history_id: str, user_id: uuid.UUID
    ) -> None:
        """Delete one history entry, enforcing ownership."""
        stmt = delete(SearchHistory).where(
            SearchHistory.id == history_id,
            SearchHistory.user_id == user_id,
        )
        await session.execute(stmt)
        await session.commit()

    async def delete_all_history(
        self, session: AsyncSession, user_id: uuid.UUID
    ) -> None:
        """Delete all history entries for ``user_id``."""
        stmt = delete(SearchHistory).where(SearchHistory.user_id == user_id)
        await session.execute(stmt)
        await session.commit()
