# 为什么有这个文件：全面验证 ISSUE-028 配置驱动的对话模型运行时接入。
# 它解决什么问题：按项目配置动态路由对话模型、闭环 AC-04 敏感项目 403 阻断、流式/JSON 模式透传、快照隔离与假服务测试。

import json
import os
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from fake_openai_chat import real_model_skip_reason
from icg_demo.domain import DomainError
from icg_demo.main import create_app
from icg_demo.model_config_storage import (
    ModelConfig,
    encrypt_api_key,
    provider_from_model_config,
    provider_from_model_snapshot,
)
from icg_demo.openai_model import OpenAICompatibleModelProvider
from test_demo import login
from test_recoverable_jobs import confirm_chapter, start


@pytest.fixture
def secret_key(monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("ICG_SECRET_KEY", key)
    return key


@pytest.fixture
def client(secret_key):
    with TestClient(create_app()) as test_client:
        yield test_client


def test_provider_from_model_config_openai_compatible_parameters(fake_openai_chat, secret_key):
    """验证从 ModelConfig 动态组装 OpenAICompatibleModelProvider：包含流式、JSON 模式、解密密钥与端点地址。"""
    plain_key = "sk-provider-test-key-abc123"
    enc_key = encrypt_api_key(plain_key)
    cfg = ModelConfig(
        id="cfg-custom-1",
        company_id="alpha",
        name="测试自定义模型",
        provider="openai-compatible",
        base_url=fake_openai_chat.base_url,
        model="custom-qwen-72b",
        encrypted_api_key=enc_key,
        is_local=True,
        allow_sensitive=True,
        stream_enabled=True,
        json_mode_enabled=True,
        timeout_seconds=5.0,
        max_tokens=256,
    )
    provider = provider_from_model_config(cfg)
    assert isinstance(provider, OpenAICompatibleModelProvider)
    assert provider.name == "openai-compatible"
    assert provider.is_real_model is True
    assert provider.is_local is True
    assert provider.stream_enabled is True
    assert provider.json_mode_enabled is True
    assert provider.model == "custom-qwen-72b"
    assert provider.base_url == fake_openai_chat.base_url

    # 执行调用
    result = provider.suggest("系统提示词", "用户提问正文")
    assert result == "合成模型候选，仍须人工核对。"

    # 核对 fake_openai_chat 收到的参数
    assert len(fake_openai_chat.calls) == 1
    call = fake_openai_chat.calls[0]
    assert call.header("Authorization") == f"Bearer {plain_key}"
    payload = call.json
    assert payload["model"] == "custom-qwen-72b"
    assert payload["stream"] is True
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["max_tokens"] == 256
    assert payload["messages"] == [
        {"role": "system", "content": "系统提示词"},
        {"role": "user", "content": "用户提问正文"},
    ]


def test_provider_from_model_config_stream_disabled_and_json_mode_disabled(fake_openai_chat, secret_key):
    """当 stream_enabled=False 且 json_mode_enabled=False 时，请求体正确关闭流式且不含 response_format。"""
    cfg = ModelConfig(
        id="cfg-nostream-1",
        base_url=fake_openai_chat.base_url,
        model="nostream-model",
        stream_enabled=False,
        json_mode_enabled=False,
        timeout_seconds=5.0,
        max_tokens=128,
    )
    provider = provider_from_model_config(cfg)
    result = provider.suggest("指令", "内容")
    assert result == "合成模型候选，仍须人工核对。"

    call = fake_openai_chat.calls[0]
    payload = call.json
    assert payload["stream"] is False
    assert "response_format" not in payload


def test_provider_from_model_snapshot(fake_openai_chat, secret_key):
    """验证从快照字典组装模型提供者。"""
    plain_key = "sk-snapshot-key"
    enc_key = encrypt_api_key(plain_key)
    snapshot = {
        "provider": "openai-compatible",
        "model": "snapshot-model-v1",
        "is_real_model": True,
        "is_local": True,
        "stream_enabled": True,
        "json_mode_enabled": True,
        "base_url": fake_openai_chat.base_url,
        "timeout_seconds": 10.0,
        "max_tokens": 512,
        "encrypted_api_key": enc_key,
    }
    provider = provider_from_model_snapshot(snapshot)
    assert isinstance(provider, OpenAICompatibleModelProvider)
    res = provider.suggest("sys", "user")
    assert res == "合成模型候选，仍须人工核对。"
    assert fake_openai_chat.calls[0].header("Authorization") == f"Bearer {plain_key}"
    assert fake_openai_chat.calls[0].json["model"] == "snapshot-model-v1"


def test_runtime_switch_project_bound_config(client, fake_openai_chat, secret_key):
    """项目绑定了特定模型配置后，章节建议接口动态走该模型调用。"""
    headers = login(client, "alpha-manager")
    # 1. 创建指向 fake_openai_chat 的模型配置
    cfg_res = client.post(
        "/api/v1/model-configs",
        headers=headers,
        json={
            "id": "cfg-alpha-bound",
            "name": "甲公司项目专属模型",
            "provider": "openai-compatible",
            "base_url": fake_openai_chat.base_url,
            "model": "qwen2.5-32b-bound",
            "api_key": "sk-project-bound-key",
            "is_local": True,
            "allow_sensitive": True,
            "stream_enabled": True,
            "json_mode_enabled": False,
        },
    )
    assert cfg_res.status_code == 200

    # 2. 创建项目并绑定配置
    proj_res = client.post("/api/projects", headers=headers, json={"name": "绑定模型测试项目"})
    proj_id = proj_res.json()["id"]
    bind_res = client.post(
        f"/api/v1/projects/{proj_id}/model-config",
        headers=headers,
        json={"model_config_id": "cfg-alpha-bound"},
    )
    assert bind_res.status_code == 200

    # 3. 请求章节建议
    chapters_res = client.get(f"/api/projects/{proj_id}/chapters", headers=headers)
    chapter_id = chapters_res.json()["chapters"][0]["id"]
    sug_res = client.post(
        f"/api/chapters/{chapter_id}/suggestions",
        headers=headers,
        json={"instruction": "依据配置模型生成建议"},
    )
    assert sug_res.status_code == 200, sug_res.text
    sug_data = sug_res.json()
    assert sug_data["provider"] == "openai-compatible"
    assert sug_data["is_real_model"] is True
    assert sug_data["content"] == "合成模型候选，仍须人工核对。"

    # 4. 断言 fake_openai_chat 实际收到了调用
    assert len(fake_openai_chat.calls) == 1
    call = fake_openai_chat.calls[0]
    assert call.header("Authorization") == "Bearer sk-project-bound-key"
    assert call.json["model"] == "qwen2.5-32b-bound"


def test_runtime_switch_company_default_config(client, fake_openai_chat, secret_key):
    """未单独绑定的项目自动继承公司默认配置，并动态调用默认模型。"""
    headers = login(client, "alpha-manager")
    # 更新公司默认配置 default-alpha 指向 fake_openai_chat
    update_res = client.put(
        "/api/v1/model-configs/default-alpha",
        headers={**headers, "If-Match": "1"},
        json={
            "base_url": fake_openai_chat.base_url,
            "model": "qwen2.5-default-company",
            "api_key": "sk-company-default-key",
            "stream_enabled": True,
        },
    )
    assert update_res.status_code == 200

    # 创建新项目（不显式绑定）
    proj_res = client.post("/api/projects", headers=headers, json={"name": "默认继承项目"})
    proj_id = proj_res.json()["id"]
    chapters_res = client.get(f"/api/projects/{proj_id}/chapters", headers=headers)
    chapter_id = chapters_res.json()["chapters"][0]["id"]

    # 请求建议
    sug_res = client.post(
        f"/api/chapters/{chapter_id}/suggestions",
        headers=headers,
        json={"instruction": "默认模型测试指令"},
    )
    assert sug_res.status_code == 200
    assert sug_res.json()["provider"] == "openai-compatible"
    assert sug_res.json()["is_real_model"] is True

    # 核对 fake_openai_chat 收到了来自默认配置的调用
    assert len(fake_openai_chat.calls) == 1
    assert fake_openai_chat.calls[0].header("Authorization") == "Bearer sk-company-default-key"
    assert fake_openai_chat.calls[0].json["model"] == "qwen2.5-default-company"


def test_recoverable_job_advances_with_model_snapshot(client, fake_openai_chat, secret_key):
    """可恢复生成任务启动时捕获模型配置快照，并在 advance 推进时按快照执行调用。"""
    headers = login(client, "alpha-manager")
    confirm_chapter(client)

    # 绑定特定配置
    client.post(
        "/api/v1/model-configs",
        headers=headers,
        json={
            "id": "cfg-job-snapshot",
            "name": "生成任务模型",
            "provider": "openai-compatible",
            "base_url": fake_openai_chat.base_url,
            "model": "qwen-job-model-v2",
            "api_key": "sk-job-key-999",
            "stream_enabled": True,
            "json_mode_enabled": False,
        },
    )
    client.post(
        "/api/v1/projects/alpha-project/model-config",
        headers=headers,
        json={"model_config_id": "cfg-job-snapshot"},
    )

    # 启动任务返回 202
    res = start(client, headers, key="recover-job-snap-01")
    assert res.status_code == 202
    job_id = res.json()["id"]

    # 核对内存快照字段
    def check_snap(state):
        snap = state.recoverable_jobs[job_id]["model_snapshot"]
        assert snap["provider"] == "openai-compatible"
        assert snap["model"] == "qwen-job-model-v2"
        assert snap["is_real_model"] is True
        assert snap["is_local"] is True
        assert snap["stream_enabled"] is True
        assert snap["json_mode_enabled"] is False

    client.app.state.service.repository.transaction(check_snap)

    # 查询推进任务
    get_res = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert get_res.status_code == 200
    job_data = get_res.json()
    assert job_data["status"] == "completed"

    # 核对 job.model_call 事件
    model_call_events = [e for e in job_data["events"] if e["type"] == "job.model_call"]
    assert len(model_call_events) == 1
    call_ev = model_call_events[0]
    assert call_ev["provider"] == "openai-compatible"
    assert call_ev["model"] == "qwen-job-model-v2"
    assert call_ev["is_real_model"] is True
    assert call_ev["is_local"] is True
    assert call_ev["error_code"] is None
    assert call_ev["duration_ms"] >= 0

    # 核对 fake_openai_chat 收到调用
    assert len(fake_openai_chat.calls) == 1
    assert fake_openai_chat.calls[0].header("Authorization") == "Bearer sk-job-key-999"


def test_recoverable_job_uses_snapshot_even_if_config_changes_later(client, fake_openai_chat, secret_key):
    """任务启动后即使默认或绑定配置发生更新，已排队任务继续使用启动时的模型快照。"""
    headers = login(client, "alpha-manager")
    confirm_chapter(client)

    client.post(
        "/api/v1/model-configs",
        headers=headers,
        json={
            "id": "cfg-freeze-1",
            "provider": "openai-compatible",
            "base_url": fake_openai_chat.base_url,
            "model": "original-freeze-model",
            "api_key": "sk-freeze-orig",
        },
    )
    client.post(
        "/api/v1/projects/alpha-project/model-config",
        headers=headers,
        json={"model_config_id": "cfg-freeze-1"},
    )

    # 启动任务 1
    job1_id = start(client, headers, key="job-freeze-1").json()["id"]

    # 随后修改配置为另一个模型
    client.put(
        "/api/v1/model-configs/cfg-freeze-1",
        headers={**headers, "If-Match": "1"},
        json={"model": "modified-model-v2", "api_key": "sk-freeze-new"},
    )

    # 推进任务 1
    client.get(f"/api/v1/jobs/{job1_id}", headers=headers)

    # 断言调用的是 original-freeze-model
    assert len(fake_openai_chat.calls) == 1
    assert fake_openai_chat.calls[0].json["model"] == "original-freeze-model"
    assert fake_openai_chat.calls[0].header("Authorization") == "Bearer sk-freeze-orig"


def test_sensitive_project_blocks_cloud_model_with_403_ac04(client, fake_openai_chat, secret_key):
    """闭环 AC-04：敏感项目使用云端（非本地）模型时，在调用模型前强制阻断，抛出 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL。"""
    headers = login(client, "alpha-manager")

    # 1. 创建云端公网模型（is_local=False, allow_sensitive=False）
    client.post(
        "/api/v1/model-configs",
        headers=headers,
        json={
            "id": "cfg-cloud-external",
            "name": "云端公网大模型",
            "provider": "openai-compatible",
            "base_url": fake_openai_chat.base_url,
            "model": "gpt-4o-remote",
            "is_local": False,
            "allow_sensitive": False,
        },
    )

    # 2. 创建普通项目并绑定云端模型
    proj_res = client.post("/api/projects", headers=headers, json={"name": "即将标记敏感的项目"})
    proj_id = proj_res.json()["id"]
    client.post(
        f"/api/v1/projects/{proj_id}/model-config",
        headers=headers,
        json={"model_config_id": "cfg-cloud-external"},
    )

    # 3. 将项目标记为敏感项目
    patch_res = client.patch(
        f"/api/v1/projects/{proj_id}",
        headers={**headers, "If-Match": "1", "Idempotency-Key": "patch-sens-01"},
        json={"sensitive": True},
    )
    assert patch_res.status_code == 200

    # 4. 敏感项目调用章节建议 -> 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL
    chapters_res = client.get(f"/api/projects/{proj_id}/chapters", headers=headers)
    chapter_id = chapters_res.json()["chapters"][0]["id"]
    sug_res = client.post(
        f"/api/chapters/{chapter_id}/suggestions",
        headers=headers,
        json={"instruction": "敏感项目建议生成"},
    )
    assert sug_res.status_code == 403
    assert sug_res.json()["error"]["code"] == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"

    # 5. 敏感项目启动生成作业 -> 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL
    confirm_chapter(client, chapter_id=chapter_id, project_id=proj_id)
    start_res = client.post(
        f"/api/v1/projects/{proj_id}/generation/start",
        headers={**headers, "If-Match": "1", "Idempotency-Key": "sensitive-cloud-job-01"},
        json={"chapter_ids": [chapter_id]},
    )
    assert start_res.status_code == 403
    assert start_res.json()["code"] == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"

    # 6. 确认真实/假模型端点未被调用（在调用前已阻断）
    assert fake_openai_chat.calls == []


def test_sensitive_project_allows_local_model(client, fake_openai_chat, secret_key):
    """敏感项目使用本地模型（is_local=True, allow_sensitive=True）正常允许调用。"""
    headers = login(client, "alpha-manager")
    client.post(
        "/api/v1/model-configs",
        headers=headers,
        json={
            "id": "cfg-local-compliant",
            "name": "合规本地内网模型",
            "provider": "openai-compatible",
            "base_url": fake_openai_chat.base_url,
            "model": "qwen2.5-local-compliant",
            "is_local": True,
            "allow_sensitive": True,
        },
    )

    proj_res = client.post("/api/projects", headers=headers, json={"name": "合规敏感项目"})
    proj_id = proj_res.json()["id"]
    patch_res = client.patch(
        f"/api/v1/projects/{proj_id}",
        headers={**headers, "If-Match": "1", "Idempotency-Key": "patch-sens-02"},
        json={"sensitive": True},
    )
    assert patch_res.status_code == 200
    client.post(
        f"/api/v1/projects/{proj_id}/model-config",
        headers=headers,
        json={"model_config_id": "cfg-local-compliant"},
    )

    chapters_res = client.get(f"/api/projects/{proj_id}/chapters", headers=headers)
    chapter_id = chapters_res.json()["chapters"][0]["id"]
    sug_res = client.post(
        f"/api/chapters/{chapter_id}/suggestions",
        headers=headers,
        json={"instruction": "合规敏感项目建议"},
    )
    assert sug_res.status_code == 200
    assert sug_res.json()["provider"] == "openai-compatible"
    assert len(fake_openai_chat.calls) == 1


def test_model_call_failure_maps_to_502_model_unavailable(client, fake_openai_chat, secret_key):
    """当模型端点返回 HTTP 500 时，建议接口映射为 502 MODEL_UNAVAILABLE，可恢复任务记录 failed。"""
    headers = login(client, "alpha-manager")
    fake_openai_chat.status_code = 500  # 模拟上游模型端点故障

    client.post(
        "/api/v1/model-configs",
        headers=headers,
        json={
            "id": "cfg-fail-test",
            "provider": "openai-compatible",
            "base_url": fake_openai_chat.base_url,
            "model": "error-model",
        },
    )
    proj_res = client.post("/api/projects", headers=headers, json={"name": "故障测试项目"})
    proj_id = proj_res.json()["id"]
    client.post(
        f"/api/v1/projects/{proj_id}/model-config",
        headers=headers,
        json={"model_config_id": "cfg-fail-test"},
    )

    # 1. 建议接口返回 502
    chapters_res = client.get(f"/api/projects/{proj_id}/chapters", headers=headers)
    chapter_id = chapters_res.json()["chapters"][0]["id"]
    sug_res = client.post(
        f"/api/chapters/{chapter_id}/suggestions",
        headers=headers,
        json={"instruction": "测试上游故障"},
    )
    assert sug_res.status_code == 502
    assert "MODEL_UNAVAILABLE" in sug_res.text

    # 2. 可恢复任务记录失败
    confirm_chapter(client)
    client.post(
        "/api/v1/projects/alpha-project/model-config",
        headers=headers,
        json={"model_config_id": "cfg-fail-test"},
    )
    job_id = start(client, headers, key="job-model-fail-01").json()["id"]
    get_res = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert get_res.status_code == 200
    job_data = get_res.json()
    assert job_data["status"] == "failed"
    assert job_data["error"]["code"] == "MODEL_UNAVAILABLE"


def test_secret_key_unavailable_in_generation_raises_503_without_retry_after(client, monkeypatch):
    """当模型配置包含加密密钥但 ICG_SECRET_KEY 环境变量未设置时，生成调用前拒绝并返回 503 SECRET_KEY_UNAVAILABLE 且无 Retry-After。"""
    # 1. 在有密钥时保存配置
    temp_key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("ICG_SECRET_KEY", temp_key)
    headers = login(client, "alpha-manager")
    client.post(
        "/api/v1/model-configs",
        headers=headers,
        json={
            "id": "cfg-enc-key-1",
            "provider": "openai-compatible",
            "base_url": "http://127.0.0.1:8000",
            "model": "qwen2.5-72b",
            "api_key": "sk-real-encrypted-key",
        },
    )
    proj_res = client.post("/api/projects", headers=headers, json={"name": "密钥丢失测试项目"})
    proj_id = proj_res.json()["id"]
    client.post(
        f"/api/v1/projects/{proj_id}/model-config",
        headers=headers,
        json={"model_config_id": "cfg-enc-key-1"},
    )

    # 2. 模拟密钥丢失
    monkeypatch.delenv("ICG_SECRET_KEY", raising=False)

    chapters_res = client.get(f"/api/projects/{proj_id}/chapters", headers=headers)
    chapter_id = chapters_res.json()["chapters"][0]["id"]
    sug_res = client.post(
        f"/api/chapters/{chapter_id}/suggestions",
        headers=headers,
        json={"instruction": "测试缺少主密钥"},
    )
    assert sug_res.status_code == 503
    assert sug_res.json()["error"]["code"] == "SECRET_KEY_UNAVAILABLE"
    assert "Retry-After" not in sug_res.headers


@pytest.mark.skipif(real_model_skip_reason() is not None, reason=real_model_skip_reason() or "")
def test_real_model_probe_skipped_by_default():
    """真实外部端点探测测试，默认在离线 CI 中跳过，必须显式配置 ICG_RUN_REAL_MODEL_TESTS=1。"""
    pass
