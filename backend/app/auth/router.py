"""
Auth & User API router.

Endpoints
---------
POST  /auth/register      — create account
POST  /auth/login         — get JWT access token (JSON body)
POST  /auth/login/form    — OAuth2 form login (for Swagger UI Bearer button)
POST  /auth/logout        — stateless; clears client-side token
GET   /auth/me            — current authenticated user
PUT   /users/profile      — update full_name / password
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import AuthService
from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.models.auth.users import User
from app.schemas.auth.auth_schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    UpdateProfileRequest,
)

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])


def _get_auth_service() -> AuthService:
    return AuthService()


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------

@auth_router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(_get_auth_service),
):
    user = await service.register(
        db, email=body.email, password=body.password, full_name=body.full_name
    )
    return UserResponse.model_validate(user)


# ---------------------------------------------------------------------------
# POST /auth/login  (JSON body — used by the React frontend)
# ---------------------------------------------------------------------------

@auth_router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive JWT access token",
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(_get_auth_service),
):
    token = await service.login(db, email=body.email, password=body.password)
    return TokenResponse(access_token=token)


# ---------------------------------------------------------------------------
# POST /auth/login/form  (OAuth2 form — used by Swagger UI)
# ---------------------------------------------------------------------------

@auth_router.post(
    "/login/form",
    response_model=TokenResponse,
    include_in_schema=False,  # Hide from public docs; only for Swagger Bearer button
)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(_get_auth_service),
):
    token = await service.login(db, email=form_data.username, password=form_data.password)
    return TokenResponse(access_token=token)


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------

@auth_router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout (client should discard the token)",
)
async def logout(_current_user: User = Depends(get_current_user)):
    """JWT is stateless. The client discards the token on logout.
    This endpoint exists so the frontend can call it cleanly and receive 200."""
    return {"message": "Logged out successfully."}


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

@auth_router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the currently authenticated user",
)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


# ---------------------------------------------------------------------------
# PUT /users/profile
# ---------------------------------------------------------------------------

@users_router.put(
    "/profile",
    response_model=UserResponse,
    summary="Update name and/or password",
)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(_get_auth_service),
):
    updated = await service.update_profile(
        db,
        current_user,
        full_name=body.full_name,
        password=body.password,
    )
    return UserResponse.model_validate(updated)
