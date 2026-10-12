# 为什么有这个文件：核对片段发布的公司隔离、版本头、拦截和幂等回执。
# 它解决什么问题：避免拦截发布改掉已存正文，或把其他公司的片段内容返回给调用方。

from uuid import uuid4

from test_reference_flow import client, login


CLEAN = {
    "product": "巡检产品",
    "snippet_type": "solution",
    "variables": ["uptime"],
    "source_group": "synthetic-source",
    "boilerplate_group": "synthetic-boilerplate",
    "draft_body": "巡检安排使用 {{uptime}}。",
}


def headers(actor, revision=None, key=None):
    result = {**actor, "Idempotency-Key": key or str(uuid4())}
    if revision is not None:
        result["If-Match"] = str(revision)
    return result


def create(client, actor, payload=None, key=None):
    body = dict(CLEAN if payload is None else payload)
    response = client.post("/api/v1/snippet-publications", headers=headers(actor, key=key), json=body)
    assert response.status_code == 200, response.text
    return response


def publish(client, actor, snippet_id, revision, key=None):
    return client.post(
        f"/api/v1/snippet-publications/{snippet_id}/publish",
        headers=headers(actor, revision, key), json={})


def store_snapshot(client):
    return client.app.state.snippet_publications.snapshot()


def receipt_count(client):
    return len(client.app.state.service.repository.read().workflow_receipts)


def test_server_assigns_id_and_ignores_client_company(client):
    actor = login(client)
    rejected = client.post("/api/v1/snippet-publications", headers=headers(actor), json={**CLEAN, "company_id": "beta", "id": "client-id"})
    assert rejected.status_code == 422, rejected.text
    assert rejected.json()["code"] == "VALIDATION_ERROR"
    created = create(client, actor)
    item = created.json()
    assert item["id"].startswith("snippet-")
    assert item["id"] != "client-id"
    assert item["company_id"] == "alpha"
    assert item["draft_revision"] == 1
    assert item["published_revision"] == 0
    assert item["kb_sync_status"] == "unsynced"
    assert item["published_body"] == ""
    assert created.headers["etag"] == '"1"'
    again = create(client, actor)
    assert again.json()["id"] != item["id"]


def test_get_returns_etag_and_sync_status_without_a_sync_route(client):
    actor = login(client)
    item = create(client, actor).json()
    listed = client.get("/api/v1/snippet-publications", headers=actor)
    assert listed.status_code == 200, listed.text
    assert listed.headers["etag"]
    assert listed.json()["items"] == [item]
    detail = client.get(f"/api/v1/snippet-publications/{item['id']}", headers=actor)
    assert detail.status_code == 200, detail.text
    assert detail.headers["etag"] == f'"{item["draft_revision"]}"'
    assert detail.json()["kb_sync_status"] == "unsynced"
    missing = client.get(f"/api/v1/snippet-publications/{item['id']}/sync", headers=actor)
    assert missing.status_code == 404


def test_other_company_id_is_not_found_and_hides_the_body(client):
    alpha = login(client, "alpha-manager")
    beta = login(client, "beta-manager")
    secret = "甲公司片段正文仅本公司可见 SYNTH-ALPHA-BODY"
    item = create(client, alpha, {**CLEAN, "draft_body": secret}).json()
    hidden = client.get(f"/api/v1/snippet-publications/{item['id']}", headers=beta)
    assert hidden.status_code == 404, hidden.text
    assert hidden.json()["code"] == "NOT_FOUND"
    assert secret not in hidden.text
    beta_list = client.get("/api/v1/snippet-publications", headers=beta)
    assert beta_list.json()["items"] == []
    assert secret not in beta_list.text


