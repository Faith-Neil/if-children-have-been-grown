# 为什么有这个文件：全面验证 ISSUE-024 模型配置的存储、加密、掩码、乐观锁、连通性测试与错误码。
# 它解决什么问题：确保密钥绝不泄漏明文、无主密钥时 503 无 Retry-After、乐观锁与敏感门禁严格生效。

import os
from cryptography.fernet import Fernet
import pytest
from fastapi.testclient import TestClient

from icg_demo.domain import DomainError, Project
from icg_demo.main import create_app
from icg_demo.model_config_storage import (
    ModelConfig,
    decrypt_api_key,
    encrypt_api_key,
    mask_api_key,
    validate_model_config_for_project,
)
from test_demo import login
from test_recoverable_jobs import confirm_chapter, start


@pytest.fixture
def secret_key(monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("ICG_SECRET_KEY", key)
    return key


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


def test_fernet_encryption_and_decryption(secret_key):
    plain = "sk-live-secret-test-key-12345"
    cipher = encrypt_api_key(plain)
    assert cipher is not None
    assert cipher != plain
    assert cipher.startswith("gAAAAA")
    decrypted = decrypt_api_key(cipher)
    assert decrypted == plain


def test_secret_key_unavailable_when_env_unset(monkeypatch):
    monkeypatch.delenv("ICG_SECRET_KEY", raising=False)
    with pytest.raises(DomainError) as exc_info:
        encrypt_api_key("sk-test")
    assert exc_info.value.status == 503
    assert exc_info.value.code == "SECRET_KEY_UNAVAILABLE"

    with pytest.raises(DomainError) as exc_info2:
        decrypt_api_key("gAAAAABtest")
    assert exc_info2.value.status == 503
    assert exc_info2.value.code == "SECRET_KEY_UNAVAILABLE"


def test_api_key_masking():
    assert mask_api_key(None) is None
    assert mask_api_key("") is None
    assert mask_api_key("short") == "***"
    assert mask_api_key("12345678") == "***"
    assert mask_api_key("sk-1234567890abcdef") == "sk-***cdef"


def test_api_response_masks_keys_and_never_returns_plaintext(client, secret_key):
    headers = login(client, "alpha-manager")
    res = client.post(
        "/api/v1/model-configs",
        headers=headers,
        json={
            "id": "cfg-secure-1",
            "name": "安全内网模型",
            "provider": "openai-compatible",
            "base_url": "http://127.0.0.1:8000",
            "model": "qwen2.5-72b",
            "api_key": "sk-1234567890abcdef",
            "is_local": True,
            "allow_sensitive": True,
            "stream_enabled": True,
            "json_mode_enabled": False,
        },
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert "api_key" not in data
    assert data["has_api_key"] is True
    assert data["api_key_masked"] == "sk-***cdef"
    assert data["revision"] == 1
    assert data["stream_enabled"] is True
    assert data["json_mode_enabled"] is False

    # GET 接口同样不返回明文
    get_res = client.get("/api/v1/model-configs/cfg-secure-1", headers=headers)
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert "api_key" not in get_data
    assert get_data["has_api_key"] is True
    assert get_data["api_key_masked"] == "sk-***cdef"
    assert get_res.headers.get("ETag") == '"1"'


def test_update_rules_omit_clear_and_mask(client, secret_key):
    headers = login(client, "alpha-manager")
    client.post(
        "/api/v1/model-configs",
        headers=headers,
        json={
            "id": "cfg-update-rules",
            "name": "初始配置",
            "model": "qwen2.5-72b",
            "api_key": "sk-original123456",
        },
    )

    # 1. 省略 api_key 代表保留原密钥
    res1 = client.put(
        "/api/v1/model-configs/cfg-update-rules",
        headers={**headers, "If-Match": "1"},
        json={"name": "改名但保留密钥"},
    )
    assert res1.status_code == 200
    assert res1.json()["revision"] == 2
    assert res1.json()["has_api_key"] is True
    assert res1.json()["api_key_masked"] == "sk-***3456"

    # 2. 传回刚才返回的掩码代表不修改
    res2 = client.put(
        "/api/v1/model-configs/cfg-update-rules",
        headers={**headers, "If-Match": "2"},
        json={"name": "送回掩码", "api_key": "sk-***3456"},
    )
    assert res2.status_code == 200
    assert res2.json()["revision"] == 3
    assert res2.json()["has_api_key"] is True
    assert res2.json()["api_key_masked"] == "sk-***3456"

    # 3. 空字符串代表清除密钥
    res3 = client.put(
        "/api/v1/model-configs/cfg-update-rules",
        headers={**headers, "If-Match": "3"},
        json={"api_key": ""},
    )
    assert res3.status_code == 200
    assert res3.json()["revision"] == 4
    assert res3.json()["has_api_key"] is False
    assert res3.json()["api_key_masked"] is None

    # 4. 传入新明文代表更新
    res4 = client.put(
        "/api/v1/model-configs/cfg-update-rules",
        headers={**headers, "If-Match": "4"},
        json={"api_key": "sk-brandnewkey888"},
    )
    assert res4.status_code == 200
    assert res4.json()["revision"] == 5
    assert res4.json()["has_api_key"] is True
    assert res4.json()["api_key_masked"] == "sk-***y888"


def test_optimistic_locking_via_if_match_and_revision(client, secret_key):
    headers = login(client, "alpha-manager")
    client.post(
        "/api/v1/model-configs",
        headers=headers,
        json={"id": "cfg-lock", "name": "并发锁测试"},
    )

    # 缺少 If-Match 请求头返回 428 IF_MATCH_REQUIRED
    res_no_match = client.put(
        "/api/v1/model-configs/cfg-lock",
        headers=headers,
        json={"name": "新名"},
    )
    assert res_no_match.status_code == 428
    assert res_no_match.json()["code"] == "IF_MATCH_REQUIRED"

    # 版本不一致返回 409 REVISION_CONFLICT
    res_conflict = client.put(
        "/api/v1/model-configs/cfg-lock",
        headers={**headers, "If-Match": "999"},
        json={"name": "新名"},
    )
    assert res_conflict.status_code == 409
    assert res_conflict.json()["code"] == "REVISION_CONFLICT"
    assert res_conflict.json()["details"]["current_revision"] == 1

    # 正确匹配 If-Match: 1 成功更新全部字段（含 stream_enabled 与 json_mode_enabled）
    res_ok = client.put(
        "/api/v1/model-configs/cfg-lock",
        headers={**headers, "If-Match": "1"},
        json={
            "stream_enabled": False,
            "json_mode_enabled": True,
            "allow_sensitive": False,
            "model": "deepseek-v3",
        },
    )
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert data["revision"] == 2
    assert data["stream_enabled"] is False
    assert data["json_mode_enabled"] is True
    assert data["allow_sensitive"] is False
    assert data["model"] == "deepseek-v3"

    # 再次使用旧版本 If-Match: 1 更新失败
    res_conflict2 = client.put(
        "/api/v1/model-configs/cfg-lock",
        headers={**headers, "If-Match": "1"},
        json={"name": "再次更新"},
    )
    assert res_conflict2.status_code == 409
    assert res_conflict2.json()["code"] == "REVISION_CONFLICT"
    assert res_conflict2.json()["details"]["current_revision"] == 2


def test_secret_key_unavailable_503_has_no_retry_after(client, monkeypatch):
    monkeypatch.delenv("ICG_SECRET_KEY", raising=False)
    headers = login(client, "alpha-manager")

    # 1. 创建带 key 的配置，主密钥缺失触发 503
    res_create = client.post(
        "/api/v1/model-configs",
        headers=headers,
        json={
            "id": "cfg-no-secret",
            "name": "缺密钥测试",
            "api_key": "sk-somesecret",
        },
    )
    assert res_create.status_code == 503
    assert res_create.json()["code"] == "SECRET_KEY_UNAVAILABLE"
    # 严格断言不得包含 Retry-After 请求头
    assert "retry-after" not in res_create.headers

    # 2. 但创建不带 key 的配置可以成功
    res_create_nokey = client.post(
        "/api/v1/model-configs",
        headers=headers,
        json={"id": "cfg-no-key", "name": "无密钥模型"},
    )
    assert res_create_nokey.status_code == 200

    # 3. 更新为有密钥触发 503 无 Retry-After
    res_update = client.put(
        "/api/v1/model-configs/cfg-no-key",
        headers={**headers, "If-Match": "1"},
        json={"api_key": "sk-new"},
    )
    assert res_update.status_code == 503
    assert res_update.json()["code"] == "SECRET_KEY_UNAVAILABLE"
    assert "retry-after" not in res_update.headers


def test_connectivity_api(client, secret_key, fake_openai_chat):
    headers = login(client, "alpha-manager")

    # 1. demo 模型测试连通性
    client.post(
        "/api/v1/model-configs",
        headers=headers,
        json={"id": "cfg-demo", "provider": "demo", "model": "demo-v1"},
    )
    res_demo = client.post("/api/v1/model-configs/cfg-demo/test", headers=headers)
    assert res_demo.status_code == 200
    demo_data = res_demo.json()
    assert demo_data["ok"] is True
    assert demo_data["provider"] == "demo"
    assert demo_data["model"] == "demo-v1"
    assert demo_data["duration_ms"] >= 0

    # 2. openai-compatible 连通性测试（打通 fake_openai_chat）
    client.post(
        "/api/v1/model-configs",
        headers=headers,
        json={
            "id": "cfg-real-like",
            "provider": "openai-compatible",
            "base_url": fake_openai_chat.base_url,
            "model": "qwen2.5-72b",
            "api_key": "sk-fake-chat-token",
        },
    )
    res_real = client.post("/api/v1/model-configs/cfg-real-like/test", headers=headers)
    assert res_real.status_code == 200
    real_data = res_real.json()
    assert real_data["ok"] is True
    assert real_data["provider"] == "openai-compatible"
    assert real_data["model"] == "qwen2.5-72b"
    assert real_data["duration_ms"] >= 0

    # 3. 失败连通性（无法连接的端口）
    client.post(
        "/api/v1/model-configs",
        headers=headers,
        json={
            "id": "cfg-dead",
            "provider": "openai-compatible",
            "base_url": "http://127.0.0.1:1",
            "model": "unreachable",
        },
    )
    res_dead = client.post("/api/v1/model-configs/cfg-dead/test", headers=headers)
    assert res_dead.status_code == 200
    dead_data = res_dead.json()
    assert dead_data["ok"] is False


def test_connectivity_fails_with_503_without_retry_after_when_secret_key_lost(client, monkeypatch):
    # 先设置 key 保存
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("ICG_SECRET_KEY", key)
    headers = login(client, "alpha-manager")
    client.post(
        "/api/v1/model-configs",
        headers=headers,
        json={"id": "cfg-with-key", "api_key": "sk-important-token"},
    )

    # 随后丢失主密钥
    monkeypatch.delenv("ICG_SECRET_KEY", raising=False)
    test_res = client.post("/api/v1/model-configs/cfg-with-key/test", headers=headers)
    assert test_res.status_code == 503
    assert test_res.json()["code"] == "SECRET_KEY_UNAVAILABLE"
    assert "retry-after" not in test_res.headers


def test_sensitive_project_requires_local_model(client, secret_key):
    headers = login(client, "alpha-manager")

    # 准备敏感项目
    project_res = client.post("/api/projects", headers=headers, json={"name": "涉密项目A"})
    project_id = project_res.json()["id"]

    # 标记为敏感项目
    patch_res = client.patch(
        f"/api/v1/projects/{project_id}",
        headers={**headers, "If-Match": "1", "Idempotency-Key": "patch-sensitive-01"},
        json={"sensitive": True},
    )
    assert patch_res.status_code == 200

    # 创建云端配置
    client.post(
        "/api/v1/model-configs",
        headers=headers,
        json={
            "id": "cfg-cloud",
            "name": "云端公网模型",
            "is_local": False,
            "allow_sensitive": False,
        },
    )

    # 敏感项目尝试绑定云端模型 -> 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL
    bind_res = client.post(
        f"/api/v1/projects/{project_id}/model-config",
        headers=headers,
        json={"model_config_id": "cfg-cloud"},
    )
    assert bind_res.status_code == 403
    assert bind_res.json()["code"] == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"

    # 创建本地但未允许敏感配置 -> 403
    client.post(
        "/api/v1/model-configs",
        headers=headers,
        json={
            "id": "cfg-local-nosensitive",
            "name": "本地非敏感模型",
            "is_local": True,
            "allow_sensitive": False,
        },
    )
    bind_res2 = client.post(
        f"/api/v1/projects/{project_id}/model-config",
        headers=headers,
        json={"model_config_id": "cfg-local-nosensitive"},
    )
    assert bind_res2.status_code == 403
    assert bind_res2.json()["code"] == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"

    # 创建本地且允许敏感配置 -> 成功
    client.post(
        "/api/v1/model-configs",
        headers=headers,
        json={
            "id": "cfg-local-sensitive",
            "name": "本地涉密合规模型",
            "is_local": True,
            "allow_sensitive": True,
        },
    )
    bind_res3 = client.post(
        f"/api/v1/projects/{project_id}/model-config",
        headers=headers,
        json={"model_config_id": "cfg-local-sensitive"},
    )
    assert bind_res3.status_code == 200
    assert bind_res3.json()["model_config_id"] == "cfg-local-sensitive"


def test_job_start_snapshots_stream_and_json_mode_enabled(client, secret_key):
    headers = login(client, "alpha-manager")
    confirm_chapter(client)

    # 启动任务，快照此时配置（stream_enabled=True, json_mode_enabled=False）
    res = start(client, headers)
    assert res.status_code == 202
    job_id = res.json()["id"]

    # 检查任务详情中的 model_snapshot
    job_res = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert job_res.status_code == 200

    # 直接核对内存中的 snapshot
    def check_snap(state):
        snap = state.recoverable_jobs[job_id]["model_snapshot"]
        assert snap["stream_enabled"] is True
        assert snap["json_mode_enabled"] is False

    client.app.state.service.repository.transaction(check_snap)


def test_company_multi_tenant_isolation(client, secret_key):
    alpha_headers = login(client, "alpha-manager")
    beta_headers = login(client, "beta-editor")

    # alpha 创建专属配置
    client.post(
        "/api/v1/model-configs",
        headers=alpha_headers,
        json={"id": "cfg-alpha-only", "name": "甲公司专属模型"},
    )

    # beta 读取返回 404 NOT_FOUND
    res_get = client.get("/api/v1/model-configs/cfg-alpha-only", headers=beta_headers)
    assert res_get.status_code == 404
    assert res_get.json()["code"] == "NOT_FOUND"

    # beta 修改返回 404 NOT_FOUND
    res_put = client.put(
        "/api/v1/model-configs/cfg-alpha-only",
        headers={**beta_headers, "If-Match": "1"},
        json={"name": "非法改名"},
    )
    assert res_put.status_code == 404
    assert res_put.json()["code"] == "NOT_FOUND"
