from app.config import SQL_ALLOWED_COLUMNS, SQL_ALLOWED_TABLES
from app.services.safety_service import validate_select_sql


def validate(sql: str, max_limit: int = 100):
    return validate_select_sql(
        sql,
        allowed_tables=SQL_ALLOWED_TABLES,
        allowed_columns=SQL_ALLOWED_COLUMNS,
        max_limit=max_limit,
    )


def test_valid_select_adds_limit():
    result = validate(
        "SELECT department, status, latency_ms FROM api_call_logs"
    )

    assert result.is_safe is True
    assert "LIMIT 100" in result.sql


def test_large_limit_is_reduced():
    result = validate(
        "SELECT department FROM api_call_logs LIMIT 500",
        max_limit=50,
    )

    assert result.is_safe is True
    assert "LIMIT 50" in result.sql


def test_rejects_dangerous_statement():
    result = validate("DELETE FROM api_call_logs")

    assert result.is_safe is False
    assert "禁止" in result.error


def test_rejects_multiple_statements():
    result = validate(
        "SELECT department FROM api_call_logs; "
        "SELECT status FROM api_call_logs"
    )

    assert result.is_safe is False
    assert "多条" in result.error


def test_rejects_comments():
    result = validate("SELECT department FROM api_call_logs -- 绕过校验")

    assert result.is_safe is False
    assert "注释" in result.error


def test_rejects_unknown_table():
    result = validate("SELECT department FROM users")

    assert result.is_safe is False
    assert "未授权的数据表" in result.error


def test_rejects_unknown_column():
    result = validate("SELECT password FROM api_call_logs")

    assert result.is_safe is False
    assert "未授权的字段" in result.error


def test_rejects_sensitive_column():
    result = validate("SELECT error_message FROM api_call_logs")

    assert result.is_safe is False
    assert "敏感字段" in result.error


def test_rejects_wildcard():
    result = validate("SELECT * FROM api_call_logs")

    assert result.is_safe is False
    assert "不允许直接查询 *" in result.error


def test_allows_count_wildcard():
    result = validate(
        "SELECT department, COUNT(*) AS total_calls "
        "FROM api_call_logs GROUP BY department"
    )

    assert result.is_safe is True
    assert "COUNT(*)" in result.sql
    assert "LIMIT 100" in result.sql
