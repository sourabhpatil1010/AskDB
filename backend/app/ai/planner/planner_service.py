import time
import logging
from app.ai.planner.planner import AIQueryPlanner
from app.ai.planner.planner_schema import ExecutionPlan, PlannerClarificationException

logger = logging.getLogger(__name__)


class PlannerService:
    """Service layer facade for AI Query Planner."""

    def __init__(self):
        self.planner = AIQueryPlanner()

    async def create_plan(self, query: str) -> ExecutionPlan:
        start_time = time.time()
        logger.info(f"Generating execution plan for query: '{query}'")
        try:
            plan = await self.planner.plan(query)
            execution_time = time.time() - start_time
            logger.info(f"Execution plan generated successfully in {execution_time:.2f}s (Intent: {plan.intent}, Confidence: {plan.confidence:.2f})")
            return plan
        except PlannerClarificationException as ce:
            execution_time = time.time() - start_time
            logger.warning(f"Planner clarification requested in {execution_time:.2f}s: {ce}")
            raise
        except Exception as e:
            execution_time = time.time() - start_time
            import tenacity
            real_error = e.last_attempt.exception() if isinstance(e, tenacity.RetryError) else e
            logger.exception(f"Failed to generate execution plan in {execution_time:.2f}s: {str(real_error)}", exc_info=real_error)
            raise real_error from e
