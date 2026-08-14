from __future__ import annotations

import argparse
import base64
import json
import time
from itertools import count
from pathlib import Path
from urllib.request import urlopen

from PIL import Image
import websocket


QUESTION = "统计各部门接口调用失败率，并生成分析报告"
REQUEST_IDS = count(1)


def _json_request(url: str) -> dict:
    with urlopen(url, timeout=10) as response:  # noqa: S310 - local Chrome CDP only
        return json.loads(response.read().decode("utf-8"))


def _send(websocket_client: websocket.WebSocket, method: str, params: dict | None = None) -> dict:
    request_id = next(REQUEST_IDS)
    websocket_client.send(
        json.dumps({"id": request_id, "method": method, "params": params or {}})
    )
    while True:
        message = json.loads(websocket_client.recv())
        if message.get("id") == request_id:
            return message


def _capture(websocket_client: websocket.WebSocket, path: Path) -> None:
    result = _send(
        websocket_client,
        "Page.captureScreenshot",
        {"format": "png"},
    )
    path.write_bytes(base64.b64decode(result["result"]["data"]))


def main() -> int:
    parser = argparse.ArgumentParser(description="录制本地 Web Demo 的真实接口流程 GIF")
    parser.add_argument("--debug-port", type=int, default=9222)
    parser.add_argument("--app-url", default="http://127.0.0.1:8000/docs")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/images/agent_demo.gif"),
    )
    args = parser.parse_args()

    targets = _json_request(f"http://127.0.0.1:{args.debug_port}/json/list")
    page_target = next(target for target in targets if target["type"] == "page")
    client = websocket.create_connection(page_target["webSocketDebuggerUrl"], timeout=15)
    try:
        _send(client, "Page.enable")
        _send(
            client,
            "Emulation.setDeviceMetricsOverride",
            {"width": 1440, "height": 1300, "deviceScaleFactor": 1, "mobile": False},
        )
        _send(client, "Page.navigate", {"url": args.app_url})
        time.sleep(1.5)

        args.output.parent.mkdir(parents=True, exist_ok=True)
        before_path = args.output.with_name("agent_demo_before.png")
        after_path = args.output.with_name("agent_demo_after.png")
        _capture(client, before_path)

        script = (
            "document.getElementById('question').value = "
            + json.dumps(QUESTION, ensure_ascii=False)
            + "; document.getElementById('submit').click();"
        )
        _send(client, "Runtime.evaluate", {"expression": script})
        for _ in range(30):
            result = _send(
                client,
                "Runtime.evaluate",
                {
                    "expression": "document.getElementById('result').textContent.length > 50",
                    "returnByValue": True,
                },
            )
            if result["result"]["result"].get("value"):
                break
            time.sleep(0.5)
        _capture(client, after_path)

        before = Image.open(before_path).convert("RGB")
        after = Image.open(after_path).convert("RGB")
        before.save(
            args.output,
            save_all=True,
            append_images=[after],
            duration=[1400, 3600],
            loop=0,
            optimize=True,
        )
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
