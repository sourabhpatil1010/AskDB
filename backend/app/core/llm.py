import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from langchain_groq import ChatGroq

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

def get_llm() -> ChatGroq:
    """Initialize and return the Groq LangChain model."""
    if not llm_settings.groq_api_key:
        logger.error("GROQ_API_KEY is missing from environment variables.")
        raise ValueError("Missing GROQ_API_KEY")
        
    try:
        llm = ChatGroq(
            api_key=llm_settings.groq_api_key,
            model_name=llm_settings.model_name,
            temperature=llm_settings.temperature,
            max_tokens=llm_settings.max_tokens,
            timeout=llm_settings.timeout,
            max_retries=llm_settings.max_retries
        )
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize ChatGroq: {str(e)}")
        raise
