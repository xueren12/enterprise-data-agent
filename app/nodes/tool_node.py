from app.state import AgentState
from app.tools.langchain_tools import csv_read_tool
from app.tools.sql_tool import sql_query_tool


def run_tool_node(state: AgentState) -> AgentState:
    if state["data_source_type"] == "postgresql":
        result = sql_query_tool.invoke(
            {"sql": state["sql"], "trace_id": state["trace_id"]}
        )
    else:
        result = csv_read_tool.invoke(
            {"csv_path": state["data_source"], "trace_id": state["trace_id"]}
        )

    if not result["success"]:
        return {**state, "raw_data": [], "error": result["error"]}

    return {
        **state,
        "raw_data": result["data"],
        "sql": result.get("executed_sql", state["sql"]),
        "error": None,
    }
