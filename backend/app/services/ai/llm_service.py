import time
import logging
from typing import Any
from tenacity import retry, wait_exponential, stop_after_attempt
from langchain_core.messages import HumanMessage, BaseMessage
import groq

from app.core.llm import get_llm
from app.services.ai.token_service import TokenService
from app.services.ai.health_service import AIHealthService

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        try:
            self.llm = get_llm()
            self.token_service = TokenService()
        except Exception as e:
            logger.error(f"Failed to initialize LLMService: {str(e)}")
            raise

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def invoke(self, prompt: str | list[BaseMessage]) -> str:
        """Synchronously invoke the LLM with retry logic."""
        if isinstance(prompt, str):
            messages = [HumanMessage(content=prompt)]
        else:
            messages = prompt

        token_count = self.token_service.count_message_tokens(messages)
        logger.info(f"Invoking LLM (sync). Input tokens: ~{token_count}")
        start_time = time.time()

        try:
            response = self.llm.invoke(messages)
            execution_time = time.time() - start_time
            logger.info(f"LLM Response received in {execution_time:.2f}s")
            return response.content
        except groq.RateLimitError as e:
            logger.warning(f"Groq Rate limit hit: {e}. Retrying...")
            raise
        except groq.APIConnectionError as e:
            logger.error(f"Groq Connection failed: {e}. Retrying...")
            raise
        except groq.APITimeoutError as e:
            logger.error(f"Groq Timeout: {e}. Retrying...")
            raise
        except Exception as e:
            logger.error(f"LLM invocation failed: {str(e)}")
            raise

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    async def ainvoke(self, prompt: str | list[BaseMessage]) -> str:
        """Asynchronously invoke the LLM with retry logic."""
        if isinstance(prompt, str):
            messages = [HumanMessage(content=prompt)]
        else:
            messages = prompt

        token_count = self.token_service.count_message_tokens(messages)
        logger.info(f"Invoking LLM (async). Input tokens: ~{token_count}")
        start_time = time.time()

        try:
            response = await self.llm.ainvoke(messages)
            execution_time = time.time() - start_time
            logger.info(f"LLM Async Response received in {execution_time:.2f}s")
            return response.content
        except groq.RateLimitError as e:
            logger.warning(f"Groq Rate limit hit: {e}. Retrying...")
            raise
        except groq.APIConnectionError as e:
            logger.error(f"Groq Connection failed: {e}. Retrying...")
            raise
        except groq.APITimeoutError as e:
            logger.error(f"Groq Timeout: {e}. Retrying...")
            raise
        except Exception as e:
            logger.error(f"Async LLM invocation failed: {str(e)}")
            raise

    async def health_check(self) -> bool:
        return await AIHealthService.health_check()
