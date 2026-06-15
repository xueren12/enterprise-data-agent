from app.state import AgentState
from app.tools.langchain_tools import chart_generate_tool, report_generate_tool


def generate_report_node(state: AgentState) -> AgentState:
    analysis_result = state["analysis_result"]
    if not isinstance(analysis_result, list):
        return {**state, "error": "生成报告失败：分析结果格式不正确。"}

    chart_result = chart_generate_tool.invoke(
        {
            "analysis_result": analysis_result,
            "trace_id": state["trace_id"],
            "analysis_type": state["intent"],
        }
    )
    if not chart_result["success"]:
        return {**state, "error": chart_result["error"]}

    report_result = report_generate_tool.invoke(
        {
            "question": state["user_question"],
            "analysis_result": analysis_result,
            "chart_path": chart_result["chart_path"],
            "trace_id": state["trace_id"],
            "analysis_type": state["intent"],
        }
    )
    if not report_result["success"]:
        return {**state, "chart_path": chart_result["chart_path"], "error": report_result["error"]}

    return {
        **state,
        "chart_path": chart_result["chart_path"],
        "report": report_result["report"],
        "report_path": report_result["report_path"],
        "error": None,
    }
