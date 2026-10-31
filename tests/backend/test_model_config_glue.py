# 为什么有这个文件：覆盖 INT-MODEL-CONFIG-MODAL 大模型与 RAGFlow 弹窗配置前后端契约与路由胶水联调。
# 它解决什么问题：
# 1. 验证 /api/v1/model-configs/test 直接连通性测试与 /api/v1/model-configs/{id}/test 契约一致性；
# 2. 验证 /api/v1/ragflow/config 与 /api/v1/ragflow-config 双路由别名一致性（GET/PUT/POST test）；
# 3. 验证非演示模式下项目模型绑定（POST /api/v1/projects/{id}/model-config）；
# 4. 验证涉密项目（sensitive=True）绑定非本地模型时，严格返回符合 RFC 7807 标准的 403 阻断体（code="SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"）。

from __future__ import annotations

from cryptography.fernet import Fernet
import pytest
from fastapi.testclient import TestClient

from icg_demo.domain import Account, Principal
from icg_demo.main import create_app
from icg_demo.model_config_storage import ICG_SECRET_KEY_ENV
from test_demo import login


@pytest.fixture
def secret_key(monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv(ICG_SECRET_KEY_ENV, key)
    return key


@pytest.fixture
def client(secret_key):
    with TestClient(create_app()) as test_client:
        yield test_client


def test_model_configs_crud_and_direct_test_alias(client):
    """验证模型配置列表查询、新增与直接连通性测试别名 (POST /api/v1/model-configs/test)"""
    headers = login(client, "alpha-manager")

    # 1. 查询模型列表
    res_list = client.get("/api/v1/model-configs", headers=headers)
    assert res_list.status_code == 200
    data = res_list.json()
    assert "items" in data
    assert isinstance(data["items"], list)

    # 2. 创建一个测试模型配置
    cfg_payload = {
        "id": "cfg-glue-openai",
        "name": "联调测试模型",
        "provider": "openai-compatible",
        "base_url": "http://127.0.0.1:8000",
        "model": "qwen2.5-72b",
        "is_local": True,
        "allow_sensitive": True,
        "stream_enabled": True,
        "json_mode_enabled": False,
        "timeout_seconds": 30.0,
        "max_tokens": 4096,
    }
    res_create = client.post("/api/v1/model-configs", headers=login(client, "alpha-company-admin"), json=cfg_payload)
    assert res_create.status_code == 200
    created = res_create.json()
    assert created["id"] == "cfg-glue-openai"
    assert created["is_local"] is True
    assert created["allow_sensitive"] is True

    # 3. 通过 ID 测试连通性 (POST /api/v1/model-configs/{id}/test)
    res_test_id = client.post("/api/v1/model-configs/cfg-glue-openai/test", headers=login(client, "alpha-company-admin"))
    assert res_test_id.status_code == 200
    test_id_data = res_test_id.json()
    assert "ok" in test_id_data
    assert "duration_ms" in test_id_data

    # 4. 通过直接测试别名测试连通性 (POST /api/v1/model-configs/test)
    res_direct_test = client.post(
        "/api/v1/model-configs/test",
        headers=login(client, "alpha-company-admin"),
        json={"id": "cfg-glue-openai"},
    )
    assert res_direct_test.status_code == 200
    direct_data = res_direct_test.json()
    assert "ok" in direct_data
    assert "duration_ms" in direct_data


def test_ragflow_config_route_aliases(client):
    """验证 RAGFlow 配置在 /ragflow/config 与 /ragflow-config 双路由别名下的完全对称一致"""
    headers = login(client, "alpha-company-admin")

    # 1. 规范路由与别名路由 GET 返回一致
    res_canonical = client.get("/api/v1/ragflow-config", headers=headers)
    assert res_canonical.status_code == 200

    res_alias = client.get("/api/v1/ragflow/config", headers=headers)
    assert res_alias.status_code == 200
    assert res_canonical.json() == res_alias.json()

    # 2. 别名路由 PUT 更新配置
    etag = res_alias.headers.get("ETag") or f'"{res_alias.json()["revision"]}"'
    headers_put = {**headers, "If-Match": etag}
    res_alias_put = client.put(
        "/api/v1/ragflow/config",
        headers=headers_put,
        json={
            "base_url": "http://192.168.10.20:9380",
            "api_key": "ragflow-key-alias-test",
            "dataset_ids": ["ds_alias_1", "ds_alias_2"],
            "timeout_seconds": 35.0,
        },
    )
    assert res_alias_put.status_code == 200
    updated_alias = res_alias_put.json()
    assert updated_alias["base_url"] == "http://192.168.10.20:9380"
    assert updated_alias["has_api_key"] is True
    assert updated_alias["dataset_ids"] == ["ds_alias_1", "ds_alias_2"]

    # 3. 规范路径读回，验证已更新
    res_canonical_read = client.get("/api/v1/ragflow-config", headers=headers)
    assert res_canonical_read.status_code == 200
    assert res_canonical_read.json()["base_url"] == "http://192.168.10.20:9380"


def test_sensitive_project_model_binding_gate_and_rfc7807(client):
    """验证涉密项目模型绑定门禁及 RFC 7807 统一错误响应结构"""
    headers = login(client, "alpha-manager")

    # 1. 创建非本地模型（云端公网模型）
    client.post(
        "/api/v1/model-configs",
        headers=login(client, "alpha-company-admin"),
        json={
            "id": "cfg-cloud-external",
            "name": "云端公网推理服务",
            "provider": "openai-compatible",
            "base_url": "https://api.external-cloud.com/v1",
            "model": "cloud-gpt",
            "is_local": False,
            "allow_sensitive": False,
        },
    )

    # 2. 创建本地涉密模型
    client.post(
        "/api/v1/model-configs",
        headers=login(client, "alpha-company-admin"),
        json={
            "id": "cfg-local-secure",
            "name": "内网物理隔离本地 Qwen",
            "provider": "openai-compatible",
            "base_url": "http://192.168.1.50:8000",
            "model": "qwen2.5-72b",
            "is_local": True,
            "allow_sensitive": True,
        },
    )

    # 3. 创建普通项目，绑定云端模型应成功
    res_proj = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "普通公开招标项目"},
    )
    assert res_proj.status_code == 200
    normal_proj_id = res_proj.json()["id"]

    bind_normal = client.post(
        f"/api/v1/projects/{normal_proj_id}/model-config",
        headers=headers,
        json={"model_config_id": "cfg-cloud-external"},
    )
    assert bind_normal.status_code == 200
    assert bind_normal.json()["model_config_id"] == "cfg-cloud-external"

    # 读取绑定的模型配置
    read_bound = client.get(
        f"/api/v1/projects/{normal_proj_id}/model-config",
        headers=headers,
    )
    assert read_bound.status_code == 200
    assert read_bound.json()["id"] == "cfg-cloud-external"

    # 4. 创建涉密项目
    res_sensitive_proj = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "重点涉密军工通信项目"},
    )
    assert res_sensitive_proj.status_code == 200
    sensitive_proj_id = res_sensitive_proj.json()["id"]

    # 标记为 sensitive
    res_patch = client.patch(
        f"/api/v1/projects/{sensitive_proj_id}",
        headers={**headers, "If-Match": "1", "Idempotency-Key": "patch-glue-sensitive-01"},
        json={"sensitive": True},
    )
    assert res_patch.status_code == 200

    # 5. 涉密项目绑定非本地云端模型 -> 必须返回 403 阻断并符合 RFC 7807 契约
    res_blocked = client.post(
        f"/api/v1/projects/{sensitive_proj_id}/model-config",
        headers=headers,
        json={"model_config_id": "cfg-cloud-external"},
    )
    assert res_blocked.status_code == 403
    err_body = res_blocked.json()
    assert err_body["code"] == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"
    assert "敏感项目" in err_body["message"]
    # 验证统一错误体字段
    assert "traceId" in err_body or "request_id" in err_body
    assert "details" in err_body

    # 6. 涉密项目绑定本地涉密模型 -> 成功
    res_allowed = client.post(
        f"/api/v1/projects/{sensitive_proj_id}/model-config",
        headers=headers,
        json={"model_config_id": "cfg-local-secure"},
    )
    assert res_allowed.status_code == 200
    assert res_allowed.json()["model_config_id"] == "cfg-local-secure"

    # 7. 读取确认
    res_check = client.get(
        f"/api/v1/projects/{sensitive_proj_id}/model-config",
        headers=headers,
    )
    assert res_check.status_code == 200
    assert res_check.json()["id"] == "cfg-local-secure"
    assert res_check.json()["is_local"] is True
