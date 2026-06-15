from __future__ import annotations

import pandas as pd
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.config import CHART_DIR, REPORT_DIR
from app.services.log_service import log_event, now_ms
from app.services.llm_service import generate_report_with_llm, summarize_llm_usage
from app.tools.chart_tool import generate_analysis_chart
from app.tools.csv_tool import read_api_logs
from app.tools.pandas_tool import SUPPORTED_ANALYSIS_TYPES, analyze_api_logs
from app.tools.report_tool import generate_analysis_report, save_report
from app.tools.sql_tool import sql_query_tool


class CsvReadInput(BaseModel):
    csv_path: str = Field(description="需要读取的 CSV 或 Excel 文件路径。")
    trace_id: str = Field(description="本次 Agent 执行的追踪 ID。")


class PandasAnalysisInput(BaseModel):
    raw_data: list[dict] = Field(description="从数据源读取到的结构化数据行。")
    trace_id: str = Field(description="本次 Agent 执行的追踪 ID。")
    analysis_type: str = Field(
        default="department_failure_rate",
        description="分析类型，支持失败率、TopN、平均耗时、趋势和调用量分析。",
    )
    top_n: int | None = Field(default=None, description="可选的 TopN 返回数量限制。")
    days: int | None = Field(default=None, description="按数据最新时间回溯的天数。")
    department: str | None = Field(default=None, description="可选的部门筛选条件。")
    project_name: str | None = Field(default=None, description="可选的项目筛选条件。")
    api_name: str | None = Field(default=None, description="可选的接口筛选条件。")


class ChartGenerateInput(BaseModel):
    analysis_result: list[dict] = Field(description="各部门失败率分析结果。")
    trace_id: str = Field(description="本次 Agent 执行的追踪 ID。")
    analysis_type: str = Field(description="当前分析类型，用于选择图表配置。")


class ReportGenerateInput(BaseModel):
    question: str = Field(description="用户原始问题。")
    analysis_result: list[dict] = Field(description="各部门失败率分析结果。")
    chart_path: str = Field(description="已生成的图表路径。")
    trace_id: str = Field(description="本次 Agent 执行的追踪 ID。")
    analysis_type: str = Field(description="当前分析类型。")


def _csv_read_tool_impl(csv_path: str, trace_id: str) -> dict:
    started_at = now_ms()
    try:
        df = read_api_logs(csv_path)
        rows = df.to_dict(orient="records")
        result = {"success": True, "data": rows, "row_count": len(rows), "error": None}
        log_event(
            trace_id=trace_id,
            tool_name="csv_read_tool",
            tool_args={"csv_path": csv_path},
            tool_result_summary={"row_count": len(rows), "columns": list(df.columns)},
            latency_ms=now_ms() - started_at,
        )
        return result
    except Exception as exc:
        error = f"读取 CSV 失败：{exc}"
        log_event(
            trace_id=trace_id,
            tool_name="csv_read_tool",
            tool_args={"csv_path": csv_path},
            error=error,
            latency_ms=now_ms() - started_at,
        )
        return {"success": False, "data": [], "row_count": 0, "error": error}


def _pandas_analysis_tool_impl(
    raw_data: list[dict],
    trace_id: str,
    analysis_type: str = "department_failure_rate",
    top_n: int | None = None,
    days: int | None = None,
    department: str | None = None,
    project_name: str | None = None,
    api_name: str | None = None,
) -> dict:
    started_at = now_ms()
    try:
        if analysis_type not in SUPPORTED_ANALYSIS_TYPES:
            raise ValueError(f"不支持的分析类型：{analysis_type}")

        df = pd.DataFrame(raw_data)
        analysis_result = analyze_api_logs(
            df,
            analysis_type,
            top_n=top_n,
            days=days,
            department=department,
            project_name=project_name,
            api_name=api_name,
        )
        result = {
            "success": True,
            "analysis_type": analysis_type,
            "data": analysis_result,
            "row_count": len(analysis_result),
            "error": None,
        }
        log_event(
            trace_id=trace_id,
            tool_name="pandas_analysis_tool",
            tool_args={
                "analysis_type": analysis_type,
                "top_n": top_n,
                "days": days,
                "department": department,
                "project_name": project_name,
                "api_name": api_name,
                "raw_data": raw_data,
            },
            tool_result_summary={"row_count": len(analysis_result)},
            latency_ms=now_ms() - started_at,
        )
        return result
    except Exception as exc:
        error = f"Pandas 分析失败：{exc}"
        log_event(
            trace_id=trace_id,
            tool_name="pandas_analysis_tool",
            tool_args={
                "analysis_type": analysis_type,
                "top_n": top_n,
                "days": days,
                "department": department,
                "project_name": project_name,
                "api_name": api_name,
                "raw_data": raw_data,
            },
            error=error,
            latency_ms=now_ms() - started_at,
        )
        return {"success": False, "analysis_type": analysis_type, "data": [], "row_count": 0, "error": error}


