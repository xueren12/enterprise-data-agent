from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_query_agent_success(monkeypatch):
    def fake_run_agent(question: str, trace_id: str | None = None) -> dict:
        return {
            "trace_id": trace_id or "trace-success",
            "user_question": question,
            "report": "测试分析报告",
            "chart_path": "charts/test.png",
            "error": None,
        }

    monkeypatch.setattr("app.main.run_agent", fake_run_agent)

    response = client.post(
        "/agent/query",
        json={"question": "统计各部门接口调用失败率"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "trace_id": body["trace_id"],
        "question": "统计各部门接口调用失败率",
        "status": "success",
        "report": "测试分析报告",
        "chart_path": "charts/test.png",
        "error": None,
    }


def test_query_agent_failed(monkeypatch):
    def fake_run_agent(question: str, trace_id: str | None = None) -> dict:
        return {
            "trace_id": trace_id or "trace-failed",
            "user_question": question,
            "report": "当前问题暂不支持。",
            "chart_path": "",
            "error": "暂时只支持接口调用失败率分析。",
        }

    monkeypatch.setattr("app.main.run_agent", fake_run_agent)

    response = client.post(
        "/agent/query",
        json={"question": "查询天气"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["chart_path"] is None
    assert body["error"] == "暂时只支持接口调用失败率分析。"


def test_query_agent_rejects_blank_question():
    response = client.post("/agent/query", json={"question": "   "})

    assert response.status_code == 422


def test_get_task_and_report(monkeypatch):
    task = {
        "trace_id": "task123",
        "question": "统计失败率",
        "status": "success",
        "report": "报告内容",
        "chart_path": None,
        "error": None,
        "intent": "department_failure_rate",
    }
    monkeypatch.setattr("app.main.get_task", lambda task_id: task)

    task_response = client.get("/agent/task/task123")
    report_response = client.get("/agent/report/task123")

    assert task_response.status_code == 200
    assert task_response.json()["intent"] == "department_failure_rate"
    assert report_response.status_code == 200
    assert report_response.text == "报告内容"


def test_get_unknown_task_returns_404(monkeypatch):
    monkeypatch.setattr("app.main.get_task", lambda task_id: None)

    response = client.get("/agent/task/missing")

    assert response.status_code == 404
