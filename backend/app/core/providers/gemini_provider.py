import asyncio
import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.providers.base import LLMProvider

logger = logging.getLogger(__name__)

# Curated production-ready Google Gemini chat models
GEMINI_MODELS = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]


class GeminiProvider(LLMProvider):
    """LLM provider backed by the Google Gemini (Generative AI) cloud API."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "gemini-2.5-flash",
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
        return "Google Gemini"

    def get_llm(self, model: str | None = None) -> BaseChatModel:
        effective_model = model or self.default_model
        if not self.api_key:
            raise ValueError("Missing Google Gemini API key – provide it in Settings.")
        return ChatGoogleGenerativeAI(
            google_api_key=self.api_key,
            model=effective_model,
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
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
                return {"connected": True, "message": "Connected to Google Gemini"}
            return {"connected": False, "message": "Empty response from Google Gemini"}
        except asyncio.TimeoutError:
            return {"connected": False, "message": "Connection to Google Gemini timed out"}
        except ValueError as ve:
            return {"connected": False, "message": str(ve)}
        except Exception as e:
            msg = str(e)
            if "401" in msg or "API_KEY_INVALID" in msg or "invalid" in msg.lower() and "key" in msg.lower():
                return {"connected": False, "message": "Invalid Google Gemini API key (401)"}
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                return {"connected": False, "message": "Google Gemini quota exceeded (429)"}
            if "403" in msg or "PERMISSION_DENIED" in msg:
                return {"connected": False, "message": "Google Gemini access forbidden (403)"}
            logger.exception("Google Gemini connection test failed", exc_info=e)
            return {"connected": False, "message": f"Google Gemini connection failed: {msg}"}

    async def list_models(self) -> list[str]:
        return list(GEMINI_MODELS)
