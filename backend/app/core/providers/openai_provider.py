import asyncio
import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.core.providers.base import LLMProvider

logger = logging.getLogger(__name__)

# Curated production-ready OpenAI chat models
OPENAI_MODELS = [
    "gpt-5",
    "gpt-5-mini",
    "gpt-4.1",
    "gpt-4.1-mini",
]


class OpenAIProvider(LLMProvider):
    """LLM provider backed by the OpenAI cloud API."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "gpt-4o",
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
        return "OpenAI"

    def get_llm(self, model: str | None = None) -> BaseChatModel:
        effective_model = model or self.default_model
        if not self.api_key:
            raise ValueError("Missing OpenAI API key – provide it in Settings.")
        return ChatOpenAI(
            api_key=self.api_key,
            model=effective_model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

    async def test_connection(self) -> dict[str, Any]:
        try:
            llm = self.get_llm()
            response = await asyncio.wait_for(
                llm.ainvoke([HumanMessage(content="Ping. Reply with 'Pong'.")]),
                timeout=15.0,
            )
            if response and response.content:
                return {"connected": True, "message": "Connected to OpenAI"}
            return {"connected": False, "message": "Empty response from OpenAI"}
        except asyncio.TimeoutError:
            return {"connected": False, "message": "Connection to OpenAI timed out"}
        except ValueError as ve:
            return {"connected": False, "message": str(ve)}
        except Exception as e:
            msg = str(e)
            if "401" in msg or "invalid_api_key" in msg.lower() or "Incorrect API key" in msg:
                return {"connected": False, "message": "Invalid OpenAI API key (401)"}
            if "429" in msg or "rate_limit" in msg.lower():
                return {"connected": False, "message": "OpenAI rate limit exceeded (429)"}
            if "403" in msg:
                return {"connected": False, "message": "OpenAI access forbidden (403)"}
            logger.exception("OpenAI connection test failed", exc_info=e)
            return {"connected": False, "message": f"OpenAI connection failed: {msg}"}

    async def list_models(self) -> list[str]:
        return list(OPENAI_MODELS)
