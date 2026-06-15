from app.config import DATABASE_URL, DEFAULT_DATA_SOURCE, SAMPLE_API_LOGS_PATH
from app.nodes.parse_node import SUPPORTED_INTENTS
from app.state import AgentState


def select_datasource_node(state: AgentState) -> AgentState:
    if state["intent"] not in SUPPORTED_INTENTS:
        return {**state, "error": "未能选择数据源：当前问题意图暂不支持。"}

    question = state["user_question"].lower()
    explicitly_requests_database = any(
        keyword in question for keyword in ("数据库", "postgresql", "postgres", "sql")
    )
    explicitly_requests_file = any(
        keyword in question for keyword in ("csv", "excel", "文件")
    )

    use_database = (
        explicitly_requests_database
        or DEFAULT_DATA_SOURCE == "postgresql"
        or (
            DEFAULT_DATA_SOURCE == "auto"
            and bool(DATABASE_URL)
            and not explicitly_requests_file
        )
    )

    if use_database:
        if not DATABASE_URL:
            return {
                **state,
                "data_source": "PostgreSQL",
                "data_source_type": "postgresql",
                "error": "问题要求查询数据库，但当前未配置 DATABASE_URL。",
            }
        return {
            **state,
            "data_source": "api_call_logs",
            "data_source_type": "postgresql",
            "error": None,
        }

    if not SAMPLE_API_LOGS_PATH.exists():
        return {
            **state,
            "data_source": str(SAMPLE_API_LOGS_PATH),
            "data_source_type": "csv",
            "error": f"示例数据源不存在：{SAMPLE_API_LOGS_PATH}",
        }

    return {
        **state,
        "data_source": str(SAMPLE_API_LOGS_PATH),
        "data_source_type": "csv",
        "error": None,
    }
