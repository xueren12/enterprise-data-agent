from app.config import SQL_ALLOWED_COLUMNS, SQL_ALLOWED_TABLES, SQL_MAX_LIMIT
from app.services.log_service import log_event
from app.services.safety_service import validate_select_sql
from app.state import AgentState


def validate_sql_node(state: AgentState) -> AgentState:
    validation = validate_select_sql(
        state["sql"],
        allowed_tables=SQL_ALLOWED_TABLES,
        allowed_columns=SQL_ALLOWED_COLUMNS,
        max_limit=SQL_MAX_LIMIT,
    )
    if validation.is_safe:
        log_event(
            trace_id=state["trace_id"],
            node_name="validate_sql",
            user_question=state["user_question"],
            intent=state["intent"],
            tool_result_summary={"is_safe": True},
        )
        return {
            **state,
            "sql": validation.sql,
            "sql_validation_error": None,
            "error": None,
        }

    retry_count = state.get("retry_count", 0) + 1
    log_event(
        trace_id=state["trace_id"],
        node_name="validate_sql",
        user_question=state["user_question"],
        intent=state["intent"],
        tool_args={"sql": state["sql"]},
        tool_result_summary={"is_safe": False, "retry_count": retry_count},
        error=validation.error,
    )
    return {
        **state,
        "sql_validation_error": validation.error,
        "error": validation.error,
        "retry_count": retry_count,
    }
