# 为什么有这个文件：前后端契约联调工单 INT-USER-SECURITY-OPS-GLUE 专属端到端集成测试。
# 它解决什么问题：
# 1. 验证重置密码契约全链路：弱密码 422 PASSWORD_WEAK 拦截、原 Token 立即作废（401 UNAUTHENTICATED）、新密码登录成功；
# 2. 验证连续登录失败锁定与管理员解锁契约：连续 5 次输错密码流转为锁定状态，第 6 次即便正确也拦截 423 ACCOUNT_LOCKED；
#    管理员调用 unlock 端点后状态恢复为 active，用户可成功登录；
# 3. 验证 8 大角色调整流转与越权安全防线：超管 admin 降权拦截 403 SUPER_ADMIN_PROTECTED、企管自降权拦截 403 CANNOT_DEMOTE_SELF；
# 4. 验证多租户强隔离（跨公司 404 NOT_FOUND）与 RBAC 权限隔离（普通成员写操作 403 FORBIDDEN）。

import pytest
from fastapi.testclient import TestClient

from icg.domain.domain import Account
from icg.domain.auth_service import hash_password
from test_reference_flow import client


@pytest.fixture
def test_users_context(client: TestClient):
    """准备平台超管、企业管理员及普通编写人账号与认证环境。"""
    service = client.app.state.service

    # 1. 超级管理员登录 Token
    super_admin_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "X_2026"})
    assert super_admin_res.status_code == 200
    super_admin_token = super_admin_res.json()["access_token"]

    # 2. Alpha 企业管理员账号
    alpha_pass_hash, alpha_salt = hash_password("Alpha_admin_2026")
    alpha_admin_user = Account(
        id="glue-alpha-admin",
        name="Alpha 企管员",
        company_id="alpha",
        role="company_admin",
        _DEMO_ONLY=False,
        password_hash=alpha_pass_hash,
        salt=alpha_salt,
        display_name="Alpha 企管",
        status="active",
    )
    # 3. Alpha 测试普通用户
    writer_pass_hash, writer_salt = hash_password("Writer_pass_2026")
    alpha_writer_user = Account(
        id="glue-alpha-writer",
        name="Alpha 编写人",
        company_id="alpha",
        role="bid_writer",
        _DEMO_ONLY=False,
        password_hash=writer_pass_hash,
        salt=writer_salt,
        display_name="Alpha 编写人",
        status="active",
        failed_login_attempts=0,
        is_locked=False,
    )
    # 4. Beta 企业管理员账号
    beta_pass_hash, beta_salt = hash_password("Beta_admin_2026")
    beta_admin_user = Account(
        id="glue-beta-admin",
        name="Beta 企管员",
        company_id="beta",
        role="company_admin",
        _DEMO_ONLY=False,
        password_hash=beta_pass_hash,
        salt=beta_salt,
        display_name="Beta 企管",
        status="active",
    )

    def _seed(state):
        state.accounts["glue-alpha-admin"] = alpha_admin_user
        state.accounts["glue-alpha-writer"] = alpha_writer_user
        state.accounts["glue-beta-admin"] = beta_admin_user

    service.repository.transaction(_seed)

    alpha_admin_login = client.post("/api/v1/auth/login", json={"username": "glue-alpha-admin", "password": "Alpha_admin_2026"})
    assert alpha_admin_login.status_code == 200
    alpha_admin_token = alpha_admin_login.json()["access_token"]

    writer_login = client.post("/api/v1/auth/login", json={"username": "glue-alpha-writer", "password": "Writer_pass_2026"})
    assert writer_login.status_code == 200
    writer_token = writer_login.json()["access_token"]

    beta_admin_login = client.post("/api/v1/auth/login", json={"username": "glue-beta-admin", "password": "Beta_admin_2026"})
    assert beta_admin_login.status_code == 200
    beta_admin_token = beta_admin_login.json()["access_token"]

    return {
        "super_admin": super_admin_token,
        "alpha_admin": alpha_admin_token,
        "writer": writer_token,
        "beta_admin": beta_admin_token,
    }


