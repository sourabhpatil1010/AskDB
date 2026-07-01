from fastapi import APIRouter
from app.api.v1.endpoints import search
from app.api.v1.endpoints import history
from app.api.v1.endpoints import llm_settings
from app.auth.router import auth_router, users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(history.router, prefix="/history", tags=["history"])
api_router.include_router(llm_settings.router, prefix="/llm", tags=["llm"])

