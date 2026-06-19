from fastapi import APIRouter
from app.api.v1.endpoints import search
from app.api.v1.endpoints import history

api_router = APIRouter()
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(history.router, prefix="/history", tags=["history"])
