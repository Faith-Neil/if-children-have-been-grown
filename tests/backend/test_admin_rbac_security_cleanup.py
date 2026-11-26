# ISSUE-056：平台安全策略、审计租户隔离与后台权限边界回归。
from uuid import uuid4

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



def test_company_admin_cannot_reach_platform_model_or_engine_config(client: TestClient):
    company_admin = login(client, "alpha-company-admin")
    for method, path, payload in (
        ("get", "/api/v1/model-configs", None),
        ("post", "/api/v1/model-configs", {"name": "越权模型", "base_url": "http://127.0.0.1:8000", "model": "qwen"}),
        ("get", "/api/v1/ragflow-config", None),
        ("put", "/api/v1/ragflow-config", {"base_url": "http://127.0.0.1:9380"}),
        ("post", "/api/v1/ragflow-config/test", {}),
    ):
        response = getattr(client, method)(path, headers=company_admin, json=payload) if payload is not None else getattr(client, method)(path, headers=company_admin)
        assert response.status_code == 403, (method, path, response.text)


def test_cross_company_users_are_not_visible_to_company_admin(client: TestClient):
    company_admin = login(client, "alpha-company-admin")
    cross_list = client.get("/api/v1/users?company_id=beta", headers=company_admin)
    assert cross_list.status_code == 404
    own_list = client.get("/api/v1/users", headers=company_admin)
    assert own_list.status_code == 200
    assert {row["company_id"] for row in own_list.json()["items"]} == {"alpha"}


def test_expired_session_is_rejected_by_backend(client: TestClient):
    platform = login(client, "admin")
    updated = client.patch("/api/v1/platform/security-settings", headers=platform,
                           json={"session_timeout_minutes": 30})
    assert updated.status_code == 200, updated.text

    login_body = client.post("/api/v1/auth/login", json={"username": "alpha-manager", "password": "X_2026"}).json()
    token = login_body["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/session", headers=headers).status_code == 200

    import time
    issued = time.time() - 31 * 60

    def expire(state):
        state.service_stores.setdefault("session_times", {}).setdefault("tokens", {})[token] = issued

    client.app.state.service.repository.transaction(expire)
    expired = client.get("/api/v1/session", headers=headers)
    assert expired.status_code == 401
    assert "过期" in expired.json()["message"]


def test_parse_job_persists_independent_demo_job_type_and_progress(client: TestClient, monkeypatch):
    from test_parse_jobs import _uploaded, _start, _wait

    flow = _uploaded(client)
    repository = client.app.state.service.repository
    saved = []
    updates = []
    monkeypatch.setattr(repository, "mode", "mysql", raising=False)
    monkeypatch.setattr(repository, "save_job", lambda data, **kwargs: saved.append(data))
    monkeypatch.setattr(repository, "update_job_progress",
                        lambda job_id, progress, **kwargs: updates.append({"id": job_id, "progress": progress, **kwargs}) or True)

    started = _start(flow)
    assert started.status_code == 202, started.text
    job_id = started.json()["id"]
    assert saved and saved[0]["job_type"] == "parse" and saved[0]["id"] == job_id

    done = _wait(flow, job_id)
    assert done["status"] == "completed"
    assert any(row["id"] == job_id and row.get("status") == "completed" and row["progress"] == 100 for row in updates)


def test_technical_volume_persists_independent_demo_job_type(client: TestClient, monkeypatch):
    from test_generation_session import _ready, _start as start_volume, _active_session, _finish

    headers, project_id, workspace, model = _ready(client)
    repository = client.app.state.service.repository
    saved = []
    updates = []
    monkeypatch.setattr(repository, "mode", "mysql", raising=False)
    monkeypatch.setattr(repository, "save_job", lambda data, **kwargs: saved.append(data))
    monkeypatch.setattr(repository, "update_job_progress",
                        lambda job_id, progress, **kwargs: updates.append({"id": job_id, "progress": progress, **kwargs}) or True)

    responses = []
    worker = start_volume(client, headers, project_id, workspace, responses)
    assert model.started.wait(10)
    running = _active_session(client, headers, project_id)
    assert saved and saved[0]["job_type"] == "technical_volume" and saved[0]["id"] == running["id"]
    model.gate.set()
    _finish(worker, responses)
    assert any(row["id"] == running["id"] for row in updates)

def test_technical_volume_cancel_syncs_demo_job_and_nonresumable_retry_is_blocked(client: TestClient, monkeypatch):
    from test_generation_session import _ready, _start as start_volume, _active_session, _finish, _wait_status

    headers, project_id, workspace, model = _ready(client)
    repository = client.app.state.service.repository
    updates = []
    monkeypatch.setattr(repository, "mode", "mysql", raising=False)
    monkeypatch.setattr(repository, "save_job", lambda data, **kwargs: True)
    monkeypatch.setattr(repository, "update_job_progress",
                        lambda job_id, progress, **kwargs: updates.append({"id": job_id, "progress": progress, **kwargs}) or True)

    responses = []
    worker = start_volume(client, headers, project_id, workspace, responses)
    assert model.started.wait(10)
    running = _active_session(client, headers, project_id)
    cancelled = client.post(
        f"/api/v1/jobs/{running['id']}/cancel",
        headers={**headers, "Idempotency-Key": str(uuid4())},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
    final = _wait_status(client, headers, running["id"], ("cancelled",))
    assert final["status"] == "cancelled"
    _finish(worker, responses)
    assert any(row["id"] == running["id"] and row.get("status") == "cancelled" for row in updates)

    retry = client.post(
        f"/api/v1/jobs/{running['id']}/retry",
        headers={**headers, "Idempotency-Key": str(uuid4())},
    )
    assert retry.status_code == 409
    assert "不能原样重试" in retry.json()["message"]
