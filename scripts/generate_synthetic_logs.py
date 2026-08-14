"""生成可复现、脱敏的企业接口调用日志样例。"""

from __future__ import annotations

import csv
import math
import random
from datetime import datetime, timedelta
from pathlib import Path


RANDOM_SEED = 20260814
START_DATE = datetime(2026, 2, 1)
DAY_COUNT = 180
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_api_logs.csv"

SYSTEMS = (
    ("销售部", "客户关系系统", ("/api/customer/search", "/api/order/create", "/api/order/list"), 0.035, 220),
    ("财务部", "财务系统", ("/api/invoice/create", "/api/payment/reconcile", "/api/budget/query"), 0.025, 320),
    ("运维部", "运维中心", ("/api/device/heartbeat", "/api/device/event", "/api/alert/create"), 0.03, 150),
    ("风控部", "风控系统", ("/api/risk/score", "/api/risk/rule/check", "/api/risk/report"), 0.05, 430),
    ("平台部", "网关平台", ("/api/auth/token", "/api/gateway/route", "/api/health"), 0.018, 100),
)


def _incident_adjustment(api_name: str, day_index: int) -> tuple[float, int]:
    """植入可观察的故障和延迟事件，便于趋势、TopN 和异常分析演示。"""
    if api_name == "/api/risk/score" and 108 <= day_index <= 116:
        return 0.32, 780
    if api_name == "/api/gateway/route" and 145 <= day_index <= 152:
        return 0.18, 420
    if api_name == "/api/payment/reconcile" and 58 <= day_index <= 65:
        return 0.13, 360
    if api_name == "/api/order/create" and 92 <= day_index <= 96:
        return 0.09, 220
    return 0.0, 0


def _error_message(status_code: int) -> str:
    return {
        500: "服务内部异常",
        502: "上游服务不可用",
        503: "服务繁忙",
        504: "请求超时",
    }.get(status_code, "请求失败")


def build_rows() -> list[dict[str, object]]:
    rng = random.Random(RANDOM_SEED)
    rows: list[dict[str, object]] = []
    row_id = 1
    for day_index in range(DAY_COUNT):
        day = START_DATE + timedelta(days=day_index)
        weekday_adjustment = 0.015 if day.weekday() >= 5 else 0.0
        for department, project_name, api_names, base_failure_rate, base_latency in SYSTEMS:
            for api_offset, api_name in enumerate(api_names):
                call_count = 9 + ((day_index * 7 + api_offset * 5 + len(department)) % 10)
                incident_failure, incident_latency = _incident_adjustment(api_name, day_index)
                failure_rate = base_failure_rate + weekday_adjustment + incident_failure
                daily_latency = int(35 * math.sin(day_index / 8 + api_offset))
                for _ in range(call_count):
                    failed = rng.random() < failure_rate
                    status_code = rng.choice((500, 502, 503, 504)) if failed else 200
                    latency_ms = max(
                        20,
                        int(rng.gauss(base_latency + daily_latency + incident_latency, max(20, base_latency * 0.16))),
                    )
                    request_time = day + timedelta(
                        seconds=rng.randrange(0, 24 * 60 * 60)
                    )
                    rows.append(
                        {
                            "id": row_id,
                            "department": department,
                            "project_name": project_name,
                            "api_name": api_name,
                            "status": "failed" if failed else "success",
                            "status_code": status_code,
                            "latency_ms": latency_ms,
                            "request_time": request_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "error_message": _error_message(status_code) if failed else "",
                        }
                    )
                    row_id += 1
    return rows


def main() -> int:
    rows = build_rows()
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"已生成 {len(rows)} 条固定随机种子合成日志：{OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
