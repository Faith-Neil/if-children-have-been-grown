# 为什么有这个文件：验证 API 收敛到 /api/v1、演示入口已移除、生产配置拒绝内置合成账号，以及统一错误体。
# 它解决什么问题：防止免密演示登录或内置账号在生产路径上重新出现。

import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_demo_routes_are_gone(client):
    assert client.get("/api/demo/accounts").status_code == 404
    assert client.post("/api/demo/login", json={"account_id": "alpha-manager"}).status_code in (404, 405)
    login = client.post("/api/v1/auth/login", json={"username": "alpha-manager", "password": "X_2026"})
    assert login.status_code == 200 and "Deprecation" not in login.headers
    paths = client.get("/openapi.json").json()["paths"] if client.get("/openapi.json").status_code == 200 else {}
    assert not any(path.startswith("/api/demo") for path in paths)


@pytest.mark.parametrize("env", [{"ICG_ENV": "production"}, {"ICG_REQUIRE_MYSQL": "1"}])
def test_production_config_rejects_seeded_accounts(client, monkeypatch, env):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    for account in ("alpha-manager", "alpha-editor", "beta-manager", "alpha-data-admin"):
        resp = client.post("/api/v1/auth/login", json={"username": account, "password": "X_2026"})
        assert resp.status_code == 401
        assert resp.json()["code"] == "INVALID_CREDENTIALS" and "traceId" in resp.json()


def test_unified_error_body(client):
    resp_unauth = client.get("/api/v1/projects")
    assert resp_unauth.status_code == 401
    err = resp_unauth.json()
    assert {"code", "message", "details", "traceId"} <= set(err)
    assert err["traceId"] == resp_unauth.headers.get("X-Request-ID")
    resp_val = client.post("/api/v1/auth/login", json={"username": 12345, "password": "X_2026"})
    assert resp_val.status_code == 422
    assert resp_val.json()["code"] == "VALIDATION_ERROR"
