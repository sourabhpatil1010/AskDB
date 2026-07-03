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
    table: Optional[str] = Field(default=None, description="The table this field belongs to. Leave None/null if sorting by an alias or metric from SELECT (e.g. 'avg_salary', 'count', 'month', 'quarter').")
    field: str = Field(description="The column name, alias, or expression to sort by")
    direction: str = Field(description="Sort direction, either 'asc' or 'desc'")


class HavingCondition(BaseModel):
    """Represents a HAVING clause condition applied to an aggregated column or expression."""
    column: str = Field(description="The aggregated expression to check, e.g. 'COUNT(employees.id)', 'AVG(payroll.base_salary)'. Must be the full aggregate expression, never a bare SELECT alias.")
    operator: str = Field(description="The comparison operator: >, <, >=, <=, =, !=")
    value: float | int = Field(description="The numeric threshold value to compare against")


class RankingConfig(BaseModel):
    """Configuration for advanced SQL ranking operations (Global, N-th, or Grouped/Partitioned)."""
    type: str = Field(description="Ranking type: 'top', 'bottom', or 'nth'")
    rank: int = Field(description="The numeric rank or Top-N limit, e.g. 3 for Top 3, 2 for second highest")
    scope: str = Field(default="global", description="Ranking scope: 'global' or 'per_group'")
    partition_by: Optional[List[str]] = Field(default=None, description="List of columns or expressions to PARTITION BY in window function, e.g. ['departments.name']")
    order_by: Optional[SortCondition] = Field(default=None, description="The column and direction to order by when computing ranks")
    dense_rank: bool = Field(default=False, description="True if DENSE_RANK() or N-th rank should be used")


class WindowFunctionConfig(BaseModel):
    """Configuration for SQL window functions (e.g., ROW_NUMBER, RANK, DENSE_RANK, SUM, AVG, DIFFERENCE)."""
    function: str = Field(description="The window function name: ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD, SUM, AVG, MIN, MAX, COUNT, FIRST_VALUE, LAST_VALUE, DIFFERENCE")
    column: Optional[str] = Field(default=None, description="The target column or expression for analytical window functions, e.g. 'payroll.base_salary' or 'id'")
    partition_by: Optional[List[str]] = Field(default=None, description="List of columns or expressions to PARTITION BY, e.g. ['department']")
    order_by: Optional[List[SortCondition]] = Field(default=None, description="List of SortCondition rules for ordering within the partition")
    frame: Optional[str] = Field(default=None, description="Window frame specification, e.g. 'ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW'")
    alias: Optional[str] = Field(default="rank_num", description="Alias for the result column of the window function")


class TimePlanConfig(BaseModel):
    """Configuration for temporal planning metadata in StructuredQuery."""
    time_expression: Optional[str] = Field(default=None, description="The natural language time phrase")
    date_field: str = Field(description="The resolved date column name or expression")
    operator: str = Field(description="The temporal comparison operator: '=', '!=', '>', '<', '>=', '<=', 'between', 'before', 'after', 'in'")
    start_date: Optional[str] = Field(default=None, description="Start date in ISO format (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="End date in ISO format (YYYY-MM-DD)")
    relative_period: Optional[str] = Field(default=None, description="Relative time period label")
    relative_offset: Optional[int] = Field(default=None, description="Numeric offset in periods")
    granularity: Optional[str] = Field(default=None, description="Time granularity: 'day', 'week', 'month', 'quarter', 'year'")


class SubqueryPlanConfig(BaseModel):
    """Configuration for subquery planning metadata in StructuredQuery."""
    subquery_type: str = Field(description="Type of subquery: 'scalar', 'in', 'not_in', 'exists', 'not_exists', 'correlated', 'table'")
    target_table: Optional[str] = Field(default=None, description="The table queried inside the subquery")
    target_column: Optional[str] = Field(default=None, description="The column selected or aggregated in the subquery")
    comparison_operator: Optional[str] = Field(default=None, description="Comparison operator linking outer query to subquery")
    aggregate_function: Optional[str] = Field(default=None, description="Aggregate function applied in the subquery")
    correlation_columns: Optional[List[str]] = Field(default=None, description="Columns linking inner subquery to outer query for correlated subqueries")
    join_columns: Optional[List[str]] = Field(default=None, description="Join columns if subquery involves joining or linking tables")
    alias: Optional[str] = Field(default=None, description="Optional alias for the subquery or correlated reference")
    group_by: Optional[List[str]] = Field(default=None, description="Optional group by columns within the subquery")
    having: Optional[List[HavingCondition]] = Field(default=None, description="Optional having conditions within the subquery")
    filters: Optional[List[FilterCondition]] = Field(default=None, description="Optional filters applied inside the subquery")
    order_by: Optional[List[SortCondition]] = Field(default=None, description="Optional ordering rules inside the subquery")
    limit: Optional[int] = Field(default=None, description="Optional row limit inside the subquery")


class StructuredQuery(BaseModel):
    table: str = Field(description="The primary table to query from")
    joins: Optional[List[JoinCondition]] = Field(default=None, description="List of JOIN conditions")
    columns: List[str] = Field(description=(
        "List of columns or expressions to SELECT. "
        "For aggregations use: COUNT(table.col) AS alias, AVG(table.col) AS alias. "
        "For time granularity use: DATE_TRUNC('month', table.date_col) AS month. "
        "Use table.column format when joins are present."
    ))
    filters: Optional[List[FilterCondition]] = Field(default=None, description="List of filter conditions")
    sort: Optional[SortCondition] = Field(default=None, description="Sorting rules")
    group_by: Optional[List[str]] = Field(default=None, description=(
        "Columns or expressions to GROUP BY. "
        "For time granularity use the same DATE_TRUNC/EXTRACT expression as in columns, e.g. DATE_TRUNC('month', attendance.date). "
        "Use table.column format when joins are present."
    ))
    having: Optional[List[HavingCondition]] = Field(default=None, description=(
        "HAVING clause conditions on aggregated results. "
        "Example: COUNT(employees.id) > 20, AVG(payroll.base_salary) > 100000"
    ))
    ranking: Optional[RankingConfig] = Field(default=None, description="Advanced ranking configuration for window function or N-th rank queries")
    window_function: Optional[WindowFunctionConfig] = Field(default=None, description="SQL window function configuration if required by the query")
    time_granularity: Optional[str] = Field(default=None, description=(
        "The time bucket granularity for grouping: 'day', 'week', 'month', 'quarter', 'year'. "
        "Set this when the planner specifies time-based grouping."
    ))
    time_plan: Optional[TimePlanConfig] = Field(default=None, description="Temporal planning configuration if query involves natural language time expressions")
    subquery_plan: Optional[SubqueryPlanConfig] = Field(default=None, description="Subquery planning configuration if query requires a subquery")
    limit: Optional[int] = Field(default=50, description="Maximum number of rows to return")
    offset: Optional[int] = Field(default=0, description="Number of rows to skip")
