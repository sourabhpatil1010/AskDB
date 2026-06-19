import logging
import tiktoken
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)

class TokenService:
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        # We use tiktoken for general approximation of tokens.
        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens for a given text."""
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.error(f"Error counting tokens: {str(e)}")
            return 0
            
    def count_message_tokens(self, messages: list[BaseMessage]) -> int:
        """Count tokens across a list of Langchain messages."""
        count = 0
        for msg in messages:
            count += self.count_tokens(str(msg.content))
        return count
