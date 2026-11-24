# 为什么有这个文件：验证站内提醒（PRD v1.8 §5.12.2 验收①～④；APP-M2-T029～T032）。
# 它解决什么问题：业务事件真的产生提醒；未读数与列表一致；同对象同类型未读期间合并；点开先标已读再核对对象与权限；
# 公司之间互相看不到；17 类都有跳转方式；没有站外渠道。

from datetime import date, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from icg.domain.notifications import TYPES, notify
from icg_demo.main import create_app
from test_reference_flow import ProjectFlow, client, login  # noqa: F401


def _list(client, account, **params):
    resp = client.get("/api/v1/notifications", headers=login(client, account), params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _take_over(client, flow, chapter_id, account="alpha-manager"):
    """alpha-tech 先拿锁，再由项目负责人填写理由接管。"""
    tech = login(client, "alpha-tech")
    first = client.post(f"/api/chapters/{chapter_id}/lock", headers=tech, json={})
    assert first.status_code == 200, first.text
    taken = client.post(f"/api/chapters/{chapter_id}/lock", headers=login(client, account),
                        json={"takeover_reason": "截止前统一修订"})
    assert taken.status_code == 200, taken.text


def test_lock_takeover_notifies_the_previous_editor_and_opening_jumps_to_the_chapter(client):
    flow = ProjectFlow(client).ready()
    chapter = next(c for c in flow.state()["chapters"] if c["volume"] == "technical")
    team = client.app.state.service.repository
    team.transaction(lambda st: st.project_teams[flow.id]["members"].__setitem__(
        "alpha-tech", {"user_id": "alpha-tech", "project_role": "writer", "volumes": ["technical"]}))
    team.transaction(lambda st: setattr(st.chapters[chapter["id"]], "assignee_id", "alpha-tech"))
    _take_over(client, flow, chapter["id"])
    data = _list(client, "alpha-tech")
    notice = next(n for n in data["items"] if n["type"] == "lock_taken_over")
    assert "编辑权已被接管" in notice["title"] and "截止前统一修订" in notice["body"] and notice["read"] is False
    assert data["unread"] == client.get("/api/v1/notifications/unread-count", headers=login(client, "alpha-tech")).json()["unread"]
    assert data["unread"] == len([n for n in data["items"] if not n["read"]])
    opened = client.post(f"/api/v1/notifications/{notice['id']}/open", headers=login(client, "alpha-tech")).json()
    assert opened["ok"] and opened["path"] == f"/projects/{flow.id}/editor/{chapter['id']}" and opened["notification"]["read"]
    # 别的公司看不到，也不能标已读
    assert all(n["id"] != notice["id"] for n in _list(client, "beta-manager")["items"])
    assert client.post(f"/api/v1/notifications/{notice['id']}/read", headers=login(client, "beta-manager"), json={"read": True}).status_code == 404


def test_same_object_and_type_merge_while_unread_and_mark_read_unread_all(client):
    service = client.app.state.service

    def send(state):
        for _ in range(3):
            notify(state, ["alpha-editor"], "parse_pending", "解析结果待处理", "有冲突", now="2026-10-29T08:00:00+00:00",
                   project_id="alpha-project", target_id="parse")
        notify(state, ["alpha-editor"], "job_failed", "导出失败", "原因", now="2026-10-29T09:00:00+00:00",
               project_id="alpha-project", target_id="e1")
    service.repository.transaction(send)
    data = _list(client, "alpha-editor")
    merged = next(n for n in data["items"] if n["type"] == "parse_pending")
    assert merged["count"] == 3 and len([n for n in data["items"] if n["type"] == "parse_pending"]) == 1
    assert data["items"][0]["type"] == "job_failed"  # 按时间倒序
    headers = login(client, "alpha-editor")
    assert client.post(f"/api/v1/notifications/{merged['id']}/read", headers=headers, json={"read": True}).json()["read"]
    assert _list(client, "alpha-editor", status="unread")["total"] == 1
    assert client.post(f"/api/v1/notifications/{merged['id']}/read", headers=headers, json={"read": False}).json()["read"] is False
    # 已读后再发生则新建一条，不再合并到已读的那条
    assert client.post("/api/v1/notifications/read-all", headers=headers).json()["updated"] == 2
    service.repository.transaction(lambda st: notify(st, ["alpha-editor"], "parse_pending", "解析结果待处理", "又有冲突",
                                                     now="2026-10-29T10:00:00+00:00", project_id="alpha-project", target_id="parse"))
    assert _list(client, "alpha-editor", type="parse_pending")["total"] == 2
    assert _list(client, "alpha-editor", project_id="none")["total"] == 0


def test_open_reports_missing_object_or_lost_access_but_still_marks_read(client):
    service = client.app.state.service
    service.repository.transaction(lambda st: notify(st, ["alpha-editor"], "draft_expired", "草稿已过期", "x",
                                                     now="2026-10-29T08:00:00+00:00", project_id="alpha-project", target_id="no-such-chapter"))
    notice = _list(client, "alpha-editor")["items"][0]
    opened = client.post(f"/api/v1/notifications/{notice['id']}/open", headers=login(client, "alpha-editor")).json()
    assert opened["ok"] is False and opened["message"] == "对象已不存在或你没有查看权限" and opened["notification"]["read"]
    service.repository.transaction(lambda st: notify(st, ["alpha-outsider-manager"], "parse_pending", "解析结果待处理", "x",
                                                     now="2026-10-29T08:00:00+00:00", project_id="alpha-project", target_id="parse"))
    other = _list(client, "alpha-outsider-manager")["items"][0]
    lost = client.post(f"/api/v1/notifications/{other['id']}/open", headers=login(client, "alpha-outsider-manager")).json()
    assert lost["ok"] is False  # 不是项目成员：跳转时再次核对权限


def test_business_events_produce_notifications(client):
    flow = ProjectFlow(client).ready()
    state = flow.state()
    tech = next(c for c in state["chapters"] if c["volume"] == "technical")
    # 交叉复核：指定复核人后提醒复核人
    flow.cross_reviewed("technical")
    assert any(n["type"] == "cross_review" for n in _list(client, "alpha-editor")["items"])
    # 草稿过期：编写人有草稿，负责人提交了新版本
    repo = client.app.state.service.repository
    lease = client.post(f"/api/chapters/{tech['id']}/lock", headers=flow.headers, json={}).json()["lease_token"]
    from icg.domain.domain import Draft
    repo.transaction(lambda st: st.chapters[tech["id"]].drafts.__setitem__("alpha-editor", Draft(1, "旧草稿", tech["revision"], None)))
    current = next(c for c in flow.state()["chapters"] if c["id"] == tech["id"])
    committed = client.post(f"/api/chapters/{tech['id']}/versions", headers=flow.headers, json={
        "lease_token": lease, "base_revision": current["revision"], "content": current["content"] + "补一句。",
        "input_fingerprint": flow.state()["input_fingerprint"], "idempotency_key": str(uuid4())})
    assert committed.status_code == 200, committed.text
    expired = next(n for n in _list(client, "alpha-editor")["items"] if n["type"] == "draft_expired")
    assert "草稿已过期" in expired["title"] and expired["target_id"] == tech["id"]


def test_library_expiry_sweep_notifies_admins_once_a_day(client):
    soon = (date.today() + timedelta(days=10)).isoformat()
    later = (date.today() + timedelta(days=90)).isoformat()

    def seed(state):
        state.library["lib-soon"] = {"id": "lib-soon", "company_id": "alpha", "name": "ISO9001 证书", "type": "qualification",
                                     "status": "confirmed", "valid_until": soon, "content": "", "revision": 1}
        state.library["lib-later"] = {"id": "lib-later", "company_id": "alpha", "name": "远期证书", "type": "qualification",
                                      "status": "confirmed", "valid_until": later, "content": "", "revision": 1}
    client.app.state.service.repository.transaction(seed)
    items = _list(client, "alpha-company-admin")["items"]
    expiring = [n for n in items if n["type"] == "library_expiring"]
    assert [n["target_id"] for n in expiring] == ["lib-soon"] and "10 天到期" in expiring[0]["body"]
    assert any(n["type"] == "library_expiring" for n in _list(client, "alpha-data-admin")["items"])
    assert not any(n["type"] == "library_expiring" for n in _list(client, "alpha-editor")["items"])
    _list(client, "alpha-company-admin")  # 当天再次读取不重复发送
    assert len([n for n in _list(client, "alpha-company-admin")["items"] if n["type"] == "library_expiring"]) == 1
    opened = client.post(f"/api/v1/notifications/{expiring[0]['id']}/open", headers=login(client, "alpha-company-admin")).json()
    assert opened["path"] == "/library"
    # 当天新增的资料也会提醒；已读过的同一资料同一到期日不再重复提醒
    client.app.state.service.repository.transaction(lambda st: st.library.__setitem__("lib-new", {
        "id": "lib-new", "company_id": "alpha", "name": "新证书", "type": "qualification", "status": "confirmed",
        "valid_until": soon, "content": "", "revision": 1}))
    targets = [n["target_id"] for n in _list(client, "alpha-company-admin")["items"] if n["type"] == "library_expiring"]
    assert sorted(targets) == ["lib-new", "lib-soon"]


def test_all_seventeen_types_have_a_target_and_there_are_no_channel_settings(client):
    assert len(TYPES) == 17
    assert all(mode.split(":")[0] in {"project_tab", "chapter", "library", "jobs", "workbench", "platform"} for _, mode in TYPES.values())
    listed = _list(client, "alpha-manager")
    assert {t["value"] for t in listed["types"]} == set(TYPES)
    spec = client.get("/openapi.json").json()
    paths = [p for p in spec["paths"] if p.startswith("/api/v1/notifications")]
    assert paths and not any(word in str(spec["paths"][p]) for p in paths for word in ("email", "sms", "邮件", "短信"))
    session = client.get("/api/v1/session", headers=login(client, "alpha-editor"))
    assert session.status_code == 200, session.text
    assert any(item["route_id"] == "notifications" for item in session.json()["navigation"])
