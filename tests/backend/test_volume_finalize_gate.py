# 为什么有这个文件：为 BE-VOLUME-FINALIZE-GATE 提供分册定稿状态机与安全门禁自动化测试套件。
# 它解决什么问题：
# 1. 验证仅当前公司项目负责人（project_lead）或公司管理员（company_admin）可定稿；
# 2. 验证编写人（bid_writer）触发定稿严格返回 403 FORBIDDEN；
# 3. 验证跨公司账号触发定稿严格返回 404 NOT_FOUND（强租户隔离）；
# 4. 验证前置门禁 1：存在未解锁章节（正在被排他锁定）或缺少正式正文时拦截 409 Conflict；
# 5. 验证前置门禁 2：存在未消解的 severity == "blocker" 缺陷（废标或关键星号条款未满足）时拦截 409 CHECK_BLOCKER_EXISTS；
# 6. 验证定稿成功后状态流转（is_finalized=True，finalized_by，finalized_at）与解锁（unlock）全生命周期闭环；
# 7. 验证在关演示/生产配置（ICG_ALLOW_DEMO_LOGIN=0 / ICG_ENV=production）与正式 8 角色 Token 下门禁严格生效。

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from icg_demo.domain import Account, Chapter, DemoService, Principal, iso_time
from icg_demo.main import create_app
from test_reference_flow import ProjectFlow, client, login


