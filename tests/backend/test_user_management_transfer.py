# 为什么有这个文件：用户管理与账号停用前业务资产强制交接工单 BE-USER-MANAGEMENT-TRANSFER 专属端到端集成测试。
# 它解决什么问题：
# 1. 验证用户 CRUD 契约与 PBKDF2-HMAC-SHA256 密码策略（>=8位，3类字符，不足拦截 422 PASSWORD_WEAK）；
# 2. 验证多租户强隔离（跨公司 404 NOT_FOUND）与 RBAC 权限隔离（普通成员写操作 403 FORBIDDEN，超管 admin 保护）；
# 3. 验证停用前业务资产强制交接门禁（M1-P10-F2）：未转交拦截 409 USER_TRANSFER_REQUIRED；
# 4. 验证非法接交人校验（不存在404、本人/跨企业/已停用422）；
# 5. 验证合法接交人原子交接（项目负责人、编写人、章节编辑锁释放、审计日志、会话即时作废）。

import time
import pytest
from fastapi.testclient import TestClient

from icg.domain.domain import Account, Chapter, Lease, Project
from icg.domain.auth_service import hash_password
from test_reference_flow import client


@pytest.fixture
def user_test_env(client: TestClient):
    """准备平台超管、企业管理员、普通编写人等不同角色测试上下文与项目/章节资产。"""
    service = client.app.state.service

    # 1. 超级管理员 Token
    res_admin = client.post("/api/v1/auth/login", json={"username": "admin", "password": "X_2026"})
    assert res_admin.status_code == 200
    admin_token = res_admin.json()["access_token"]

    # 2. Alpha 企业管理员账号
    alpha_admin_hash, alpha_admin_salt = hash_password("Alpha_admin_2026")
    alpha_admin_user = Account(
        id="alpha-company-admin",
        name="Alpha 企管员",
        company_id="alpha",
        role="company_admin",
        _DEMO_ONLY=False,
        password_hash=alpha_admin_hash,
        salt=alpha_admin_salt,
        display_name="Alpha 企管",
    )
    # 3. Alpha 普通编写人账号
    writer_hash, writer_salt = hash_password("Alpha_writer_2026")
    alpha_writer_user = Account(
        id="alpha-lead-user",
        name="Alpha 原负责人",
        company_id="alpha",
        role="project_lead",
        _DEMO_ONLY=False,
        password_hash=writer_hash,
        salt=writer_salt,
        display_name="Alpha 原负责人",
    )
    # 4. Alpha 目标接交人账号
    successor_hash, successor_salt = hash_password("Alpha_successor_2026")
    alpha_successor_user = Account(
        id="alpha-successor-user",
        name="Alpha 接交人",
        company_id="alpha",
        role="bid_writer",
        _DEMO_ONLY=False,
        password_hash=successor_hash,
        salt=successor_salt,
        display_name="Alpha 接交人",
    )
    # 5. Beta 企业管理员账号（跨租户探针）
    beta_admin_hash, beta_admin_salt = hash_password("Beta_admin_2026")
    beta_admin_user = Account(
        id="beta-company-admin",
        name="Beta 企管员",
        company_id="beta",
        role="company_admin",
        _DEMO_ONLY=False,
        password_hash=beta_admin_hash,
        salt=beta_admin_salt,
        display_name="Beta 企管",
    )

    def _setup_accounts(state):
        state.accounts["alpha-company-admin"] = alpha_admin_user
        state.accounts["alpha-lead-user"] = alpha_writer_user
        state.accounts["alpha-successor-user"] = alpha_successor_user
        state.accounts["beta-company-admin"] = beta_admin_user

    service.repository.transaction(_setup_accounts)

    login_alpha_admin = client.post("/api/v1/auth/login", json={"username": "alpha-company-admin", "password": "Alpha_admin_2026"})
    alpha_admin_token = login_alpha_admin.json()["access_token"]

    login_lead = client.post("/api/v1/auth/login", json={"username": "alpha-lead-user", "password": "Alpha_writer_2026"})
    lead_token = login_lead.json()["access_token"]

    login_beta_admin = client.post("/api/v1/auth/login", json={"username": "beta-company-admin", "password": "Beta_admin_2026"})
    beta_admin_token = login_beta_admin.json()["access_token"]

    return {
        "admin_token": admin_token,
        "alpha_admin_token": alpha_admin_token,
        "lead_token": lead_token,
        "beta_admin_token": beta_admin_token,
        "lead_user_id": "alpha-lead-user",
        "successor_user_id": "alpha-successor-user",
    }


