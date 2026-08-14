import json

from app.services import llm_service


def test_generate_query_plan_uses_valid_structured_llm_output(monkeypatch):
    response = {
        "intent": "api_failure_topn",
        "data_source_type": "csv",
        "analysis_type": "api_failure_topn",
        "filters": {"department": "运维部"},
        "top_n": 5,
        "required_columns": ["api_name", "status", "latency_ms", "department"],
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
        "csv",
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
        "postgresql",
    )

    plan = result["content"]
    assert result["used_llm"] is False
    assert plan.intent == "department_failure_rate"
    assert plan.data_source_type == "postgresql"
    assert plan.filters == {"days": 30}
    assert plan.required_columns == [
        "department",
        "status",
        "latency_ms",
        "request_time",
    ]


def test_generate_query_plan_allows_llm_to_plan_within_registry(monkeypatch):
    response = {
        "intent": "average_latency",
        "data_source_type": "csv",
        "analysis_type": "average_latency",
        "filters": {"department": "财务部"},
        "top_n": 20,
        "required_columns": ["api_name", "status", "latency_ms", "department"],
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
        "csv",
    )

    plan = result["content"]
    assert result["used_llm"] is True
    assert plan.intent == "average_latency"
    assert plan.filters == {"department": "财务部"}
    assert plan.top_n == 20


def test_query_plan_registry_normalizes_execution_fields_and_output_flags():
    plan = llm_service.QueryPlan.model_validate(
        {
            "intent": "failure_trend",
            "data_source_type": "csv",
            "analysis_type": "failure_trend",
            "filters": {"days": 7, "api_name": None},
            "top_n": None,
            "required_columns": ["request_time", "status"],
            "need_chart": False,
            "need_report": False,
        }
    )

    assert plan.filters == {"days": 7}
    assert plan.required_columns == ["request_time", "status"]
    assert plan.need_chart is True
    assert plan.need_report is True
