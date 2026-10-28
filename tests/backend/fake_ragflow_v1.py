# 为什么有这个文件：按实测的 RAGFlow 1.0 接口（v1.0.0-rc2）做一个进程内假服务，供知识库同步/检索测试使用。
# 它解决什么问题：旧 fake_ragflow 只回固定分块，无法验证“上传→解析→按文档过滤检索→删除旧版本”的完整闭环。
# 字段与行为来自对真实实例的探测：parse_type 必填、ingestion_status、?id= 过滤、PATCH meta_fields、DELETE {"ids"}。

from __future__ import annotations

import json
import re
import threading
from typing import Any
from uuid import uuid4

import httpx

from icg.infra.ragflow_client import RagflowRetrievalClient

FAIL_MARKER = "[[fake-parse-fail]]"


def _bigrams(text: str) -> set[str]:
    compact = re.sub(r"\s+", "", text.casefold())
    return {compact[i:i + 2] for i in range(len(compact) - 1)} if len(compact) > 1 else {compact}


class FakeRagflowV1:
    def __init__(self, *, async_parse: bool = False, api_key: str = "fake-key") -> None:
        self.api_key = api_key
        self.async_parse = async_parse
        self.datasets: dict[str, dict] = {}
        self.documents: dict[str, dict] = {}
        self.calls: list[tuple[str, str, Any]] = []
        self.fail_uploads = False
        self.fail_retrieval = False
        self.fail_deletes = False
        self._lock = threading.Lock()
        self._seq = 0
        self.transport = httpx.MockTransport(self._handle)

    # ---------- 测试辅助 ----------

    def client(self) -> RagflowRetrievalClient:
        return RagflowRetrievalClient(base_url="http://ragflow.test", api_key=self.api_key, transport=self.transport)

    def finish_parsing(self) -> None:
        with self._lock:
            for doc in self.documents.values():
                if doc["ingestion_status"] in ("SCHEDULED", "RUNNING"):
                    self._parse(doc)

    def docs_in(self, dataset_id: str) -> list[dict]:
        return [d for d in self.documents.values() if d["dataset_id"] == dataset_id]

    # ---------- 内部 ----------

    def _id(self, prefix: str) -> str:
        # 与真实 RAGFlow 一样用全局唯一 id：持久化仓储跨测试保留索引时不会撞上旧 id。
        self._seq += 1
        return f"{prefix}{self._seq:04d}{uuid4().hex[:8]}"

    def _parse(self, doc: dict) -> None:
        if FAIL_MARKER in doc["content"]:
            doc.update(ingestion_status="FAILED", progress=0.0, progress_msg="synthetic parse failure", chunk_count=0)
            doc["chunks"] = []
            return
        # 按空行切块，模拟 general 解析器。
        parts = [p.strip() for p in re.split(r"\n\s*\n", doc["content"]) if p.strip()]
        doc["chunks"] = [{"id": self._id("chunk"), "content": p} for p in parts]
        doc.update(ingestion_status="COMPLETED", progress=1.0, progress_msg="", chunk_count=len(parts))

    @staticmethod
    def _ok(data: Any) -> httpx.Response:
        return httpx.Response(200, json={"code": 0, "data": data})

    @staticmethod
    def _err(code: int, message: str) -> httpx.Response:
        return httpx.Response(200, json={"code": code, "message": message})

    def _public_doc(self, doc: dict) -> dict:
        return {k: doc[k] for k in ("id", "name", "dataset_id", "ingestion_status", "progress", "progress_msg",
                                     "chunk_count", "meta_fields", "enabled")} | {"run": None}

    def _handle(self, request: httpx.Request) -> httpx.Response:
        if request.headers.get("Authorization") != f"Bearer {self.api_key}":
            return self._err(109, "Authentication error: API key is invalid!")
        path = request.url.path
        method = request.method
        body: Any = None
        if request.content and request.headers.get("content-type", "").startswith("application/json"):
            body = json.loads(request.content)
        self.calls.append((method, path, body))
        with self._lock:
            if path == "/api/v1/retrieval" and method == "POST":
                return self._retrieval(body or {})
            if path == "/api/v1/datasets":
                return self._datasets(request, method, body)
            m = re.fullmatch(r"/api/v1/datasets/([^/]+)/documents(?:/([^/]+))?", path)
            if m:
                return self._documents(request, method, m.group(1), m.group(2), body)
            m = re.fullmatch(r"/api/v1/datasets/([^/]+)/chunks", path)
            if m and method == "POST":
                for doc_id in (body or {}).get("document_ids", []):
                    doc = self.documents.get(doc_id)
                    if doc is None:
                        return self._err(102, f"document {doc_id} not found")
                    doc["ingestion_status"] = "SCHEDULED"
                    if not self.async_parse:
                        self._parse(doc)
                return self._ok(True)
        return httpx.Response(404, json={"message": "not found"})

    def _datasets(self, request: httpx.Request, method: str, body: Any) -> httpx.Response:
        if method == "POST":
            if "chunk_method" in body:
                return self._err(101, "chunk_method is not supported")
            if "parse_type" not in body:
                return self._err(102, "parse_type is required")
            ds = {"id": self._id("ds"), "name": body["name"], "parser_id": body.get("parser_id", "general"),
                  "embedding_model": "fake-embedding", "document_count": 0}
            self.datasets[ds["id"]] = ds
            return self._ok(ds)
        if method == "GET":
            wanted = request.url.params.get("id")
            items = [d for d in self.datasets.values() if not wanted or d["id"] == wanted]
            return self._ok(items)
        if method == "DELETE":
            for ds_id in (body or {}).get("ids", []):
                self.datasets.pop(ds_id, None)
            return self._ok(None)
        return httpx.Response(405)

    def _documents(self, request: httpx.Request, method: str, ds_id: str, doc_id: str | None, body: Any) -> httpx.Response:
        if ds_id not in self.datasets:
            return self._err(102, "You don't own the dataset.")
        if method == "POST" and doc_id is None:
            if self.fail_uploads:
                return httpx.Response(500, json={"message": "synthetic upload failure"})
            raw = request.content.decode("utf-8", errors="ignore")
            name = re.search(r'filename="([^"]+)"', raw).group(1)
            content = raw.split("\r\n\r\n", 1)[1].rsplit("\r\n--", 1)[0]
            doc = {"id": self._id("doc"), "name": name, "dataset_id": ds_id, "content": content,
                   "ingestion_status": "UNSTART", "progress": 0.0, "progress_msg": "", "chunk_count": 0,
                   "meta_fields": {}, "enabled": 1, "chunks": []}
            self.documents[doc["id"]] = doc
            self.datasets[ds_id]["document_count"] += 1
            return self._ok([self._public_doc(doc)])
        if method == "GET" and doc_id is None:
            wanted = request.url.params.get("id")
            docs = [self._public_doc(d) for d in self.docs_in(ds_id) if not wanted or d["id"] == wanted]
            return self._ok({"docs": docs, "total": len(docs)})
        if method == "PATCH" and doc_id:
            doc = self.documents.get(doc_id)
            if doc is None or doc["dataset_id"] != ds_id:
                return self._err(102, "document not found")
            if "meta_fields" in body:
                doc["meta_fields"] = dict(body["meta_fields"])
            if "enabled" in body:
                doc["enabled"] = body["enabled"]
            return self._ok(self._public_doc(doc))
        if method == "DELETE" and doc_id is None:
            if self.fail_deletes:
                return httpx.Response(500, json={"message": "synthetic delete failure"})
            deleted = 0
            for target in (body or {}).get("ids", []):
                doc = self.documents.get(target)
                if doc and doc["dataset_id"] == ds_id:
                    del self.documents[target]
                    deleted += 1
            return self._ok({"deleted": deleted})
        return httpx.Response(405)

    def _retrieval(self, body: dict) -> httpx.Response:
        if self.fail_retrieval:
            return httpx.Response(500, json={"message": "synthetic retrieval failure"})
        question = _bigrams(body.get("question", ""))
        datasets = set(body.get("dataset_ids") or [])
        doc_filter = set(body.get("document_ids") or [])
        threshold = float(body.get("similarity_threshold", 0.2))
        chunks = []
        for doc in self.documents.values():
            if doc["dataset_id"] not in datasets or (doc_filter and doc["id"] not in doc_filter):
                continue
            if doc["ingestion_status"] != "COMPLETED" or not doc["enabled"]:
                continue
            for chunk in doc["chunks"]:
                grams = _bigrams(chunk["content"])
                score = len(question & grams) / max(len(question), 1)
                if score >= threshold:
                    chunks.append({"id": chunk["id"], "content": chunk["content"], "document_id": doc["id"],
                                   "dataset_id": doc["dataset_id"], "document_keyword": doc["name"],
                                   "similarity": score, "vector_similarity": score, "term_similarity": score})
        chunks.sort(key=lambda c: -c["similarity"])
        chunks = chunks[: int(body.get("page_size", 30))]
        return self._ok({"chunks": chunks, "doc_aggs": [], "total": len(chunks)})
