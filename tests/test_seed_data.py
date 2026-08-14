from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parent.parent


def test_postgresql_seed_uses_canonical_large_synthetic_dataset():
    csv_path = ROOT_DIR / "data" / "sample_api_logs.csv"
    init_sql = (ROOT_DIR / "data" / "init.sql").read_text(encoding="utf-8")

    assert len(pd.read_csv(csv_path)) >= 5_000
    assert "COPY api_call_logs" in init_sql
    assert "sample_api_logs.csv" in init_sql
    assert "INSERT INTO api_call_logs" not in init_sql


def test_synthetic_dataset_contains_time_range_and_injected_anomalies():
    csv_path = ROOT_DIR / "data" / "sample_api_logs.csv"
    logs = pd.read_csv(csv_path, parse_dates=["request_time"])

    assert logs["request_time"].max() - logs["request_time"].min() >= pd.Timedelta(days=170)
    risk_score = logs[logs["api_name"] == "/api/risk/score"]
    assert (risk_score["status"] == "failed").mean() > 0.06


def test_postgresql_seed_creates_readonly_application_role():
    init_sql = (ROOT_DIR / "data" / "init.sql").read_text(encoding="utf-8")

    assert "CREATE ROLE agent_reader LOGIN" in init_sql
    assert "GRANT SELECT ON TABLE api_call_logs TO agent_reader" in init_sql
