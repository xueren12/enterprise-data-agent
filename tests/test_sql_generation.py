from app.services import llm_service
from app.services.safety_service import validate_sql_matches_plan


QUERY_PLAN = {
    "intent": "api_failure_topn",
    "data_source_type": "postgresql",
    "analysis_type": "api_failure_topn",
    "filters": {
        "days": 30,
        "department": "运维部",
        "api_name": "/api/orders",
    },
    "top_n": 5,
    "required_columns": ["api_name", "status", "request_time", "department"],
    "need_chart": True,
    "need_report": True,
}


def test_fallback_sql_uses_query_plan_columns_and_filters():
    sql = llm_service.fallback_select_sql(QUERY_PLAN)

    assert sql.startswith(
        "SELECT api_name, status, request_time, department FROM api_call_logs"
    )
    assert "request_time >= CURRENT_TIMESTAMP - INTERVAL '30 days'" in sql
    assert "department = '运维部'" in sql
    assert "api_name = '/api/orders'" in sql
    assert "LIMIT 200" in sql


def test_generate_sql_prompt_contains_query_plan(monkeypatch):
    captured = {}

    def fake_call(prompt: str, temperature: float = 0.2) -> str:
        captured["prompt"] = prompt
        return (
            "SELECT api_name, status, request_time, department "
            "FROM api_call_logs WHERE department = '运维部' LIMIT 200"
        )

    monkeypatch.setattr(llm_service, "call_deepseek", fake_call)

    result = llm_service.generate_select_sql(
        "统计最近30天运维部失败率最高的接口 Top5",
        "api_failure_topn",
        QUERY_PLAN,
    )

    assert result["used_llm"] is True
    assert '"api_name"' in captured["prompt"]
    assert '"department": "运维部"' in captured["prompt"]
    assert '"days": 30' in captured["prompt"]
    assert "分析结果 TopN：\n5" in captured["prompt"]


def test_sql_plan_validation_rejects_missing_columns_and_filters():
    missing_column_error = validate_sql_matches_plan(
        "SELECT api_name, status FROM api_call_logs "
        "WHERE department = '运维部' LIMIT 200",
        required_columns=QUERY_PLAN["required_columns"],
        filters=QUERY_PLAN["filters"],
    )
    missing_filter_error = validate_sql_matches_plan(
        "SELECT api_name, status, request_time, department FROM api_call_logs "
        "LIMIT 200",
        required_columns=QUERY_PLAN["required_columns"],
        filters=QUERY_PLAN["filters"],
    )

    assert "缺少查询计划要求的字段" in missing_column_error
    assert "缺少查询计划要求的筛选条件" in missing_filter_error


def test_sql_plan_validation_accepts_fallback_sql():
    sql = llm_service.fallback_select_sql(QUERY_PLAN)

    error = validate_sql_matches_plan(
        sql,
        required_columns=QUERY_PLAN["required_columns"],
        filters=QUERY_PLAN["filters"],
    )

    assert error is None
