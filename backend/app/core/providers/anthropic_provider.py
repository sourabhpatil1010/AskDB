import asyncio
import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_anthropic import ChatAnthropic

from app.core.providers.base import LLMProvider

logger = logging.getLogger(__name__)

# Curated production-ready Anthropic Claude models
ANTHROPIC_MODELS = [
    "claude-opus-4",
    "claude-sonnet-4",
    "claude-haiku-4",
]


class AnthropicProvider(LLMProvider):
    """LLM provider backed by the Anthropic Claude API."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "claude-sonnet-4",
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
        return "Anthropic"

    def get_llm(self, model: str | None = None) -> BaseChatModel:
        effective_model = model or self.default_model
        if not self.api_key:
            raise ValueError("Missing Anthropic API key – provide it in Settings.")
        return ChatAnthropic(
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
                return {"connected": True, "message": "Connected to Anthropic"}
            return {"connected": False, "message": "Empty response from Anthropic"}
        except asyncio.TimeoutError:
            return {"connected": False, "message": "Connection to Anthropic timed out"}
        except ValueError as ve:
            return {"connected": False, "message": str(ve)}
        except Exception as e:
            msg = str(e)
            if "401" in msg or "authentication_error" in msg.lower():
                return {"connected": False, "message": "Invalid Anthropic API key (401)"}
            if "429" in msg or "rate_limit_error" in msg.lower() or "overloaded" in msg.lower():
                return {"connected": False, "message": "Anthropic rate limit / overloaded (429)"}
            if "403" in msg or "permission_error" in msg.lower():
                return {"connected": False, "message": "Anthropic access forbidden (403)"}
            logger.exception("Anthropic connection test failed", exc_info=e)
            return {"connected": False, "message": f"Anthropic connection failed: {msg}"}

    async def list_models(self) -> list[str]:
        return list(ANTHROPIC_MODELS)
