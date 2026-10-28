# 为什么有这个文件：实现 RAGFlow 检索、数据集管理与知识库文档摄入同步客户端，调用官方 HTTP API（按 RAGFlow 1.0 Go 后端契约，兼容 0.x 响应）。
# 它解决什么问题：把鉴权、路径拼接、chunks 检索、多租户数据集隔离、文档上传/元数据/删除、解析触发、同步状态查询与异常映射封装为统一客户端，落实 B5/B6 内网自建 RAGFlow 闭环。
# 1.0 差异（2026-10-28 用 v1.0.0-rc2 实测）：建数据集须 parse_type=1 + parser_id；文档状态在 ingestion_status；
# 文档元数据用 PATCH meta_fields；删除用 DELETE .../documents {"ids"}；单个数据集/文档用列表接口加 ?id= 过滤。

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Mapping
from urllib.parse import urlsplit

import httpx

RETRIEVAL_SUFFIX = "/api/v1/retrieval"
HEALTH_SUFFIX = "/api/v1/system/healthz"
DATASETS_SUFFIX = "/api/v1/datasets"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_API_KEY_ENV = "ICG_RAGFLOW_API_KEY"
INGEST_SUFFIX = "/api/v1/documents/ingest"


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


def ragflow_run_to_kb_sync_status(run: str | None) -> str:
    """将 RAGFlow 官方文档解析 run 状态映射为 ICG 统一 kb_sync_status。

    对照关系（依据 docs/architecture/ragflow-retrieval-adapter.md）：
    - DONE, 3 -> synced
    - FAIL, 4, CANCEL -> failed
    - UNSTART, 0, RUNNING, 1, SCHEDULE -> unsynced
    """
    r = (run or "").upper().strip()
    if r in {"DONE", "3", "COMPLETED", "SUCCESS"}:
        return "synced"
    elif r in {"FAIL", "4", "CANCEL", "2", "FAILED", "CANCELED", "CANCELLED"}:
        return "failed"
    else:
        return "unsynced"


def document_state(raw: dict[str, Any]) -> str:
    """RAGFlow 1.0 用 ingestion_status，0.x 用 run；两者都可能出现，优先 1.0 字段。"""
    return str(raw.get("ingestion_status") or raw.get("run") or "UNSTART")


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
    document_name: str = ""
    vector_similarity: float = 0.0
    term_similarity: float = 0.0


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


@dataclass(frozen=True)
class RagflowDataset:
    id: str
    name: str
    company_id: str | None = None
    embedding_model: str = ""
    parser_id: str = "general"
    document_count: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RagflowDocument:
    id: str
    name: str
    dataset_id: str
    run: str = "UNSTART"
    progress: float = 0.0
    progress_msg: str = ""
    status: str = "1"
    raw: dict[str, Any] = field(default_factory=dict)
    chunk_count: int = 0
    meta_fields: dict[str, Any] = field(default_factory=dict)

    @property
    def sync_status(self) -> str:
        return ragflow_run_to_kb_sync_status(self.run)


def _document_from(raw: dict[str, Any], dataset_id: str, fallback_name: str = "") -> RagflowDocument:
    progress_raw = raw.get("progress", 0.0)
    message = raw.get("progress_msg", "")
    if isinstance(message, list):
        message = message[-1] if message else ""
    event = raw.get("latest_ingestion_event")
    if not message and isinstance(event, dict):
        message = str(event.get("message", ""))
    return RagflowDocument(
        id=str(raw.get("id", "")),
        name=str(raw.get("name", fallback_name)),
        dataset_id=str(raw.get("dataset_id") or dataset_id).strip(),
        run=document_state(raw),
        progress=float(progress_raw) if isinstance(progress_raw, (int, float)) else 0.0,
        progress_msg=str(message)[:500],
        status=str(raw.get("status", "1")),
        raw=raw,
        chunk_count=int(raw.get("chunk_count") or 0),
        meta_fields=raw.get("meta_fields") if isinstance(raw.get("meta_fields"), dict) else {},
    )


