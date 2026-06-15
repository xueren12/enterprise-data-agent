import re

from app.state import AgentState


SUPPORTED_INTENTS = {
    "department_failure_rate",
    "api_failure_topn",
    "average_latency",
    "failure_trend",
    "department_call_volume",
    "department_call_volume_trend",
}


def _extract_top_n(question: str, default: int = 10) -> int:
    match = re.search(r"(?:top\s*|前\s*)(\d+)", question, flags=re.IGNORECASE)
    return min(max(int(match.group(1)), 1), 100) if match else default


def _extract_filters(question: str) -> dict:
    params: dict = {}
    days_match = re.search(r"最近\s*(\d+)\s*天", question)
    if days_match:
        params["days"] = min(max(int(days_match.group(1)), 1), 3650)

    for department in ("销售部", "财务部", "运维部", "风控部", "平台部"):
        if department in question:
            params["department"] = department
            break

    for project in ("客户关系系统", "财务系统", "运维中心", "风控系统", "网关平台"):
        if project in question:
            params["project_name"] = project
            break

    api_match = re.search(r"(/api/[A-Za-z0-9_./-]+)", question)
    if api_match:
        params["api_name"] = api_match.group(1)
    return params


def parse_question_node(state: AgentState) -> AgentState:
    question = state["user_question"].strip()
    if not question:
        return {**state, "error": "用户问题为空，请输入需要分析的问题。"}

    normalized = question.lower()
    params = _extract_filters(question)

    if (
        ("调用量" in question or "调用次数" in question)
        and any(word in question for word in ("趋势", "变化", "走势", "按天", "每日"))
    ):
        intent = "department_call_volume_trend"
    elif any(word in question for word in ("趋势", "走势", "按天", "每日")):
        intent = "failure_trend"
    elif any(word in question for word in ("响应时间", "平均耗时", "延迟", "耗时")):
        intent = "average_latency"
        params.setdefault("top_n", _extract_top_n(question))
    elif "调用量" in question or "调用次数" in question:
        intent = "department_call_volume"
    elif (
        ("接口" in question and any(word in normalized for word in ("top", "最高")))
        or "失败率最高的接口" in question
    ):
        intent = "api_failure_topn"
        params.setdefault("top_n", _extract_top_n(question))
    elif "失败率" in question or "失败" in question:
        intent = "department_failure_rate"
        if "top" in normalized or "前" in question:
            params.setdefault("top_n", _extract_top_n(question))
    else:
        return {
            **state,
            "intent": "unknown",
            "analysis_params": {},
            "error": (
                "暂时支持失败率、失败接口 TopN、平均响应时间、失败趋势和部门调用量分析。"
            ),
        }

    return {
        **state,
        "intent": intent,
        "analysis_params": params,
        "error": None,
    }
