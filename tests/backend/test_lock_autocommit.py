# 为什么有这个文件：验证编辑锁释放时草稿自动提交与按公司设置的锁超时（PRD v1.8 §5.11.9 第 1、3 点；APP-M2-T172）。
# 它解决什么问题：主动释放、被接管、超时后他人取锁时，持锁人已保存的草稿自动提交为“手改”版本，避免下一位在旧版本上改；
# 草稿基于旧版本、来源已变或含对话残留时不提交、原样保留；锁时长取公司设置 edit_lock_timeout_minutes。

import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from test_demo import MutableClock
from test_reference_flow import ProjectFlow, login


@pytest.fixture()
def clock():
    return MutableClock()


@pytest.fixture()
def client(clock):
    with TestClient(create_app(clock=clock)) as actual:
        yield actual


def _setup(client):
    flow = ProjectFlow(client).ready()
    chapter = next(c for c in flow.state()["chapters"] if c["volume"] == "technical")
    repo = client.app.state.service.repository
    repo.transaction(lambda st: st.project_teams[flow.id]["members"].__setitem__(
        "alpha-tech", {"user_id": "alpha-tech", "project_role": "writer", "volumes": ["technical"]}))
    repo.transaction(lambda st: setattr(st.chapters[chapter["id"]], "assignee_id", "alpha-tech"))
    return flow, chapter


def _draft(client, flow, chapter_id, headers, text, sequence=1):
    lock = client.post(f"/api/chapters/{chapter_id}/lock", headers=headers, json={})
    assert lock.status_code == 200, lock.text
    current = client.get(f"/api/chapters/{chapter_id}", headers=headers).json()
    saved = client.put(f"/api/chapters/{chapter_id}/draft", headers=headers, json={
        "lease_token": lock.json()["lease_token"], "base_revision": current["revision"], "sequence": sequence,
        "content": text, "input_fingerprint": flow.state()["input_fingerprint"]})
    assert saved.status_code == 200, saved.text
    return lock.json()["lease_token"], current["revision"]


def _chapter(client, chapter_id, headers):
    return client.get(f"/api/chapters/{chapter_id}", headers=headers).json()


def test_manual_release_commits_the_draft_as_a_manual_version(client):
    flow, chapter = _setup(client)
    tech = login(client, "alpha-tech")
    lease, base = _draft(client, flow, chapter["id"], tech, "技术正文：草稿里写的新内容。")
    assert client.post(f"/api/chapters/{chapter['id']}/lock/release", headers=tech, json={"lease_token": lease}).status_code == 200
    after = _chapter(client, chapter["id"], tech)
    assert after["revision"] == base + 1 and after["content"] == "技术正文：草稿里写的新内容。" and not after.get("draft")
    versions = client.get(f"/api/chapters/{chapter['id']}/versions", headers=tech).json()["versions"]
    assert versions[-1]["edit_mode"] == "manual" and "自动提交（主动释放编辑权）" == versions[-1]["note"]


def test_takeover_commits_the_previous_holders_draft_and_tells_them(client):
    flow, chapter = _setup(client)
    tech = login(client, "alpha-tech")
    _, base = _draft(client, flow, chapter["id"], tech, "技术正文：被接管前保存的草稿。")
    taken = client.post(f"/api/chapters/{chapter['id']}/lock", headers=flow.headers, json={"takeover_reason": "统一修订"})
    assert taken.status_code == 200, taken.text
    after = _chapter(client, chapter["id"], flow.headers)
    assert after["revision"] == base + 1 and after["content"] == "技术正文：被接管前保存的草稿。"
    notice = next(n for n in client.get("/api/v1/notifications", headers=tech).json()["items"] if n["type"] == "lock_taken_over")
    assert f"已自动提交为 v{base + 1}" in notice["body"]


def test_expired_lock_commits_draft_when_someone_else_takes_the_chapter(client, clock):
    flow, chapter = _setup(client)
    tech = login(client, "alpha-tech")
    _, base = _draft(client, flow, chapter["id"], tech, "技术正文：超时前保存的草稿。")
    clock.value += 31 * 60  # 默认 30 分钟无心跳即释放
    acquired = client.post(f"/api/chapters/{chapter['id']}/lock", headers=flow.headers, json={})
    assert acquired.status_code == 200, acquired.text
    versions = client.get(f"/api/chapters/{chapter['id']}/versions", headers=flow.headers).json()["versions"]
    assert versions[-1]["revision"] == base + 1 and versions[-1]["note"] == "自动提交（编辑锁超时释放）"


def test_drafts_on_stale_sources_or_with_chat_residue_are_kept_not_committed(client):
    flow, chapter = _setup(client)
    tech = login(client, "alpha-tech")
    lease, base = _draft(client, flow, chapter["id"], tech, "技术正文：希望对你有帮助")
    client.post(f"/api/chapters/{chapter['id']}/lock/release", headers=tech, json={"lease_token": lease})
    after = _chapter(client, chapter["id"], tech)
    assert after["revision"] == base and after["draft"]["content"] == "技术正文：希望对你有帮助"
    # 来源变化后的草稿也不自动提交
    lease, base = _draft(client, flow, chapter["id"], tech, "技术正文：来源变化前写的草稿。", sequence=2)
    fact = flow.state()["facts"][0]
    flow.write("/facts/" + fact["id"], {"value": "另一个取值"}, "PATCH")
    client.post(f"/api/chapters/{chapter['id']}/lock/release", headers=tech, json={"lease_token": lease})
    assert _chapter(client, chapter["id"], tech)["revision"] == base


def test_lease_length_follows_company_setting(client, clock):
    flow, chapter = _setup(client)
    admin = login(client, "alpha-company-admin")
    resp = client.patch("/api/v1/companies/alpha/settings", headers=admin, json={
        "edit_lock_timeout_minutes": 20, "edit_lock_heartbeat_seconds": 60})
    assert resp.status_code == 200, resp.text
    lock = client.post(f"/api/chapters/{chapter['id']}/lock", headers=flow.headers, json={}).json()
    from icg.domain.domain import iso_time
    assert lock["expires_at"] == iso_time(clock.value + 20 * 60)
    clock.value += 60
    renewed = client.post(f"/api/chapters/{chapter['id']}/lock/renew", headers=flow.headers,
                          json={"lease_token": lock["lease_token"]})
    assert renewed.status_code == 200 and renewed.json()["expires_at"] == iso_time(clock.value + 20 * 60)
