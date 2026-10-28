# 为什么有这个文件：把企业资料库与已发布方案片段持续、可核对地同步进 RAGFlow，并从中检索写作候选。
# 它解决什么问题：此前知识库只有一次性手动上传，检索结果无法映射回资料、删除/过期/改版的资料仍会被召回，
# 生产检索链路也从未接通。这里维护“资料 → RAGFlow 文档”的索引，检索时只认索引内的当前文档并实时复核资料状态，
# 保证召回内容可追溯、不过期、不跨公司，且候选不会被当成已挂接的 [证]（PRD 原则 1：零虚构）。

from __future__ import annotations

import hashlib
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Iterable

from .domain import DemoState, iso_time

log = logging.getLogger(__name__)

INDEX_STORE = "kb_index"
DATASET_SUFFIX = "icg-library"
SOURCE_LIBRARY = "library"
SOURCE_SNIPPET = "snippet"
# 索引条目状态：parsing（已上传、RAGFlow 解析中）、synced（可检索）、failed（上传或解析失败，下次同步重试）。
STATUS_PARSING = "parsing"
STATUS_SYNCED = "synced"
STATUS_FAILED = "failed"
TYPE_LABELS = {
    "qualification": "资质证书", "personnel": "人员", "performance": "业绩", "sla": "服务承诺",
    "snippet": "方案片段", "history": "历史标书参考",
}
SNIPPET_STATUS = {STATUS_PARSING: "unsynced", STATUS_SYNCED: "synced", STATUS_FAILED: "failed"}


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    try:
        return float(raw) if raw else default
    except ValueError:
        return default


@dataclass(frozen=True)
class KnowledgeDocument:
    """一条应当存在于知识库中的资料或片段。content_hash 决定是否需要重新上传。"""
    key: str
    source_type: str
    source_id: str
    revision: int
    name: str
    item_type: str
    markdown: str
    meta: dict[str, str]
    content_hash: str

    @property
    def filename(self) -> str:
        return f"{self.source_type}__{self.source_id}__r{self.revision}.md"


@dataclass(frozen=True)
class KnowledgeHit:
    """检索命中，已按资料聚合。source_id 是资料或片段 id（不是 RAGFlow chunk id），便于引用与复核。"""
    source_type: str
    source_id: str
    name: str
    item_type: str
    revision: int
    score: float
    content: str
    document_id: str
    chunk_ids: list[str] = field(default_factory=list)
    attachable: bool = False
    reference_only: bool = False

    @property
    def cite_tag(self) -> str:
        return f"[片:{self.source_id}]"

    # 兼容旧调用方（answer_card / editor_ai_context）读取的属性名。
    @property
    def id(self) -> str:
        return self.source_id

    @property
    def record_type(self) -> str:
        return self.item_type

    @property
    def text(self) -> str:
        return self.content

    @property
    def chunk_id(self) -> str:
        return self.source_id

    def to_public(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type, "source_id": self.source_id, "name": self.name,
            "item_type": self.item_type, "revision": self.revision, "score": round(self.score, 4),
            "content": self.content, "document_id": self.document_id, "chunk_ids": list(self.chunk_ids),
            "attachable": self.attachable, "reference_only": self.reference_only, "cite_tag": self.cite_tag,
        }


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _today() -> Any:
    from .generation_context import SHANGHAI
    return datetime.now(SHANGHAI).date()


def _library_expired(item: dict, today: Any) -> bool:
    from .generation_context import evidence_expired
    try:
        return evidence_expired(item, None, today=today)
    except Exception:
        return True  # 日期无法解析时不进知识库，避免把无法核对有效期的资料当成可用。


def library_document(item: dict) -> KnowledgeDocument:
    item_type = str(item.get("type") or "")
    label = TYPE_LABELS.get(item_type, item_type or "资料")
    valid = "长期有效" if item.get("is_long_term") else (item.get("valid_to") or item.get("valid_until") or "未登记")
    name = str(item.get("name") or item["id"])
    content = str(item.get("content") or "")
    # 标题与类别写进正文首行：RAGFlow 关键词检索对标题命中更敏感，资料名称常含证书/人员名。
    markdown = f"# {name}\n\n类别：{label}；有效期：{valid}\n\n{content}\n"
    meta = {
        "company_id": str(item["company_id"]), "source_type": SOURCE_LIBRARY, "source_id": str(item["id"]),
        "revision": str(item.get("revision", 1)), "item_type": item_type,
        "source_tier": str(item.get("source_tier") or "own"),
    }
    return KnowledgeDocument(
        key=f"{SOURCE_LIBRARY}:{item['id']}", source_type=SOURCE_LIBRARY, source_id=str(item["id"]),
        revision=int(item.get("revision", 1)), name=name, item_type=item_type, markdown=markdown, meta=meta,
        content_hash=_hash(markdown + repr(sorted(meta.items()))),
    )


