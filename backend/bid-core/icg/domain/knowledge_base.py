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
SETTINGS_STORE = "kb_settings"
SOURCE_FILE = "file"
# 知识类别 → 数据集名后缀与摄入流程。library：本系统资料与片段；history：历史投标文件原件（仅参考）；
# certificate：资质/证明附件原件（抽取字段辅助录入，不直接参与写作检索）。
DATASET_KINDS = {"library": "icg-library", "history": "icg-history", "certificate": "icg-certificate"}
KIND_PROFILE = {"library": "structured", "history": "history_bid", "certificate": "certificate"}
FILE_KINDS = ("history", "certificate")
SECTION_CHARS = 500  # 结构化资料每节字数上限：一节一块，每块都带资料名称标题


def default_settings() -> dict[str, Any]:
    return {
        "revision": 1,
        "embedding_model": os.environ.get("ICG_KB_EMBEDDING_MODEL", "").strip(),
        "rerank_id": os.environ.get("ICG_KB_RERANK_ID", "").strip(),
        "llm_id": os.environ.get("ICG_KB_LLM_ID", "").strip(),
        "similarity_threshold": _env_float("ICG_KB_SIMILARITY_THRESHOLD", 0.2),
        "keywords_weight": _env_float("ICG_KB_KEYWORDS_WEIGHT", 0.7),
        "use_pipelines": os.environ.get("ICG_KB_USE_PIPELINES", "1").strip() != "0",
        "language": "Chinese",
        "profiles": {},
    }


def read_settings(state: DemoState, company_id: str) -> dict[str, Any]:
    stored = (state.service_stores.get(SETTINGS_STORE) or {}).get(company_id) or {}
    merged = default_settings()
    merged.update({k: v for k, v in stored.items() if k != "profiles"})
    merged["profiles"] = {**(stored.get("profiles") or {})}
    return merged


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


def _sectioned_markdown(name: str, label: str, meta_line: str, body: str) -> str:
    """按段落把正文分成不超过 SECTION_CHARS 字的节，每节一个“## 名称·类别”标题。

    配合“结构化资料”摄入流程（按 #/## 切块并把标题带进块）：每块都带资料名称，关键词检索
    命中名称时不会只命中第一块；也让切块结果确定、可复现，不依赖分词器的 token 计数。
    """
    paragraphs = [p.strip() for p in body.replace("\r\n", "\n").split("\n") if p.strip()]
    sections: list[list[str]] = [[]]
    size = 0
    for paragraph in paragraphs:
        while len(paragraph) > SECTION_CHARS:  # 超长段落按句号硬切
            cut = max(paragraph.rfind("。", 0, SECTION_CHARS), paragraph.rfind("；", 0, SECTION_CHARS))
            cut = cut + 1 if cut > SECTION_CHARS // 3 else SECTION_CHARS
            head, paragraph = paragraph[:cut], paragraph[cut:]
            if sections[-1]:
                sections.append([])
            sections[-1].append(head)
            sections.append([])
            size = 0
        if size and size + len(paragraph) > SECTION_CHARS:
            sections.append([])
            size = 0
        sections[-1].append(paragraph)
        size += len(paragraph)
    sections = [sec for sec in sections if sec] or [[""]]
    lines = [f"# {name}", ""]
    for index, section in enumerate(sections):
        suffix = "" if index == 0 else f"（续{index + 1}）"
        lines += [f"## {name}·{label}{suffix}", ""]
        if index == 0:
            lines += [meta_line, ""]
        lines += ["\n\n".join(section), ""]
    return "\n".join(lines)


def library_document(item: dict) -> KnowledgeDocument:
    item_type = str(item.get("type") or "")
    label = TYPE_LABELS.get(item_type, item_type or "资料")
    valid = "长期有效" if item.get("is_long_term") else (item.get("valid_to") or item.get("valid_until") or "未登记")
    name = str(item.get("name") or item["id"])
    content = str(item.get("content") or "")
    markdown = _sectioned_markdown(name, label, f"类别：{label}；有效期：{valid}", content)
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
    markdown = _sectioned_markdown(name, "方案片段", f"类别：方案片段；来源组：{record.get('source_group') or '未登记'}", body)
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
    index = store.setdefault(company_id, {"dataset_id": "", "entries": {}, "last_sync_at": None, "last_error": ""})
    index.setdefault("datasets", {})
    index.setdefault("pipelines", {})
    index.setdefault("files", {})
    return index


