from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
from app.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    PROMPT_DIR,
    SQL_MAX_LIMIT,
)
from app.schemas.query_plan import QueryPlan, REQUIRED_COLUMNS_BY_ANALYSIS


def read_prompt(prompt_name: str) -> str:
    prompt_path = Path(PROMPT_DIR) / prompt_name
    return prompt_path.read_text(encoding="utf-8")


def is_deepseek_enabled() -> bool:
    return bool(DEEPSEEK_API_KEY)


def call_deepseek(prompt: str, temperature: float = 0.2) -> str:
    if not is_deepseek_enabled():
        raise RuntimeError("未配置 DEEPSEEK_API_KEY，跳过大模型调用。")

    url = f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "你是企业数据分析 Agent 的专业助手，只基于已提供数据生成计划和报告。",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
    }

    with httpx.Client(timeout=30) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    return data["choices"][0]["message"]["content"].strip()


def fallback_query_plan(
    intent: str,
    data_source_type: str,
    analysis_params: dict[str, Any] | None = None,
) -> QueryPlan:
    params = dict(analysis_params or {})
    top_n = params.pop("top_n", None)
    required_columns = sorted(REQUIRED_COLUMNS_BY_ANALYSIS[intent])
    filter_columns = {
        "days": "request_time",
        "department": "department",
        "project_name": "project_name",
        "api_name": "api_name",
    }
    for filter_name in params:
        column = filter_columns.get(filter_name)
        if column and column not in required_columns:
            required_columns.append(column)

    return QueryPlan(
        intent=intent,
        data_source_type=data_source_type,
        analysis_type=intent,
        filters=params,
        top_n=top_n,
        required_columns=required_columns,
        need_chart=True,
        need_report=True,
    )


def _extract_json_object(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```")
        cleaned = cleaned.removesuffix("```").strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("模型响应中未找到 JSON 对象。")
    return json.loads(cleaned[start : end + 1])


def _escape_sql_literal(value: str) -> str:
    return value.replace("'", "''")


def fallback_select_sql(query_plan: QueryPlan | dict[str, Any]) -> str:
    plan = QueryPlan.model_validate(query_plan)
    columns = ", ".join(plan.required_columns)
    clauses: list[str] = []

    if days := plan.filters.get("days"):
        clauses.append(
            f"request_time >= CURRENT_TIMESTAMP - INTERVAL '{int(days)} days'"
        )
    for filter_name in ("department", "project_name", "api_name"):
        if filter_name in plan.filters:
            value = _escape_sql_literal(str(plan.filters[filter_name]))
            clauses.append(f"{filter_name} = '{value}'")

    where_clause = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    return (
        f"SELECT {columns} FROM api_call_logs"
        f"{where_clause} LIMIT {SQL_MAX_LIMIT}"
    )


def generate_select_sql(
    question: str,
    intent: str,
    query_plan: QueryPlan | dict[str, Any],
) -> dict:
    plan = QueryPlan.model_validate(query_plan)
    prompt = read_prompt("sql_generate_prompt.txt").format(
        question=question,
        intent=intent,
        required_columns=json.dumps(plan.required_columns, ensure_ascii=False),
        filters=json.dumps(plan.filters, ensure_ascii=False, sort_keys=True),
        top_n=plan.top_n,
    )
    try:
        content = call_deepseek(prompt, temperature=0)
        content = content.removeprefix("```sql").removeprefix("```").removesuffix("```").strip()
        return {"used_llm": True, "content": content, "error": None}
    except Exception as exc:
        return {
            "used_llm": False,
            "content": fallback_select_sql(plan),
            "error": str(exc),
        }


def repair_select_sql(
    *,
    question: str,
    intent: str,
    query_plan: QueryPlan | dict[str, Any],
    original_sql: str,
    validation_error: str,
) -> dict:
    plan = QueryPlan.model_validate(query_plan)
    prompt = read_prompt("sql_repair_prompt.txt").format(
        question=question,
        intent=intent,
        required_columns=json.dumps(plan.required_columns, ensure_ascii=False),
        filters=json.dumps(plan.filters, ensure_ascii=False, sort_keys=True),
        top_n=plan.top_n,
        original_sql=original_sql,
        validation_error=validation_error,
    )
    try:
        content = call_deepseek(prompt, temperature=0)
        content = content.removeprefix("```sql").removeprefix("```")
        content = content.removesuffix("```").strip()
        return {"used_llm": True, "content": content, "error": None}
    except Exception as exc:
        return {
            "used_llm": False,
            "content": fallback_select_sql(plan),
            "error": str(exc),
        }


def generate_query_plan(
    question: str,
    intent: str,
    data_source_type: str,
    analysis_params: dict[str, Any] | None = None,
) -> dict:
    fallback_plan = fallback_query_plan(intent, data_source_type, analysis_params)
    prompt = read_prompt("query_plan_prompt.txt").format(
        question=question,
        intent=intent,
        data_source_type=data_source_type,
        analysis_params=json.dumps(
            analysis_params or {},
            ensure_ascii=False,
            sort_keys=True,
        ),
    )
    try:
        content = call_deepseek(prompt)
        plan = QueryPlan.model_validate(_extract_json_object(content))
        if plan.data_source_type != data_source_type:
            raise ValueError("模型计划的数据源与系统已选择的数据源不一致。")
        expected_params = dict(analysis_params or {})
        expected_top_n = expected_params.pop("top_n", None)
        if plan.intent != intent or plan.analysis_type != intent:
            raise ValueError("模型计划不得覆盖规则解析出的意图。")
        if plan.filters != expected_params or plan.top_n != expected_top_n:
            raise ValueError("模型计划不得覆盖规则解析出的筛选参数。")
        return {"used_llm": True, "content": plan, "error": None}
    except Exception as exc:
        return {
            "used_llm": False,
            "content": fallback_plan,
            "error": str(exc),
        }


def generate_report_with_llm(
    *,
    question: str,
    analysis_result: list[dict],
    chart_path: str,
    fallback_report: str,
) -> dict:
    prompt = read_prompt("report_prompt.txt").format(
        question=question,
        analysis_result=json.dumps(analysis_result, ensure_ascii=False, indent=2),
        chart_path=chart_path,
    )
    try:
        content = call_deepseek(prompt)
        return {"used_llm": True, "content": content, "error": None}
    except Exception as exc:
        return {
            "used_llm": False,
            "content": fallback_report,
            "error": str(exc),
        }


def summarize_llm_usage(result: dict[str, Any]) -> str:
    if result.get("used_llm"):
        return "已使用 DeepSeek 生成。"
    return f"未使用 DeepSeek，已采用本地兜底。原因：{result.get('error')}"
