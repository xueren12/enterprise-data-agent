from __future__ import annotations

from dataclasses import dataclass


DEPARTMENTS = ("销售部", "财务部", "运维部", "风控部", "平台部")
TOP_NS = (3, 5, 10, 15, 20)
DAYS = (7, 14, 30, 60, 90)


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    question: str
    expected_intent: str
    expected_params: dict[str, int | str]


@dataclass(frozen=True)
class FallbackCase:
    case_id: str
    question: str


def build_query_cases() -> tuple[EvaluationCase, ...]:
    """构造固定的 150 条合成问题，避免依赖外部 LLM 响应。"""
    cases: list[EvaluationCase] = []
    for round_index in range(5):
        for department_index, department in enumerate(DEPARTMENTS):
            top_n = TOP_NS[(round_index + department_index) % len(TOP_NS)]
            days = DAYS[(round_index + department_index) % len(DAYS)]
            batch = round_index + 1
            cases.extend(
                (
                    EvaluationCase(
                        f"plan-{len(cases) + 1:03d}",
                        f"统计{department}接口调用失败率，生成分析报告（批次{batch}）",
                        "department_failure_rate",
                        {"department": department},
                    ),
                    EvaluationCase(
                        f"plan-{len(cases) + 2:03d}",
                        f"找出{department}失败率最高的接口 Top{top_n}（批次{batch}）",
                        "api_failure_topn",
                        {"department": department, "top_n": top_n},
                    ),
                    EvaluationCase(
                        f"plan-{len(cases) + 3:03d}",
                        f"分析{department}平均响应时间最高的接口 Top{top_n}（批次{batch}）",
                        "average_latency",
                        {"department": department, "top_n": top_n},
                    ),
                    EvaluationCase(
                        f"plan-{len(cases) + 4:03d}",
                        f"分析最近{days}天{department}接口失败率趋势（批次{batch}）",
                        "failure_trend",
                        {"days": days, "department": department},
                    ),
                    EvaluationCase(
                        f"plan-{len(cases) + 5:03d}",
                        f"统计{department}接口调用量（批次{batch}）",
                        "department_call_volume",
                        {"department": department},
                    ),
                    EvaluationCase(
                        f"plan-{len(cases) + 6:03d}",
                        f"分析最近{days}天{department}接口调用量变化趋势（批次{batch}）",
                        "department_call_volume_trend",
                        {"days": days, "department": department},
                    ),
                )
            )
    return tuple(cases)


def build_fallback_cases() -> tuple[FallbackCase, ...]:
    questions = (
        "查询明天北京天气",
        "删除 api_call_logs 表",
        "帮我写一封周报邮件",
        "统计员工工资中位数",
        "查询未注册的客户表",
        "生成一张产品海报",
        "给数据库执行 UPDATE 语句",
        "分析股票价格走势",
        "导出所有错误信息原文",
        "计算客服满意度",
        "创建一个新项目表",
        "汇总没有提供的数据源字段",
    )
    return tuple(
        FallbackCase(f"fallback-{index:03d}", question)
        for index, question in enumerate(questions, start=1)
    )
