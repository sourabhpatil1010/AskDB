import asyncio
import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from app.core.providers.base import LLMProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

# Curated production-ready Groq chat models
GROQ_MODELS = [
    "qwen/qwen3-32b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b",
    "gemma2-9b-it",
]


class GroqProvider(LLMProvider):
    """LLM provider backed by the Groq cloud API."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "qwen/qwen3-32b",
        temperature: float = 0.0,
        max_tokens: int = 4096,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.default_model = default_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries

    @property
    def provider_name(self) -> str:
        return "Groq"

    def get_llm(self, model: str | None = None) -> BaseChatModel:
        effective_model = model or self.default_model
        if not self.api_key:
            raise ValueError("Missing GROQ_API_KEY – set it in .env or pass it explicitly.")
        return ChatGroq(
            api_key=self.api_key,
            model_name=effective_model,
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
                timeout=10.0,
            )
            if response and response.content:
                return {"connected": True, "message": "Connected to Groq"}
            return {"connected": False, "message": "Empty response from Groq"}
        except asyncio.TimeoutError:
            return {"connected": False, "message": "Connection to Groq timed out"}
        except Exception as e:
            logger.exception("Groq connection test failed", exc_info=e)
            return {"connected": False, "message": f"Groq connection failed: {str(e)}"}

    async def list_models(self) -> list[str]:
        return list(GROQ_MODELS)
