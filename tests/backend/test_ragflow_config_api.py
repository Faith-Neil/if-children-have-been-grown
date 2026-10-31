# 为什么有这个文件：自动化测试租户级 RAGFlow 知识库配置的 GET/PUT/test 接口及多租户强隔离。
# 它解决什么问题：验证密钥加密、掩码保护、If-Match 乐观锁并发保护与健康检测端点，杜绝机密泄露与跨租户越权。

from __future__ import annotations

from cryptography.fernet import Fernet
import pytest
from fastapi.testclient import TestClient

from fake_ragflow import FakeRagflow
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


def test_get_ragflow_config_default_isolation(client):
    # Alpha 公司管理员登录
    headers_alpha = login(client, "alpha-manager")
    res_alpha = client.get("/api/v1/ragflow-config", headers=headers_alpha)
    assert res_alpha.status_code == 200
    data_alpha = res_alpha.json()
    assert data_alpha["company_id"] == "alpha"
    assert "api_key" not in data_alpha
    assert data_alpha["has_api_key"] is False
    assert data_alpha["is_enabled"] is True
    assert data_alpha["revision"] == 1

    # Beta 公司成员登录
    headers_beta = login(client, "beta-editor")
    res_beta = client.get("/api/v1/ragflow-config", headers=headers_beta)
    assert res_beta.status_code == 200
    data_beta = res_beta.json()
    assert data_beta["company_id"] == "beta"
    assert data_beta["revision"] == 1


def test_update_ragflow_config_with_optimistic_lock_and_encryption(client):
    headers = login(client, "alpha-company-admin")

    # 1. 未提供 If-Match 触发 428
    res_no_if_match = client.put(
        "/api/v1/ragflow-config",
        json={"base_url": "http://127.0.0.1:9380", "api_key": "ragflow-sec-alpha-999"},
        headers=headers,
    )
    assert res_no_if_match.status_code == 428

    # 2. 正常带 If-Match: "1" 更新并设置密钥
    headers_match_1 = {**headers, "If-Match": '"1"'}
    res_ok = client.put(
        "/api/v1/ragflow-config",
        json={
            "base_url": "http://192.168.1.100:9380",
            "api_key": "ragflow-key-alpha-xyz",
            "dataset_ids": ["ds_alpha_knowledge", "ds_alpha_cases"],
            "timeout_seconds": 45.0,
        },
        headers=headers_match_1,
    )
    assert res_ok.status_code == 200
    updated = res_ok.json()
    assert updated["base_url"] == "http://192.168.1.100:9380"
    assert updated["has_api_key"] is True
    assert updated["api_key_masked"] == "rag***-xyz"
    assert updated["dataset_ids"] == ["ds_alpha_knowledge", "ds_alpha_cases"]
    assert updated["timeout_seconds"] == 45.0
    assert updated["revision"] == 2
    assert res_ok.headers.get("ETag") == '"2"'

    # 3. 版本号冲突 If-Match: "1" 再次提交触发 409
    res_conflict = client.put(
        "/api/v1/ragflow-config",
        json={"timeout_seconds": 50.0},
        headers=headers_match_1,
    )
    assert res_conflict.status_code == 409

    # 4. 传回掩码保留原密钥
    headers_match_2 = {**headers, "If-Match": '"2"'}
    res_keep_mask = client.put(
        "/api/v1/ragflow-config",
        json={"api_key": updated["api_key_masked"], "timeout_seconds": 60.0},
        headers=headers_match_2,
    )
    assert res_keep_mask.status_code == 200
    keep_data = res_keep_mask.json()
    assert keep_data["has_api_key"] is True
    assert keep_data["api_key_masked"] == "rag***-xyz"
    assert keep_data["revision"] == 3


def test_test_ragflow_connectivity(client, fake_ragflow):
    headers = login(client, "alpha-company-admin")

    # 执行连通性测试，指向 FakeRagflow 服务地址
    res = client.post(
        "/api/v1/ragflow-config/test",
        json={"base_url": fake_ragflow.base_url},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["message"] == "连接成功"
    assert data["health"].get("status") == "ok"
    assert data["duration_ms"] >= 0
