from app.services.db_service import DatabaseServiceError, execute_select
from app.services.log_service import log_event, now_ms
from app.state import AgentState


def execute_sql_node(state: AgentState) -> AgentState:
    started_at = now_ms()
    try:
        rows = execute_select(state["sql"])
        log_event(
            trace_id=state["trace_id"],
            node_name="execute_sql",
            user_question=state["user_question"],
            intent=state["intent"],
            tool_name="postgresql_select",
            tool_args={"sql": state["sql"]},
            tool_result_summary={"row_count": len(rows)},
            latency_ms=now_ms() - started_at,
        )
        return {**state, "raw_data": rows, "error": None}
    except DatabaseServiceError as exc:
        error = str(exc)
        log_event(
            trace_id=state["trace_id"],
            node_name="execute_sql",
            user_question=state["user_question"],
            intent=state["intent"],
            tool_name="postgresql_select",
            tool_args={"sql": state["sql"]},
            error=error,
            latency_ms=now_ms() - started_at,
        )
        return {**state, "raw_data": [], "error": error}
