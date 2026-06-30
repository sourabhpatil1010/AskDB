import logging
from typing import Any

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama

from app.core.providers.base import LLMProvider

logger = logging.getLogger(__name__)

# Fallback models shown when Ollama discovery fails
OLLAMA_FALLBACK_MODELS = [
    "llama3:latest",
    "llama3:8b",
    "llama3.2:latest",
    "phi3:latest",
    "gemma4:31b-cloud",
]


class OllamaProvider(LLMProvider):
    """LLM provider backed by a local Ollama instance."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "llama3:latest",
        temperature: float = 0.0,
        timeout: int = 120,
    ):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.temperature = temperature
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return "Ollama"

    def get_llm(self, model: str | None = None) -> BaseChatModel:
        effective_model = model or self.default_model
        return ChatOllama(
            base_url=self.base_url,
            model=effective_model,
            temperature=self.temperature,
            timeout=self.timeout,
        )

    async def test_connection(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                model_count = len(data.get("models", []))
                return {
                    "connected": True,
                    "message": f"Ollama running – {model_count} model(s) installed",
                }
        except httpx.ConnectError:
            return {"connected": False, "message": "Ollama not running – connection refused"}
        except httpx.TimeoutException:
            return {"connected": False, "message": "Ollama connection timed out"}
        except Exception as e:
            logger.exception("Ollama connection test failed", exc_info=e)
            return {"connected": False, "message": f"Ollama connection failed: {str(e)}"}

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                if models:
                    return models
                logger.warning("Ollama returned 0 models – using fallback list")
                return list(OLLAMA_FALLBACK_MODELS)
        except Exception as e:
            logger.warning(f"Failed to discover Ollama models: {e} – using fallback list")
            return list(OLLAMA_FALLBACK_MODELS)
