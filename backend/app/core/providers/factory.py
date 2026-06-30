import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from app.core.providers.base import LLMProvider
from app.core.providers.groq_provider import GroqProvider
from app.core.providers.ollama_provider import OllamaProvider
from app.core.providers.openai_provider import OpenAIProvider
from app.core.providers.gemini_provider import GeminiProvider
from app.core.providers.anthropic_provider import AnthropicProvider
from app.core.providers.openrouter_provider import OpenRouterProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

# Canonical provider name → class mapping
_CLOUD_PROVIDERS = {
    "groq": GroqProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "anthropic": AnthropicProvider,
    "openrouter": OpenRouterProvider,
}

# Default model per provider
_DEFAULT_MODELS: dict[str, str] = {
    "groq": "qwen/qwen3-32b",
    "openai": "gpt-5",
    "gemini": "gemini-2.5-flash",
    "anthropic": "claude-sonnet-4",
    "openrouter": "deepseek/deepseek-r1",
    "ollama": "gemma4:31b-cloud ",
}


class ProviderFactory:
    """Singleton-ish factory that creates and caches LLM provider instances.

    The active provider / model / API key can be swapped at runtime via
    ``configure()``.  Every part of the application that needs an LLM must
    go through this factory – no provider-specific logic lives elsewhere.
    """

    _instance: "ProviderFactory | None" = None

    def __init__(self):
        # Defaults – cloud / Groq
        self._source: str = "cloud"           # "cloud" | "local"
        self._provider_name: str = "groq"     # one of the keys in _CLOUD_PROVIDERS or "ollama"
        self._model: str = _DEFAULT_MODELS["groq"]
        self._api_key: str = settings.GROQ_API_KEY
        self._ollama_base_url: str = "http://localhost:11434"
        self._provider: LLMProvider | None = None

    # ------------------------------------------------------------------
    # Singleton accessor
    # ------------------------------------------------------------------
    @classmethod
    def get_instance(cls) -> "ProviderFactory":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    def configure(
        self,
        source: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        ollama_base_url: str | None = None,
    ) -> dict[str, Any]:
        """Update the active configuration.  Returns the sanitised new state."""
        changed = False

        if source is not None and source != self._source:
            self._source = source
            changed = True

        if provider is not None and provider != self._provider_name:
            self._provider_name = provider
            changed = True
            # Reset to provider default model when switching providers
            if model is None:
                self._model = _DEFAULT_MODELS.get(provider, self._model)

        if model is not None and model != self._model:
            self._model = model
            changed = True

        # api_key=None means "don't change", api_key="" means "clear"
        if api_key is not None and api_key != self._api_key:
            self._api_key = api_key
            changed = True

        if ollama_base_url is not None and ollama_base_url != self._ollama_base_url:
            self._ollama_base_url = ollama_base_url
            changed = True

        if changed:
            # Invalidate cached provider so the next call re-creates it
            self._provider = None
            logger.info(
                f"Provider config changed → source={self._source}, "
                f"provider={self._provider_name}, model={self._model}, "
                f"ollama_url={self._ollama_base_url}"
            )

        return self.get_config()

    def get_config(self) -> dict[str, Any]:
        return {
            "source": self._source,
            "provider": self._provider_name,
            "model": self._model,
            "ollama_base_url": self._ollama_base_url,
            # Never expose raw api_key – return a masked version
            "api_key_set": bool(self._api_key),
        }

    # ------------------------------------------------------------------
    # Provider creation
    # ------------------------------------------------------------------
    def _build_provider(self) -> LLMProvider:
        if self._source == "local" or self._provider_name == "ollama":
            logger.info(f"Creating OllamaProvider (model={self._model}, url={self._ollama_base_url})")
            return OllamaProvider(
                base_url=self._ollama_base_url,
                default_model=self._model,
            )

        # Cloud provider
        provider_class = _CLOUD_PROVIDERS.get(self._provider_name)
        if provider_class is None:
            logger.warning(f"Unknown provider '{self._provider_name}', falling back to Groq")
            provider_class = GroqProvider

        logger.info(f"Creating {provider_class.__name__} (model={self._model})")
        return provider_class(
            api_key=self._api_key or None,
            default_model=self._model,
        )

    def get_provider(self) -> LLMProvider:
        if self._provider is None:
            self._provider = self._build_provider()
        return self._provider

    def get_llm(self) -> BaseChatModel:
        """Convenience: return a ready-to-use LangChain chat model."""
        return self.get_provider().get_llm(self._model)

    # ------------------------------------------------------------------
    # Helpers for the API layer
    # ------------------------------------------------------------------
    @staticmethod
    def build_temp_provider(
        source: str,
        provider_name: str,
        api_key: str = "",
        ollama_base_url: str = "http://localhost:11434",
        model: str = "",
    ) -> LLMProvider:
        """Build a throw-away provider for model-listing / connection-testing
        without touching the singleton configuration.
        """
        if source == "local" or provider_name == "ollama":
            return OllamaProvider(base_url=ollama_base_url, default_model=model or "llama3:latest")

        provider_class = _CLOUD_PROVIDERS.get(provider_name, GroqProvider)
        return provider_class(
            api_key=api_key or None,
            default_model=model or _DEFAULT_MODELS.get(provider_name, ""),
        )
