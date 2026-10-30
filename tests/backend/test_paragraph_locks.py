# 为什么有这个文件：验证编辑台段落锁定（APP-M2-T163，PRD v1.8 §5.11.8）。
# 它解决什么问题：锁定段落不能被手改提交、草稿自动提交改动或删除（挪位置可以）；对话助手选区落在锁定段落上不调用模型；
# 章节循环里锁定段落的问题转人工；只有锁定人或项目负责人能解锁；只读成员不能锁；版本不对不能锁。

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from icg.domain.chapter_loop import LoopContext, check_paragraphs
from icg.domain.domain import DomainError
from icg.domain.paragraph_locks import locked_lines, refuse_locked_selection
from icg_demo.main import create_app

CHAPTER = "alpha-tech"
BODY = "# 运维服务\n\n本项目提供七乘二十四小时驻场运维。\n\n巡检每月一次，备份每日一次。\n\n应急预案每季度演练一次。"
LOCKED = "本项目提供七乘二十四小时驻场运维。"


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


def acquire(client, headers):
    response = client.post(f"/api/chapters/{CHAPTER}/lock", headers=headers, json={"takeover_reason": None})
    assert response.status_code == 200, response.text
    return response.json()["lease_token"]


def commit(client, headers, lease, content, key):
    return client.post(f"/api/chapters/{CHAPTER}/versions", headers=headers,
                       json={"lease_token": lease, "base_revision": chapter(client, headers)["revision"],
                             "content": content, "idempotency_key": key})


def locks_path(client, headers):
    return f"/api/v1/projects/{chapter(client, headers)['project_id']}/chapters/{CHAPTER}/paragraph-locks"


def lock(client, headers, text=LOCKED, reason="已与客户确认的承诺原文"):
    data = chapter(client, headers)
    key = next(p["key"] for p in data["paragraphs"] if data["content"].splitlines()[p["line_start"]] == text)
    return client.post(locks_path(client, headers), headers=headers,
                       json={"paragraph_key": key, "base_revision": data["revision"], "reason": reason})


def test_locked_paragraph_cannot_be_changed_or_deleted_but_can_move(client):
    editor = login(client)
    lease = acquire(client, editor)
    assert commit(client, editor, lease, BODY, "lock-body-1").status_code == 200
    locked = lock(client, editor)
    assert locked.status_code == 200, locked.text
    item = locked.json()["locks"][0]
    assert item["locked_by_name"] and item["can_unlock"] and item["present"]
    marked = [p for p in chapter(client, editor)["paragraphs"] if p["locked"]]
    assert len(marked) == 1 and marked[0]["locked_by_name"] == item["locked_by_name"]

    changed = commit(client, editor, lease, BODY.replace("驻场运维", "远程运维"), "lock-body-2")
    assert changed.status_code == 409 and changed.json()["code"] == "PARAGRAPH_LOCKED"
    assert changed.json()["details"]["paragraphs"][0]["excerpt"].startswith("本项目提供")
    deleted = commit(client, editor, lease, BODY.replace(LOCKED, ""), "lock-body-3")
    assert deleted.status_code == 409
    assert chapter(client, editor)["content"] == BODY

    moved = BODY.replace(LOCKED + "\n\n", "") + "\n\n" + LOCKED
    other_edit = moved.replace("每月一次", "每两周一次")
    assert commit(client, editor, lease, other_edit, "lock-body-4").status_code == 200
    after = client.get(locks_path(client, editor), headers=editor).json()["locks"][0]
    assert after["present"] and after["line_start"] == len(other_edit.splitlines()) - 1


def test_only_locker_or_project_lead_can_unlock(client):
    editor, manager, viewer = login(client), login(client, "alpha-manager"), login(client, "alpha-viewer")
    lease = acquire(client, editor)
    commit(client, editor, lease, BODY, "lock-unlock-1")
    assert lock(client, viewer).status_code == 403
    service = client.app.state.service
    project_id = chapter(client, editor)["project_id"]
    service.repository.transaction(lambda st: st.project_teams[project_id]["members"].__setitem__(
        "alpha-business", {"user_id": "alpha-business", "project_role": "writer", "volumes": ["technical"]}))
    key = lock(client, manager).json()["locks"][0]["paragraph_key"]
    assert client.get(locks_path(client, editor), headers=editor).json()["locks"][0]["can_unlock"] is False
    other = login(client, "alpha-business")
    assert client.delete(f"{locks_path(client, other)}/{key}", headers=other).status_code == 403
    assert client.delete(f"{locks_path(client, editor)}/{key}", headers=editor).status_code == 403
    released = client.delete(f"{locks_path(client, manager)}/{key}", headers=manager)
    assert released.status_code == 200 and released.json()["locks"] == []
    assert commit(client, editor, lease, BODY.replace("驻场运维", "远程运维"), "lock-unlock-2").status_code == 200


