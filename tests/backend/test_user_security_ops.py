# 为什么有这个文件：后端核心安全工单 BE-USER-SECURITY-OPS 专属端到端集成测试。
# 它解决什么问题：
# 1. 验证密码强制重置与 Q28 密码策略（>=8位，3类字符，不足拦截 422 PASSWORD_WEAK）及活跃会话即时作废；
# 2. 验证账号连续登录失败自动锁定门限（默认5次触发 423 ACCOUNT_LOCKED）与管理员一键解锁端点；
# 3. 验证角色调配端点、系统超管保护（403 SUPER_ADMIN_PROTECTED）与管理员防自降权门禁（403 CANNOT_DEMOTE_SELF）；
# 4. 验证多租户强隔离（跨公司 404 NOT_FOUND）与 RBAC 权限隔离（普通成员写操作 403 FORBIDDEN）。

import pytest
from fastapi.testclient import TestClient

from icg.domain.domain import Account
from icg.domain.auth_service import hash_password
from test_reference_flow import client


@pytest.fixture
def sec_ops_env(client: TestClient):
    """为角色调配、密码重置与锁定解锁准备多角色与多租户测试上下文。"""
    service = client.app.state.service

    # 1. 超级管理员 Token
    res_super = client.post("/api/v1/auth/login", json={"username": "admin", "password": "X_2026"})
    assert res_super.status_code == 200
    admin_token = res_super.json()["access_token"]

    # 2. Alpha 企管账号与 Token
    alpha_adm_hash, alpha_adm_salt = hash_password("Alpha_admin_2026")
    alpha_adm = Account(
        id="alpha-security-admin",
        name="Alpha 安全管理员",
        company_id="alpha",
        role="company_admin",
        _DEMO_ONLY=False,
        password_hash=alpha_adm_hash,
        salt=alpha_adm_salt,
        display_name="Alpha 安全管理员",
    )

    # 3. Alpha 普通待维护用户
    target_hash, target_salt = hash_password("Target_user_2026")
    alpha_target = Account(
        id="alpha-target-user",
        name="Alpha 目标测试用户",
        company_id="alpha",
        role="bid_writer",
        _DEMO_ONLY=False,
        password_hash=target_hash,
        salt=target_salt,
        display_name="Alpha 目标测试用户",
    )

    # 4. Alpha 普通成员（未锁定，用于测试越权拦截）
    mem_hash, mem_salt = hash_password("Member_pass_2026")
    alpha_mem = Account(
        id="alpha-regular-member",
        name="Alpha 普通成员",
        company_id="alpha",
        role="bid_writer",
        _DEMO_ONLY=False,
        password_hash=mem_hash,
        salt=mem_salt,
        display_name="Alpha 普通成员",
    )

    # 5. Beta 企管账号（跨企业隔离探针）
    beta_adm_hash, beta_adm_salt = hash_password("Beta_admin_2026")
    beta_adm = Account(
        id="beta-security-admin",
        name="Beta 安全管理员",
        company_id="beta",
        role="company_admin",
        _DEMO_ONLY=False,
        password_hash=beta_adm_hash,
        salt=beta_adm_salt,
        display_name="Beta 安全管理员",
    )

    def _setup(st):
        st.accounts["alpha-security-admin"] = alpha_adm
        st.accounts["alpha-target-user"] = alpha_target
        st.accounts["alpha-regular-member"] = alpha_mem
        st.accounts["beta-security-admin"] = beta_adm

    service.repository.transaction(_setup)

    login_alpha = client.post("/api/v1/auth/login", json={"username": "alpha-security-admin", "password": "Alpha_admin_2026"})
    alpha_adm_token = login_alpha.json()["access_token"]

    login_target = client.post("/api/v1/auth/login", json={"username": "alpha-target-user", "password": "Target_user_2026"})
    target_token = login_target.json()["access_token"]

    login_mem = client.post("/api/v1/auth/login", json={"username": "alpha-regular-member", "password": "Member_pass_2026"})
    member_token = login_mem.json()["access_token"]

    login_beta = client.post("/api/v1/auth/login", json={"username": "beta-security-admin", "password": "Beta_admin_2026"})
    beta_adm_token = login_beta.json()["access_token"]

    return {
        "admin_token": admin_token,
        "alpha_adm_token": alpha_adm_token,
        "target_token": target_token,
        "member_token": member_token,
        "beta_adm_token": beta_adm_token,
        "target_user_id": "alpha-target-user",
        "alpha_adm_id": "alpha-security-admin",
    }


