import time
import logging
from app.ai.chains.json_chain import JSONGenerationChain
from app.ai.structured_output.schemas import StructuredQuery

logger = logging.getLogger(__name__)

class JSONService:
    def __init__(self):
        self.chain = JSONGenerationChain()

    async def process_query(self, query: str) -> StructuredQuery:
        start_time = time.time()
        logger.info(f"Processing natural language query to JSON: {query}")
        
        try:
            result = await self.chain.generate(query)
            
            execution_time = time.time() - start_time
            logger.info(f"JSON generated successfully in {execution_time:.2f}s")
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            import tenacity
            real_error = e.last_attempt.exception() if isinstance(e, tenacity.RetryError) else e
            logger.exception(f"Failed to process query in {execution_time:.2f}s: {str(real_error)}", exc_info=real_error)
            raise real_error from e
