from __future__ import annotations

from typing import Any

from app.catalog.schema_registry import (
    get_filterable_columns,
    get_queryable_columns,
    get_table,
)


DEFAULT_TABLE = "api_call_logs"
FILTER_FIELD_ALIASES = {"days": "request_time"}


def resolve_filter_field(filter_name: str, table_name: str = DEFAULT_TABLE) -> str:
    return FILTER_FIELD_ALIASES.get(filter_name, filter_name)


def validate_filter_fields(
    filters: dict[str, Any],
    *,
    allowed_filters: set[str] | None = None,
    table_name: str = DEFAULT_TABLE,
) -> dict[str, Any]:
    filterable_columns = get_filterable_columns(table_name)
    normalized: dict[str, Any] = {}

    for filter_name, filter_value in filters.items():
        if allowed_filters is not None and filter_name not in allowed_filters:
            raise ValueError(f"指标不支持筛选条件：{filter_name}")

        resolved_field = resolve_filter_field(filter_name, table_name)
        if resolved_field not in filterable_columns:
            raise ValueError(f"字段不允许作为筛选条件：{resolved_field}")

        normalized[filter_name] = filter_value
    return normalized


def validate_query_columns(
    columns: list[str],
    *,
    table_name: str = DEFAULT_TABLE,
) -> list[str]:
    queryable_columns = get_queryable_columns(table_name)
    table = get_table(table_name)
    normalized = list(dict.fromkeys(columns))

    unknown = set(normalized) - set(table.fields)
    if unknown:
        raise ValueError(f"字段未在数据目录注册：{', '.join(sorted(unknown))}")

    disallowed = set(normalized) - queryable_columns
    if disallowed:
        raise ValueError(f"字段不允许查询：{', '.join(sorted(disallowed))}")
    return normalized


def columns_for_filters(
    filters: dict[str, Any],
    *,
    table_name: str = DEFAULT_TABLE,
) -> list[str]:
    return [
        resolve_filter_field(filter_name, table_name)
        for filter_name in filters
    ]
