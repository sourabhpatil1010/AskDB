import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_not_exception_type

from app.core.llm import get_llm
from app.ai.structured_output.schemas import StructuredQuery
from app.query_builder.query_validator import QueryValidator
from app.services.ai.prompt_service import PromptService
from app.models import Base
from app.ai.planner.planner_service import PlannerService
from app.ai.planner.planner_schema import PlannerClarificationException, ExecutionPlan

logger = logging.getLogger(__name__)

# Maps abstract time granularity labels to DATE_TRUNC PostgreSQL expressions per table's primary date column
_TABLE_DATE_COLUMNS = {
    "employees": "hire_date",
    "attendance": "date",
    "payroll": "period_start",
    "projects": "start_date",
    "leave_requests": "start_date",
    "performance_reviews": "review_date",
}

# Maps abstract group_by labels to canonical time granularity strings
_ABSTRACT_TIME_LABELS = {"month", "week", "quarter", "year", "day", "hour", "minute"}


def _build_translation_hints(plan: ExecutionPlan) -> str:
    """
    Converts ExecutionPlan semantic fields into explicit SQL-ready translation hints
    for the JSON generation prompt. This bridges the gap between planner abstract
    labels (e.g., group_by: ['month']) and concrete SQL expressions
    (DATE_TRUNC('month', employees.hire_date)).
    """
    hints = []

    # --- 1. Detect time granularity from group_by or explicit time_granularity field ---
    time_granularity: str | None = None
    if hasattr(plan, "time_granularity") and plan.time_granularity:
        time_granularity = plan.time_granularity.lower().strip()

    # Also detect from group_by abstract labels
    if not time_granularity and plan.group_by:
        for gb in plan.group_by:
            if gb.lower().strip() in _ABSTRACT_TIME_LABELS:
                time_granularity = gb.lower().strip()
                break

    # --- 2. Determine primary date column for the query ---
    primary_table = plan.tables[0] if plan.tables else "employees"
    date_col = _TABLE_DATE_COLUMNS.get(primary_table)

    # Also check joined tables for better date column selection
    if plan.tables:
        for t in plan.tables:
            if t in _TABLE_DATE_COLUMNS:
                date_col = _TABLE_DATE_COLUMNS[t]
                primary_table_for_date = t
                break
        else:
            primary_table_for_date = primary_table
    else:
        primary_table_for_date = primary_table

    # --- 3. Time granularity hint ---
    if time_granularity and date_col:
        qualified_date = f"{primary_table_for_date}.{date_col}"
        trunc_expr = f"DATE_TRUNC('{time_granularity}', {qualified_date})"
        hints.append(
            f"TIME GRANULARITY HINT: Group by {time_granularity}.\n"
            f"  - Use in SELECT:   {trunc_expr} AS {time_granularity}\n"
            f"  - Use in GROUP BY: {trunc_expr}\n"
            f"  - Set time_granularity field to: \"{time_granularity}\""
        )

    # --- 4. Metrics → Column expressions hint ---
    if plan.metrics:
        col_exprs = []
        for m in plan.metrics:
            op = m.operation.upper()
            field = m.field

            # Qualify field with table name if we can determine it
            qualified_field = field
            for t in (plan.tables or []):
                if t in _TABLE_DATE_COLUMNS or True:  # try all tables
                    from app.models import Base as _Base
                    table_obj = _Base.metadata.tables.get(t)
                    if table_obj is not None and field in [c.name for c in table_obj.columns]:
                        qualified_field = f"{t}.{field}"
                        break

            alias = m.alias or f"{op.lower()}_{field}"
            if op == "COUNT" and field in ("*", "id", "count"):
                # Use primary key of primary table for COUNT
                from app.models import Base as _Base
                tbl_obj = _Base.metadata.tables.get(primary_table)
                pk_col = None
                if tbl_obj is not None:
                    pk_cols = list(tbl_obj.primary_key.columns)
                    pk_col = f"{primary_table}.{pk_cols[0].name}" if pk_cols else f"{primary_table}.id"
                expr = f"COUNT({pk_col or '*'}) AS {alias}"
            else:
                expr = f"{op}({qualified_field}) AS {alias}"
            col_exprs.append(expr)

        hints.append(
            f"AGGREGATION HINT: Use these exact expressions in the columns field:\n"
            + "\n".join(f"  - {e}" for e in col_exprs)
        )

    # --- 5. HAVING conditions hint ---
    if plan.having:
        having_exprs = []
        for h in plan.having:
            # Map abstract metric names to actual SQL expressions
            metric_name = h.metric.lower()
            # Try to find the matching metric alias from plan.metrics
            matched_expr = None
            if plan.metrics:
                for m in plan.metrics:
                    if m.alias and m.alias.lower() == metric_name:
                        op_up = m.operation.upper()
                        field = m.field
                        from app.models import Base as _Base
                        qualified_field = field
                        for t in (plan.tables or []):
                            tbl_obj = _Base.metadata.tables.get(t)
                            if tbl_obj and field in [c.name for c in tbl_obj.columns]:
                                qualified_field = f"{t}.{field}"
                                break
                        if op_up == "COUNT":
                            tbl_obj = _Base.metadata.tables.get(primary_table)
                            pk_cols = list(tbl_obj.primary_key.columns) if tbl_obj else []
                            pk_str = f"{primary_table}.{pk_cols[0].name}" if pk_cols else "*"
                            matched_expr = f"COUNT({pk_str})"
                        else:
                            matched_expr = f"{op_up}({qualified_field})"
                        break
            if not matched_expr:
                # Fallback: use metric name directly
                matched_expr = metric_name if "(" in metric_name else f"COUNT(*)"

            having_exprs.append(
                f"  - column: \"{matched_expr}\", operator: \"{h.operator}\", value: {h.value}"
            )

        hints.append(
            "HAVING HINT: Populate the 'having' field with these conditions:\n"
            + "\n".join(having_exprs)
        )

    # --- 6. Filters summary hint ---
    if plan.filters:
        filter_hints = []
        for f in plan.filters:
            if f.time_reasoning:
                filter_hints.append(
                    f"  - {f.field} {f.operator} {f.value}  [Time reasoning: {f.time_reasoning}]"
                )
            else:
                filter_hints.append(f"  - {f.field} {f.operator} {f.value}")
        if filter_hints:
            hints.append(
                "FILTER HINT: Apply these WHERE conditions:\n" + "\n".join(filter_hints)
            )

    # --- 7. Join hint ---
    if plan.relationships:
        hints.append(
            "JOIN HINT: The following joins are required:\n"
            + "\n".join(f"  - {r}" for r in plan.relationships)
        )

    # --- 8. Order + Limit hint ---
    if plan.order_by:
        order_strs = [f"{o.field} {o.direction.upper()}" for o in plan.order_by]
        hints.append(f"SORT HINT: ORDER BY {', '.join(order_strs)}")
    if plan.limit:
        hints.append(f"LIMIT HINT: LIMIT {plan.limit}")

    return "\n\n".join(hints) if hints else ""


