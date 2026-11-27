# 为什么有这个文件：登记 ISSUE-059(g) 平台级 RAGFlow 配置对下属公司生效的复现与回归。
# 它解决什么问题：
# 1. 公司未完成配置（无密钥）时正确回落平台 system 配置（端点/密钥/超时）；
# 2. 公司级有自己的配置时公司级优先；公司显式停用不回落；
# 3. 数据集列表永远按公司隔离（${company_id}:: 前缀语义不变），密钥绝不跨端点错配。

from __future__ import annotations

from cryptography.fernet import Fernet
import pytest
from fastapi.testclient import TestClient

from icg.infra.memory_repository import MemoryRepository
from icg.domain.domain import DemoService
from icg.infra.adapters import DemoModelProvider
from icg.domain.knowledge_base import KnowledgeBaseService
from icg.domain.ragflow_config import (
    RagflowCompanyConfig,
    RagflowConfigService,
    effective_ragflow_connection,
)
from icg.infra.model_config_storage import encrypt_api_key
from icg_demo.main import create_app
from test_demo import login

PLATFORM_URL = "http://192.168.20.10:9380"
COMPANY_URL = "http://192.168.30.20:9380"


@pytest.fixture
def secret_key(monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("ICG_SECRET_KEY", key)
    return key


@pytest.fixture
def client(secret_key):
    with TestClient(create_app()) as test_client:
        yield test_client


def _service():
    return DemoService(MemoryRepository(), DemoModelProvider())


def _platform_config(**overrides):
    values = dict(
        company_id="system",
        base_url=PLATFORM_URL,
        encrypted_api_key=encrypt_api_key("rf-platform-key"),
        api_key_masked="rf-***-key",
        dataset_ids=["dataset-system-01"],
        timeout_seconds=45.0,
        is_enabled=True,
    )
    values.update(overrides)
    return RagflowCompanyConfig(**values)


def _seed(state, *configs):
    for cfg in configs:
        state.ragflow_configs[cfg.company_id] = cfg


# ---------------------------------------------------------------------------
# 1. 回落语义（领域层）
# ---------------------------------------------------------------------------

def test_company_without_key_falls_back_to_platform(secret_key):
    service = _service()

    def op(s):
        _seed(s, _platform_config())

    service.repository.transaction(op)
    state = service.repository.read()
    effective = effective_ragflow_connection(state, "alpha")
    assert effective is not None
    assert effective.base_url == PLATFORM_URL
    assert effective.company_id == "alpha", "回落必须保持公司租户身份"
    assert effective.dataset_ids == ["dataset-alpha-01"], "数据集必须保留公司自己的隔离空间"
    assert effective.timeout_seconds == 45.0


def test_company_own_config_wins_over_platform(secret_key):
    service = _service()

    def op(s):
        _seed(
            s,
            _platform_config(),
            RagflowCompanyConfig(
                company_id="alpha",
                base_url=COMPANY_URL,
                encrypted_api_key=encrypt_api_key("rf-company-key"),
                api_key_masked="rf-***-key",
                dataset_ids=["ds-alpha-own"],
                timeout_seconds=20.0,
            ),
        )

    service.repository.transaction(op)
    effective = effective_ragflow_connection(service.repository.read(), "alpha")
    assert effective.base_url == COMPANY_URL, "公司级有自己的配置时公司级优先"
    assert effective.timeout_seconds == 20.0
    assert effective.dataset_ids == ["ds-alpha-own"]


def test_company_explicit_disable_is_not_overridden_by_platform(secret_key):
    service = _service()

    def op(s):
        _seed(
            s,
            _platform_config(),
            RagflowCompanyConfig(company_id="alpha", base_url=COMPANY_URL, is_enabled=False),
        )

    service.repository.transaction(op)
    effective = effective_ragflow_connection(service.repository.read(), "alpha")
    assert effective is not None and effective.is_enabled is False
    assert effective.base_url == COMPANY_URL, "显式停用不得被平台配置覆盖"


def test_platform_disabled_or_keyless_means_no_fallback(secret_key):
    service = _service()

    def op(s):
        _seed(s, _platform_config(is_enabled=False))

    service.repository.transaction(op)
    tenant = RagflowCompanyConfig(company_id="alpha")
    state = service.repository.read()
    state.ragflow_configs["alpha"] = tenant
    # PM 第三轮裁定：平台显式停用是解析终态——公司侧同样停用，严禁落入环境变量分支复活旧实例
    effective = effective_ragflow_connection(state, "alpha")
    assert effective is not None and effective.is_enabled is False


def test_platform_config_itself_returned_for_system(secret_key):
    service = _service()

    def op(s):
        _seed(s, _platform_config())

    service.repository.transaction(op)
    effective = effective_ragflow_connection(service.repository.read(), "system")
    assert effective is not None and effective.company_id == "system"
    assert effective.dataset_ids == ["dataset-system-01"]


# ---------------------------------------------------------------------------
# 2. 消费路径：知识库 client_for 与 RagflowConfigService.get_client
# ---------------------------------------------------------------------------

def test_knowledge_base_client_uses_platform_fallback(secret_key):
    service = _service()
    kb = KnowledgeBaseService(service)

    def op(s):
        _seed(s, _platform_config())

    service.repository.transaction(op)
    client_obj = kb.client_for("alpha")
    assert client_obj is not None, "仅平台配置时公司知识库必须可用"
    assert client_obj._config.base_url == PLATFORM_URL
    assert kb.enabled("alpha") is True


def test_knowledge_base_client_prefers_company_config(secret_key):
    service = _service()
    kb = KnowledgeBaseService(service)

    def op(s):
        _seed(
            s,
            _platform_config(),
            RagflowCompanyConfig(
                company_id="alpha",
                base_url=COMPANY_URL,
                encrypted_api_key=encrypt_api_key("rf-company-key"),
                dataset_ids=["ds-alpha-own"],
            ),
        )

    service.repository.transaction(op)
    client_obj = kb.client_for("alpha")
    assert client_obj is not None
    assert client_obj._config.base_url == COMPANY_URL


def test_knowledge_base_client_disabled_when_company_explicitly_disabled(secret_key):
    service = _service()
    kb = KnowledgeBaseService(service)

    def op(s):
        _seed(
            s,
            _platform_config(),
            RagflowCompanyConfig(company_id="alpha", is_enabled=False),
        )

    service.repository.transaction(op)
    assert kb.client_for("alpha") is None
    assert kb.enabled("alpha") is False


def test_ragflow_config_service_get_client_falls_back(secret_key):
    service = _service()
    principal = _login(service, "alpha-company-admin")

    def op(s):
        _seed(s, _platform_config())

    service.repository.transaction(op)
    config_service = RagflowConfigService(service)
    client_obj = config_service.get_client(principal)
    assert client_obj._config.base_url == PLATFORM_URL


def _login(service, account):
    token = service.auth_login(account, "X_2026")["access_token"]
    return service.authenticate(token)


# ---------------------------------------------------------------------------
# 3. HTTP 全链路：平台管理员写入 system 配置，公司消费回落
# ---------------------------------------------------------------------------

def test_platform_admin_writes_system_config_and_company_falls_back(client):
    """平台管理员（admin/system）保存的配置写入 ragflow_configs['system'] 并对公司生效。"""
    platform = login(client, "admin")
    read = client.get("/api/v1/ragflow-config", headers=platform)
    assert read.status_code == 200, read.text
    revision = read.json()["revision"]
    updated = client.put(
        "/api/v1/ragflow-config",
        headers={**platform, "If-Match": str(revision)},
        json={"base_url": PLATFORM_URL, "api_key": "rf-platform-secret", "timeout_seconds": 45.0},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["company_id"] == "system"

    def check(state):
        assert "system" in state.ragflow_configs
        assert state.ragflow_configs["system"].base_url == PLATFORM_URL

    client.app.state.service.repository.transaction(check)

    # 公司（alpha）未完成配置：知识库消费路径回落平台端点
    kb = client.app.state.service.knowledge_base
    client_obj = kb.client_for("alpha")
    assert client_obj is not None
    assert client_obj._config.base_url == PLATFORM_URL

    # PM 最终权限模型：公司管理员不再能写引擎配置（403）；公司级覆盖行只能由平台侧代管/种子直铺。
    # 这里直接种子公司显式配置，验证公司级优先语义不变。
    company_admin = login(client, "alpha-company-admin")
    refused = client.put("/api/v1/ragflow-config", headers={**company_admin, "If-Match": "1"},
                         json={"base_url": COMPANY_URL, "api_key": "rf-alpha-own-secret"})
    assert refused.status_code == 403, refused.text

    from icg.domain.ragflow_config import RagflowCompanyConfig
    from icg.infra.model_config_storage import encrypt_api_key, mask_api_key

    def seed_company(state):
        state.ragflow_configs["alpha"] = RagflowCompanyConfig(
            company_id="alpha", base_url=COMPANY_URL,
            encrypted_api_key=encrypt_api_key("rf-alpha-own-secret"),
            api_key_masked=mask_api_key("rf-alpha-own-secret"),
        )

    client.app.state.service.repository.transaction(seed_company)
    client_obj2 = kb.client_for("alpha")
    assert client_obj2 is not None
    assert client_obj2._config.base_url == COMPANY_URL


def test_dataset_isolation_prefix_unchanged_with_fallback(client, secret_key):
    """回落生效时数据集命名仍按公司前缀隔离（${company_id}::）。"""
    from icg.domain.knowledge_base import dataset_full_name

    # 数据集全名按公司拼前缀，与使用哪份连接配置无关
    assert dataset_full_name("alpha", "materials").startswith("alpha::")
    assert dataset_full_name("beta", "materials").startswith("beta::")

    # 回落配置的 dataset_ids 必须是公司自己的，而不是平台 system 的
    def op(s):
        _seed(s, _platform_config())

    client.app.state.service.repository.transaction(op)
    effective = effective_ragflow_connection(client.app.state.service.repository.read(), "alpha")
    assert all(not ds.startswith("dataset-system") for ds in effective.dataset_ids)
    assert effective.company_id == "alpha"
