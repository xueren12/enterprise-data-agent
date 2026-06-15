from app.state import AgentState


def validate_result_node(state: AgentState) -> AgentState:
    raw_data = state.get("raw_data", [])
    if not raw_data:
        return {
            **state,
            "error": "本次查询未获得有效结果，可能是数据源为空或字段不匹配。",
        }

    return {**state, "error": None}
