# 为什么有这个文件：验证招标解析后台任务与任务事件流（APP-M2-T020 / PRD v1.8 §5.12.4、§5.2.1）。
# 它解决什么问题：启动即返回 202 与任务；后台按原解析流程执行并写进度事件；RAGFlow 仍在识别时反复取回直到完成或等满上限；
# 事件流在任务进行中保持连接并推送新事件；取消、重试、权限与重复启动行为如实。

import time
from uuid import uuid4

import pytest

from test_reference_flow import TENDER, ProjectFlow, client, login  # noqa: F401


@pytest.fixture(autouse=True)
def fast_polling(monkeypatch):
    monkeypatch.setenv("ICG_PARSE_JOB_POLL_SECONDS", "0.05")
    monkeypatch.setenv("ICG_SSE_HOLD_SECONDS", "5")


def _uploaded(client):
    flow = ProjectFlow(client)
    flow.write("", {"tender_number": "SYNTH-001", "deadline": "2026-12-31T17:00:00+08:00"}, "PATCH")
    flow.upload(TENDER.encode())
    return flow


def _start(flow, account="alpha-manager", expected=200):
    headers = {**login(flow.client, account), "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())}
    return flow.client.post(f"{flow.path}/parse/jobs", json={}, headers=headers)


def _wait(flow, job_id, statuses=("completed", "failed", "cancelled"), timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = flow.client.get(f"/api/v1/jobs/{job_id}", headers=flow.headers).json()
        if job["status"] in statuses:
            return job
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} did not reach {statuses}: {job}")


def test_parse_job_runs_in_background_and_reports_events(client):
    flow = _uploaded(client)
    started = _start(flow)
    assert started.status_code == 202, started.text
    body = started.json()
    assert started.headers["Location"] == f"/api/v1/jobs/{body['id']}"
    assert body["type"] == "parse" and body["status"] in ("queued", "running", "completed")

    job = _wait(flow, body["id"])
    assert job["status"] == "completed", job
    assert "条款" in job["message"] and job["progress"] == 100 and job["allowedActions"] == []
    kinds = [e["type"] for e in job["events"]]
    assert kinds[0] == "job.status_changed" and kinds[-1] == "job.completed"
    assert [e["seq"] for e in job["events"]] == list(range(1, len(kinds) + 1))
    assert flow.state()["requirements"], "解析结果已写入项目"

    listed = [j for j in client.get("/api/v1/jobs", headers=flow.headers).json()["jobs"] if j["project_id"] == flow.id]
    assert [j["type"] for j in listed].count("parse") == 1  # 后台任务代表这次解析，内部调用不重复列出
    assert next(j for j in listed if j["id"] == body["id"])["status"] == "completed"

    stream = client.get(f"/api/v1/jobs/{body['id']}/events", headers={**flow.headers, "Last-Event-ID": f"{body['id']}:1"})
    assert stream.status_code == 200 and stream.headers["content-type"].startswith("text/event-stream")
    assert f"id: {body['id']}:1\n" not in stream.text and f"id: {body['id']}:2\n" in stream.text
    assert "event: job.completed" in stream.text


def test_remote_parse_is_fetched_repeatedly_and_the_stream_stays_open(client, monkeypatch):
    flow = _uploaded(client)
    runner = client.app.state.parse_job_runner
    calls = {"n": 0}
    original = runner._pending_files

    def pending(project_id, payload):
        calls["n"] += 1
        return ["file-remote"] if calls["n"] <= 3 else original(project_id, payload)

    monkeypatch.setattr(runner, "_pending_files", pending)
    body = _start(flow).json()
    with client.stream("GET", f"/api/v1/jobs/{body['id']}/events", headers=flow.headers) as response:
        text = "".join(response.iter_text())
    assert "RAGFlow 正在识别 1 份文件" in text
    assert text.rstrip().endswith("}") and "event: job.completed" in text  # 连接保持到任务结束
    job = _wait(flow, body["id"])
    assert job["status"] == "completed" and calls["n"] >= 4
    progress = [e["payload"]["message"] for e in job["events"] if e["type"] == "job.progress"]
    assert sum("第" in m and "次取回" in m for m in progress) == 3


def test_waiting_too_long_fails_then_retry_continues(client, monkeypatch):
    monkeypatch.setenv("ICG_PARSE_JOB_MAX_WAIT_SECONDS", "1")
    flow = _uploaded(client)
    runner = client.app.state.parse_job_runner
    original = runner._pending_files
    monkeypatch.setattr(runner, "_pending_files", lambda project_id, payload: ["file-remote"])
    body = _start(flow).json()
    failed = _wait(flow, body["id"])
    assert failed["status"] == "failed" and failed["error"]["code"] == "PARSER_UNAVAILABLE"
    assert failed["allowedActions"] == ["retry"] and failed["events"][-1]["type"] == "job.failed"

    monkeypatch.setattr(runner, "_pending_files", original)
    retried = client.post(f"/api/v1/jobs/{body['id']}/retry", headers={**flow.headers, "Idempotency-Key": str(uuid4())})
    assert retried.status_code == 200, retried.text
    assert _wait(flow, body["id"])["status"] == "completed"


def test_cancel_stops_the_job_and_duplicate_start_returns_the_running_job(client, monkeypatch):
    flow = _uploaded(client)
    runner = client.app.state.parse_job_runner
    monkeypatch.setattr(runner, "_pending_files", lambda project_id, payload: ["file-remote"])
    first = _start(flow).json()
    _wait(flow, first["id"], statuses=("running",))
    again = _start(flow)
    assert again.status_code == 202 and again.json()["id"] == first["id"]
    cancelled = client.post(f"/api/v1/jobs/{first['id']}/cancel", headers={**flow.headers, "Idempotency-Key": str(uuid4())})
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    time.sleep(0.3)
    job = client.get(f"/api/v1/jobs/{first['id']}", headers=flow.headers).json()
    assert job["status"] == "cancelled" and job["events"][-1]["type"] == "job.cancelled"


def test_parse_job_permissions(client):
    flow = _uploaded(client)
    viewer = _start(flow, "alpha-viewer")
    assert viewer.status_code == 403
    beta = _start(flow, "beta-manager")
    assert beta.status_code == 404
    no_match = client.post(f"{flow.path}/parse/jobs", json={}, headers={**flow.headers, "Idempotency-Key": str(uuid4())})
    assert no_match.status_code == 428 and no_match.json()["code"] == "IF_MATCH_REQUIRED"
    job = _start(flow).json()
    assert client.get(f"/api/v1/jobs/{job['id']}", headers=login(client, "beta-manager")).status_code == 404
    _wait(flow, job["id"])
