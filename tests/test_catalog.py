import pytest
from pydantic import ValidationError

from app.catalog.metric_registry import get_metric_definition
from app.catalog.schema_registry import get_queryable_columns, get_table
from app.schemas.query_plan import QueryPlan
from app.services.safety_service import validate_select_sql


def test_schema_registry_loads_api_call_logs_table():
    table = get_table("api_call_logs")

    assert table.name == "api_call_logs"
    assert table.fields["department"].description == "部门名称"
    assert table.fields["error_message"].sensitive is True


def test_metric_registry_returns_department_failure_rate_columns():
    metric = get_metric_definition("department_failure_rate")

    assert metric.display_name == "各部门接口调用失败率"
    assert metric.required_columns == ["department", "status"]


def test_illegal_field_cannot_enter_query_plan():
    with pytest.raises(ValidationError):
        QueryPlan(
            intent="department_failure_rate",
            data_source_type="csv",
            analysis_type="department_failure_rate",
            filters={},
            top_n=None,
            required_columns=["department", "status", "password"],
            need_chart=True,
            need_report=True,
        )


def test_sensitive_catalog_field_cannot_enter_query_plan_required_columns():
    with pytest.raises(ValidationError):
        QueryPlan(
            intent="department_failure_rate",
            data_source_type="csv",
            analysis_type="department_failure_rate",
            filters={},
            top_n=None,
            required_columns=["department", "status", "error_message"],
            need_chart=True,
            need_report=True,
        )


def test_sensitive_catalog_field_cannot_enter_query_plan_filters():
    with pytest.raises(ValidationError):
        QueryPlan(
            intent="department_failure_rate",
            data_source_type="csv",
            analysis_type="department_failure_rate",
            filters={"error_message": "timeout"},
            top_n=None,
            required_columns=["department", "status"],
            need_chart=True,
            need_report=True,
        )


def test_sensitive_field_cannot_be_selected_by_sql():
    result = validate_select_sql(
        "SELECT error_message FROM api_call_logs LIMIT 20",
        max_limit=100,
    )

    assert result.is_safe is False
    assert "敏感字段" in result.error


def test_sql_validation_uses_catalog_queryable_columns():
    queryable_columns = get_queryable_columns("api_call_logs")
    assert "error_message" not in queryable_columns

    result = validate_select_sql(
        "SELECT department, status_code FROM api_call_logs LIMIT 20",
        max_limit=100,
    )

    assert result.is_safe is True


def test_where_field_must_be_filterable():
    result = validate_select_sql(
        "SELECT department FROM api_call_logs WHERE latency_ms > 100 LIMIT 20",
        max_limit=100,
    )

    assert result.is_safe is False
    assert "不允许筛选" in result.error
