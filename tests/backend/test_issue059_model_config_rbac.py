# 为什么有这个文件：登记 ISSUE-059 PM 最终权限模型的复现与回归。
# 它解决什么问题：模型配置 CRUD/密钥轮换/连通性测试严格仅限 platform_admin；
# 项目负责人与公司管理员对项目绑定已有合规模型（独立授权，只读候选列表绝不暴露明文密钥）。

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from test_demo import login

PRIVATE_URL = "http://192.168.10.50:8000"


@pytest.fixture
def secret_key(monkeypatch):
    from cryptography.fernet import Fernet
    from icg_demo.model_config_storage import ICG_SECRET_KEY_ENV
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv(ICG_SECRET_KEY_ENV, key)
    return key


@pytest.fixture
def client(secret_key):
    with TestClient(create_app()) as test_client:
        yield test_client


def _create(client, admin, config_id="cfg-rbac"):
    return client.post(
        "/api/v1/model-configs",
        headers=admin,
        json={"id": config_id, "name": "RBAC 验证模型", "base_url": PRIVATE_URL, "model": "qwen2.5-72b"},
    )


def test_company_admin_cannot_crud_only_platform_admin_can(client):
    """PM 最终模型：公司管理员 CRUD/轮换/测试一律 403；平台管理员全链路 200。"""
    company_admin = login(client, "alpha-company-admin")
    for method, path, payload in (
        ("post", "/api/v1/model-configs", {"id": "cfg-forbidden", "base_url": PRIVATE_URL}),
        ("get", "/api/v1/model-configs", None),
        ("get", "/api/v1/model-configs/cfg-rbac", None),
        ("put", "/api/v1/model-configs/cfg-rbac", {"name": "越权"}),
        ("post", "/api/v1/model-configs/cfg-rbac/test", None),
    ):
        response = getattr(client, method)(path, headers={**company_admin, "If-Match": "1"}, json=payload) if payload else getattr(client, method)(path, headers=company_admin)
        assert response.status_code == 403, (method, path, response.text)

    platform = login(client, "admin")
    created = _create(client, platform)
    assert created.status_code == 200, created.text
    assert created.json()["id"] == "cfg-rbac"
    read = client.get("/api/v1/model-configs/cfg-rbac", headers=platform)
    assert read.status_code == 200
    updated = client.put("/api/v1/model-configs/cfg-rbac", headers={**platform, "If-Match": "1"},
                         json={"name": "改名后"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["revision"] == 2
    listed = client.get("/api/v1/model-configs", headers=platform)
    assert listed.status_code == 200
    assert any(item["id"] == "cfg-rbac" for item in listed.json()["items"])


def test_platform_admin_rotates_key_and_manages_company_scoped_config(client):
    """在用/历史公司模型的密钥轮换同样严格仅限平台管理员；支持跨租户代管。"""
    platform = login(client, "admin")
    created = client.post("/api/v1/model-configs", headers=platform,
                          json={"id": "cfg-alpha-1", "company_id": "alpha", "base_url": PRIVATE_URL,
                                "api_key": "initial-secret-key-1"})
    assert created.status_code == 200, created.text

    def check_tenant(state):
        assert state.model_configs["cfg-alpha-1"].company_id == "alpha"

    client.app.state.service.repository.transaction(check_tenant)
    rotated = client.put("/api/v1/model-configs/cfg-alpha-1", headers={**platform, "If-Match": "1"},
                         json={"api_key": "rotated-secret-key-2"})
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["api_key_masked"] != created.json()["api_key_masked"]


def test_project_lead_binds_model_successfully(client):
    """项目负责人（alpha-manager 是 alpha-project 的 lead）可绑定平台代管的合规模型。"""
    platform = login(client, "admin")
    assert _create(client, platform).status_code == 200

    lead = login(client, "alpha-manager")
    bound = client.post("/api/v1/projects/alpha-project/model-config", headers=lead,
                        json={"model_config_id": "cfg-rbac"})
    assert bound.status_code == 200, bound.text
    assert bound.json()["model_config_id"] == "cfg-rbac"

    read = client.get("/api/v1/projects/alpha-project/model-config", headers=lead)
    assert read.status_code == 200
    assert read.json()["id"] == "cfg-rbac"


def test_bindable_options_readonly_and_key_safe(client):
    """项目负责人/公司管理员可读本项目绑定候选列表；普通成员 403；响应绝无明文密钥。"""
    platform = login(client, "admin")
    assert client.post("/api/v1/model-configs", headers=platform,
                       json={"id": "cfg-rbac", "base_url": PRIVATE_URL, "api_key": "super-secret-key-123"}).status_code == 200

    lead = login(client, "alpha-manager")
    options = client.get("/api/v1/projects/alpha-project/model-options", headers=lead)
    assert options.status_code == 200, options.text
    items = options.json()["items"]
    assert any(item["id"] == "cfg-rbac" for item in items)
    for item in items:
        assert "api_key" not in item and "encrypted_api_key" not in item

    company_admin = login(client, "alpha-company-admin")
    assert client.get("/api/v1/projects/alpha-project/model-options", headers=company_admin).status_code == 200

    editor = login(client, "alpha-editor")
    refused = client.get("/api/v1/projects/alpha-project/model-options", headers=editor)
    assert refused.status_code == 403


def test_plain_member_cannot_bind_or_manage(client):
    """普通成员（writer/readonly/未进项目）不能管理配置、不能绑定。"""
    platform = login(client, "admin")
    assert _create(client, platform).status_code == 200

    for account in ("alpha-editor", "alpha-viewer", "alpha-auditor"):
        member = login(client, account)
        created = client.post("/api/v1/model-configs", headers=member,
                              json={"id": f"cfg-evil-{account}", "base_url": "http://evil.example.com"})
        assert created.status_code == 403, f"{account} 不应能新建配置"
        updated = client.put("/api/v1/model-configs/cfg-rbac", headers={**member, "If-Match": "1"},
                             json={"base_url": "http://evil.example.com"})
        assert updated.status_code == 403, f"{account} 不应能修改配置"
        tested = client.post("/api/v1/model-configs/cfg-rbac/test", headers=member)
        assert tested.status_code == 403, f"{account} 不应能测试连通（探测内网）"

    editor = login(client, "alpha-editor")
    bound = client.post("/api/v1/projects/alpha-project/model-config", headers=editor,
                        json={"model_config_id": "cfg-rbac"})
    assert bound.status_code == 403
    assert bound.json()["code"] == "PROJECT_LEAD_REQUIRED"

    outsider = login(client, "alpha-outsider-manager")
    res = client.post("/api/v1/projects/alpha-project/model-config", headers=outsider,
                      json={"model_config_id": "cfg-rbac"})
    assert res.status_code in (403, 404)


def test_company_admin_can_bind(client):
    platform = login(client, "admin")
    assert _create(client, platform).status_code == 200
    admin = login(client, "alpha-company-admin")
    bound = client.post("/api/v1/projects/alpha-project/model-config", headers=admin,
                        json={"model_config_id": "cfg-rbac"})
    assert bound.status_code == 200, bound.text


def test_cross_company_member_cannot_bind_foreign_project(client):
    platform = login(client, "admin")
    assert _create(client, platform).status_code == 200
    beta = login(client, "beta-manager")
    res = client.post("/api/v1/projects/alpha-project/model-config", headers=beta,
                      json={"model_config_id": "cfg-rbac"})
    assert res.status_code in (403, 404), "跨公司绑定必须拒绝"
