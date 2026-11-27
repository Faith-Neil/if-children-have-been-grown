# 为什么有这个文件：登记 ISSUE-059(a) 涉密项目公网外泄封堵与密钥轮换的复现与回归。
# 它解决什么问题：
# 1. 平台 system 兜底绝不选择公网 URL 的模型配置（数据不出内网红线）；
# 2. resolve_model_provider 的绑定/公司兜底/进程兜底分支与任务表分支施加同等涉密校验（防御纵深不看 is_local 标志）；
# 3. require_allowed_model 基于「实际将生效的模型配置」校验，任务路由/公司配置提供合规本地模型时不被进程兜底误挡；
# 4. 仍在使用（项目绑定 + 任务路由引用）的公司模型可以轮换密钥，且 MySQL before/after diff 能检测密文变化。

from __future__ import annotations

from cryptography.fernet import Fernet
import pytest
from fastapi.testclient import TestClient

from icg.infra.memory_repository import MemoryRepository
from icg.domain.domain import DemoService, DomainError, Project
from icg.infra.adapters import DemoModelProvider
from icg.infra.model_config_storage import (
    ModelConfig,
    ModelConfigService,
    decrypt_api_key,
    encrypt_api_key,
    saved_company_model,
)
from icg_demo.main import create_app
from test_demo import login

PUBLIC_URL = "https://api.public-cloud-provider.example.com/v1"
PRIVATE_URL = "http://192.168.10.50:8000"


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


def _principal(service, account):
    token = service.auth_login(account, "X_2026")["access_token"]
    return service.authenticate(token)


def _config(config_id, company_id, *, base_url=PRIVATE_URL, is_local=True, allow_sensitive=True, key=None):
    return ModelConfig(
        id=config_id,
        company_id=company_id,
        name=f"合成配置-{config_id}",
        provider="openai-compatible",
        base_url=base_url,
        model="qwen2.5-72b",
        encrypted_api_key=encrypt_api_key(key) if key else None,
        is_local=is_local,
        allow_sensitive=allow_sensitive,
    )


def _sensitive_project(state, project_id="sec-proj", company_id="alpha"):
    state.projects[project_id] = Project(id=project_id, name="合成涉密项目", company_id=company_id, sensitive=True)
    return project_id


class _RealCloudProvider:
    """进程级兜底为非本地真实模型的替身（生产误配场景）。"""

    is_real_model = True
    is_local = False

    def suggest(self, *_args, **_kwargs):  # pragma: no cover - 不应被调用
        raise AssertionError("涉密项目不应调用非本地进程兜底模型")


# ---------------------------------------------------------------------------
# 1. 平台 system 兜底排除公网端点
# ---------------------------------------------------------------------------

def test_platform_fallback_never_selects_public_url_config(secret_key):
    service = _service()
    state = service.repository.read()
    # 平台只配了公网端点（即使管理员误标 is_local=True/allow_sensitive=True）
    state.model_configs["cfg-sys-public"] = _config(
        "cfg-sys-public", "system", base_url=PUBLIC_URL, is_local=True, allow_sensitive=True)

    def op(s):
        s.model_configs["cfg-sys-public"] = state.model_configs["cfg-sys-public"]

    service.repository.transaction(op)
    chosen = saved_company_model(service.repository.read(), "alpha")
    assert chosen is None, "平台公网配置不得参与公司兜底"


def test_platform_fallback_selects_private_system_config(secret_key):
    service = _service()

    def op(s):
        s.model_configs["cfg-sys-public"] = _config("cfg-sys-public", "system", base_url=PUBLIC_URL)
        s.model_configs["cfg-sys-private"] = _config("cfg-sys-private", "system", base_url=PRIVATE_URL)

    service.repository.transaction(op)
    chosen = saved_company_model(service.repository.read(), "alpha")
    assert chosen is not None and chosen.id == "cfg-sys-private"


# ---------------------------------------------------------------------------
# 2. resolve_model_provider 全分支涉密校验（含防御纵深）
# ---------------------------------------------------------------------------

def _resolve(service, project_id, task="chapter_generation"):
    state = service.repository.read()
    return service.resolve_model_provider(state, project_id, task)