class RagflowRetrievalClient:
    """RAGFlow 客户端：支持只读检索、多租户数据集管理、文档摄入与解析状态同步。"""

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

    @property
    def datasets_url(self) -> str:
        return f"{self.base_url}{DATASETS_SUFFIX}"

    def dataset_url(self, dataset_id: str) -> str:
        return f"{self.base_url}{DATASETS_SUFFIX}/{dataset_id.strip()}"

    def documents_url(self, dataset_id: str) -> str:
        return f"{self.base_url}{DATASETS_SUFFIX}/{dataset_id.strip()}/documents"

    def chunks_url(self, dataset_id: str) -> str:
        return f"{self.base_url}{DATASETS_SUFFIX}/{dataset_id.strip()}/chunks"

    def _resolve_api_key(self) -> str:
        if self._config.api_key is not None:
            return self._config.api_key.strip()
        source = os.environ if self._environ is None else self._environ
        return source.get(self._config.api_key_env, "").strip()

    def _send_request(
        self,
        method: str,
        url: str,
        *,
        json_body: Any = None,
        files: Any = None,
        params: dict[str, Any] | None = None,
        require_auth: bool = True,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {
            "Accept": "application/json",
        }
        if require_auth:
            api_key = self._resolve_api_key()
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
        if json_body is not None and files is None:
            headers["Content-Type"] = "application/json"

        try:
            # trust_env=False：内网 RAGFlow 请求不能被系统代理/VPN 劫持（AGENTS.md 内网隔离红线）。
            with httpx.Client(
                transport=self._transport,
                timeout=self.timeout_seconds,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                m = method.upper()
                if m == "GET":
                    response = client.get(url, headers=headers, params=params)
                elif m == "POST":
                    response = client.post(url, headers=headers, json=json_body, files=files, params=params)
                elif m in ("DELETE", "PATCH", "PUT"):
                    response = client.request(m, url, headers=headers, json=json_body, params=params)
                else:
                    raise ValueError(f"unsupported HTTP method: {method}")
        except httpx.TimeoutException:
            raise RagflowTimeoutError(f"{method} request timed out") from None
        except httpx.TransportError as exc:
            raise RagflowConnectionError(f"{method} transport error: {type(exc).__name__}") from None

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
            raise RagflowResponseError("malformed JSON in response") from None

        if not isinstance(body, dict):
            raise RagflowResponseError("response body must be a JSON object")

        code = body.get("code")
        if code is None or not isinstance(code, int):
            raise RagflowResponseError("response missing valid integer 'code'")

        if code != 0:
            msg = str(body.get("message", ""))
            raise RagflowBusinessError(code, msg)

        return body

    def retrieve(
        self,
        question: str,
        dataset_ids: list[str],
        *,
        rerank_id: str | None = None,
        document_ids: list[str] | None = None,
        page_size: int | None = None,
        similarity_threshold: float | None = None,
        keywords_similarity_weight: float | None = None,
        metadata_condition: dict[str, Any] | None = None,
        highlight: bool | None = None,
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
        if document_ids:
            payload["document_ids"] = [d.strip() for d in document_ids if d and d.strip()]
        if page_size is not None:
            payload["page_size"] = max(1, min(int(page_size), 100))
        if similarity_threshold is not None:
            payload["similarity_threshold"] = float(similarity_threshold)
        if keywords_similarity_weight is not None:
            payload["keywords_similarity_weight"] = float(keywords_similarity_weight)
        if metadata_condition:
            payload["metadata_condition"] = metadata_condition
        if highlight is not None:
            payload["highlight"] = bool(highlight)

        body = self._send_request("POST", self.retrieval_url, json_body=payload)

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
            def _num(key: str) -> float:
                value = item.get(key, 0.0)
                return float(value) if isinstance(value, (int, float)) else 0.0

            chunks.append(
                RagflowChunk(
                    id=str(item.get("id", "")),
                    content=str(item.get("content", "")),
                    document_id=str(item.get("document_id", "")),
                    dataset_id=str(item.get("dataset_id", "")),
                    similarity=_num("similarity"),
                    document_name=str(item.get("document_keyword") or item.get("document_name") or ""),
                    vector_similarity=_num("vector_similarity"),
                    term_similarity=_num("term_similarity"),
                )
            )

        return RagflowRetrievalResult(
            chunks=chunks,
            doc_aggs=safe_doc_aggs,
            total=total,
            skipped=False,
            skip_reason="",
        )

    def create_dataset(
        self,
        name: str,
        *,
        company_id: str | None = None,
        embedding_model: str | None = None,
        parser_id: str = "general",
    ) -> RagflowDataset:
        """创建数据集。若传入 company_id，自动注入租户前缀强隔离命名空间。"""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")

        clean_name = name.strip()
        if company_id:
            clean_cid = company_id.strip()
            if not clean_name.startswith(f"{clean_cid}::"):
                clean_name = f"{clean_cid}::{clean_name}"

        # RAGFlow 1.0：parse_type=1 表示内置解析器，必须同时给 parser_id。
        payload: dict[str, Any] = {
            "name": clean_name,
            "parse_type": 1,
            "parser_id": parser_id.strip() or "general",
            "language": "Chinese",
        }
        if embedding_model:
            payload["embedding_model"] = embedding_model.strip()

        body = self._send_request("POST", self.datasets_url, json_body=payload)
        data = body.get("data")
        if not isinstance(data, dict):
            raise RagflowResponseError("create_dataset response missing 'data' object")

        ds_id = str(data.get("id", ""))
        ds_name = str(data.get("name", clean_name))
        detected_cid = company_id
        if "::" in ds_name:
            detected_cid = ds_name.split("::", 1)[0]

        return RagflowDataset(
            id=ds_id,
            name=ds_name,
            company_id=detected_cid,
            embedding_model=str(data.get("embedding_model", "")),
            parser_id=str(data.get("parser_id", parser_id)),
            document_count=int(data.get("document_count", 0)),
            raw=data,
        )

    def list_datasets(
        self,
        *,
        company_id: str | None = None,
        page: int = 1,
        page_size: int = 30,
    ) -> list[RagflowDataset]:
        """列出数据集。若传入 company_id，执行租户过滤，绝不展示其他公司的知识库。"""
        params = {"page": page, "page_size": page_size}
        body = self._send_request("GET", self.datasets_url, params=params)
        data = body.get("data")
        raw_list: list[dict[str, Any]] = []
        if isinstance(data, list):
            raw_list = [d for d in data if isinstance(d, dict)]
        elif isinstance(data, dict):
            items = data.get("datasets") or data.get("list") or []
            if isinstance(items, list):
                raw_list = [d for d in items if isinstance(d, dict)]

        datasets: list[RagflowDataset] = []
        for item in raw_list:
            ds_id = str(item.get("id", ""))
            ds_name = str(item.get("name", ""))
            detected_cid = None
            if "::" in ds_name:
                detected_cid = ds_name.split("::", 1)[0]
            elif item.get("company_id"):
                detected_cid = str(item["company_id"])

            if company_id:
                clean_cid = company_id.strip()
                if detected_cid != clean_cid and not ds_name.startswith(f"{clean_cid}::"):
                    continue

            datasets.append(
                RagflowDataset(
                    id=ds_id,
                    name=ds_name,
                    company_id=detected_cid,
                    embedding_model=str(item.get("embedding_model", "")),
                    parser_id=str(item.get("parser_id", "general")),
                    document_count=int(item.get("document_count", 0)),
                    raw=item,
                )
            )
        return datasets

    def get_dataset(
        self,
        dataset_id: str,
        *,
        company_id: str | None = None,
    ) -> RagflowDataset:
        """获取单个数据集信息。若传入 company_id，校验租户归属，防止越权访问。"""
        if not isinstance(dataset_id, str) or not dataset_id.strip():
            raise ValueError("dataset_id must be a non-empty string")

        try:
            body = self._send_request("GET", self.datasets_url, params={"id": dataset_id.strip()})
            data = body.get("data")
            if isinstance(data, list):
                data = next((d for d in data if isinstance(d, dict) and str(d.get("id")) == dataset_id.strip()), None)
            if not isinstance(data, dict):
                raise RagflowBusinessError(102, f"dataset {dataset_id} not found")
        except (RagflowHttpError, RagflowBusinessError):
            all_ds = self.list_datasets(company_id=company_id)
            for ds in all_ds:
                if ds.id == dataset_id.strip():
                    return ds
            raise RagflowBusinessError(102, f"dataset {dataset_id} not found")

        ds_name = str(data.get("name", ""))
        detected_cid = None
        if "::" in ds_name:
            detected_cid = ds_name.split("::", 1)[0]
        elif data.get("company_id"):
            detected_cid = str(data["company_id"])

        if company_id:
            clean_cid = company_id.strip()
            if detected_cid != clean_cid and not ds_name.startswith(f"{clean_cid}::"):
                raise RagflowBusinessError(102, f"dataset {dataset_id} does not belong to company {company_id}")

        return RagflowDataset(
            id=str(data.get("id", dataset_id)),
            name=ds_name,
            company_id=detected_cid,
            embedding_model=str(data.get("embedding_model", "")),
            parser_id=str(data.get("parser_id", "general")),
            document_count=int(data.get("document_count", 0)),
            raw=data,
        )

    def upload_document(
        self,
        dataset_id: str,
        name: str,
        content: str | bytes,
        *,
        company_id: str | None = None,
        parser_id: str | None = None,
    ) -> RagflowDocument:
        """上传知识库文档到指定数据集。支持租户强隔离校验。"""
        if not isinstance(dataset_id, str) or not dataset_id.strip():
            raise ValueError("dataset_id must be a non-empty string")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")

        if company_id:
            self.get_dataset(dataset_id, company_id=company_id)

        raw_bytes = content.encode("utf-8") if isinstance(content, str) else content
        media = "text/markdown" if name.strip().lower().endswith((".md", ".markdown")) else "text/plain"
        files = {"file": (name.strip(), raw_bytes, media)}
        url = self.documents_url(dataset_id)
        # 1.0 上传不接受 parser_id 查询参数；解析方式继承数据集，个别文档用 update_document 调整。
        body = self._send_request("POST", url, files=files)
        data = body.get("data")
        doc_dict: dict[str, Any] = {}
        if isinstance(data, list) and data:
            doc_dict = data[0] if isinstance(data[0], dict) else {}
        elif isinstance(data, dict):
            doc_dict = data

        if not doc_dict.get("id"):
            raise RagflowResponseError("upload_document response missing document id")
        return _document_from(doc_dict, dataset_id, name.strip())

    def list_documents(
        self,
        dataset_id: str,
        *,
        run: str | None = None,
        page: int = 1,
        page_size: int = 30,
        document_id: str | None = None,
    ) -> list[RagflowDocument]:
        """查询指定数据集内的文档列表。"""
        if not isinstance(dataset_id, str) or not dataset_id.strip():
            raise ValueError("dataset_id must be a non-empty string")

        url = self.documents_url(dataset_id)
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if run:
            params["run"] = run.strip()
        if document_id:
            params["id"] = document_id.strip()

        body = self._send_request("GET", url, params=params)
        data = body.get("data")
        raw_list: list[dict[str, Any]] = []
        if isinstance(data, list):
            raw_list = [d for d in data if isinstance(d, dict)]
        elif isinstance(data, dict):
            docs = data.get("docs") or data.get("documents") or data.get("list") or []
            if isinstance(docs, list):
                raw_list = [d for d in docs if isinstance(d, dict)]

        return [_document_from(d, dataset_id) for d in raw_list]

    def get_document_status(
        self,
        dataset_id: str,
        document_id: str,
    ) -> RagflowDocument:
        """查询单个文档解析状态（列表接口 ?id= 精确过滤，不受分页限制）。"""
        docs = self.list_documents(dataset_id, document_id=document_id)
        for d in docs:
            if d.id == document_id.strip():
                return d
        raise RagflowBusinessError(102, f"document {document_id} not found in dataset {dataset_id}")

    def update_document(
        self,
        dataset_id: str,
        document_id: str,
        *,
        meta_fields: dict[str, Any] | None = None,
        enabled: bool | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        """PATCH 文档：写入元数据（公司、资料ID、版本、类别等）或启停用。不触发重新解析。"""
        payload: dict[str, Any] = {}
        if meta_fields is not None:
            payload["meta_fields"] = {str(k): ("" if v is None else str(v)) for k, v in meta_fields.items()}
        if enabled is not None:
            payload["enabled"] = 1 if enabled else 0
        if name:
            payload["name"] = name
        if not payload:
            return {}
        body = self._send_request("PATCH", f"{self.documents_url(dataset_id)}/{document_id.strip()}", json_body=payload)
        data = body.get("data")
        return data if isinstance(data, dict) else {}

    def delete_documents(self, dataset_id: str, document_ids: list[str]) -> int:
        """删除文档及其分块。ids 为空时什么都不删（绝不发送 delete_all）。"""
        ids = [d.strip() for d in document_ids if d and d.strip()]
        if not ids:
            return 0
        body = self._send_request("DELETE", self.documents_url(dataset_id), json_body={"ids": ids})
        data = body.get("data")
        if isinstance(data, dict) and isinstance(data.get("deleted"), int):
            return data["deleted"]
        return len(ids)

    def trigger_parse(
        self,
        dataset_id: str,
        document_ids: list[str],
    ) -> bool:
        """调用 POST /api/v1/datasets/{dataset_id}/chunks 触发内置文档切块与解析。"""
        if not isinstance(dataset_id, str) or not dataset_id.strip():
            raise ValueError("dataset_id must be a non-empty string")
        if not isinstance(document_ids, list) or not document_ids:
            raise ValueError("document_ids must be a non-empty list of strings")

        url = self.chunks_url(dataset_id)
        ids = [d.strip() for d in document_ids]
        try:
            body = self._send_request("POST", url, json_body={"document_ids": ids})
        except RagflowBusinessError as error:
            # 使用摄入流水线的数据集不支持内置解析接口，改用 1.0 的 /documents/ingest。
            if "pipeline" not in (error.message or "").lower():
                raise
            body = self._send_request("POST", f"{self.base_url}{INGEST_SUFFIX}",
                                      json_body={"doc_ids": ids, "run": "1"})
        return body.get("code") == 0

    def health(self) -> dict[str, Any]:
        """健康检查 GET {base_url}/api/v1/system/healthz，不带 Authorization。"""
        try:
            with httpx.Client(
                transport=self._transport,
                timeout=self.timeout_seconds,
                follow_redirects=False,
                trust_env=False,
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


# 兼容别名
RagflowClient = RagflowRetrievalClient