class JSONGenerationChain:
    def __init__(self):
        try:
            self.llm = get_llm()
        except Exception as e:
            logger.warning(f"LLM initialization failed in JSONGenerationChain ({e}).")
            self.llm = None
        self.parser = PydanticOutputParser(pydantic_object=StructuredQuery)
        self.validator = QueryValidator()
        self.prompt_service = PromptService()
        self.planner_service = PlannerService()
        
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

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3), retry=retry_if_not_exception_type((ValueError, PlannerClarificationException)))
    async def generate(self, natural_language: str) -> StructuredQuery:
        logger.info("Generating structured JSON from natural language.")
        
        # 1. AI Query Planner Stage (Single Source of Truth for Intent & Structure)
        execution_plan = await self.planner_service.create_plan(natural_language)

        # Log full planner output for debugging
        logger.info(f"[PIPELINE DEBUG] Planner Output:\n{execution_plan.model_dump_json(indent=2)}")

        if execution_plan.confidence < 0.70:
            raise PlannerClarificationException(
                questions=execution_plan.clarification_questions or ["Query intent unclear."],
                confidence=execution_plan.confidence
            )

        # 2. Build structured translation hints that bridge planner → SQL
        translation_hints = _build_translation_hints(execution_plan)

        # 3. Compose the enriched query block for the JSON generation prompt
        plan_json_str = execution_plan.model_dump_json(indent=2)
        enriched_query = (
            f"=== EXECUTION PLAN (Single Source of Truth) ===\n{plan_json_str}\n\n"
            f"=== SQL TRANSLATION HINTS ===\n{translation_hints}\n\n"
            f"=== ORIGINAL NATURAL LANGUAGE QUESTION ===\n{natural_language}"
        )

        prompt_text = self.prompt_service.load_prompt("json_generation.txt")
        prompt_template = ChatPromptTemplate.from_template(prompt_text)
        
        messages = prompt_template.format_messages(
            schema_info=self.schema_info,
            query=enriched_query,
            format_instructions=self.parser.get_format_instructions()
        )
        
        try:
            # Generate the structured output
            response = await self.llm.ainvoke(messages)
            
            structured_query = self.parser.parse(response.content)

            # Log generated StructuredQuery for debugging
            logger.info(f"[PIPELINE DEBUG] Generated StructuredQuery:\n{structured_query.model_dump_json(indent=2)}")
            
            # Validate against database schema
            self.validator.validate(structured_query)

            logger.info(f"[PIPELINE DEBUG] Validation passed.")
            
            return structured_query
            
        except ValueError as ve:
            logger.exception(f"Validation Error: {str(ve)}. Retrying...", exc_info=ve)
            raise
        except Exception as e:
            import tenacity
            real_error = e.last_attempt.exception() if isinstance(e, tenacity.RetryError) else e
            logger.exception(f"Chain execution failed: {str(real_error)}", exc_info=real_error)
            raise real_error from e