def test_password_reset_and_policy_enforcement(client: TestClient, sec_ops_env):
    """测试管理员重置密码功能：Q28密码强度校验、会话作废与新密码登录。"""
    alpha_adm_token = sec_ops_env["alpha_adm_token"]
    target_token = sec_ops_env["target_token"]
    target_id = sec_ops_env["target_user_id"]
    beta_adm_token = sec_ops_env["beta_adm_token"]

    # 1. 弱密码（不足8位）重置拦截 -> 422 PASSWORD_WEAK
    res_weak1 = client.post(
        f"/api/v1/users/{target_id}/reset-password",
        headers={"Authorization": f"Bearer {alpha_adm_token}"},
        json={"new_password": "Short1!"},
    )
    assert res_weak1.status_code == 422
    assert res_weak1.json()["code"] == "PASSWORD_WEAK"

    # 2. 弱密码（长但类别不足3类，纯字母数字无大写） -> 422 PASSWORD_WEAK
    res_weak2 = client.post(
        f"/api/v1/users/{target_id}/reset-password",
        headers={"Authorization": f"Bearer {alpha_adm_token}"},
        json={"new_password": "onlylowanddigits12345"},
    )
    assert res_weak2.status_code == 422
    assert res_weak2.json()["code"] == "PASSWORD_WEAK"

    # 3. 普通角色尝试重置密码 -> 403 FORBIDDEN
    res_forbid = client.post(
        f"/api/v1/users/{target_id}/reset-password",
        headers={"Authorization": f"Bearer {target_token}"},
        json={"new_password": "NewStrongPass_2026!"},
    )
    assert res_forbid.status_code == 403
    assert res_forbid.json()["code"] == "FORBIDDEN"

    # 4. 跨企业管理员尝试重置 -> 404 NOT_FOUND
    res_cross = client.post(
        f"/api/v1/users/{target_id}/reset-password",
        headers={"Authorization": f"Bearer {beta_adm_token}"},
        json={"new_password": "NewStrongPass_2026!"},
    )
    assert res_cross.status_code == 404
    assert res_cross.json()["code"] == "NOT_FOUND"

    # 5. 合法重置成功 -> 200 OK
    res_success = client.post(
        f"/api/v1/users/{target_id}/reset-password",
        headers={"Authorization": f"Bearer {alpha_adm_token}"},
        json={"new_password": "NewStrongPass_2026!"},
    )
    assert res_success.status_code == 200
    body = res_success.json()
    assert body["success"] is True
    assert body["user_id"] == target_id

    # 6. 原既有活跃会话被作废 -> 401 UNAUTHENTICATED
    res_session = client.get("/api/v1/session", headers={"Authorization": f"Bearer {target_token}"})
    assert res_session.status_code == 401
    assert res_session.json()["code"] == "UNAUTHENTICATED"

    # 7. 旧密码无法登录 -> 401 INVALID_CREDENTIALS
    res_old_login = client.post("/api/v1/auth/login", json={"username": target_id, "password": "Target_user_2026"})
    assert res_old_login.status_code == 401
    assert res_old_login.json()["code"] == "INVALID_CREDENTIALS"

    # 8. 新密码正常登录 -> 200 OK
    res_new_login = client.post("/api/v1/auth/login", json={"username": target_id, "password": "NewStrongPass_2026!"})
    assert res_new_login.status_code == 200
    assert "access_token" in res_new_login.json()


