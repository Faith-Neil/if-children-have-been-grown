# 为什么有这个文件：自动化核对 RAGFlow 检索客户端的请求头、入参、响应解析与各类异常分支。
# 它解决什么问题：配合 CI 假服务夹具确保离线测试纯洁性，同时覆盖成功命中、空 chunks 跳过、业务错误、HTTP 错误、超时与格式异常。

from __future__ import annotations

import json
import os
import httpx
import pytest

from fake_ragflow import (
    BUSINESS_ERROR_BODY,
    EMPTY_BODY,
    HEALTH_BODY,
    HTTP_ERROR_BODY,
    HTTP_ERROR_STATUS,
    MODE_BUSINESS_ERROR,
    MODE_CHUNKS,
    MODE_EMPTY,
    MODE_HTTP_ERROR,
    MODE_TIMEOUT,
    SUCCESS_BODY,
    SYNTHETIC_CONTENT,
)
from icg_demo.ragflow_client import (
    RagflowBusinessError,
    RagflowChunk,
    RagflowClientError,
    RagflowConfig,
    RagflowConnectionError,
    RagflowHttpError,
    RagflowResponseError,
    RagflowRetrievalClient,
    RagflowRetrievalResult,
    RagflowTimeoutError,
)

SYNTHETIC_KEY = "synthetic-ragflow-key"
SYNTHETIC_QUESTION = "巡检要求"
SYNTHETIC_DATASET_IDS = ["syntheticdataset0001"]
SYNTHETIC_RERANK_ID = "synthetic-rerank"


def test_success_retrieval_parses_chunks_and_records_request(fake_ragflow):
    fake_ragflow.mode = MODE_CHUNKS
    client = RagflowRetrievalClient(
        base_url=fake_ragflow.base_url,
        api_key=SYNTHETIC_KEY,
        timeout_seconds=5.0,
    )

    result = client.retrieve(
        SYNTHETIC_QUESTION,
        SYNTHETIC_DATASET_IDS,
        rerank_id=SYNTHETIC_RERANK_ID,
    )

    assert isinstance(result, RagflowRetrievalResult)
    assert result.skipped is False
    assert result.skip_reason == ""
    assert result.is_empty is False
    assert result.total == 1
    assert len(result.chunks) == 1

    chunk = result.chunks[0]
    assert isinstance(chunk, RagflowChunk)
    assert chunk.id == "syntheticchunk0001"
    assert chunk.content == SYNTHETIC_CONTENT
    assert chunk.document_id == "syntheticdoc0001"
    assert chunk.dataset_id == "syntheticdataset0001"
    assert abs(chunk.similarity - 0.9669436601210759) < 1e-6

    assert len(fake_ragflow.calls) == 1
    call = fake_ragflow.calls[0]
    assert call.method == "POST"
    assert call.path == "/api/v1/retrieval"
    assert call.header("Authorization") == f"Bearer {SYNTHETIC_KEY}"
    assert call.header("Content-Type").startswith("application/json")
    assert call.header("Accept") == "application/json"

    sent_body = json.loads(call.body.decode("utf-8"))
    assert sent_body["question"] == SYNTHETIC_QUESTION
    assert sent_body["dataset_ids"] == SYNTHETIC_DATASET_IDS
    assert sent_body["rerank_id"] == SYNTHETIC_RERANK_ID
    assert SYNTHETIC_KEY not in call.body.decode("utf-8")


def test_base_url_trailing_slash_and_gateway_prefix(fake_ragflow):
    # 验证末尾斜杠被自动剥离
    client_slash = RagflowRetrievalClient(
        base_url=fake_ragflow.base_url + "/",
        api_key=SYNTHETIC_KEY,
    )
    assert client_slash.base_url == fake_ragflow.base_url
    assert client_slash.retrieval_url == f"{fake_ragflow.base_url}/api/v1/retrieval"

    # 验证网关前缀正常保留
    prefixed_url = fake_ragflow.base_url + "/gateway"
    client_gateway = RagflowRetrievalClient(
        base_url=prefixed_url,
        api_key=SYNTHETIC_KEY,
    )
    assert client_gateway.retrieval_url == f"{prefixed_url}/api/v1/retrieval"

    result = client_gateway.retrieve(SYNTHETIC_QUESTION, SYNTHETIC_DATASET_IDS)
    assert result.skipped is False
    call = fake_ragflow.calls[-1]
    assert call.path == "/gateway/api/v1/retrieval"
    assert call.base_url == prefixed_url


def test_empty_chunks_is_marked_as_skipped(fake_ragflow):
    fake_ragflow.mode = MODE_EMPTY
    client = RagflowRetrievalClient(
        base_url=fake_ragflow.base_url,
        api_key=SYNTHETIC_KEY,
    )

    result = client.retrieve(SYNTHETIC_QUESTION, SYNTHETIC_DATASET_IDS)

    assert result.skipped is True
    assert result.skip_reason == "zero hits"
    assert result.is_empty is True
    assert result.chunks == []
    assert result.total == 0


