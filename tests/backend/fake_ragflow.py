# 为什么有这个文件：给 CI 一个只监听本机的 RAGFlow 检索端点。
# 它解决什么问题：测试能核对实际收到的 Authorization 和 base_url，同时默认不访问真实 RAGFlow。

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REAL_RAGFLOW_FLAG = "ICG_RUN_REAL_RAGFLOW_TESTS"
RETRIEVAL_SUFFIX = "/api/v1/retrieval"
HEALTH_SUFFIX = "/api/v1/system/healthz"

MODE_CHUNKS = "chunks"
MODE_EMPTY = "empty"
MODE_BUSINESS_ERROR = "business_error"
MODE_HTTP_ERROR = "http_error"
MODE_TIMEOUT = "timeout"

SYNTHETIC_CHUNK_ID = "syntheticchunk0001"
SYNTHETIC_DOCUMENT_ID = "syntheticdoc0001"
SYNTHETIC_DATASET_ID = "syntheticdataset0001"
SYNTHETIC_CONTENT = "合成检索片段，仍须人工核对。"

# 字段名来自公开发布的 POST /api/v1/retrieval 成功体。不另造产品字段。
SUCCESS_CHUNK = {
    "id": SYNTHETIC_CHUNK_ID,
    "content": SYNTHETIC_CONTENT,
    "document_id": SYNTHETIC_DOCUMENT_ID,
    "dataset_id": SYNTHETIC_DATASET_ID,
    "similarity": 0.9669436601210759,
}
SUCCESS_BODY = {
    "code": 0,
    "data": {
        "chunks": [SUCCESS_CHUNK],
        "doc_aggs": [{
            "count": 1,
            "doc_id": SYNTHETIC_DOCUMENT_ID,
            "doc_name": "synthetic.txt",
        }],
        "total": 1,
    },
}
EMPTY_BODY = {"code": 0, "data": {"chunks": [], "doc_aggs": [], "total": 0}}
# 官方失败示例：HTTP 仍成功，业务 code 非 0。
BUSINESS_ERROR_BODY = {"code": 102, "message": "`dataset_ids` is required."}
HEALTH_BODY = {
    "db": "ok",
    "redis": "ok",
    "doc_engine": "ok",
    "storage": "ok",
    "message_queue": "ok",
    "status": "ok",
}
HTTP_ERROR_STATUS = 500
HTTP_ERROR_BODY = {"message": "synthetic http error"}


def real_ragflow_skip_reason() -> str | None:
    if os.environ.get(REAL_RAGFLOW_FLAG, "").strip() != "1":
        return f"real RAGFlow endpoint tests require {REAL_RAGFLOW_FLAG}=1"
    return None


def _effective_base(path: str, host: str) -> str:
    for suffix in (RETRIEVAL_SUFFIX, HEALTH_SUFFIX):
        if path.endswith(suffix):
            prefix = path[: -len(suffix)]
            return f"http://{host}{prefix}".rstrip("/")
    return f"http://{host}".rstrip("/")


@dataclass(frozen=True)
class RecordedRagflowCall:
    headers: dict[str, str]
    base_url: str
    path: str
    method: str
    body: bytes

    def header(self, name: str) -> str:
        for key, value in self.headers.items():
            if key.lower() == name.lower():
                return value
        return ""


class FakeRagflow:
    """本机 POST {base_url}/api/v1/retrieval，以及 GET {base_url}/api/v1/system/healthz。

    mode 只作用于检索 POST：chunks、empty、business_error、http_error、timeout。
    空 chunks 仍是 code 0 的官方信封。产品侧零命中记为跳过，由后续客户端处理，不在这里。
    """

    def __init__(self) -> None:
        self.calls: list[RecordedRagflowCall] = []
        self.mode = MODE_CHUNKS
        self._lock = threading.Lock()
        self._hold = threading.Event()
        self._hold.set()
        self._stopped = threading.Event()
        handler = self._handler_type()
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, name="fake-ragflow", daemon=True)
        self._thread.start()

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def hold_responses(self) -> None:
        """timeout 模式下，检索 POST 在记下请求后停住，直到 release_responses。"""
        self._hold.clear()

    def release_responses(self) -> None:
        self._hold.set()

    def close(self) -> None:
        self._stopped.set()
        self._hold.set()
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    def _wait_until_released(self) -> None:
        while not self._hold.is_set():
            if self._stopped.is_set():
                return
            self._hold.wait(0.05)

    def _handler_type(self):
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, format: str, *args) -> None:
                return

            def do_GET(self) -> None:
                self._dispatch(b"", "GET")

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0") or "0")
                raw = self.rfile.read(length)
                self._dispatch(raw, "POST")

            def _dispatch(self, raw: bytes, method: str) -> None:
                path = self.path.split("?", 1)[0]
                host = self.headers.get("Host", "")
                recorded = {key: value for key, value in self.headers.items()}
                with owner._lock:
                    owner.calls.append(RecordedRagflowCall(
                        headers=recorded,
                        base_url=_effective_base(path, host),
                        path=path,
                        method=method,
                        body=raw,
                    ))
                if method == "GET" and path.endswith(HEALTH_SUFFIX):
                    self._send(200, json.dumps(HEALTH_BODY).encode())
                    return
                if method == "POST" and path.endswith(RETRIEVAL_SUFFIX):
                    self._retrieval()
                    return
                self._send(404, b'{"message":"not found"}')

            def _retrieval(self) -> None:
                mode = owner.mode
                if mode == MODE_TIMEOUT:
                    owner._wait_until_released()
                    if owner._stopped.is_set():
                        return
                    mode = owner.mode if owner.mode != MODE_TIMEOUT else MODE_CHUNKS
                if mode == MODE_HTTP_ERROR:
                    self._send(HTTP_ERROR_STATUS, json.dumps(HTTP_ERROR_BODY).encode())
                    return
                if mode == MODE_BUSINESS_ERROR:
                    self._send(200, json.dumps(BUSINESS_ERROR_BODY).encode())
                    return
                if mode == MODE_EMPTY:
                    self._send(200, json.dumps(EMPTY_BODY).encode())
                    return
                if mode == MODE_CHUNKS:
                    self._send(200, json.dumps(SUCCESS_BODY).encode())
                    return
                self._send(500, b'{"message":"unknown fixture mode"}')

            def _send(self, status: int, body: bytes) -> None:
                try:
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError):
                    return

        return Handler
