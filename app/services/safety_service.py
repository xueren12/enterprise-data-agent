from __future__ import annotations

import re
from dataclasses import dataclass

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