def test_sensitive_project_blocked_when_binding_turned_noncompliant(secret_key):
    """绑定时不合规校验可以绕过后门：先绑定合规配置再改成云端，运行时必须拦截。"""
    service = _service()

    def op(s):
        s.model_configs["cfg-bind"] = _config("cfg-bind", "alpha", is_local=False, allow_sensitive=False)
        _sensitive_project(s)
        s.project_model_configs["sec-proj"] = "cfg-bind"

    service.repository.transaction(op)
    with pytest.raises(DomainError) as exc:
        _resolve(service, "sec-proj")
    assert exc.value.status == 403
    assert exc.value.code == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"


def test_sensitive_project_blocked_when_company_fallback_noncompliant(secret_key):
    service = _service()

    def op(s):
        s.model_configs["cfg-company-cloud"] = _config("cfg-company-cloud", "alpha", is_local=False, allow_sensitive=False)
        _sensitive_project(s)

    service.repository.transaction(op)
    with pytest.raises(DomainError) as exc:
        _resolve(service, "sec-proj")
    assert exc.value.status == 403
    assert exc.value.code == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"


def test_sensitive_project_blocked_when_is_local_mislabeled_on_public_url(secret_key):
    """防御纵深：is_local 标志被误填 True 也不能掩盖公网 URL。"""
    service = _service()

    def op(s):
        s.model_configs["cfg-mislabeled"] = _config(
            "cfg-mislabeled", "alpha", base_url=PUBLIC_URL, is_local=True, allow_sensitive=True)
        _sensitive_project(s)
        s.project_model_configs["sec-proj"] = "cfg-mislabeled"

    service.repository.transaction(op)
    with pytest.raises(DomainError) as exc:
        _resolve(service, "sec-proj")
    assert exc.value.status == 403
    assert exc.value.code == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"


def test_sensitive_project_blocked_when_process_fallback_is_remote_real_model(secret_key):
    service = _service()
    service.model_provider = _RealCloudProvider()

    def op(s):
        _sensitive_project(s)

    service.repository.transaction(op)
    with pytest.raises(DomainError) as exc:
        _resolve(service, "sec-proj")
    assert exc.value.status == 409
    assert exc.value.code == "LOCAL_MODEL_REQUIRED"


def test_sensitive_project_resolves_compliant_local_binding(secret_key, fake_openai_chat):
    service = _service()

    def op(s):
        s.model_configs["cfg-ok"] = _config(
            "cfg-ok", "alpha", base_url=fake_openai_chat.base_url, is_local=True, allow_sensitive=True, key="sk-ok")
        _sensitive_project(s)
        s.project_model_configs["sec-proj"] = "cfg-ok"

    service.repository.transaction(op)
    provider = _resolve(service, "sec-proj")
    assert getattr(provider, "is_real_model", False) is True
    assert provider.suggest("sys", "user") == "合成模型候选，仍须人工核对。"
    assert fake_openai_chat.calls[-1].header("Authorization") == "Bearer sk-ok"


def test_non_sensitive_project_may_use_cloud_config(secret_key):
    """非涉密项目不禁云端配置（产品明确支持），收紧只针对涉密项目。"""
    service = _service()

    def op(s):
        s.model_configs["cfg-cloud"] = _config("cfg-cloud", "alpha", base_url=PUBLIC_URL, is_local=False, allow_sensitive=False)
        s.projects["open-proj"] = Project(id="open-proj", name="合成普通项目", company_id="alpha", sensitive=False)
        s.project_model_configs["open-proj"] = "cfg-cloud"

    service.repository.transaction(op)
    provider = _resolve(service, "open-proj")
    assert getattr(provider, "is_real_model", False) is True  # 不抛错即通过


# ---------------------------------------------------------------------------
# 3. require_allowed_model 与实际生效配置一致（不误挡合规本地模型）
# ---------------------------------------------------------------------------

def _route(state, company_id, task, primary_id):
    saved = state.service_stores.setdefault("task_model_routes", {}).setdefault(company_id, {"routes": {}, "revision": 0})
    saved["routes"][task] = {"primary_config_id": primary_id, "fallback_config_id": None}