def test_volume_finalize_normal_by_project_lead(client):
    """验证项目负责人（project_lead / manager）正常触发分册定稿通过，记录状态与时间戳。"""
    flow = ProjectFlow(client).ready().cross_reviewed("technical")
    lead_headers = login(client, "alpha-manager")

    rev = flow.state()["revision"]
    resp = client.post(
        f"{flow.path}/volumes/technical/finalize",
        json={},
        headers={
            **lead_headers,
            "If-Match": str(rev),
            "Idempotency-Key": str(uuid4()),
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["volume_id"] == "technical"
    assert data["is_finalized"] is True
    assert data["finalized_by"] == "alpha-manager"
    assert data["finalized_at"] is not None
    assert data["revision"] > rev

    # 查询单分册状态
    status_resp = client.get(
        f"{flow.path}/volumes/technical",
        headers=lead_headers,
    )
    assert status_resp.status_code == 200
    st = status_resp.json()
    assert st["is_finalized"] is True
    assert st["finalized_by"] == "alpha-manager"


def test_volume_finalize_normal_by_company_admin(client):
    """验证公司管理员（company_admin）正常触发分册定稿通过。"""
    flow = ProjectFlow(client).ready().cross_reviewed("business")
    admin_headers = login(client, "alpha-company-admin")

    rev = flow.state()["revision"]
    resp = client.post(
        f"{flow.path}/volumes/business/finalize",
        json={},
        headers={
            **admin_headers,
            "If-Match": str(rev),
            "Idempotency-Key": str(uuid4()),
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["volume_id"] == "business"
    assert data["is_finalized"] is True
    assert data["finalized_by"] == "alpha-company-admin"
    assert data["finalized_at"] is not None

    # 查询分册列表状态
    list_resp = client.get(
        f"{flow.path}/volumes",
        headers=admin_headers,
    )
    assert list_resp.status_code == 200
    volumes = {v["volume_id"]: v for v in list_resp.json()["volumes"]}
    assert "technical" in volumes
    assert "business" in volumes
    assert volumes["business"]["is_finalized"] is True
    assert volumes["business"]["finalized_by"] == "alpha-company-admin"


def test_volume_finalize_blocked_for_writer_with_403(client):
    """验证编写人（bid_writer / editor）越权触发定稿被拦截，返回 403 FORBIDDEN。"""
    flow = ProjectFlow(client).ready()
    writer_headers = login(client, "alpha-editor")

    rev = flow.state()["revision"]
    resp = client.post(
        f"{flow.path}/volumes/technical/finalize",
        json={},
        headers={
            **writer_headers,
            "If-Match": str(rev),
            "Idempotency-Key": str(uuid4()),
        },
    )
    assert resp.status_code == 403
    err = resp.json()
    assert err["code"] == "FORBIDDEN"
    assert "traceId" in err


def test_volume_finalize_cross_tenant_isolation_with_404(client):
    """验证跨租户（访问其他公司项目）触发定稿被隔离，返回 404 NOT_FOUND。"""
    flow = ProjectFlow(client).ready()  # 项目属于 alpha 公司
    beta_headers = login(client, "beta-manager")  # 属于 beta 公司

    resp = client.post(
        f"{flow.path}/volumes/technical/finalize",
        json={},
        headers={
            **beta_headers,
            "If-Match": "1",
            "Idempotency-Key": str(uuid4()),
        },
    )
    assert resp.status_code == 404
    err = resp.json()
    assert err["code"] == "NOT_FOUND"
    assert "traceId" in err


def test_volume_finalize_invalid_volume_returns_404(client):
    """验证非法分册名称触发定稿返回 404 NOT_FOUND。"""
    flow = ProjectFlow(client).ready()
    lead_headers = login(client, "alpha-manager")

    resp = client.post(
        f"{flow.path}/volumes/nonexistent_volume/finalize",
        json={},
        headers={
            **lead_headers,
            "If-Match": "1",
            "Idempotency-Key": str(uuid4()),
        },
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


def test_volume_finalize_gate_blocks_when_chapter_is_locked(client):
    """前置门禁 1：验证分册存在处于排他锁定的章节时，定稿被拦截 409 LOCK_HELD。"""
    flow = ProjectFlow(client).ready().cross_reviewed("technical")
    lead_headers = login(client, "alpha-manager")

    # 获取技术分册的某个章节
    state = flow.state()
    tech_chapters = [c for c in state["chapters"] if c["volume"] == "technical"]
    assert len(tech_chapters) > 0
    target_chapter = tech_chapters[0]

    # 项目负责人获取该章节排他锁定
    lock_resp = client.post(
        f"/api/v1/chapters/{target_chapter['id']}/lock",
        json={"takeover_reason": "负责人正在核对正文"},
        headers={
            **lead_headers,
            "Idempotency-Key": str(uuid4()),
        },
    )
    assert lock_resp.status_code == 200
    assert "lease_token" in lock_resp.json()
    lease_token = lock_resp.json()["lease_token"]

    # 尝试定稿技术分册 -> 应被 409 LOCK_HELD 拦截
    rev = flow.state()["revision"]
    resp = client.post(
        f"{flow.path}/volumes/technical/finalize",
        json={},
        headers={
            **lead_headers,
            "If-Match": str(rev),
            "Idempotency-Key": str(uuid4()),
        },
    )
    assert resp.status_code == 409
    err = resp.json()
    assert err["code"] == "LOCK_HELD"
    assert "锁定" in err["message"]

    # 释放该章节锁定
    rel_resp = client.post(
        f"/api/v1/chapters/{target_chapter['id']}/lock/release",
        json={"lease_token": lease_token},
        headers={
            **lead_headers,
            "Idempotency-Key": str(uuid4()),
        },
    )
    assert rel_resp.status_code == 200

    # 释放锁定后重新尝试定稿 -> 预期放行 200
    rev2 = flow.state()["revision"]
    resp2 = client.post(
        f"{flow.path}/volumes/technical/finalize",
        json={},
        headers={
            **lead_headers,
            "If-Match": str(rev2),
            "Idempotency-Key": str(uuid4()),
        },
    )
    assert resp2.status_code == 200
    assert resp2.json()["is_finalized"] is True


def test_volume_finalize_gate_blocks_when_chapter_content_empty(client):
    """前置门禁 1：验证分册存在尚未提交正式正文的章节时，定稿被拦截 409 CHAPTER_CONTENT_EMPTY。"""
    flow = ProjectFlow(client).ready()
    lead_headers = login(client, "alpha-manager")

    state = flow.state()
    tech_chapters = [c for c in state["chapters"] if c["volume"] == "technical"]
    target_chapter = tech_chapters[0]

    # 清空该章节正文
    app_service = client.app.state.service
    repo = app_service.repository

    def clear_content(st):
        ch = st.chapters.get(target_chapter["id"])
        ch.content = "   "

    repo.transaction(clear_content)

    rev = flow.state()["revision"]
    resp = client.post(
        f"{flow.path}/volumes/technical/finalize",
        json={},
        headers={
            **lead_headers,
            "If-Match": str(rev),
            "Idempotency-Key": str(uuid4()),
        },
    )
    assert resp.status_code == 409
    err = resp.json()
    assert err["code"] == "CHAPTER_CONTENT_EMPTY"
    assert "缺少正式版本正文" in err["message"]


def test_volume_finalize_gate_blocks_when_blocker_defects_exist(client):
    """前置门禁 2：验证分册存在未消解的 blocker 缺陷时，定稿被拦截 409 CHECK_BLOCKER_EXISTS。"""
    flow = ProjectFlow(client).ready()
    lead_headers = login(client, "alpha-manager")

    # 制造技术分册废标条款未响应产生的 blocker
    state = flow.state()
    r0 = state["requirements"][0]
    flow.write(
        f"/requirements/{r0['id']}",
        {
            "text": "废标红线：核心数据库集群必须满足故障切换时间小于30秒，否则按否决投标处理。",
            "category": "disqualification",
            "status": "confirmed",
            "response": "",  # 空响应产生 blocker
            "reason": "废标门禁测试",
            "volume": "technical",
        },
        "PATCH",
    )

    # 运行检查
    check_res = flow.write("/checks", {"volume": "technical"})
    check = check_res["check"]
    assert any(i.get("severity") == "blocker" for i in check["issues"])

    # 尝试定稿技术分册 -> 应被 409 CHECK_BLOCKER_EXISTS 拦截
    rev = flow.state()["revision"]
    resp = client.post(
        f"{flow.path}/volumes/technical/finalize",
        json={"check_id": check["id"]},
        headers={
            **lead_headers,
            "If-Match": str(rev),
            "Idempotency-Key": str(uuid4()),
        },
    )
    assert resp.status_code == 409
    err = resp.json()
    assert err["code"] == "CHECK_BLOCKER_EXISTS"
    assert "blocker" in err["message"] or "阻断" in err["message"]

    # 消解 blocker：填写有效响应并确认状态
    flow.write(
        f"/requirements/{r0['id']}",
        {
            "response": "经专家团队复核，本公司采用全同步双活架构，完全满足故障切换时间小于30秒要求。",
            "status": "confirmed",
            "reason": "消减废标阻断",
        },
        "PATCH",
    )
    # 重新检查
    clean_check = flow.write("/checks", {"volume": "technical"})["check"]
    assert not any(i.get("severity") == "blocker" for i in clean_check["issues"]), clean_check["issues"]

    # 消解 blocker 后完成交叉复核再定稿 -> 预期放行 200
    flow.cross_reviewed("technical")
    rev2 = flow.state()["revision"]
    resp2 = client.post(
        f"{flow.path}/volumes/technical/finalize",
        json={"check_id": clean_check["id"]},
        headers={
            **lead_headers,
            "If-Match": str(rev2),
            "Idempotency-Key": str(uuid4()),
        },
    )
    assert resp2.status_code == 200
    assert resp2.json()["is_finalized"] is True


def test_volume_unlock_lifecycle_and_reason_requirement(client):
    """验证定稿后解锁（unlock）全生命周期：编写人拦截、必填原因与状态回退。"""
    flow = ProjectFlow(client).ready().cross_reviewed("technical")
    lead_headers = login(client, "alpha-manager")
    writer_headers = login(client, "alpha-editor")

    # 1. 先定稿技术分册
    rev = flow.state()["revision"]
    finalize_res = client.post(
        f"{flow.path}/volumes/technical/finalize",
        json={},
        headers={
            **lead_headers,
            "If-Match": str(rev),
            "Idempotency-Key": str(uuid4()),
        },
    )
    assert finalize_res.status_code == 200
    assert finalize_res.json()["is_finalized"] is True

    # 2. 编写人尝试解锁 -> 403 FORBIDDEN
    rev = flow.state()["revision"]
    resp_writer = client.post(
        f"{flow.path}/volumes/technical/unlock",
        json={"reason": "编写人想修改参数"},
        headers={
            **writer_headers,
            "If-Match": str(rev),
            "Idempotency-Key": str(uuid4()),
        },
    )
    assert resp_writer.status_code == 403
    assert resp_writer.json()["code"] == "FORBIDDEN"

    # 3. 项目经理未填原因尝试解锁 -> 422 VALIDATION_ERROR / REASON_REQUIRED
    resp_no_reason = client.post(
        f"{flow.path}/volumes/technical/unlock",
        json={"reason": "   "},
        headers={
            **lead_headers,
            "If-Match": str(rev),
            "Idempotency-Key": str(uuid4()),
        },
    )
    assert resp_no_reason.status_code in (422, 400)

    # 4. 项目经理合规填写原因解锁 -> 200 成功，is_finalized 流转为 False
    rev = flow.state()["revision"]
    resp_unlock = client.post(
        f"{flow.path}/volumes/technical/unlock",
        json={"reason": "招标文件澄清通知：更新数据库容灾切换性能指标。"},
        headers={
            **lead_headers,
            "If-Match": str(rev),
            "Idempotency-Key": str(uuid4()),
        },
    )
    assert resp_unlock.status_code == 200
    unlocked_data = resp_unlock.json()
    assert unlocked_data["is_finalized"] is False
    assert unlocked_data["unlocked_by"] == "alpha-manager"
    assert "澄清通知" in unlocked_data["unlock_reason"]
    assert unlocked_data["unlocked_at"] is not None

    # 查询状态确认已解锁；交叉复核随解锁作废
    st = client.get(f"{flow.path}/volumes/technical", headers=lead_headers).json()
    assert st["is_finalized"] is False
    assert st["unlock_reason"] is not None
    assert st["cross_review"]["status"] == "none"


def test_volume_finalize_in_non_demo_eight_roles_environment(monkeypatch):
    """验证在生产关演示环境（ICG_ALLOW_DEMO_LOGIN=0 / ICG_ENV=production）与正式 8 角色 Token 下门禁严格生效。"""
    monkeypatch.setenv("ICG_ALLOW_DEMO_LOGIN", "0")
    monkeypatch.setenv("ICG_ENV", "production")

    from icg_demo.adapters import MemoryRepository, seed_state

    state = seed_state()
    # 注册标准 8 角色
    roles = [
        ("lead-usr", "生产项目经理", "alpha", "project_lead"),
        ("writer-usr", "生产编写人", "alpha", "bid_writer"),
        ("admin-usr", "生产管理员", "alpha", "company_admin"),
        ("beta-lead-usr", "外部项目经理", "beta", "project_lead"),
    ]
    tokens = {}
    for uid, name, comp, role in roles:
        tok = f"prod-token-{uid}"
        state.accounts[uid] = Account(uid, name, comp, role)
        state.sessions[tok] = uid
        tokens[uid] = {"Authorization": f"Bearer {tok}"}

    repo = MemoryRepository(state)
    app = create_app(repository=repo)
    client = TestClient(app)

    # 1. 由 lead-usr 创建项目
    p_resp = client.post(
        "/api/v1/projects",
        json={"name": "生产正式分册定稿工程"},
        headers={**tokens["lead-usr"], "Idempotency-Key": str(uuid4())},
    )
    assert p_resp.status_code == 200
    pid = p_resp.json()["id"]

    # 配置团队与章节正文
    def init_project_data(st):
        st.project_teams[pid] = {
            "members": {
                "lead-usr": {"user_id": "lead-usr", "project_role": "lead", "volumes": ["technical", "business"]},
                "writer-usr": {"user_id": "writer-usr", "project_role": "writer", "volumes": ["technical", "business"]},
                "admin-usr": {"user_id": "admin-usr", "project_role": "lead", "volumes": ["technical", "business"]},
            },
            "owners": {"technical": "lead-usr", "business": "lead-usr"},
            "assembly_owner_id": "lead-usr",
            "handoffs": [],
        }
        for ch in st.chapters.values():
            if ch.project_id == pid:
                ch.content = "正式生产技术方案正文，满足全部设计指标。"

    repo.transaction(init_project_data)

    # 2. 跨租户 beta-lead-usr 触发定稿 -> 404
    resp_cross = client.post(
        f"/api/v1/projects/{pid}/volumes/technical/finalize",
        json={},
        headers={**tokens["beta-lead-usr"], "Idempotency-Key": str(uuid4())},
    )
    assert resp_cross.status_code == 404
    assert resp_cross.json()["code"] == "NOT_FOUND"

    # 3. 编写人 writer-usr 触发定稿 -> 403
    rev = client.get(f"/api/v1/projects/{pid}/workspace", headers=tokens["lead-usr"]).json()["revision"]
    resp_writer = client.post(
        f"/api/v1/projects/{pid}/volumes/technical/finalize",
        json={},
        headers={**tokens["writer-usr"], "If-Match": str(rev), "Idempotency-Key": str(uuid4())},
    )
    assert resp_writer.status_code == 403
    assert resp_writer.json()["code"] == "FORBIDDEN"

    def review(volume):
        for token, path, data in (("lead-usr", "cross-review", {"reviewer_id": "writer-usr"}),
                                  ("writer-usr", "cross-review/confirm", {"decision": "approved"})):
            current = client.get(f"/api/v1/projects/{pid}/workspace", headers=tokens["lead-usr"]).json()["revision"]
            done = client.post(f"/api/v1/projects/{pid}/volumes/{volume}/{path}", json=data,
                               headers={**tokens[token], "If-Match": str(current), "Idempotency-Key": str(uuid4())})
            assert done.status_code == 200, done.text

    # 4. 交叉复核后，项目负责人 lead-usr 触发定稿 -> 200
    review("technical")
    review("business")
    rev = client.get(f"/api/v1/projects/{pid}/workspace", headers=tokens["lead-usr"]).json()["revision"]
    resp_lead = client.post(
        f"/api/v1/projects/{pid}/volumes/technical/finalize",
        json={},
        headers={**tokens["lead-usr"], "If-Match": str(rev), "Idempotency-Key": str(uuid4())},
    )
    assert resp_lead.status_code == 200, resp_lead.text
    assert resp_lead.json()["is_finalized"] is True
    assert resp_lead.json()["finalized_by"] == "lead-usr"

    # 5. 公司管理员 admin-usr 触发商务分册定稿 -> 200
    rev = client.get(f"/api/v1/projects/{pid}/workspace", headers=tokens["lead-usr"]).json()["revision"]
    resp_admin = client.post(
        f"/api/v1/projects/{pid}/volumes/business/finalize",
        json={},
        headers={**tokens["admin-usr"], "If-Match": str(rev), "Idempotency-Key": str(uuid4())},
    )
    assert resp_admin.status_code == 200, resp_admin.text
    assert resp_admin.json()["is_finalized"] is True
    assert resp_admin.json()["finalized_by"] == "admin-usr"