def test_draft_save_checks_draft_revision_and_keeps_published_body(client):
    actor = login(client)
    item = create(client, actor).json()
    published = publish(client, actor, item["id"], 1)
    assert published.status_code == 200, published.text
    assert published.json()["blocked"] is False
    saved = client.put(
        f"/api/v1/snippet-publications/{item['id']}",
        headers=headers(actor, 1), json={"draft_body": "新草稿仍使用 {{uptime}}。"})
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["draft_revision"] == 2
    assert body["draft_body"] == "新草稿仍使用 {{uptime}}。"
    assert body["published_body"] == CLEAN["draft_body"]
    assert body["published_revision"] == 1
    assert saved.headers["etag"] == '"2"'
    before = store_snapshot(client)
    missing = client.put(
        f"/api/v1/snippet-publications/{item['id']}", headers=headers(actor), json={"draft_body": "缺少版本的草稿"})
    assert missing.status_code == 428, missing.text
    assert missing.json()["code"] == "IF_MATCH_REQUIRED"
    assert store_snapshot(client) == before
    stale = client.put(
        f"/api/v1/snippet-publications/{item['id']}",
        headers=headers(actor, 1), json={"draft_body": "旧版本草稿"})
    assert stale.status_code == 409, stale.text
    assert stale.json()["code"] == "VERSION_CONFLICT"
    assert stale.json()["details"]["current_revision"] == 2
    assert store_snapshot(client) == before


def test_blocked_publish_keeps_records_and_audits_but_stores_a_receipt(client):
    actor = login(client)
    item = create(client, actor, {**CLEAN, "draft_body": "我们承诺99%可用。", "source_group": "synthetic-source"}).json()
    before = store_snapshot(client)
    receipts = receipt_count(client)
    key = str(uuid4())
    blocked = publish(client, actor, item["id"], 1, key)
    assert blocked.status_code == 200, blocked.text
    body = blocked.json()
    assert body["blocked"] is True
    assert [reason["code"] for reason in body["reasons"]] == ["hardcoded_promise"]
    assert body["item"]["published_body"] == ""
    assert body["item"]["kb_sync_status"] == "unsynced"
    assert store_snapshot(client) == before
    assert receipt_count(client) == receipts + 1
    replay = publish(client, actor, item["id"], 1, key)
    assert replay.status_code == 200, replay.text
    assert replay.headers.get("idempotent-replayed") == "true"
    assert replay.json() == body
    assert store_snapshot(client) == before
    conflict = publish(client, actor, item["id"], 2, key)
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"
    assert store_snapshot(client) == before


def test_publish_lists_every_block_reason_without_another_companys_text(client):
    alpha = login(client, "alpha-manager")
    beta = login(client, "beta-manager")
    foreign = "乙公司片段正文 SYNTH-BETA-BODY"
    beta_item = create(client, beta, {**CLEAN, "draft_body": foreign}).json()
    unpublished = create(client, alpha, {**CLEAN, "draft_body": "尚未发布的引用目标。"}).json()
    draft = f"承诺99 {{{{missing}}}} 报告 snippet:{beta_item['id']} snippet:{unpublished['id']}"
    item = create(client, alpha, {
        **CLEAN, "variables": [], "source_group": "", "draft_body": draft}).json()
    before = store_snapshot(client)
    blocked = publish(client, alpha, item["id"], 1)
    assert blocked.status_code == 200, blocked.text
    assert [reason["code"] for reason in blocked.json()["reasons"]] == [
        "real_report", "hardcoded_promise", "unknown_variable", "unpublished_body", "cross_company_reference"]
    assert foreign not in blocked.text
    assert "尚未发布的引用目标" not in blocked.text
    assert store_snapshot(client) == before


def test_successful_publish_replaces_published_body_and_records_an_audit(client):
    actor = login(client)
    item = create(client, actor).json()
    result = publish(client, actor, item["id"], 1)
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["blocked"] is False
    assert body["reasons"] == []
    assert body["item"]["published_body"] == CLEAN["draft_body"]
    assert body["item"]["published_revision"] == 1
    assert body["item"]["draft_revision"] == 1
    assert body["item"]["kb_sync_status"] == "unsynced"
    snapshot = store_snapshot(client)
    assert snapshot["audits"][item["id"]][0]["action"] == "publish"
    assert snapshot["audits"][item["id"]][0]["published_revision"] == 1


