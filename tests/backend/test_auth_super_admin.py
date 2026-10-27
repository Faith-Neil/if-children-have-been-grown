# 为什么有这个文件：验证正式账号密码认证机制与全系统超级管理员内置能力 (BE-AUTH-SUPER-ADMIN)。
# 它解决什么问题：
# 1. 验证基于 PBKDF2-HMAC-SHA256 的加盐哈希存储与常量时间比对（杜绝明文与时序侧信道）；
# 2. 验证 POST /api/v1/auth/login 契约及防缓存头 (Cache-Control: no-store / Pragma: no-cache)；
# 3. 验证错误凭据时严格返回 401 INVALID_CREDENTIALS 符合 RFC 7807 规范；
# 4. 验证内置超级管理员 (admin / X_2026) 具备全系统跨公司、跨项目全路由权限与双卷导出资格；
# 5. 验证在生产模式 / 关闭演示模式 (ICG_ALLOW_DEMO_LOGIN=0) 下正式账号密码认证独立通畅可用。

import pytest
from fastapi.testclient import TestClient

from icg.domain.auth_service import (
    DEFAULT_SUPER_ADMIN_PASSWORD,
    DEFAULT_SUPER_ADMIN_USERNAME,
    hash_password,
    is_super_admin,
    verify_password,
)
from icg_demo.adapters import DemoModelProvider, MemoryRepository, seed_state
from icg_demo.domain import DemoService
from icg_demo.main import create_app


@pytest.fixture
def repo():
    return MemoryRepository(seed_state())


@pytest.fixture
def client(repo):
    app = create_app(repository=repo)
    return TestClient(app)


def test_password_hashing_and_constant_time_verification():
    """验证 PBKDF2-HMAC-SHA256 算法加盐哈希及核验。"""
    pwd = "SecretPassword_2026"
    hashed, salt = hash_password(pwd)

    assert hashed.startswith("pbkdf2:sha256:100000$")
    assert salt in hashed
    assert verify_password(pwd, hashed, salt) is True
    assert verify_password("WrongPassword", hashed, salt) is False
    assert verify_password("", hashed, salt) is False
    assert verify_password(pwd, "") is False

    # 验证两次加盐哈希使用不同 salt，密文不一致
    hashed2, salt2 = hash_password(pwd)
    assert salt != salt2
    assert hashed != hashed2
    assert verify_password(pwd, hashed2, salt2) is True


def test_is_super_admin_helper():
    """验证超级管理员识别逻辑对 string / Account / Principal 的支持。"""
    assert is_super_admin("admin") is True
    assert is_super_admin("alpha-manager") is False
    assert is_super_admin(None) is False

    class DummyUser:
        id = "admin"

    class DummyPrincipal:
        user = DummyUser()

    assert is_super_admin(DummyUser()) is True
    assert is_super_admin(DummyPrincipal()) is True


def test_super_admin_positive_login(client):
    """验证超级管理员使用 admin / X_2026 正式登录成功，返回 Bearer Token 与防缓存响应头。"""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": DEFAULT_SUPER_ADMIN_USERNAME, "password": DEFAULT_SUPER_ADMIN_PASSWORD},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 20

    user = data["user"]
    assert user["id"] == "admin"
    assert user["username"] == "admin"
    assert user["company_id"] == "system"
    assert user["role"] == "platform_admin"
    assert user["display_name"] == "系统超级管理员"

    # 安全底线：严禁在响应中回显密码哈希或明文
    assert "password" not in user
    assert "password_hash" not in user
    assert "salt" not in user

    # 验证防缓存响应头
    assert "no-store" in resp.headers.get("cache-control", "").lower()
    assert resp.headers.get("pragma", "").lower() == "no-cache"


