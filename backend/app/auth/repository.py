"""
Database repository for User CRUD operations.
Follows the Repository pattern — no business logic lives here.
"""
import uuid
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth.users import User

logger = logging.getLogger(__name__)


class UserRepository:
    """Thin data-access layer for the User model."""

    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        """Fetch a user by their email address (case-insensitive lookup)."""
        result = await session.execute(
            select(User).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, session: AsyncSession, user_id: uuid.UUID) -> User | None:
        """Fetch a user by their primary key UUID."""
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(
        self,
        session: AsyncSession,
        *,
        email: str,
        password_hash: str,
        full_name: str | None = None,
    ) -> User:
        """Persist a new user and return the ORM object."""
        user = User(
            email=email.lower().strip(),
            password_hash=password_hash,
            full_name=full_name,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info(f"Created new user: {user.id} ({user.email})")
        return user

    async def update(
        self,
        session: AsyncSession,
        user: User,
        **fields,
    ) -> User:
        """Apply field updates to an existing user and persist."""
        for key, value in fields.items():
            setattr(user, key, value)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
