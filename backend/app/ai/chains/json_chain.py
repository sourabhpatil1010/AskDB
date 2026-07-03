import logging
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_not_exception_type

from app.core.llm import get_llm
from app.ai.structured_output.schemas import StructuredQuery, TimePlanConfig
from app.query_builder.query_validator import QueryValidator
from app.services.ai.prompt_service import PromptService
from app.models import Base
from app.ai.planner.planner_service import PlannerService
from app.ai.planner.planner_schema import PlannerClarificationException, ExecutionPlan
from app.ai.planner.planner_utils import SchemaDateColumnResolver

logger = logging.getLogger(__name__)

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

    # --- 2. Determine primary date column for the query (schema-aware, no hardcoding) ---
    primary_table = plan.tables[0] if plan.tables else "employees"

    # Use SchemaDateColumnResolver to find the date column for the best matching table
    primary_table_for_date, date_col = SchemaDateColumnResolver.resolve_for_tables(
        plan.tables or ["employees"]
    )
    if primary_table_for_date is None:
        primary_table_for_date = primary_table
        date_col = None

    # --- 3. Time granularity hint ---
    if time_granularity and date_col:
        qualified_date = f"{primary_table_for_date}.{date_col}"
        trunc_expr = f"DATE_TRUNC('{time_granularity}', {qualified_date})"
        hints.append(
            f"TIME GRANULARITY HINT: Group by {time_granularity}.\n"
            f"  - Use in SELECT:   {trunc_expr} AS {time_granularity}\n"
            f"  - Use in GROUP BY: {trunc_expr}\n"
            f"  - Use in SORT / ORDER BY: Set field to \"{time_granularity}\" (the alias), NOT the raw date column!\n"
            f"  - Set time_granularity field to: \"{time_granularity}\""
        )

    # --- 4. Metrics → Column expressions hint ---
    if plan.metrics:
        col_exprs = []
        for m in plan.metrics:
            op = m.operation.upper() if m.operation and m.operation.lower() != "none" else ""
            field = m.field

            # Qualify field with table name if we can determine it
            # Qualify field with table name if we can determine it
            from app.ai.planner.planner_utils import SchemaColumnResolver, SchemaAggregationResolver
            owner_tbl = SchemaColumnResolver.resolve_column_owner(field, plan.tables or [])
            qualified_field = f"{owner_tbl}.{field}" if owner_tbl else field

            alias = m.alias or (f"{op.lower()}_{field}" if op else field)
            if op in ("COUNT", "DISTINCT_COUNT", "COUNT_DISTINCT") and field in ("*", "id", "count"):
                from app.models import Base as _Base
                tbl_obj = _Base.metadata.tables.get(primary_table)
                pk_col = None
                if tbl_obj is not None:
                    pk_cols = list(tbl_obj.primary_key.columns)
                    pk_col = f"{primary_table}.{pk_cols[0].name}" if pk_cols else f"{primary_table}.id"
                if op == "COUNT":
                    expr = f"COUNT({pk_col or '*'}) AS {alias}"
                else:
                    expr = f"COUNT(DISTINCT {pk_col or '*'}) AS {alias}"
            elif not op:
                expr = f"{qualified_field} AS {alias}" if alias != qualified_field else qualified_field
            else:
                expr = SchemaAggregationResolver.format_aggregation_expression(op, qualified_field, alias=alias)
            col_exprs.append(expr)

        hints.append(
            f"AGGREGATION HINT: Use these exact expressions in the columns field:\n"
            + "\n".join(f"  - \"{e}\"" for e in col_exprs)
        )

    # --- 5. HAVING conditions hint ---
    if plan.having:
        having_exprs = []
        for h in plan.having:
            metric_name = h.metric.lower()
            matched_expr = None
            if plan.metrics:
                for m in plan.metrics:
                    if m.alias and m.alias.lower() == metric_name:
                        op_up = m.operation.upper() if m.operation else ""
                        field = m.field
                        from app.ai.planner.planner_utils import SchemaColumnResolver
                        owner_tbl = SchemaColumnResolver.resolve_column_owner(field, plan.tables or [])
                        qualified_field = f"{owner_tbl}.{field}" if owner_tbl else field
                        if op_up in ("COUNT", "DISTINCT_COUNT", "COUNT_DISTINCT"):
                            from app.models import Base as _Base
                            tbl_obj = _Base.metadata.tables.get(primary_table)
                            pk_cols = list(tbl_obj.primary_key.columns) if tbl_obj is not None else []
                            pk_str = f"{primary_table}.{pk_cols[0].name}" if pk_cols else "*"
                            matched_expr = f"COUNT({pk_str})" if op_up == "COUNT" else f"COUNT(DISTINCT {pk_str})"
                        elif op_up:
                            matched_expr = f"{op_up}({qualified_field})"
                        else:
                            matched_expr = qualified_field
                        break
            if not matched_expr:
                if "count" in metric_name:
                    matched_expr = f"COUNT({primary_table}.id)"
                elif "avg" in metric_name:
                    matched_expr = f"AVG({primary_table}.base_salary)"
                elif "sum" in metric_name or "total" in metric_name:
                    matched_expr = f"SUM({primary_table}.base_salary)"
                else:
                    matched_expr = metric_name if "(" in metric_name else f"COUNT(*)"

            having_exprs.append(
                f"  {{\"column\": \"{matched_expr}\", \"operator\": \"{h.operator}\", \"value\": {h.value}}}"
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
    tables_to_join = plan.relationships if plan.relationships else (plan.tables if len(plan.tables) > 1 else None)
    if tables_to_join:
        from app.ai.planner.planner_utils import SchemaJoinResolver
        resolved_joins = SchemaJoinResolver.resolve_joins_for_tables(tables_to_join)
        if resolved_joins:
            hints.append(
                "JOIN HINT: The following joins are required:\n"
                + "\n".join(f"  - JOIN {j.table} ON {j.on}" for j in resolved_joins)
            )

    # --- 7.5. Ranking hint ---
    win_p_hint = getattr(plan, "window_plan", None) or getattr(plan, "analytical_window_plan", None)
    is_analytical_win_hint = (hasattr(plan, "intent") and getattr(plan.intent, "value", str(plan.intent)) == "analytical_window") or (win_p_hint is not None and getattr(win_p_hint, "function", "") not in {"ROW_NUMBER", "RANK", "DENSE_RANK", ""})
    is_ranking = not is_analytical_win_hint and (
        (hasattr(plan, "intent") and getattr(plan.intent, "value", str(plan.intent)) == "ranking")
        or getattr(plan, "requires_window_function", False)
        or getattr(plan, "ranking_type", None)
        or getattr(plan, "nth_rank", None)
    )
    if is_ranking:
        r_type = getattr(plan, "ranking_type", None) or ("nth" if getattr(plan, "nth_rank", None) else "top")
        r_rank = getattr(plan, "rank", None) or getattr(plan, "nth_rank", None) or getattr(plan, "limit_per_group", None) or getattr(plan, "limit", None) or 1
        r_scope = getattr(plan, "scope", None) or ("per_group" if getattr(plan, "group_by", None) or getattr(plan, "group", None) else "global")
        r_part = getattr(plan, "partition_by", None) or (list(plan.group_by) if getattr(plan, "group_by", None) else ([plan.group] if getattr(plan, "group", None) else None))
        r_order_dir = getattr(plan, "order", None) or (plan.order_by[0].direction if getattr(plan, "order_by", None) else "desc")
        r_order_col = plan.order_by[0].field if getattr(plan, "order_by", None) else (plan.metrics[0].field if getattr(plan, "metrics", None) else "base_salary")
        
        part_cols = []
        if r_part:
            for p in r_part:
                if p == "department":
                    part_cols.append("departments.name")
                elif p == "project":
                    part_cols.append("projects.name")
                else:
                    part_cols.append(p)
                    
        hints.append(
            f"RANKING HINT: Populate the 'ranking' configuration object:\n"
            f"  {{\"type\": \"{r_type}\", \"rank\": {r_rank}, \"scope\": \"{r_scope}\", "
            f"\"partition_by\": {json.dumps(part_cols) if part_cols else 'null'}, "
            f"\"order_by\": {{\"field\": \"{r_order_col}\", \"direction\": \"{r_order_dir}\"}}, \"dense_rank\": {str(r_type == 'nth').lower()}}}"
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

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3), retry=retry_if_not_exception_type((ValueError, PlannerClarificationException, RuntimeError, AttributeError)))
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

        if not self.llm:
            logger.warning("LLM not initialized or API key missing in JSONGenerationChain. Using deterministic heuristic JSON fallback.")
            return self._create_heuristic_structured_query(execution_plan)

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
            logger.warning(f"LLM execution unavailable or failed ({str(real_error)}). Using deterministic heuristic JSON fallback.")
            return self._create_heuristic_structured_query(execution_plan)

    def _create_heuristic_structured_query(self, plan: ExecutionPlan) -> StructuredQuery:
        """Fallback deterministic conversion of ExecutionPlan to StructuredQuery when LLM is unavailable."""
        from app.ai.structured_output.schemas import (
            StructuredQuery, JoinCondition, FilterCondition, SortCondition,
            RankingConfig, OperatorEnum, HavingCondition, WindowFunctionConfig
        )
        from app.ai.planner.planner_utils import JoinDetectionUtils, SchemaDateColumnResolver, SchemaJoinResolver
        from app.models import Base as _Base
        
        primary_table = plan.tables[0] if plan.tables else "employees"
        
        tables_to_join = plan.relationships if plan.relationships else (plan.tables if len(plan.tables) > 1 else None)
        joins = SchemaJoinResolver.resolve_joins_for_tables(tables_to_join) if tables_to_join else []
                    
        columns = []
        group_by = []
        time_gran = getattr(plan, "time_granularity", None)
        if not time_gran and plan.group_by:
            for gb in plan.group_by:
                if gb.lower().strip() in _ABSTRACT_TIME_LABELS:
                    time_gran = gb.lower().strip()
                    break
                    
        if time_gran:
            pt_for_date, dcol = SchemaDateColumnResolver.resolve_for_tables(plan.tables or ["employees"])
            if dcol:
                expr = f"DATE_TRUNC('{time_gran}', {pt_for_date}.{dcol})"
                columns.append(f"{expr} AS {time_gran}")
                group_by.append(expr)
        elif plan.group_by:
            from app.ai.planner.planner_utils import SchemaGroupingResolver
            for gb in plan.group_by:
                q_gb = SchemaGroupingResolver.resolve_grouping_column(gb, plan.tables or [primary_table], default_table=primary_table)
                if q_gb not in columns:
                    columns.append(q_gb)
                if q_gb not in group_by:
                    group_by.append(q_gb)
                    
        if plan.metrics:
            from app.ai.planner.planner_utils import SchemaColumnResolver, SchemaAggregationResolver
            for m in plan.metrics:
                op = m.operation.upper() if m.operation and m.operation.lower() != "none" else ""
                field = m.field
                alias = m.alias or (f"{op.lower()}_{field}" if op else field)
                if not op:
                    q_f = SchemaColumnResolver.qualify_column(field, plan.tables or [], default_table=primary_table)
                    if f"{q_f} AS {alias}" not in columns and q_f not in columns:
                        columns.append(f"{q_f} AS {alias}" if alias != field else q_f)
                else:
                    if op in ("COUNT", "DISTINCT_COUNT", "COUNT_DISTINCT") and field in ("*", "id", "count"):
                        from app.models import Base as _Base
                        tbl_obj = _Base.metadata.tables.get(primary_table)
                        pk_cols = list(tbl_obj.primary_key.columns) if tbl_obj is not None else []
                        q_f = f"{primary_table}.{pk_cols[0].name}" if pk_cols else f"{primary_table}.id"
                    else:
                        q_f = SchemaColumnResolver.qualify_column(field, plan.tables or [], default_table=primary_table)
                    
                    expr = SchemaAggregationResolver.format_aggregation_expression(op, q_f, alias=alias)
                    if expr not in columns:
                        columns.append(expr)
        elif not columns:
            columns.append(f"{primary_table}.*")
            
        ranking_cfg = None
        is_ranking = (
            (hasattr(plan, "intent") and getattr(plan.intent, "value", str(plan.intent)) == "ranking")
            or getattr(plan, "requires_window_function", False)
            or getattr(plan, "ranking_type", None)
            or getattr(plan, "nth_rank", None)
        )
        if is_ranking:
            r_type = getattr(plan, "ranking_type", None) or ("nth" if getattr(plan, "nth_rank", None) else "top")
            r_rank = getattr(plan, "rank", None) or getattr(plan, "nth_rank", None) or getattr(plan, "limit_per_group", None) or getattr(plan, "limit", None) or 1
            r_scope = getattr(plan, "scope", None) or ("per_group" if getattr(plan, "group_by", None) or getattr(plan, "group", None) else "global")
            r_part = getattr(plan, "partition_by", None) or (list(plan.group_by) if getattr(plan, "group_by", None) else ([plan.group] if getattr(plan, "group", None) else None))
            r_order_dir = getattr(plan, "order", None) or (plan.order_by[0].direction if getattr(plan, "order_by", None) else "desc")
            r_order_col = plan.order_by[0].field if getattr(plan, "order_by", None) else (plan.metrics[0].field if getattr(plan, "metrics", None) else "base_salary")
            
            part_cols = []
            if r_part:
                from app.ai.planner.planner_utils import SchemaGroupingResolver
                for p in r_part:
                    part_col = SchemaGroupingResolver.resolve_grouping_column(p, plan.tables or [primary_table], default_table=primary_table)
                    if part_col:
                        part_cols.append(part_col)
            
            from app.ai.planner.planner_utils import SchemaColumnResolver
            order_tbl = SchemaColumnResolver.resolve_column_owner(r_order_col, plan.tables or [primary_table]) or primary_table
                
            ranking_cfg = RankingConfig(
                type=r_type,
                rank=r_rank,
                scope=r_scope,
                partition_by=part_cols if part_cols else None,
                order_by=SortCondition(table=order_tbl, field=r_order_col, direction=r_order_dir),
                dense_rank=(r_type == "nth")
            )
            
        window_cfg = None
        win_p = getattr(plan, "window_plan", None) or getattr(plan, "analytical_window_plan", None)
        if win_p or is_ranking:
            w_func = getattr(win_p, "function", None) if win_p else ("DENSE_RANK" if getattr(plan, "nth_rank", None) else ("RANK" if "rank" in str(getattr(plan, "intent", "")).lower() else "ROW_NUMBER"))
            w_col = getattr(win_p, "column", None) if win_p else None
            if not w_col and win_p:
                w_col = getattr(win_p, "target_metric", None)
            w_part_raw = getattr(win_p, "partition_by", None) if win_p else None
            if w_part_raw:
                from app.ai.planner.planner_utils import SchemaGroupingResolver
                w_part = [SchemaGroupingResolver.resolve_grouping_column(p, plan.tables or [primary_table], default_table=primary_table) or p for p in w_part_raw]
            else:
                w_part = part_cols if is_ranking and part_cols else None
            w_alias = getattr(win_p, "alias", None) if win_p else "rank_num"
            w_frame = getattr(win_p, "frame", None) if win_p else None
            w_order = None
            if win_p and getattr(win_p, "order_by", None):
                w_order = []
                for o in win_p.order_by:
                    fld = o.field
                    if fld in ("salary", "salaries"): fld = "base_salary"
                    o_tbl = SchemaColumnResolver.resolve_column_owner(fld, plan.tables or [primary_table]) or primary_table
                    w_order.append(SortCondition(table=o_tbl, field=fld, direction=o.direction))
            elif is_ranking and ranking_cfg and ranking_cfg.order_by:
                w_order = [ranking_cfg.order_by]
                
            window_cfg = WindowFunctionConfig(
                function=w_func or "ROW_NUMBER",
                column=w_col,
                partition_by=w_part,
                order_by=w_order,
                frame=w_frame,
                alias=w_alias
            )
            if getattr(window_cfg, "function", "") not in {"ROW_NUMBER", "RANK", "DENSE_RANK", ""}:
                group_by = []
                if window_cfg.partition_by:
                    for p in window_cfg.partition_by:
                        if p not in columns and not any(p in c for c in columns):
                            columns.append(p)
                if window_cfg.order_by:
                    for o in window_cfg.order_by:
                        q_o = f"{o.table}.{o.field}" if o.table else o.field
                        if q_o not in columns and not any(o.field in c for c in columns):
                            columns.append(q_o)

        filters = []
        if plan.filters:
            for f in plan.filters:
                op_map = {"=": OperatorEnum.EQ, "!=": OperatorEnum.NEQ, ">": OperatorEnum.GT, "<": OperatorEnum.LT, ">=": OperatorEnum.GTE, "<=": OperatorEnum.LTE, "like": OperatorEnum.LIKE, "between": OperatorEnum.BETWEEN, "in": OperatorEnum.IN}
                op_enum = op_map.get(str(f.operator).lower(), OperatorEnum.EQ)
                from app.ai.planner.planner_utils import SchemaColumnResolver
                f_tbl = SchemaColumnResolver.resolve_column_owner(f.field, plan.tables or [primary_table]) or primary_table
                filters.append(FilterCondition(table=f_tbl, field=f.field, operator=op_enum, value=f.value))
                
        sort_cond = None
        if plan.order_by and not (ranking_cfg and ranking_cfg.scope == "per_group"):
            o = plan.order_by[0]
            from app.ai.planner.planner_utils import SchemaColumnResolver
            sort_tbl = SchemaColumnResolver.resolve_column_owner(o.field, plan.tables or [primary_table]) or primary_table
            sort_cond = SortCondition(table=sort_tbl, field=o.field, direction=o.direction)
            
        having_list = []
        if plan.having:
            for h in plan.having:
                metric_name = h.metric.lower() if h.metric else ""
                matched_expr = None
                if plan.metrics:
                    for m in plan.metrics:
                        if (m.alias and m.alias.lower() == metric_name) or (m.field and m.field.lower() == metric_name) or (not m.alias and m.operation):
                            op_up = m.operation.upper() if m.operation else ""
                            field = m.field
                            from app.ai.planner.planner_utils import SchemaColumnResolver
                            owner_tbl = SchemaColumnResolver.resolve_column_owner(field, plan.tables or [])
                            qualified_field = f"{owner_tbl}.{field}" if owner_tbl else field
                            if op_up in ("COUNT", "DISTINCT_COUNT", "COUNT_DISTINCT"):
                                from app.models import Base as _Base
                                tbl_obj = _Base.metadata.tables.get(primary_table)
                                pk_cols = list(tbl_obj.primary_key.columns) if tbl_obj is not None else []
                                pk_str = f"{primary_table}.{pk_cols[0].name}" if pk_cols else "*"
                                matched_expr = f"COUNT({pk_str})" if op_up == "COUNT" else f"COUNT(DISTINCT {pk_str})"
                            elif op_up:
                                matched_expr = f"{op_up}({qualified_field})"
                            else:
                                matched_expr = qualified_field
                            break
                if not matched_expr:
                    if "count" in metric_name or not metric_name:
                        matched_expr = f"COUNT({primary_table}.id)"
                    elif "avg" in metric_name:
                        matched_expr = f"AVG({primary_table}.base_salary)"
                    elif "sum" in metric_name or "total" in metric_name:
                        matched_expr = f"SUM({primary_table}.base_salary)"
                    else:
                        matched_expr = metric_name if "(" in metric_name else f"COUNT(*)"
                having_list.append(HavingCondition(column=matched_expr, operator=h.operator, value=h.value))

        time_plan_cfg = None
        if plan.time_plan:
            time_plan_cfg = TimePlanConfig(
                time_expression=plan.time_plan.time_expression,
                date_field=plan.time_plan.date_field,
                operator=plan.time_plan.operator,
                start_date=plan.time_plan.start_date,
                end_date=plan.time_plan.end_date,
                relative_period=plan.time_plan.relative_period,
                relative_offset=plan.time_plan.relative_offset,
                granularity=plan.time_plan.granularity
            )

        sq = StructuredQuery(
            table=primary_table,
            joins=joins if joins else None,
            columns=columns,
            filters=filters if filters else None,
            sort=sort_cond,
            group_by=group_by if group_by else None,
            having=having_list if having_list else None,
            ranking=ranking_cfg,
            window_function=window_cfg,
            time_granularity=time_gran,
            time_plan=time_plan_cfg,
            limit=plan.limit or 50
        )
        return sq
