from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from threading import Lock

from app.config import TASK_DIR


_lock = Lock()


def _task_path(task_id: str) -> Path:
    if not task_id.isalnum():
        raise ValueError("任务 ID 格式不正确。")
    return TASK_DIR / f"{task_id}.json"


def save_task(task: dict) -> None:
    TASK_DIR.mkdir(parents=True, exist_ok=True)
    task["updated_at"] = datetime.now().isoformat(timespec="seconds")
    path = _task_path(task["trace_id"])
    temp_path = path.with_suffix(".tmp")
    with _lock:
        temp_path.write_text(
            json.dumps(task, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(path)


def get_task(task_id: str) -> dict | None:
    try:
        path = _task_path(task_id)
    except ValueError:
        return None
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
