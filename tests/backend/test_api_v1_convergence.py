# 为什么有这个文件：验证 WP-5 API/错误体收敛、/api/demo 弃用与生产演示账号禁用门禁。
# 它解决什么问题：
# 1. 确保 /api/demo/accounts 与 /api/demo/login 带有 Deprecation: true 响应头；
# 2. 确保在生产配置（ICG_ALLOW_DEMO_LOGIN=0 / ICG_ENV=production）下禁用内置演示账号登录（403 FORBIDDEN）；
# 3. 确保统一错误体格式包含 code, message, details, traceId。

import os
import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from icg_demo.domain import DEMO_ONLY_ACCOUNT_IDS


@pytest.fixture
def client():
    return TestClient(create_app())


def test_api_demo_routes_return_deprecation_header(client):
    """验证 /api/demo/* 响应头包含 Deprecation: true。"""
    resp_accounts = client.get("/api/demo/accounts")
    assert resp_accounts.status_code == 200
    assert resp_accounts.headers.get("Deprecation") == "true"
    assert resp_accounts.headers.get("X-Request-ID") is not None

    resp_login = client.post("/api/demo/login", json={"account_id": "alpha-manager"})
    assert resp_login.status_code == 200
    assert resp_login.headers.get("Deprecation") == "true"
    assert "access_token" in resp_login.json()


def test_production_config_disables_demo_accounts(client, monkeypatch):
    """验证生产配置下，内置演示账号登录被严格拒绝（403 FORBIDDEN）。"""
    monkeypatch.setenv("ICG_ALLOW_DEMO_LOGIN", "0")
    for demo_acc in ("alpha-manager", "alpha-editor", "beta-manager"):
        resp = client.post("/api/demo/login", json={"account_id": demo_acc})
        assert resp.status_code == 403
        data = resp.json()
        assert data["code"] == "FORBIDDEN"
        assert "traceId" in data
        assert resp.headers.get("Deprecation") == "true"


def test_production_env_production_disables_demo_accounts(client, monkeypatch):
    """验证 ICG_ENV=production 时内置演示账号登录被拦截。"""
    monkeypatch.setenv("ICG_ENV", "production")
    resp = client.post("/api/demo/login", json={"account_id": "alpha-manager"})
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


def test_unified_error_body_across_v1_and_demo(client):
    """验证统一错误体结构统一具备 code, message, details, traceId。"""
    # 401 unauthenticated
    resp_unauth = client.get("/api/v1/projects")
    assert resp_unauth.status_code == 401
    err = resp_unauth.json()
    assert "code" in err
    assert "message" in err
    assert "details" in err
    assert "traceId" in err
    assert err["traceId"] == resp_unauth.headers.get("X-Request-ID")

    # 422 validation
    resp_val = client.post("/api/demo/login", json={"account_id": 12345})
    assert resp_val.status_code == 422
    err2 = resp_val.json()
    assert err2["code"] == "VALIDATION_ERROR"
    assert "traceId" in err2
