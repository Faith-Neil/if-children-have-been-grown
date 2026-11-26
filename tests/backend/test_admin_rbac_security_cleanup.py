# ISSUE-056：平台安全策略、审计租户隔离与后台权限边界回归。
from fastapi.testclient import TestClient
from test_reference_flow import client, login  # noqa: F401


def test_platform_security_is_platform_admin_only_and_enforced(client: TestClient):
    company_admin = login(client, "alpha-company-admin")
    refused = client.get("/api/v1/platform/security-settings", headers=company_admin)
    assert refused.status_code == 403

    platform = login(client, "admin")
    updated = client.patch("/api/v1/platform/security-settings", headers=platform,
                           json={"password_min_length": 10, "password_min_char_classes": 4,
                                 "max_login_attempts": 2, "session_timeout_minutes": 120})
    assert updated.status_code == 200, updated.text

    created = client.post("/api/v1/users", headers=platform, json={
        "username": "iss056-user", "name": "安全策略验证", "company_id": "alpha", "role": "member",
        "password": "Aa1aaaaaa"})
    assert created.status_code == 422 and created.json()["code"] == "PASSWORD_WEAK"

    created = client.post("/api/v1/users", headers=platform, json={
        "username": "iss056-user", "name": "安全策略验证", "company_id": "alpha", "role": "member",
        "password": "Aa1!aaaaaaaa", "must_change_password": False})
    assert created.status_code in (200, 201), created.text

    for _ in range(2):
        bad = client.post("/api/v1/auth/login", json={"username": "iss056-user", "password": "Wrong_Pass_1"})
        assert bad.status_code in (401, 423)
    locked = client.post("/api/v1/auth/login", json={"username": "iss056-user", "password": "Aa1!aaaaaaaa"})
    assert locked.status_code == 423 and locked.json()["code"] == "ACCOUNT_LOCKED"


def test_audit_logs_real_api_and_tenant_isolation(client: TestClient):
    company_admin = login(client, "alpha-company-admin")
    own = client.get("/api/v1/audit-logs", headers=company_admin)
    assert own.status_code == 200, own.text
    assert all(row.get("company_id") in (None, "alpha") for row in own.json()["items"])
    cross = client.get("/api/v1/audit-logs?company_id=beta", headers=company_admin)
    assert cross.status_code == 403

    platform = login(client, "admin")
    global_rows = client.get("/api/v1/audit-logs", headers=platform)
    assert global_rows.status_code == 200
    assert global_rows.json()["total"] >= 1
