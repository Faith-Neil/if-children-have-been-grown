# 为什么有这个文件：通过真实资料接口验证多人修改、失败重试和已读版本保护。
# 它解决什么问题：避免旧表单覆盖另一人的修改，或失败请求留下资料、版本与重复请求收据。

from uuid import uuid4

import pytest

from test_reference_flow import client, login


def read_library(client, actor):
    response = client.get("/api/v1/library", headers=actor)
    assert response.status_code == 200, response.text
    result = response.json()
    assert response.headers["etag"] == f'"{result["revision"]}"'
    return result


def mutation_headers(actor, revision, key=None):
    # 调用者传入实际读到的版本，不能在发请求时自动升级到服务器最新版本。
    return {**actor, "If-Match": str(revision), "Idempotency-Key": key or str(uuid4())}


def create_record(client, actor, name="合成资料旧表单验收"):
    before = read_library(client, actor)
    payload = {
        "name": name,
        "type": "qualification",
        "content": "合成证据原内容：证书编号 BASIS-001，经人工核对。",
        "valid_until": "2027-12-31",
        "status": "confirmed",
        "reason": "初次逐项核对合成资料。",
    }
    headers = mutation_headers(actor, before["revision"])
    response = client.post("/api/v1/library", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    return response.json(), payload, headers


def repository_snapshot(client):
    # 一并核对实际仓储中的正文、版本、审计、收据和项目，不能只看错误码。
    return client.app.state.service.repository.read()


def test_old_company_version_cannot_overwrite_after_another_record_changes(client):
    manager, editor = login(client, "alpha-manager"), login(client, "alpha-editor")
    first, _, _ = create_record(client, manager)
    second, _, _ = create_record(client, manager, "另一个协作者更新的合成资料")
    previously_read = read_library(client, manager)
    old_headers = mutation_headers(manager, previously_read["revision"])

    changed = client.patch(
        "/api/v1/library/" + second["item"]["id"],
        headers=mutation_headers(editor, previously_read["revision"]),
        json={"content": "另一位协作者的新内容，尚未重新确认。"},
    )
    assert changed.status_code == 200, changed.text
    current = read_library(client, manager)
    before = repository_snapshot(client)
    rejected = client.patch(
        "/api/v1/library/" + first["item"]["id"],
        headers=old_headers,
        json={"content": "旧页面试图直接覆盖资料。", "status": "confirmed", "reason": "旧页面的核对依据。"},
    )
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["code"] == "VERSION_CONFLICT"
    assert rejected.json()["details"]["current_revision"] == current["revision"]
    assert repository_snapshot(client) == before
    assert read_library(client, manager) == current
    assert next(item for item in current["items"] if item["id"] == first["item"]["id"]) == first["item"]


def test_stale_create_does_not_leave_a_record_or_idempotency_receipt(client):
    actor = login(client)
    previously_read = read_library(client, actor)
    create_record(client, actor, "在旧新建窗口打开后加入的合成资料")
    before = repository_snapshot(client)
    rejected = client.post(
        "/api/v1/library",
        headers=mutation_headers(actor, previously_read["revision"]),
        json={"name": "不能偷偷新增的旧窗口资料", "type": "qualification", "content": "旧窗口内容。"},
    )
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["code"] == "VERSION_CONFLICT"
    assert repository_snapshot(client) == before
    assert all(item["name"] != "不能偷偷新增的旧窗口资料" for item in read_library(client, actor)["items"])


def test_explicit_new_read_and_reviewed_payload_can_save_without_restoring_old_values(client):
    manager, editor = login(client, "alpha-manager"), login(client, "alpha-editor")
    created, _, _ = create_record(client, manager)
    old_listing = read_library(client, manager)
    path = "/api/v1/library/" + created["item"]["id"]
    external = client.patch(
        path, headers=mutation_headers(editor, old_listing["revision"]),
        json={"content": "另一个协作者保存的最新编号 BASIS-900。"},
    )
    assert external.status_code == 200, external.text
    obsolete = {"content": created["item"]["content"], "status": "confirmed", "reason": "尚未看到另一人的改动。"}
    rejected = client.patch(path, headers=mutation_headers(manager, old_listing["revision"]), json=obsolete)
    assert rejected.status_code == 409, rejected.text

    reread = read_library(client, manager)
    current_record = next(item for item in reread["items"] if item["id"] == created["item"]["id"])
    assert current_record["content"] == "另一个协作者保存的最新编号 BASIS-900。"
    assert current_record["status"] == "pending"
    reviewed_payload = {
        "content": current_record["content"] + " 本次已核对最新编号，补充用途说明。",
        "status": "confirmed",
        "reason": "重新读取后逐项核对 BASIS-900，保留另一位协作者的新编号。",
    }
    accepted = client.patch(path, headers=mutation_headers(manager, reread["revision"]), json=reviewed_payload)
    assert accepted.status_code == 200, accepted.text
    result = accepted.json()
    assert result["revision"] == reread["revision"] + 1
    assert result["item"]["revision"] == current_record["revision"] + 1
    assert result["item"]["content"] == reviewed_payload["content"]
    assert result["item"]["reason"] == reviewed_payload["reason"]
    assert result["item"]["status"] == "confirmed"
    assert next(item for item in read_library(client, manager)["items"] if item["id"] == created["item"]["id"]) == result["item"]


def test_identical_retry_keeps_original_receipt_without_duplicating_current_records(client):
    actor = login(client)
    first, payload, original_headers = create_record(client, actor)
    create_record(client, actor, "原请求完成后另一笔合成资料")
    current = read_library(client, actor)
    before = repository_snapshot(client)
    replay = client.post("/api/v1/library", headers=original_headers, json=payload)
    assert replay.status_code == 200, replay.text
    assert replay.json() == first
    assert repository_snapshot(client) == before
    assert read_library(client, actor) == current
    assert len([item for item in current["items"] if item["id"] == first["item"]["id"]]) == 1


@pytest.mark.parametrize("change", ["content", "read_revision", "target_action"])
def test_reused_request_key_with_changed_request_has_no_side_effects(client, change):
    actor = login(client)
    first, payload, original_headers = create_record(client, actor)
    headers, request_payload = dict(original_headers), dict(payload)
    method, path = "POST", "/api/v1/library"
    if change == "content":
        request_payload["content"] = "同一个请求标记不允许换成另一份内容。"
    elif change == "read_revision":
        headers["If-Match"] = str(read_library(client, actor)["revision"])
    else:
        method, path = "PATCH", "/api/v1/library/" + first["item"]["id"]
    before = repository_snapshot(client)
    rejected = client.request(method, path, headers=headers, json=request_payload)
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["code"] == "IDEMPOTENCY_CONFLICT"
    assert repository_snapshot(client) == before


@pytest.mark.parametrize("account", ["beta-editor", "beta-manager"])
def test_other_company_cannot_read_or_change_known_record_even_with_its_current_version(client, account):
    owner = login(client, "alpha-manager")
    created, _, _ = create_record(client, owner)
    outsider = login(client, account)
    outsiders_listing = read_library(client, outsider)
    assert created["item"]["id"] not in {item["id"] for item in outsiders_listing["items"]}
    before = repository_snapshot(client)
    rejected = client.patch(
        "/api/v1/library/" + created["item"]["id"],
        headers=mutation_headers(outsider, outsiders_listing["revision"]),
        json={"content": "已知甲公司ID也不能跨公司写入。"},
    )
    assert rejected.status_code == 404, rejected.text
    assert rejected.json()["code"] == "NOT_FOUND"
    assert repository_snapshot(client) == before


@pytest.mark.parametrize("method", ["POST", "PATCH"])
def test_viewer_cannot_mutate_or_replay_a_writers_request_key(client, method):
    writer = login(client, "alpha-manager")
    created, payload, writer_headers = create_record(client, writer)
    viewer = login(client, "alpha-viewer")
    current = read_library(client, viewer)
    assert created["item"]["id"] in {item["id"] for item in current["items"]}
    headers = mutation_headers(viewer, current["revision"], writer_headers["Idempotency-Key"])
    path = "/api/v1/library" if method == "POST" else "/api/v1/library/" + created["item"]["id"]
    before = repository_snapshot(client)
    rejected = client.request(method, path, headers=headers, json=payload)
    assert rejected.status_code == 403, rejected.text
    assert rejected.json()["code"] == "FORBIDDEN"
    assert repository_snapshot(client) == before


@pytest.mark.parametrize("missing,code", [
    ("If-Match", "IF_MATCH_REQUIRED"),
    ("Idempotency-Key", "IDEMPOTENCY_KEY_REQUIRED"),
])
def test_missing_write_preconditions_do_not_commit_partial_changes(client, missing, code):
    actor = login(client)
    created, _, _ = create_record(client, actor)
    headers = mutation_headers(actor, read_library(client, actor)["revision"])
    del headers[missing]
    before = repository_snapshot(client)
    rejected = client.patch(
        "/api/v1/library/" + created["item"]["id"], headers=headers,
        json={"content": "缺少写入前提不应变成已保存资料。"},
    )
    assert rejected.status_code == 428, rejected.text
    assert rejected.json()["code"] == code
    assert repository_snapshot(client) == before
