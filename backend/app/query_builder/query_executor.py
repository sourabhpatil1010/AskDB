import logging
import re
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class QueryExecutor:
    """Safely executes parameterized SELECT queries."""
    
    # Regex to detect dangerous SQL commands
    # We enforce that the query MUST start with SELECT and must NOT contain forbidden keywords.
    FORBIDDEN_KEYWORDS = re.compile(
        r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|MERGE|GRANT|REVOKE|EXEC|EXECUTE)\b',
        re.IGNORECASE
    )

    def _is_safe(self, sql: str) -> bool:
        """Validates that the SQL is a SELECT statement and contains no dangerous keywords."""
        cleaned_sql = sql.strip().upper()
        
        # Must start with SELECT
        if not cleaned_sql.startswith("SELECT"):
            logger.error("SQL validation failed: Query does not start with SELECT.")
            return False
            
        # Must not contain multiple statements (;) inside
        # A single trailing semicolon is allowed, but not inside.
        if ';' in sql.strip()[:-1]:
            logger.error("SQL validation failed: Multiple statements detected.")
            return False

        # Must not contain forbidden keywords
        if self.FORBIDDEN_KEYWORDS.search(sql):
            logger.error("SQL validation failed: Forbidden keyword detected.")
            return False
            
        return True

    async def execute(self, session: AsyncSession, sql: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self._is_safe(sql):
            raise ValueError("Unsafe SQL query detected. Only SELECT statements are allowed.")
            
        try:
            # text() ensures it's treated as a parameterized query by SQLAlchemy
            statement = text(sql)
            
            # Execute with parameters safely bound by SQLAlchemy
            result = await session.execute(statement, parameters)
            
            # Fetch all rows
            rows = result.mappings().all()
            
            # Convert SQLAlchemy mappings to standard dictionaries
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.exception(f"Database execution failed: {str(e)}", exc_info=e)
            raise
