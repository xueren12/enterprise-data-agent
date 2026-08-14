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

from app.nodes.parse_node import infer_intent_and_params
from app.services.llm_service import (
    fallback_query_plan,
    fallback_query_plan_from_question,
    fallback_select_sql,
    generate_query_plan,
    is_deepseek_enabled,
)
from app.services.safety_service import validate_select_sql, validate_sql_matches_plan
from evaluation.cases import build_fallback_cases, build_query_cases


GOLD_DATASET_PATH = ROOT_DIR / "evaluation" / "datasets" / "query_plan_gold.jsonl"
RULE_OUTPUT_PATH = ROOT_DIR / "evaluation" / "results" / "rule-safety-latest.json"
LLM_OUTPUT_PATH = ROOT_DIR / "evaluation" / "results" / "llm-query-plan-latest.json"


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


def _validate_controlled_sql(plan: Any) -> tuple[str | None, str | None]:
    sql = fallback_select_sql(plan)
    validation = validate_select_sql(sql, max_limit=200)
    if not validation.is_safe:
        return None, validation.error or "SQL 安全校验失败"
    plan_error = validate_sql_matches_plan(
        validation.sql,
        required_columns=plan.required_columns,
        filters=plan.filters,
    )
    return validation.sql, plan_error


def load_gold_cases() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in GOLD_DATASET_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _matches_gold(plan: Any, expected: dict[str, Any]) -> bool:
    return (
        plan.intent == expected["intent"]
        and plan.analysis_type == expected["intent"]
        and plan.filters == expected["filters"]
        and plan.top_n == expected["top_n"]
    )


def evaluate_rule_safety(database_url: str | None = None) -> dict[str, Any]:
    """验证规则兜底与受控 SQL，不将结果描述为模型准确率。"""
    plan_cases = build_query_cases()
    fallback_cases = build_fallback_cases()
    rule_plan_success = 0
    sql_validation_success = 0
    sql_execution_success = 0
    sql_execution_attempted = 0
    fallback_success = 0
    failures: list[dict[str, str]] = []

    for case in plan_cases:
        intent, params = infer_intent_and_params(case.question)
        if intent != case.expected_intent or params != case.expected_params:
            failures.append(
                {
                    "case_id": case.case_id,
                    "stage": "rule_parse",
                    "detail": str({"intent": intent, "params": params}),
                }
            )
            continue
        plan = fallback_query_plan(intent, "postgresql", params)
        rule_plan_success += 1
        sql, error = _validate_controlled_sql(plan)
        if error or sql is None:
            failures.append(
                {
                    "case_id": case.case_id,
                    "stage": "controlled_sql_validation",
                    "detail": error or "未知校验失败",
                }
            )
            continue
        sql_validation_success += 1
        if not database_url:
            continue
        sql_execution_attempted += 1
        try:
            if _execute_readonly_sql(sql, database_url):
                sql_execution_success += 1
            else:
                failures.append(
                    {"case_id": case.case_id, "stage": "sql_execution", "detail": "查询结果为空"}
                )
        except SQLAlchemyError as exc:
            failures.append(
                {"case_id": case.case_id, "stage": "sql_execution", "detail": str(exc)}
            )

    for case in fallback_cases:
        try:
            fallback_query_plan_from_question(case.question, "postgresql")
            failures.append(
                {"case_id": case.case_id, "stage": "fallback", "detail": "规则不应支持该问题"}
            )
        except ValueError:
            fallback_success += 1

    return {
        "mode": "rule_safety_with_postgresql" if database_url else "rule_safety",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "这是确定性规则与受控 SQL 回归集，不代表 LLM 自然语言理解准确率。",
        "rule_plan": {"total": len(plan_cases), "success": rule_plan_success, "success_rate": _rate(rule_plan_success, len(plan_cases))},
        "controlled_sql_validation": {"total": len(plan_cases), "success": sql_validation_success, "success_rate": _rate(sql_validation_success, len(plan_cases))},
        "controlled_sql_execution": {"attempted": sql_execution_attempted, "success": sql_execution_success, "success_rate": _rate(sql_execution_success, sql_execution_attempted), "skipped": database_url is None},
        "fallback": {"total": len(fallback_cases), "success": fallback_success, "success_rate": _rate(fallback_success, len(fallback_cases))},
        "failures": failures,
    }


