# 为什么有这个文件：用合成响应核对 OpenAI 兼容模型适配器的成功和失败契约。
# 它解决什么问题：避免未接通内网时把超时、错误或空回复当成可用建议，或让敏感项目绕过本地门禁。

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from icg_demo.adapters import DemoModelProvider
from icg_demo.main import create_app
from icg_demo.openai_model import (
    ModelCallError, OpenAICompatibleConfig, OpenAICompatibleModelProvider, openai_provider_from_environment,
)
from test_reference_flow import ProjectFlow


CHAPTER = "alpha-tech"
SYNTHETIC_KEY = "synthetic-test-key"
SYNTHETIC_TEXT = "合成模型候选，仍须人工核对。"


def config(**overrides):
    values = dict(base_url="http://127.0.0.1:9", model="synthetic-qwen",
                  api_key_env="ICG_SYNTHETIC_MODEL_KEY", timeout_seconds=2.0,
                  max_tokens=128, retries=0, is_local=True)
    values.update(overrides)
    return OpenAICompatibleConfig(**values)


def provider(handler, **overrides):
    calls = []

    def transport_handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        result = handler(request, len(calls))
        if isinstance(result, Exception):
            raise result
        return result

    actual = OpenAICompatibleModelProvider(
        config(**overrides), transport=httpx.MockTransport(transport_handler),
        environ={"ICG_SYNTHETIC_MODEL_KEY": SYNTHETIC_KEY})
    return actual, calls


def success_body(text=SYNTHETIC_TEXT):
    return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": text}}]})


def assert_request(request: httpx.Request, instruction, content):
    assert request.method == "POST"
    assert str(request.url) == "http://127.0.0.1:9/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer " + SYNTHETIC_KEY
    payload = json.loads(request.content.decode())
    assert payload["model"] == "synthetic-qwen"
    assert payload["stream"] is False
    assert payload["max_tokens"] == 128
    assert payload["messages"] == [
        {"role": "system", "content": instruction},
        {"role": "user", "content": content},
    ]
    assert SYNTHETIC_KEY not in request.content.decode()


def test_success_returns_assistant_text_without_inventing_a_suffix():
    model, calls = provider(lambda request, index: success_body("  合成建议保留原文空格。  "))
    assert model.suggest("补充巡检", "甲公司合成正文") == "  合成建议保留原文空格。  "
    assert_request(calls[0], "补充巡检", "甲公司合成正文")
    assert model.name == "openai-compatible" and model.is_real_model is True and model.is_local is True


def test_chat_url_appends_one_v1_path():
    assert config(base_url="http://127.0.0.1:9/").chat_completions_url == "http://127.0.0.1:9/v1/chat/completions"
    assert config(base_url="http://127.0.0.1:9/gateway").chat_completions_url == "http://127.0.0.1:9/gateway/v1/chat/completions"


@pytest.mark.parametrize("status", [401, 403, 404])
def test_non_200_does_not_retry_or_return_text(status):
    model, calls = provider(lambda request, index: httpx.Response(status, text="synthetic-failure"), retries=2)
    with pytest.raises(ModelCallError, match=f"HTTP {status}"):
        model.suggest("补充巡检", "甲公司合成正文")
    assert len(calls) == 1


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
def test_transient_http_status_retries_then_fails(status):
    model, calls = provider(lambda request, index: httpx.Response(status, text="busy"), retries=1)
    with pytest.raises(ModelCallError, match="model call failed") as caught:
        model.suggest("补充巡检", "secret-content")
    assert len(calls) == 2
    assert "secret-content" not in str(caught.value) and "busy" not in str(caught.value)


def test_timeout_then_success_uses_only_the_real_response():
    def handler(request, index):
        if index == 1:
            return httpx.ReadTimeout("synthetic timeout")
        return success_body()

    model, calls = provider(handler, retries=1)
    assert model.suggest("补充巡检", "甲公司合成正文") == SYNTHETIC_TEXT
    assert len(calls) == 2


def test_timeout_exhaustion_does_not_fabricate_success():
    model, calls = provider(lambda request, index: httpx.ConnectError("synthetic connect"), retries=1)
    with pytest.raises(ModelCallError, match="model call failed") as caught:
        model.suggest("instruction-secret", "content-secret")
    assert len(calls) == 2
    message = str(caught.value)
    assert SYNTHETIC_KEY not in message and "content-secret" not in message and "instruction-secret" not in message


@pytest.mark.parametrize("body", [b"{", b'"text"', b"[]", b'{"choices":[]}', b'{"choices":[{"message":{}}]}',
                                   b'{"choices":[{"message":{"content":""}}]}',
                                   b'{"choices":[{"message":{"content":"   "}}]}',
                                   b'{"choices":[{"message":{"content":["part"]}}]}'])
def test_malformed_or_empty_success_body_is_not_accepted(body):
    model, calls = provider(lambda request, index: httpx.Response(200, content=body), retries=2)
    with pytest.raises(ModelCallError):
        model.suggest("补充巡检", "甲公司合成正文")
    assert len(calls) == 1


def test_redirect_is_not_followed():
    model, calls = provider(lambda request, index: httpx.Response(302, headers={"Location": "http://127.0.0.1:9/elsewhere"}))
    with pytest.raises(ModelCallError, match="HTTP 302"):
        model.suggest("补充巡检", "甲公司合成正文")
    assert len(calls) == 1


