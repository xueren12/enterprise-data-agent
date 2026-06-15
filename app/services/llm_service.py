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
)


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


def fallback_query_plan(intent: str, data_source_type: str) -> str:
    source_name = "PostgreSQL 数据库" if data_source_type == "postgresql" else "CSV 文件"
    analysis_steps = {
        "department_failure_rate": "按部门统计调用总数、失败数、成功数和失败率",
        "api_failure_topn": "按接口统计失败率，并按失败率降序选取 TopN",
        "average_latency": "按接口统计平均耗时和最大耗时，并按平均耗时降序排列",
        "failure_trend": "按日期统计调用数、失败数和失败率，形成时间趋势",
        "department_call_volume": "按部门统计接口调用总数并降序排列",
        "department_call_volume_trend": "按日期和部门统计接口调用量变化",
    }
    analysis_step = analysis_steps.get(intent, "根据问题执行结构化数据分析")
    return (
        f"1. 从{source_name}读取企业接口调用日志。\n"
        "2. 校验部门、接口、状态、耗时和请求时间等必要字段。\n"
        f"3. 使用 Pandas {analysis_step}。\n"
        "4. 校验分析结果是否为空以及指标是否可计算。\n"
        "5. 生成对应图表和结构化分析报告。"
    )


def fallback_select_sql() -> str:
    return (
        "SELECT id, department, project_name, api_name, status, status_code, "
        "latency_ms, request_time, error_message "
        "FROM api_call_logs ORDER BY request_time DESC LIMIT 200"
    )


def generate_select_sql(question: str, intent: str) -> dict:
    prompt = read_prompt("sql_generate_prompt.txt").format(
        question=question,
        intent=intent,
    )
    try:
        content = call_deepseek(prompt, temperature=0)
        content = content.removeprefix("```sql").removeprefix("```").removesuffix("```").strip()
        return {"used_llm": True, "content": content, "error": None}
    except Exception as exc:
        return {
            "used_llm": False,
            "content": fallback_select_sql(),
            "error": str(exc),
        }


def generate_query_plan(
    question: str,
    intent: str,
    data_source_type: str,
) -> dict:
    prompt = read_prompt("query_plan_prompt.txt").format(
        question=question,
        intent=intent,
        data_source_type=data_source_type,
    )
    try:
        content = call_deepseek(prompt)
        return {"used_llm": True, "content": content, "error": None}
    except Exception as exc:
        return {
            "used_llm": False,
            "content": fallback_query_plan(intent, data_source_type),
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