def _chart_generate_tool_impl(
    analysis_result: list[dict],
    trace_id: str,
    analysis_type: str,
) -> dict:
    started_at = now_ms()
    try:
        chart_path = generate_analysis_chart(
            analysis_result=analysis_result,
            output_dir=CHART_DIR,
            trace_id=trace_id,
            analysis_type=analysis_type,
        )
        log_event(
            trace_id=trace_id,
            tool_name="chart_generate_tool",
            tool_args={"analysis_type": analysis_type, "analysis_result": analysis_result},
            tool_result_summary={"chart_path": chart_path},
            latency_ms=now_ms() - started_at,
        )
        return {"success": True, "chart_path": chart_path, "error": None}
    except Exception as exc:
        error = f"图表生成失败：{exc}"
        log_event(
            trace_id=trace_id,
            tool_name="chart_generate_tool",
            tool_args={"analysis_type": analysis_type, "analysis_result": analysis_result},
            error=error,
            latency_ms=now_ms() - started_at,
        )
        return {"success": False, "chart_path": "", "error": error}


def _report_generate_tool_impl(
    question: str,
    analysis_result: list[dict],
    chart_path: str,
    trace_id: str,
    analysis_type: str,
) -> dict:
    started_at = now_ms()
    try:
        report = generate_analysis_report(
            question=question,
            analysis_result=analysis_result,
            chart_path=chart_path,
            analysis_type=analysis_type,
        )
        llm_result = generate_report_with_llm(
            question=question,
            analysis_result=analysis_result,
            chart_path=chart_path,
            fallback_report=report,
        )
        final_report = llm_result["content"]
        report_path = save_report(final_report, REPORT_DIR, trace_id)
        log_event(
            trace_id=trace_id,
            tool_name="report_generate_tool",
            tool_args={
                "question": question,
                "analysis_result": analysis_result,
                "chart_path": chart_path,
                "analysis_type": analysis_type,
            },
            tool_result_summary={
                "report_path": report_path,
                "report_length": len(final_report),
                "llm_usage": summarize_llm_usage(llm_result),
            },
            latency_ms=now_ms() - started_at,
            final_report=final_report,
        )
        return {
            "success": True,
            "report": final_report,
            "report_path": report_path,
            "error": None,
            "used_llm": llm_result["used_llm"],
        }
    except Exception as exc:
        error = f"报告生成失败：{exc}"
        log_event(
            trace_id=trace_id,
            tool_name="report_generate_tool",
            tool_args={
                "question": question,
                "analysis_result": analysis_result,
                "chart_path": chart_path,
                "analysis_type": analysis_type,
            },
            error=error,
            latency_ms=now_ms() - started_at,
        )
        return {"success": False, "report": "", "report_path": "", "error": error}


csv_read_tool = StructuredTool.from_function(
    func=_csv_read_tool_impl,
    name="csv_read_tool",
    description="读取并校验企业接口调用日志 CSV 文件，适用于从本地示例数据源加载原始日志。",
    args_schema=CsvReadInput,
)

pandas_analysis_tool = StructuredTool.from_function(
    func=_pandas_analysis_tool_impl,
    name="pandas_analysis_tool",
    description="使用 Pandas 分析接口调用日志，支持失败率、TopN、平均耗时、趋势和调用量。",
    args_schema=PandasAnalysisInput,
)

chart_generate_tool = StructuredTool.from_function(
    func=_chart_generate_tool_impl,
    name="chart_generate_tool",
    description="根据结构化分析结果生成 Matplotlib 图表，并返回保存后的图表文件路径。",
    args_schema=ChartGenerateInput,
)

report_generate_tool = StructuredTool.from_function(
    func=_report_generate_tool_impl,
    name="report_generate_tool",
    description="根据用户问题、分析结果和图表路径生成并保存结构化业务分析报告。",
    args_schema=ReportGenerateInput,
)


LANGCHAIN_TOOLS = [
    sql_query_tool,
    csv_read_tool,
    pandas_analysis_tool,
    chart_generate_tool,
    report_generate_tool,
]
