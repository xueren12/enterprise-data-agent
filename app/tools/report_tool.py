from __future__ import annotations

from pathlib import Path


INTENT_NAMES = {
    "department_failure_rate": "各部门接口调用失败率",
    "api_failure_topn": "高失败率接口 TopN",
    "average_latency": "接口平均响应时间",
    "failure_trend": "接口失败率趋势",
    "department_call_volume": "各部门接口调用量",
    "department_call_volume_trend": "各部门接口调用量变化",
}


def generate_analysis_report(
    question: str,
    analysis_result: list[dict],
    chart_path: str,
    analysis_type: str,
) -> str:
    if not analysis_result:
        return (
            "## 分析目标\n"
            f"{question}\n\n"
            "## 核心结论\n"
            "当前数据不足以支持该结论。\n\n"
            "## 下一步建议\n"
            "请检查数据源、筛选条件和字段完整性。"
        )

    first = analysis_result[0]
    intent_name = INTENT_NAMES.get(analysis_type, analysis_type)

    if analysis_type in {"department_failure_rate", "api_failure_topn"}:
        highest_rate = first["failure_rate"]
        leaders = [
            row.get("department") or row.get("api_name")
            for row in analysis_result
            if row["failure_rate"] == highest_rate
        ]
        if len(leaders) == 1:
            conclusion = (
                f"{leaders[0]} 的失败率最高，为 {highest_rate:.2f}%，"
                f"共调用 {first['total_calls']} 次、失败 {first['failed_calls']} 次。"
            )
        else:
            conclusion = (
                f"{'、'.join(leaders)} 并列最高，失败率均为 "
                f"{highest_rate:.2f}%。"
            )
    elif analysis_type == "average_latency":
        highest_latency = first["avg_latency_ms"]
        leaders = [
            row["api_name"]
            for row in analysis_result
            if row["avg_latency_ms"] == highest_latency
        ]
        conclusion = (
            f"{'、'.join(leaders)} 的平均响应时间最高，为 "
            f"{highest_latency:.2f} ms。"
        )
    elif analysis_type == "failure_trend":
        highest = max(analysis_result, key=lambda row: row["failure_rate"])
        conclusion = (
            f"{highest['date']} 的失败率最高，为 "
            f"{highest['failure_rate']:.2f}%。"
        )
    elif analysis_type == "department_call_volume":
        conclusion = (
            f"{first['department']} 的接口调用量最高，共 "
            f"{first['total_calls']} 次。"
        )
    else:
        peak = max(analysis_result, key=lambda row: row["total_calls"])
        conclusion = (
            f"{peak['date']} 的 {peak['department']} 调用量最高，"
            f"为 {peak['total_calls']} 次。"
        )

    columns = list(first.keys())
    table = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in analysis_result:
        table.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")

    return (
        "## 分析目标\n"
        f"{question}\n\n"
        "## 核心结论\n"
        f"{conclusion}\n\n"
        "## 数据依据\n"
        f"分析类型：{intent_name}\n\n"
        + "\n".join(table)
        + "\n\n"
        "## 异常发现\n"
        "结果已按核心指标排序，排名靠前的对象需要优先关注。\n\n"
        "## 业务建议\n"
        "建议结合错误码、错误信息、发布时间和流量变化进一步定位原因。\n\n"
        "## 图表路径\n"
        f"{Path(chart_path)}"
    )


def generate_failure_rate_report(
    question: str,
    analysis_result: list[dict],
    chart_path: str,
) -> str:
    return generate_analysis_report(
        question,
        analysis_result,
        chart_path,
        "department_failure_rate",
    )


def save_report(report: str, output_dir: str | Path, trace_id: str) -> str:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report_path = output_path / f"{trace_id}_report.md"
    report_path.write_text(report, encoding="utf-8")
    return str(report_path)
