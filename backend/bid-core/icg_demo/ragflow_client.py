# 为什么有这个文件：实现只读的 RAGFlow 检索客户端，调用官方 POST /api/v1/retrieval 接口。
# 它解决什么问题：把鉴权、路径拼接、chunks 解析、非零业务码、HTTP 错误、超时与空 chunks 跳过封装为统一客户端，供证据候选层消费。

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlsplit

import httpx

RETRIEVAL_SUFFIX = "/api/v1/retrieval"
HEALTH_SUFFIX = "/api/v1/system/healthz"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_API_KEY_ENV = "ICG_RAGFLOW_API_KEY"


class RagflowClientError(Exception):
    """RAGFlow 客户端异常基类。异常信息不包含 API Key 等机密信息。"""


class RagflowHttpError(RagflowClientError):
    """HTTP 状态码非 200 异常。"""

    def __init__(self, status_code: int, message: str = "") -> None:
        self.status_code = status_code
        self.message = message
        detail = f": {message}" if message else ""
        super().__init__(f"HTTP {status_code}{detail}")


class RagflowBusinessError(RagflowClientError):
    """RAGFlow 业务返回码非 0 异常。"""

    def __init__(self, code: int, message: str = "") -> None:
        self.code = code
        self.message = message
        detail = f": {message}" if message else ""
        super().__init__(f"RAGFlow business error {code}{detail}")


class RagflowTimeoutError(RagflowClientError):
    """请求超时异常。"""


class RagflowConnectionError(RagflowClientError):
    """网络连接或传输层异常。"""


class RagflowResponseError(RagflowClientError):
    """响应解析或结构异常（非预期 JSON 或缺少必要字段）。"""


