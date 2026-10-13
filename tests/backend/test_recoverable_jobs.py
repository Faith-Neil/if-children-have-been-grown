# 为什么有这个文件：证明可恢复生成任务按冻结契约返回 202、状态和事件流。
# 它解决什么问题：避免把同步生成改成已恢复，或让失败和取消没有明确状态。

import json

import pytest
from fastapi.testclient import TestClient

from icg_demo.domain import Lease, iso_time
from icg_demo.generation_context import writing_source_fingerprint
from icg_demo.main import create_app
from test_demo import MutableClock, login

PROJECT = "alpha-project"
CHAPTER = "alpha-tech"
START = f"/api/v1/projects/{PROJECT}/generation/start"
KEY = "recover-job-01"


@pytest.fixture
def clock():
    return MutableClock()


@pytest.fixture
def client(clock):
    with TestClient(create_app(clock=clock)) as actual_client:
        yield actual_client


def _blank(project_id):
    return {"files": {}, "requirements": {}, "facts": {}, "conflicts": {},
            "candidates": {}, "checks": {}, "exports": {}, "parse_confirmed": True,
            "plan_confirmed": True, "chapter_order": [], "sla": None, "sla_commitments": {},
            "writing_plan": {}}


def confirm_chapter(client, chapter_id=CHAPTER, project_id=PROJECT, revision=1, stale=False):
    def operation(state):
        workflow = state.workflows.setdefault(project_id, _blank(project_id))
        workflow.update(parse_confirmed=True, plan_confirmed=True, outline_revision=revision)
        chapters = workflow.setdefault("writing_plan", {}).setdefault("chapters", {})
        chapters[chapter_id] = {
            "fact_ids": [], "writing_points": "合成要点", "target_length": 100,
            "confirmed_by": "alpha-manager", "confirmed_by_name": "甲公司项目经理（合成）",
            "confirmed_at": iso_time(1), "confirmation_pending": False,
        }
        fingerprint = "0" * 64 if stale else writing_source_fingerprint(state, project_id, chapter_id)
        chapters[chapter_id]["confirmed_input_fingerprint"] = fingerprint
    client.app.state.service.repository.transaction(operation)


def start(client, headers, key=KEY, match="1", body=None):
    return client.post(START, headers={**headers, "Idempotency-Key": key, "If-Match": match},
                       json={} if body is None else body)


def parse_sse(text):
    events = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        item, data = {}, []
        for line in block.splitlines():
            if line.startswith("id: "):
                item["id"] = line[4:]
            elif line.startswith("event: "):
                item["event"] = line[7:]
            elif line.startswith("data: "):
                data.append(line[6:])
        item["data"] = json.loads("".join(data))
        events.append(item)
    return events


def test_start_returns_202_and_sync_generate_stays_separate(client):
    headers = login(client, "alpha-manager")
    confirm_chapter(client)
    accepted = start(client, headers)
    assert accepted.status_code == 202, accepted.text
    body = accepted.json()
    assert body["status"] == "queued"
    assert body["recoverable"] is True
    assert body["completed_at"] is None
    assert body["error"] is None
    assert accepted.headers["Location"] == "/api/v1/jobs/" + body["id"]
    assert "Idempotent-Replayed" not in accepted.headers

    replay = start(client, headers)
    assert replay.status_code == 202, replay.text
    assert replay.json()["id"] == body["id"]
    assert replay.headers["Location"] == accepted.headers["Location"]
    assert replay.headers["Idempotent-Replayed"] == "true"

    conflict = start(client, headers, body={"chapter_ids": [CHAPTER]})
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"

    listed = client.get("/api/v1/jobs", headers=headers)
    assert listed.status_code == 200
    assert body["id"] not in {item["id"] for item in listed.json()["jobs"]}

    sync = client.post(f"/api/v1/projects/{PROJECT}/generate", headers=headers, json={})
    assert sync.status_code != 202


