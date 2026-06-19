import logging
import asyncio
from app.core.llm import get_llm
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

class AIHealthService:
    @staticmethod
    async def health_check() -> bool:
        """Check if Groq LLM is reachable and responding correctly."""
        try:
            llm = get_llm()
            messages = [HumanMessage(content="Ping. Reply with 'Pong'.")]
            response = await asyncio.wait_for(llm.ainvoke(messages), timeout=5.0)
            
            if response and response.content:
                logger.info("AI Health check passed.")
                return True
            return False
        except asyncio.TimeoutError:
            logger.error("AI Health check timed out.")
            return False
        except Exception as e:
            logger.error(f"AI Health check failed: {str(e)}")
            return False