def _validate_base_url(base_url: str) -> str:
    cleaned = base_url.strip()
    if not cleaned:
        raise ValueError("base_url is required")
    parsed = urlsplit(cleaned)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("base_url scheme must be http or https")
    if not parsed.netloc:
        raise ValueError("base_url must have a valid host")
    if parsed.username or parsed.password:
        raise ValueError("base_url must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("base_url must not contain query or fragment")
    return cleaned.rstrip("/")


@dataclass(frozen=True)
class RagflowConfig:
    base_url: str
    api_key_env: str = DEFAULT_API_KEY_ENV
    api_key: str | None = None
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_url", _validate_base_url(self.base_url))
        if self.timeout_seconds <= 0 or self.timeout_seconds > 600:
            raise ValueError("timeout_seconds must be greater than 0 and at most 600")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> RagflowConfig:
        source = os.environ if environ is None else environ
        base_url = source.get("ICG_RAGFLOW_BASE_URL", "").strip()
        if not base_url:
            raise ValueError("ICG_RAGFLOW_BASE_URL is required")
        timeout_raw = source.get("ICG_RAGFLOW_TIMEOUT_SECONDS", "").strip()
        timeout = float(timeout_raw) if timeout_raw else DEFAULT_TIMEOUT_SECONDS
        api_key_env = source.get("ICG_RAGFLOW_API_KEY_ENV", "").strip() or DEFAULT_API_KEY_ENV
        return cls(
            base_url=base_url,
            api_key_env=api_key_env,
            timeout_seconds=timeout,
        )


@dataclass(frozen=True)
class RagflowChunk:
    id: str
    content: str
    document_id: str
    dataset_id: str
    similarity: float


@dataclass(frozen=True)
class RagflowRetrievalResult:
    chunks: list[RagflowChunk]
    doc_aggs: list[dict[str, Any]]
    total: int
    skipped: bool = False
    skip_reason: str = ""

    @property
    def is_empty(self) -> bool:
        return len(self.chunks) == 0


class RagflowRetrievalClient:
    """只读 RAGFlow 检索客户端。

    调用 POST {base_url}/api/v1/retrieval 接口。
    请求头携带 Authorization: Bearer <token>。
    请求体只携带 question, dataset_ids 以及可选的 rerank_id。
    解析返回的 chunks；非零业务码、HTTP 4xx/5xx 与超时转换为相应异常；
    空 chunks 记为 skipped=True、skip_reason='zero hits'，不伪装为成功的空候选列表。
    """

    def __init__(
        self,
        config: RagflowConfig | None = None,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        api_key_env: str | None = None,
        timeout_seconds: float | None = None,
        transport: httpx.BaseTransport | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self._environ = environ
        self._transport = transport

        if config is not None:
            self._config = config
        else:
            effective_base = base_url or ""
            effective_api_key_env = api_key_env or DEFAULT_API_KEY_ENV
            effective_timeout = timeout_seconds if timeout_seconds is not None else DEFAULT_TIMEOUT_SECONDS
            self._config = RagflowConfig(
                base_url=effective_base,
                api_key_env=effective_api_key_env,
                api_key=api_key,
                timeout_seconds=effective_timeout,
            )

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> RagflowRetrievalClient:
        config = RagflowConfig.from_env(environ=environ)
        return cls(config=config, transport=transport, environ=environ)

    @property
    def base_url(self) -> str:
        return self._config.base_url

    @property
    def timeout_seconds(self) -> float:
        return self._config.timeout_seconds

    @property
    def retrieval_url(self) -> str:
        return f"{self.base_url}{RETRIEVAL_SUFFIX}"

    @property
    def health_url(self) -> str:
        return f"{self.base_url}{HEALTH_SUFFIX}"

    def _resolve_api_key(self) -> str:
        if self._config.api_key is not None:
            return self._config.api_key.strip()
        source = os.environ if self._environ is None else self._environ
        return source.get(self._config.api_key_env, "").strip()

    def retrieve(
        self,
        question: str,
        dataset_ids: list[str],
        *,
        rerank_id: str | None = None,
    ) -> RagflowRetrievalResult:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must be a non-empty string")
        if not isinstance(dataset_ids, list) or not dataset_ids:
            raise ValueError("dataset_ids must be a non-empty list of strings")
        if any(not isinstance(did, str) or not did.strip() for did in dataset_ids):
            raise ValueError("dataset_ids must contain non-empty strings")
        if rerank_id is not None and not isinstance(rerank_id, str):
            raise ValueError("rerank_id must be a string if provided")

        payload: dict[str, Any] = {
            "question": question.strip(),
            "dataset_ids": [did.strip() for did in dataset_ids],
        }
        if rerank_id is not None and rerank_id.strip():
            payload["rerank_id"] = rerank_id.strip()

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        api_key = self._resolve_api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            with httpx.Client(
                transport=self._transport,
                timeout=self.timeout_seconds,
                follow_redirects=False,
            ) as client:
                response = client.post(self.retrieval_url, headers=headers, json=payload)
        except httpx.TimeoutException:
            raise RagflowTimeoutError("retrieval request timed out") from None
        except httpx.TransportError as exc:
            raise RagflowConnectionError(f"retrieval transport error: {type(exc).__name__}") from None

        if response.status_code != 200:
            error_msg = ""
            try:
                err_body = response.json()
                if isinstance(err_body, dict):
                    error_msg = str(err_body.get("message", ""))
            except Exception:
                pass
            raise RagflowHttpError(response.status_code, error_msg)

        try:
            body = response.json()
        except ValueError:
            raise RagflowResponseError("malformed JSON in retrieval response") from None

        if not isinstance(body, dict):
            raise RagflowResponseError("retrieval response body must be a JSON object")

        code = body.get("code")
        if code is None or not isinstance(code, int):
            raise RagflowResponseError("retrieval response missing valid integer 'code'")

        if code != 0:
            msg = str(body.get("message", ""))
            raise RagflowBusinessError(code, msg)

        data = body.get("data")
        if not isinstance(data, dict):
            raise RagflowResponseError("retrieval response missing 'data' object")

        raw_chunks = data.get("chunks")
        if not isinstance(raw_chunks, list):
            raise RagflowResponseError("retrieval response 'chunks' must be a list")

        doc_aggs = data.get("doc_aggs")
        safe_doc_aggs = [agg for agg in doc_aggs if isinstance(agg, dict)] if isinstance(doc_aggs, list) else []

        raw_total = data.get("total")
        total = int(raw_total) if isinstance(raw_total, (int, float)) else len(raw_chunks)

        if len(raw_chunks) == 0:
            return RagflowRetrievalResult(
                chunks=[],
                doc_aggs=safe_doc_aggs,
                total=total,
                skipped=True,
                skip_reason="zero hits",
            )

        chunks: list[RagflowChunk] = []
        for item in raw_chunks:
            if not isinstance(item, dict):
                raise RagflowResponseError("retrieval response chunk must be an object")
            raw_sim = item.get("similarity", 0.0)
            sim = float(raw_sim) if isinstance(raw_sim, (int, float)) else 0.0
            chunks.append(
                RagflowChunk(
                    id=str(item.get("id", "")),
                    content=str(item.get("content", "")),
                    document_id=str(item.get("document_id", "")),
                    dataset_id=str(item.get("dataset_id", "")),
                    similarity=sim,
                )
            )

        return RagflowRetrievalResult(
            chunks=chunks,
            doc_aggs=safe_doc_aggs,
            total=total,
            skipped=False,
            skip_reason="",
        )

    def health(self) -> dict[str, Any]:
        """健康检查 GET {base_url}/api/v1/system/healthz，不带 Authorization。"""
        try:
            with httpx.Client(
                transport=self._transport,
                timeout=self.timeout_seconds,
                follow_redirects=False,
            ) as client:
                response = client.get(self.health_url, headers={"Accept": "application/json"})
        except httpx.TimeoutException:
            raise RagflowTimeoutError("health request timed out") from None
        except httpx.TransportError as exc:
            raise RagflowConnectionError(f"health transport error: {type(exc).__name__}") from None

        if response.status_code != 200:
            raise RagflowHttpError(response.status_code, "health check failed")

        try:
            body = response.json()
        except ValueError:
            raise RagflowResponseError("malformed JSON in health response") from None

        if not isinstance(body, dict):
            raise RagflowResponseError("health response must be a JSON object")

        return body
