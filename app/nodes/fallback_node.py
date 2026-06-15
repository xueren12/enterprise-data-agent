from app.state import AgentState


def fallback_node(state: AgentState) -> AgentState:
    error = state.get("error") or "未知错误"
    report = (
        "## 分析结果\n"
        "本次查询未获得有效结果。\n\n"
        "## 原因说明\n"
        f"{error}\n\n"
        "## 下一步建议\n"
        "请检查问题类型、数据源配置和字段完整性后重试。"
    )
    return {
        **state,
        "chart_path": "",
        "report": report,
        "report_path": "",
        "error": error,
    }
