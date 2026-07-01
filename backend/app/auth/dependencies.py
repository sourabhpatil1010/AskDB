"""
FastAPI dependency for authenticated endpoints.

Usage:
    from app.auth.dependencies import get_current_user

    @router.get("/me")
    async def me(current_user: User = Depends(get_current_user)):
        ...
"""
import uuid
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import decode_access_token
from app.auth.repository import UserRepository
from app.database.session import get_db
from app.models.auth.users import User

logger = logging.getLogger(__name__)

# Points to the login endpoint so Swagger UI can auto-fill Bearer tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login/form")

_user_repo = UserRepository()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode the Bearer JWT and return the authenticated User ORM object.

    Raises 401 if token is missing, invalid, expired, or the user no longer
    exists / is inactive.
    """
    payload = decode_access_token(token)  # raises 401 on bad token

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await _user_repo.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    return user
