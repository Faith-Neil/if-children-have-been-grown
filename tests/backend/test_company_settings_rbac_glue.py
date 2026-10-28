# 为什么有这个文件：前后端契约联调工单 INT-COMPANY-SETTINGS-RBAC-GLUE 专属端到端集成测试。
# 它解决什么问题：
# 1. 验证非演示模式（VITE_DEMO=0）下，企业设置 CRUD 端点（GET/PATCH /api/v1/companies/{company_id}/settings）的端到端契约；
# 2. 验证超级管理员可跨企业管理任意公司设置，企业管理员只能管理本公司设置；
# 3. 验证租户隔离（跨租户访问严格返回 404 NOT_FOUND 拦截，杜绝租户信息嗅探）；
# 4. 验证企业内细粒度 RBAC 权限（普通编写人/只读角色允许读本公司设置，修改严格拦截 403 FORBIDDEN）；
# 5. 验证“企业设置只能调严不能调宽”安全基线与 9.11 联动规则（越界拦截 422 SETTING_VALUE_OUT_OF_BOUNDS）。

import pytest
from fastapi.testclient import TestClient

from icg.domain.domain import Account
from icg.domain.auth_service import hash_password
from test_reference_flow import client


@pytest.fixture
def auth_tokens(client: TestClient):
    """为不同测试角色创建账号与认证 Token。"""
    service = client.app.state.service

    # 1. 超级管理员登录 Token
    super_admin_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "X_2026"})
    assert super_admin_res.status_code == 200
    super_admin_token = super_admin_res.json()["access_token"]

    # 2. Alpha 企业管理员账号
    alpha_pass_hash, alpha_salt = hash_password("Alpha_admin_2026")
    alpha_admin_user = Account(
        id="formal-alpha-admin",
        name="Alpha 企业管理员",
        company_id="alpha",
        role="company_admin",
        _DEMO_ONLY=False,
        password_hash=alpha_pass_hash,
        salt=alpha_salt,
        display_name="Alpha 企管",
    )
    service.repository.transaction(lambda state: state.accounts.__setitem__("formal-alpha-admin", alpha_admin_user))
    alpha_login = client.post("/api/v1/auth/login", json={"username": "formal-alpha-admin", "password": "Alpha_admin_2026"})
    assert alpha_login.status_code == 200
    alpha_admin_token = alpha_login.json()["access_token"]

    # 3. Alpha 投标编写人账号（普通非管理员角色）
    writer_pass_hash, writer_salt = hash_password("Alpha_writer_2026")
    alpha_writer_user = Account(
        id="formal-alpha-writer",
        name="Alpha 标书编写人",
        company_id="alpha",
        role="bid_writer",
        _DEMO_ONLY=False,
        password_hash=writer_pass_hash,
        salt=writer_salt,
        display_name="Alpha 标书编写人",
    )
    service.repository.transaction(lambda state: state.accounts.__setitem__("formal-alpha-writer", alpha_writer_user))
    writer_login = client.post("/api/v1/auth/login", json={"username": "formal-alpha-writer", "password": "Alpha_writer_2026"})
    assert writer_login.status_code == 200
    alpha_writer_token = writer_login.json()["access_token"]

    # 4. Beta 企业管理员账号
    beta_pass_hash, beta_salt = hash_password("Beta_admin_2026")
    beta_admin_user = Account(
        id="formal-beta-admin",
        name="Beta 企业管理员",
        company_id="beta",
        role="company_admin",
        _DEMO_ONLY=False,
        password_hash=beta_pass_hash,
        salt=beta_salt,
        display_name="Beta 企管",
    )
    service.repository.transaction(lambda state: state.accounts.__setitem__("formal-beta-admin", beta_admin_user))
    beta_login = client.post("/api/v1/auth/login", json={"username": "formal-beta-admin", "password": "Beta_admin_2026"})
    assert beta_login.status_code == 200
    beta_admin_token = beta_login.json()["access_token"]

    return {
        "super_admin": super_admin_token,
        "alpha_admin": alpha_admin_token,
        "alpha_writer": alpha_writer_token,
        "beta_admin": beta_admin_token,
    }


