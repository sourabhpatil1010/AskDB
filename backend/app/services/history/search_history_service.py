import logging
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.history.search_history import SearchHistory
from app.models.auth.users import User

logger = logging.getLogger(__name__)

class SearchHistoryService:
    async def get_default_user_id(self, session: AsyncSession):
        result = await session.execute(select(User.id).limit(1))
        user_id = result.scalar_one_or_none()
        if not user_id:
            logger.warning("No users found in database for History saving. Using dummy UUID or failing.")
        return user_id

    async def save_history(self, session: AsyncSession, natural_language: str, structured_json: dict | None, generated_sql: str | None, execution_time_ms: int, status: str = "SUCCESS", error_message: str | None = None, row_count: int | None = None):
        try:
            user_id = await self.get_default_user_id(session)
            if not user_id:
                return

            history = SearchHistory(
                user_id=user_id,
                natural_language=natural_language,
                structured_json=structured_json,
                generated_sql=generated_sql,
                execution_time_ms=execution_time_ms,
                status=status,
                error_message=error_message,
                row_count=row_count
            )
            session.add(history)
            await session.commit()
            await session.refresh(history)
            logger.info(f"Saved search history {history.id}")
        except Exception as e:
            logger.error(f"Failed to save search history: {str(e)}")
            await session.rollback()

    async def get_all_history(self, session: AsyncSession):
        stmt = select(SearchHistory).order_by(SearchHistory.created_at.desc())
        result = await session.execute(stmt)
        return result.scalars().all()

    async def get_history_by_id(self, session: AsyncSession, history_id: str):
        stmt = select(SearchHistory).where(SearchHistory.id == history_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_history(self, session: AsyncSession, history_id: str):
        stmt = delete(SearchHistory).where(SearchHistory.id == history_id)
        await session.execute(stmt)
        await session.commit()

    async def delete_all_history(self, session: AsyncSession):
        stmt = delete(SearchHistory)
        await session.execute(stmt)
        await session.commit()
