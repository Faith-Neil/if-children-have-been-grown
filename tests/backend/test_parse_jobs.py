# 为什么有这个文件：验证招标解析后台任务与任务事件流（APP-M2-T020 / PRD v1.8 §5.12.4、§5.2.1）。
# 它解决什么问题：启动即返回 202 与任务；后台按原解析流程执行并写进度事件；RAGFlow 仍在识别时反复取回直到完成或等满上限；
# 事件流在任务进行中保持连接并推送新事件；取消、重试、权限与重复启动行为如实。

import threading
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


def test_outer_parse_stays_listed_after_inner_sync_job_is_dropped(client):
    """工作区能看到运行中的解析时，任务列表也要能看到；丢掉同步记录不能带走外层任务。"""
    flow = _uploaded(client)
    runner = client.app.state.parse_job_runner
    gate = threading.Event()
    entered = threading.Event()
    original = runner._parse_once

    def blocked(principal, project_id, payload):
        entered.set()
        assert gate.wait(timeout=20), "parse was not released"
        return original(principal, project_id, payload)

    runner._parse_once = blocked
    try:
        started = _start(flow)
        assert started.status_code == 202, started.text
        job_id = started.json()["id"]
        assert entered.wait(timeout=10), "parse did not reach the background call"

        def parse_ids(jobs):
            return {job["id"] for job in jobs if job["id"] == job_id}

        assert job_id in parse_ids(flow.state()["jobs"])
        listed = client.get("/api/v1/jobs", headers=flow.headers)
        assert listed.status_code == 200, listed.text
        assert job_id in parse_ids(listed.json()["jobs"])

        runner.repository.transaction(lambda state: state.jobs.pop(job_id, None))
        assert job_id in parse_ids(flow.state()["jobs"])
        listed = client.get("/api/v1/jobs", headers=flow.headers)
        assert listed.status_code == 200, listed.text
        row = next(job for job in listed.json()["jobs"] if job["id"] == job_id)
        assert row["status"] == "running" and row["recoverable"] is False and row["type"] == "parse"

        admin = client.get("/api/v1/jobs", headers=login(client, "platform-admin"))
        assert admin.status_code == 200, admin.text
        assert job_id in {job["id"] for job in admin.json()["jobs"]}

        inner_id = "job-inner-sync-only"
        def plant(state):
            state.jobs[inner_id] = {
                "id": inner_id, "project_id": flow.id, "type": "parse", "status": "completed",
                "progress": 100, "message": "同步解析记录", "created_at": "2026-11-12T00:00:00+00:00",
                "completed_at": "2026-11-12T00:00:00+00:00", "error": None, "recoverable": False,
            }

        runner.repository.transaction(plant)
        runner._drop_inner_job({"job": {"id": inner_id}})
        runner._drop_inner_job({"job": {"id": job_id}})
        listed_ids = {job["id"] for job in client.get("/api/v1/jobs", headers=flow.headers).json()["jobs"]}
        assert inner_id not in listed_ids
        assert job_id in listed_ids
    finally:
        gate.set()


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


def test_orphan_running_parse_job_is_failed_so_restart_can_reparse(client, monkeypatch):
    """进程崩溃后遗留的 running 任务：再次 start 应收口并开新任务，而不是永远返回僵尸。"""
    flow = _uploaded(client)
    runner = client.app.state.parse_job_runner
    monkeypatch.setattr(runner, "_pending_files", lambda project_id, payload: ["file-remote"])
    first = _start(flow).json()
    _wait(flow, first["id"], statuses=("running",))
    with runner._lock:
        runner._running.discard(first["id"])  # 模拟进程/线程丢失
    again = _start(flow)
    assert again.status_code == 202, again.text
    body = again.json()
    assert body["id"] != first["id"]
    orphan = client.get(f"/api/v1/jobs/{first['id']}", headers=flow.headers).json()
    assert orphan["status"] == "failed"
    assert orphan["error"]["code"] == "PARSER_INTERRUPTED"
    client.post(f"/api/v1/jobs/{body['id']}/cancel", headers={**flow.headers, "Idempotency-Key": str(uuid4())})


def test_fail_orphans_on_wire_marks_stale_running_jobs(client):
    flow = _uploaded(client)
    runner = client.app.state.parse_job_runner
    now = "2026-11-12T00:00:00+08:00"
    stale_id = "job-stale-orphan"

    def plant(state):
        job = {"id": stale_id, "project_id": flow.id, "type": "parse", "status": "running", "progress": 5,
               "message": "后台任务处理中", "created_at": now, "completed_at": None, "error": None,
               "events": [], "recoverable": True, "live": True, "created_by": "alpha-manager",
               "file_ids": None, "service": "auto"}
        state.recoverable_jobs[stale_id] = job
        state.jobs[stale_id] = {
            key: job.get(key) for key in ("id", "project_id", "type", "status", "progress", "message",
                                          "created_at", "completed_at", "error")
        } | {"recoverable": False}

    runner.repository.transaction(plant)
    assert runner.fail_orphans() >= 1
    orphan = client.get(f"/api/v1/jobs/{stale_id}", headers=flow.headers).json()
    assert orphan["status"] == "failed" and orphan["error"]["code"] == "PARSER_INTERRUPTED"


def test_health_exposes_effective_model(client):
    health = client.get("/health").json()
    assert health["model"] in ("mock", "real")
    assert health["effective_model"] in ("mock", "real", "company_real")
    assert "effective_model" in health