def test_gate_not_blocked_by_process_default_when_task_route_compliant(secret_key, fake_openai_chat):
    """复现误挡：任务路由提供合规本地模型时，进程兜底非 local 不得再拦涉密生成。"""
    service = _service()
    service.model_provider = _RealCloudProvider()

    def op(s):
        s.model_configs["cfg-route-local"] = _config(
            "cfg-route-local", "alpha", base_url=fake_openai_chat.base_url, key="sk-route")
        _sensitive_project(s)
        _route(s, "alpha", "chapter_generation", "cfg-route-local")

    service.repository.transaction(op)
    state = service.repository.read()
    project = state.projects["sec-proj"]
    service.require_allowed_model(project, state=state)  # 修复前：409 LOCAL_MODEL_REQUIRED 误挡
    provider = service.resolve_model_provider(state, "sec-proj", "chapter_generation")
    assert getattr(provider, "is_real_model", False) is True
    assert provider.suggest("sys", "user") == "合成模型候选，仍须人工核对。"
    assert fake_openai_chat.calls[-1].header("Authorization") == "Bearer sk-route"


def test_gate_not_blocked_by_process_default_when_company_config_compliant(secret_key, fake_openai_chat):
    service = _service()
    service.model_provider = _RealCloudProvider()

    def op(s):
        s.model_configs["cfg-company-local"] = _config(
            "cfg-company-local", "alpha", base_url=fake_openai_chat.base_url, key="sk-company")
        _sensitive_project(s)

    service.repository.transaction(op)
    state = service.repository.read()
    service.require_allowed_model(state.projects["sec-proj"], state=state)  # 不得误挡


def test_gate_still_blocks_sensitive_when_nothing_compliant(secret_key):
    service = _service()
    service.model_provider = _RealCloudProvider()

    def op(s):
        s.model_configs["cfg-only-cloud"] = _config("cfg-only-cloud", "alpha", is_local=False, allow_sensitive=False)
        _sensitive_project(s)

    service.repository.transaction(op)
    state = service.repository.read()
    with pytest.raises(DomainError) as exc:
        service.require_allowed_model(state.projects["sec-proj"], state=state)
    assert exc.value.status == 403


# ---------------------------------------------------------------------------
# 4. 仍在使用的公司模型密钥轮换（HTTP 全链路 + MySQL diff 检测）
# ---------------------------------------------------------------------------

def test_in_use_config_key_rotation_end_to_end(client):
    """创建 → 项目绑定 + 任务路由引用 → PUT 新明文密钥：密文必须真的更新。"""
    admin = login(client, "alpha-company-admin")
    lead = login(client, "alpha-manager")
    created = client.post(
        "/api/v1/model-configs",
        headers=admin,
        json={"id": "cfg-rotate", "name": "使用中模型", "base_url": PRIVATE_URL,
              "model": "qwen2.5-72b", "api_key": "sk-original-key-aa01"},
    )
    assert created.status_code == 200, created.text
    assert created.json()["api_key_masked"] == "sk-***aa01"

    # 「仍在使用」：绑定到项目 + 被任务与模型对应表引用
    bound = client.post("/api/v1/projects/alpha-project/model-config", headers=lead,
                        json={"model_config_id": "cfg-rotate"})
    assert bound.status_code == 200, bound.text
    routed = client.put("/api/v1/task-model-routes", headers={**admin, "If-Match": "0"},
                        json={"routes": [{"task": "chapter_generation", "primary_config_id": "cfg-rotate"}]})
    assert routed.status_code == 200, routed.text

    def cipher_of(state):
        return state.model_configs["cfg-rotate"].encrypted_api_key

    before_cipher = client.app.state.service.repository.transaction(cipher_of)

    # 轮换密钥：PUT 新明文
    rotated = client.put(
        "/api/v1/model-configs/cfg-rotate",
        headers={**admin, "If-Match": "1"},
        json={"api_key": "sk-rotated-key-bb02"},
    )
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["revision"] == 2
    assert rotated.json()["api_key_masked"] == "sk-***bb02"

    after_cipher = client.app.state.service.repository.transaction(cipher_of)
    assert after_cipher != before_cipher, "密文必须随轮换更新"
    assert decrypt_api_key(after_cipher) == "sk-rotated-key-bb02"
    # 绑定与任务路由引用不受轮换影响
    state = client.app.state.service.repository.read()
    assert state.project_model_configs["alpha-project"] == "cfg-rotate"


