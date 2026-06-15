from typing import Literal

from pydantic import BaseModel, Field


class AgentQueryResponse(BaseModel):
    trace_id: str = Field(description="本次 Agent 执行的追踪 ID。")
    question: str = Field(description="用户提交的原始问题。")
    status: Literal["success", "failed"] = Field(description="本次执行状态。")
    report: str | None = Field(description="生成的结构化分析报告。")
    chart_path: str | None = Field(description="生成的图表文件路径。")
    error: str | None = Field(description="执行失败时的友好错误信息。")


class AgentTaskResponse(AgentQueryResponse):
    data_source: str | None = Field(default=None, description="实际使用的数据源。")
    intent: str | None = Field(default=None, description="识别出的分析意图。")
    query_plan: str | None = Field(default=None, description="Agent 查询计划。")
    sql: str | None = Field(default=None, description="数据库分支实际执行的 SQL。")
    updated_at: str | None = Field(default=None, description="任务最近更新时间。")