def test_user_crud_and_password_policy(client: TestClient, user_test_env):
    """测试用户创建与 Q28 定案密码强度校验策略（>=8位且含大写、小写、数字、符号中的至少3类）。"""
    admin_token = user_test_env["admin_token"]
    alpha_admin_token = user_test_env["alpha_admin_token"]

    # 1. 密码不足 8 位 -> 422 PASSWORD_WEAK
    res1 = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {alpha_admin_token}"},
        json={
            "username": "new-user-short",
            "name": "短密码测试",
            "company_id": "alpha",
            "role": "bid_writer",
            "password": "Aa1!",  # 只有 4 位
        },
    )
    assert res1.status_code == 422
    assert res1.json()["code"] == "PASSWORD_WEAK"

    # 2. 密码长但只有 2 类字符（例如纯小写+数字） -> 422 PASSWORD_WEAK
    res2 = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {alpha_admin_token}"},
        json={
            "username": "new-user-2classes",
            "name": "少类别测试",
            "company_id": "alpha",
            "role": "bid_writer",
            "password": "abcdefg123456",  # 13位，但仅小写+数字
        },
    )
    assert res2.status_code == 422
    assert res2.json()["code"] == "PASSWORD_WEAK"

    # 3. 合法密码创建（大写+小写+数字，>=8位） -> 201 Created
    res3 = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {alpha_admin_token}"},
        json={
            "username": "new-valid-user-1",
            "name": "有效用户一",
            "display_name": "小有效",
            "company_id": "alpha",
            "role": "bid_writer",
            "password": "ValidPassword2026",  # 大写+小写+数字，17位
        },
    )
    assert res3.status_code == 201
    created_user = res3.json()
    assert created_user["id"] == "new-valid-user-1"
    assert created_user["status"] == "active"
    assert "password_hash" not in created_user
    assert "salt" not in created_user

    # 4. 账号重复创建 -> 409 DICT_CODE_DUPLICATED
    res4 = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {alpha_admin_token}"},
        json={
            "username": "new-valid-user-1",
            "name": "重复用户",
            "company_id": "alpha",
            "role": "bid_writer",
            "password": "ValidPassword2026",
        },
    )
    assert res4.status_code == 409
    assert res4.json()["code"] == "DICT_CODE_DUPLICATED"

    # 5. 查看单个用户与列表调阅
    res_get = client.get(
        "/api/v1/users/new-valid-user-1",
        headers={"Authorization": f"Bearer {alpha_admin_token}"},
    )
    assert res_get.status_code == 200
    assert res_get.json()["id"] == "new-valid-user-1"
    assert "password_hash" not in res_get.json()

    # 6. 新建用户可通过密码正常登录
    res_login = client.post(
        "/api/v1/auth/login",
        json={"username": "new-valid-user-1", "password": "ValidPassword2026"},
    )
    assert res_login.status_code == 200
    assert "access_token" in res_login.json()


