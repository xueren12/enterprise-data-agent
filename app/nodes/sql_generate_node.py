from app.services.llm_service import generate_select_sql
from app.services.log_service import log_event
from app.state import AgentState


def generate_sql_node(state: AgentState) -> AgentState:
    result = generate_select_sql(
        state["user_question"],
        state["intent"],
        state["query_plan"],
    )
    log_event(
        trace_id=state["trace_id"],
        node_name="generate_sql",
        user_question=state["user_question"],
        intent=state["intent"],
        tool_name="deepseek_text_to_sql",
        tool_result_summary={"used_llm": result["used_llm"]},
        error=None if result["used_llm"] else result["error"],
    )
    return {
        **state,
        "sql": result["content"],
        "sql_validation_error": None,
        "error": None,
    }
