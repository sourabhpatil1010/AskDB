from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any
import logging

from app.core.providers.factory import ProviderFactory

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class LLMConfigRequest(BaseModel):
    """Full or partial runtime configuration update."""
    source: str | None = None           # "cloud" | "local"
    provider: str | None = None         # "groq" | "openai" | "gemini" | "anthropic" | "openrouter" | "ollama"
    model: str | None = None
    api_key: str | None = None          # Cloud API key (never persisted server-side)
    ollama_base_url: str | None = None


class LLMConfigResponse(BaseModel):
    source: str
    provider: str
    model: str
    ollama_base_url: str
    api_key_set: bool = False


class ConnectionTestRequest(BaseModel):
    """Payload for an ad-hoc connection test without changing the active config."""
    source: str = "cloud"
    provider: str = "groq"
    model: str = ""
    api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"


class ConnectionTestResponse(BaseModel):
    connected: bool
    message: str


class ModelsRequest(BaseModel):
    """Payload for on-demand model listing."""
    source: str = "cloud"
    provider: str = "groq"
    api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"


class ModelsResponse(BaseModel):
    models: list[str]
    provider: str


# ---------------------------------------------------------------------------
# GET /config — current active configuration
# ---------------------------------------------------------------------------

@router.get("/config", response_model=LLMConfigResponse)
async def get_config():
    """Return the current LLM provider configuration (api_key is never returned)."""
    factory = ProviderFactory.get_instance()
    cfg = factory.get_config()
    return LLMConfigResponse(
        source=cfg["source"],
        provider=cfg["provider"],
        model=cfg["model"],
        ollama_base_url=cfg["ollama_base_url"],
        api_key_set=cfg["api_key_set"],
    )


# ---------------------------------------------------------------------------
# PUT /config — update active configuration
# ---------------------------------------------------------------------------

@router.put("/config", response_model=LLMConfigResponse)
async def update_config(request: LLMConfigRequest):
    """Update the active LLM provider / model / API key at runtime.

    The api_key is held only in memory for the lifetime of the server process.
    It is *never* written to the database.
    """
    factory = ProviderFactory.get_instance()
    new_config = factory.configure(
        source=request.source,
        provider=request.provider,
        model=request.model,
        api_key=request.api_key,
        ollama_base_url=request.ollama_base_url,
    )
    logger.info(
        f"LLM config updated: source={new_config['source']}, "
        f"provider={new_config['provider']}, model={new_config['model']}"
    )
    return LLMConfigResponse(
        source=new_config["source"],
        provider=new_config["provider"],
        model=new_config["model"],
        ollama_base_url=new_config["ollama_base_url"],
        api_key_set=new_config["api_key_set"],
    )


# ---------------------------------------------------------------------------
# POST /test-connection — test active provider
# ---------------------------------------------------------------------------

@router.post("/test-connection", response_model=ConnectionTestResponse)
async def test_connection():
    """Test connectivity using the currently-active provider."""
    factory = ProviderFactory.get_instance()
    provider = factory.get_provider()
    result = await provider.test_connection()
    return ConnectionTestResponse(**result)


# ---------------------------------------------------------------------------
# POST /test-connection/probe — ad-hoc connection test (no config change)
# ---------------------------------------------------------------------------

@router.post("/test-connection/probe", response_model=ConnectionTestResponse)
async def test_connection_probe(request: ConnectionTestRequest):
    """Test a provider connection without changing the active configuration.

    The frontend sends provider / api_key / model so we can validate before
    saving.  Nothing is persisted on the server.
    """
    try:
        provider = ProviderFactory.build_temp_provider(
            source=request.source,
            provider_name=request.provider,
            api_key=request.api_key,
            ollama_base_url=request.ollama_base_url,
            model=request.model,
        )
        result = await provider.test_connection()
        return ConnectionTestResponse(**result)
    except Exception as e:
        return ConnectionTestResponse(connected=False, message=str(e))


# ---------------------------------------------------------------------------
# POST /models — list models for a given provider (ad-hoc, no config change)
# ---------------------------------------------------------------------------

@router.post("/models", response_model=ModelsResponse)
async def list_models_for_provider(request: ModelsRequest):
    """Return available models for the given provider.

    Uses a temporary (ephemeral) provider instance so the active config is
    never mutated.
    """
    try:
        provider = ProviderFactory.build_temp_provider(
            source=request.source,
            provider_name=request.provider,
            api_key=request.api_key,
            ollama_base_url=request.ollama_base_url,
        )
        models = await provider.list_models()
        return ModelsResponse(models=models, provider=provider.provider_name)
    except Exception as e:
        logger.exception(f"Failed to list models for provider '{request.provider}'", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# GET /models — legacy endpoint (lists models for active provider)
# ---------------------------------------------------------------------------

@router.get("/models", response_model=ModelsResponse)
async def list_models_active(source: str | None = None):
    """Legacy: list models for the currently active (or a source-specific) provider.

    Kept for backward compatibility – the UI now uses POST /models instead.
    """
    factory = ProviderFactory.get_instance()
    config = factory.get_config()
    effective_source = source or config["source"]

    provider = ProviderFactory.build_temp_provider(
        source=effective_source,
        provider_name=config["provider"] if effective_source == config["source"] else (
            "ollama" if effective_source == "local" else "groq"
        ),
        api_key="",
        ollama_base_url=config["ollama_base_url"],
    )
    models = await provider.list_models()
    return ModelsResponse(models=models, provider=provider.provider_name)


# ---------------------------------------------------------------------------
# POST /test-connection/{source} — legacy per-source test
# ---------------------------------------------------------------------------

@router.post("/test-connection/{source}", response_model=ConnectionTestResponse)
async def test_connection_for_source(source: str):
    """Legacy: test connectivity for a specific source without changing config."""
    factory = ProviderFactory.get_instance()
    config = factory.get_config()

    if source not in ("local", "cloud"):
        raise HTTPException(status_code=400, detail=f"Unknown source: {source}")

    provider = ProviderFactory.build_temp_provider(
        source=source,
        provider_name="ollama" if source == "local" else config["provider"],
        api_key="" if source == "local" else "",
        ollama_base_url=config["ollama_base_url"],
    )
    result = await provider.test_connection()
    return ConnectionTestResponse(**result)
