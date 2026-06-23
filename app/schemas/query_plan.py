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

        normalized = dict(value)
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
        return normalized

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
        filter_columns = {
            "days": "request_time",
            "department": "department",
            "project_name": "project_name",
            "api_name": "api_name",
        }
        missing_filter_columns = {
            filter_columns[name]
            for name in self.filters
            if filter_columns[name] not in self.required_columns
        }
        if missing_filter_columns:
            raise ValueError(
                "required_columns 缺少筛选所需字段："
                f"{', '.join(sorted(missing_filter_columns))}"
            )
        return self
