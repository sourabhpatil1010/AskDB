from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field

class OperatorEnum(str, Enum):
    EQ = "="
    NEQ = "!="
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    LIKE = "LIKE"
    IN = "IN"
    BETWEEN = "BETWEEN"
    IS_NULL = "IS NULL"
    IS_NOT_NULL = "IS NOT NULL"

class JoinCondition(BaseModel):
    table: str = Field(description="The table to join with")
    on: str = Field(description="The ON condition, e.g. 'employees.department_id = departments.id'")

class FilterCondition(BaseModel):
    table: Optional[str] = Field(default=None, description="The table this field belongs to")
    field: str = Field(description="The column name to filter on")
    operator: OperatorEnum = Field(description="The comparison operator")
    value: str | int | float | list[str] | list[int] | list[float] | None = Field(default=None, description="The value to compare against")

class SortCondition(BaseModel):
    table: Optional[str] = Field(default=None, description="The table this field belongs to")
    field: str = Field(description="The column name to sort by")
    direction: str = Field(description="Sort direction, either 'asc' or 'desc'")

class StructuredQuery(BaseModel):
    table: str = Field(description="The primary table to query from")
    joins: Optional[List[JoinCondition]] = Field(default=None, description="List of JOIN conditions")
    columns: List[str] = Field(description="List of columns to select. Use table.column format if using joins.")
    filters: Optional[List[FilterCondition]] = Field(default=None, description="List of filter conditions")
    sort: Optional[SortCondition] = Field(default=None, description="Sorting rules")
    group_by: Optional[List[str]] = Field(default=None, description="Columns to group by")
    limit: Optional[int] = Field(default=50, description="Maximum number of rows to return")
    offset: Optional[int] = Field(default=0, description="Number of rows to skip")
