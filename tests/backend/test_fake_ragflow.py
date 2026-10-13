# 为什么有这个文件：核对 CI 假 RAGFlow 记下的请求头和几种响应，而不连接真实服务。
# 它解决什么问题：避免把本机夹具的通过写成已经接通公司知识库。

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

import pytest

from fake_ragflow import (
    BUSINESS_ERROR_BODY,
    EMPTY_BODY,
    HEALTH_BODY,
    HTTP_ERROR_STATUS,
    MODE_BUSINESS_ERROR,
    MODE_EMPTY,
    MODE_HTTP_ERROR,
    MODE_TIMEOUT,
    SUCCESS_BODY,
    SYNTHETIC_CONTENT,
    real_ragflow_skip_reason,
)

SYNTHETIC_KEY = "synthetic-ragflow-key"
REQUEST_BODY = {
    "question": "巡检要求",
    "dataset_ids": ["syntheticdataset0001"],
    "rerank_id": "synthetic-rerank",
}


def _request(url: str, *, method: str = "GET", payload: dict | None = None, timeout: float = 5):
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
        headers["Authorization"] = "Bearer " + SYNTHETIC_KEY
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return response.status, json.loads(raw.decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        parsed = json.loads(raw.decode()) if raw else None
        return exc.code, parsed


def test_success_records_bearer_and_effective_base_url(fake_ragflow):
    status, payload = _request(
        fake_ragflow.base_url + "/api/v1/retrieval",
        method="POST",
        payload=REQUEST_BODY,
    )
    assert status == 200
    assert payload == SUCCESS_BODY
    assert payload["data"]["chunks"][0]["content"] == SYNTHETIC_CONTENT
    assert len(fake_ragflow.calls) == 1
    call = fake_ragflow.calls[0]
    assert call.method == "POST"
    assert call.path == "/api/v1/retrieval"
    assert call.base_url == fake_ragflow.base_url
    assert call.header("authorization") == "Bearer " + SYNTHETIC_KEY
    assert call.header("content-type").startswith("application/json")
    assert json.loads(call.body.decode())["dataset_ids"] == ["syntheticdataset0001"]
    assert json.loads(call.body.decode())["rerank_id"] == "synthetic-rerank"


def test_gateway_prefix_stays_on_recorded_base_url(fake_ragflow):
    prefixed = fake_ragflow.base_url + "/gateway"
    status, payload = _request(
        prefixed + "/api/v1/retrieval",
        method="POST",
        payload=REQUEST_BODY,
    )
    assert status == 200 and payload["code"] == 0
    call = fake_ragflow.calls[0]
    assert call.base_url == prefixed
    assert call.path == "/gateway/api/v1/retrieval"


def test_empty_chunks_mode_is_code_zero_with_no_chunks(fake_ragflow):
    # 夹具只返回官方空信封。零命中在适配器里记为跳过，不在这里当成成功候选。
    fake_ragflow.mode = MODE_EMPTY
    status, payload = _request(
        fake_ragflow.base_url + "/api/v1/retrieval",
        method="POST",
        payload=REQUEST_BODY,
    )
    assert status == 200
    assert payload == EMPTY_BODY
    assert payload["code"] == 0
    assert payload["data"]["chunks"] == []
    assert payload["data"]["total"] == 0


def test_business_error_uses_nonzero_code(fake_ragflow):
    fake_ragflow.mode = MODE_BUSINESS_ERROR
    status, payload = _request(
        fake_ragflow.base_url + "/api/v1/retrieval",
        method="POST",
        payload=REQUEST_BODY,
    )
    assert status == 200
    assert payload == BUSINESS_ERROR_BODY
    assert payload["code"] != 0


def test_http_error_mode_returns_500(fake_ragflow):
    fake_ragflow.mode = MODE_HTTP_ERROR
    status, payload = _request(
        fake_ragflow.base_url + "/api/v1/retrieval",
        method="POST",
        payload=REQUEST_BODY,
    )
    assert status == HTTP_ERROR_STATUS
    assert payload == {"message": "synthetic http error"}
    assert fake_ragflow.calls[0].header("authorization") == "Bearer " + SYNTHETIC_KEY


def test_healthz_returns_documented_ok_body(fake_ragflow):
    status, payload = _request(fake_ragflow.base_url + "/api/v1/system/healthz")
    assert status == 200
    assert payload == HEALTH_BODY
    call = fake_ragflow.calls[0]
    assert call.method == "GET"
    assert call.path == "/api/v1/system/healthz"
    assert call.base_url == fake_ragflow.base_url


def test_unknown_path_is_404(fake_ragflow):
    status, payload = _request(fake_ragflow.base_url + "/v1/system/healthz")
    assert status == 404
    assert payload == {"message": "not found"}


def test_timeout_mode_holds_until_released(fake_ragflow):
    fake_ragflow.mode = MODE_TIMEOUT
    fake_ragflow.hold_responses()
    outcome: dict[str, object] = {}

    def call() -> None:
        try:
            _request(
                fake_ragflow.base_url + "/api/v1/retrieval",
                method="POST",
                payload=REQUEST_BODY,
                timeout=0.4,
            )
            outcome["finished"] = True
        except (urllib.error.URLError, TimeoutError) as exc:
            outcome["error"] = exc

    worker = threading.Thread(target=call)
    worker.start()
    worker.join(2)
    assert not worker.is_alive()
    assert "finished" not in outcome
    assert isinstance(outcome.get("error"), (urllib.error.URLError, TimeoutError))
    assert len(fake_ragflow.calls) == 1
    assert fake_ragflow.calls[0].header("authorization") == "Bearer " + SYNTHETIC_KEY
    fake_ragflow.release_responses()
    fake_ragflow.mode = "chunks"
    status, payload = _request(
        fake_ragflow.base_url + "/api/v1/retrieval",
        method="POST",
        payload=REQUEST_BODY,
    )
    assert status == 200 and payload["code"] == 0


def test_real_ragflow_skip_reason_requires_exact_one(monkeypatch):
    monkeypatch.delenv("ICG_RUN_REAL_RAGFLOW_TESTS", raising=False)
    assert real_ragflow_skip_reason() == "real RAGFlow endpoint tests require ICG_RUN_REAL_RAGFLOW_TESTS=1"
    monkeypatch.setenv("ICG_RUN_REAL_RAGFLOW_TESTS", "true")
    assert real_ragflow_skip_reason() is not None
    monkeypatch.setenv("ICG_RUN_REAL_RAGFLOW_TESTS", "1")
    assert real_ragflow_skip_reason() is None


@pytest.mark.live_ragflow
def test_real_ragflow_health_when_opted_in():
    import os

    base = os.environ.get("ICG_RAGFLOW_BASE_URL", "").strip().rstrip("/")
    assert base.startswith("http://") or base.startswith("https://")
    status, payload = _request(base + "/api/v1/system/healthz", timeout=10)
    assert status == 200
    assert payload.get("status") == "ok"
