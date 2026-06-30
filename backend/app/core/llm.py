import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)


class LLMSettings(BaseSettings):
    groq_api_key: str = ""
    model_name: str = "qwen/qwen3-32b"
    temperature: float = 0.0
    max_tokens: int = 4096
    timeout: int = 30
    max_retries: int = 3

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


llm_settings = LLMSettings()


def get_llm() -> BaseChatModel:
    """Return the active LLM instance via the ProviderFactory.

    All call-sites that previously imported ``get_llm`` continue to work
    without changes — but now the underlying provider and model are
    determined by the runtime configuration in ProviderFactory.
    """
    from app.core.providers.factory import ProviderFactory
    return ProviderFactory.get_instance().get_llm()
