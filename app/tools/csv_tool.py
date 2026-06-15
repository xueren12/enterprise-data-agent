from pathlib import Path

import pandas as pd


REQUIRED_API_LOG_COLUMNS = {
    "id",
    "department",
    "project_name",
    "api_name",
    "status",
    "status_code",
    "latency_ms",
    "request_time",
    "error_message",
}


def read_api_logs(csv_path: str | Path) -> pd.DataFrame:
    """读取接口调用日志 CSV，并校验 MVP 所需字段。"""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV 文件不存在：{path}")

    df = pd.read_csv(path)
    missing_columns = REQUIRED_API_LOG_COLUMNS - set(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"CSV 缺少必要字段：{missing}")

    if df.empty:
        raise ValueError("CSV 没有任何数据行。")

    return df