def test_lock_needs_current_revision_and_cannot_repeat(client):
    editor = login(client)
    lease = acquire(client, editor)
    commit(client, editor, lease, BODY, "lock-rev-1")
    data = chapter(client, editor)
    key = data["paragraphs"][1]["key"]
    stale = client.post(locks_path(client, editor), headers=editor,
                        json={"paragraph_key": key, "base_revision": data["revision"] - 1})
    assert stale.status_code == 409 and stale.json()["code"] == "REVISION_CONFLICT"
    assert client.post(locks_path(client, editor), headers=editor,
                       json={"paragraph_key": key, "base_revision": data["revision"]}).status_code == 200
    again = client.post(locks_path(client, editor), headers=editor,
                        json={"paragraph_key": key, "base_revision": data["revision"]})
    assert again.status_code == 409 and again.json()["code"] == "PARAGRAPH_ALREADY_LOCKED"
    missing = client.post(locks_path(client, editor), headers=editor,
                          json={"paragraph_key": "pk-nope", "base_revision": data["revision"]})
    assert missing.status_code == 404


def test_release_does_not_autocommit_a_draft_that_changes_a_locked_paragraph(client):
    editor = login(client)
    lease = acquire(client, editor)
    commit(client, editor, lease, BODY, "lock-draft-1")
    lock(client, editor)
    revision = chapter(client, editor)["revision"]
    draft = client.put(f"/api/chapters/{CHAPTER}/draft", headers=editor,
                       json={"lease_token": lease, "base_revision": revision, "sequence": 1,
                             "content": BODY.replace("驻场运维", "远程运维")})
    assert draft.status_code == 200, draft.text
    released = client.post(f"/api/chapters/{CHAPTER}/lock/release", headers=editor, json={"lease_token": lease})
    assert released.status_code == 200, released.text
    after = chapter(client, editor)
    assert after["revision"] == revision and after["content"] == BODY
    assert after["draft"]["content"].count("远程运维") == 1


def _chapter_with_lock(content: str, locked_text: str):
    from icg.domain.paragraph_keys import split
    block = next(b for b in split(content) if b["text"] == locked_text)
    workflow = {"paragraph_locks": {"c": {"k": {"paragraph_key": "k", "hash": block["hash"], "locked_at": "t",
                                                "locked_by_name": "甲", "locked_by": "u"}}}}
    chapter = SimpleNamespace(id="c", project_id="p", content=content, revision=1,
                              versions=[{"revision": 1, "content": content}])
    return chapter, workflow


def test_assistant_selection_on_locked_paragraph_is_refused_before_any_model_call():
    chapter, workflow = _chapter_with_lock(BODY, LOCKED)
    state = SimpleNamespace(workflows={"p": workflow})
    start = BODY.index(LOCKED)
    with pytest.raises(DomainError) as whole:
        refuse_locked_selection(state, chapter, start + 2, start + 8)
    assert whole.value.code == "PARAGRAPH_LOCKED" and whole.value.details == {"partial": False}
    with pytest.raises(DomainError) as partial:
        refuse_locked_selection(state, chapter, start, BODY.index("每月一次"))
    assert partial.value.details == {"partial": True}
    free = BODY.index("应急预案")
    refuse_locked_selection(state, chapter, free, free + 4)


def test_chapter_loop_routes_issues_in_locked_paragraphs_to_people():
    content = "本项目提供【待补：服务期限】驻场运维。\n巡检【待补：服务期限】一次。"
    chapter, workflow = _chapter_with_lock(content, "本项目提供【待补：服务期限】驻场运维。")
    lines = locked_lines(chapter, workflow)
    assert lines == {0}
    facts = [{"id": "f1", "key": "服务期限", "status": "confirmed", "variable": "{{fact:f1}}"}]
    findings = check_paragraphs(content.split("\n"), LoopContext(facts=facts, locked_paragraphs=lines))
    by_line = {f["paragraph_index"]: f for f in findings}
    assert by_line[0]["human_reason"] == "PARAGRAPH_LOCKED" and by_line[0]["route"] != "auto_fix"
    assert by_line[1]["route"] == "auto_fix"


def test_locking_in_a_new_project_keeps_the_workspace_readable(client):
    manager = login(client, "alpha-manager")
    project_id = client.post("/api/v1/projects", headers=manager, json={"name": "段落锁定新项目"}).json()["id"]
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=manager).json()
    chapter_id = next(c["id"] for c in workspace["chapters"] if c["volume"] == "technical")
    lease = client.post(f"/api/chapters/{chapter_id}/lock", headers=manager, json={}).json()["lease_token"]
    committed = client.post(f"/api/chapters/{chapter_id}/versions", headers=manager, json={
        "lease_token": lease, "base_revision": workspace["chapters"][0]["revision"] if workspace["chapters"][0]["id"] == chapter_id
        else next(c["revision"] for c in workspace["chapters"] if c["id"] == chapter_id),
        "content": BODY, "idempotency_key": "fresh-project-lock-1"})
    assert committed.status_code == 200, committed.text
    data = client.get(f"/api/chapters/{chapter_id}", headers=manager).json()
    locked = client.post(f"/api/v1/projects/{project_id}/chapters/{chapter_id}/paragraph-locks", headers=manager,
                         json={"paragraph_key": data["paragraphs"][1]["key"], "base_revision": data["revision"]})
    assert locked.status_code == 200, locked.text
    assert client.get(f"/api/v1/projects/{project_id}/workspace", headers=manager).status_code == 200
