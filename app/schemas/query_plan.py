from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.config import SQL_ALLOWED_COLUMNS


AnalysisType = Literal[
    "department_failure_rate",
    "api_failure_topn",
    "average_latency",
    "failure_trend",
    "department_call_volume",
    "department_call_volume_trend",
]

REQUIRED_COLUMNS_BY_ANALYSIS = {
    "department_failure_rate": {"department", "status"},
    "api_failure_topn": {"api_name", "status"},
    "average_latency": {"api_name", "latency_ms"},
    "failure_trend": {"request_time", "status"},
    "department_call_volume": {"department"},
    "department_call_volume_trend": {"request_time", "department"},
}


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
        normalized = list(dict.fromkeys(value))
        unknown = set(normalized) - SQL_ALLOWED_COLUMNS
        if unknown:
            raise ValueError(f"包含未授权字段：{', '.join(sorted(unknown))}")
        return normalized

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, value: dict[str, Any]) -> dict[str, Any]:
        allowed_filters = {"days", "department", "project_name", "api_name"}
        unknown = set(value) - allowed_filters
        if unknown:
            raise ValueError(f"包含不支持的筛选条件：{', '.join(sorted(unknown))}")
        return value

    @model_validator(mode="after")
    def validate_intent_matches_analysis(self) -> "QueryPlan":
        if self.intent != self.analysis_type:
            raise ValueError("intent 与 analysis_type 必须一致。")
        missing = REQUIRED_COLUMNS_BY_ANALYSIS[self.analysis_type] - set(
            self.required_columns
        )
        if missing:
            raise ValueError(
                f"required_columns 缺少分析必需字段：{', '.join(sorted(missing))}"
            )
        return self
