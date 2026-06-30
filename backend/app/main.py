from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
import logging
from app.core.providers.factory import ProviderFactory

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    factory = ProviderFactory.get_instance()
    config = factory.get_config()
    logger.info(f"LLM Source: {config['source']}")
    logger.info(f"LLM Provider: {config['provider']}")
    logger.info(f"LLM Model: {config['model']}")

@app.get("/")
def root():
    return {"message": "Welcome to AskDB API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
