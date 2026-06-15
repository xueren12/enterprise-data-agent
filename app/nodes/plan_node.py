from app.services.llm_service import (
    generate_query_plan,
    generate_select_sql,
    summarize_llm_usage,
)
from app.services.log_service import log_event
from app.state import AgentState


def generate_plan_node(state: AgentState) -> AgentState:
    plan_result = generate_query_plan(
        state["user_question"],
        state["intent"],
        state["data_source_type"],
    )
    log_event(
        trace_id=state["trace_id"],
        node_name="generate_plan",
        user_question=state["user_question"],
        intent=state["intent"],
        tool_name="deepseek_query_plan",
        tool_result_summary={
            "used_llm": plan_result["used_llm"],
            "message": summarize_llm_usage(plan_result),
        },
        error=None if plan_result["used_llm"] else plan_result["error"],
    )
    sql = ""
    if state["data_source_type"] == "postgresql":
        sql_result = generate_select_sql(state["user_question"], state["intent"])
        sql = sql_result["content"]
        log_event(
            trace_id=state["trace_id"],
            node_name="generate_plan",
            user_question=state["user_question"],
            intent=state["intent"],
            tool_name="deepseek_text_to_sql",
            tool_result_summary={"used_llm": sql_result["used_llm"]},
            error=None if sql_result["used_llm"] else sql_result["error"],
        )

    return {
        **state,
        "query_plan": plan_result["content"],
        "sql": sql,
        "error": None,
    }
