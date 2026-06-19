import logging
from pathlib import Path
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)

class PromptService:
    def __init__(self, base_path: str = "app/prompts"):
        self.base_path = Path(base_path)

    def load_prompt(self, filename: str) -> str:
        """Read prompt template from file."""
        file_path = self.base_path / filename
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                logger.info(f"Loaded prompt template: {filename}")
                return content
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to load prompt {filename}: {str(e)}")
            raise

    def render_prompt(self, template_str: str, **kwargs) -> str:
        """Render a Langchain prompt template with variables."""
        try:
            template = PromptTemplate.from_template(template_str)
            return template.format(**kwargs)
        except Exception as e:
            logger.error(f"Failed to render prompt: {str(e)}")
            raise
