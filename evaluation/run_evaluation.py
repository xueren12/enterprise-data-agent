from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.nodes.parse_node import parse_question_node
from app.services.agent_service import build_initial_state
from app.services.llm_service import fallback_query_plan, fallback_select_sql
from app.services.safety_service import validate_select_sql, validate_sql_matches_plan
from evaluation.cases import build_fallback_cases, build_query_cases


DEFAULT_OUTPUT_PATH = ROOT_DIR / "evaluation" / "results" / "latest.json"


def _rate(success: int, total: int) -> float:
    return round(success / total * 100, 2) if total else 0.0


def _execute_readonly_sql(sql: str, database_url: str) -> int:
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                connection.execute(text("SET LOCAL statement_timeout = 5000"))
                return len(connection.execute(text(sql)).mappings().all())
    finally:
        engine.dispose()


def evaluate(database_url: str | None = None) -> dict[str, Any]:
    plan_cases = build_query_cases()
    fallback_cases = build_fallback_cases()
    plan_success = 0
    sql_validation_success = 0
    sql_execution_success = 0
    sql_execution_attempted = 0
    fallback_success = 0
    failures: list[dict[str, str]] = []

    for case in plan_cases:
        parsed = parse_question_node(build_initial_state(case.question))
        if (
            parsed["error"] is not None
            or parsed["intent"] != case.expected_intent
            or parsed["analysis_params"] != case.expected_params
        ):
            failures.append(
                {
                    "case_id": case.case_id,
                    "stage": "parse_question",
                    "detail": str(
                        {
                            "intent": parsed["intent"],
                            "params": parsed["analysis_params"],
                            "error": parsed["error"],
                        }
                    ),
                }
            )
            continue

        try:
            plan = fallback_query_plan(
                parsed["intent"], "postgresql", parsed["analysis_params"]
            )
        except ValueError as exc:
            failures.append(
                {"case_id": case.case_id, "stage": "query_plan", "detail": str(exc)}
            )
            continue

        plan_success += 1
        sql = fallback_select_sql(plan)
        validation = validate_select_sql(sql, max_limit=200)
        plan_error = (
            validate_sql_matches_plan(
                validation.sql,
                required_columns=plan.required_columns,
                filters=plan.filters,
            )
            if validation.is_safe
            else validation.error
        )
        if not validation.is_safe or plan_error:
            failures.append(
                {
                    "case_id": case.case_id,
                    "stage": "sql_validation",
                    "detail": plan_error or validation.error or "未知校验失败",
                }
            )
            continue

        sql_validation_success += 1
        if not database_url:
            continue
        sql_execution_attempted += 1
        try:
            row_count = _execute_readonly_sql(validation.sql, database_url)
            if row_count:
                sql_execution_success += 1
            else:
                failures.append(
                    {
                        "case_id": case.case_id,
                        "stage": "sql_execution",
                        "detail": "查询成功但没有返回数据",
                    }
                )
        except SQLAlchemyError as exc:
            failures.append(
                {
                    "case_id": case.case_id,
                    "stage": "sql_execution",
                    "detail": str(exc),
                }
            )

    for case in fallback_cases:
        parsed = parse_question_node(build_initial_state(case.question))
        if parsed["error"] and parsed["intent"] == "unknown":
            fallback_success += 1
        else:
            failures.append(
                {
                    "case_id": case.case_id,
                    "stage": "fallback",
                    "detail": "未进入预期 fallback 分支",
                }
            )

    return {
        "mode": (
            "offline_deterministic_with_postgresql"
            if database_url
            else "offline_deterministic"
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "query_plan": {
            "total": len(plan_cases),
            "success": plan_success,
            "success_rate": _rate(plan_success, len(plan_cases)),
        },
        "sql_validation": {
            "total": len(plan_cases),
            "success": sql_validation_success,
            "success_rate": _rate(sql_validation_success, len(plan_cases)),
        },
        "sql_execution": {
            "attempted": sql_execution_attempted,
            "success": sql_execution_success,
            "success_rate": _rate(sql_execution_success, sql_execution_attempted),
            "skipped": database_url is None,
        },
        "fallback": {
            "total": len(fallback_cases),
            "success": fallback_success,
            "success_rate": _rate(fallback_success, len(fallback_cases)),
        },
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="运行企业数据 Agent 离线评测")
    parser.add_argument(
        "--database-url",
        help="可选。提供后会实际执行受控 SQL，并统计 SQL 执行成功率。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="评测 JSON 结果路径。",
    )
    args = parser.parse_args()
    result = evaluate(args.database_url)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not result["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
