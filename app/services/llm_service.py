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
from app.catalog.field_resolver import (
    columns_for_filters,
    resolve_filter_field,
    validate_filter_fields,
)
from app.catalog.metric_registry import get_metric_definition, get_metric_prompt_summary
from app.catalog.schema_registry import get_queryable_columns, get_table
from app.schemas.query_plan import QueryPlan


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
    metric = get_metric_definition(intent)
    filters = validate_filter_fields(
        params,
        allowed_filters=metric.allowed_filters,
    )
    required_columns = list(metric.required_columns)
    for column in columns_for_filters(filters):
        if column not in required_columns:
            required_columns.append(column)

    return QueryPlan(
        intent=intent,
        data_source_type=data_source_type,
        analysis_type=intent,
        filters=filters,
        top_n=top_n or metric.default_top_n,
        required_columns=required_columns,
        need_chart=metric.need_chart,
        need_report=metric.need_report,
    )


def fallback_query_plan_from_question(
    question: str,
    data_source_type: str,
) -> QueryPlan:
    """模型故障后的离线规则规划路径，不参与正常模型规划。"""
    from app.nodes.parse_node import SUPPORTED_INTENTS, infer_intent_and_params

    intent, params = infer_intent_and_params(question)
    if intent not in SUPPORTED_INTENTS:
        raise ValueError(
            "暂时支持失败率、失败接口 TopN、平均响应时间、失败趋势和部门调用量分析。"
        )
    return fallback_query_plan(intent, data_source_type, params)


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


def _catalog_prompt_summary(table_name: str = "api_call_logs") -> str:
    table = get_table(table_name)
    queryable_columns = get_queryable_columns(table_name)
    lines = [
        f"表：{table.name}",
        f"描述：{table.description}",
        "允许查询字段：",
    ]
    for field_name, field in table.fields.items():
        if field_name in queryable_columns:
            lines.append(f"- {field_name}：{field.description}，类型 {field.type}")
    return "\n".join(lines)


def _dimension_prompt_summary() -> str:
    """演示数据的受控维度值，帮助模型选择正确的筛选字段。"""
    return "\n".join(
        (
            "部门：销售部、财务部、运维部、风控部、平台部。",
            "项目：客户关系系统、财务系统、运维中心、风控系统、网关平台。",
            "接口：/api/customer/search、/api/order/create、/api/order/list、/api/invoice/create、/api/payment/reconcile、/api/budget/query、/api/device/heartbeat、/api/device/event、/api/alert/create、/api/risk/score、/api/risk/rule/check、/api/risk/report、/api/auth/token、/api/gateway/route、/api/health。",
            "筛选字段必须匹配实体类型：部门用 department，项目用 project_name，接口用 api_name。",
        )
    )


def fallback_select_sql(query_plan: QueryPlan | dict[str, Any]) -> str:
    plan = QueryPlan.model_validate(query_plan)
    columns = ", ".join(plan.required_columns)
    clauses: list[str] = []

    if days := plan.filters.get("days"):
        clauses.append(
            "request_time >= (SELECT MAX(request_time) FROM api_call_logs) "
            f"- INTERVAL '{int(days)} days'"
        )
    for filter_name, filter_value in plan.filters.items():
        if filter_name == "days":
            continue
        column = resolve_filter_field(filter_name)
        value = _escape_sql_literal(str(filter_value))
        clauses.append(f"{column} = '{value}'")

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
        catalog_fields=_catalog_prompt_summary(),
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
        catalog_fields=_catalog_prompt_summary(),
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


def generate_query_plan(question: str, data_source_type: str) -> dict:
    """让模型在 Registry 白名单内规划，失败时才使用规则兜底。"""
    prompt = read_prompt("query_plan_prompt.txt").format(
        question=question,
        data_source_type=data_source_type,
        catalog_fields=_catalog_prompt_summary(),
        metric_definitions=get_metric_prompt_summary(),
        dimension_values=_dimension_prompt_summary(),
    )
    try:
        content = call_deepseek(prompt, temperature=0)
        plan = QueryPlan.model_validate(_extract_json_object(content))
        if plan.data_source_type != data_source_type:
            raise ValueError("模型计划的数据源与系统已选择的数据源不一致。")
        return {"used_llm": True, "content": plan, "error": None}
    except Exception as exc:
        try:
            fallback_plan = fallback_query_plan_from_question(question, data_source_type)
        except Exception as fallback_exc:
            return {
                "used_llm": False,
                "content": None,
                "error": f"模型规划失败：{exc}；规则兜底失败：{fallback_exc}",
            }
        return {
            "used_llm": False,
            "content": fallback_plan,
            "error": str(exc),
        }


def generate_report_with_llm(
    *,
    question: str,
    analysis_result: list[dict],
    chart_url: str,
    fallback_report: str,
) -> dict:
    prompt = read_prompt("report_prompt.txt").format(
        question=question,
        analysis_result=json.dumps(analysis_result, ensure_ascii=False, indent=2),
        chart_url=chart_url,
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