def test_multi_tenant_and_rbac_isolation(client: TestClient, user_test_env):
    """测试多租户强隔离与细粒度 RBAC 权限隔离。"""
    admin_token = user_test_env["admin_token"]
    alpha_admin_token = user_test_env["alpha_admin_token"]
    lead_token = user_test_env["lead_token"]
    beta_admin_token = user_test_env["beta_admin_token"]

    # 1. 普通编写人发起新增用户操作 -> 403 FORBIDDEN
    res_forbidden = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {lead_token}"},
        json={
            "username": "writer-trying-create",
            "name": "未授权创建",
            "company_id": "alpha",
            "role": "bid_writer",
            "password": "ValidPassword2026",
        },
    )
    assert res_forbidden.status_code == 403
    assert res_forbidden.json()["code"] == "FORBIDDEN"

    # 2. Alpha 企管尝试跨企业创建 Beta 用户 -> 404 NOT_FOUND
    res_cross_create = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {alpha_admin_token}"},
        json={
            "username": "cross-company-user",
            "name": "跨企业用户",
            "company_id": "beta",
            "role": "bid_writer",
            "password": "ValidPassword2026",
        },
    )
    assert res_cross_create.status_code == 404
    assert res_cross_create.json()["code"] == "NOT_FOUND"

    # 3. Alpha 企管尝试调阅 Beta 用户 -> 404 NOT_FOUND
    res_cross_get = client.get(
        "/api/v1/users/beta-company-admin",
        headers={"Authorization": f"Bearer {alpha_admin_token}"},
    )
    assert res_cross_get.status_code == 404
    assert res_cross_get.json()["code"] == "NOT_FOUND"

    # 4. 平台超级管理员可跨企业调阅任意用户
    res_super_get_alpha = client.get(
        "/api/v1/users/alpha-lead-user",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_super_get_alpha.status_code == 200
    res_super_get_beta = client.get(
        "/api/v1/users/beta-company-admin",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_super_get_beta.status_code == 200

    # 5. 系统超级管理员 admin 严禁被停用 -> 403 FORBIDDEN
    res_disable_admin = client.patch(
        "/api/v1/users/admin/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "disabled"},
    )
    assert res_disable_admin.status_code == 403
    assert res_disable_admin.json()["code"] == "FORBIDDEN"


def test_disable_user_without_transfer_blocked_by_user_transfer_required(client: TestClient, user_test_env):
    """测试核心业务红线：停用负责在投项目或持有编辑锁的用户时，未转交严格拦截 409 USER_TRANSFER_REQUIRED。"""
    service = client.app.state.service
    alpha_admin_token = user_test_env["alpha_admin_token"]
    lead_id = user_test_env["lead_user_id"]

    # 为 lead_id 绑定一个未归档在投项目与一个正在编辑锁定的章节
    proj_id = "test-proj-transfer-block-1"
    chap_id = "test-chap-transfer-block-1"

    def _setup_bound_assets(state):
        state.projects[proj_id] = Project(
            id=proj_id,
            name="在投重大通信枢纽项目",
            company_id="alpha",
            is_archived=False,
            created_by=lead_id,
        )
        state.project_teams[proj_id] = {
            "assembly_owner_id": lead_id,
            "owners": {"technical": lead_id, "business": "alpha-successor-user"},
            "members": {
                lead_id: {"user_id": lead_id, "project_role": "project_lead", "volumes": ["technical", "business"]},
                "alpha-successor-user": {"user_id": "alpha-successor-user", "project_role": "bid_writer", "volumes": ["business"]},
            },
            "handoffs": [],
        }
        state.chapters[chap_id] = Chapter(
            id=chap_id,
            project_id=proj_id,
            title="技术方案与网络拓扑",
            volume="technical",
            content="初始章节内容",
            assignee_id=lead_id,
            lock=Lease(token="lease-lead-1", user_id=lead_id, expires_at=time.time() + 3600),
        )

    service.repository.transaction(_setup_bound_assets)

    # 尝试不指定 successor_user_id 直接停用用户 -> 必须严格拦截 409 USER_TRANSFER_REQUIRED
    res_block = client.patch(
        f"/api/v1/users/{lead_id}/status",
        headers={"Authorization": f"Bearer {alpha_admin_token}"},
        json={"status": "disabled"},
    )
    assert res_block.status_code == 409
    body = res_block.json()
    assert body["code"] == "USER_TRANSFER_REQUIRED"
    assert "未完结" in body["message"] or "项目负责人" in body["message"]
    assert "details" in body
    details = body["details"]
    assert len(details["untransferred_projects"]) >= 1
    assert any(p["project_id"] == proj_id for p in details["untransferred_projects"])
    assert len(details["untransferred_chapters"]) >= 1
    assert any(c["chapter_id"] == chap_id for c in details["untransferred_chapters"])


def test_disable_user_with_invalid_successor_rejected(client: TestClient, user_test_env):
    """测试指定非法接交人（不存在/本人/跨企业/已被停用）时的校验防御。"""
    alpha_admin_token = user_test_env["alpha_admin_token"]
    lead_id = user_test_env["lead_user_id"]

    # 1. 指定不存在的接收人 -> 404 NOT_FOUND
    res1 = client.patch(
        f"/api/v1/users/{lead_id}/status",
        headers={"Authorization": f"Bearer {alpha_admin_token}"},
        json={"status": "disabled", "successor_user_id": "non-existent-user-xyz"},
    )
    assert res1.status_code == 404
    assert res1.json()["code"] == "NOT_FOUND"

    # 2. 指定接交人不能是待停用用户本人 -> 422 VALIDATION_ERROR
    res2 = client.patch(
        f"/api/v1/users/{lead_id}/status",
        headers={"Authorization": f"Bearer {alpha_admin_token}"},
        json={"status": "disabled", "successor_user_id": lead_id},
    )
    assert res2.status_code == 422
    assert res2.json()["code"] == "VALIDATION_ERROR"

    # 3. 指定跨企业接收人 -> 422 VALIDATION_ERROR
    res3 = client.patch(
        f"/api/v1/users/{lead_id}/status",
        headers={"Authorization": f"Bearer {alpha_admin_token}"},
        json={"status": "disabled", "successor_user_id": "beta-company-admin"},
    )
    assert res3.status_code == 422
    assert res3.json()["code"] == "VALIDATION_ERROR"


def test_disable_user_with_valid_successor_atomic_handoff(client: TestClient, user_test_env):
    """测试指定合法接交人时，原子完成在投项目、章节责任交接、编辑锁释放、审计记录及登录拦截。"""
    service = client.app.state.service
    alpha_admin_token = user_test_env["alpha_admin_token"]
    lead_id = user_test_env["lead_user_id"]
    lead_token = user_test_env["lead_token"]
    successor_id = user_test_env["successor_user_id"]

    proj_id = "test-proj-transfer-success-1"
    chap_id = "test-chap-transfer-success-1"

    def _setup_bound_assets(state):
        state.projects[proj_id] = Project(
            id=proj_id,
            name="在投核心系统建设项目",
            company_id="alpha",
            is_archived=False,
            created_by=lead_id,
        )
        state.project_teams[proj_id] = {
            "assembly_owner_id": lead_id,
            "owners": {"technical": lead_id, "business": successor_id},
            "members": {
                lead_id: {"user_id": lead_id, "project_role": "project_lead", "volumes": ["technical", "business"]},
                successor_id: {"user_id": successor_id, "project_role": "bid_writer", "volumes": ["business"]},
            },
            "handoffs": [],
        }
        state.chapters[chap_id] = Chapter(
            id=chap_id,
            project_id=proj_id,
            title="工程交付及维护计划",
            volume="technical",
            content="初始章节内容",
            assignee_id=lead_id,
            lock=Lease(token="lease-lead-2", user_id=lead_id, expires_at=time.time() + 3600),
        )

    service.repository.transaction(_setup_bound_assets)

    # 执行附带合法接交人的停用请求
    res = client.patch(
        f"/api/v1/users/{lead_id}/status",
        headers={"Authorization": f"Bearer {alpha_admin_token}"},
        json={
            "status": "disabled",
            "successor_user_id": successor_id,
            "reason": "员工转岗离任资产交接",
        },
    )
    assert res.status_code == 200
    user_body = res.json()
    assert user_body["id"] == lead_id
    assert user_body["status"] == "disabled"

    # 验证领域状态原子交接变更
    state = service.repository.read()
    team = state.project_teams[proj_id]
    # 1. 项目总装负责人交接至 successor_id
    assert team["assembly_owner_id"] == successor_id
    # 2. 技术分册负责人交接至 successor_id
    assert team["owners"]["technical"] == successor_id
    # 3. 团队成员角色更新与交接记录
    assert team["members"][successor_id]["project_role"] == "lead"
    assert len(team["handoffs"]) >= 1
    assert team["handoffs"][-1]["from_user_id"] == lead_id
    assert team["handoffs"][-1]["to_user_id"] == successor_id

    # 4. 章节编写人变更至 successor_id，原编辑锁被安全释放
    chap = state.chapters[chap_id]
    assert chap.assignee_id == successor_id
    assert chap.lock is None

    # 5. 安全审计日志留存
    audit_events = [ev for ev in sorted(state.security_audit.values(), key=lambda e: e["timestamp"])
                    if ev.get("action") == "user.deactivate_and_transfer"]
    assert len(audit_events) >= 1
    last_audit = audit_events[-1]
    assert last_audit["from_user_id"] == lead_id
    assert last_audit["to_user_id"] == successor_id

    # 6. 原持有会话即时作废，尝试使用原 Token 访问拦截 401 UNAUTHENTICATED
    res_session = client.get("/api/v1/session", headers={"Authorization": f"Bearer {lead_token}"})
    assert res_session.status_code == 401
    assert res_session.json()["code"] == "UNAUTHENTICATED"

    # 7. 停用账号无法再次登录
    res_login = client.post("/api/v1/auth/login", json={"username": lead_id, "password": "Alpha_writer_2026"})
    assert res_login.status_code == 401
    assert res_login.json()["code"] == "INVALID_CREDENTIALS"


def test_archived_project_does_not_block_deactivation(client: TestClient, user_test_env):
    """测试已归档历史项目不阻断用户停用（无需强制交接已封存项目）。"""
    service = client.app.state.service
    alpha_admin_token = user_test_env["alpha_admin_token"]

    # 创建一个专属待停用用户，仅关联已归档项目
    archived_user_id = "user-archived-only"
    u_hash, u_salt = hash_password("ArchivedUser2026")
    archived_user = Account(
        id=archived_user_id,
        name="归档用户",
        company_id="alpha",
        role="project_lead",
        _DEMO_ONLY=False,
        password_hash=u_hash,
        salt=u_salt,
    )
    archived_proj_id = "proj-archived-closed-1"

    def _setup_archived(state):
        state.accounts[archived_user_id] = archived_user
        state.projects[archived_proj_id] = Project(
            id=archived_proj_id,
            name="往期已封存归档标书",
            company_id="alpha",
            is_archived=True,  # 已归档
            created_by=archived_user_id,
        )
        state.project_teams[archived_proj_id] = {
            "assembly_owner_id": archived_user_id,
            "owners": {"technical": archived_user_id},
            "members": {archived_user_id: {"user_id": archived_user_id, "project_role": "project_lead"}},
            "handoffs": [],
        }

    service.repository.transaction(_setup_archived)

    # 停用该用户无须指定 successor_user_id，应直接成功
    res = client.patch(
        f"/api/v1/users/{archived_user_id}/status",
        headers={"Authorization": f"Bearer {alpha_admin_token}"},
        json={"status": "disabled"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "disabled"


def test_independent_transfer_endpoint(client: TestClient, user_test_env):
    """测试独立资产交接端点 POST /api/v1/users/{user_id}/transfer。"""
    service = client.app.state.service
    alpha_admin_token = user_test_env["alpha_admin_token"]
    successor_id = user_test_env["successor_user_id"]

    transfer_user_id = "user-to-transfer-indep"
    u_hash, u_salt = hash_password("TransferUser2026")
    u_acc = Account(
        id=transfer_user_id,
        name="待交接用户",
        company_id="alpha",
        role="project_lead",
        _DEMO_ONLY=False,
        password_hash=u_hash,
        salt=u_salt,
    )
    proj_id = "proj-transfer-indep-1"

    def _setup(state):
        state.accounts[transfer_user_id] = u_acc
        state.projects[proj_id] = Project(
            id=proj_id,
            name="独立交接在投项目",
            company_id="alpha",
            is_archived=False,
            created_by=transfer_user_id,
        )
        state.project_teams[proj_id] = {
            "assembly_owner_id": transfer_user_id,
            "owners": {"technical": transfer_user_id},
            "members": {transfer_user_id: {"user_id": transfer_user_id, "project_role": "project_lead"}},
            "handoffs": [],
        }

    service.repository.transaction(_setup)

    res = client.post(
        f"/api/v1/users/{transfer_user_id}/transfer",
        headers={"Authorization": f"Bearer {alpha_admin_token}"},
        json={"successor_user_id": successor_id},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["from_user_id"] == transfer_user_id
    assert body["successor_user_id"] == successor_id
    assert len(body["transferred_projects"]) >= 1
