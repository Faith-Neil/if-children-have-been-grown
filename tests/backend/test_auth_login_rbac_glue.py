# 为什么有这个文件：前后端契约联调工单 INT-AUTH-LOGIN-RBAC-GLUE 专属端到端集成测试。
# 它解决什么问题：
# 1. 验证非演示模式（VITE_DEMO=0）下，基于账号密码登录（POST /api/v1/auth/login）与超级管理员鉴权（admin / X_2026）完整链路；
# 2. 验证凭据错误（密码错误、未知账号）统一拦截 401 INVALID_CREDENTIALS 及 RFC 7807 规范体；
# 3. 验证超级管理员成功获取 Access Token 并调用 GET /api/v1/session 拉取全权限导航会话（auth_mode="authenticated", role_mode="rbac-8roles", home_path="/platform"）；
# 4. 验证超级管理员四大核心系统级能力：全量任务脱敏/运维审计（/jobs?masked=true）、A-03 字典配置读写（/metadata/dict/*）、合规规则全目录调阅（/compliance-rules/catalog）以及跨租户运维审计。

import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from test_reference_flow import client


def test_auth_login_super_admin_success(client: TestClient):
    """验证超级管理员 admin / X_2026 登录并成功签发 Access Token。"""
    payload = {"username": "admin", "password": "X_2026"}
    res = client.post("/api/v1/auth/login", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert "access_token" in data and len(data["access_token"]) > 20
    assert data["token_type"] == "bearer"
    user = data["user"]
    assert user["id"] == "admin"
    assert user["role"] == "platform_admin"
    assert user["company_id"] == "system"


def test_auth_login_invalid_password_blocked_401(client: TestClient):
    """验证密码错误拦截 401 INVALID_CREDENTIALS 与 RFC 7807 统一错误响应。"""
    payload = {"username": "admin", "password": "X_wrong_password"}
    res = client.post("/api/v1/auth/login", json=payload)
    assert res.status_code == 401, res.text

    err = res.json()
    assert err["code"] == "INVALID_CREDENTIALS"
    assert "密码错误" in err["message"] or "用户名或密码错误" in err["message"]
    assert "traceId" in err
    assert res.headers.get("X-Request-ID") == err["traceId"]


def test_auth_login_unknown_user_blocked_401(client: TestClient):
    """验证未知用户名拦截 401 INVALID_CREDENTIALS。"""
    payload = {"username": "unknown_user_999", "password": "X_2026"}
    res = client.post("/api/v1/auth/login", json=payload)
    assert res.status_code == 401, res.text

    err = res.json()
    assert err["code"] == "INVALID_CREDENTIALS"
    assert "traceId" in err


def test_super_admin_session_retrieval(client: TestClient):
    """验证超级管理员通过 Token 换取正式 RBAC-8 角色导航会话。"""
    # 1. 登录
    login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "X_2026"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. 会话查询
    sess_res = client.get("/api/v1/session", headers=headers)
    assert sess_res.status_code == 200, sess_res.text
    session = sess_res.json()

    assert session["auth_mode"] == "authenticated"
    assert session["role_mode"] == "rbac-8roles"
    assert session["home_path"] in ("/platform", "/workbench")
    assert session["user"]["id"] == "admin"
    assert session["user"]["primary_role"] == "platform_admin"
    assert "platform_admin" in session["user"]["roles"]

    # 验证超级管理员全权限导航菜单：包含 platform (write)、jobs 等核心入口
    nav_routes = {n["route_id"]: n for n in session["navigation"]}
    assert "platform" in nav_routes
    assert nav_routes["platform"]["access"] == "write"
    assert "jobs" in nav_routes


def test_super_admin_system_capabilities(client: TestClient):
    """验证超级管理员系统级四大核心能力：全量任务脱敏审计、A-03 字典管理、合规规则目录、跨租户调阅。"""
    login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "X_2026"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. 调阅平台全量任务（支持查看脱敏/运维审计）
    res_jobs = client.get("/api/v1/jobs?masked=true", headers=headers)
    assert res_jobs.status_code == 200, res_jobs.text
    assert "jobs" in res_jobs.json()

    res_jobs_masked = client.get("/api/v1/jobs/masked", headers=headers)
    assert res_jobs_masked.status_code == 200

    # 2. 访问 A-03 字典配置与元数据管理（超管具备写权限）
    res_dict_types = client.get("/api/v1/metadata/dict/types", headers=headers)
    assert res_dict_types.status_code == 200
    assert res_dict_types.json()["total"] >= 10

    # 超管可新增系统级字典代码
    res_create_dict = client.post(
        "/api/v1/metadata/dict/items",
        headers=headers,
        json={
            "type_code": "requirement_category",
            "item_code": "super_admin_spec",
            "label": "超管专属需求规范",
            "sort_order": 99,
        },
    )
    assert res_create_dict.status_code == 201
    created_item = res_create_dict.json()
    assert created_item["item_code"] == "super_admin_spec"

    # 3. 调阅合规检查规则目录
    res_rules = client.get("/api/v1/compliance-rules/catalog", headers=headers)
    assert res_rules.status_code == 200, res_rules.text
    catalog = res_rules.json()["catalog"]
    assert len(catalog) >= 20
    rule_ids = {r["rule_id"] for r in catalog}
    assert "R15" in rule_ids
    assert "R23" in rule_ids
    assert "R34" in rule_ids
    assert "R37" in rule_ids


def test_standard_account_password_login(client: TestClient):
    """验证企业常规管理账号（formal-company-admin）支持基于默认密码登录认证并加载工作台会话。"""
    repo = client.app.state.service.repository
    from icg.domain.auth_service import hash_password
    from icg.domain.domain import Account
    digest, salt = hash_password("X_2026")
    repo.transaction(lambda state: state.accounts.__setitem__(
        "formal-company-admin",
        Account("formal-company-admin", "正式企业管理员", "alpha", "company_admin", _DEMO_ONLY=False,
                password_hash=digest, salt=salt)
    ))

    payload = {"username": "formal-company-admin", "password": "X_2026"}
    res = client.post("/api/v1/auth/login", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["user"]["id"] == "formal-company-admin"
    assert data["user"]["role"] == "company_admin"
    assert data["user"]["company_id"] == "alpha"

    # 会话验证
    token = data["access_token"]
    sess_res = client.get("/api/v1/session", headers={"Authorization": f"Bearer {token}"})
    assert sess_res.status_code == 200, sess_res.text
    session = sess_res.json()
    assert session["auth_mode"] == "authenticated"
    assert session["role_mode"] == "rbac-8roles"
    assert session["user"]["primary_role"] == "company_admin"
    assert session["home_path"] == "/workbench"
