from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.config import SQL_ALLOWED_COLUMNS, SQL_ALLOWED_TABLES, SQL_MAX_LIMIT
from app.services.db_service import DatabaseServiceError, execute_select
from app.services.log_service import log_event, now_ms
from app.services.safety_service import validate_select_sql


class SqlQueryInput(BaseModel):
    sql: str = Field(description="需要校验并执行的单条 SELECT 查询。")
    trace_id: str = Field(description="本次 Agent 执行的追踪 ID。")


def _sql_query_tool_impl(sql: str, trace_id: str) -> dict:
    started_at = now_ms()
    validation = validate_select_sql(
        sql,
        allowed_tables=SQL_ALLOWED_TABLES,
        allowed_columns=SQL_ALLOWED_COLUMNS,
        max_limit=SQL_MAX_LIMIT,
    )
    if not validation.is_safe:
        log_event(
            trace_id=trace_id,
            tool_name="sql_query_tool",
            tool_args={"sql": sql},
            error=validation.error,
            latency_ms=now_ms() - started_at,
        )
        return {
            "success": False,
            "data": [],
            "row_count": 0,
            "executed_sql": "",
            "error": validation.error,
        }

    try:
        rows = execute_select(validation.sql)
        log_event(
            trace_id=trace_id,
            tool_name="sql_query_tool",
            tool_args={"sql": validation.sql},
            tool_result_summary={"row_count": len(rows)},
            latency_ms=now_ms() - started_at,
        )
        return {
            "success": True,
            "data": rows,
            "row_count": len(rows),
            "executed_sql": validation.sql,
            "error": None,
        }
    except DatabaseServiceError as exc:
        error = str(exc)
        log_event(
            trace_id=trace_id,
            tool_name="sql_query_tool",
            tool_args={"sql": validation.sql},
            error=error,
            latency_ms=now_ms() - started_at,
        )
        return {
            "success": False,
            "data": [],
            "row_count": 0,
            "executed_sql": validation.sql,
            "error": error,
        }


sql_query_tool = StructuredTool.from_function(
    func=_sql_query_tool_impl,
    name="sql_query_tool",
    description=(
        "校验并执行 PostgreSQL 只读查询。只允许单条 SELECT，"
        "并强制执行表白名单、字段白名单和 LIMIT 限制。"
    ),
    args_schema=SqlQueryInput,
)
