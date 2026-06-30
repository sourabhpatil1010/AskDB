import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from tenacity import retry, wait_exponential, stop_after_attempt

from app.core.llm import get_llm
from app.ai.structured_output.schemas import StructuredQuery
from app.query_builder.query_validator import QueryValidator
from app.services.ai.prompt_service import PromptService
from app.models import Base

logger = logging.getLogger(__name__)

class JSONGenerationChain:
    def __init__(self):
        self.llm = get_llm()
        self.parser = PydanticOutputParser(pydantic_object=StructuredQuery)
        self.validator = QueryValidator()
        self.prompt_service = PromptService()
        
        schema_lines = []
        for table_name, table in Base.metadata.tables.items():
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

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    async def generate(self, natural_language: str) -> StructuredQuery:
        logger.info("Generating structured JSON from natural language.")
        
        prompt_text = self.prompt_service.load_prompt("json_generation.txt")
        prompt_template = ChatPromptTemplate.from_template(prompt_text)
        
        messages = prompt_template.format_messages(
            schema_info=self.schema_info,
            query=natural_language,
            format_instructions=self.parser.get_format_instructions()
        )
        
        try:
            # Generate the structured output
            response = await self.llm.ainvoke(messages)
            
            structured_query = self.parser.parse(response.content)
            
            # Validate against database schema
            self.validator.validate(structured_query)
            
            return structured_query
            
        except ValueError as ve:
            logger.exception(f"Validation Error: {str(ve)}. Retrying...", exc_info=ve)
            raise
        except Exception as e:
            import tenacity
            real_error = e.last_attempt.exception() if isinstance(e, tenacity.RetryError) else e
            logger.exception(f"Chain execution failed: {str(real_error)}", exc_info=real_error)
            raise real_error from e
