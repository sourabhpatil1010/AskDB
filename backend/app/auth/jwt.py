"""
JWT creation and validation.
Uses python-jose with HS256 signing.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings

# Payload claim key for the subject (user id)
_SUBJECT_KEY = "sub"
_EXPIRY_KEY = "exp"


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token.

    Args:
        data: Payload dict. Must contain ``sub`` (subject / user id).
        expires_delta: Custom expiry. Defaults to settings.ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode[_EXPIRY_KEY] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token.

    Args:
        token: Raw Bearer token string.

    Returns:
        Decoded payload dict.

    Raises:
        HTTPException 401 on invalid or expired token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get(_SUBJECT_KEY) is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception
