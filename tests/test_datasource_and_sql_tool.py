from app.nodes.datasource_node import select_datasource_node
from app.tools.sql_tool import sql_query_tool


def state(question: str) -> dict:
    return {
        "trace_id": "route-test",
        "user_question": question,
        "intent": "department_failure_rate",
        "data_source": "",
        "data_source_type": "",
        "analysis_params": {},
        "query_plan": "",
        "sql": "",
        "raw_data": [],
        "analysis_result": {},
        "chart_path": "",
        "report": "",
        "error": None,
        "retry_count": 0,
    }


def test_explicit_database_question_routes_to_postgresql(monkeypatch):
    monkeypatch.setattr(
        "app.nodes.datasource_node.DATABASE_URL",
        "postgresql+psycopg://agent_user@localhost/agent_db",
    )

    result = select_datasource_node(state("从 PostgreSQL 数据库统计失败率"))

    assert result["data_source_type"] == "postgresql"
    assert result["data_source"] == "api_call_logs"
    assert result["error"] is None


def test_csv_question_routes_to_csv(monkeypatch):
    monkeypatch.setattr("app.nodes.datasource_node.DEFAULT_DATA_SOURCE", "auto")
    monkeypatch.setattr("app.nodes.datasource_node.DATABASE_URL", "configured")

    result = select_datasource_node(state("从 CSV 文件统计失败率"))

    assert result["data_source_type"] == "csv"
    assert result["error"] is None


def test_sql_tool_blocks_unsafe_sql_before_execution(monkeypatch):
    def fail_if_called(sql: str):
        raise AssertionError("危险 SQL 不应进入数据库执行层")

    monkeypatch.setattr("app.tools.sql_tool.execute_select", fail_if_called)

    result = sql_query_tool.invoke(
        {"sql": "DELETE FROM api_call_logs", "trace_id": "unsafe"}
    )

    assert result["success"] is False
    assert result["executed_sql"] == ""
    assert "禁止" in result["error"]