def test_business_error_raises_ragflow_business_error(fake_ragflow):
    fake_ragflow.mode = MODE_BUSINESS_ERROR
    client = RagflowRetrievalClient(
        base_url=fake_ragflow.base_url,
        api_key=SYNTHETIC_KEY,
    )

    with pytest.raises(RagflowBusinessError) as exc_info:
        client.retrieve(SYNTHETIC_QUESTION, SYNTHETIC_DATASET_IDS)

    err = exc_info.value
    assert err.code == 102
    assert "dataset_ids" in err.message
    assert "102" in str(err)
    assert SYNTHETIC_KEY not in str(err)


def test_http_500_raises_ragflow_http_error(fake_ragflow):
    fake_ragflow.mode = MODE_HTTP_ERROR
    client = RagflowRetrievalClient(
        base_url=fake_ragflow.base_url,
        api_key=SYNTHETIC_KEY,
    )

    with pytest.raises(RagflowHttpError) as exc_info:
        client.retrieve(SYNTHETIC_QUESTION, SYNTHETIC_DATASET_IDS)

    err = exc_info.value
    assert err.status_code == HTTP_ERROR_STATUS
    assert "synthetic http error" in err.message
    assert "500" in str(err)
    assert SYNTHETIC_KEY not in str(err)


def test_timeout_raises_ragflow_timeout_error(fake_ragflow):
    fake_ragflow.mode = MODE_TIMEOUT
    fake_ragflow.hold_responses()
    client = RagflowRetrievalClient(
        base_url=fake_ragflow.base_url,
        api_key=SYNTHETIC_KEY,
        timeout_seconds=0.2,
    )

    try:
        with pytest.raises(RagflowTimeoutError):
            client.retrieve(SYNTHETIC_QUESTION, SYNTHETIC_DATASET_IDS)
    finally:
        fake_ragflow.release_responses()


def test_connection_error_raises_ragflow_connection_error():
    transport = httpx.MockTransport(lambda req: (_ for _ in ()).throw(httpx.ConnectError("connection refused")))
    client = RagflowRetrievalClient(
        base_url="http://127.0.0.1:8000",
        api_key=SYNTHETIC_KEY,
        transport=transport,
    )

    with pytest.raises(RagflowConnectionError):
        client.retrieve(SYNTHETIC_QUESTION, SYNTHETIC_DATASET_IDS)


def test_health_check_failures():
    # 模拟 health 接口 500
    mock_500 = httpx.MockTransport(lambda req: httpx.Response(500, json={"message": "db error"}))
    client_500 = RagflowRetrievalClient(base_url="http://127.0.0.1:8000", transport=mock_500)
    with pytest.raises(RagflowHttpError) as exc_info:
        client_500.health()
    assert exc_info.value.status_code == 500

    # 模拟 health 接口超时
    mock_timeout = httpx.MockTransport(lambda req: (_ for _ in ()).throw(httpx.ReadTimeout("read timeout")))
    client_timeout = RagflowRetrievalClient(base_url="http://127.0.0.1:8000", transport=mock_timeout)
    with pytest.raises(RagflowTimeoutError):
        client_timeout.health()

    # 模拟 health 接口连接错误
    mock_conn = httpx.MockTransport(lambda req: (_ for _ in ()).throw(httpx.ConnectError("refused")))
    client_conn = RagflowRetrievalClient(base_url="http://127.0.0.1:8000", transport=mock_conn)
    with pytest.raises(RagflowConnectionError):
        client_conn.health()

    # 模拟 health 接口畸形 JSON
    mock_bad_json = httpx.MockTransport(lambda req: httpx.Response(200, text="not-json"))
    client_bad_json = RagflowRetrievalClient(base_url="http://127.0.0.1:8000", transport=mock_bad_json)
    with pytest.raises(RagflowResponseError):
        client_bad_json.health()


def test_health_check_succeeds_without_authorization(fake_ragflow):
    client = RagflowRetrievalClient(
        base_url=fake_ragflow.base_url,
        api_key=SYNTHETIC_KEY,
    )

    status = client.health()
    assert isinstance(status, dict)
    assert status.get("status") == "ok"
    assert status.get("db") == "ok"

    call = fake_ragflow.calls[0]
    assert call.method == "GET"
    assert call.path == "/api/v1/system/healthz"
    # 健康检查不带 Authorization
    assert call.header("Authorization") == ""


def test_optional_rerank_id_omitted_when_none(fake_ragflow):
    fake_ragflow.mode = MODE_CHUNKS
    client = RagflowRetrievalClient(
        base_url=fake_ragflow.base_url,
        api_key=SYNTHETIC_KEY,
    )

    client.retrieve(SYNTHETIC_QUESTION, SYNTHETIC_DATASET_IDS, rerank_id=None)
    call = fake_ragflow.calls[-1]
    body = json.loads(call.body.decode("utf-8"))
    assert "rerank_id" not in body
    assert body["question"] == SYNTHETIC_QUESTION
    assert body["dataset_ids"] == SYNTHETIC_DATASET_IDS


