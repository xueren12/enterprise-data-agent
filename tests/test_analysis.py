import pandas as pd

from app.nodes.parse_node import parse_question_node
from app.tools.pandas_tool import analyze_api_logs
from app.tools.report_tool import generate_analysis_report


SAMPLE_ROWS = [
    {
        "department": "销售部",
        "project_name": "客户关系系统",
        "api_name": "/orders",
        "status": "failed",
        "latency_ms": 500,
        "request_time": "2026-05-01 10:00:00",
    },
    {
        "department": "销售部",
        "project_name": "客户关系系统",
        "api_name": "/orders",
        "status": "success",
        "latency_ms": 100,
        "request_time": "2026-05-01 11:00:00",
    },
    {
        "department": "平台部",
        "project_name": "网关平台",
        "api_name": "/health",
        "status": "success",
        "latency_ms": 20,
        "request_time": "2026-05-02 10:00:00",
    },
]


def base_state(question: str) -> dict:
    return {
        "trace_id": "test",
        "user_question": question,
        "intent": "",
        "data_source": "",
        "data_source_type": "",
        "analysis_params": {},
        "query_plan": {},
        "sql": "",
        "sql_validation_error": None,
        "raw_data": [],
        "analysis_result": {},
        "chart_path": "",
        "report": "",
        "error": None,
        "retry_count": 0,
    }


def test_parse_supported_intents():
    questions = {
        "统计各部门失败率": "department_failure_rate",
        "找出失败率最高的接口 Top5": "api_failure_topn",
        "找出平均响应时间最高的接口": "average_latency",
        "分析每日失败率趋势": "failure_trend",
        "统计各部门接口调用量": "department_call_volume",
        "分析各部门接口调用量变化趋势": "department_call_volume_trend",
    }

    for question, expected_intent in questions.items():
        result = parse_question_node(base_state(question))
        assert result["intent"] == expected_intent
        assert result["error"] is None


def test_parse_top_n():
    result = parse_question_node(base_state("找出失败率最高的接口 Top5"))

    assert result["analysis_params"]["top_n"] == 5


def test_all_analysis_types_return_results():
    frame = pd.DataFrame(SAMPLE_ROWS)

    for analysis_type in (
        "department_failure_rate",
        "api_failure_topn",
        "average_latency",
        "failure_trend",
        "department_call_volume",
        "department_call_volume_trend",
    ):
        result = analyze_api_logs(frame, analysis_type, top_n=10)
        assert result


def test_failure_trend_is_sorted_by_date():
    result = analyze_api_logs(pd.DataFrame(SAMPLE_ROWS), "failure_trend")

    assert [row["date"] for row in result] == ["2026-05-01", "2026-05-02"]


def test_days_and_department_filters():
    result = parse_question_node(base_state("分析最近30天销售部接口失败率趋势"))
    analysis = analyze_api_logs(
        pd.DataFrame(SAMPLE_ROWS),
        result["intent"],
        **result["analysis_params"],
    )

    assert result["analysis_params"]["days"] == 30
    assert result["analysis_params"]["department"] == "销售部"
    assert all(row["date"] == "2026-05-01" for row in analysis)


def test_report_explains_tied_failure_rate_leaders():
    report = generate_analysis_report(
        question="统计失败率",
        analysis_result=[
            {
                "department": "销售部",
                "total_calls": 2,
                "failed_calls": 1,
                "failure_rate": 50.0,
            },
            {
                "department": "平台部",
                "total_calls": 2,
                "failed_calls": 1,
                "failure_rate": 50.0,
            },
        ],
        chart_path="chart.png",
        analysis_type="department_failure_rate",
    )

    assert "销售部、平台部 并列最高" in report