def snippet_document(record: dict) -> KnowledgeDocument:
    name = " / ".join(part for part in (record.get("product"), record.get("snippet_type")) if part) or record["id"]
    body = str(record.get("published_body") or "")
    markdown = f"# {name}\n\n类别：方案片段；来源组：{record.get('source_group') or '未登记'}\n\n{body}\n"
    meta = {
        "company_id": str(record["company_id"]), "source_type": SOURCE_SNIPPET, "source_id": str(record["id"]),
        "revision": str(record.get("published_revision", 1)), "item_type": "snippet", "source_tier": "own",
    }
    return KnowledgeDocument(
        key=f"{SOURCE_SNIPPET}:{record['id']}", source_type=SOURCE_SNIPPET, source_id=str(record["id"]),
        revision=int(record.get("published_revision", 1)), name=name, item_type="snippet", markdown=markdown,
        meta=meta, content_hash=_hash(markdown + repr(sorted(meta.items()))),
    )


def desired_documents(state: DemoState, company_id: str, today: Any | None = None) -> dict[str, KnowledgeDocument]:
    """本公司当前应在知识库中的全部文档。

    资料：仅已确认、未过期（长期有效除外）的资料；历史标书也须已确认，检索时只作参考。
    片段：仅已发布且正文非空。待审、驳回、过期、删除的内容一律不在知识库中。
    """
    today = today or _today()
    wanted: dict[str, KnowledgeDocument] = {}
    for item in state.library.values():
        if item.get("company_id") != company_id or item.get("status") != "confirmed":
            continue
        if not str(item.get("content") or "").strip() or _library_expired(item, today):
            continue
        doc = library_document(item)
        wanted[doc.key] = doc
    records = (state.service_stores.get("snippets") or {}).get("records", {})
    for record in records.values():
        if record.get("company_id") != company_id or int(record.get("published_revision") or 0) <= 0:
            continue
        if not str(record.get("published_body") or "").strip():
            continue
        doc = snippet_document(record)
        wanted[doc.key] = doc
    return wanted


def _company_index(state: DemoState, company_id: str) -> dict:
    store = state.service_stores.setdefault(INDEX_STORE, {})
    return store.setdefault(company_id, {"dataset_id": "", "entries": {}, "last_sync_at": None, "last_error": ""})


def read_index(state: DemoState, company_id: str) -> dict:
    return ((state.service_stores.get(INDEX_STORE) or {}).get(company_id)
            or {"dataset_id": "", "entries": {}, "last_sync_at": None, "last_error": ""})


