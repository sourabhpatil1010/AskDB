import asyncio
import logging
from typing import Any

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.core.providers.base import LLMProvider

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

# Sensible default models for OpenRouter
OPENROUTER_FALLBACK_MODELS = [
    "deepseek/deepseek-r1",
    "deepseek/deepseek-chat",
    "meta-llama/llama-3.3-70b-instruct",
    "meta-llama/llama-3.1-8b-instruct",
    "mistralai/mistral-7b-instruct",
    "qwen/qwen-2.5-72b-instruct",
    "google/gemini-flash-1.5",
    "anthropic/claude-3.5-sonnet",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
]


class OpenRouterProvider(LLMProvider):
    """LLM provider backed by OpenRouter (multi-model cloud gateway).

    OpenRouter exposes an OpenAI-compatible API so we reuse ``ChatOpenAI``
    with a custom ``base_url``.
    """

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "deepseek/deepseek-r1",
        temperature: float = 0.0,
        max_tokens: int = 4096,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.api_key = api_key or ""
        self.default_model = default_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries

    @property
    def provider_name(self) -> str:
        return "OpenRouter"

    def get_llm(self, model: str | None = None) -> BaseChatModel:
        effective_model = model or self.default_model
        if not self.api_key:
            raise ValueError("Missing OpenRouter API key – provide it in Settings.")
        return ChatOpenAI(
            api_key=self.api_key,
            base_url=OPENROUTER_BASE_URL,
            model=effective_model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
            max_retries=self.max_retries,
            default_headers={
                "HTTP-Referer": "https://askdb.app",
                "X-Title": "AskDB",
            },
        )

    async def test_connection(self) -> dict[str, Any]:
        try:
            llm = self.get_llm()
            response = await asyncio.wait_for(
                llm.ainvoke([HumanMessage(content="Ping. Reply with 'Pong'.")]),
                timeout=15.0,
            )
            if response and response.content:
                return {"connected": True, "message": "Connected to OpenRouter"}
            return {"connected": False, "message": "Empty response from OpenRouter"}
        except asyncio.TimeoutError:
            return {"connected": False, "message": "Connection to OpenRouter timed out"}
        except ValueError as ve:
            return {"connected": False, "message": str(ve)}
        except Exception as e:
            msg = str(e)
            if "401" in msg or "invalid_api_key" in msg.lower():
                return {"connected": False, "message": "Invalid OpenRouter API key (401)"}
            if "429" in msg or "rate_limit" in msg.lower():
                return {"connected": False, "message": "OpenRouter rate limit exceeded (429)"}
            if "403" in msg:
                return {"connected": False, "message": "OpenRouter access forbidden (403)"}
            logger.exception("OpenRouter connection test failed", exc_info=e)
            return {"connected": False, "message": f"OpenRouter connection failed: {msg}"}

    async def list_models(self) -> list[str]:
        """Fetch available models from OpenRouter's /models endpoint.

        Falls back to a curated static list on error so the UI is never empty.
        """
        if not self.api_key:
            return list(OPENROUTER_FALLBACK_MODELS)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    OPENROUTER_MODELS_URL,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                resp.raise_for_status()
                data = resp.json()
                models = [m["id"] for m in data.get("data", []) if m.get("id")]
                if models:
                    # Sort and return top 50 to keep the dropdown manageable
                    return sorted(models)[:50]
        except Exception as e:
            logger.warning(f"Failed to discover OpenRouter models: {e} – using fallback list")
        return list(OPENROUTER_FALLBACK_MODELS)
