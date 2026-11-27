# 为什么有这个文件：ISSUE-059 第二轮（PM 裁定/Devin Review）纵深防御修复的可复现回归。
# 覆盖：CWE-639 跨租户覆写、CWE-522 改地址携带旧密钥、CWE-862 知识库写授权、
# CWE-918 SSRF 端点校验、RAGFlow 部署默认值不落盘回归。

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


# ---------- CWE-639：跨租户覆写 ----------

def test_create_rejects_globally_duplicate_config_id(client):
    """任何租户已占用的模型 ID 都拒绝新建，杜绝覆写其他租户配置。"""
    platform = login(client, "admin")
    first = client.post("/api/v1/model-configs", headers=platform,
                        json={"id": "cfg-shared-id", "company_id": "alpha", "base_url": PRIVATE_URL})
    assert first.status_code == 200, first.text
    # 同 ID 即使指定不同公司也必须是 409，而不是悄悄覆盖 alpha 的行
    duplicate = client.post("/api/v1/model-configs", headers=platform,
                            json={"id": "cfg-shared-id", "company_id": "beta", "base_url": "http://192.168.10.99:8000"})
    assert duplicate.status_code == 409, duplicate.text

    def check(state):
        assert state.model_configs["cfg-shared-id"].company_id == "alpha"
        assert state.model_configs["cfg-shared-id"].base_url == PRIVATE_URL

    client.app.state.service.repository.transaction(check)


def test_update_cannot_reassign_tenant_ownership(client):
    platform = login(client, "admin")
    assert client.post("/api/v1/model-configs", headers=platform,
                       json={"id": "cfg-owned", "company_id": "alpha", "base_url": PRIVATE_URL}).status_code == 200
    moved = client.put("/api/v1/model-configs/cfg-owned", headers={**platform, "If-Match": "1"},
                       json={"company_id": "beta"})
    assert moved.status_code == 422, moved.text


def test_mysql_scoped_update_refuses_cross_tenant_row():
    """持久层纵深：UPDATE 必须带 company_id 归属约束。"""
    import inspect
    from icg.infra.repositories import model_config as repo
    source = inspect.getsource(repo.save_model_configs)
    assert "WHERE id = :id AND company_id = :company_id" in source
    assert "rowcount" in source


# ---------- CWE-522：改地址禁止携带旧密钥 ----------

def test_ragflow_base_url_change_requires_explicit_key(client):
    platform = login(client, "admin")
    read = client.get("/api/v1/ragflow-config", headers=platform)
    rev = read.json()["revision"]
    seeded = client.put("/api/v1/ragflow-config", headers={**platform, "If-Match": str(rev)},
                        json={"base_url": "http://192.168.20.10:9380", "api_key": "rf-key-original-01"})
    assert seeded.status_code == 200, seeded.text
    rev2 = seeded.json()["revision"]

    # 改地址不带新密钥 → 422；掩码回传也不算显式凭证
    masked = seeded.json()["api_key_masked"]
    refused = client.put("/api/v1/ragflow-config", headers={**platform, "If-Match": str(rev2)},
                         json={"base_url": "http://192.168.20.99:9380"})
    assert refused.status_code == 422, refused.text
    refused_mask = client.put("/api/v1/ragflow-config", headers={**platform, "If-Match": str(rev2)},
                              json={"base_url": "http://192.168.20.99:9380", "api_key": masked})
    assert refused_mask.status_code == 422, refused_mask.text

    # 改地址 + 显式新密钥 → 200
    rotated = client.put("/api/v1/ragflow-config", headers={**platform, "If-Match": str(rev2)},
                         json={"base_url": "http://192.168.20.99:9380", "api_key": "rf-key-new-instance-02"})
    assert rotated.status_code == 200, rotated.text
    rev3 = rotated.json()["revision"]

    # 改地址 + 显式空串清除 → 200 且无密钥
    cleared = client.put("/api/v1/ragflow-config", headers={**platform, "If-Match": str(rev3)},
                         json={"base_url": "http://192.168.20.10:9380", "api_key": ""})
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["has_api_key"] is False
    rev4 = cleared.json()["revision"]

    # 地址不变时密钥留空不改（原语义保留）
    same = client.put("/api/v1/ragflow-config", headers={**platform, "If-Match": str(rev4)},
                      json={"timeout_seconds": 45.0})
    assert same.status_code == 200, same.text


# ---------- CWE-862：知识库写授权 ----------

def test_dataset_create_and_kb_sync_require_admin_role(client):
    for account in ("alpha-editor", "alpha-viewer"):
        member = login(client, account)
        created = client.post("/api/v1/ragflow/datasets", headers=member, json={"name": "evil-dataset"})
        assert created.status_code == 403, (account, created.text)
        synced = client.post("/api/v1/ragflow/sync", headers=member, json={"snippet_id": "sn-any"})
        assert synced.status_code == 403, (account, synced.text)


# ---------- CWE-918：SSRF 端点校验 ----------

def test_model_config_rejects_non_http_and_userinfo_urls(client):
    platform = login(client, "admin")
    for bad_url in ("file:///etc/passwd", "ftp://192.168.1.1/x", "http://user@evil.example.com/v1", "not-a-url"):
        refused = client.post("/api/v1/model-configs", headers=platform,
                              json={"id": f"cfg-ssrf-{abs(hash(bad_url))}", "base_url": bad_url})
        assert refused.status_code == 422, (bad_url, refused.text)


def test_ragflow_update_rejects_non_http_urls(client):
    platform = login(client, "admin")
    read = client.get("/api/v1/ragflow-config", headers=platform)
    rev = read.json()["revision"]
    refused = client.put("/api/v1/ragflow-config", headers={**platform, "If-Match": str(rev)},
                         json={"base_url": "file:///etc/passwd", "api_key": "any"})
    assert refused.status_code == 422, refused.text


# ---------- 部署默认值不落盘回归 ----------

def test_env_default_not_persisted_and_platform_update_takes_over(client, monkeypatch):
    """带部署环境变量 → 读公司配置不落盘默认 → 平台配置更新后公司立即生效新平台配置。"""
    from icg.domain.ragflow_config import RagflowCompanyConfig
    from icg.infra.model_config_storage import encrypt_api_key, mask_api_key

    monkeypatch.setenv("ICG_RAGFLOW_BASE_URL", "http://192.168.30.10:9380")
    monkeypatch.setenv("ICG_RAGFLOW_API_KEY", "rf-deploy-env-key")
    service = client.app.state.service

    # 1. 消费路径回落到部署默认（运行时生效）
    kb = service.knowledge_base
    client_obj = kb.client_for("alpha")
    assert client_obj is not None
    assert client_obj._config.base_url == "http://192.168.30.10:9380"

    # 2. 读取/消费之后，部署默认值绝不能被持久化进公司配置行
    def check_row(state):
        row = state.ragflow_configs.get("alpha")
        assert row is None or not row.encrypted_api_key, "部署默认密钥不得写入公司配置行"

    service.repository.transaction(check_row)

    # 3. 平台管理员写入 platform(system) 配置后，公司立即生效新平台配置
    def seed_platform(state):
        state.ragflow_configs["system"] = RagflowCompanyConfig(
            company_id="system", base_url="http://192.168.30.99:9380",
            encrypted_api_key=encrypt_api_key("rf-platform-new-key"),
            api_key_masked=mask_api_key("rf-platform-new-key"),
        )

    service.repository.transaction(seed_platform)
    client_obj2 = kb.client_for("alpha")
    assert client_obj2 is not None
    assert client_obj2._config.base_url == "http://192.168.30.99:9380"