def evaluate_llm_query_plans(database_url: str | None = None) -> dict[str, Any]:
    """真实调用 DeepSeek，并和人工标注的 QueryPlan 金标逐条比较。"""
    if not is_deepseek_enabled():
        raise RuntimeError("未配置 DEEPSEEK_API_KEY，无法运行真实 LLM 评测。")

    cases = load_gold_cases()
    model_valid = 0
    semantic_match = 0
    sql_validation_success = 0
    sql_execution_success = 0
    sql_execution_attempted = 0
    failures: list[dict[str, str]] = []

    for case in cases:
        result = generate_query_plan(case["question"], "postgresql")
        plan = result["content"]
        if not result["used_llm"] or plan is None:
            failures.append(
                {"case_id": case["case_id"], "stage": "llm_plan", "detail": result["error"] or "模型未返回有效计划"}
            )
            continue
        model_valid += 1
        if not _matches_gold(plan, case["expected_plan"]):
            failures.append(
                {
                    "case_id": case["case_id"],
                    "stage": "semantic_match",
                    "detail": json.dumps(plan.model_dump(), ensure_ascii=False),
                }
            )
            continue
        semantic_match += 1
        sql, error = _validate_controlled_sql(plan)
        if error or sql is None:
            failures.append(
                {"case_id": case["case_id"], "stage": "controlled_sql_validation", "detail": error or "未知校验失败"}
            )
            continue
        sql_validation_success += 1
        if not database_url:
            continue
        sql_execution_attempted += 1
        try:
            if _execute_readonly_sql(sql, database_url):
                sql_execution_success += 1
            else:
                failures.append(
                    {"case_id": case["case_id"], "stage": "sql_execution", "detail": "查询结果为空"}
                )
        except SQLAlchemyError as exc:
            failures.append(
                {"case_id": case["case_id"], "stage": "sql_execution", "detail": str(exc)}
            )

    return {
        "mode": "llm_query_plan_with_postgresql" if database_url else "llm_query_plan",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "DeepSeek API（由当前环境变量 DEEPSEEK_MODEL 指定）",
        "dataset": str(GOLD_DATASET_PATH.relative_to(ROOT_DIR)).replace("\\", "/"),
        "model_query_plan_validation": {"total": len(cases), "success": model_valid, "success_rate": _rate(model_valid, len(cases))},
        "semantic_match_to_human_gold": {"total": len(cases), "success": semantic_match, "success_rate": _rate(semantic_match, len(cases))},
        "controlled_sql_validation_after_semantic_match": {"total": semantic_match, "success": sql_validation_success, "success_rate": _rate(sql_validation_success, semantic_match)},
        "controlled_sql_execution_after_semantic_match": {"attempted": sql_execution_attempted, "success": sql_execution_success, "success_rate": _rate(sql_execution_success, sql_execution_attempted), "skipped": database_url is None},
        "failures": failures,
    }


# 保留导入入口，供已有测试和外部脚本调用。
def evaluate(database_url: str | None = None) -> dict[str, Any]:
    return evaluate_rule_safety(database_url)


def main() -> int:
    parser = argparse.ArgumentParser(description="运行企业数据 Agent 评测")
    parser.add_argument("--mode", choices=("rule", "llm"), default="rule")
    parser.add_argument("--database-url", help="可选。提供后会实际执行受控 SQL。")
    parser.add_argument("--output", type=Path, help="评测 JSON 输出路径。")
    args = parser.parse_args()
    try:
        result = (
            evaluate_llm_query_plans(args.database_url)
            if args.mode == "llm"
            else evaluate_rule_safety(args.database_url)
        )
    except RuntimeError as exc:
        print(f"评测未运行：{exc}", file=sys.stderr)
        return 2

    output_path = args.output or (LLM_OUTPUT_PATH if args.mode == "llm" else RULE_OUTPUT_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not result["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
