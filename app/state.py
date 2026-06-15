from __future__ import annotations

from typing import NotRequired, TypedDict


class AgentState(TypedDict):
    trace_id: str
    user_question: str
    intent: str
    data_source: str
    data_source_type: str
    analysis_params: dict
    query_plan: str
    sql: str
    raw_data: list[dict]
    analysis_result: dict | list[dict]
    chart_path: str
    report: str
    error: str | None
    retry_count: int
    report_path: NotRequired[str]
