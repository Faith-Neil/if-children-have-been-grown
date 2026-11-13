# 为什么有这个文件：验收 ISSUE-052 公司开通与租户隔离。
# 它解决什么问题：证明平台管理员可一次开通公司并创建首个公司管理员；公司管理员不能开通；冲突与弱密码被拒。

from fastapi.testclient import TestClient

from test_reference_flow import client, login  # noqa: F401


def test_platform_admin_creates_company_and_first_admin(client: TestClient):
    headers = login(client, "platform-admin")
    res = client.post("/api/v1/companies", headers=headers, json={
        "name": "合成华北智造有限公司",
        "admin_username": "huabei-admin",
        "admin_name": "李开通",
        "admin_password": "Init_Pass_2026",
        "must_change_password": True,
    })
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["company"]["name"] == "合成华北智造有限公司"
    assert body["company"]["status"] == "active"
    assert body["company"]["id"].startswith("co-")
    assert len(body["company"]["id"]) == 11  # co- + 8 hex
    assert body["admin"]["id"] == "huabei-admin"
    assert body["admin"]["role"] == "company_admin"
    assert body["admin"]["company_id"] == body["company"]["id"]
    assert body["admin"]["must_change_password"] is True


def test_company_admin_cannot_create_company(client: TestClient):
    headers = login(client, "alpha-company-admin")
    res = client.post("/api/v1/companies", headers=headers, json={
        "name": "不该出现的公司",
        "admin_username": "nope-admin",
        "admin_name": "无",
        "admin_password": "Init_Pass_2026",
    })
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


def test_create_company_rejects_duplicate_display_name(client: TestClient):
    headers = login(client, "platform-admin")
    first = client.post("/api/v1/companies", headers=headers, json={
        "name": "合成重名探测公司",
        "admin_username": "dup-name-admin",
        "admin_name": "甲",
        "admin_password": "Init_Pass_2026",
    })
    assert first.status_code == 201, first.text
    again = client.post("/api/v1/companies", headers=headers, json={
        "name": "合成重名探测公司",
        "admin_username": "dup-name-admin-2",
        "admin_name": "乙",
        "admin_password": "Init_Pass_2026",
    })
    assert again.status_code == 409
    assert again.json()["code"] == "COMPANY_NAME_DUPLICATED"


def test_create_company_rejects_weak_password(client: TestClient):
    headers = login(client, "platform-admin")
    res = client.post("/api/v1/companies", headers=headers, json={
        "name": "合成弱密公司",
        "admin_username": "weak-admin",
        "admin_name": "弱",
        "admin_password": "short1",
    })
    assert res.status_code == 422
    assert res.json()["code"] == "PASSWORD_WEAK"


def test_create_company_must_change_password_false_allows_work(client: TestClient):
    headers = login(client, "platform-admin")
    created = client.post("/api/v1/companies", headers=headers, json={
        "name": "合成免改密公司",
        "admin_username": "nochg-admin",
        "admin_name": "免改",
        "admin_password": "Init_Pass_2026",
        "must_change_password": False,
    })
    assert created.status_code == 201, created.text
    assert created.json()["admin"]["must_change_password"] is False
    logged = client.post("/api/v1/auth/login", json={"username": "nochg-admin", "password": "Init_Pass_2026"})
    assert logged.status_code == 200, logged.text
    assert logged.json()["must_change_password"] is False
    projects = client.get(
        "/api/v1/projects",
        headers={"Authorization": "Bearer " + logged.json()["access_token"]},
    )
    assert projects.status_code == 200, projects.text


def test_two_provisioned_companies_cannot_see_each_others_projects(client: TestClient):
    admin = login(client, "platform-admin")
    a = client.post("/api/v1/companies", headers=admin, json={
        "name": "隔离公司甲", "admin_username": "iso-a-admin", "admin_name": "甲",
        "admin_password": "Init_Pass_2026", "must_change_password": False,
    })
    assert a.status_code == 201, a.text
    b = client.post("/api/v1/companies", headers=admin, json={
        "name": "隔离公司乙", "admin_username": "iso-b-admin", "admin_name": "乙",
        "admin_password": "Init_Pass_2026", "must_change_password": False,
    })
    assert b.status_code == 201, b.text
    token_a = client.post("/api/v1/auth/login", json={"username": "iso-a-admin", "password": "Init_Pass_2026"}).json()["access_token"]
    token_b = client.post("/api/v1/auth/login", json={"username": "iso-b-admin", "password": "Init_Pass_2026"}).json()["access_token"]
    created = client.post("/api/v1/projects", headers={"Authorization": f"Bearer {token_a}"},
                          json={"name": "甲公司机密项目"})
    assert created.status_code in (200, 201), created.text
    pid = created.json()["id"]
    list_b = client.get("/api/v1/projects", headers={"Authorization": f"Bearer {token_b}"})
    assert list_b.status_code == 200, list_b.text
    projects = list_b.json().get("projects", [])
    assert all(p["id"] != pid for p in projects)
    other = client.get(f"/api/v1/projects/{pid}", headers={"Authorization": f"Bearer {token_b}"})
    assert other.status_code == 404


def test_create_user_respects_must_change_password_false(client: TestClient):
    admin = login(client, "platform-admin")
    created_co = client.post("/api/v1/companies", headers=admin, json={
        "name": "合成改密可选公司",
        "admin_username": "opt-admin",
        "admin_name": "管",
        "admin_password": "Init_Pass_2026",
        "must_change_password": False,
    })
    assert created_co.status_code == 201, created_co.text
    cid = created_co.json()["company"]["id"]
    res = client.post("/api/v1/users", headers=admin, json={
        "username": "opt-member",
        "name": "员",
        "company_id": cid,
        "role": "member",
        "password": "Init_Pass_2026",
        "must_change_password": False,
    })
    assert res.status_code in (200, 201), res.text
    assert res.json()["must_change_password"] is False
    login_res = client.post("/api/v1/auth/login", json={"username": "opt-member", "password": "Init_Pass_2026"})
    assert login_res.status_code == 200, login_res.text
    assert login_res.json()["must_change_password"] is False
    projects = client.get(
        "/api/v1/projects",
        headers={"Authorization": "Bearer " + login_res.json()["access_token"]},
    )
    assert projects.status_code == 200, projects.text