def test_missing_api_key_omits_authorization_header():
    captured = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return success_body()

    model = OpenAICompatibleModelProvider(config(), transport=httpx.MockTransport(handler), environ={})
    assert model.suggest("补充巡检", "甲公司合成正文") == SYNTHETIC_TEXT
    assert "authorization" not in {key.lower() for key in captured[0].headers}


def test_http_failure_uses_existing_unavailable_path_and_keeps_chapter():
    model, calls = provider(lambda request, index: httpx.Response(500, text="synthetic"), retries=0)
    with TestClient(create_app(model_provider=model)) as client:
        login = client.post("/api/demo/login", json={"account_id": "alpha-editor"})
        headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        before = client.get(f"/api/chapters/{CHAPTER}", headers=headers).json()
        response = client.post(f"/api/chapters/{CHAPTER}/suggestions", headers=headers,
                               json={"instruction": "补充巡检"})
        after = client.get(f"/api/chapters/{CHAPTER}", headers=headers).json()
    assert response.status_code == 502, response.text
    assert response.json()["error"]["code"] == "MODEL_UNAVAILABLE"
    assert SYNTHETIC_KEY not in response.text and "synthetic" not in response.text
    assert after["content"] == before["content"] and after["revision"] == before["revision"]
    assert len(calls) == 1


@pytest.mark.parametrize("local,expected", [(False, 409), (True, 200)])
def test_sensitive_gate_uses_provider_is_local(local, expected):
    model, calls = provider(lambda request, index: success_body(), is_local=local, retries=0)
    with TestClient(create_app(model_provider=model)) as client:
        flow = ProjectFlow(client).ready()
        flow.write("", {"sensitive": True}, "PATCH")
        flow.confirm_plan()
        chapter = flow.state()["chapters"][0]
        response = client.post(f"/api/chapters/{chapter['id']}/suggestions", headers=flow.headers,
                               json={"instruction": "依据合成正文提出建议"})
        assert response.status_code == expected, response.text
        generated = flow.write("/generate", {}, expected=expected)
    if local:
        assert response.json()["provider"] == "openai-compatible"
        assert response.json()["is_real_model"] is True
        assert len(calls) == 3
        assert generated["job"]["status"] == "completed"
        assert generated["chapters"]
        for request in calls:
            assert request.headers["authorization"] == "Bearer " + SYNTHETIC_KEY
            assert str(request.url).endswith("/v1/chat/completions")
    else:
        assert response.json()["error"]["code"] == "LOCAL_MODEL_REQUIRED"
        assert generated["code"] == "LOCAL_MODEL_REQUIRED"
        assert calls == []


def test_create_app_keeps_demo_until_configuration_is_explicit(monkeypatch):
    monkeypatch.setenv("ICG_MODEL_PROVIDER", "openai-compatible")
    monkeypatch.setenv("ICG_MODEL_BASE_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("ICG_MODEL_NAME", "synthetic-qwen")
    monkeypatch.setenv("ICG_MODEL_IS_LOCAL", "true")
    implicit = create_app()
    assert isinstance(implicit.state.service.model_provider, DemoModelProvider)
    explicit = create_app(use_configured_model=True)
    selected = explicit.state.service.model_provider
    assert isinstance(selected, OpenAICompatibleModelProvider)
    assert selected.is_real_model is True and selected.is_local is True and selected.name == "openai-compatible"


def test_explicit_switch_rejects_incomplete_config_instead_of_falling_back(monkeypatch):
    monkeypatch.setenv("ICG_MODEL_PROVIDER", "openai-compatible")
    monkeypatch.delenv("ICG_MODEL_BASE_URL", raising=False)
    monkeypatch.setenv("ICG_MODEL_NAME", "synthetic-qwen")
    monkeypatch.setenv("ICG_MODEL_IS_LOCAL", "false")
    with pytest.raises(ValueError, match="ICG_MODEL_BASE_URL"):
        create_app(use_configured_model=True)
    assert openai_provider_from_environment({"ICG_MODEL_PROVIDER": "demo"}) is None


def test_environment_reader_uses_documented_defaults_and_rejects_embedded_secrets():
    selected = OpenAICompatibleConfig.from_env({
        "ICG_MODEL_BASE_URL": "https://model.example",
        "ICG_MODEL_NAME": "company-qwen",
        "ICG_MODEL_IS_LOCAL": "false",
    })
    assert selected.api_key_env == "ICG_MODEL_API_KEY"
    assert selected.timeout_seconds == 60 and selected.max_tokens == 1024 and selected.retries == 1
    assert selected.is_local is False
    with pytest.raises(ValueError):
        OpenAICompatibleConfig.from_env({
            "ICG_MODEL_BASE_URL": "http://user:secret@127.0.0.1:9",
            "ICG_MODEL_NAME": "company-qwen",
            "ICG_MODEL_IS_LOCAL": "true",
        })


def test_unknown_provider_name_is_rejected():
    with pytest.raises(ValueError, match="openai-compatible"):
        openai_provider_from_environment({"ICG_MODEL_PROVIDER": "pgvector"})
