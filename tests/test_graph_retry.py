from app import graph as graph_module
from app.config import SAMPLE_API_LOGS_PATH
from app.services import llm_service
from app.services.agent_service import build_initial_state


def _patch_common_graph_nodes(monkeypatch, data_source_type: str) -> None:
    monkeypatch.setattr(
        graph_module,
        "select_datasource_node",
        lambda state: {
            **state,
            "data_source_type": data_source_type,
            "data_source": "test-source",
            "error": None,
        },
    )
    monkeypatch.setattr(
        graph_module,
        "generate_plan_node",
        lambda state: {
            **state,
            "query_plan": {
                "intent": state["intent"],
                "data_source_type": data_source_type,
                "analysis_type": state["intent"],
                "filters": {},
                "top_n": None,
                "required_columns": ["department", "status"],
                "need_chart": True,
                "need_report": True,
            },
            "error": None,
        },
    )
    monkeypatch.setattr(
        graph_module,
        "analyze_data_node",
        lambda state: {
            **state,
            "analysis_result": [{"department": "运维部", "failure_rate": 20.0}],
            "error": None,
        },
    )
    monkeypatch.setattr(
        graph_module,
        "generate_report_node",
        lambda state: {**state, "report": "测试报告", "error": None},
    )


def test_postgresql_retries_once_then_succeeds(monkeypatch):
    _patch_common_graph_nodes(monkeypatch, "postgresql")
    repair_calls = []

    monkeypatch.setattr(
        graph_module,
        "generate_sql_node",
        lambda state: {**state, "sql": "SELECT * FROM api_call_logs", "error": None},
    )

    def repair_sql(state):
        repair_calls.append(state["retry_count"])
        return {
            **state,
            "sql": "SELECT department, status FROM api_call_logs LIMIT 20",
            "sql_validation_error": None,
            "error": None,
        }

    monkeypatch.setattr(graph_module, "repair_sql_node", repair_sql)
    monkeypatch.setattr(
        graph_module,
        "execute_sql_node",
        lambda state: {
            **state,
            "raw_data": [{"department": "运维部", "status": "failed"}],
            "error": None,
        },
    )

    result = graph_module.build_graph().invoke(
        build_initial_state("统计各部门接口调用失败率")
    )

    assert result["error"] is None
    assert result["retry_count"] == 1
    assert repair_calls == [1]
    assert result["report"] == "测试报告"


def test_postgresql_falls_back_after_two_validation_failures(monkeypatch):
    _patch_common_graph_nodes(monkeypatch, "postgresql")
    monkeypatch.setattr(
        graph_module,
        "generate_sql_node",
        lambda state: {**state, "sql": "DELETE FROM api_call_logs", "error": None},
    )
    monkeypatch.setattr(
        graph_module,
        "repair_sql_node",
        lambda state: {
            **state,
            "sql": "SELECT * FROM api_call_logs",
            "sql_validation_error": None,
            "error": None,
        },
    )

    result = graph_module.build_graph().invoke(
        build_initial_state("统计各部门接口调用失败率")
    )

    assert result["retry_count"] == 2
    assert result["error"]
    assert "本次查询未获得有效结果" in result["report"]


def test_csv_path_does_not_enter_sql_repair(monkeypatch):
    _patch_common_graph_nodes(monkeypatch, "csv")
    monkeypatch.setattr(
        graph_module,
        "run_tool_node",
        lambda state: {
            **state,
            "raw_data": [{"department": "运维部", "status": "success"}],
            "error": None,
        },
    )

    def unexpected_repair(state):
        raise AssertionError("CSV 流程不应进入 SQL 修复节点")

    monkeypatch.setattr(graph_module, "repair_sql_node", unexpected_repair)

    result = graph_module.build_graph().invoke(
        build_initial_state("统计各部门接口调用失败率")
    )

    assert result["error"] is None
    assert result["retry_count"] == 0
    assert result["report"] == "测试报告"


def test_full_graph_runs_with_structured_plan_on_csv(monkeypatch):
    monkeypatch.setattr(
        graph_module,
        "select_datasource_node",
        lambda state: {
            **state,
            "data_source_type": "csv",
            "data_source": str(SAMPLE_API_LOGS_PATH),
            "error": None,
        },
    )

    def disable_llm(prompt, temperature=0.2):
        raise RuntimeError("测试环境禁用外部大模型调用")

    monkeypatch.setattr(llm_service, "call_deepseek", disable_llm)

    result = graph_module.build_graph().invoke(
        build_initial_state("统计各部门接口调用失败率")
    )

    assert result["error"] is None
    assert result["query_plan"]["analysis_type"] == "department_failure_rate"
    assert result["query_plan"]["data_source_type"] == "csv"
    assert result["analysis_result"]
    assert result["chart_path"]
    assert result["report"]
