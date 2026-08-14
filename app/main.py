from __future__ import annotations

from uuid import uuid4
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse

from app.schemas.request import AgentQueryRequest
from app.schemas.response import AgentQueryResponse, AgentTaskResponse
from app.services.agent_service import run_agent
from app.services.log_service import log_event
from app.services.task_service import get_task, save_task


app = FastAPI(
    title="企业数据问答与报告生成 Agent",
    description="面向企业接口调用日志的数据分析 Agent 服务。",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)


def build_artifact_urls(
    trace_id: str,
    *,
    has_report: bool,
    has_chart: bool,
) -> dict[str, str | None]:
    return {
        "task_url": f"/agent/task/{trace_id}",
        "report_url": f"/agent/report/{trace_id}" if has_report else None,
        "chart_url": f"/agent/chart/{trace_id}" if has_chart else None,
    }


@app.get("/health", include_in_schema=False)
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
def local_docs() -> str:
    return """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>企业数据分析 Agent</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0; background: #f4f6f8; color: #17202a;
      font: 15px/1.6 "Microsoft YaHei", Arial, sans-serif;
    }
    header { background: #17324d; color: white; padding: 20px 28px; }
    header h1 { margin: 0; font-size: 22px; }
    main { width: min(960px, calc(100% - 32px)); margin: 24px auto; }
    section {
      background: white; border: 1px solid #dce2e8; border-radius: 8px;
      padding: 20px; margin-bottom: 16px;
    }
    h2 { margin: 0 0 14px; font-size: 17px; }
    textarea {
      width: 100%; min-height: 92px; resize: vertical; padding: 12px;
      border: 1px solid #aeb8c2; border-radius: 6px; font: inherit;
    }
    button {
      margin-top: 12px; padding: 9px 18px; border: 0; border-radius: 6px;
      background: #1677ff; color: white; font: inherit; cursor: pointer;
    }
    button:disabled { opacity: .6; cursor: wait; }
    .meta { display: grid; grid-template-columns: 110px 1fr; gap: 6px 12px; }
    pre {
      margin: 14px 0 0; padding: 14px; overflow: auto;
      white-space: pre-wrap; background: #f7f8fa; border-radius: 6px;
    }
    .ok { color: #087443; } .failed { color: #b42318; }
    a { color: #0969da; }
  </style>
</head>
<body>
  <header><h1>企业数据问答与报告生成 Agent</h1></header>
  <main>
    <section>
      <h2>POST /agent/query</h2>
      <textarea id="question">统计各部门接口调用失败率，并生成分析报告</textarea>
      <button id="submit" type="button">提交分析</button>
    </section>
    <section>
      <h2>执行结果</h2>
      <div id="status">等待提交</div>
      <div id="result"></div>
    </section>
    <section>
      OpenAPI 定义：<a href="/openapi.json" target="_blank">/openapi.json</a>
    </section>
  </main>
  <script>
    const button = document.getElementById("submit");
    const status = document.getElementById("status");
    const result = document.getElementById("result");
    button.addEventListener("click", async () => {
      const question = document.getElementById("question").value.trim();
      if (!question) { status.textContent = "请输入问题。"; return; }
      button.disabled = true;
      status.textContent = "Agent 正在分析，请稍候...";
      result.innerHTML = "";
      try {
        const response = await fetch("/agent/query", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({question})
        });
        const data = await response.json();
        status.className = data.status === "success" ? "ok" : "failed";
        status.textContent = data.status === "success" ? "分析成功" : "分析失败";
        const meta = document.createElement("div");
        meta.className = "meta";
        const task = data.task_url
          ? await fetch(data.task_url).then(item => item.json())
          : {};
        const details = {
          trace_id: data.trace_id,
          data_source: task.data_source || "无",
          intent: task.intent || "无",
          query_plan: task.query_plan || null,
          sql: task.sql || null,
          retry_count: task.retry_count || 0,
          sql_validation_error: task.sql_validation_error || null,
          analysis_result: task.analysis_result || []
        };
        const entries = [
          ["追踪 ID", data.trace_id],
          ["任务详情", data.task_url || "无"],
          ["报告接口", data.report_url || "无"],
          ["图表接口", data.chart_url || "无"],
          ["错误信息", data.error || "无"]
        ];
        for (const [label, value] of entries) {
          const key = document.createElement("strong");
          const content = document.createElement("span");
          key.textContent = label;
          content.textContent = value;
          meta.append(key, content);
        }
        const report = document.createElement("pre");
        report.textContent = data.report || "没有生成报告。";
        const execution = document.createElement("pre");
        execution.textContent = JSON.stringify(details, null, 2);
        result.append(meta, report, execution);
        if (data.chart_url) {
          const chart = document.createElement("img");
          chart.src = data.chart_url;
          chart.alt = "分析图表";
          chart.style.cssText = "max-width: 100%; margin-top: 14px; border: 1px solid #dce2e8;";
          result.append(chart);
        }
      } catch (error) {
        status.className = "failed";
        status.textContent = "请求失败：" + error.message;
      } finally {
        button.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


@app.post(
    "/agent/query",
    response_model=AgentQueryResponse,
    summary="提交自然语言数据分析问题",
)
def query_agent(request: AgentQueryRequest) -> AgentQueryResponse:
    trace_id = uuid4().hex[:12]
    save_task(
        {
            "trace_id": trace_id,
            "question": request.question,
            "status": "running",
            "report": None,
            "error": None,
        }
    )
    try:
        result = run_agent(request.question, trace_id=trace_id)
        error = result.get("error")
        task = {
            "trace_id": result["trace_id"],
            "question": request.question,
            "status": "failed" if error else "success",
            "report": result.get("report") or None,
            # 仅持久化供 /agent/chart 读取；响应模型不会暴露本机绝对路径。
            "chart_path": result.get("chart_path") or None,
            "error": error,
            "data_source": result.get("data_source"),
            "intent": result.get("intent"),
            "query_plan": result.get("query_plan"),
            "sql": result.get("sql") or None,
            "sql_validation_error": result.get("sql_validation_error"),
            "retry_count": result.get("retry_count", 0),
            "analysis_result": result.get("analysis_result") or [],
            **build_artifact_urls(
                result["trace_id"],
                has_report=bool(result.get("report")),
                has_chart=bool(result.get("chart_path")),
            ),
        }
        save_task(task)
        return AgentQueryResponse(**task)
    except Exception:
        error = "Agent 执行失败，请稍后重试或检查服务日志。"
        log_event(
            trace_id=trace_id,
            node_name="fastapi_query",
            user_question=request.question,
            error=error,
        )
        task = {
            "trace_id": trace_id,
            "question": request.question,
            "status": "failed",
            "report": None,
            "error": error,
            **build_artifact_urls(
                trace_id,
                has_report=False,
                has_chart=False,
            ),
        }
        save_task(task)
        return AgentQueryResponse(**task)


@app.get(
    "/agent/task/{task_id}",
    response_model=AgentTaskResponse,
    summary="查询 Agent 任务状态和完整结果",
)
def get_agent_task(task_id: str) -> AgentTaskResponse:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在。")
    return AgentTaskResponse(**task)


@app.get(
    "/agent/report/{task_id}",
    response_class=PlainTextResponse,
    summary="获取任务分析报告",
)
def get_agent_report(task_id: str) -> str:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在。")
    if not task.get("report"):
        raise HTTPException(status_code=404, detail="该任务尚未生成报告。")
    return task["report"]


@app.get(
    "/agent/chart/{task_id}",
    response_class=FileResponse,
    summary="获取任务图表文件",
)
def get_agent_chart(task_id: str) -> FileResponse:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在。")
    chart_path = task.get("chart_path")
    if not chart_path or not Path(chart_path).is_file():
        raise HTTPException(status_code=404, detail="该任务尚未生成图表。")
    return FileResponse(chart_path, media_type="image/png", filename=Path(chart_path).name)
