from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


INTEGRATION_DATABASE_URL = os.getenv("INTEGRATION_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not INTEGRATION_DATABASE_URL,
    reason="未配置 INTEGRATION_DATABASE_URL，跳过 PostgreSQL 集成测试。",
)


def test_postgresql_loads_large_synthetic_dataset():
    engine = create_engine(INTEGRATION_DATABASE_URL)
    try:
        with engine.connect() as connection:
            count = connection.execute(
                text("SELECT COUNT(*) FROM api_call_logs")
            ).scalar_one()
    finally:
        engine.dispose()

    assert count >= 5_000


def test_readonly_application_role_cannot_insert_records():
    engine = create_engine(INTEGRATION_DATABASE_URL)
    try:
        with engine.connect() as connection:
            with pytest.raises(SQLAlchemyError):
                connection.execute(
                    text(
                        "INSERT INTO api_call_logs "
                        "(id, department, project_name, api_name, status, "
                        "status_code, latency_ms, request_time) "
                        "VALUES (999999, '测试', '测试', '/api/test', 'success', "
                        "200, 1, CURRENT_TIMESTAMP)"
                    )
                )
    finally:
        engine.dispose()