def test_unauthenticated_company_settings_blocked_401(client: TestClient):
    """验证未认证请求调阅或修改企业设置严格拦截 401 UNAUTHENTICATED。"""
    res_get = client.get("/api/v1/companies/alpha/settings")
    assert res_get.status_code == 401
    assert res_get.json()["code"] == "UNAUTHENTICATED"

    res_patch = client.patch("/api/v1/companies/alpha/settings", json={"password_min_length": 10})
    assert res_patch.status_code == 401
    assert res_patch.json()["code"] == "UNAUTHENTICATED"


def test_super_admin_manage_any_company_settings(client: TestClient, auth_tokens):
    """验证超级管理员拥有系统级能力，可跨租户调阅与管理任意公司设置。"""
    headers = {"Authorization": f"Bearer {auth_tokens['super_admin']}"}

    # 1. 调阅 Alpha 公司设置
    res_alpha = client.get("/api/v1/companies/alpha/settings", headers=headers)
    assert res_alpha.status_code == 200, res_alpha.text
    alpha_data = res_alpha.json()
    assert alpha_data["company_id"] == "alpha"
    assert alpha_data["password_min_length"] == 8

    # 2. 超管更新 Alpha 公司设置（调严密码策略为 12 位，4 类）
    patch_alpha = client.patch(
        "/api/v1/companies/alpha/settings",
        json={"password_min_length": 12, "password_min_char_classes": 4},
        headers=headers,
    )
    assert patch_alpha.status_code == 200, patch_alpha.text
    assert patch_alpha.json()["password_min_length"] == 12
    assert patch_alpha.json()["password_min_char_classes"] == 4
    assert patch_alpha.json()["updated_by"] == "admin"

    # 3. 调阅 Beta 公司设置
    res_beta = client.get("/api/v1/companies/beta/settings", headers=headers)
    assert res_beta.status_code == 200, res_beta.text
    assert res_beta.json()["company_id"] == "beta"

    # 4. 超管更新 Beta 公司设置
    patch_beta = client.patch(
        "/api/v1/companies/beta/settings",
        json={"max_login_attempts": 3, "loop_max_rounds": 2},
        headers=headers,
    )
    assert patch_beta.status_code == 200, patch_beta.text
    assert patch_beta.json()["max_login_attempts"] == 3
    assert patch_beta.json()["loop_max_rounds"] == 2


