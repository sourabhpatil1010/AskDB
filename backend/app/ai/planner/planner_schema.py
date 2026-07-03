from enum import Enum
from typing import Any, List, Optional, Union
from pydantic import BaseModel, Field


class IntentEnum(str, Enum):
    AGGREGATION = "aggregation"
    COMPARISON = "comparison"
    RANKING = "ranking"
    ANALYTICAL_WINDOW = "analytical_window"
    TREND_ANALYSIS = "trend_analysis"
    DISTRIBUTION = "distribution"
    CORRELATION = "correlation"
    SEARCH = "search"
    FILTERING = "filtering"
    FORECAST = "forecast"


class Metric(BaseModel):
    field: str = Field(description="The column name or expression to aggregate, e.g. 'salary', 'id', or '*'")
    operation: str = Field(description="The aggregation operation: count, sum, avg, min, max, distinct_count, median. Leave empty ('') or 'none' for ranking/non-aggregated column selection.")
    alias: Optional[str] = Field(default=None, description="Optional alias for the metric result, e.g. 'avg_salary'")


class Filter(BaseModel):
    field: str = Field(description="The column name to filter on, e.g. 'hire_date', 'department_id', 'salary'")
    operator: str = Field(description="The comparison operator: >, <, >=, <=, =, !=, between, in, not in, like")
    value: Any = Field(default=None, description="The value or list of values to compare against")
    time_reasoning: Optional[str] = Field(default=None, description="Explanation or label if time reasoning was applied")


class HavingCondition(BaseModel):
    metric: str = Field(description="The aggregated metric to check, e.g. 'count', 'avg_salary', 'sum'")
    operator: str = Field(description="The comparison operator: >, <, >=, <=, =, !=")
    value: Any = Field(description="The threshold value to check against")


class OrderCondition(BaseModel):
    field: str = Field(description="The column name or metric alias to sort by")
    direction: str = Field(description="Sort direction: 'asc' or 'desc'")


class WindowPlan(BaseModel):
    """Generic window function planning metadata carried from AI Planner to JSON Generator."""
    requires_window: bool = Field(default=True, description="True if a window function is required")
    function: str = Field(default="ROW_NUMBER", description="Window function name: ROW_NUMBER, RANK, DENSE_RANK, SUM, AVG, COUNT, MIN, MAX, LAG, LEAD, FIRST_VALUE, LAST_VALUE, DIFFERENCE")
    column: Optional[str] = Field(default=None, description="The target column or expression for analytical window functions")
    target_metric: Optional[str] = Field(default=None, description="The target metric or column expression for analytical window functions")
    partition_by: Optional[List[str]] = Field(default=None, description="List of columns or expressions to partition by")
    order_by: Optional[List[OrderCondition]] = Field(default=None, description="Ordering rules within each partition")
    frame: Optional[str] = Field(default=None, description="Window frame specification, e.g. 'ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW'")
    alias: Optional[str] = Field(default="rank_num", description="Alias for the window function result column")
    ranking_type: Optional[str] = Field(default=None, description="Type of ranking: top, bottom, nth")


AnalyticalWindowPlan = WindowPlan


class TimePlan(BaseModel):
    """Generic temporal planning metadata carried from AI Planner to JSON Generator."""
    time_expression: Optional[str] = Field(default=None, description="The natural language time phrase, e.g. 'last month', 'this year', 'yesterday'")
    date_field: str = Field(description="The resolved date column name or expression, e.g. 'employees.hire_date'")
    operator: str = Field(description="The temporal comparison operator: '=', '!=', '>', '<', '>=', '<=', 'between', 'before', 'after', 'in'")
    start_date: Optional[str] = Field(default=None, description="Start date in ISO format (YYYY-MM-DD) or relative start expression")
    end_date: Optional[str] = Field(default=None, description="End date in ISO format (YYYY-MM-DD) or relative end expression")
    relative_period: Optional[str] = Field(default=None, description="Relative time period label, e.g. 'yesterday', 'today', 'last_week', 'this_month', 'last_30_days'")
    relative_offset: Optional[int] = Field(default=None, description="Numeric offset in days, weeks, months, or years")
    granularity: Optional[str] = Field(default=None, description="Time granularity: 'day', 'week', 'month', 'quarter', 'year'")


