from app.state import AgentState
from app.tools.langchain_tools import pandas_analysis_tool


def analyze_data_node(state: AgentState) -> AgentState:
    params = state["analysis_params"]
    result = pandas_analysis_tool.invoke(
        {
            "raw_data": state["raw_data"],
            "trace_id": state["trace_id"],
            "analysis_type": state["intent"],
            "top_n": params.get("top_n"),
            "days": params.get("days"),
            "department": params.get("department"),
            "project_name": params.get("project_name"),
            "api_name": params.get("api_name"),
        }
    )
    if not result["success"]:
        return {**state, "analysis_result": [], "error": result["error"]}

    return {**state, "analysis_result": result["data"], "error": None}