def test_unauthenticated_security_ops_blocked_401(client: TestClient):
    """验证未提供认证凭据访问安全运维接口一律拦截 401 UNAUTHENTICATED。"""
    res_reset = client.post("/api/v1/users/glue-alpha-writer/reset-password", json={"new_password": "NewPassword123!"})
    assert res_reset.status_code == 401
    assert res_reset.json()["code"] == "UNAUTHENTICATED"

    res_unlock = client.post("/api/v1/users/glue-alpha-writer/unlock")
    assert res_unlock.status_code == 401
    assert res_unlock.json()["code"] == "UNAUTHENTICATED"

    res_role = client.patch("/api/v1/users/glue-alpha-writer/role", json={"role": "auditor"})
    assert res_role.status_code == 401
    assert res_role.json()["code"] == "UNAUTHENTICATED"


def test_reset_password_weak_password_rejected_422(client: TestClient, test_users_context):
    """验证重置密码时若新密码不符合 Q28 强度策略（<8位或<3类字符）严格拦截 422 PASSWORD_WEAK。"""
    headers = {"Authorization": f"Bearer {test_users_context['alpha_admin']}"}

    # 1. 长度不足 8 位
    res_short = client.post(
        "/api/v1/users/glue-alpha-writer/reset-password",
        headers=headers,
        json={"new_password": "Ab1!"},
    )
    assert res_short.status_code == 422, res_short.text
    err = res_short.json()
    assert err["code"] == "PASSWORD_WEAK"
    assert "密码长度" in err["message"]
    assert err["details"]["field"] == "new_password"

    # 2. 字符种类不足 3 类（仅小写字母）
    res_few_classes = client.post(
        "/api/v1/users/glue-alpha-writer/reset-password",
        headers=headers,
        json={"new_password": "alllowercasewords"},
    )
    assert res_few_classes.status_code == 422, res_few_classes.text
    err_classes = res_few_classes.json()
    assert err_classes["code"] == "PASSWORD_WEAK"
    assert "包含" in err_classes["message"]


def test_reset_password_invalidates_existing_tokens_and_allows_login(client: TestClient, test_users_context):
    """验证管理员重置密码全链路：旧 Token 即时作废报 401，用户原密码失效，新密码登录成功。"""
    admin_headers = {"Authorization": f"Bearer {test_users_context['alpha_admin']}"}
    old_writer_token = test_users_context["writer"]

    # 1. 验证原 Token 在重置前可用
    res_before = client.get("/api/v1/users/glue-alpha-writer", headers={"Authorization": f"Bearer {old_writer_token}"})
    assert res_before.status_code == 200

    # 2. 管理员执行重置密码
    res_reset = client.post(
        "/api/v1/users/glue-alpha-writer/reset-password",
        headers=admin_headers,
        json={"new_password": "New_SuperPass_2026!"},
    )
    assert res_reset.status_code == 200, res_reset.text
    data = res_reset.json()
    assert data["success"] is True
    assert data["user_id"] == "glue-alpha-writer"

    # 3. 核心红线验证：原 Token 即时失效拦截 401 UNAUTHENTICATED
    res_after = client.get("/api/v1/users/glue-alpha-writer", headers={"Authorization": f"Bearer {old_writer_token}"})
    assert res_after.status_code == 401, "旧 Token 必须被作废"
    assert res_after.json()["code"] == "UNAUTHENTICATED"

    # 4. 原旧密码登录失败
    res_old_login = client.post("/api/v1/auth/login", json={"username": "glue-alpha-writer", "password": "Writer_pass_2026"})
    assert res_old_login.status_code == 401
    assert res_old_login.json()["code"] == "INVALID_CREDENTIALS"

    # 5. 使用新密码登录成功并获取新有效 Token
    res_new_login = client.post("/api/v1/auth/login", json={"username": "glue-alpha-writer", "password": "New_SuperPass_2026!"})
    assert res_new_login.status_code == 200, res_new_login.text
    new_token = res_new_login.json()["access_token"]
    assert new_token != old_writer_token

    assert res_new_login.json()["must_change_password"] is True

    # 6. 被重置后须先改密：业务接口拒绝（APP-M2-T260），改密后才能调阅
    new_headers = {"Authorization": f"Bearer {new_token}"}
    blocked = client.get("/api/v1/users/glue-alpha-writer", headers=new_headers)
    assert blocked.status_code == 403 and blocked.json()["code"] == "PASSWORD_CHANGE_REQUIRED"
    changed = client.post("/api/v1/auth/password", headers=new_headers,
                          json={"old_password": "New_SuperPass_2026!", "new_password": "Own_Choice_2026#"})
    assert changed.status_code == 200, changed.text
    res_new_access = client.get("/api/v1/users/glue-alpha-writer", headers=new_headers)
    assert res_new_access.status_code == 200