class ExecutionPlan(BaseModel):
    intent: Union[IntentEnum, str] = Field(description="The primary business intent of the query")
    tables: List[str] = Field(description="List of database tables required for this query")
    relationships: Optional[List[str]] = Field(default=None, description="Join paths or relationship descriptions between tables")
    primary_entity: Optional[str] = Field(default=None, description="The primary table or business entity being investigated")
    secondary_entity: Optional[str] = Field(default=None, description="Secondary table or entity involved in comparison or grouping")
    metrics: Optional[List[Metric]] = Field(default=None, description="List of metrics or aggregations to calculate")
    filters: Optional[List[Filter]] = Field(default=None, description="List of filtering conditions")
    group_by: Optional[List[str]] = Field(default=None, description="List of columns or time granularity labels to group by (e.g., 'department', 'month', 'quarter')")
    time_granularity: Optional[str] = Field(default=None, description="Time bucket granularity for grouping: 'day', 'week', 'month', 'quarter', 'year'. Set when user asks to group by a time period.")
    time_plan: Optional[TimePlan] = Field(default=None, description="Temporal planning metadata if the query involves natural language time expressions")
    having: Optional[List[HavingCondition]] = Field(default=None, description="List of HAVING conditions for aggregated results")
    order_by: Optional[List[OrderCondition]] = Field(default=None, description="Sorting rules")
    limit: Optional[int] = Field(default=None, description="Maximum number of rows to return, e.g. Top 5, Top 10")
    scope: Optional[str] = Field(default=None, description="Scope of ranking: 'global' or 'per_group'")
    ranking_type: Optional[str] = Field(default=None, description="Type of ranking: 'top' (highest/best/latest), 'bottom' (lowest/worst/oldest), or 'nth' (specific rank)")
    rank: Optional[int] = Field(default=None, description="The integer rank or limit requested, e.g., 10 for 'Top 10', 3 for 'Top 3 per department', or 2 for 'second highest'")
    partition_by: Optional[List[str]] = Field(default=None, description="List of columns or entities to partition by when ranking within groups, e.g., ['department', 'team']")
    order: Optional[str] = Field(default=None, description="Sort order for ranking: 'desc' or 'asc'")
    group: Optional[str] = Field(default=None, description="Group name for scoped queries, e.g., 'department'")
    metric: Optional[str] = Field(default=None, description="Primary metric string for ranking or analysis, e.g., 'salary'")
    sort: Optional[str] = Field(default=None, description="Primary sort direction, e.g., 'DESC' or 'ASC'")
    limit_per_group: Optional[int] = Field(default=None, description="Limit per group for Top-N per group queries")
    nth_rank: Optional[int] = Field(default=None, description="Specific rank requested, e.g., 2 for second highest, 3 for third highest")
    requires_window_function: bool = Field(default=False, description="True if query requires SQL window functions (e.g., ROW_NUMBER, RANK)")
    window_plan: Optional[WindowPlan] = Field(default=None, description="Window function planning metadata if the query requires a window function")
    analytical_window_plan: Optional[WindowPlan] = Field(default=None, description="Analytical window function planning metadata")
    requires_correlated_subquery: bool = Field(default=False, description="True if query requires correlated subqueries")
    requires_partition_ranking: bool = Field(default=False, description="True if query requires partition ranking across groups")
    decomposition: Optional[List[str]] = Field(default=None, description="Logical task-by-task breakdown of complex queries")
    business_rules_applied: Optional[List[str]] = Field(default=None, description="List of business rule interpretations applied during planning")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Planner confidence score between 0.0 and 1.0")
    clarification_questions: Optional[List[str]] = Field(default=None, description="Clarification questions if confidence < 0.70 or query is ambiguous")



class PlannerValidationException(ValueError):
    """Exception raised when planner confidence is below 0.70 or validation fails requiring user clarification.
    
    Inherits from ValueError and contains 'Validation' in name so that SearchPipeline._map_exception_to_status
    properly classifies it as VALIDATION_ERROR and FastAPI returns HTTP status code 400 with clarification questions.
    """
    def __init__(self, questions: List[str], confidence: float = 0.0, message: Optional[str] = None):
        self.questions = questions
        self.confidence = confidence
        if not message:
            q_str = "\n- ".join(questions) if questions else "Query intent unclear."
            message = f"Clarification required (confidence: {confidence:.2f}):\n- {q_str}"
        super().__init__(message)


# Alias for semantics where clarification is the primary context
PlannerClarificationException = PlannerValidationException
