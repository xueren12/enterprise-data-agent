from langgraph.graph import END, StateGraph

from app.config import SQL_MAX_RETRIES
from app.nodes.analyze_node import analyze_data_node
from app.nodes.datasource_node import select_datasource_node
from app.nodes.fallback_node import fallback_node
from app.nodes.parse_node import parse_question_node
from app.nodes.plan_node import generate_plan_node
from app.nodes.report_node import generate_report_node
from app.nodes.sql_execute_node import execute_sql_node
from app.nodes.sql_generate_node import generate_sql_node
from app.nodes.sql_repair_node import repair_sql_node
from app.nodes.sql_validate_node import validate_sql_node
from app.nodes.tool_node import run_tool_node
from app.nodes.validate_node import validate_result_node
from app.state import AgentState


def route_on_error(state: AgentState) -> str:
    return "fallback" if state.get("error") else "continue"


def route_data_source(state: AgentState) -> str:
    if state.get("error"):
        return "fallback"
    if state["data_source_type"] == "postgresql":
        return "postgresql"
    return "csv"


def route_sql_validation(state: AgentState) -> str:
    if not state.get("sql_validation_error"):
        return "execute"
    if state.get("retry_count", 0) < SQL_MAX_RETRIES:
        return "repair"
    return "fallback"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("parse_question", parse_question_node)
    graph.add_node("select_datasource", select_datasource_node)
    graph.add_node("generate_plan", generate_plan_node)
    graph.add_node("run_tool", run_tool_node)
    graph.add_node("generate_sql", generate_sql_node)
    graph.add_node("validate_sql", validate_sql_node)
    graph.add_node("repair_sql", repair_sql_node)
    graph.add_node("execute_sql", execute_sql_node)
    graph.add_node("validate_result", validate_result_node)
    graph.add_node("analyze_data", analyze_data_node)
    graph.add_node("generate_report", generate_report_node)
    graph.add_node("fallback", fallback_node)

    graph.set_entry_point("parse_question")
    graph.add_conditional_edges(
        "parse_question",
        route_on_error,
        {"continue": "select_datasource", "fallback": "fallback"},
    )
    graph.add_conditional_edges(
        "select_datasource",
        route_on_error,
        {"continue": "generate_plan", "fallback": "fallback"},
    )
    graph.add_conditional_edges(
        "generate_plan",
        route_data_source,
        {
            "csv": "run_tool",
            "postgresql": "generate_sql",
            "fallback": "fallback",
        },
    )
    graph.add_conditional_edges(
        "generate_sql",
        route_on_error,
        {"continue": "validate_sql", "fallback": "fallback"},
    )
    graph.add_conditional_edges(
        "validate_sql",
        route_sql_validation,
        {
            "execute": "execute_sql",
            "repair": "repair_sql",
            "fallback": "fallback",
        },
    )
    graph.add_edge("repair_sql", "validate_sql")
    graph.add_conditional_edges(
        "execute_sql",
        route_on_error,
        {"continue": "validate_result", "fallback": "fallback"},
    )
    graph.add_conditional_edges(
        "run_tool",
        route_on_error,
        {"continue": "validate_result", "fallback": "fallback"},
    )
    graph.add_conditional_edges(
        "validate_result",
        route_on_error,
        {"continue": "analyze_data", "fallback": "fallback"},
    )
    graph.add_conditional_edges(
        "analyze_data",
        route_on_error,
        {"continue": "generate_report", "fallback": "fallback"},
    )
    graph.add_conditional_edges(
        "generate_report",
        route_on_error,
        {"continue": END, "fallback": "fallback"},
    )
    graph.add_edge("fallback", END)

    return graph.compile()


agent_graph = build_graph()
