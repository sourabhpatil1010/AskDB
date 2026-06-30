"""Automatic type coercion for SQL query parameters.

Converts raw string/numeric values from the LLM-generated StructuredQuery
into proper Python types that asyncpg expects for the corresponding
PostgreSQL column types (Date, DateTime, UUID, Integer, Numeric, Boolean, etc.).

Uses SQLAlchemy model metadata for dynamic type detection — no hardcoded
column names.
"""

import logging
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict

from sqlalchemy import Integer, Numeric, Float, Boolean, Date, DateTime, Uuid, String, Text, Enum
from app.models import Base

logger = logging.getLogger(__name__)

# Build a lookup: (table_name, column_name) -> SQLAlchemy column type instance
_COLUMN_TYPE_MAP: Dict[tuple[str, str], Any] = {}


def _build_type_map():
    """Populate the column type map from SQLAlchemy metadata (called once)."""
    if _COLUMN_TYPE_MAP:
        return
    for table_name, table in Base.metadata.tables.items():
        for col in table.columns:
            _COLUMN_TYPE_MAP[(table_name, col.name)] = col.type


def _coerce_single_value(value: Any, col_type: Any, table: str, field: str) -> Any:
    """Coerce a single parameter value to match the column's SQLAlchemy type.

    Returns the coerced value or raises ValueError with a clean message.
    """
    if value is None:
        return None

    # --- Date ---
    if isinstance(col_type, Date) and not isinstance(col_type, DateTime):
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                raise ValueError(
                    f"Invalid date format for {table}.{field}: '{value}'. Expected ISO format (YYYY-MM-DD)."
                )
        raise ValueError(
            f"Cannot convert {type(value).__name__} to date for {table}.{field}."
        )

    # --- DateTime ---
    if isinstance(col_type, DateTime):
        if isinstance(value, datetime):
            return value
        if isinstance(value, date) and not isinstance(value, datetime):
            return datetime(value.year, value.month, value.day)
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                raise ValueError(
                    f"Invalid datetime format for {table}.{field}: '{value}'. "
                    f"Expected ISO format (YYYY-MM-DDTHH:MM:SS)."
                )
        raise ValueError(
            f"Cannot convert {type(value).__name__} to datetime for {table}.{field}."
        )

    # --- UUID ---
    if isinstance(col_type, Uuid):
        if isinstance(value, uuid.UUID):
            return value
        if isinstance(value, str):
            try:
                return uuid.UUID(value)
            except ValueError:
                raise ValueError(
                    f"Invalid UUID for {table}.{field}: '{value}'."
                )
        raise ValueError(
            f"Cannot convert {type(value).__name__} to UUID for {table}.{field}."
        )

    # --- Integer ---
    if isinstance(col_type, Integer) and not isinstance(col_type, (Numeric, Float)):
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        if isinstance(value, str):
            try:
                return int(value)
            except (ValueError, TypeError):
                raise ValueError(
                    f"Invalid integer for {table}.{field}: '{value}'."
                )
        if isinstance(value, float):
            return int(value)
        raise ValueError(
            f"Cannot convert {type(value).__name__} to integer for {table}.{field}."
        )

    # --- Numeric / Float / Decimal ---
    if isinstance(col_type, (Numeric, Float)):
        if isinstance(value, (int, float, Decimal)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except (ValueError, TypeError):
                raise ValueError(
                    f"Invalid numeric value for {table}.{field}: '{value}'."
                )
        raise ValueError(
            f"Cannot convert {type(value).__name__} to numeric for {table}.{field}."
        )

    # --- Boolean ---
    if isinstance(col_type, Boolean):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lower = value.lower()
            if lower in ("true", "1", "yes", "t"):
                return True
            if lower in ("false", "0", "no", "f"):
                return False
            raise ValueError(
                f"Invalid boolean for {table}.{field}: '{value}'."
            )
        if isinstance(value, (int, float)):
            return bool(value)
        raise ValueError(
            f"Cannot convert {type(value).__name__} to boolean for {table}.{field}."
        )

    # --- Enum ---
    if isinstance(col_type, Enum):
        # Pass through as string — PostgreSQL enum columns accept string values
        return str(value) if value is not None else None

    # --- String / Text / Unknown — pass through ---
    return value


def coerce_parameters(
    table_name: str,
    parameters: Dict[str, Any],
    param_field_map: Dict[str, tuple[str, str]],
) -> Dict[str, Any]:
    """Coerce all parameters in the dict to their correct Python types.

    Args:
        table_name: The primary table (used as fallback if field table is unknown).
        parameters: The raw parameter dict {param_name: raw_value}.
        param_field_map: Mapping {param_name: (table, field)} so we can look up
                         the column type for each parameter.

    Returns:
        A new dict with coerced values.

    Raises:
        ValueError: If any value cannot be coerced — with a clean message.
    """
    _build_type_map()

    coerced = {}
    for param_name, raw_value in parameters.items():
        mapping = param_field_map.get(param_name)
        if not mapping:
            # No type info — pass through
            coerced[param_name] = raw_value
            continue

        tbl, fld = mapping
        col_type = _COLUMN_TYPE_MAP.get((tbl, fld))

        if col_type is None:
            # Column not found in metadata — pass through
            logger.debug(f"No type metadata for {tbl}.{fld}, passing value through")
            coerced[param_name] = raw_value
            continue

        try:
            coerced[param_name] = _coerce_single_value(raw_value, col_type, tbl, fld)
        except ValueError:
            raise  # Already has a clean message
        except Exception as e:
            raise ValueError(
                f"Failed to convert parameter '{param_name}' for {tbl}.{fld}: {str(e)}"
            ) from e

    return coerced
