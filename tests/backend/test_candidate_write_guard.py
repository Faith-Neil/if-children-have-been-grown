# 为什么有这个文件：独立验证候选、草稿和正式提交在来源变化时都受到同一写入保护。
# 它解决什么问题：防止浏览器核对以后来源被别人改动，章节版本未变化却仍把旧候选写进正式正文。

from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from icg_demo.adapters import MemoryRepository, seed_state
from icg_demo.main import create_app
from test_generation_context import CapturingProvider, prepare_context
from test_reference_flow import login


@pytest.fixture
def guarded_context():
    repository = MemoryRepository(seed_state())
    provider = CapturingProvider()
    with TestClient(create_app(repository=repository, model_provider=provider)) as client:
        setup = prepare_context(client, repository)
        flow, chapter = setup["flow"], setup["chapter"]
        flow.write("/generate", {"chapter_ids": [chapter["id"]]})
        candidate = next(item for item in flow.state()["chapters"] if item["id"] == chapter["id"])["candidate"]
        lock = client.post(f"/api/chapters/{chapter['id']}/lock", headers=flow.headers, json={})
        assert lock.status_code == 200, lock.text
        yield client, repository, setup, candidate, lock.json()["lease_token"]


def body(chapter, candidate, lease):
    return {"lease_token": lease, "base_revision": chapter["revision"],
            "content": candidate["content"], "input_fingerprint": candidate["input_fingerprint"]}


def change_source(setup):
    flow = setup["flow"]
    row = next(item for item in flow.state()["requirements"] if item["chapter_id"] == setup["chapter"]["id"])
    flow.write("/requirements/" + row["id"], {"response": "另一位负责人已重新核对的新响应。"}, "PATCH")


@pytest.mark.parametrize("operation", ["draft", "versions"])
def test_source_change_after_candidate_preview_rejects_atomic_write(guarded_context, operation):
    client, repository, setup, candidate, lease = guarded_context
    flow, chapter = setup["flow"], setup["chapter"]
    payload = body(chapter, candidate, lease)
    change_source(setup)
    # 来源变化没有改变章节版本号，这是只检查章节版本无法发现的真实窗口。
    assert repository.read().chapters[chapter["id"]].revision == chapter["revision"]
    before = repository.read()
    if operation == "draft":
        payload["sequence"] = 1
        response = client.put(f"/api/chapters/{chapter['id']}/draft", headers=flow.headers, json=payload)
    else:
        payload["idempotency_key"] = str(uuid4())
        response = client.post(f"/api/chapters/{chapter['id']}/versions", headers=flow.headers, json=payload)
    assert response.status_code == 409, response.text
    assert (response.json().get("code") or response.json().get("error", {}).get("code")) == "INPUT_FINGERPRINT_STALE"
    assert repository.read() == before


@pytest.mark.parametrize("operation", ["draft", "versions"])
@pytest.mark.parametrize("explicit_null", [False, True])
def test_missing_or_null_fingerprint_cannot_bypass_sources(guarded_context, operation, explicit_null):
    client, repository, setup, candidate, lease = guarded_context
    flow, chapter = setup["flow"], setup["chapter"]
    payload = body(chapter, candidate, lease)
    if explicit_null:
        payload["input_fingerprint"] = None
    else:
        payload.pop("input_fingerprint")
    before = repository.read()
    if operation == "draft":
        payload["sequence"] = 1
        response = client.put(f"/api/chapters/{chapter['id']}/draft", headers=flow.headers, json=payload)
    else:
        payload["idempotency_key"] = str(uuid4())
        response = client.post(f"/api/chapters/{chapter['id']}/versions", headers=flow.headers, json=payload)
    assert response.status_code == 409, response.text
    assert (response.json().get("code") or response.json().get("error", {}).get("code")) == "INPUT_FINGERPRINT_REQUIRED"
    assert repository.read() == before