def test_super_admin_session_navigation_and_permissions(client):
    """验证超级管理员登录后换取会话，拥有全局 system 范围与全路由写入权限。"""
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "X_2026"},
    )
    token = login_resp.json()["access_token"]

    session_resp = client.get(
        "/api/v1/session",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert session_resp.status_code == 200
    session_data = session_resp.json()

    assert session_data["auth_mode"] == "authenticated"
    assert session_data["role_mode"] == "rbac-8roles"
    assert session_data["home_path"] == "/workbench"
    assert session_data["scope"]["kind"] == "system"
    assert session_data["scope"]["active_company_id"] == "system"

    # 验证导航包含所有标准业务与管理路由，且全部为 write 权限
    expected_routes = {
        "workbench", "library", "knowledge", "writing", "statistics",
        "admin", "admin.rules", "jobs", "platform", "platform.audit", "platform.jobs"
    }
    nav_routes = {item["route_id"]: item["access"] for item in session_data["navigation"]}
    for route in expected_routes:
        assert route in nav_routes, f"Missing route {route}"
        assert nav_routes[route] == "write", f"Route {route} expected write access"

    # 验证全局操作动作
    actions = set(session_data["allowedActions"])
    required_actions = {
        "projects.read", "projects.create", "library.read", "library.write",
        "sla_templates.read", "sla_templates.write", "jobs.read",
        "platform.write", "admin.write"
    }
    assert required_actions.issubset(actions)


def test_super_admin_negative_credentials(client):
    """验证错误密码、未知用户和空参数均返回 401 INVALID_CREDENTIALS (RFC 7807)。"""
    # 错误密码
    resp_bad_pwd = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "IncorrectPassword"},
    )
    assert resp_bad_pwd.status_code == 401
    bad_pwd_err = resp_bad_pwd.json()
    assert bad_pwd_err["code"] == "INVALID_CREDENTIALS"
    assert "traceId" in bad_pwd_err
    assert "details" in bad_pwd_err

    # 未知用户名
    resp_unknown = client.post(
        "/api/v1/auth/login",
        json={"username": "non_existent_user_999", "password": "X_2026"},
    )
    assert resp_unknown.status_code == 401
    assert resp_unknown.json()["code"] == "INVALID_CREDENTIALS"

    # 空用户名或空密码由 Pydantic 模型层拦截为 422 VALIDATION_ERROR
    resp_empty = client.post(
        "/api/v1/auth/login",
        json={"username": "", "password": ""},
    )
    assert resp_empty.status_code == 422
    assert resp_empty.json()["code"] == "VALIDATION_ERROR"


def test_normal_account_password_login(client):
    """验证普通业务账号（如 alpha-manager）同样支持正式账号密码登录。"""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "alpha-manager", "password": "X_2026"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["id"] == "alpha-manager"
    assert data["user"]["company_id"] == "alpha"

    # 获取会话应为 company 隔离范围
    token = data["access_token"]
    session_resp = client.get(
        "/api/v1/session",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert session_resp.status_code == 200
    sdata = session_resp.json()
    assert sdata["scope"]["kind"] == "company"
    assert sdata["scope"]["active_company_id"] == "alpha"


def test_super_admin_cross_company_access(client):
    """验证超级管理员能够跨公司穿透访问业务项目（如 alpha-project）并享有全套权限。"""
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "X_2026"},
    )
    token = login_resp.json()["access_token"]

    # 查询跨公司项目会话
    resp = client.get(
        "/api/v1/session?project_id=alpha-project",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    proj_access = resp.json()["project_access"]
    assert proj_access["id"] == "alpha-project"

    perms = proj_access["permissions"]
    assert perms["manage_team"] is True
    assert perms["manage_project"] is True
    assert perms["manage_structure"] is True
    assert perms["export_internal"] is True
    assert perms["check_all"] is True
    assert "technical" in perms["check_volumes"]
    assert "business" in perms["check_volumes"]
    assert "technical" in perms["export_volumes"]
    assert "business" in perms["export_volumes"]
    assert "project.export" in proj_access["route_permissions"]

    # 验证能顺利读取工作区
    ws_resp = client.get(
        "/api/v1/projects/alpha-project/workspace",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ws_resp.status_code == 200


def test_super_admin_in_production_mode(monkeypatch, client):
    """验证在关闭演示登录 (ICG_ALLOW_DEMO_LOGIN=0 / ICG_ENV=production) 下正式认证依然有效。"""
    monkeypatch.setenv("ICG_ALLOW_DEMO_LOGIN", "0")
    monkeypatch.setenv("ICG_ENV", "production")

    # 旧演示登录接口被阻断
    demo_login_resp = client.post(
        "/api/demo/login",
        json={"account_id": "alpha-manager"},
    )
    assert demo_login_resp.status_code == 403

    # 正式账号密码认证依然完全正常通畅
    formal_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "X_2026"},
    )
    assert formal_resp.status_code == 200
    assert "access_token" in formal_resp.json()
