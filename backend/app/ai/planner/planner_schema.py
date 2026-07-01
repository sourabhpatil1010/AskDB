from enum import Enum
from typing import Any, List, Optional, Union
from pydantic import BaseModel, Field


class IntentEnum(str, Enum):
    AGGREGATION = "aggregation"
    COMPARISON = "comparison"
    RANKING = "ranking"
    TREND_ANALYSIS = "trend_analysis"
    DISTRIBUTION = "distribution"
    CORRELATION = "correlation"
    SEARCH = "search"
    FILTERING = "filtering"
    FORECAST = "forecast"


class Metric(BaseModel):
    field: str = Field(description="The column name or expression to aggregate, e.g. 'salary', 'id', or '*'")
    operation: str = Field(description="The aggregation operation: count, sum, avg, min, max, distinct_count, median")
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
    having: Optional[List[HavingCondition]] = Field(default=None, description="List of HAVING conditions for aggregated results")
    order_by: Optional[List[OrderCondition]] = Field(default=None, description="Sorting rules")
    limit: Optional[int] = Field(default=None, description="Maximum number of rows to return, e.g. Top 5, Top 10")
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
