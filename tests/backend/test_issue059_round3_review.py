# 为什么有这个文件：ISSUE-059 第三轮（Devin Review 复扫收口）可复现回归。
# 覆盖：绑定不得绕过公网过滤（CWE-200）、RAGFlow 平台继承两 Bug、绑定候选租户口径、任务路由平台池。

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from test_demo import login

PRIVATE_URL = "http://192.168.10.50:8000"
PUBLIC_URL = "https://api.public-cloud.example.com/v1"


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


def _mkcfg(client, platform, config_id, base_url, **extra):
    return client.post("/api/v1/model-configs", headers=platform,
                       json={"id": config_id, "base_url": base_url, **extra})


def test_public_endpoint_model_cannot_be_bound_even_for_non_sensitive_project(client):
    """CWE-200：非涉密项目绑定公网平台模型同样被拦截；候选列表也不含公网配置。"""
    platform = login(client, "admin")
    assert _mkcfg(client, platform, "cfg-pub", PUBLIC_URL, is_local=False, allow_sensitive=False).status_code == 200
    assert _mkcfg(client, platform, "cfg-priv", PRIVATE_URL).status_code == 200

    lead = login(client, "alpha-manager")
    bound = client.post("/api/v1/projects/alpha-project/model-config", headers=lead,
                        json={"model_config_id": "cfg-pub"})
    assert bound.status_code == 422, bound.text

    options = client.get("/api/v1/projects/alpha-project/model-options", headers=lead)
    ids = [item["id"] for item in options.json()["items"]]
    assert "cfg-pub" not in ids and "cfg-priv" in ids

    ok = client.post("/api/v1/projects/alpha-project/model-config", headers=lead,
                     json={"model_config_id": "cfg-priv"})
    assert ok.status_code == 200, ok.text


def test_platform_admin_binding_uses_project_tenant_pool(client):
    """平台超管（system 租户）代绑时候选池按项目所属公司计算。"""
    platform = login(client, "admin")
    assert _mkcfg(client, platform, "cfg-alpha-co", PRIVATE_URL, company_id="alpha").status_code == 200
    options = client.get("/api/v1/projects/alpha-project/model-options", headers=platform)
    assert options.status_code == 200, options.text
    ids = [item["id"] for item in options.json()["items"]]
    assert "cfg-alpha-co" in ids
    bound = client.post("/api/v1/projects/alpha-project/model-config", headers=platform,
                        json={"model_config_id": "cfg-alpha-co"})
    assert bound.status_code == 200, bound.text


def test_task_route_accepts_system_pool_and_rejects_public(client):
    """目录任务路由放行平台 system 池合规本地模型，拒绝公网端点。"""
    platform = login(client, "admin")
    assert _mkcfg(client, platform, "cfg-sys-local", PRIVATE_URL, is_local=True, allow_sensitive=True).status_code == 200
    assert _mkcfg(client, platform, "cfg-sys-pub", PUBLIC_URL, is_local=False, allow_sensitive=False).status_code == 200
    lead = login(client, "alpha-company-admin")
    routes = client.get("/api/v1/task-model-routes", headers=lead)
    rev = routes.json().get("revision", 0)
    ok = client.put("/api/v1/task-model-routes", headers={**lead, "If-Match": str(rev)},
                    json={"routes": [{"task": "technical_structure", "primary_config_id": "cfg-sys-local"}]})
    assert ok.status_code == 200, ok.text
    rev2 = ok.json().get("revision", 1)
    bad = client.put("/api/v1/task-model-routes", headers={**lead, "If-Match": str(rev2)},
                     json={"routes": [{"task": "technical_structure", "primary_config_id": "cfg-sys-pub"}]})
    assert bad.status_code in (409, 422), bad.text


def test_env_key_rotation_keeps_deployed_address_and_never_copies_env_key(client, monkeypatch):
    """带部署环境变量：仅换密钥保存保留实际生效地址；环境变量旧密钥绝不复制入库。"""
    monkeypatch.setenv("ICG_RAGFLOW_BASE_URL", "http://ragflow.internal:9380")
    monkeypatch.setenv("ICG_RAGFLOW_API_KEY", "rf-env-old-key")
    platform = login(client, "admin")
    read = client.get("/api/v1/ragflow-config", headers=platform)
    assert read.status_code == 200, read.text
    assert read.json()["base_url"] == "http://ragflow.internal:9380"
    rev = read.json()["revision"]
    saved = client.put("/api/v1/ragflow-config", headers={**platform, "If-Match": str(rev)},
                       json={"api_key": "rf-brand-new-key"})
    assert saved.status_code == 200, saved.text
    assert saved.json()["base_url"] == "http://ragflow.internal:9380"

    def check(state):
        row = state.ragflow_configs.get("system")
        assert row is not None and row.base_url == "http://ragflow.internal:9380"
        from icg.infra.model_config_storage import decrypt_api_key
        assert decrypt_api_key(row.encrypted_api_key) == "rf-brand-new-key"

    client.app.state.service.repository.transaction(check)


def test_disabled_platform_config_is_terminal_and_never_revives_env(client, monkeypatch):
    """平台显式停用后公司级检索不再连接环境变量旧实例。"""
    monkeypatch.setenv("ICG_RAGFLOW_BASE_URL", "http://ragflow.internal:9380")
    monkeypatch.setenv("ICG_RAGFLOW_API_KEY", "rf-env-old-key")
    service = client.app.state.service
    from icg.domain.ragflow_config import RagflowCompanyConfig

    def seed(state):
        state.ragflow_configs["system"] = RagflowCompanyConfig(
            company_id="system", base_url="http://ragflow.internal:9380", is_enabled=False)

    service.repository.transaction(seed)
    kb = service.knowledge_base
    assert kb.client_for("alpha") is None or not kb.enabled("alpha")
