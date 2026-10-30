# 为什么有这个文件：验证编辑台版本回退（APP-M2-T175）。
# 它解决什么问题：回退生成新版本、历史不删、修改方式记“版本回退”；回来的段落沿用原段落键与来源；
# 没有编辑锁、版本不是最新、有未提交草稿、目标与当前相同、会改动锁定段落、系统章节、只读成员时都被拒绝。

import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app

CHAPTER = "alpha-tech"
V1 = "运维服务方案\n\n驻场工程师两名，七乘二十四小时值守。\n\n巡检每月一次。"
V2 = "运维服务方案\n\n远程支持为主。\n\n巡检每月一次。\n\n应急演练每季度一次。"


@pytest.fixture
def client():
    with TestClient(create_app()) as actual:
        yield actual


def login(client, account="alpha-editor"):
    response = client.post("/api/v1/auth/login", json={"username": account, "password": "X_2026"})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def chapter(client, headers):
    return client.get(f"/api/chapters/{CHAPTER}", headers=headers).json()


def setup(client):
    editor = login(client)
    lease = client.post(f"/api/chapters/{CHAPTER}/lock", headers=editor, json={"takeover_reason": None}).json()["lease_token"]
    for key, body in (("rollback-v1", V1), ("rollback-v2", V2)):
        response = client.post(f"/api/chapters/{CHAPTER}/versions", headers=editor, json={
            "lease_token": lease, "base_revision": chapter(client, editor)["revision"], "content": body, "idempotency_key": key})
        assert response.status_code == 200, response.text
    data = chapter(client, editor)
    return editor, lease, data, f"/api/v1/projects/{data['project_id']}/chapters/{CHAPTER}/rollback"


def versions(client, headers):
    return client.get(f"/api/chapters/{CHAPTER}/versions", headers=headers).json()["versions"]


def test_rollback_creates_a_new_version_and_keeps_paragraph_keys(client):
    editor, lease, data, path = setup(client)
    history = versions(client, editor)
    target = next(v for v in history if v["content"] == V1)
    response = client.post(path, headers=editor, json={"lease_token": lease, "base_revision": data["revision"],
                                                        "target_revision": target["revision"]})
    assert response.status_code == 200, response.text
    assert response.json()["revision"] == data["revision"] + 1 and response.json()["rollback_from"] == target["revision"]
    after = versions(client, editor)
    assert len(after) == len(history) + 1 and [v["content"] for v in after[:-1]] == [v["content"] for v in history]
    latest = after[-1]
    assert latest["content"] == V1 and latest["edit_mode"] == "rollback" and latest["rollback_from"] == target["revision"]
    assert "rollback_paragraphs" not in latest
    assert [p["key"] for p in latest["paragraphs"]] == [p["key"] for p in target["paragraphs"]]
    audit = client.get(f"/api/chapters/{CHAPTER}/audit", headers=editor).json()["events"]
    assert any(e["action"] == "version.rollback" for e in audit)


def test_rollback_is_checked_like_a_commit(client):
    editor, lease, data, path = setup(client)
    v1 = next(v["revision"] for v in versions(client, editor) if v["content"] == V1)
    body = {"lease_token": lease, "base_revision": data["revision"], "target_revision": v1}
    assert client.post(path, headers=editor, json={**body, "lease_token": "wrong"}).status_code == 423
    stale = client.post(path, headers=editor, json={**body, "base_revision": data["revision"] - 1})
    assert stale.status_code == 409 and stale.json()["code"] == "REVISION_CONFLICT"
    same = client.post(path, headers=editor, json={**body, "target_revision": data["revision"]})
    assert same.status_code == 409 and same.json()["code"] == "ROLLBACK_NOOP"
    missing = client.post(path, headers=editor, json={**body, "target_revision": 999})
    assert missing.status_code == 404
    viewer = login(client, "alpha-viewer")
    assert client.post(path, headers=viewer, json=body).status_code in (403, 423)

    draft = client.put(f"/api/chapters/{CHAPTER}/draft", headers=editor, json={
        "lease_token": lease, "base_revision": data["revision"], "sequence": 1, "content": V2 + "\n草稿里加的一句。"})
    assert draft.status_code == 200, draft.text
    pending = client.post(path, headers=editor, json=body)
    assert pending.status_code == 409 and pending.json()["code"] == "DRAFT_PENDING"
    client.request("DELETE", f"/api/chapters/{CHAPTER}/draft", headers=editor, json={"sequence": 1})

    locks = f"/api/v1/projects/{data['project_id']}/chapters/{CHAPTER}/paragraph-locks"
    key = next(p["key"] for p in data["paragraphs"] if p["line_start"] == V2.splitlines().index("远程支持为主。"))
    assert client.post(locks, headers=editor, json={"paragraph_key": key, "base_revision": data["revision"]}).status_code == 200
    locked = client.post(path, headers=editor, json=body)
    assert locked.status_code == 409 and locked.json()["code"] == "PARAGRAPH_LOCKED"
    assert chapter(client, editor)["content"] == V2


def test_system_chapter_cannot_be_rolled_back(client):
    editor, lease, data, path = setup(client)
    service = client.app.state.service
    service.repository.transaction(lambda st: st.workflows.setdefault(data["project_id"], {}).setdefault(
        "system_chapters", {}).__setitem__(CHAPTER, {"kind": "deviation_table"}))
    v1 = next(v["revision"] for v in versions(client, editor) if v["content"] == V1)
    response = client.post(path, headers=editor, json={"lease_token": lease, "base_revision": data["revision"], "target_revision": v1})
    assert response.status_code == 409 and response.json()["code"] == "SYSTEM_CHAPTER_READONLY"
