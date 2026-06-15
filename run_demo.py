from __future__ import annotations
from app.services.agent_service import run_agent
from app.state import AgentState


def run_demo() -> AgentState:
    question = "统计各部门接口调用失败率，并生成分析报告"
    return run_agent(question)


if __name__ == "__main__":
    result = run_demo()
    print(f"追踪 ID：{result['trace_id']}")
    print(f"识别意图：{result['intent']}")
    print(f"数据源：{result['data_source']}")
    print(f"执行计划：{result['query_plan']}")
    print(f"图表路径：{result['chart_path']}")
    print(f"报告路径：{result.get('report_path', '')}")
    print(f"错误信息：{result['error']}")
    print()
    print(result["report"])