def read_index(state: DemoState, company_id: str) -> dict:
    index = ((state.service_stores.get(INDEX_STORE) or {}).get(company_id)
             or {"dataset_id": "", "entries": {}, "last_sync_at": None, "last_error": ""})
    return {"datasets": {}, "pipelines": {}, "files": {}, **index}


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

    # ---------- 摄入流程与数据集 ----------

    def _update_index(self, company_id: str, mutate: Callable[[dict], Any]) -> Any:
        return self.repository.transaction(lambda state: mutate(_company_index(state, company_id)))

    def ensure_pipeline(self, client: Any, company_id: str, profile_key: str,
                        settings: dict[str, Any] | None = None) -> tuple[str, bool]:
        """确保本公司的 ICG 摄入流程已部署且与当前定义一致。返回 (流程 id, 是否新建或更新过)。"""
        from icg.infra.ragflow_pipelines import (PROFILES, PipelineOptions, build_dsl, dsl_fingerprint,
                                                 pipeline_title, PIPELINE_VERSION)
        state = self.repository.read()
        settings = settings or read_settings(state, company_id)
        profile = PROFILES[profile_key]
        overrides = (settings.get("profiles") or {}).get(profile_key) or {}
        options = PipelineOptions(
            llm_id=settings.get("llm_id") or "",
            chunk_token_size=overrides.get("chunk_token_size"),
            questions_top_n=overrides.get("questions_top_n"),
            keywords_top_n=overrides.get("keywords_top_n"),
            extra_heading_patterns=tuple(overrides.get("extra_heading_patterns") or ()),
        )
        dsl = build_dsl(profile, options)
        expected = dsl_fingerprint(dsl)
        title = pipeline_title(company_id, profile)
        registry = read_index(state, company_id).get("pipelines", {}).get(profile_key) or {}
        pipeline_id, changed = registry.get("id", ""), False
        if pipeline_id:
            try:
                current = client.get_agent(pipeline_id)
                if dsl_fingerprint(current.get("dsl") or {}) != expected:
                    client.update_agent(pipeline_id, dsl=dsl, title=title)
                    changed = True
            except Exception:
                pipeline_id = ""
        if not pipeline_id:
            found = next((row for row in client.list_agents(canvas_category="dataflow_canvas", keywords=title)
                          if row.get("title") == title), None)
            if found:
                pipeline_id = str(found["id"])
                client.update_agent(pipeline_id, dsl=dsl)
            else:
                pipeline_id = str(client.create_agent(title, dsl, description=profile.description,
                                                      canvas_category="dataflow_canvas")["id"])
            changed = True
        now = iso_time(self.demo._now())

        def save(index: dict) -> None:
            previous = index["pipelines"].get(profile_key) or {}
            index["pipelines"][profile_key] = {
                "id": pipeline_id, "title": title, "version": PIPELINE_VERSION, "fingerprint": expected,
                "deployed_at": now if changed or not previous else previous.get("deployed_at", now),
            }
        self._update_index(company_id, save)
        return pipeline_id, changed

    def ensure_dataset(self, client: Any, company_id: str, kind: str = "library", *,
                       force_new: bool = False) -> dict[str, Any]:
        """确保某类知识的数据集存在，并绑定当前 ICG 摄入流程与公司嵌入模型。

        RAGFlow 不支持摄入流程（老版本无画布接口）或流程部署失败时，退回内置 general 解析器并记下原因。
        """
        state = self.repository.read()
        settings = read_settings(state, company_id)
        index = read_index(state, company_id)
        record = dict(index.get("datasets", {}).get(kind) or {})
        if kind == "library" and not record.get("dataset_id") and index.get("dataset_id"):
            record["dataset_id"] = index["dataset_id"]  # 兼容 Wave 12 初版只记了一个 dataset_id
        name = DATASET_KINDS[kind]
        pipeline_id, pipeline_changed, warning = "", False, ""
        if settings.get("use_pipelines"):
            try:
                pipeline_id, pipeline_changed = self.ensure_pipeline(client, company_id, KIND_PROFILE[kind], settings)
            except Exception as exc:
                warning = f"摄入流程不可用，已退回内置解析器：{type(exc).__name__}"
                log.warning("pipeline unavailable for %s/%s: %s", company_id, kind, type(exc).__name__)
        dataset_id = "" if force_new else record.get("dataset_id", "")
        if dataset_id:
            try:
                client.get_dataset(dataset_id, company_id=company_id)
            except Exception:
                dataset_id = ""
        if not dataset_id:
            wanted = f"{company_id}::{name}"
            found = None if force_new else next(
                (d for d in client.list_datasets(company_id=company_id, page_size=100) if d.name == wanted), None)
            if found is not None:
                dataset_id = found.id
                pipeline_changed = True  # 不知道它绑的是什么，重新绑定一次
            elif pipeline_id:
                dataset_id = client.create_pipeline_dataset(name, pipeline_id, company_id=company_id,
                                                            embedding_model=settings.get("embedding_model") or None,
                                                            language=settings.get("language") or "Chinese").id
                pipeline_changed = False
            else:
                dataset_id = client.create_dataset(name, company_id=company_id,
                                                   embedding_model=settings.get("embedding_model") or None).id
        rebound = False
        if pipeline_id and (pipeline_changed or record.get("pipeline_id") != pipeline_id):
            # 数据集创建时复制了流程参数；流程更新后要重新绑定，再把新参数应用到已有文档（需重新解析才生效）。
            try:
                client.update_dataset(dataset_id, parse_type=2, pipeline_id=pipeline_id)
                client.apply_parser_config(dataset_id)
                rebound = bool(record.get("dataset_id"))
            except Exception as exc:
                warning = f"数据集重新绑定摄入流程失败：{type(exc).__name__}"
        info = {"dataset_id": dataset_id, "pipeline_id": pipeline_id, "profile": KIND_PROFILE[kind] if pipeline_id else "",
                "mode": "pipeline" if pipeline_id else "builtin",
                "embedding_model": record.get("embedding_model") or settings.get("embedding_model") or "",
                "warning": warning, "reparse_required": bool(record.get("reparse_required") or rebound)}

        def save(index: dict) -> None:
            index["datasets"][kind] = info
            if kind == "library":
                index["dataset_id"] = dataset_id
        self._update_index(company_id, save)
        return info

    def _ensure_dataset(self, client: Any, company_id: str, dataset_id: str) -> str:
        return self.ensure_dataset(client, company_id, "library")["dataset_id"]

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

            remote = self._remote_documents(client, dataset_id) if only is None else None
            if remote is not None:
                # 漂移修复：索引里有、RAGFlow 里没有（被手工删除）→ 重新上传；
                # RAGFlow 里有、索引不认识（上传后进程中断等遗留）→ 删除。数据集为本系统专用，删除是安全的。
                known = {e.get("document_id") for e in entries.values()}
                missing = {k for k, e in entries.items() if e.get("document_id") not in remote}
                removed |= {k for k in missing if k not in wanted}
                entries = {k: e for k, e in entries.items() if k not in missing}
                stale_docs.extend(sorted(remote - known - set(stale_docs)))

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
    def _remote_documents(client: Any, dataset_id: str) -> set[str] | None:
        """数据集内全部文档 id；列举失败返回 None（跳过漂移修复，不误删）。"""
        ids: set[str] = set()
        try:
            for page in range(1, 201):
                batch = client.list_documents(dataset_id, page=page, page_size=100)
                ids.update(d.id for d in batch if d.id)
                if len(batch) < 100:
                    return ids
        except Exception as exc:
            log.info("document listing failed for %s: %s", dataset_id, type(exc).__name__)
        return None

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

    @staticmethod
    def _refreshed(client: Any, dataset_id: str, entry: dict, now: str) -> dict | None:
        try:
            document = client.get_document_status(dataset_id, entry["document_id"])
        except Exception as exc:
            log.info("status refresh failed for %s: %s", entry.get("key"), type(exc).__name__)
            return None
        status = {"synced": STATUS_SYNCED, "failed": STATUS_FAILED}.get(document.sync_status, STATUS_PARSING)
        if status == STATUS_SYNCED and document.chunk_count == 0 and document.raw.get("chunk_count") is not None:
            status, message = STATUS_FAILED, "解析完成但没有生成分块，请检查资料正文。"
        else:
            message = document.progress_msg if status == STATUS_FAILED else ""
        if status == entry["status"] and document.chunk_count == entry.get("chunk_count"):
            return None
        refreshed = {**entry, "status": status, "message": message, "chunk_count": document.chunk_count,
                     "updated_at": now}
        if document.meta_fields:
            refreshed["meta_fields"] = dict(document.meta_fields)
        return refreshed

    def refresh_status(self, company_id: str) -> dict[str, Any]:
        """向 RAGFlow 查询解析中的文档（资料、片段与上传原件），把完成/失败写回索引。"""
        state = self.repository.read()
        client = self.client_for(company_id, state)
        index = read_index(state, company_id)
        if client is None:
            return self.status(company_id)
        now = iso_time(self.demo._now())
        dataset_id = index.get("dataset_id", "")
        updates: dict[str, dict] = {}
        if dataset_id:
            for key, entry in index.get("entries", {}).items():
                if entry.get("status") == STATUS_PARSING and entry.get("document_id"):
                    refreshed = self._refreshed(client, dataset_id, entry, now)
                    if refreshed:
                        updates[key] = refreshed
        file_updates: dict[str, dict] = {}
        for key, entry in index.get("files", {}).items():
            file_dataset = self._dataset_of(index, entry)
            if entry.get("status") == STATUS_PARSING and entry.get("document_id") and file_dataset:
                refreshed = self._refreshed(client, file_dataset, entry, now)
                if refreshed:
                    file_updates[key] = refreshed
        if updates:
            self._record(company_id, updates, set(), dataset_id=dataset_id, error=index.get("last_error", ""))
        if file_updates:
            self._update_index(company_id, lambda idx: idx["files"].update(file_updates))
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
               user: Any = None, reference_date: Any = None,
               overrides: dict[str, Any] | None = None) -> tuple[list[KnowledgeHit], str]:
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
        settings = {**read_settings(state, company_id), **(overrides or {})}
        wanted_kinds = kinds or {"evidence", "snippet", "history"}
        candidates = list(index.get("entries", {}).values()) + list(index.get("files", {}).values())
        entries = {e["document_id"]: e for e in candidates
                   if e.get("status") == STATUS_SYNCED and e.get("document_id") and e.get("enabled", True)
                   and self._kind(e) in wanted_kinds}
        dataset_ids = sorted({self._dataset_of(index, e) for e in entries.values()} - {""})
        if not dataset_ids or not entries:
            return [], "knowledge base has no synced documents"
        result = client.retrieve(
            question=query.strip()[:2000], dataset_ids=dataset_ids, document_ids=list(entries),
            page_size=max(limit * 4, 12),
            similarity_threshold=float(settings.get("similarity_threshold", self.similarity_threshold)),
            keywords_similarity_weight=float(settings.get("keywords_weight", self.keywords_weight)),
            rerank_id=(settings.get("rerank_id") or self.rerank_id or None),
        )
        if result.skipped or not result.chunks:
            return [], result.skip_reason or "zero hits"
        today = reference_date or _today()
        records = (state.service_stores.get("snippets") or {}).get("records", {})
        grouped: dict[str, dict] = {}
        for chunk in result.chunks:
            if chunk.dataset_id and chunk.dataset_id not in dataset_ids:
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
    def _dataset_of(index: dict, entry: dict) -> str:
        kind = entry.get("dataset_kind") or "library"
        if kind == "library":
            return (index.get("datasets", {}).get("library") or {}).get("dataset_id") or index.get("dataset_id", "")
        return (index.get("datasets", {}).get(kind) or {}).get("dataset_id", "")

    @staticmethod
    def _kind(entry: dict) -> str:
        if entry.get("source_type") == SOURCE_FILE:
            return entry.get("dataset_kind") or "history"
        if entry.get("source_type") == SOURCE_SNIPPET:
            return "snippet"
        return "history" if entry.get("item_type") == "history" else "evidence"

    def _live(self, state: DemoState, records: dict, entry: dict, company_id: str, today: Any, user: Any) -> dict | None:
        if entry["source_type"] == SOURCE_FILE:
            # 历史投标原件：管理员上传、未删除即可用，永远只作参考，不能挂为 [证]。
            if entry.get("company_id", company_id) != company_id:
                return None
            return {"name": entry["name"], "attachable": False, "reference_only": True}
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