def test_account_lock_on_failed_logins_and_unlock(client: TestClient, sec_ops_env):
    """测试连续登录失败触发账号锁定（423 ACCOUNT_LOCKED）与管理员一键解锁端点。"""
    alpha_adm_token = sec_ops_env["alpha_adm_token"]
    target_id = sec_ops_env["target_user_id"]
    beta_adm_token = sec_ops_env["beta_adm_token"]
    target_token = sec_ops_env["target_token"]
    member_token = sec_ops_env["member_token"]

    # 1. 连续 4 次输错密码 -> 每次返回 401 INVALID_CREDENTIALS
    for i in range(1, 5):
        res = client.post("/api/v1/auth/login", json={"username": target_id, "password": f"wrong_pass_{i}"})
        assert res.status_code == 401
        assert res.json()["code"] == "INVALID_CREDENTIALS"
        assert f"还剩 {5 - i} 次" in res.json()["message"]

    # 2. 第 5 次输错密码 -> 触发自动锁定 423 ACCOUNT_LOCKED
    res5 = client.post("/api/v1/auth/login", json={"username": target_id, "password": "wrong_pass_5"})
    assert res5.status_code == 423
    assert res5.json()["code"] == "ACCOUNT_LOCKED"
    assert "账号已被锁定" in res5.json()["message"]

    # 3. 锁定后即便输入正确密码 -> 依然被拦截 423 ACCOUNT_LOCKED
    res_correct_blocked = client.post("/api/v1/auth/login", json={"username": target_id, "password": "Target_user_2026"})
    assert res_correct_blocked.status_code == 423
    assert res_correct_blocked.json()["code"] == "ACCOUNT_LOCKED"

    # 3.1 被锁定的用户既有 Token 访问系统受限 -> 401 UNAUTHENTICATED
    res_locked_tok = client.get("/api/v1/session", headers={"Authorization": f"Bearer {target_token}"})
    assert res_locked_tok.status_code == 401
    assert res_locked_tok.json()["code"] == "UNAUTHENTICATED"

    # 4. 普通成员尝试解锁 -> 403 FORBIDDEN
    res_unlock_forbid = client.post(
        f"/api/v1/users/{target_id}/unlock",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert res_unlock_forbid.status_code == 403
    assert res_unlock_forbid.json()["code"] == "FORBIDDEN"

    # 5. 跨公司企管尝试解锁 -> 404 NOT_FOUND
    res_unlock_cross = client.post(
        f"/api/v1/users/{target_id}/unlock",
        headers={"Authorization": f"Bearer {beta_adm_token}"},
    )
    assert res_unlock_cross.status_code == 404
    assert res_unlock_cross.json()["code"] == "NOT_FOUND"

    # 6. 本公司管理员解锁 -> 200 OK
    res_unlock = client.post(
        f"/api/v1/users/{target_id}/unlock",
        headers={"Authorization": f"Bearer {alpha_adm_token}"},
    )
    assert res_unlock.status_code == 200
    body = res_unlock.json()
    assert body["success"] is True
    assert body["is_locked"] is False
    assert body["failed_login_attempts"] == 0

    # 7. 解锁后使用正确密码登录 -> 成功 200 OK
    res_login_after = client.post("/api/v1/auth/login", json={"username": target_id, "password": "Target_user_2026"})
    assert res_login_after.status_code == 200
    assert "access_token" in res_login_after.json()


def test_role_update_super_admin_protection_and_cannot_demote_self(client: TestClient, sec_ops_env):
    """测试角色分配端点：角色合法性、超管 admin 保护门禁与管理员防自降权门禁。"""
    admin_token = sec_ops_env["admin_token"]
    alpha_adm_token = sec_ops_env["alpha_adm_token"]
    alpha_adm_id = sec_ops_env["alpha_adm_id"]
    target_id = sec_ops_env["target_user_id"]
    beta_adm_token = sec_ops_env["beta_adm_token"]

    # 1. 调整目标用户为 project_lead -> 200 OK
    res_role1 = client.patch(
        f"/api/v1/users/{target_id}/role",
        headers={"Authorization": f"Bearer {alpha_adm_token}"},
        json={"role": "project_lead"},
    )
    assert res_role1.status_code == 200
    assert res_role1.json()["role"] == "project_lead"

    # 2. 传入非法角色代码 -> 422 VALIDATION_ERROR
    res_invalid = client.patch(
        f"/api/v1/users/{target_id}/role",
        headers={"Authorization": f"Bearer {alpha_adm_token}"},
        json={"role": "invalid_magic_role"},
    )
    assert res_invalid.status_code == 422
    assert res_invalid.json()["code"] == "VALIDATION_ERROR"

    # 3. 跨企业管理员修改角色 -> 404 NOT_FOUND
    res_cross = client.patch(
        f"/api/v1/users/{target_id}/role",
        headers={"Authorization": f"Bearer {beta_adm_token}"},
        json={"role": "viewer"},
    )
    assert res_cross.status_code == 404
    assert res_cross.json()["code"] == "NOT_FOUND"

    # 4. 尝试修改系统超管 admin 角色 -> 403 SUPER_ADMIN_PROTECTED
    res_admin_protect = client.patch(
        "/api/v1/users/admin/role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "bid_writer"},
    )
    assert res_admin_protect.status_code == 403
    assert res_admin_protect.json()["code"] == "SUPER_ADMIN_PROTECTED"

    # 5. 管理员尝试自我降权为普通用户 -> 403 CANNOT_DEMOTE_SELF
    res_demote_self = client.patch(
        f"/api/v1/users/{alpha_adm_id}/role",
        headers={"Authorization": f"Bearer {alpha_adm_token}"},
        json={"role": "bid_writer"},
    )
    assert res_demote_self.status_code == 403
    assert res_demote_self.json()["code"] == "CANNOT_DEMOTE_SELF"

    # 6. 超级管理员可跨企业调整任意用户角色 -> 200 OK
    res_super_change = client.patch(
        f"/api/v1/users/{target_id}/role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "auditor"},
    )
    assert res_super_change.status_code == 200
    assert res_super_change.json()["role"] == "auditor"