class KnowledgeBaseService:
    """资料 → RAGFlow 文档的同步与检索。

    - 每家公司一个数据集 ``{company_id}::icg-library``，数据集 id 与“资料→文档”索引存于
      ``DemoState.service_stores["kb_index"]``，随其他状态持久化（ISSUE-041）。
    - 同步是对账：上传新增/改版资料，删除旧版本、已撤销确认、已过期和已删除资料对应的文档。
    - 网络调用都在仓储事务之外；资料写入后的自动同步尽力而为（后台单线程），失败只记录在索引里，
      不影响资料保存，下次同步重试。
    - 未配置 RAGFlow（无启用的公司配置或缺 API Key）时全部操作为空操作，检索返回“未配置”。
    """

    def __init__(self, demo: Any, *, client_factory: Callable[[DemoState, str], Any] | None = None,
                 background: bool | None = None) -> None:
        self.demo = demo
        self.repository = demo.repository
        self._client_factory = client_factory or self._configured_client
        if background is None:
            background = os.environ.get("ICG_KB_SYNC_INLINE", "").strip() != "1"
        self.background = background
        self._executor: ThreadPoolExecutor | None = None
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()
        self.similarity_threshold = _env_float("ICG_KB_SIMILARITY_THRESHOLD", 0.2)
        self.keywords_weight = _env_float("ICG_KB_KEYWORDS_WEIGHT", 0.7)
        self.rerank_id = os.environ.get("ICG_KB_RERANK_ID", "").strip() or None

    # ---------- 客户端 ----------

    @staticmethod
    def _configured_client(state: DemoState, company_id: str) -> Any:
        from icg.infra.model_config_storage import decrypt_api_key
        from icg.infra.ragflow_client import RagflowRetrievalClient

        cfg = (getattr(state, "ragflow_configs", None) or {}).get(company_id)
        if cfg is not None:
            if not cfg.is_enabled or not cfg.encrypted_api_key:
                return None
            return RagflowRetrievalClient(base_url=cfg.base_url, api_key=decrypt_api_key(cfg.encrypted_api_key),
                                          timeout_seconds=cfg.timeout_seconds)
        base = os.environ.get("ICG_RAGFLOW_BASE_URL", "").strip()
        key = os.environ.get("ICG_RAGFLOW_API_KEY", "").strip()
        if base and key:
            return RagflowRetrievalClient(base_url=base, api_key=key)
        return None

    def client_for(self, company_id: str, state: DemoState | None = None) -> Any:
        try:
            return self._client_factory(state if state is not None else self.repository.read(), company_id)
        except Exception as exc:  # 配置损坏（如密钥无法解密）按未配置处理，原因写日志。
            log.warning("knowledge base client unavailable for %s: %s", company_id, type(exc).__name__)
            return None

    def enabled(self, company_id: str) -> bool:
        return self.client_for(company_id) is not None

    def _lock(self, company_id: str) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(company_id, threading.Lock())

    # ---------- 同步 ----------

    def schedule(self, company_id: str) -> None:
        """资料或片段写入成功后调用。从不抛错。"""
        try:
            if not self.enabled(company_id):
                return
            if not self.background:
                self.sync_company(company_id)
                return
            if self._executor is None:
                self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="kb-sync")
            self._executor.submit(self._safe_sync, company_id)
        except Exception as exc:
            log.warning("knowledge base sync scheduling failed for %s: %s", company_id, type(exc).__name__)

    def _safe_sync(self, company_id: str) -> None:
        try:
            self.sync_company(company_id)
        except Exception as exc:
            log.warning("knowledge base background sync failed for %s: %s", company_id, type(exc).__name__)

    def _ensure_dataset(self, client: Any, company_id: str, dataset_id: str) -> str:
        if dataset_id:
            try:
                client.get_dataset(dataset_id, company_id=company_id)
                return dataset_id
            except Exception:
                pass
        wanted = f"{company_id}::{DATASET_SUFFIX}"
        for dataset in client.list_datasets(company_id=company_id, page_size=100):
            if dataset.name == wanted:
                return dataset.id
        return client.create_dataset(DATASET_SUFFIX, company_id=company_id).id

    def sync_company(self, company_id: str, *, keys: Iterable[str] | None = None) -> dict[str, Any]:
        """对账一家公司的知识库。keys 给出时只处理这些条目（用于单个片段的即时同步）。"""
        state = self.repository.read()
        client = self.client_for(company_id, state)
        if client is None:
            return {"enabled": False, "uploaded": 0, "deleted": 0, "failed": 0, "unchanged": 0,
                    "message": "未配置或未启用 RAGFlow 知识库。"}
        with self._lock(company_id):
            state = self.repository.read()
            index = read_index(state, company_id)
            wanted = desired_documents(state, company_id)
            only = set(keys) if keys is not None else None
            summary = {"enabled": True, "uploaded": 0, "deleted": 0, "failed": 0, "unchanged": 0, "message": ""}
            try:
                dataset_id = self._ensure_dataset(client, company_id, index.get("dataset_id", ""))
            except Exception as exc:
                self._record(company_id, {}, set(), dataset_id=index.get("dataset_id", ""),
                             error=f"数据集不可用：{type(exc).__name__}")
                return {**summary, "enabled": True, "failed": len(wanted), "message": "RAGFlow 数据集不可用，稍后重试。"}
            if dataset_id != index.get("dataset_id"):
                index = {**index, "entries": {}}  # 数据集换了，旧文档映射全部失效。
            entries = index.get("entries", {})
            updates: dict[str, dict] = {}
            removed: set[str] = set()
            previous_pending = list(index.get("pending_deletes") or [])
            # 全量对账时顺带重试上次没删掉的旧文档。
            stale_docs: list[str] = list(previous_pending) if only is None else []
            now = iso_time(self.demo._now())

            for key, doc in wanted.items():
                if only is not None and key not in only:
                    continue
                entry = entries.get(key)
                if entry and entry.get("content_hash") == doc.content_hash and entry.get("status") != STATUS_FAILED:
                    summary["unchanged"] += 1
                    continue
                try:
                    uploaded = client.upload_document(dataset_id, doc.filename, doc.markdown)
                    try:
                        client.update_document(dataset_id, uploaded.id, meta_fields=doc.meta)
                    except Exception as exc:  # 元数据只用于 RAGFlow 侧筛查，失败不阻断；检索靠索引映射。
                        log.info("meta update failed for %s: %s", key, type(exc).__name__)
                    client.trigger_parse(dataset_id, [uploaded.id])
                    updates[key] = self._entry(doc, uploaded.id, STATUS_PARSING, "", now)
                    summary["uploaded"] += 1
                    if entry and entry.get("document_id") and entry["document_id"] != uploaded.id:
                        stale_docs.append(entry["document_id"])
                except Exception as exc:
                    summary["failed"] += 1
                    failed = self._entry(doc, (entry or {}).get("document_id", ""), STATUS_FAILED,
                                         f"上传或解析请求失败：{type(exc).__name__}", now)
                    updates[key] = failed

            for key, entry in entries.items():
                if key in wanted or (only is not None and key not in only):
                    continue
                if entry.get("document_id"):
                    stale_docs.append(entry["document_id"])
                removed.add(key)

            pending: list[str] | None = None
            if stale_docs:
                try:
                    client.delete_documents(dataset_id, stale_docs)
                    summary["deleted"] = len(stale_docs)
                    if only is None:
                        pending = []
                except Exception as exc:
                    # 删除失败：旧文档仍在 RAGFlow，但已不在索引里，检索按索引过滤，不会被召回；下次全量对账时会再清理。
                    log.warning("stale document delete failed for %s: %s", company_id, type(exc).__name__)
                    summary["message"] = "部分旧文档删除失败，已从检索中排除，稍后重试清理。"
                    pending = sorted(set(previous_pending) | set(stale_docs))
            self._record(company_id, updates, removed, dataset_id=dataset_id, error="",
                         pending_deletes=pending, synced_at=now)
        refreshed = self.refresh_status(company_id)
        summary["status_counts"] = refreshed.get("counts", {})
        return summary

    @staticmethod
    def _entry(doc: KnowledgeDocument, document_id: str, status: str, message: str, now: str) -> dict:
        return {"key": doc.key, "source_type": doc.source_type, "source_id": doc.source_id, "revision": doc.revision,
                "name": doc.name, "item_type": doc.item_type, "content_hash": doc.content_hash,
                "document_id": document_id, "status": status, "message": message, "chunk_count": 0,
                "updated_at": now}

    def _record(self, company_id: str, updates: dict[str, dict], removed: set[str], *, dataset_id: str,
                error: str, pending_deletes: list[str] | None = None, synced_at: str | None = None) -> None:
        def apply(state: DemoState) -> None:
            index = _company_index(state, company_id)
            if dataset_id and dataset_id != index.get("dataset_id"):
                index["entries"] = {}
            index["dataset_id"] = dataset_id
            for key in removed:
                index["entries"].pop(key, None)
            index["entries"].update(updates)
            index["last_error"] = error
            if synced_at:
                index["last_sync_at"] = synced_at
            if pending_deletes is not None:
                index["pending_deletes"] = list(pending_deletes)
            records = (state.service_stores.get("snippets") or {}).get("records", {})
            for key, entry in updates.items():
                if entry["source_type"] == SOURCE_SNIPPET and entry["source_id"] in records:
                    records[entry["source_id"]]["kb_sync_status"] = SNIPPET_STATUS[entry["status"]]
            for key in removed:
                source_type, _, source_id = key.partition(":")
                if source_type == SOURCE_SNIPPET and source_id in records:
                    records[source_id]["kb_sync_status"] = "unsynced"

        self.repository.transaction(apply)

    def refresh_status(self, company_id: str) -> dict[str, Any]:
        """向 RAGFlow 查询解析中的文档，把完成/失败写回索引。"""
        state = self.repository.read()
        client = self.client_for(company_id, state)
        index = read_index(state, company_id)
        if client is None or not index.get("dataset_id"):
            return self.status(company_id)
        dataset_id = index["dataset_id"]
        updates: dict[str, dict] = {}
        now = iso_time(self.demo._now())
        for key, entry in index.get("entries", {}).items():
            if entry.get("status") != STATUS_PARSING or not entry.get("document_id"):
                continue
            try:
                document = client.get_document_status(dataset_id, entry["document_id"])
            except Exception as exc:
                log.info("status refresh failed for %s: %s", key, type(exc).__name__)
                continue
            status = {"synced": STATUS_SYNCED, "failed": STATUS_FAILED}.get(document.sync_status, STATUS_PARSING)
            if status == STATUS_SYNCED and document.chunk_count == 0 and document.raw.get("chunk_count") is not None:
                status, message = STATUS_FAILED, "解析完成但没有生成分块，请检查资料正文。"
            else:
                message = document.progress_msg if status == STATUS_FAILED else ""
            if status != entry["status"] or document.chunk_count != entry.get("chunk_count"):
                updates[key] = {**entry, "status": status, "message": message,
                                "chunk_count": document.chunk_count, "updated_at": now}
        if updates:
            self._record(company_id, updates, set(), dataset_id=dataset_id, error=index.get("last_error", ""))
        return self.status(company_id)

    def status(self, company_id: str) -> dict[str, Any]:
        state = self.repository.read()
        index = read_index(state, company_id)
        wanted = desired_documents(state, company_id)
        entries = index.get("entries", {})
        rows = []
        for key, doc in wanted.items():
            entry = entries.get(key)
            if entry is None:
                rows.append({"key": key, "source_type": doc.source_type, "source_id": doc.source_id,
                             "name": doc.name, "item_type": doc.item_type, "revision": doc.revision,
                             "status": "unsynced", "message": "尚未同步", "chunk_count": 0, "updated_at": None,
                             "document_id": ""})
                continue
            stale = entry.get("content_hash") != doc.content_hash
            rows.append({k: entry.get(k) for k in ("key", "source_type", "source_id", "name", "item_type",
                                                    "revision", "status", "message", "chunk_count",
                                                    "updated_at", "document_id")}
                        | ({"status": "unsynced", "message": "资料已改版，等待重新同步"} if stale else {}))
        counts: dict[str, int] = {}
        for row in rows:
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        return {"enabled": self.client_for(company_id, state) is not None, "dataset_id": index.get("dataset_id", ""),
                "last_sync_at": index.get("last_sync_at"), "last_error": index.get("last_error", ""),
                "counts": counts, "items": sorted(rows, key=lambda r: r["key"])}

    # ---------- 检索 ----------

    def search(self, company_id: str, query: str, *, limit: int = 6, kinds: set[str] | None = None,
               user: Any = None, reference_date: Any = None) -> tuple[list[KnowledgeHit], str]:
        """返回 (命中, 跳过原因)。

        只认索引里已同步的当前文档；每个命中都按 DemoState 实时复核（公司、确认状态、版本、有效期、受限授权），
        不通过的直接丢弃。kinds 可取 "evidence"（非历史资料）、"snippet"、"history"。
        """
        if not query or not query.strip():
            return [], "query is empty"
        state = self.repository.read()
        client = self.client_for(company_id, state)
        if client is None:
            return [], "RAGFlow is not configured"
        index = read_index(state, company_id)
        dataset_id = index.get("dataset_id")
        entries = {e["document_id"]: e for e in index.get("entries", {}).values()
                   if e.get("status") == STATUS_SYNCED and e.get("document_id") and self._kind(e) in (kinds or {"evidence", "snippet", "history"})}
        if not dataset_id or not entries:
            return [], "knowledge base has no synced documents"
        result = client.retrieve(
            question=query.strip()[:2000], dataset_ids=[dataset_id], document_ids=list(entries),
            page_size=max(limit * 4, 12), similarity_threshold=self.similarity_threshold,
            keywords_similarity_weight=self.keywords_weight, rerank_id=self.rerank_id,
        )
        if result.skipped or not result.chunks:
            return [], result.skip_reason or "zero hits"
        today = reference_date or _today()
        records = (state.service_stores.get("snippets") or {}).get("records", {})
        grouped: dict[str, dict] = {}
        for chunk in result.chunks:
            if chunk.dataset_id and chunk.dataset_id != dataset_id:
                continue  # 不接受请求数据集以外的分块。
            entry = entries.get(chunk.document_id)
            if entry is None:
                continue  # 旧版本、已删除或未登记的文档。
            live = self._live(state, records, entry, company_id, today, user)
            if live is None:
                continue
            group = grouped.setdefault(entry["key"], {"entry": entry, "live": live, "score": 0.0, "chunks": []})
            group["score"] = max(group["score"], chunk.similarity)
            if len(group["chunks"]) < 2:
                group["chunks"].append(chunk)
        hits = []
        for group in grouped.values():
            entry, live = group["entry"], group["live"]
            content = "\n…\n".join(c.content.strip() for c in group["chunks"] if c.content.strip())
            hits.append(KnowledgeHit(
                source_type=entry["source_type"], source_id=entry["source_id"], name=live["name"],
                item_type=entry["item_type"], revision=entry["revision"], score=group["score"], content=content,
                document_id=entry["document_id"], chunk_ids=[c.id for c in group["chunks"]],
                attachable=live["attachable"], reference_only=live["reference_only"],
            ))
        hits.sort(key=lambda h: (-h.score, h.source_id))
        return hits[:limit], ("" if hits else "zero usable hits")

    @staticmethod
    def _kind(entry: dict) -> str:
        if entry.get("source_type") == SOURCE_SNIPPET:
            return "snippet"
        return "history" if entry.get("item_type") == "history" else "evidence"

    def _live(self, state: DemoState, records: dict, entry: dict, company_id: str, today: Any, user: Any) -> dict | None:
        if entry["source_type"] == SOURCE_SNIPPET:
            record = records.get(entry["source_id"])
            if (record is None or record.get("company_id") != company_id
                    or int(record.get("published_revision") or 0) != entry["revision"]):
                return None
            return {"name": entry["name"], "attachable": False, "reference_only": False}
        item = state.library.get(entry["source_id"])
        if (item is None or item.get("company_id") != company_id or item.get("status") != "confirmed"
                or int(item.get("revision", 1)) != entry["revision"] or _library_expired(item, today)):
            return None
        if item.get("is_restricted") and not self._restricted_allowed(state, item, user):
            return None
        history = item.get("type") == "history"
        tier = item.get("source_tier") or "own"
        return {"name": str(item.get("name") or entry["name"]),
                "attachable": not history and tier == "own",
                "reference_only": history or tier == "reference"}

    @staticmethod
    def _restricted_allowed(state: DemoState, item: dict, user: Any) -> bool:
        if user is None:
            return False
        if getattr(user, "role", "") in ("company_admin", "data_admin"):
            return True
        return any(row.get("ref_type") == "library" and row.get("ref_id") == item["id"]
                   and row.get("user_id") == getattr(user, "id", None) for row in state.resource_acl)


