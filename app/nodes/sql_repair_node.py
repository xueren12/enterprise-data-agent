from app.services.llm_service import repair_select_sql
from app.services.log_service import log_event
from app.state import AgentState


def repair_sql_node(state: AgentState) -> AgentState:
    result = repair_select_sql(
        question=state["user_question"],
        intent=state["intent"],
        original_sql=state["sql"],
        validation_error=state.get("sql_validation_error") or "SQL 未通过安全校验。",
    )
    log_event(
        trace_id=state["trace_id"],
        node_name="repair_sql",
        user_question=state["user_question"],
        intent=state["intent"],
        tool_name="deepseek_sql_repair",
        tool_result_summary={
            "used_llm": result["used_llm"],
            "retry_count": state.get("retry_count", 0),
        },
        error=None if result["used_llm"] else result["error"],
    )
    return {
        **state,
        "sql": result["content"],
        "sql_validation_error": None,
        "error": None,
    }
