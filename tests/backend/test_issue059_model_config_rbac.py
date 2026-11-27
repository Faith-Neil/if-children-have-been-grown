# 为什么有这个文件：登记 ISSUE-059(h) 恢复项目负责人绑定模型能力的复现与回归。
# 它解决什么问题：API 层曾用 require_platform_admin 一刀切，导致公司管理员不能 CRUD、
# 项目负责人不能绑定；服务层本就实现了精细授权（配置管理=公司/平台管理员，项目绑定=负责人或管理员）。
# 安全性保留：普通成员不能管理配置、不能绑定。

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from test_demo import login

PRIVATE_URL = "http://192.168.10.50:8000"


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


def _create(client, admin, config_id="cfg-rbac"):
    return client.post(
        "/api/v1/model-configs",
        headers=admin,
        json={"id": config_id, "name": "RBAC 验证模型", "base_url": PRIVATE_URL, "model": "qwen2.5-72b"},
    )


def test_company_admin_crud_roundtrip(client):
    admin = login(client, "alpha-company-admin")
    created = _create(client, admin)
    assert created.status_code == 200, created.text
    assert created.json()["id"] == "cfg-rbac"

    read = client.get("/api/v1/model-configs/cfg-rbac", headers=admin)
    assert read.status_code == 200

    updated = client.put("/api/v1/model-configs/cfg-rbac", headers={**admin, "If-Match": "1"},
                         json={"name": "改名后"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["revision"] == 2

    listed = client.get("/api/v1/model-configs", headers=admin)
    assert listed.status_code == 200
    assert any(item["id"] == "cfg-rbac" for item in listed.json()["items"])


def test_project_lead_binds_model_successfully(client):
    """项目负责人（alpha-manager 是 alpha-project 的 lead）可以绑定，修复前被一刀切 403。"""
    admin = login(client, "alpha-company-admin")
    assert _create(client, admin).status_code == 200

    lead = login(client, "alpha-manager")
    bound = client.post("/api/v1/projects/alpha-project/model-config", headers=lead,
                        json={"model_config_id": "cfg-rbac"})
    assert bound.status_code == 200, bound.text
    assert bound.json()["model_config_id"] == "cfg-rbac"

    read = client.get("/api/v1/projects/alpha-project/model-config", headers=lead)
    assert read.status_code == 200
    assert read.json()["id"] == "cfg-rbac"


def test_plain_member_cannot_bind_or_manage(client):
    """普通成员（writer/readonly/未进项目）不能管理配置、不能绑定。"""
    admin = login(client, "alpha-company-admin")
    assert _create(client, admin).status_code == 200

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

    # 项目编写人（非负责人）不能绑定
    editor = login(client, "alpha-editor")
    bound = client.post("/api/v1/projects/alpha-project/model-config", headers=editor,
                        json={"model_config_id": "cfg-rbac"})
    assert bound.status_code == 403
    assert bound.json()["code"] == "PROJECT_LEAD_REQUIRED"

    # 不是本项目成员的普通成员也不能绑定
    outsider = login(client, "alpha-outsider-manager")
    res = client.post("/api/v1/projects/alpha-project/model-config", headers=outsider,
                      json={"model_config_id": "cfg-rbac"})
    assert res.status_code in (403, 404)


def test_company_admin_can_bind(client):
    admin = login(client, "alpha-company-admin")
    assert _create(client, admin).status_code == 200
    bound = client.post("/api/v1/projects/alpha-project/model-config", headers=admin,
                        json={"model_config_id": "cfg-rbac"})
    assert bound.status_code == 200, bound.text


def test_platform_admin_manages_own_system_configs(client):
    """平台超级管理员可管理平台（system）侧配置，但仍受租户边界约束。"""
    platform = login(client, "admin")
    created = client.post("/api/v1/model-configs", headers=platform,
                          json={"id": "cfg-system-1", "name": "平台侧模型", "base_url": PRIVATE_URL})
    assert created.status_code == 200, created.text
    read = client.get("/api/v1/model-configs/cfg-system-1", headers=platform)
    assert read.status_code == 200


def test_cross_company_member_cannot_bind_foreign_project(client):
    admin = login(client, "alpha-company-admin")
    assert _create(client, admin).status_code == 200
    beta = login(client, "beta-manager")
    res = client.post("/api/v1/projects/alpha-project/model-config", headers=beta,
                      json={"model_config_id": "cfg-rbac"})
    assert res.status_code in (403, 404), "跨公司绑定必须拒绝"