def test_login_failure_lockout_423_and_admin_unlock_lifecycle(client: TestClient, test_users_context):
    """验证连续 5 次输错密码自动流转锁定（423 ACCOUNT_LOCKED），管理员调用 unlock 解锁后恢复正常登录。"""
    admin_headers = {"Authorization": f"Bearer {test_users_context['alpha_admin']}"}
    target_username = "glue-alpha-writer"
    correct_password = "Writer_pass_2026"

    # 1. 前 4 次输错密码：返回 401 INVALID_CREDENTIALS，提示剩余重试机会
    for i in range(1, 5):
        res_fail = client.post("/api/v1/auth/login", json={"username": target_username, "password": f"WrongPwd_{i}"})
        assert res_fail.status_code == 401, f"第 {i} 次失败应返回 401"
        assert res_fail.json()["code"] == "INVALID_CREDENTIALS"

    # 2. 第 5 次输错密码：触发上限，账号流转为锁定状态，返回 423 ACCOUNT_LOCKED
    res_fail_5 = client.post("/api/v1/auth/login", json={"username": target_username, "password": "WrongPwd_5"})
    assert res_fail_5.status_code == 423, res_fail_5.text
    assert res_fail_5.json()["code"] == "ACCOUNT_LOCKED"
    assert "锁定" in res_fail_5.json()["message"]

    # 3. 账号锁定后，第 6 次即便输入正确密码，也必须严格拦截 423 ACCOUNT_LOCKED
    res_correct_while_locked = client.post("/api/v1/auth/login", json={"username": target_username, "password": correct_password})
    assert res_correct_while_locked.status_code == 423, "锁定状态下输入正确密码也必须阻断"
    assert res_correct_while_locked.json()["code"] == "ACCOUNT_LOCKED"

    # 4. 管理员调用解锁接口 POST /api/v1/users/{id}/unlock
    res_unlock = client.post(f"/api/v1/users/{target_username}/unlock", headers=admin_headers)
    assert res_unlock.status_code == 200, res_unlock.text
    unlock_data = res_unlock.json()
    assert unlock_data["success"] is True
    assert unlock_data["is_locked"] is False
    assert unlock_data["failed_login_attempts"] == 0

    # 5. 解锁后，再次输入原正确密码，登录成功（200 OK）
    res_login_after_unlock = client.post("/api/v1/auth/login", json={"username": target_username, "password": correct_password})
    assert res_login_after_unlock.status_code == 200, res_login_after_unlock.text
    assert "access_token" in res_login_after_unlock.json()


