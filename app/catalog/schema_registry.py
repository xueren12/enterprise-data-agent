from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


CATALOG_PATH = Path(__file__).with_name("table_catalog.yaml")


@dataclass(frozen=True)
class FieldDefinition:
    name: str
    description: str
    type: str
    allow_query: bool
    allow_filter: bool
    allow_aggregate: bool
    sensitive: bool


@dataclass(frozen=True)
class TableDefinition:
    name: str
    description: str
    fields: dict[str, FieldDefinition]


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, TableDefinition]:
    raw_catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    tables: dict[str, TableDefinition] = {}
    for table_name, table_data in raw_catalog["tables"].items():
        fields = {
            field["name"]: FieldDefinition(
                name=field["name"],
                description=field["description"],
                type=field["type"],
                allow_query=bool(field["allow_query"]),
                allow_filter=bool(field["allow_filter"]),
                allow_aggregate=bool(field["allow_aggregate"]),
                sensitive=bool(field["sensitive"]),
            )
            for field in table_data["fields"]
        }
        tables[table_name] = TableDefinition(
            name=table_data["name"],
            description=table_data["description"],
            fields=fields,
        )
    return tables


def get_table(table_name: str) -> TableDefinition:
    catalog = load_catalog()
    if table_name not in catalog:
        raise ValueError(f"未注册的数据表：{table_name}")
    return catalog[table_name]


def list_queryable_tables() -> set[str]:
    return set(load_catalog())


def get_queryable_columns(table_name: str) -> set[str]:
    table = get_table(table_name)
    return {
        name
        for name, field in table.fields.items()
        if field.allow_query and not field.sensitive
    }


def get_filterable_columns(table_name: str) -> set[str]:
    table = get_table(table_name)
    return {
        name
        for name, field in table.fields.items()
        if field.allow_filter and not field.sensitive
    }


def get_aggregatable_columns(table_name: str) -> set[str]:
    table = get_table(table_name)
    return {
        name
        for name, field in table.fields.items()
        if field.allow_aggregate and not field.sensitive
    }


def is_sensitive_column(table_name: str, column_name: str) -> bool:
    table = get_table(table_name)
    field = table.fields.get(column_name)
    return bool(field and field.sensitive)
