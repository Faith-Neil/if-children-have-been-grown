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


def test_task_route_runtime_uses_system_pool_saved_by_company_admin(client):
    """保存与运行时同一归属口径：公司路由显式选择 system 池后不得静默回落。"""
    platform = login(client, "admin")
    assert _mkcfg(client, platform, "cfg-sys-runtime", PRIVATE_URL, is_local=True, allow_sensitive=True).status_code == 200
    company_admin = login(client, "alpha-company-admin")
    routes = client.get("/api/v1/task-model-routes", headers=company_admin)
    rev = routes.json().get("revision", 0)
    saved = client.put("/api/v1/task-model-routes", headers={**company_admin, "If-Match": str(rev)},
                       json={"routes": [{"task": "technical_structure", "primary_config_id": "cfg-sys-runtime"}]})
    assert saved.status_code == 200, saved.text
    service = client.app.state.service
    state = service.repository.read()
    provider = service.resolve_model_provider(state, "alpha-project", "technical_structure")
    assert getattr(provider, "is_real_model", False) is True
    assert getattr(provider, "_config").base_url == PRIVATE_URL


def test_first_ragflow_save_with_inherited_mask_does_not_encrypt_mask(client, monkeypatch):
    """首次保存沿用部署密钥掩码时不得把掩码覆写成新密钥。"""
    monkeypatch.setenv("ICG_RAGFLOW_BASE_URL", "http://ragflow.internal:9380")
    monkeypatch.setenv("ICG_RAGFLOW_API_KEY", "rf-env-secret-1234")
    platform = login(client, "admin")
    read = client.get("/api/v1/ragflow-config", headers=platform)
    assert read.status_code == 200, read.text
    masked = read.json()["api_key_masked"]
    saved = client.put("/api/v1/ragflow-config", headers={**platform, "If-Match": str(read.json()["revision"])},
                       json={"api_key": masked, "timeout_seconds": 33})
    assert saved.status_code == 200, saved.text

    def check(state):
        row = state.ragflow_configs.get("system")
        assert row is not None
        assert row.encrypted_api_key is None, "环境密钥掩码不得被加密保存成新密钥"
        assert row.api_key_masked is None

    client.app.state.service.repository.transaction(check)
    effective = client.app.state.service.knowledge_base.client_for("system")
    assert effective is not None and effective._config.base_url == "http://ragflow.internal:9380"


def test_disabled_platform_ragflow_blocks_inherited_dataset_write(client):
    """CWE-863：平台停用后，继承平台连接的公司不得再用平台密钥创建数据集。"""
    service = client.app.state.service
    from icg.domain.ragflow_config import RagflowCompanyConfig
    from icg.infra.model_config_storage import encrypt_api_key, mask_api_key

    def seed(state):
        state.ragflow_configs["system"] = RagflowCompanyConfig(
            company_id="system", base_url="http://ragflow.internal:9380",
            encrypted_api_key=encrypt_api_key("rf-platform-secret"),
            api_key_masked=mask_api_key("rf-platform-secret"), is_enabled=False)

    service.repository.transaction(seed)
    company_admin = login(client, "alpha-company-admin")
    result = client.post("/api/v1/ragflow/datasets", headers=company_admin, json={"name": "blocked"})
    assert result.status_code == 409, result.text
    assert result.json()["code"] == "KNOWLEDGE_BASE_NOT_CONFIGURED"


def test_assistant_public_model_rejection_is_403_not_500(client):
    """显式绑定公网模型时，对话助手 HTTP 路由返回冻结的 403 业务错误。"""
    service = client.app.state.service
    from icg.infra.model_config_storage import ModelConfig

    def seed(state):
        state.model_configs["cfg-assistant-public"] = ModelConfig(
            id="cfg-assistant-public", company_id="alpha", name="公网模型", provider="openai-compatible",
            base_url=PUBLIC_URL, model="public-model", is_local=False, allow_sensitive=False)
        state.project_model_configs["alpha-project"] = "cfg-assistant-public"

    service.repository.transaction(seed)
    writer = login(client, "alpha-editor")
    result = client.post("/api/v1/projects/alpha-project/chapters/alpha-tech/assistant-questions/stream",
                         headers=writer, json={"question": "这一章还需要补什么？", "knowledge_base_enabled": False})
    assert result.status_code == 403, result.text
    assert result.json()["code"] == "PUBLIC_MODEL_ENDPOINT_FORBIDDEN"
    assert "内网模型" in result.json()["message"]


def test_explicit_blank_ragflow_key_is_cleared_and_does_not_fall_back_to_env(client, monkeypatch):
    """显式 api_key="" 是清除态：不得重新继承 ICG_RAGFLOW_API_KEY。"""
    monkeypatch.setenv("ICG_RAGFLOW_BASE_URL", "http://ragflow.internal:9380")
    monkeypatch.setenv("ICG_RAGFLOW_API_KEY", "rf-env-secret-1234")
    platform = login(client, "admin")
    read = client.get("/api/v1/ragflow-config", headers=platform)
    saved = client.put("/api/v1/ragflow-config", headers={**platform, "If-Match": str(read.json()["revision"])},
                       json={"api_key": "", "timeout_seconds": 90})
    assert saved.status_code == 200, saved.text
    service = client.app.state.service
    state = service.repository.read()
    row = state.ragflow_configs["system"]
    assert row.encrypted_api_key is None and row.api_key_cleared is True
    from icg.domain.ragflow_config import effective_ragflow_connection
    effective = effective_ragflow_connection(state, "system")
    assert effective is not None and effective.encrypted_api_key is None
    assert service.knowledge_base.client_for("system") is None


def test_inherited_ragflow_key_uses_saved_timeout_when_only_timeout_changes(client, monkeypatch):
    """省略密钥仅改超时：继续继承部署密钥，并把持久化超时合并到最终连接。"""
    monkeypatch.setenv("ICG_RAGFLOW_BASE_URL", "http://ragflow.internal:9380")
    monkeypatch.setenv("ICG_RAGFLOW_API_KEY", "rf-env-secret-1234")
    platform = login(client, "admin")
    read = client.get("/api/v1/ragflow-config", headers=platform)
    saved = client.put("/api/v1/ragflow-config", headers={**platform, "If-Match": str(read.json()["revision"])},
                       json={"timeout_seconds": 90})
    assert saved.status_code == 200, saved.text
    service = client.app.state.service
    state = service.repository.read()
    row = state.ragflow_configs["system"]
    assert row.encrypted_api_key is None and row.api_key_cleared is False
    client_obj = service.knowledge_base.client_for("system")
    assert client_obj is not None
    assert client_obj._config.base_url == "http://ragflow.internal:9380"
    assert client_obj._config.timeout_seconds == 90
    assert client_obj._config.api_key == "rf-env-secret-1234"
    inherited_company_client = service.knowledge_base.client_for("alpha")
    assert inherited_company_client is not None
    assert inherited_company_client._config.timeout_seconds == 90
    assert inherited_company_client._config.api_key == "rf-env-secret-1234"
