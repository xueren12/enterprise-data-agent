import json

from app.services import llm_service


def test_generate_query_plan_uses_valid_structured_llm_output(monkeypatch):
    response = {
        "intent": "api_failure_topn",
        "data_source_type": "csv",
        "analysis_type": "api_failure_topn",
        "filters": {"department": "运维部"},
        "top_n": 5,
        "required_columns": ["api_name", "status", "department"],
        "need_chart": True,
        "need_report": True,
    }
    monkeypatch.setattr(
        llm_service,
        "call_deepseek",
        lambda prompt, temperature=0.2: json.dumps(response, ensure_ascii=False),
    )

    result = llm_service.generate_query_plan(
        "统计运维部失败率最高的接口 Top5",
        "api_failure_topn",
        "csv",
        {"department": "运维部", "top_n": 5},
    )

    assert result["used_llm"] is True
    assert result["content"].model_dump() == response


def test_generate_query_plan_falls_back_when_llm_json_is_invalid(monkeypatch):
    monkeypatch.setattr(
        llm_service,
        "call_deepseek",
        lambda prompt, temperature=0.2: '{"intent": "unknown"}',
    )

    result = llm_service.generate_query_plan(
        "统计最近 30 天各部门失败率",
        "department_failure_rate",
        "postgresql",
        {"days": 30},
    )

    plan = result["content"]
    assert result["used_llm"] is False
    assert plan.intent == "department_failure_rate"
    assert plan.data_source_type == "postgresql"
    assert plan.filters == {"days": 30}
    assert plan.required_columns == ["department", "status", "request_time"]