def test_rotation_with_masked_key_echo_is_noop_but_new_plaintext_rotates(client):
    """传回掩码不动密钥；全新明文必须轮换。"""
    admin = login(client, "alpha-company-admin")
    created = client.post("/api/v1/model-configs", headers=admin,
                          json={"id": "cfg-mask", "api_key": "sk-aaa-unchanged-z99", "base_url": PRIVATE_URL})
    assert created.status_code == 200, created.text
    masked = created.json()["api_key_masked"]
    assert masked and "***" in masked

    def cipher_of(state):
        return state.model_configs["cfg-mask"].encrypted_api_key

    first = client.app.state.service.repository.transaction(cipher_of)
    # 传回掩码：无操作（密钥保持不变）
    res = client.put("/api/v1/model-configs/cfg-mask", headers={**admin, "If-Match": "1"},
                     json={"api_key": masked, "timeout_seconds": 45.0})
    assert res.status_code == 200, res.text
    assert decrypt_api_key(client.app.state.service.repository.transaction(cipher_of)) == "sk-aaa-unchanged-z99"
    # 新明文：轮换
    res2 = client.put("/api/v1/model-configs/cfg-mask", headers={**admin, "If-Match": "2"},
                      json={"api_key": "sk-aaa-rotated2-w88"})
    assert res2.status_code == 200, res2.text
    assert res2.json()["api_key_masked"] == "sk-***-w88"
    assert decrypt_api_key(client.app.state.service.repository.transaction(cipher_of)) == "sk-aaa-rotated2-w88"


def test_mysql_save_diff_detects_key_rotation(secret_key):
    """infra/repositories/model_config.py 的 before/after diff：密文变化必须触发 UPDATE，未变化不写。"""
    from dataclasses import replace
    from icg.infra.repositories.model_config import save_model_configs

    class RecordingConnection:
        def __init__(self):
            self.calls = []

        def execute(self, clause, params=None):
            self.calls.append((str(clause), dict(params or {})))

            class Result:
                rowcount = 1
            return Result()

    cfg = _config("cfg-diff", "alpha", key="sk-before-0001")
    before = {"cfg-diff": replace(cfg)}
    # 模拟轮换：密文变化（Fernet 非确定性，每次加密结果不同）
    cfg.encrypted_api_key = encrypt_api_key("sk-after-0002")
    cfg.api_key_masked = "sk-***0002"
    cfg.revision = 2
    after = {"cfg-diff": cfg}

    conn = RecordingConnection()
    save_model_configs(conn, before, after, {}, {})
    updates = [c for c in conn.calls if c[0].startswith("UPDATE demo_model_config")]
    assert len(updates) == 1, f"密文轮换必须产生一条 UPDATE，实际: {[c[0][:30] for c in conn.calls]}"
    assert updates[0][1]["encrypted_api_key"] == cfg.encrypted_api_key
    assert decrypt_api_key(updates[0][1]["encrypted_api_key"]) == "sk-after-0002"

    # 未变化时不写库
    conn2 = RecordingConnection()
    save_model_configs(conn2, {"cfg-diff": replace(cfg)}, {"cfg-diff": cfg}, {}, {})
    assert conn2.calls == [], "配置未变化不得产生任何写入"


def test_platform_admin_cannot_rotate_but_company_admin_can(client):
    """轮换的执行人是公司管理员；平台账号因租户不匹配也动不了公司配置（404 不泄露）。"""
    admin = login(client, "alpha-company-admin")
    client.post("/api/v1/model-configs", headers=admin,
                json={"id": "cfg-owner", "api_key": "sk-owner-key-0001", "base_url": PRIVATE_URL})
    platform = login(client, "admin")
    res = client.put("/api/v1/model-configs/cfg-owner", headers={**platform, "If-Match": "1"},
                     json={"api_key": "sk-hijack-9999"})
    assert res.status_code == 404  # 平台账号 company=system 看不到 alpha 的配置
    res_ok = client.put("/api/v1/model-configs/cfg-owner", headers={**admin, "If-Match": "1"},
                        json={"api_key": "sk-owner-key-0002"})
    assert res_ok.status_code == 200, res_ok.text
