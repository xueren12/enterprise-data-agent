from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from app.config import BASE_DIR


LOG_DIR = BASE_DIR / "logs"
TRACE_LOG_PATH = LOG_DIR / "agent_trace.jsonl"


def now_ms() -> int:
    return int(time.time() * 1000)


def summarize_value(value: Any) -> Any:
    if isinstance(value, list):
        return {"type": "list", "length": len(value)}
    if isinstance(value, dict):
        return {"type": "dict", "keys": sorted(value.keys())[:20]}
    if isinstance(value, Path):
        return str(value)
    return value


def log_event(
    *,
    trace_id: str,
    node_name: str = "",
    user_question: str = "",
    intent: str = "",
    tool_name: str = "",
    tool_args: dict | None = None,
    tool_result_summary: Any = None,
    error: str | None = None,
    latency_ms: int | None = None,
    final_report: str = "",
) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    event = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "trace_id": trace_id,
        "node_name": node_name,
        "user_question": user_question,
        "intent": intent,
        "tool_name": tool_name,
        "tool_args": {k: summarize_value(v) for k, v in (tool_args or {}).items()},
        "tool_result_summary": summarize_value(tool_result_summary),
        "error": error,
        "latency_ms": latency_ms,
        "final_report": final_report[:500] if final_report else "",
    }
    with TRACE_LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")