def test_get_advances_to_completed_and_sse_honors_last_event_id(client):
    headers = login(client, "alpha-manager")
    confirm_chapter(client)
    job_id = start(client, headers, key="recover-job-02").json()["id"]
    current = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert current.status_code == 200, current.text
    body = current.json()
    assert body["status"] == "completed"
    assert body["recoverable"] is True
    assert body["progress"] == 100
    assert body["error"] is None
    types = [event["type"] for event in body["events"]]
    assert types == [
        "job.status_changed", "job.progress", "job.model_call", "job.progress", "job.completed"]
    call = body["events"][2]
    assert call["id"] == f"{job_id}:3"
    assert call["provider"] == "demo"
    assert call["model"] == "demo"
    assert call["is_real_model"] is False
    assert call["is_local"] is True
    assert call["duration_ms"] == 0
    assert call["error_code"] is None
    assert "payload" not in call
    changed = body["events"][0]["payload"]
    assert changed == {"from": "queued", "to": "running"}
    assert body["events"][-1]["payload"]["status"] == "completed"
    assert body["events"][-1]["payload"]["error"] is None

    resumed = client.get(f"/api/v1/jobs/{job_id}/events", headers={**headers, "Last-Event-ID": f"{job_id}:3"})
    assert resumed.status_code == 200
    assert resumed.headers["content-type"].startswith("text/event-stream")
    parsed = parse_sse(resumed.text)
    assert [item["id"] for item in parsed] == [f"{job_id}:4", f"{job_id}:5"]
    assert [item["event"] for item in parsed] == ["job.progress", "job.completed"]

    other = login(client, "beta-manager")
    hidden = client.get(f"/api/v1/jobs/{job_id}", headers=other)
    assert hidden.status_code == 404
    assert hidden.json()["code"] == "NOT_FOUND"


def test_cancel_and_failure_are_explicit(client):
    headers = login(client, "alpha-manager")
    confirm_chapter(client)
    queued = start(client, headers, key="recover-job-03").json()
    cancelled = client.post(f"/api/v1/jobs/{queued['id']}/cancel",
                            headers={**headers, "Idempotency-Key": "cancel-job-03"})
    assert cancelled.status_code == 200, cancelled.text
    body = cancelled.json()
    assert body["status"] == "cancelled"
    assert body["error"] is None
    assert body["events"][-1]["type"] == "job.cancelled"
    assert body["events"][-1]["payload"]["error"] is None
    assert "Location" not in cancelled.headers
    again = client.post(f"/api/v1/jobs/{queued['id']}/cancel",
                        headers={**headers, "Idempotency-Key": "cancel-job-03"})
    assert again.headers["Idempotent-Replayed"] == "true"
    assert again.json()["id"] == queued["id"]
    finished = client.post(f"/api/v1/jobs/{queued['id']}/cancel",
                           headers={**headers, "Idempotency-Key": "cancel-job-04"})
    assert finished.status_code == 409
    assert finished.json()["code"] == "VERSION_CONFLICT"

    viewer = login(client, "alpha-viewer")
    refused = client.post(f"/api/v1/jobs/{queued['id']}/cancel",
                          headers={**viewer, "Idempotency-Key": "cancel-job-05"})
    assert refused.status_code == 403
    assert refused.json()["code"] == "PROJECT_WRITER_REQUIRED"

    provider = client.app.state.service.model_provider
    provider.suggest = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("synthetic"))
    try:
        failed_id = start(client, headers, key="recover-job-06").json()["id"]
        failed = client.get(f"/api/v1/jobs/{failed_id}", headers=headers)
    finally:
        del provider.suggest
    assert failed.status_code == 200, failed.text
    assert failed.json()["status"] == "failed"
    assert failed.json()["error"]["code"] == "MODEL_UNAVAILABLE"
    call = next(event for event in failed.json()["events"] if event["type"] == "job.model_call")
    assert call["error_code"] == "MODEL_UNAVAILABLE"
    assert call["provider"] and call["model"]
    assert isinstance(call["is_real_model"], bool) and isinstance(call["is_local"], bool)
    assert isinstance(call["duration_ms"], int)
    terminal = failed.json()["events"][-1]
    assert terminal["type"] == "job.failed"
    assert terminal["payload"]["status"] == "failed"
    assert terminal["payload"]["error"] == "MODEL_UNAVAILABLE"