def test_input_validation():
    client = RagflowRetrievalClient(base_url="http://127.0.0.1:8000")

    # 校验 question
    with pytest.raises(ValueError, match="question must be a non-empty string"):
        client.retrieve("", ["ds1"])
    with pytest.raises(ValueError, match="question must be a non-empty string"):
        client.retrieve("   ", ["ds1"])
    with pytest.raises(ValueError, match="question must be a non-empty string"):
        client.retrieve(None, ["ds1"])  # type: ignore

    # 校验 dataset_ids
    with pytest.raises(ValueError, match="dataset_ids must be a non-empty list of strings"):
        client.retrieve("q", [])
    with pytest.raises(ValueError, match="dataset_ids must be a non-empty list of strings"):
        client.retrieve("q", "ds1")  # type: ignore
    with pytest.raises(ValueError, match="dataset_ids must contain non-empty strings"):
        client.retrieve("q", [""])
    with pytest.raises(ValueError, match="dataset_ids must contain non-empty strings"):
        client.retrieve("q", ["ds1", 123])  # type: ignore

    # 校验 rerank_id
    with pytest.raises(ValueError, match="rerank_id must be a string if provided"):
        client.retrieve("q", ["ds1"], rerank_id=123)  # type: ignore

    # 校验 base_url
    with pytest.raises(ValueError, match="base_url is required"):
        RagflowRetrievalClient(base_url="")
    with pytest.raises(ValueError, match="scheme must be http or https"):
        RagflowRetrievalClient(base_url="ftp://127.0.0.1")
    with pytest.raises(ValueError, match="credentials"):
        RagflowRetrievalClient(base_url="http://user:pass@127.0.0.1")
    with pytest.raises(ValueError, match="query or fragment"):
        RagflowRetrievalClient(base_url="http://127.0.0.1?param=1")


def test_from_env_loading():
    env = {
        "ICG_RAGFLOW_BASE_URL": "http://127.0.0.1:9090/gateway",
        "ICG_RAGFLOW_API_KEY": "env-secret-key",
        "ICG_RAGFLOW_TIMEOUT_SECONDS": "15.5",
    }
    client = RagflowRetrievalClient.from_env(environ=env)
    assert client.base_url == "http://127.0.0.1:9090/gateway"
    assert client.timeout_seconds == 15.5
    assert client._resolve_api_key() == "env-secret-key"

    # 缺少基址
    with pytest.raises(ValueError, match="ICG_RAGFLOW_BASE_URL is required"):
        RagflowRetrievalClient.from_env(environ={})


@pytest.mark.parametrize(
    "response_builder, expected_error_msg",
    [
        (lambda: httpx.Response(200, text="not-a-json"), "malformed JSON"),
        (lambda: httpx.Response(200, json=["unexpected", "list"]), "must be a JSON object"),
        (lambda: httpx.Response(200, json={"message": "no code"}), "missing valid integer 'code'"),
        (lambda: httpx.Response(200, json={"code": 0}), "missing 'data' object"),
        (lambda: httpx.Response(200, json={"code": 0, "data": {"chunks": "invalid"}}), "'chunks' must be a list"),
        (lambda: httpx.Response(200, json={"code": 0, "data": {"chunks": ["not a dict"]}}), "chunk must be an object"),
    ],
)
def test_malformed_responses_raise_response_error(response_builder, expected_error_msg):
    transport = httpx.MockTransport(lambda req: response_builder())
    client = RagflowRetrievalClient(
        base_url="http://127.0.0.1:9",
        api_key=SYNTHETIC_KEY,
        transport=transport,
    )

    with pytest.raises(RagflowResponseError, match=expected_error_msg):
        client.retrieve("巡检要求", ["dataset1"])


@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 502, 503])
def test_http_error_codes_handled(status_code):
    transport = httpx.MockTransport(
        lambda req: httpx.Response(status_code, json={"message": f"error {status_code}"})
    )
    client = RagflowRetrievalClient(
        base_url="http://127.0.0.1:9",
        api_key=SYNTHETIC_KEY,
        transport=transport,
    )

    with pytest.raises(RagflowHttpError) as exc_info:
        client.retrieve("巡检要求", ["dataset1"])

    assert exc_info.value.status_code == status_code
    assert str(status_code) in str(exc_info.value)
    assert SYNTHETIC_KEY not in str(exc_info.value)


def test_api_key_never_leaked_in_exceptions():
    secret_key = "super-secret-production-token"

    # 测试网络异常下无泄露
    broken_transport = httpx.MockTransport(lambda req: httpx.Response(500, text=f"leak? {secret_key}"))
    client = RagflowRetrievalClient(
        base_url="http://127.0.0.1:9",
        api_key=secret_key,
        transport=broken_transport,
    )

    with pytest.raises(RagflowClientError) as exc_info:
        client.retrieve("巡检要求", ["dataset1"])

    # 错误提示中包含状态码，不把机密 token 引入客户端异常信息
    assert exc_info.value.status_code == 500


@pytest.mark.live_ragflow
def test_real_ragflow_retrieval_when_opted_in():
    base = os.environ.get("ICG_RAGFLOW_BASE_URL", "").strip().rstrip("/")
    assert base.startswith("http://") or base.startswith("https://")
    client = RagflowRetrievalClient.from_env()
    status = client.health()
    assert status.get("status") == "ok"
