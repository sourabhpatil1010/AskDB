import logging
from abc import ABC, abstractmethod
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers.
    
    All providers must implement this interface so the rest of
    the application is completely agnostic to the underlying LLM backend.
    """

    @abstractmethod
    def get_llm(self, model: str | None = None) -> BaseChatModel:
        """Return a LangChain-compatible chat model instance.
        
        Args:
            model: Optional model override. If None, use the provider default.
        """
        ...

    @abstractmethod
    async def test_connection(self) -> dict[str, Any]:
        """Verify connectivity to the provider.
        
        Returns:
            A dict with at minimum ``{"connected": bool, "message": str}``.
        """
        ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        """Return available model identifiers from the provider."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name (e.g. 'Groq', 'Ollama')."""
        ...
