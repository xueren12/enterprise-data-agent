from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricDefinition:
    name: str
    display_name: str
    required_columns: list[str]
    allowed_filters: set[str]
    default_top_n: int | None
    need_chart: bool
    need_report: bool


METRIC_REGISTRY: dict[str, MetricDefinition] = {
    "department_failure_rate": MetricDefinition(
        name="department_failure_rate",
        display_name="各部门接口调用失败率",
        required_columns=["department", "status"],
        allowed_filters={"days", "department", "project_name", "api_name"},
        default_top_n=None,
        need_chart=True,
        need_report=True,
    ),
    "api_failure_topn": MetricDefinition(
        name="api_failure_topn",
        display_name="高失败率接口 TopN",
        required_columns=["api_name", "status"],
        allowed_filters={"days", "department", "project_name", "api_name"},
        default_top_n=10,
        need_chart=True,
        need_report=True,
    ),
    "average_latency": MetricDefinition(
        name="average_latency",
        display_name="接口平均响应时间",
        required_columns=["api_name", "latency_ms"],
        allowed_filters={"days", "department", "project_name", "api_name"},
        default_top_n=10,
        need_chart=True,
        need_report=True,
    ),
    "failure_trend": MetricDefinition(
        name="failure_trend",
        display_name="接口失败率趋势",
        required_columns=["request_time", "status"],
        allowed_filters={"days", "department", "project_name", "api_name"},
        default_top_n=None,
        need_chart=True,
        need_report=True,
    ),
    "department_call_volume": MetricDefinition(
        name="department_call_volume",
        display_name="各部门接口调用量",
        required_columns=["department"],
        allowed_filters={"days", "department", "project_name", "api_name"},
        default_top_n=None,
        need_chart=True,
        need_report=True,
    ),
    "department_call_volume_trend": MetricDefinition(
        name="department_call_volume_trend",
        display_name="各部门接口调用量变化",
        required_columns=["request_time", "department"],
        allowed_filters={"days", "department", "project_name", "api_name"},
        default_top_n=None,
        need_chart=True,
        need_report=True,
    ),
}


def get_metric_definition(metric_name: str) -> MetricDefinition:
    if metric_name not in METRIC_REGISTRY:
        raise ValueError(f"未注册的分析指标：{metric_name}")
    return METRIC_REGISTRY[metric_name]
