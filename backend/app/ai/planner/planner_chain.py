import logging
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_not_exception_type

from app.core.llm import get_llm
from app.ai.planner.planner_schema import ExecutionPlan
from app.models import Base
from app.ai.planner.planner_utils import SYSTEM_TABLES

logger = logging.getLogger(__name__)


class PlannerChain:
    """LangChain integration for invoking LLM to generate an ExecutionPlan."""

    def __init__(self):
        try:
            self.llm = get_llm()
        except Exception as e:
            logger.warning(f"LLM initialization failed in PlannerChain ({e}). Will use fallback.")
            self.llm = None
        self.parser = PydanticOutputParser(pydantic_object=ExecutionPlan)
        
        # Format database schema info
        schema_lines = []
        for table_name, table in Base.metadata.tables.items():
            if table_name in SYSTEM_TABLES:
                continue
            col_strs = []
            for col in table.columns:
                if hasattr(col.type, 'enums') and col.type.enums:
                    col_strs.append(f"{col.name}[{'|'.join(col.type.enums)}]")
                else:
                    col_strs.append(col.name)
            cols = ", ".join(col_strs)
            pks = ", ".join([col.name for col in table.primary_key.columns])
            
            fks = []
            for fk in table.foreign_keys:
                fks.append(f"{fk.parent.name} -> {fk.column.table.name}.{fk.column.name}")
                
            schema_lines.append(f"- {table_name}: {cols}")
            if pks:
                schema_lines.append(f"  Primary Keys: {pks}")
            if fks:
                schema_lines.append(f"  Foreign Keys: {', '.join(fks)}")
        self.schema_info = "\n".join(schema_lines)

    def _load_prompt_text(self) -> str:
        """Loads planner prompt from planner_prompt.txt."""
        prompt_path = Path(__file__).parent / "planner_prompt.txt"
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read planner_prompt.txt from {prompt_path}: {e}")
            raise

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3), retry=retry_if_not_exception_type((RuntimeError, AttributeError, ValueError)))
    async def generate_plan(self, natural_language: str) -> ExecutionPlan:
        """Invokes LangChain chat model to generate a Pydantic-parsed ExecutionPlan."""
        logger.info(f"Invoking PlannerChain for query: '{natural_language}'")
        if not self.llm:
            raise RuntimeError("LLM not initialized or API key missing.")
        prompt_text = self._load_prompt_text()
        prompt_template = ChatPromptTemplate.from_template(prompt_text)
        
        messages = prompt_template.format_messages(
            schema_info=self.schema_info,
            query=natural_language,
            format_instructions=self.parser.get_format_instructions()
        )
        
        try:
            response = await self.llm.ainvoke(messages)
            plan = self.parser.parse(response.content)
            return plan
        except Exception as e:
            import tenacity
            real_error = e.last_attempt.exception() if isinstance(e, tenacity.RetryError) else e
            logger.exception(f"PlannerChain execution failed: {str(real_error)}", exc_info=real_error)
            raise real_error from e
