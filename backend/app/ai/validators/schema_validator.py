import logging
from app.models import Base
from app.ai.structured_output.schemas import StructuredQuery

logger = logging.getLogger(__name__)

class SchemaValidator:
    def __init__(self):
        # Extract tables and columns from SQLAlchemy metadata
        self.schema = {}
        for table_name, table in Base.metadata.tables.items():
            self.schema[table_name] = [col.name for col in table.columns]

    def validate(self, query: StructuredQuery) -> bool:
        if query.table not in self.schema:
            logger.error(f"Validation failed: Table '{query.table}' does not exist.")
            raise ValueError(f"Table '{query.table}' does not exist in the database.")
            
        valid_tables = [query.table]
        if query.joins:
            for j in query.joins:
                if j.table not in self.schema:
                    raise ValueError(f"Joined table '{j.table}' does not exist.")
                valid_tables.append(j.table)
                
        def _validate_col(col_name: str, explicit_table: str = None):
            cleaned_col = col_name.lower().replace("count(", "").replace("sum(", "").replace("avg(", "").replace("max(", "").replace("min(", "").replace(")", "").strip()
            if cleaned_col == "*":
                return
                
            # If the column has a dot, extract table and column
            if "." in cleaned_col:
                parts = cleaned_col.split(".", 1)
                t_name, c_name = parts[0], parts[1]
                if t_name not in valid_tables:
                    raise ValueError(f"Table qualifier '{t_name}' not in query tables {valid_tables}")
                if c_name not in self.schema.get(t_name, []):
                    raise ValueError(f"Column '{c_name}' not found in '{t_name}'")
                return
                
            if explicit_table:
                if explicit_table not in valid_tables:
                    raise ValueError(f"Table qualifier '{explicit_table}' not in query tables {valid_tables}")
                if cleaned_col not in self.schema.get(explicit_table, []):
                    raise ValueError(f"Column '{cleaned_col}' not found in '{explicit_table}'")
                return
                
            # Check if column exists in any of the valid tables
            found = False
            for t in valid_tables:
                if cleaned_col in self.schema[t]:
                    found = True
                    break
            if not found:
                raise ValueError(f"Column '{cleaned_col}' not found in tables {valid_tables}")

        # Validate selected columns
        for col in query.columns:
            _validate_col(col)

        # Validate filters
        if query.filters:
            for f in query.filters:
                _validate_col(f.field, f.table)

        # Validate sort
        if query.sort:
            _validate_col(query.sort.field, query.sort.table)

        # Validate group_by
        if query.group_by:
            for gb in query.group_by:
                _validate_col(gb)

        return True
