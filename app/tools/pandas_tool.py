from __future__ import annotations

import pandas as pd


SUPPORTED_ANALYSIS_TYPES = {
    "department_failure_rate",
    "api_failure_topn",
    "average_latency",
    "failure_trend",
    "department_call_volume",
    "department_call_volume_trend",
}


def _prepare_logs(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise ValueError("没有可用于分析的数据。")

    required_columns = {
        "department",
        "project_name",
        "api_name",
        "status",
        "latency_ms",
        "request_time",
    }
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"分析数据缺少必要字段：{missing}")

    normalized = df.copy()
    normalized["status"] = normalized["status"].astype(str).str.lower().str.strip()
    normalized["latency_ms"] = pd.to_numeric(
        normalized["latency_ms"], errors="coerce"
    )
    normalized["request_time"] = pd.to_datetime(
        normalized["request_time"], errors="coerce"
    )
    normalized["is_failed"] = normalized["status"].eq("failed")
    return normalized


def _failure_rate_by(
    df: pd.DataFrame,
    group_column: str,
    top_n: int | None = None,
) -> list[dict]:
    grouped = (
        df.groupby(group_column, dropna=False)
        .agg(
            total_calls=("status", "size"),
            failed_calls=("is_failed", "sum"),
            avg_latency_ms=("latency_ms", "mean"),
        )
        .reset_index()
    )
    grouped["success_calls"] = grouped["total_calls"] - grouped["failed_calls"]
    grouped["failure_rate"] = grouped["failed_calls"] / grouped["total_calls"]
    grouped = grouped.sort_values(
        by=["failure_rate", "failed_calls", "total_calls"],
        ascending=[False, False, False],
    )
    if top_n is not None:
        grouped = grouped.head(top_n)
    grouped["failure_rate"] = (grouped["failure_rate"] * 100).round(2)
    grouped["avg_latency_ms"] = grouped["avg_latency_ms"].round(2)
    return grouped.to_dict(orient="records")


def analyze_api_logs(
    df: pd.DataFrame,
    analysis_type: str,
    top_n: int | None = None,
    days: int | None = None,
    department: str | None = None,
    project_name: str | None = None,
    api_name: str | None = None,
) -> list[dict]:
    if analysis_type not in SUPPORTED_ANALYSIS_TYPES:
        raise ValueError(f"不支持的分析类型：{analysis_type}")

    logs = _prepare_logs(df)
    if days is not None:
        latest_time = logs["request_time"].max()
        if pd.notna(latest_time):
            logs = logs[logs["request_time"] >= latest_time - pd.Timedelta(days=days)]
    if department:
        logs = logs[logs["department"] == department]
    if project_name:
        logs = logs[logs["project_name"] == project_name]
    if api_name:
        logs = logs[logs["api_name"] == api_name]
    if logs.empty:
        raise ValueError("筛选条件下没有可用于分析的数据。")

    if analysis_type == "department_failure_rate":
        return _failure_rate_by(logs, "department", top_n)

    if analysis_type == "api_failure_topn":
        return _failure_rate_by(logs, "api_name", top_n or 10)

    if analysis_type == "average_latency":
        grouped = (
            logs.groupby("api_name", dropna=False)
            .agg(
                total_calls=("status", "size"),
                avg_latency_ms=("latency_ms", "mean"),
                max_latency_ms=("latency_ms", "max"),
            )
            .reset_index()
            .sort_values("avg_latency_ms", ascending=False)
            .head(top_n or 10)
        )
        grouped[["avg_latency_ms", "max_latency_ms"]] = grouped[
            ["avg_latency_ms", "max_latency_ms"]
        ].round(2)
        return grouped.to_dict(orient="records")

    if analysis_type == "failure_trend":
        valid_logs = logs.dropna(subset=["request_time"]).copy()
        valid_logs["date"] = valid_logs["request_time"].dt.strftime("%Y-%m-%d")
        grouped = (
            valid_logs.groupby("date")
            .agg(
                total_calls=("status", "size"),
                failed_calls=("is_failed", "sum"),
            )
            .reset_index()
            .sort_values("date")
        )
        grouped["failure_rate"] = (
            grouped["failed_calls"] / grouped["total_calls"] * 100
        ).round(2)
        return grouped.to_dict(orient="records")

    if analysis_type == "department_call_volume":
        grouped = (
            logs.groupby("department", dropna=False)
            .agg(total_calls=("status", "size"))
            .reset_index()
            .sort_values("total_calls", ascending=False)
        )
        return grouped.to_dict(orient="records")

    valid_logs = logs.dropna(subset=["request_time"]).copy()
    valid_logs["date"] = valid_logs["request_time"].dt.strftime("%Y-%m-%d")
    grouped = (
        valid_logs.groupby(["date", "department"], dropna=False)
        .agg(total_calls=("status", "size"))
        .reset_index()
        .sort_values(["date", "department"])
    )
    return grouped.to_dict(orient="records")


def calculate_department_failure_rate(
    df: pd.DataFrame,
    top_n: int | None = None,
) -> list[dict]:
    """兼容第一阶段调用的部门失败率分析入口。"""
    return analyze_api_logs(df, "department_failure_rate", top_n)
