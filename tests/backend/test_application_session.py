# 为什么有这个文件：通过真实HTTP会话入口验证可信身份、兼容导航及最小项目资源权限。
# 它解决什么问题：避免页面伪造公司或角色、沿用撤权前身份，或在读取权限时泄露正文和私人草稿。

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from icg_demo.adapters import MemoryRepository, seed_state
from icg_demo.domain import Draft, Principal
from icg_demo.main import create_app
from icg_demo.session_navigation import get_application_session, navigation_for_roles, ROLE_NAVIGATION


@pytest.fixture
def setup():
    repository = MemoryRepository(seed_state())
    with TestClient(create_app(repository=repository)) as client:
        yield client, repository


def login(client, identity="alpha-manager"):
    response = client.post("/api/demo/login", json={"account_id": identity})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


@pytest.mark.parametrize("identity,role,routes,actions", [
    ("alpha-manager", "project_lead", {"workbench", "library", "knowledge", "writing", "admin.rules", "jobs"},
     {"projects.read", "library.read", "sla_templates.read", "jobs.read", "library.write", "projects.create", "sla_templates.write"}),
    ("alpha-editor", "bid_writer", {"workbench", "library", "knowledge", "writing", "jobs"},
     {"projects.read", "library.read", "sla_templates.read", "jobs.read", "library.write"}),
    ("alpha-viewer", "readonly", {"workbench", "library", "knowledge", "jobs"},
     {"projects.read", "library.read", "sla_templates.read", "jobs.read"}),
])
def test_session_returns_only_server_identity_and_explicit_compat_mode(setup, identity, role, routes, actions):
    client, repository = setup
    headers = login(client, identity)
    before = repository.read()
    response = client.get("/api/v1/session", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["auth_mode"] == "synthetic-demo"
    assert data["role_mode"] == "legacy-demo-compat"
    assert data["user"]["id"] == identity
    assert data["user"]["role"] == before.accounts[identity].role
    assert data["user"]["roles"] == [role]
    assert data["user"]["primary_role"] == role
    assert data["scope"] == {"kind": "company", "active_company_id": "alpha", "allowed_company_ids": ["alpha"]}
    assert {item["route_id"] for item in data["navigation"]} == routes
    assert set(data["allowedActions"]) == actions
    assert data["home_path"] == "/workbench"
    assert data["session"] == {"expires_at": None, "renew_supported": False}
    assert "project_access" not in data
    assert "access_token" not in data and headers["Authorization"].split()[1] not in response.text
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Request-ID"]
    assert repository.read() == before


@pytest.mark.parametrize("authorization", [None, "Bearer missing-token", "Basic anything", "Bearer "])
def test_missing_or_bad_token_is_401(setup, authorization):
    client, _ = setup
    response = client.get("/api/v1/session", headers={"Authorization": authorization} if authorization else {})
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert "user" not in response.json() and "project_access" not in response.json()


@pytest.mark.parametrize("role", ["unknown", "company_admin", "platform_admin", "group_admin", "data_admin", "reviewer"])
def test_unadapted_roles_are_denied_even_when_the_original_matrix_defines_them(setup, role):
    client, repository = setup
    headers = login(client)
    repository.transaction(lambda state: state.accounts.__setitem__(
        "alpha-manager", replace(state.accounts["alpha-manager"], role=role)))
    response = client.get("/api/v1/session", headers=headers)
    assert response.status_code == 403
    assert response.json()["code"] == "SESSION_ROLE_UNSUPPORTED"
    assert "navigation" not in response.json() and "user" not in response.json()


@pytest.mark.parametrize("company_id", [None, "", "  "])
def test_untrusted_company_scope_is_denied(setup, company_id):
    client, repository = setup
    headers = login(client)
    repository.transaction(lambda state: state.accounts.__setitem__(
        "alpha-manager", replace(state.accounts["alpha-manager"], company_id=company_id)))
    response = client.get("/api/v1/session", headers=headers)
    assert response.status_code == 403
    assert response.json()["code"] == "SESSION_SCOPE_UNSUPPORTED"


@pytest.mark.parametrize("query", ["company_id=beta", "role=company_admin", "user_id=beta-manager",
                                    "project_id=alpha-project&project_id=beta-project", "project_id="])
def test_client_cannot_override_session_identity_or_company(setup, query):
    client, _ = setup
    response = client.get("/api/v1/session?" + query, headers=login(client))
    assert response.status_code == 422
    assert "user" not in response.json()


def test_session_rejects_request_body(setup):
    client, _ = setup
    response = client.request("GET", "/api/v1/session", headers=login(client), json={"role": "company_admin"})
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_SESSION_INPUT"


@pytest.mark.parametrize("identity,project_id", [("beta-manager", "alpha-project"),
                                               ("alpha-outsider-manager", "alpha-project"),
                                               ("alpha-manager", "missing-project")])
def test_project_access_hides_foreign_nonmember_and_missing_projects(setup, identity, project_id):
    client, _ = setup
    response = client.get("/api/v1/session", params={"project_id": project_id}, headers=login(client, identity))
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
    assert response.json()["message"] == "未找到有权访问的项目。"
    assert "user" not in response.json() and "project_access" not in response.json()


def test_project_access_is_minimal_and_does_not_create_or_change_business_state(setup):
    client, repository = setup
    headers = login(client)
    def private_content(state):
        state.chapters["alpha-tech"].content = "不得出现在会话响应的正式正文"
        state.chapters["alpha-tech"].drafts["alpha-editor"] = Draft(1, "不得出现在会话响应的私人草稿", 1)
    repository.transaction(private_content)
    before = repository.read()
    response = client.get("/api/v1/session?project_id=alpha-project", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()["project_access"]
    assert set(data) == {"id", "revision", "route_permissions", "permissions", "chapters"}
    assert data["id"] == "alpha-project" and data["revision"] == before.projects["alpha-project"].revision
    assert data["permissions"]["manage_team"] is True
    assert "project.export" in data["route_permissions"]
    assert {chapter["id"] for chapter in data["chapters"]} == {"alpha-tech", "alpha-business"}
    assert all(set(chapter) == {"id", "volume", "permissions"} for chapter in data["chapters"])
    assert "正式正文" not in response.text and "私人草稿" not in response.text
    assert repository.read() == before


def test_session_reloads_changed_role_and_ignores_the_old_principal(setup):
    client, repository = setup
    headers = login(client)
    service = client.app.state.service
    token = headers["Authorization"].split()[1]
    stale = Principal(repository.read().accounts["alpha-manager"], token)
    repository.transaction(lambda state: state.accounts.__setitem__(
        "alpha-manager", replace(state.accounts["alpha-manager"], role="viewer")))
    response = client.get("/api/v1/session?project_id=alpha-project", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["user"]["roles"] == ["readonly"]
    assert "projects.create" not in data["allowedActions"]
    assert "admin.rules" not in {item["route_id"] for item in data["navigation"]}
    assert not data["project_access"]["permissions"]["manage_team"]
    assert all(not chapter["permissions"]["edit"] for chapter in data["project_access"]["chapters"])
    assert "project.export" not in data["project_access"]["route_permissions"]
    assert get_application_session(service, stale)["user"]["roles"] == ["readonly"]


def test_removed_membership_is_denied_with_existing_token(setup):
    client, repository = setup
    headers = login(client, "alpha-editor")
    assert client.get("/api/v1/session?project_id=alpha-project", headers=headers).status_code == 200
    repository.transaction(lambda state: state.project_teams["alpha-project"]["members"].pop("alpha-editor"))
    response = client.get("/api/v1/session?project_id=alpha-project", headers=headers)
    assert response.status_code == 404
    assert client.get("/api/v1/projects/alpha-project/workspace", headers=headers).status_code == 404


def test_current_volume_chapter_and_assembly_assignments_control_project_access(setup):
    client, repository = setup
    headers = login(client, "alpha-editor")
    def assignment(state):
        state.project_teams["alpha-project"]["owners"]["technical"] = "alpha-editor"
        state.project_teams["alpha-project"]["assembly_owner_id"] = "alpha-editor"
        state.chapters["alpha-business"].assignee_id = "alpha-manager"
    repository.transaction(assignment)
    response = client.get("/api/v1/session?project_id=alpha-project", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()["project_access"]
    assert not data["permissions"]["manage_project"]
    assert data["permissions"]["export_volumes"] == ["technical"]
    assert "project.export" in data["route_permissions"]
    chapters = {chapter["id"]: chapter["permissions"] for chapter in data["chapters"]}
    assert chapters["alpha-tech"]["edit"] and chapters["alpha-tech"]["manage_structure"]
    assert not chapters["alpha-business"]["edit"] and not chapters["alpha-business"]["manage_structure"]
    workspace = client.get("/api/v1/projects/alpha-project/workspace", headers=headers).json()
    assert data["permissions"] == workspace["permissions"]
    assert chapters == {chapter["id"]: chapter["permissions"] for chapter in workspace["chapters"]}


@pytest.mark.parametrize("remove_account", [False, True])
def test_revoked_token_or_account_is_rejected_on_next_request(setup, remove_account):
    client, repository = setup
    headers = login(client)
    token = headers["Authorization"].split()[1]
    repository.transaction(lambda state: state.accounts.pop("alpha-manager") if remove_account else state.sessions.pop(token))
    response = client.get("/api/v1/session", headers=headers)
    assert response.status_code == 401


def test_original_eight_role_navigation_definition_is_explicit_and_does_not_grant_platform_business_access():
    assert set(ROLE_NAVIGATION) == {"platform_admin", "group_admin", "company_admin", "data_admin",
                                    "project_lead", "bid_writer", "reviewer", "readonly"}
    platform = {item["route_id"] for item in navigation_for_roles(["platform_admin"])}
    assert platform == {"platform", "platform.audit", "platform.jobs"}
    for role in ("readonly", "reviewer"):
        routes = {item["route_id"] for item in navigation_for_roles([role])}
        assert "writing" not in routes and "admin" not in routes and "platform" not in routes
    assert all(item["access"] == "read" for item in navigation_for_roles(["group_admin"]))
    union = {item["route_id"]: item["access"] for item in navigation_for_roles(["bid_writer", "company_admin"])}
    assert union["writing"] == "write" and union["admin"] == "write"
    with pytest.raises(Exception) as raised:
        navigation_for_roles(["invented_admin"])
    assert raised.value.status == 403


def test_session_openapi_names_operation_and_declares_authentication_and_optional_project(setup):
    client, _ = setup
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/api/v1/session"]["get"]
    assert operation["operationId"] == "getSession"
    assert "requestBody" not in operation
    params = {item["name"]: item for item in operation["parameters"]}
    assert set(params) == {"project_id", "authorization"}
    assert params["project_id"]["required"] is False
    assert {"401", "403", "404", "422"}.issubset(operation["responses"])
    fields = schema["components"]["schemas"]["ApplicationSessionResponse"]["properties"]
    assert {"auth_mode", "role_mode", "user", "scope", "navigation", "allowedActions", "home_path", "session", "project_access"} == set(fields)
    assert "/{full_path:path}" not in schema["paths"]


def test_product_paths_serve_the_shell_and_unknown_api_stays_json(setup):
    client, _ = setup
    missing = client.get("/api/v1/does-not-exist")
    assert missing.status_code == 404
    assert missing.headers["content-type"].startswith("application/json")
    assert missing.json()["code"] == "NOT_FOUND"
    other = client.get("/api/demo/does-not-exist")
    assert other.status_code == 404
    assert (other.json().get("code") or other.json().get("error", {}).get("code")) == "NOT_FOUND"
    page = client.get("/workbench")
    index = Path(__file__).resolve().parents[2] / "frontend" / "web" / "dist" / "index.html"
    if index.is_file():
        assert page.status_code == 200
        assert page.headers["content-type"].startswith("text/html")
        assert "id=\"root\"" in page.text or "id='root'" in page.text
    else:
        assert page.status_code == 503
        assert (page.json().get("code") or page.json().get("error", {}).get("code")) == "UI_NOT_READY"