def test_start_rejects_bad_preconditions_without_a_new_error_code(client, clock):
    headers = login(client, "alpha-manager")
    missing_key = client.post(START, headers={**headers, "If-Match": "1"}, json={})
    assert missing_key.status_code == 428
    assert missing_key.json()["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    missing_match = client.post(START, headers={**headers, "Idempotency-Key": "recover-job-07"}, json={})
    assert missing_match.status_code == 428
    assert missing_match.json()["code"] == "IF_MATCH_REQUIRED"

    confirm_chapter(client)
    stale_match = start(client, headers, key="recover-job-08", match="9")
    assert stale_match.status_code == 409
    assert stale_match.json()["code"] == "VERSION_CONFLICT"

    editor = login(client, "alpha-editor")
    owned = start(client, editor, key="recover-job-09")
    assert owned.status_code == 403
    assert owned.json()["code"] == "VOLUME_OWNER_REQUIRED"

    def hold(state):
        state.chapters[CHAPTER].lock = Lease("held-token", "alpha-editor", "session", clock.value + 30)
    client.app.state.service.repository.transaction(hold)
    held = start(client, headers, key="recover-job-10")
    assert held.status_code == 423
    assert held.json()["code"] == "LOCK_HELD"
    assert "Idempotent-Replayed" not in held.headers

    def unlock(state):
        state.chapters[CHAPTER].lock = None
    client.app.state.service.repository.transaction(unlock)
    confirm_chapter(client, stale=True)
    stale = start(client, headers, key="recover-job-11", body={"chapter_ids": [CHAPTER]})
    assert stale.status_code == 409
    assert stale.json()["code"] == "PLAN_STALE"

    confirm_chapter(client)
    provider = client.app.state.service.model_provider
    provider.available = False
    try:
        unavailable = start(client, headers, key="recover-job-12", match="1")
    finally:
        del provider.available
    assert unavailable.status_code == 502
    assert unavailable.json()["code"] == "MODEL_UNAVAILABLE"
    provider.secret_key_available = False
    try:
        secret = start(client, headers, key="recover-job-13")
    finally:
        del provider.secret_key_available
    assert secret.status_code == 503
    assert secret.json()["code"] == "SECRET_KEY_UNAVAILABLE"
    assert "Idempotent-Replayed" not in secret.headers

    provider.is_local = False
    provider.is_real_model = True
    def sensitive(state):
        state.projects[PROJECT].sensitive = True
    client.app.state.service.repository.transaction(sensitive)
    confirm_chapter(client)
    try:
        cloud = start(client, headers, key="recover-job-14")
    finally:
        provider.is_local = True
        provider.is_real_model = False
        def clear(state):
            state.projects[PROJECT].sensitive = False
        client.app.state.service.repository.transaction(clear)
    assert cloud.status_code == 403
    assert cloud.json()["code"] == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"


def test_live_contract_uses_the_frozen_operation_ids():
    schema = create_app().openapi()
    paths = schema["paths"]
    assert paths["/api/v1/projects/{project_id}/generation/start"]["post"]["operationId"] == "startGeneration"
    assert paths["/api/v1/jobs/{job_id}"]["get"]["operationId"] == "getJob"
    assert paths["/api/v1/jobs/{job_id}/events"]["get"]["operationId"] == "streamJobEvents"
    assert paths["/api/v1/jobs/{job_id}/cancel"]["post"]["operationId"] == "cancelJob"
    job = schema["components"]["schemas"]["Job"]
    assert job["properties"]["recoverable"]["const"] is False
    status = schema["components"]["schemas"]["JobStatus"]
    assert "allOf" not in status
    assert status["properties"]["recoverable"]["type"] == "boolean"
    assert "const" not in status["properties"]["recoverable"]
    assert status["properties"]["status"]["enum"] == ["queued", "running", "completed", "failed", "cancelled"]