def test_role_assignment_and_rbac_protection_matrix(client: TestClient, test_users_context):
    """验证角色调整流转、超管保护门禁（403 SUPER_ADMIN_PROTECTED）与企管防自降权门禁（403 CANNOT_DEMOTE_SELF）。"""
    admin_headers = {"Authorization": f"Bearer {test_users_context['alpha_admin']}"}
    super_admin_headers = {"Authorization": f"Bearer {test_users_context['super_admin']}"}

    # 1. 尝试修改系统超管 admin 角色：严格拦截 403 SUPER_ADMIN_PROTECTED
    res_demote_admin = client.patch(
        "/api/v1/users/admin/role",
        headers=super_admin_headers,
        json={"role": "company_admin"},
    )
    assert res_demote_admin.status_code == 403, res_demote_admin.text
    assert res_demote_admin.json()["code"] == "SUPER_ADMIN_PROTECTED"

    # 2. 企管尝试对自己进行降权操作：严格拦截 403 CANNOT_DEMOTE_SELF
    res_demote_self = client.patch(
        "/api/v1/users/glue-alpha-admin/role",
        headers=admin_headers,
        json={"role": "bid_writer"},
    )
    assert res_demote_self.status_code == 403, res_demote_self.text
    assert res_demote_self.json()["code"] == "CANNOT_DEMOTE_SELF"

    # 3. 企管成功调整同企业普通用户角色为 8 大标准角色的 auditor, data_admin, viewer
    for target_role in ("auditor", "data_admin", "viewer", "project_lead"):
        res_role = client.patch(
            "/api/v1/users/glue-alpha-writer/role",
            headers=admin_headers,
            json={"role": target_role},
        )
        assert res_role.status_code == 200, res_role.text
        assert res_role.json()["role"] == target_role

    # 4. 非法系统角色代码：拦截 422 VALIDATION_ERROR
    res_invalid_role = client.patch(
        "/api/v1/users/glue-alpha-writer/role",
        headers=admin_headers,
        json={"role": "invalid_cyber_hacker"},
    )
    assert res_invalid_role.status_code == 422
    assert res_invalid_role.json()["code"] == "VALIDATION_ERROR"


def test_tenant_and_privilege_isolation_cross_operations(client: TestClient, test_users_context):
    """验证多租户强隔离（跨租户 404 NOT_FOUND）与 RBAC 权限隔离（普通成员写操作 403 FORBIDDEN）。"""
    alpha_admin_headers = {"Authorization": f"Bearer {test_users_context['alpha_admin']}"}
    writer_headers = {"Authorization": f"Bearer {test_users_context['writer']}"}

    # 1. 跨企业重置密码：Alpha 企管重置 Beta 企管，返回 404 NOT_FOUND 防嗅探
    res_cross_reset = client.post(
        "/api/v1/users/glue-beta-admin/reset-password",
        headers=alpha_admin_headers,
        json={"new_password": "NewBetaPass123!"},
    )
    assert res_cross_reset.status_code == 404, res_cross_reset.text
    assert res_cross_reset.json()["code"] == "NOT_FOUND"

    # 2. 跨企业解锁账号：Alpha 企管解锁 Beta 账号，返回 404 NOT_FOUND
    res_cross_unlock = client.post(
        "/api/v1/users/glue-beta-admin/unlock",
        headers=alpha_admin_headers,
    )
    assert res_cross_unlock.status_code == 404, res_cross_unlock.text
    assert res_cross_unlock.json()["code"] == "NOT_FOUND"

    # 3. 跨企业角色变更：Alpha 企管修改 Beta 账号角色，返回 404 NOT_FOUND
    res_cross_role = client.patch(
        "/api/v1/users/glue-beta-admin/role",
        headers=alpha_admin_headers,
        json={"role": "viewer"},
    )
    assert res_cross_role.status_code == 404, res_cross_role.text
    assert res_cross_role.json()["code"] == "NOT_FOUND"

    # 4. 普通编写人尝试执行重置密码：拦截 403 FORBIDDEN
    res_writer_reset = client.post(
        "/api/v1/users/glue-alpha-admin/reset-password",
        headers=writer_headers,
        json={"new_password": "WriterHackPass123!"},
    )
    assert res_writer_reset.status_code == 403
    assert res_writer_reset.json()["code"] == "FORBIDDEN"

    # 5. 普通编写人尝试执行账号解锁：拦截 403 FORBIDDEN
    res_writer_unlock = client.post(
        "/api/v1/users/glue-alpha-admin/unlock",
        headers=writer_headers,
    )
    assert res_writer_unlock.status_code == 403
    assert res_writer_unlock.json()["code"] == "FORBIDDEN"

    # 6. 普通编写人尝试执行角色变更：拦截 403 FORBIDDEN
    res_writer_role = client.patch(
        "/api/v1/users/glue-alpha-admin/role",
        headers=writer_headers,
        json={"role": "viewer"},
    )
    assert res_writer_role.status_code == 403
    assert res_writer_role.json()["code"] == "FORBIDDEN"
