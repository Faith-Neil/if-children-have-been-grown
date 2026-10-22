# 为什么有这个文件：给 CI 一个只监听本机的 OpenAI 兼容对话端点。
# 它解决什么问题：测试能核对实际收到的请求头和 base_url，同时默认不访问真实模型。

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REAL_MODEL_FLAG = "ICG_RUN_REAL_MODEL_TESTS"
CHAT_SUFFIX = "/v1/chat/completions"
ASSISTANT_TEXT = "合成模型候选，仍须人工核对。"


def real_model_skip_reason() -> str | None:
    if os.environ.get(REAL_MODEL_FLAG, "").strip() != "1":
        return f"real model endpoint tests require {REAL_MODEL_FLAG}=1"
    return None


@dataclass(frozen=True)
class RecordedChatCall:
    headers: dict[str, str]
    base_url: str
    path: str
    body: bytes = b""

    def header(self, name: str) -> str:
        for key, value in self.headers.items():
            if key.lower() == name.lower():
                return value
        return ""

    @property
    def json(self) -> dict:
        if not self.body:
            return {}
        return json.loads(self.body.decode("utf-8"))


class FakeOpenAIChat:
    """本机 POST {base_url}/v1/chat/completions。记下请求头，并从路径还原调用方使用的 base_url。"""

    def __init__(self) -> None:
        self.calls: list[RecordedChatCall] = []
        self._lock = threading.Lock()
        self.status_code: int = 200
        self.response_body: bytes | None = None
        self.assistant_text: str = ASSISTANT_TEXT
        handler = self._handler_type()
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, name="fake-openai-chat", daemon=True)
        self._thread.start()

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    def _handler_type(self):
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, format: str, *args) -> None:
                return

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0") or "0")
                raw_body = self.rfile.read(length)
                path = self.path.split("?", 1)[0]
                host = self.headers.get("Host", "")
                if path.endswith(CHAT_SUFFIX):
                    prefix = path[: -len(CHAT_SUFFIX)]
                    effective = f"http://{host}{prefix}".rstrip("/")
                else:
                    effective = f"http://{host}".rstrip("/")
                recorded = {key: value for key, value in self.headers.items()}
                with owner._lock:
                    owner.calls.append(RecordedChatCall(headers=recorded, base_url=effective, path=path, body=raw_body))
                if not path.endswith(CHAT_SUFFIX):
                    body = b'{"error":"not found"}'
                    self._send(404, body)
                    return
                if owner.status_code != 200:
                    self._send(owner.status_code, owner.response_body or b'{"error":"upstream model error"}')
                    return
                if owner.response_body is not None:
                    self._send(200, owner.response_body)
                    return
                assistant_content = getattr(owner, "assistant_text", ASSISTANT_TEXT)
                payload = {"choices": [{"message": {"role": "assistant", "content": assistant_content}}]}
                self._send(200, json.dumps(payload).encode())

            def _send(self, status: int, body: bytes) -> None:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body)

        return Handler