class KnowledgeEvidenceService:
    """把知识库检索接到既有的证据候选口（collect）和问答/编辑器的 search 口。

    路径 A：已确认资料本地规则（不经 RAGFlow）。
    路径 B：知识库命中的非历史资料与方案片段——只是候选，引用写 [片:id]；要成为 [证] 必须由人挂到响应矩阵。
    路径 C：历史标书与仅供参考资料，reference_only。
    """

    def __init__(self, knowledge_base: KnowledgeBaseService) -> None:
        self.knowledge_base = knowledge_base

    def collect(self, request: Any) -> Any:
        from icg.infra.retrieval import CandidateResult, EvidenceCandidate, EvidenceCandidateService, SkippedPath

        path_a = EvidenceCandidateService()._path_a(request)
        try:
            hits, reason = self.knowledge_base.search(request.company_id, request.query, limit=8)
        except Exception as exc:
            reason = f"B failed: {type(exc).__name__}"
            hits = []
        if not hits:
            return CandidateResult(path_a, [SkippedPath("B", reason or "zero hits"), SkippedPath("C", reason or "zero hits")])
        candidates = list(path_a)
        for hit in hits:
            path = "C" if hit.reference_only else "B"
            candidates.append(EvidenceCandidate(
                path, hit.source_id, request.company_id, hit.content, hit.attachable, hit.reference_only,
                document_id=hit.document_id, chunk_id=hit.source_id, name=hit.name, score=hit.score,
                source_type=hit.source_type, revision=hit.revision,
            ))
        return CandidateResult(candidates, [])

    def search(self, company_id: str, query: str, limit: int = 5) -> list[KnowledgeHit]:
        try:
            hits, _ = self.knowledge_base.search(company_id, query, limit=limit)
        except Exception as exc:
            log.info("knowledge search failed for %s: %s", company_id, type(exc).__name__)
            return []
        return hits
