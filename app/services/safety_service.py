from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlglot import exp, parse
from sqlglot.errors import ParseError


FORBIDDEN_SQL_KEYWORDS = {
    "DROP",
    "DELETE",
    "UPDATE",
    "INSERT",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE",
    "EXEC",
    "EXECUTE",
    "MERGE",
    "CALL",
    "COPY",
}


@dataclass(frozen=True)
class SqlValidationResult:
    is_safe: bool
    sql: str
    error: str | None = None


def validate_sql_matches_plan(
    sql: str,
    *,
    required_columns: list[str],
    filters: dict[str, Any],
) -> str | None:
    try:
        statement = parse(sql, read="postgres")[0]
    except (ParseError, IndexError):
        return "SQL 无法与查询计划进行一致性校验。"

    selected_columns: set[str] = set()
    for expression in statement.args.get("expressions") or []:
        if isinstance(expression, exp.Column):
            selected_columns.add(expression.name.lower())
        selected_columns.update(
            column.name.lower() for column in expression.find_all(exp.Column)
        )

    missing_columns = {
        column.lower() for column in required_columns
    } - selected_columns
    if missing_columns:
        return f"SQL 缺少查询计划要求的字段：{', '.join(sorted(missing_columns))}"

    where = statement.args.get("where")
    if filters and where is None:
        return "SQL 缺少查询计划要求的筛选条件。"
    if where is None:
        return None

    where_columns = {
        column.name.lower() for column in where.find_all(exp.Column)
    }
    filter_columns = {
        "days": "request_time",
        "department": "department",
        "project_name": "project_name",
        "api_name": "api_name",
    }
    for filter_name, expected_value in filters.items():
        column = filter_columns[filter_name]
        if column not in where_columns:
            return f"SQL 缺少筛选字段：{column}"

        where_sql = where.sql(dialect="postgres")
        if filter_name == "days":
            if f"{expected_value} day" not in where_sql.lower():
                return f"SQL 未正确应用最近 {expected_value} 天筛选。"
        elif str(expected_value) not in where_sql:
            return f"SQL 未正确应用筛选条件：{filter_name}"
    return None


def validate_select_sql(
    sql: str,
    *,
    allowed_tables: set[str],
    allowed_columns: set[str],
    max_limit: int,
) -> SqlValidationResult:
    normalized_sql = sql.strip()
    if not normalized_sql:
        return SqlValidationResult(False, "", "SQL 不能为空。")

    if "--" in normalized_sql or "/*" in normalized_sql or "*/" in normalized_sql:
        return SqlValidationResult(False, "", "SQL 不允许包含注释。")

    if ";" in normalized_sql.rstrip(";"):
        return SqlValidationResult(False, "", "SQL 不允许执行多条语句。")

    keyword_pattern = r"\b(" + "|".join(sorted(FORBIDDEN_SQL_KEYWORDS)) + r")\b"
    if re.search(keyword_pattern, normalized_sql, flags=re.IGNORECASE):
        return SqlValidationResult(False, "", "SQL 包含禁止的 DDL/DML 关键字。")

    try:
        statements = parse(normalized_sql, read="postgres")
    except ParseError as exc:
        return SqlValidationResult(False, "", f"SQL 语法解析失败：{exc}")

    if len(statements) != 1:
        return SqlValidationResult(False, "", "SQL 只允许包含一条查询语句。")

    statement = statements[0]
    if not isinstance(statement, exp.Query):
        return SqlValidationResult(False, "", "只允许执行 SELECT 查询。")

    dangerous_nodes = (
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Create,
        exp.Drop,
        exp.Alter,
        exp.Command,
    )
    if any(statement.find(node_type) for node_type in dangerous_nodes):
        return SqlValidationResult(False, "", "SQL 包含不允许执行的操作。")

    tables = {table.name.lower() for table in statement.find_all(exp.Table)}
    unknown_tables = tables - {name.lower() for name in allowed_tables}
    if unknown_tables:
        return SqlValidationResult(
            False,
            "",
            f"SQL 包含未授权的数据表：{', '.join(sorted(unknown_tables))}",
        )
    if not tables:
        return SqlValidationResult(False, "", "SQL 必须查询白名单中的数据表。")

    unsafe_stars = [
        star
        for star in statement.find_all(exp.Star)
        if not isinstance(star.parent, exp.Count)
    ]
    if unsafe_stars:
        return SqlValidationResult(
            False,
            "",
            "SQL 不允许直接查询 *，请明确指定字段；COUNT(*) 聚合除外。",
        )

    columns = {column.name.lower() for column in statement.find_all(exp.Column)}
    unknown_columns = columns - {name.lower() for name in allowed_columns}
    if unknown_columns:
        return SqlValidationResult(
            False,
            "",
            f"SQL 包含未授权的字段：{', '.join(sorted(unknown_columns))}",
        )

    limit = statement.args.get("limit")
    if limit is None:
        statement = statement.limit(max_limit)
    else:
        limit_expression = limit.expression
        if not isinstance(limit_expression, exp.Literal) or not limit_expression.is_int:
            return SqlValidationResult(False, "", "LIMIT 必须是明确的正整数。")

        limit_value = int(limit_expression.this)
        if limit_value <= 0:
            return SqlValidationResult(False, "", "LIMIT 必须大于 0。")
        if limit_value > max_limit:
            statement.set("limit", exp.Limit(expression=exp.Literal.number(max_limit)))

    safe_sql = statement.sql(dialect="postgres")
    return SqlValidationResult(True, safe_sql, None)
