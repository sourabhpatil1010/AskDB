import time
import logging
import traceback
from typing import Any
from tenacity import retry, wait_exponential, stop_after_attempt, RetryCallState
from langchain_core.messages import HumanMessage, BaseMessage

from app.core.llm import get_llm
from app.services.ai.health_service import AIHealthService

logger = logging.getLogger(__name__)


def _detect_provider_name() -> str:
    """Determine the active provider name from the factory."""
    try:
        from app.core.providers.factory import ProviderFactory
        return ProviderFactory.get_instance().get_provider().provider_name
    except Exception:
        return "Unknown"


def log_llm_error(retry_state: RetryCallState):
    e = retry_state.outcome.exception()
    if not e:
        return

    self_inst = retry_state.args[0] if retry_state.args else None
    model = getattr(getattr(self_inst, "llm", None), "model_name", None)
    if model is None:
        model = getattr(getattr(self_inst, "llm", None), "model", "Unknown")

    provider_name = _detect_provider_name()

    status_code = getattr(e, "status_code", "N/A")
    if status_code == "N/A" and hasattr(e, "response") and e.response:
        status_code = getattr(e.response, "status_code", "N/A")

    request_id = "N/A"
    if hasattr(e, "response") and e.response:
        if hasattr(e.response, "headers"):
            request_id = e.response.headers.get("x-request-id", "N/A")

    error_code = "N/A"
    body = getattr(e, "body", {})
    if isinstance(body, dict):
        err_dict = body.get("error", {})
        if isinstance(err_dict, dict):
            error_code = err_dict.get("code", "N/A")

    if error_code == "N/A" and hasattr(e, "code"):
        error_code = getattr(e, "code")

    stack_trace = "".join(traceback.format_exception(type(e), e, e.__traceback__))

    error_msg = f"""
------------------------------------------------
Model: {model}
HTTP Status: {status_code}
Provider: {provider_name}
Error Type: {type(e).__name__}
Error Code: {error_code}
Message: {str(e)}
Request ID: {request_id}
Stack Trace:
{stack_trace}
Retry Attempt: {retry_state.attempt_number} of 3
------------------------------------------------
"""
    logger.error(error_msg)


class LLMService:
    def __init__(self):
        try:
            self.llm = get_llm()
        except Exception as e:
            logger.exception(f"Failed to initialize LLMService: {str(e)}", exc_info=e)
            raise

    def _get_model_name(self) -> str:
        return getattr(self.llm, "model_name", None) or getattr(self.llm, "model", "Unknown")

    def _log_pre_request(self):
        provider_name = _detect_provider_name()
        logger.info(
            f"LLM Request -> Model: {self._get_model_name()} | "
            f"Provider: {provider_name} | "
            f"Temp: {getattr(self.llm, 'temperature', 'N/A')} | "
            f"MaxTokens: {getattr(self.llm, 'max_tokens', 'N/A')} | "
            f"Timeout: {getattr(self.llm, 'timeout', 'N/A')}"
        )

    def _log_post_request(self, latency: float, success: bool, response: Any = None):
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0

        if success and response and hasattr(response, "response_metadata"):
            token_usage = response.response_metadata.get("token_usage", {})
            if token_usage:
                input_tokens = token_usage.get("prompt_tokens", 0)
                output_tokens = token_usage.get("completion_tokens", 0)
                total_tokens = token_usage.get("total_tokens", 0)

        status_str = "Success" if success else "Failure"
        logger.info(
            f"LLM Response -> Latency: {latency:.2f}s | "
            f"Status: {status_str} | "
            f"Input Tokens: {input_tokens} | "
            f"Output Tokens: {output_tokens} | "
            f"Total Tokens: {total_tokens}"
        )

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3), after=log_llm_error)
    def invoke(self, prompt: str | list[BaseMessage]) -> str:
        """Synchronously invoke the LLM with retry logic."""
        if isinstance(prompt, str):
            messages = [HumanMessage(content=prompt)]
        else:
            messages = prompt

        self._log_pre_request()
        start_time = time.time()

        try:
            response = self.llm.invoke(messages)
            latency = time.time() - start_time
            self._log_post_request(latency, True, response)
            return response.content
        except Exception as e:
            latency = time.time() - start_time
            self._log_post_request(latency, False)
            raise

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3), after=log_llm_error)
    async def ainvoke(self, prompt: str | list[BaseMessage]) -> str:
        """Asynchronously invoke the LLM with retry logic."""
        if isinstance(prompt, str):
            messages = [HumanMessage(content=prompt)]
        else:
            messages = prompt

        self._log_pre_request()
        start_time = time.time()

        try:
            response = await self.llm.ainvoke(messages)
            latency = time.time() - start_time
            self._log_post_request(latency, True, response)
            return response.content
        except Exception as e:
            latency = time.time() - start_time
            self._log_post_request(latency, False)
            raise

    async def health_check(self) -> bool:
        return await AIHealthService.health_check()