def test_missing_idempotency_key_and_viewer_do_not_publish(client):
    manager = login(client, "alpha-manager")
    viewer = login(client, "alpha-viewer")
    item = create(client, manager).json()
    before = store_snapshot(client)
    receipts = receipt_count(client)
    missing = client.post(f"/api/v1/snippet-publications/{item['id']}/publish", headers={**manager, "If-Match": "1"}, json={})
    assert missing.status_code == 428, missing.text
    assert missing.json()["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    forbidden = publish(client, viewer, item["id"], 1)
    assert forbidden.status_code == 403, forbidden.text
    assert forbidden.json()["code"] == "FORBIDDEN"
    assert store_snapshot(client) == before
    assert receipt_count(client) == receipts


def test_sync_uses_published_revision_and_failure_does_not_mark_synced(client):
    actor = login(client)
    item = create(client, actor).json()
    before_publish = store_snapshot(client)
    unpublished = client.post(
        f"/api/v1/snippet-publications/{item['id']}/sync", headers=headers(actor, 0), json={})
    assert unpublished.status_code == 200, unpublished.text
    assert unpublished.json()["synced"] is False
    assert unpublished.json()["item"]["kb_sync_status"] == "failed"
    assert unpublished.json()["item"]["published_revision"] == 0
    failed_audits = store_snapshot(client)["audits"][item["id"]]
    assert failed_audits == before_publish["audits"][item["id"]]
    saved = client.put(
        f"/api/v1/snippet-publications/{item['id']}",
        headers=headers(actor, 1),
        json={"draft_body": "知识库拒绝这段 [[sync-fail]]，变量仍是 {{uptime}}。"})
    assert saved.status_code == 200, saved.text
    published = publish(client, actor, item["id"], 2)
    assert published.status_code == 200, published.text
    assert published.json()["blocked"] is False
    synced_attempt = client.post(
        f"/api/v1/snippet-publications/{item['id']}/sync",
        headers=headers(actor, published.json()["item"]["published_revision"]), json={})
    assert synced_attempt.status_code == 200, synced_attempt.text
    assert synced_attempt.json()["synced"] is False
    assert synced_attempt.json()["item"]["kb_sync_status"] == "failed"
    assert synced_attempt.json()["item"]["published_body"] == saved.json()["draft_body"]
    assert store_snapshot(client)["audits"][item["id"]][-1]["action"] == "publish"
    clean = client.put(
        f"/api/v1/snippet-publications/{item['id']}",
        headers=headers(actor, saved.json()["draft_revision"]),
        json={"draft_body": CLEAN["draft_body"]})
    assert clean.status_code == 200, clean.text
    republished = publish(client, actor, item["id"], clean.json()["draft_revision"])
    assert republished.json()["item"]["kb_sync_status"] == "unsynced"
    done = client.post(
        f"/api/v1/snippet-publications/{item['id']}/sync",
        headers=headers(actor, republished.json()["item"]["published_revision"]), json={})
    assert done.status_code == 200, done.text
    assert done.json()["synced"] is True
    assert done.json()["item"]["kb_sync_status"] == "synced"
    assert done.json()["item"]["published_revision"] == republished.json()["item"]["published_revision"]
    assert store_snapshot(client)["audits"][item["id"]][-1]["action"] == "sync"
    stale = client.post(
        f"/api/v1/snippet-publications/{item['id']}/sync",
        headers=headers(actor, 0), json={})
    assert stale.status_code == 409, stale.text
    assert stale.json()["code"] == "VERSION_CONFLICT"
    assert stale.json()["details"]["current_revision"] == done.json()["item"]["published_revision"]


def test_snippet_receipt_shares_the_library_scope(client):
    actor = login(client)
    library = client.get("/api/v1/library", headers=actor)
    assert library.status_code == 200, library.text
    key = str(uuid4())
    created = client.post("/api/v1/library", headers=headers(actor, library.json()["revision"], key), json={
        "name": "合成资料",
        "type": "qualification",
        "content": "合成证据。",
        "valid_until": "2027-12-31",
        "status": "confirmed",
        "reason": "初次核对。",
    })
    assert created.status_code == 200, created.text
    conflict = client.post("/api/v1/snippet-publications", headers=headers(actor, key=key), json=CLEAN)
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"


def test_snippet_records_are_not_stored_on_demo_state(client):
    actor = login(client)
    before = client.app.state.service.repository.read()
    item = create(client, actor).json()
    after = client.app.state.service.repository.read()
    assert item["id"] not in after.library
    assert before.library == after.library
    assert before.chapters == after.chapters
    assert before.workflows == after.workflows
    assert item["id"] in client.app.state.snippet_publications.records