def test_company_admin_manage_own_company_settings(client: TestClient, auth_tokens):
    """验证企业管理员可读写本企业设置，成功生效。"""
    headers = {"Authorization": f"Bearer {auth_tokens['alpha_admin']}"}

    # 1. 获取本企业设置
    res = client.get("/api/v1/companies/alpha/settings", headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["company_id"] == "alpha"

    # 2. 更新本企业设置
    update_res = client.patch(
        "/api/v1/companies/alpha/settings",
        json={
            "edit_lock_timeout_minutes": 45,
            "edit_lock_heartbeat_seconds": 60,
            "editor_autosave_seconds": 15,
            "assistant_suggestion_count": 4,
        },
        headers=headers,
    )
    assert update_res.status_code == 200, update_res.text
    data = update_res.json()
    assert data["edit_lock_timeout_minutes"] == 45
    assert data["edit_lock_heartbeat_seconds"] == 60
    assert data["editor_autosave_seconds"] == 15
    assert data["assistant_suggestion_count"] == 4
    assert data["updated_by"] == "formal-alpha-admin"


def test_cross_company_access_blocked_with_404(client: TestClient, auth_tokens):
    """验证租户隔离红线：Alpha 企业管理员访问 Beta 企业设置严格返回 404 NOT_FOUND（防嗅探）。"""
    headers = {"Authorization": f"Bearer {auth_tokens['alpha_admin']}"}

    # 1. 尝试读取跨租户公司设置
    res_get = client.get("/api/v1/companies/beta/settings", headers=headers)
    assert res_get.status_code == 404, res_get.text
    assert res_get.json()["code"] == "NOT_FOUND"
    assert "无权访问" in res_get.json()["message"] or "未找到" in res_get.json()["message"]

    # 2. 尝试修改跨租户公司设置
    res_patch = client.patch(
        "/api/v1/companies/beta/settings",
        json={"password_min_length": 10},
        headers=headers,
    )
    assert res_patch.status_code == 404, res_patch.text
    assert res_patch.json()["code"] == "NOT_FOUND"


def test_same_company_non_admin_cannot_patch_settings(client: TestClient, auth_tokens):
    """验证同企业非管理员角色（编写人）可以只读查看本公司设置，但修改被严格拦截 403 FORBIDDEN。"""
    headers = {"Authorization": f"Bearer {auth_tokens['alpha_writer']}"}

    # 1. 读取本公司设置允许（用于前端展示或规则感知）
    res_get = client.get("/api/v1/companies/alpha/settings", headers=headers)
    assert res_get.status_code == 200, res_get.text
    assert res_get.json()["company_id"] == "alpha"

    # 2. 尝试更新本公司设置被 403 FORBIDDEN 拦截
    res_patch = client.patch(
        "/api/v1/companies/alpha/settings",
        json={"password_min_length": 10},
        headers=headers,
    )
    assert res_patch.status_code == 403, res_patch.text
    err = res_patch.json()
    assert err["code"] == "FORBIDDEN"
    assert "企业管理员" in err["message"]


def test_setting_bounds_tighten_only_rules(client: TestClient, auth_tokens):
    """验证“公司设置只能调严不能调宽”安全基线与 9.11 联动规则校验（越界抛出 422 SETTING_VALUE_OUT_OF_BOUNDS）。"""
    headers = {"Authorization": f"Bearer {auth_tokens['alpha_admin']}"}

    # 1. 密码最小长度调宽拦截：低于平台下限 8 位
    res = client.patch("/api/v1/companies/alpha/settings", json={"password_min_length": 6}, headers=headers)
    assert res.status_code == 422, res.text
    assert res.json()["code"] == "SETTING_VALUE_OUT_OF_BOUNDS"
    assert "低于平台下限 8 位" in res.json()["message"]

    # 超过平台上限 32 位拦截
    res = client.patch("/api/v1/companies/alpha/settings", json={"password_min_length": 40}, headers=headers)
    assert res.status_code == 422, res.text
    assert res.json()["code"] == "SETTING_VALUE_OUT_OF_BOUNDS"
    assert "超过平台上限 32 位" in res.json()["message"]

    # 2. 密码字符分类数调宽拦截：低于平台下限 3 类
    res = client.patch("/api/v1/companies/alpha/settings", json={"password_min_char_classes": 2}, headers=headers)
    assert res.status_code == 422, res.text
    assert res.json()["code"] == "SETTING_VALUE_OUT_OF_BOUNDS"
    assert "低于平台下限 3 类" in res.json()["message"]

    # 超过 4 类拦截
    res = client.patch("/api/v1/companies/alpha/settings", json={"password_min_char_classes": 5}, headers=headers)
    assert res.status_code == 422, res.text
    assert res.json()["code"] == "SETTING_VALUE_OUT_OF_BOUNDS"

    # 3. 连续失败登录锁定次数调宽拦截：超过平台上限 5 次
    res = client.patch("/api/v1/companies/alpha/settings", json={"max_login_attempts": 8}, headers=headers)
    assert res.status_code == 422, res.text
    assert res.json()["code"] == "SETTING_VALUE_OUT_OF_BOUNDS"
    assert "超过平台上限 5 次" in res.json()["message"]

    # 4. 编辑锁超时时长调宽拦截：超过平台上限 60 分钟
    res = client.patch("/api/v1/companies/alpha/settings", json={"edit_lock_timeout_minutes": 90}, headers=headers)
    assert res.status_code == 422, res.text
    assert res.json()["code"] == "SETTING_VALUE_OUT_OF_BOUNDS"
    assert "超过平台上限 60 分钟" in res.json()["message"]

    # 小于等于 5 分钟拦截（必须大于释放提醒 5 分钟）
    res = client.patch("/api/v1/companies/alpha/settings", json={"edit_lock_timeout_minutes": 5}, headers=headers)
    assert res.status_code == 422, res.text
    assert res.json()["code"] == "SETTING_VALUE_OUT_OF_BOUNDS"

    # 5. 编辑锁心跳越界：< 15 秒或 > 120 秒
    res = client.patch("/api/v1/companies/alpha/settings", json={"edit_lock_heartbeat_seconds": 10}, headers=headers)
    assert res.status_code == 422, res.text
    assert res.json()["code"] == "SETTING_VALUE_OUT_OF_BOUNDS"

    res = client.patch("/api/v1/companies/alpha/settings", json={"edit_lock_heartbeat_seconds": 150}, headers=headers)
    assert res.status_code == 422, res.text
    assert res.json()["code"] == "SETTING_VALUE_OUT_OF_BOUNDS"

    # 6. 自动保存越界：< 5 秒或 > 60 秒
    res = client.patch("/api/v1/companies/alpha/settings", json={"editor_autosave_seconds": 2}, headers=headers)
    assert res.status_code == 422, res.text
    assert res.json()["code"] == "SETTING_VALUE_OUT_OF_BOUNDS"

    # 7. 联动规则一：自动保存间隔 > 心跳间隔拦截
    res = client.patch(
        "/api/v1/companies/alpha/settings",
        json={"edit_lock_heartbeat_seconds": 20, "editor_autosave_seconds": 30},
        headers=headers,
    )
    assert res.status_code == 422, res.text
    assert res.json()["code"] == "SETTING_VALUE_OUT_OF_BOUNDS"
    assert "不能大于编辑锁心跳间隔" in res.json()["message"]

    # 8. 联动规则二：心跳间隔 * 10 > 锁超时时长 * 60 拦截
    # 心跳 60 秒 * 10 = 600 秒；若锁超时设为 8 分钟 = 480 秒 -> 违背
    res = client.patch(
        "/api/v1/companies/alpha/settings",
        json={"edit_lock_heartbeat_seconds": 60, "edit_lock_timeout_minutes": 8},
        headers=headers,
    )
    assert res.status_code == 422, res.text
    assert res.json()["code"] == "SETTING_VALUE_OUT_OF_BOUNDS"
    assert "不能超过锁超时总时长" in res.json()["message"]

    # 9. 章节生成最大循环轮数调宽拦截：超过平台上限 5 轮
    res = client.patch("/api/v1/companies/alpha/settings", json={"loop_max_rounds": 8}, headers=headers)
    assert res.status_code == 422, res.text
    assert res.json()["code"] == "SETTING_VALUE_OUT_OF_BOUNDS"
    assert "超过平台上限 5 轮" in res.json()["message"]

    # 10. 合法调严参数保存成功
    res_valid = client.patch(
        "/api/v1/companies/alpha/settings",
        json={
            "password_min_length": 14,
            "password_min_char_classes": 4,
            "max_login_attempts": 3,
            "edit_lock_timeout_minutes": 30,
            "edit_lock_heartbeat_seconds": 60,
            "editor_autosave_seconds": 10,
            "loop_max_rounds": 2,
        },
        headers=headers,
    )
    assert res_valid.status_code == 200, res_valid.text
    data = res_valid.json()
    assert data["password_min_length"] == 14
    assert data["password_min_char_classes"] == 4
    assert data["max_login_attempts"] == 3
    assert data["loop_max_rounds"] == 2
