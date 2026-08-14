from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.catalog.field_resolver import (
    columns_for_filters,
    validate_filter_fields,
    validate_query_columns,
)
from app.catalog.metric_registry import get_metric_definition


AnalysisType = Literal[
    "department_failure_rate",
    "api_failure_topn",
    "average_latency",
    "failure_trend",
    "department_call_volume",
    "department_call_volume_trend",
]

class QueryPlan(BaseModel):
    intent: AnalysisType = Field(description="识别出的用户分析意图。")
    data_source_type: Literal["csv", "postgresql"] = Field(
        description="计划使用的数据源类型。"
    )
    analysis_type: AnalysisType = Field(description="Pandas 实际执行的分析类型。")
    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="结构化筛选条件。",
    )
    top_n: int | None = Field(default=None, ge=1, le=100)
    required_columns: list[str] = Field(
        min_length=1,
        description="完成分析所需的原始字段。",
    )
    need_chart: bool = True
    need_report: bool = True

    @field_validator("required_columns")
    @classmethod
    def validate_required_columns(cls, value: list[str]) -> list[str]:
        return validate_query_columns(value)

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, value: dict[str, Any]) -> dict[str, Any]:
        # 部分模型会把未使用的可选条件输出为 null，将其视为未提供。
        normalized = {name: item for name, item in value.items() if item is not None}
        if "days" in normalized:
            days = normalized["days"]
            if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 3650:
                raise ValueError("days 必须是 1 到 3650 的整数。")

        for name in ("department", "project_name", "api_name"):
            if name not in normalized:
                continue
            filter_value = normalized[name]
            if not isinstance(filter_value, str) or not filter_value.strip():
                raise ValueError(f"{name} 必须是非空字符串。")
            normalized[name] = filter_value.strip()
        return validate_filter_fields(normalized)

    @model_validator(mode="after")
    def validate_intent_matches_analysis(self) -> "QueryPlan":
        if self.intent != self.analysis_type:
            raise ValueError("intent 与 analysis_type 必须一致。")
        metric = get_metric_definition(self.analysis_type)
        if self.top_n is None and metric.default_top_n is not None:
            self.top_n = metric.default_top_n
        # 图表和报告属于指标口径，不信任模型的自由开关值。
        self.need_chart = metric.need_chart
        self.need_report = metric.need_report
        missing = set(metric.required_columns) - set(
            self.required_columns
        )
        if missing:
            raise ValueError(
                f"required_columns 缺少分析必需字段：{', '.join(sorted(missing))}"
            )
        validate_filter_fields(
            self.filters,
            allowed_filters=metric.allowed_filters,
        )
        missing_filter_columns = set(columns_for_filters(self.filters)) - set(self.required_columns)
        if missing_filter_columns:
            # 选择列由受控 Registry 推导，而不是由模型决定是否读取筛选字段。
            self.required_columns = validate_query_columns(
                self.required_columns + sorted(missing_filter_columns)
            )
        return self