def test_saved_draft_retains_original_fingerprint_and_cannot_commit_after_change(guarded_context):
    client, repository, setup, candidate, lease = guarded_context
    flow, chapter = setup["flow"], setup["chapter"]
    payload = body(chapter, candidate, lease)
    response = client.put(f"/api/chapters/{chapter['id']}/draft", headers=flow.headers,
                          json={**payload, "sequence": 1})
    assert response.status_code == 200, response.text
    assert response.json()["input_fingerprint"] == candidate["input_fingerprint"]
    change_source(setup)
    loaded = client.get(f"/api/chapters/{chapter['id']}", headers=flow.headers).json()
    assert loaded["draft"]["input_fingerprint"] == candidate["input_fingerprint"]
    assert loaded["draft"]["input_fingerprint"] != flow.state()["input_fingerprint"]
    before = repository.read()
    response = client.post(f"/api/chapters/{chapter['id']}/versions", headers=flow.headers,
                           json={**payload, "idempotency_key": str(uuid4())})
    assert response.status_code == 409, response.text
    assert (response.json().get("code") or response.json().get("error", {}).get("code")) == "INPUT_FINGERPRINT_STALE"
    assert repository.read() == before
    assert repository.read().chapters[chapter["id"]].drafts["alpha-manager"].content == candidate["content"]


def test_current_fingerprint_allows_explicit_manual_write(guarded_context):
    client, repository, setup, candidate, lease = guarded_context
    flow, chapter = setup["flow"], setup["chapter"]
    change_source(setup)
    payload = {**body(chapter, candidate, lease), "content": "已人工重新核对当前来源的手工正文。",
               "input_fingerprint": flow.state()["input_fingerprint"]}
    response = client.put(f"/api/chapters/{chapter['id']}/draft", headers=flow.headers,
                          json={**payload, "sequence": 1})
    assert response.status_code == 200, response.text
    response = client.post(f"/api/chapters/{chapter['id']}/versions", headers=flow.headers,
                           json={**payload, "idempotency_key": str(uuid4())})
    assert response.status_code == 200, response.text
    assert repository.read().chapters[chapter["id"]].content == payload["content"]


def test_retry_returns_original_commit_but_changed_request_key_is_conflict(guarded_context):
    client, repository, setup, candidate, lease = guarded_context
    flow, chapter = setup["flow"], setup["chapter"]
    payload = {**body(chapter, candidate, lease), "idempotency_key": str(uuid4())}
    response = client.post(f"/api/chapters/{chapter['id']}/versions", headers=flow.headers, json=payload)
    assert response.status_code == 200, response.text
    original = response.json()
    change_source(setup)
    before = repository.read()
    retry = client.post(f"/api/chapters/{chapter['id']}/versions", headers=flow.headers, json=payload)
    assert retry.status_code == 200, retry.text
    assert retry.json() == original
    assert repository.read() == before
    changed = deepcopy(payload)
    changed["input_fingerprint"] = flow.state()["input_fingerprint"]
    conflict = client.post(f"/api/chapters/{chapter['id']}/versions", headers=flow.headers, json=changed)
    assert conflict.status_code == 409, conflict.text
    assert (conflict.json().get("code") or conflict.json().get("error", {}).get("code")) == "IDEMPOTENCY_CONFLICT"
    assert repository.read() == before


def test_independent_seed_demo_keeps_optional_fingerprint_compatibility():
    repository = MemoryRepository(seed_state())
    with TestClient(create_app(repository=repository)) as client:
        headers = login(client)
        lease = client.post("/api/chapters/alpha-tech/lock", headers=headers, json={}).json()["lease_token"]
        payload = {"lease_token": lease, "base_revision": 1, "content": "独立示例手工正文。"}
        saved = client.put("/api/chapters/alpha-tech/draft", headers=headers, json={**payload, "sequence": 1})
        assert saved.status_code == 200, saved.text
        assert saved.json()["input_fingerprint"] is None
        committed = client.post("/api/chapters/alpha-tech/versions", headers=headers,
                                json={**payload, "idempotency_key": str(uuid4())})
        assert committed.status_code == 200, committed.text


def test_stale_input_never_bypasses_editing_lease(guarded_context):
    client, repository, setup, candidate, lease = guarded_context
    flow, chapter = setup["flow"], setup["chapter"]
    change_source(setup)
    before = repository.read()
    response = client.put(f"/api/chapters/{chapter['id']}/draft", headers=flow.headers,
                          json={**body(chapter, candidate, lease), "lease_token": "invalid-lease", "sequence": 1})
    assert response.status_code == 423, response.text
    assert repository.read() == before
