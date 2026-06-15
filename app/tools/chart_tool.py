from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "Arial Unicode MS",
    "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False


CHART_CONFIGS = {
    "department_failure_rate": {
        "x": "department",
        "y": "failure_rate",
        "title": "各部门接口调用失败率",
        "xlabel": "部门",
        "ylabel": "失败率 (%)",
        "type": "bar",
    },
    "api_failure_topn": {
        "x": "api_name",
        "y": "failure_rate",
        "title": "接口失败率 TopN",
        "xlabel": "接口",
        "ylabel": "失败率 (%)",
        "type": "bar",
    },
    "average_latency": {
        "x": "api_name",
        "y": "avg_latency_ms",
        "title": "接口平均响应时间",
        "xlabel": "接口",
        "ylabel": "平均耗时 (ms)",
        "type": "bar",
    },
    "failure_trend": {
        "x": "date",
        "y": "failure_rate",
        "title": "接口失败率趋势",
        "xlabel": "日期",
        "ylabel": "失败率 (%)",
        "type": "line",
    },
    "department_call_volume": {
        "x": "department",
        "y": "total_calls",
        "title": "各部门接口调用量",
        "xlabel": "部门",
        "ylabel": "调用次数",
        "type": "bar",
    },
    "department_call_volume_trend": {
        "x": "date",
        "y": "total_calls",
        "title": "各部门接口调用量变化",
        "xlabel": "日期",
        "ylabel": "调用次数",
        "type": "multi_line",
    },
}


def generate_analysis_chart(
    analysis_result: list[dict],
    output_dir: str | Path,
    trace_id: str,
    analysis_type: str,
) -> str:
    if not analysis_result:
        raise ValueError("没有可用于生成图表的分析结果。")
    if analysis_type not in CHART_CONFIGS:
        raise ValueError(f"不支持的图表分析类型：{analysis_type}")

    config = CHART_CONFIGS[analysis_type]
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    chart_path = output_path / f"{trace_id}_{analysis_type}.png"

    plt.figure(figsize=(10, 5.5))
    if config["type"] == "multi_line":
        departments = sorted({str(item["department"]) for item in analysis_result})
        for department in departments:
            rows = [
                item for item in analysis_result if str(item["department"]) == department
            ]
            plt.plot(
                [str(item["date"]) for item in rows],
                [float(item["total_calls"]) for item in rows],
                marker="o",
                linewidth=2,
                label=department,
            )
        plt.legend()
    else:
        labels = [str(item[config["x"]]) for item in analysis_result]
        values = [float(item[config["y"]]) for item in analysis_result]
    if config["type"] == "line":
        plt.plot(labels, values, marker="o", color="#1677FF", linewidth=2)
    elif config["type"] == "bar":
        bars = plt.bar(labels, values, color="#1677FF")
        for bar, value in zip(bars, values, strict=True):
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{value:.2f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    plt.title(config["title"])
    plt.xlabel(config["xlabel"])
    plt.ylabel(config["ylabel"])
    plt.grid(axis="y", linestyle="--", alpha=0.3)
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(chart_path, dpi=150)
    plt.close()
    return str(chart_path)


def generate_failure_rate_bar_chart(
    analysis_result: list[dict],
    output_dir: str | Path,
    trace_id: str,
) -> str:
    """兼容第一阶段调用的部门失败率图表入口。"""
    return generate_analysis_chart(
        analysis_result,
        output_dir,
        trace_id,
        "department_failure_rate",
    )
