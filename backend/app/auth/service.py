"""
Authentication business logic.
Orchestrates repository + security + JWT — no HTTP concerns here.
"""
import logging
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.repository import UserRepository
from app.auth.security import hash_password, verify_password
from app.auth.jwt import create_access_token
from app.core.config import settings
from app.models.auth.users import User

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self) -> None:
        self._repo = UserRepository()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    async def register(
        self,
        session: AsyncSession,
        *,
        email: str,
        password: str,
        full_name: str | None = None,
    ) -> User:
        """Register a new user.

        Raises:
            409 Conflict if email is already taken.
        """
        existing = await self._repo.get_by_email(session, email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )
        hashed = hash_password(password)
        return await self._repo.create(
            session, email=email, password_hash=hashed, full_name=full_name
        )

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def login(
        self,
        session: AsyncSession,
        *,
        email: str,
        password: str,
    ) -> str:
        """Authenticate a user and return a signed JWT access token.

        Raises:
            401 Unauthorized on bad credentials or inactive account.
        """
        _bad_creds = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

        user = await self._repo.get_by_email(session, email)
        if not user:
            raise _bad_creds
        if not verify_password(password, user.password_hash):
            raise _bad_creds
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled. Please contact support.",
            )

        token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        logger.info(f"User {user.id} authenticated successfully.")
        return token

    # ------------------------------------------------------------------
    # Profile update
    # ------------------------------------------------------------------

    async def update_profile(
        self,
        session: AsyncSession,
        user: User,
        *,
        full_name: str | None = None,
        password: str | None = None,
    ) -> User:
        """Update full_name and/or password for an authenticated user."""
        updates: dict = {}
        if full_name is not None:
            updates["full_name"] = full_name
        if password is not None:
            updates["password_hash"] = hash_password(password)

        if not updates:
            return user  # Nothing to change

        return await self._repo.update(session, user, **updates)
