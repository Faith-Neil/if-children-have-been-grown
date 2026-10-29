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
        self.agents: dict[str, dict] = {}
        self.supports_agents = True
        self.models = [
            {"name": "bge-m3", "instance_name": "local", "provider_name": "Ollama", "model_type": ["embedding"]},
            {"name": "bge-reranker-v2-m3", "instance_name": "local", "provider_name": "Ollama", "model_type": ["rerank"]},
            {"name": "qwen3-32b", "instance_name": "local", "provider_name": "Ollama", "model_type": ["chat"]},
        ]
        # 测试可替换：模拟摄入流程 Extractor 的元数据抽取（输入文档正文，返回 meta_fields）。
        self.metadata_extractor = None
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
        dataset = self.datasets.get(doc["dataset_id"], {})
        title_chunker = any(k.startswith("TitleChunker") for k in (dataset.get("parser_config") or {}))
        if title_chunker and re.search(r"^#{1,2} ", doc["content"], re.M):
            # 模拟“按标题切块 + 标题带进每块”：每个 ## 节一块，前缀 H1 标题。
            h1 = next((line for line in doc["content"].splitlines() if line.startswith("# ")), "")
            sections = re.split(r"^(?=## )", doc["content"], flags=re.M)
            parts = [(h1 + "\n" + sec.strip()) if not sec.startswith("# ") else sec.strip()
                     for sec in sections if sec.strip() and sec.strip() != h1]
        else:
            parts = [p.strip() for p in re.split(r"\n\s*\n", doc["content"]) if p.strip()]
        # 版面位置：真实 DeepDOC 返回 [[页码(1 起), 左, 右, 上, 下], …]；这里按换页符 \f 推算页码
        chunks, cursor = [], 0
        for part in parts:
            found = doc["content"].find(part.splitlines()[0] if part.splitlines() else part, cursor)
            at = found if found >= 0 else cursor
            cursor = max(cursor, at)
            page = doc["content"][:at].count("\f") + 1
            chunks.append({"id": self._id("chunk"), "content": part, "important_keywords": [],
                           "questions": [], "available": True, "positions": [[page, 0, 0, at, at + 1]]})
        doc["chunks"] = chunks
        if dataset.get("pipeline_id") and self.metadata_extractor is not None:
            doc["meta_fields"] = {**doc.get("meta_fields", {}), **self.metadata_extractor(doc["content"])}
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
            if path == "/api/v1/models" and method == "GET":
                return self._ok(self.models)
            if path.startswith("/api/v1/agents"):
                return self._agents(request, method, path, body)
            m = re.fullmatch(r"/api/v1/datasets/([^/]+)", path)
            if m and method == "PUT":
                ds = self.datasets.get(m.group(1))
                if ds is None:
                    return self._err(102, "You don't own the dataset.")
                if "embedding_model" in body and body["embedding_model"] != ds["embedding_model"] and ds.get("chunk_count"):
                    return self._err(102, "chunk_count must be 0 before changing embedding_model")
                if body.get("parse_type") == 2:
                    agent = self.agents.get(body.get("pipeline_id", ""))
                    if agent is None:
                        return self._err(102, "pipeline not found")
                    ds["pipeline_id"] = agent["id"]
                    ds["parser_config"] = {k: v["obj"]["params"] for k, v in agent["dsl"]["components"].items()}
                ds.update({k: v for k, v in body.items() if k in ("name", "description", "embedding_model", "pagerank")})
                return self._ok(ds)
            m = re.fullmatch(r"/api/v1/datasets/([^/]+)/metadata/summary", path)
            if m and method == "GET":
                summary: dict[str, dict] = {}
                for doc in self.docs_in(m.group(1)):
                    for key, value in (doc.get("meta_fields") or {}).items():
                        bucket = summary.setdefault(key, {"type": "string", "values": {}})
                        bucket["values"][value] = bucket["values"].get(value, 0) + 1
                return self._ok({"summary": {k: {"type": v["type"], "values": [[a, b] for a, b in v["values"].items()]}
                                             for k, v in summary.items()}})
            m = re.fullmatch(r"/api/v1/datasets/([^/]+)/documents/apply-parser-config", path)
            if m and method == "POST":
                docs = self.docs_in(m.group(1))
                return self._ok({"dataset_id": m.group(1), "total_documents": len(docs), "updated_documents": len(docs),
                                 "unchanged_documents": 0})
            m = re.fullmatch(r"/api/v1/datasets/([^/]+)/documents/([^/]+)/chunks(?:/([^/]+))?", path)
            if m:
                return self._chunks(request, method, m.group(1), m.group(2), m.group(3), body)
            m = re.fullmatch(r"/api/v1/datasets/([^/]+)/documents(?:/([^/]+))?", path)
            if m:
                return self._documents(request, method, m.group(1), m.group(2), body)
            m = re.fullmatch(r"/api/v1/datasets/([^/]+)/chunks", path)
            if m and method == "DELETE":
                for doc_id in (body or {}).get("document_ids", []):
                    if doc_id in self.documents:
                        self.documents[doc_id]["ingestion_status"] = "CANCELED"
                return self._ok(None)
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
            if body.get("parse_type") == 2 and ("parser_id" in body or body.get("pipeline_id") not in self.agents):
                return self._err(102, "pipeline_id is invalid or parser_id given with parse_type 2")
            ds = {"id": self._id("ds"), "name": body["name"], "parser_id": body.get("parser_id", "general"),
                  "embedding_model": body.get("embedding_model") or "fake-embedding", "document_count": 0,
                  "chunk_count": 0, "pipeline_id": body.get("pipeline_id", ""), "parser_config": {}}
            if ds["pipeline_id"]:
                ds["parser_config"] = {k: v["obj"]["params"] for k, v in self.agents[ds["pipeline_id"]]["dsl"]["components"].items()}
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
            raw_bytes = request.content
            head = raw_bytes[:1000].decode("utf-8", errors="ignore")
            name = re.search(r'filename="([^"]+)"', head).group(1)
            payload = raw_bytes.split(b"\r\n\r\n", 1)[1].rsplit(b"\r\n--", 1)[0]
            content = payload.decode("utf-8", errors="ignore")
            doc = {"id": self._id("doc"), "name": name, "dataset_id": ds_id, "content": content, "raw": payload,
                   "ingestion_status": "UNSTART", "progress": 0.0, "progress_msg": "", "chunk_count": 0,
                   "meta_fields": {}, "enabled": 1, "chunks": []}
            self.documents[doc["id"]] = doc
            self.datasets[ds_id]["document_count"] += 1
            return self._ok([self._public_doc(doc)])
        if method == "GET" and doc_id is None:
            wanted = request.url.params.get("id")
            docs = [self._public_doc(d) for d in self.docs_in(ds_id) if not wanted or d["id"] == wanted]
            return self._ok({"docs": docs, "total": len(docs)})
        if method == "GET" and doc_id:
            doc = self.documents.get(doc_id)
            if doc is None or doc["dataset_id"] != ds_id:
                return self._err(102, "document not found")
            return httpx.Response(200, content=doc["raw"], headers={"content-type": "application/octet-stream"})
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

    def _agents(self, request: httpx.Request, method: str, path: str, body: Any) -> httpx.Response:
        if not self.supports_agents:
            return httpx.Response(404, json={"code": 404, "message": "Not Found"})
        m = re.fullmatch(r"/api/v1/agents(?:/([^/]+))?", path)
        agent_id = m.group(1) if m else None
        if method == "GET" and agent_id is None:
            category = request.url.params.get("canvas_category")
            keywords = request.url.params.get("keywords")
            rows = [{k: a[k] for k in ("id", "title", "canvas_category")} for a in self.agents.values()
                    if (not category or a["canvas_category"] == category) and (not keywords or keywords in a["title"])]
            return self._ok({"canvas": rows, "total": len(rows)})
        if method == "POST" and agent_id is None:
            if not body.get("dsl"):
                return self._err(101, "no DSL data in request")
            agent = {"id": self._id("agent"), "title": body["title"], "description": body.get("description", ""),
                     "dsl": body["dsl"], "canvas_category": body.get("canvas_category", "agent_canvas")}
            self.agents[agent["id"]] = agent
            return self._ok(agent)
        agent = self.agents.get(agent_id or "")
        if agent is None:
            return self._err(102, "canvas not found")
        if method == "GET":
            return self._ok(agent)
        if method == "PUT":
            agent.update({k: v for k, v in body.items() if k in ("title", "dsl", "description") and v is not None})
            return self._ok(True)
        if method == "DELETE":
            del self.agents[agent_id]
            return self._ok(True)
        return httpx.Response(405)

    def _chunks(self, request: httpx.Request, method: str, ds_id: str, doc_id: str, chunk_id: str | None,
                body: Any) -> httpx.Response:
        doc = self.documents.get(doc_id)
        if doc is None or doc["dataset_id"] != ds_id:
            return self._err(102, "document not found")
        if method == "GET":
            keywords = request.url.params.get("keywords") or ""
            rows = [c for c in doc["chunks"] if keywords in c["content"]]
            page = int(request.url.params.get("page") or 1)
            size = int(request.url.params.get("page_size") or 30)
            window = rows[(page - 1) * size: page * size]
            # 1.0 列表接口返回内部字段名。
            return self._ok({"total": len(rows), "doc": self._public_doc(doc), "chunks": [
                {"chunk_id": c["id"], "content_with_weight": c["content"], "important_kwd": json.dumps(c["important_keywords"]),
                 "question_kwd": json.dumps(c["questions"]), "available": str(c["available"]), "doc_type_kwd": "text",
                 "positions": c.get("positions") or []}
                for c in window]})
        if method == "PATCH" and chunk_id:
            chunk = next((c for c in doc["chunks"] if c["id"] == chunk_id), None)
            if chunk is None:
                return self._err(102, "Can't find this chunk")
            for key in ("content", "important_keywords", "questions", "available"):
                if key in body:
                    chunk[key] = body[key]
            return self._ok(None)
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
                if not chunk.get("available", True):
                    continue
                grams = _bigrams(chunk["content"] + " " + " ".join(chunk.get("questions", [])))
                score = len(question & grams) / max(len(question), 1)
                if score >= threshold:
                    chunks.append({"id": chunk["id"], "content": chunk["content"], "document_id": doc["id"],
                                   "dataset_id": doc["dataset_id"], "document_keyword": doc["name"],
                                   "similarity": score, "vector_similarity": score, "term_similarity": score})
        chunks.sort(key=lambda c: -c["similarity"])
        chunks = chunks[: int(body.get("page_size", 30))]
        return self._ok({"chunks": chunks, "doc_aggs": [], "total": len(chunks)})
