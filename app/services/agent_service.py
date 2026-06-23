from __future__ import annotations

from uuid import uuid4

from app.graph import agent_graph
from app.state import AgentState


def build_initial_state(question: str, trace_id: str | None = None) -> AgentState:
    return {
        "trace_id": trace_id or uuid4().hex[:12],
        "user_question": question,
        "intent": "",
        "data_source": "",
        "data_source_type": "",
        "analysis_params": {},
        "query_plan": {},
        "sql": "",
        "sql_validation_error": None,
        "raw_data": [],
        "analysis_result": {},
        "chart_path": "",
        "report": "",
        "error": None,
        "retry_count": 0,
    }


def run_agent(question: str, trace_id: str | None = None) -> AgentState:
    return agent_graph.invoke(build_initial_state(question, trace_id))
