from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.config import DATABASE_URL, SQL_STATEMENT_TIMEOUT_MS


class DatabaseServiceError(RuntimeError):
    """数据库服务对外暴露的友好异常。"""


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    if not DATABASE_URL:
        raise DatabaseServiceError("未配置 DATABASE_URL，当前无法连接 PostgreSQL。")

    try:
        return create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
    except (SQLAlchemyError, ValueError) as exc:
        raise DatabaseServiceError("数据库连接配置无效，请检查 DATABASE_URL。") from exc


def execute_select(sql: str) -> list[dict]:
    try:
        engine = get_engine()
        with engine.connect() as connection:
            with connection.begin():
                # SQL 校验之外，再由数据库事务保证本次连接只读并限制耗时。
                connection.execute(text("SET TRANSACTION READ ONLY"))
                connection.execute(
                    text(
                        "SET LOCAL statement_timeout = "
                        f"{max(1, SQL_STATEMENT_TIMEOUT_MS)}"
                    )
                )
                result = connection.execute(text(sql))
                return [dict(row) for row in result.mappings().all()]
    except DatabaseServiceError:
        raise
    except SQLAlchemyError as exc:
        raise DatabaseServiceError(
            "数据库查询失败，请检查数据库状态、查询字段和筛选条件。"
        ) from exc
