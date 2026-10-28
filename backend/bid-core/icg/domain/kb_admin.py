# 为什么有这个文件：让本系统通过 API 完整管理公司在 RAGFlow 中的知识库：模型与检索参数、ICG 摄入流程、
# 数据集、文档原件、分块、元数据与检索试查，并留下审计记录。
# 它解决什么问题：此前只能在 RAGFlow 自带界面里改配置，本系统看不到也管不住；改了嵌入模型、切块规则后
# 本系统的索引与 RAGFlow 实际状态脱节。这里把这些操作收进本系统，按公司隔离、按角色授权、全部留痕。
#
# 业务边界（PRD 原则 1）：知识库里任何内容都只是候选。历史投标原件永远只作参考；证书附件抽取出的字段
# 只能生成“待核验”资料草稿，必须由资料管理员确认后才进入资料库、才可能成为 [证]。

from __future__ import annotations

import base64
import binascii
from copy import deepcopy
from typing import Any

from .domain import DemoState, DomainError, Principal, iso_time, new_id
from .knowledge_base import (DATASET_KINDS, FILE_KINDS, KIND_PROFILE, SETTINGS_STORE, SOURCE_FILE, STATUS_FAILED,
                             STATUS_PARSING, KnowledgeBaseService, _company_index, default_settings, read_index,
                             read_settings)

AUDIT_STORE = "kb_audit"
AUDIT_LIMIT = 500
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
READ_ROLES = {"company_admin", "data_admin", "manager", "project_lead"}
WRITE_ROLES = {"company_admin", "data_admin"}
CONNECTION_ROLES = {"company_admin"}
SETTING_FIELDS = {
    "embedding_model": str, "rerank_id": str, "llm_id": str, "similarity_threshold": float,
    "keywords_weight": float, "use_pipelines": bool, "language": str,
}
PROFILE_FIELDS = {"chunk_token_size": int, "questions_top_n": int, "keywords_top_n": int, "extra_heading_patterns": list}
UPLOAD_SUFFIXES = {
    "history": (".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".md", ".txt", ".pptx"),
    "certificate": (".pdf", ".png", ".jpg", ".jpeg", ".docx"),
}
CERT_FIELD_TO_LIBRARY = {"cert_name": "name", "valid_to": "valid_until"}


def _role(principal: Principal) -> str:
    from .project_access import normalize_role
    return normalize_role(principal.user.role)


def _is_super(principal: Principal) -> bool:
    from .auth_service import is_super_admin
    return is_super_admin(principal)


def require_kb_role(principal: Principal, level: str = "read") -> None:
    """read：管理/资料/项目负责角色；write：公司管理员与资料管理员；connection：只有公司管理员。"""
    if _is_super(principal):
        return
    allowed = {"read": READ_ROLES, "write": WRITE_ROLES, "connection": CONNECTION_ROLES}[level]
    if _role(principal) not in allowed:
        raise DomainError(403, "FORBIDDEN", "当前账号无权管理公司知识库。")


class KbAdminService:
    def __init__(self, demo: Any, knowledge_base: KnowledgeBaseService) -> None:
        self.demo = demo
        self.repository = demo.repository
        self.kb = knowledge_base

    # ---------- 公共 ----------

    def _client(self, principal: Principal) -> Any:
        client = self.kb.client_for(principal.user.company_id)
        if client is None:
            raise DomainError(409, "KNOWLEDGE_BASE_NOT_CONFIGURED", "未配置或未启用 RAGFlow（含 API Key），请公司管理员先完成知识库连接配置。")
        return client

    @staticmethod
    def _kind(kind: str, *, files_only: bool = False) -> str:
        if kind not in DATASET_KINDS or (files_only and kind not in FILE_KINDS):
            allowed = "、".join(FILE_KINDS if files_only else DATASET_KINDS)
            raise DomainError(422, "VALIDATION_ERROR", f"知识类别只能是：{allowed}。")
        return kind

    def _dataset(self, principal: Principal, kind: str, *, create: bool = True) -> dict[str, Any]:
        company = principal.user.company_id
        info = read_index(self.repository.read(), company).get("datasets", {}).get(kind)
        if not create:
            if info and info.get("dataset_id"):
                return info
            raise DomainError(404, "NOT_FOUND", "该类知识库尚未建立。")
        # 写入前总是核对一次：数据集若在 RAGFlow 侧被删除，会按名称找回或重建，而不是一直报上游错误。
        try:
            return self.kb.ensure_dataset(self._client(principal), company, kind)
        except DomainError:
            raise
        except Exception as exc:
            raise self._wrap(exc, "准备数据集") from None

    def _owned_document(self, principal: Principal, kind: str, document_id: str) -> tuple[str, dict | None]:
        """确认文档属于本公司该类数据集；返回 (dataset_id, 本系统索引条目)。"""
        info = self._dataset(principal, kind, create=False)
        client = self._client(principal)
        try:
            client.get_document_status(info["dataset_id"], document_id)
        except Exception:
            raise DomainError(404, "NOT_FOUND", "未找到本公司知识库中的该文档。") from None
        index = read_index(self.repository.read(), principal.user.company_id)
        pool = index.get("files", {}) if kind in FILE_KINDS else index.get("entries", {})
        entry = next((e for e in pool.values() if e.get("document_id") == document_id), None)
        return info["dataset_id"], entry

    def _audit(self, principal: Principal, action: str, target: str = "", detail: dict | None = None) -> None:
        company = principal.user.company_id
        row = {"id": new_id("kbaudit"), "at": iso_time(self.demo._now()), "actor_id": principal.user.id,
               "actor_name": getattr(principal.user, "display_name", "") or principal.user.id,
               "action": action, "target": target, "detail": detail or {}}

        def apply(state: DemoState) -> None:
            rows = state.service_stores.setdefault(AUDIT_STORE, {}).setdefault(company, [])
            rows.append(row)
            del rows[:-AUDIT_LIMIT]
        self.repository.transaction(apply)

    @staticmethod
    def _wrap(error: Exception, what: str) -> DomainError:
        if isinstance(error, DomainError):
            return error
        return DomainError(502, "KNOWLEDGE_BASE_UPSTREAM_ERROR", f"{what}失败：RAGFlow 返回 {type(error).__name__}。",
                           {"upstream": str(error)[:300]})

    # ---------- 总览、模型、设置 ----------

    def overview(self, principal: Principal) -> dict[str, Any]:
        require_kb_role(principal, "read")
        company = principal.user.company_id
        state = self.repository.read()
        index = read_index(state, company)
        files = list(index.get("files", {}).values())
        return {
            "enabled": self.kb.client_for(company, state) is not None,
            "settings": self._public_settings(read_settings(state, company)),
            "datasets": {kind: index.get("datasets", {}).get(kind) for kind in DATASET_KINDS},
            "pipelines": index.get("pipelines", {}),
            "library_status": self.kb.status(company)["counts"],
            "file_counts": {kind: sum(1 for f in files if f.get("dataset_kind") == kind) for kind in FILE_KINDS},
            "last_sync_at": index.get("last_sync_at"), "last_error": index.get("last_error", ""),
        }

    def models(self, principal: Principal) -> dict[str, Any]:
        require_kb_role(principal, "read")
        client = self._client(principal)
        try:
            rows = client.list_models()
        except Exception as exc:
            raise self._wrap(exc, "读取模型列表") from None
        grouped: dict[str, list[dict]] = {"embedding": [], "rerank": [], "chat": []}
        for row in rows:
            for kind in grouped:
                if kind in row["model_type"]:
                    grouped[kind].append({"id": row["id"], "name": row["name"], "provider": row["provider"]})
        return grouped

    @staticmethod
    def _public_settings(settings: dict[str, Any]) -> dict[str, Any]:
        return {**settings, "profiles": deepcopy(settings.get("profiles") or {})}

    def get_settings(self, principal: Principal) -> dict[str, Any]:
        require_kb_role(principal, "read")
        return self._public_settings(read_settings(self.repository.read(), principal.user.company_id))

    def update_settings(self, principal: Principal, payload: dict[str, Any], expected_revision: int) -> dict[str, Any]:
        require_kb_role(principal, "write")
        company = principal.user.company_id
        changes: dict[str, Any] = {}
        for key, kind in SETTING_FIELDS.items():
            if key in payload and payload[key] is not None:
                value = payload[key]
                if kind is float:
                    value = float(value)
                    if not 0.0 <= value <= 1.0:
                        raise DomainError(422, "VALIDATION_ERROR", f"{key} 须在 0～1 之间。")
                changes[key] = value
        profiles = payload.get("profiles")
        if profiles is not None:
            from icg.infra.ragflow_pipelines import PROFILES
            for key, overrides in profiles.items():
                if key not in PROFILES or not isinstance(overrides, dict):
                    raise DomainError(422, "VALIDATION_ERROR", f"未知摄入流程：{key}。")
                for field_name in overrides:
                    if field_name not in PROFILE_FIELDS:
                        raise DomainError(422, "VALIDATION_ERROR", f"摄入流程不支持调整 {field_name}。")
                size = overrides.get("chunk_token_size")
                if size is not None and not 128 <= int(size) <= 2048:
                    raise DomainError(422, "VALIDATION_ERROR", "chunk_token_size 须在 128～2048 之间。")
                for count in ("questions_top_n", "keywords_top_n"):
                    if overrides.get(count) is not None and not 0 <= int(overrides[count]) <= 10:
                        raise DomainError(422, "VALIDATION_ERROR", f"{count} 须在 0～10 之间。")
                for pattern in overrides.get("extra_heading_patterns") or []:
                    import re
                    try:
                        re.compile(pattern)
                    except re.error:
                        raise DomainError(422, "VALIDATION_ERROR", f"标题规则不是合法正则：{pattern}") from None
            changes["profiles"] = profiles

        def apply(state: DemoState) -> dict[str, Any]:
            current = read_settings(state, company)
            if current["revision"] != expected_revision:
                raise DomainError(409, "VERSION_CONFLICT", "知识库设置已被他人修改，请刷新后再保存。",
                                  {"current_revision": current["revision"]})
            embedding_changed = "embedding_model" in changes and changes["embedding_model"] != current["embedding_model"]
            stored = state.service_stores.setdefault(SETTINGS_STORE, {}).setdefault(company, {})
            for key, value in changes.items():
                stored[key] = deepcopy(value)
            stored["revision"] = current["revision"] + 1
            if embedding_changed:
                # 不同嵌入模型的向量不可混用：已有数据集必须重建，检索前提示管理员。
                index = _company_index(state, company)
                for info in index["datasets"].values():
                    info["rebuild_required"] = True
            return read_settings(state, company)

        result = self.repository.transaction(apply)
        self._audit(principal, "settings.update", "", {"fields": sorted(changes)})
        return self._public_settings(result)

    # ---------- 摄入流程 ----------

    def pipelines(self, principal: Principal) -> dict[str, Any]:
        require_kb_role(principal, "read")
        from icg.infra.ragflow_pipelines import PIPELINE_VERSION, PROFILES
        index = read_index(self.repository.read(), principal.user.company_id)
        items = []
        for key, profile in PROFILES.items():
            deployed = index.get("pipelines", {}).get(key) or {}
            items.append({"key": key, "title": profile.title, "description": profile.description,
                          "knowledge_kind": profile.knowledge_kind, "file_formats": list(profile.file_formats),
                          "chunker": profile.chunker, "questions_top_n": profile.questions_top_n,
                          "keywords_top_n": profile.keywords_top_n,
                          "metadata_fields": [m.key for m in profile.metadata_fields],
                          "latest_version": PIPELINE_VERSION, "deployed": deployed or None})
        return {"items": items}

    def pipeline_dsl(self, principal: Principal, key: str) -> dict[str, Any]:
        require_kb_role(principal, "read")
        from icg.infra.ragflow_pipelines import PROFILES, PipelineOptions, build_dsl
        if key not in PROFILES:
            raise DomainError(404, "NOT_FOUND", "未知摄入流程。")
        settings = read_settings(self.repository.read(), principal.user.company_id)
        overrides = (settings.get("profiles") or {}).get(key) or {}
        options = PipelineOptions(llm_id=settings.get("llm_id") or "",
                                  chunk_token_size=overrides.get("chunk_token_size"),
                                  questions_top_n=overrides.get("questions_top_n"),
                                  keywords_top_n=overrides.get("keywords_top_n"),
                                  extra_heading_patterns=tuple(overrides.get("extra_heading_patterns") or ()))
        return {"key": key, "dsl": build_dsl(PROFILES[key], options)}

    def deploy(self, principal: Principal, kinds: list[str] | None = None) -> dict[str, Any]:
        """部署或升级 ICG 摄入流程并把各类数据集绑定上去。已有文档需重新解析才会按新流程切块。"""
        require_kb_role(principal, "write")
        client = self._client(principal)
        company = principal.user.company_id
        results = {}
        for kind in kinds or list(DATASET_KINDS):
            self._kind(kind)
            try:
                results[kind] = self.kb.ensure_dataset(client, company, kind)
            except Exception as exc:
                raise self._wrap(exc, f"部署 {kind} 知识库") from None
        self._audit(principal, "pipelines.deploy", ",".join(results), {
            kind: {"mode": info["mode"], "warning": info["warning"]} for kind, info in results.items()})
        return {"datasets": results, "pipelines": read_index(self.repository.read(), company).get("pipelines", {})}

    # ---------- 数据集 ----------

    def datasets(self, principal: Principal) -> dict[str, Any]:
        require_kb_role(principal, "read")
        company = principal.user.company_id
        index = read_index(self.repository.read(), company)
        client = self.kb.client_for(company)
        rows = []
        for kind, suffix in DATASET_KINDS.items():
            info = index.get("datasets", {}).get(kind) or {}
            row = {"kind": kind, "name": f"{company}::{suffix}", "profile": KIND_PROFILE[kind], **info,
                   "document_count": None, "chunk_count": None}
            if client is not None and info.get("dataset_id"):
                try:
                    raw = client.get_dataset(info["dataset_id"], company_id=company).raw
                    row.update(document_count=raw.get("document_count"), chunk_count=raw.get("chunk_count"),
                               live_embedding_model=raw.get("embedding_model"))
                except Exception:
                    row["warning"] = "RAGFlow 中找不到该数据集，下次同步会重建。"
            rows.append(row)
        return {"items": rows}

    def ensure(self, principal: Principal, kind: str) -> dict[str, Any]:
        require_kb_role(principal, "write")
        self._kind(kind)
        try:
            info = self.kb.ensure_dataset(self._client(principal), principal.user.company_id, kind)
        except Exception as exc:
            raise self._wrap(exc, "建立数据集") from None
        self._audit(principal, "dataset.ensure", kind, {"dataset_id": info["dataset_id"], "mode": info["mode"]})
        return info

    def reparse(self, principal: Principal, kind: str) -> dict[str, Any]:
        """按当前流程重新解析该类全部文档（切块规则或流程升级后使用）。"""
        require_kb_role(principal, "write")
        self._kind(kind)
        client = self._client(principal)
        company = principal.user.company_id
        info = self._dataset(principal, kind, create=False)
        try:
            ids = sorted(self.kb._remote_documents(client, info["dataset_id"]) or set())
            for start in range(0, len(ids), 50):
                client.trigger_parse(info["dataset_id"], ids[start:start + 50])
        except Exception as exc:
            raise self._wrap(exc, "重新解析") from None
        pool = "files" if kind in FILE_KINDS else "entries"

        def mark(index: dict) -> None:
            for entry in index[pool].values():
                if entry.get("document_id") in ids:
                    entry["status"] = STATUS_PARSING
            if kind in index["datasets"]:
                index["datasets"][kind]["reparse_required"] = False
        self.kb._update_index(company, mark)
        self._audit(principal, "dataset.reparse", kind, {"documents": len(ids)})
        return {"kind": kind, "documents": len(ids)}

    def rebuild(self, principal: Principal, kind: str) -> dict[str, Any]:
        """换嵌入模型后重建：新建数据集，原件从旧数据集下载迁移，结构化资料重新同步，最后删除旧数据集。"""
        require_kb_role(principal, "write")
        self._kind(kind)
        client = self._client(principal)
        company = principal.user.company_id
        old = self._dataset(principal, kind, create=False)
        state = self.repository.read()
        index = read_index(state, company)
        migrated, failed = 0, []
        files = {k: e for k, e in index.get("files", {}).items() if e.get("dataset_kind") == kind}
        blobs: dict[str, bytes] = {}
        for key, entry in files.items():  # 先把原件全部取回，确认可迁移再动数据集
            try:
                blobs[key] = client.download_document(old["dataset_id"], entry["document_id"])
            except Exception:
                failed.append(entry.get("name", key))
        if failed:
            raise DomainError(409, "REBUILD_BLOCKED", "以下原件无法从旧数据集取回，已停止重建：" + "、".join(failed[:10]))

        def detach(idx: dict) -> None:
            idx["datasets"].pop(kind, None)
            if kind == "library":
                idx["dataset_id"] = ""
                idx["entries"] = {}
        self.kb._update_index(company, detach)
        try:
            new = self.kb.ensure_dataset(client, company, kind, force_new=True)
            if kind == "library":
                self.kb.sync_company(company)
            for key, entry in files.items():
                doc = client.upload_file(new["dataset_id"], entry["name"], blobs[key], entry.get("content_type", ""))
                if entry.get("meta_fields") or entry.get("user_meta"):
                    client.update_document(new["dataset_id"], doc.id, meta_fields=entry.get("user_meta") or {})
                client.trigger_parse(new["dataset_id"], [doc.id])

                def move(idx: dict, key=key, doc_id=doc.id) -> None:
                    idx["files"][key] = {**idx["files"][key], "document_id": doc_id, "status": STATUS_PARSING}
                self.kb._update_index(company, move)
                migrated += 1
            client.delete_datasets([old["dataset_id"]])
        except Exception as exc:
            raise self._wrap(exc, "重建数据集") from None
        self._audit(principal, "dataset.rebuild", kind, {"old": old["dataset_id"], "new": new["dataset_id"],
                                                        "migrated_files": migrated})
        return {"kind": kind, "old_dataset_id": old["dataset_id"], "dataset_id": new["dataset_id"],
                "migrated_files": migrated}

    def delete_dataset(self, principal: Principal, kind: str, confirm_name: str) -> dict[str, Any]:
        require_kb_role(principal, "connection")
        self._kind(kind)
        company = principal.user.company_id
        info = self._dataset(principal, kind, create=False)
        expected = f"{company}::{DATASET_KINDS[kind]}"
        if confirm_name != expected:
            raise DomainError(422, "CONFIRMATION_REQUIRED", f"请输入数据集全名 {expected} 以确认删除。")
        try:
            self._client(principal).delete_datasets([info["dataset_id"]])
        except Exception as exc:
            raise self._wrap(exc, "删除数据集") from None

        def detach(idx: dict) -> None:
            idx["datasets"].pop(kind, None)
            idx["files"] = {k: e for k, e in idx["files"].items() if e.get("dataset_kind") != kind}
            if kind == "library":
                idx["dataset_id"] = ""
                idx["entries"] = {}
        self.kb._update_index(company, detach)
        self._audit(principal, "dataset.delete", kind, {"dataset_id": info["dataset_id"]})
        return {"kind": kind, "deleted": True}

    def metadata_summary(self, principal: Principal, kind: str) -> dict[str, Any]:
        require_kb_role(principal, "read")
        info = self._dataset(principal, self._kind(kind), create=False)
        try:
            return {"kind": kind, "summary": self._client(principal).metadata_summary(info["dataset_id"])}
        except Exception as exc:
            raise self._wrap(exc, "读取元数据汇总") from None

    # ---------- 文档 ----------

    def documents(self, principal: Principal, kind: str, *, page: int = 1, page_size: int = 30,
                  keywords: str | None = None) -> dict[str, Any]:
        require_kb_role(principal, "read")
        self._kind(kind)
        company = principal.user.company_id
        info = read_index(self.repository.read(), company).get("datasets", {}).get(kind)
        if not info or not info.get("dataset_id"):
            return {"kind": kind, "items": [], "page": page}
        index = read_index(self.repository.read(), company)
        pool = index.get("files", {}) if kind in FILE_KINDS else index.get("entries", {})
        by_doc = {e.get("document_id"): e for e in pool.values()}
        try:
            docs = self._client(principal).list_documents(info["dataset_id"], page=page, page_size=page_size)
        except Exception as exc:
            raise self._wrap(exc, "读取文档列表") from None
        items = []
        for doc in docs:
            entry = by_doc.get(doc.id) or {}
            if keywords and keywords not in doc.name and keywords not in str(entry.get("name", "")):
                continue
            items.append({"document_id": doc.id, "name": doc.name, "status": doc.sync_status, "run": doc.run,
                          "progress": doc.progress, "message": doc.progress_msg, "chunk_count": doc.chunk_count,
                          "meta_fields": doc.meta_fields, "enabled": str(doc.raw.get("enabled", 1)) not in ("0", "False"),
                          "source_type": entry.get("source_type", "unmanaged"), "source_id": entry.get("source_id", ""),
                          "key": entry.get("key", ""), "uploaded_by": entry.get("uploaded_by", "")})
        return {"kind": kind, "items": items, "page": page}

    def upload(self, principal: Principal, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        """上传原件到历史投标或证书数据集，并按 ICG 流程解析。"""
        require_kb_role(principal, "write")
        self._kind(kind, files_only=True)
        filename = str(payload.get("filename") or "").strip()
        if not filename or "/" in filename or "\\" in filename:
            raise DomainError(422, "VALIDATION_ERROR", "文件名无效。")
        if not filename.lower().endswith(UPLOAD_SUFFIXES[kind]):
            raise DomainError(422, "FILE_TYPE_UNSUPPORTED", "该类知识只接受：" + "、".join(UPLOAD_SUFFIXES[kind]))
        try:
            data = base64.b64decode(str(payload.get("content_base64") or ""), validate=True)
        except (binascii.Error, ValueError):
            raise DomainError(422, "VALIDATION_ERROR", "文件内容不是合法的 base64。") from None
        if not data:
            raise DomainError(422, "VALIDATION_ERROR", "文件为空。")
        if len(data) > MAX_UPLOAD_BYTES:
            raise DomainError(413, "FILE_SIZE_LIMIT", "单个文件不能超过 50MB。")
        user_meta = {str(k)[:64]: str(v)[:500] for k, v in (payload.get("metadata") or {}).items() if str(v).strip()}
        company = principal.user.company_id
        client = self._client(principal)
        info = self._dataset(principal, kind)
        file_id = new_id("kbfile")
        meta = {**user_meta, "company_id": company, "source_type": SOURCE_FILE, "source_id": file_id,
                "knowledge_kind": kind}
        try:
            doc = client.upload_file(info["dataset_id"], filename, data, str(payload.get("content_type") or ""))
            client.update_document(info["dataset_id"], doc.id, meta_fields=meta)
            client.trigger_parse(info["dataset_id"], [doc.id])
        except Exception as exc:
            raise self._wrap(exc, "上传原件") from None
        now = iso_time(self.demo._now())
        entry = {"key": f"{SOURCE_FILE}:{file_id}", "source_type": SOURCE_FILE, "source_id": file_id,
                 "dataset_kind": kind, "company_id": company, "name": filename, "item_type": kind, "revision": 1,
                 "document_id": doc.id, "status": STATUS_PARSING, "message": "", "chunk_count": 0,
                 "content_type": str(payload.get("content_type") or ""), "size": len(data), "enabled": True,
                 "user_meta": user_meta, "uploaded_by": principal.user.id, "updated_at": now}
        self.kb._update_index(company, lambda idx: idx["files"].__setitem__(entry["key"], entry))
        self._audit(principal, "document.upload", entry["key"], {"kind": kind, "name": filename, "size": len(data)})
        self.kb.refresh_status(company)
        current = read_index(self.repository.read(), company)["files"].get(entry["key"], entry)
        return {k: v for k, v in current.items() if k != "content_hash"}

    def update_document(self, principal: Principal, kind: str, document_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        require_kb_role(principal, "write")
        self._kind(kind)
        dataset_id, entry = self._owned_document(principal, kind, document_id)
        enabled = payload.get("enabled")
        user_meta = payload.get("metadata")
        if kind == "library" and user_meta is not None:
            raise DomainError(409, "MANAGED_DOCUMENT", "资料与片段文档的元数据由系统维护，请在资料库中修改资料。")
        meta = None
        if user_meta is not None:
            if entry is None:
                raise DomainError(409, "MANAGED_DOCUMENT", "该文档不是本系统上传的原件，不能修改元数据。")
            clean = {str(k)[:64]: str(v)[:500] for k, v in user_meta.items() if str(v).strip()}
            meta = {**clean, "company_id": principal.user.company_id, "source_type": SOURCE_FILE,
                    "source_id": entry["source_id"], "knowledge_kind": kind}
        try:
            self._client(principal).update_document(dataset_id, document_id, meta_fields=meta,
                                                    enabled=None if enabled is None else bool(enabled))
        except Exception as exc:
            raise self._wrap(exc, "更新文档") from None
        if entry is not None:
            pool = "files" if kind in FILE_KINDS else "entries"

            def apply(idx: dict) -> None:
                target = idx[pool][entry["key"]]
                if enabled is not None:
                    target["enabled"] = bool(enabled)
                if meta is not None:
                    target["user_meta"] = {k: v for k, v in meta.items()
                                           if k not in ("company_id", "source_type", "source_id", "knowledge_kind")}
            self.kb._update_index(principal.user.company_id, apply)
        self._audit(principal, "document.update", document_id, {"kind": kind, "enabled": enabled,
                                                                "metadata_keys": sorted((user_meta or {}).keys())})
        return {"document_id": document_id, "updated": True}

    def reparse_document(self, principal: Principal, kind: str, document_id: str) -> dict[str, Any]:
        require_kb_role(principal, "write")
        dataset_id, entry = self._owned_document(principal, self._kind(kind), document_id)
        try:
            self._client(principal).trigger_parse(dataset_id, [document_id])
        except Exception as exc:
            raise self._wrap(exc, "重新解析文档") from None
        if entry is not None:
            pool = "files" if kind in FILE_KINDS else "entries"
            self.kb._update_index(principal.user.company_id,
                                  lambda idx: idx[pool][entry["key"]].__setitem__("status", STATUS_PARSING))
        self._audit(principal, "document.reparse", document_id, {"kind": kind})
        return {"document_id": document_id, "status": STATUS_PARSING}

    def stop_parse(self, principal: Principal, kind: str, document_id: str) -> dict[str, Any]:
        require_kb_role(principal, "write")
        dataset_id, entry = self._owned_document(principal, self._kind(kind), document_id)
        try:
            self._client(principal).stop_parse(dataset_id, [document_id])
        except Exception as exc:
            raise self._wrap(exc, "停止解析") from None
        if entry is not None:
            pool = "files" if kind in FILE_KINDS else "entries"

            def apply(idx: dict) -> None:
                idx[pool][entry["key"]].update(status=STATUS_FAILED, message="已由管理员停止解析")
            self.kb._update_index(principal.user.company_id, apply)
        self._audit(principal, "document.stop_parse", document_id, {"kind": kind})
        return {"document_id": document_id, "status": STATUS_FAILED}

    def delete_document(self, principal: Principal, kind: str, document_id: str) -> dict[str, Any]:
        require_kb_role(principal, "write")
        self._kind(kind)
        if kind == "library":
            raise DomainError(409, "MANAGED_DOCUMENT", "资料与片段文档由系统同步维护；请在资料库撤销确认或下架片段，系统会自动删除。")
        dataset_id, entry = self._owned_document(principal, kind, document_id)
        try:
            self._client(principal).delete_documents(dataset_id, [document_id])
        except Exception as exc:
            raise self._wrap(exc, "删除文档") from None
        if entry is not None:
            self.kb._update_index(principal.user.company_id, lambda idx: idx["files"].pop(entry["key"], None))
        self._audit(principal, "document.delete", document_id, {"kind": kind, "name": (entry or {}).get("name", "")})
        return {"document_id": document_id, "deleted": True}

    # ---------- 分块 ----------

    def chunks(self, principal: Principal, kind: str, document_id: str, *, keywords: str | None = None,
               page: int = 1, page_size: int = 30) -> dict[str, Any]:
        require_kb_role(principal, "read")
        dataset_id, _ = self._owned_document(principal, self._kind(kind), document_id)
        try:
            return {"document_id": document_id, **self._client(principal).list_chunks(
                dataset_id, document_id, keywords=keywords, page=page, page_size=page_size)}
        except Exception as exc:
            raise self._wrap(exc, "读取分块") from None

    def update_chunk(self, principal: Principal, kind: str, document_id: str, chunk_id: str,
                     payload: dict[str, Any]) -> dict[str, Any]:
        """人工修正分块：改正文、关键词、问题，或停用错误分块。修正结果只影响检索，不改资料本身。"""
        require_kb_role(principal, "write")
        self._kind(kind)
        if kind == "library" and payload.get("content") is not None:
            raise DomainError(409, "MANAGED_DOCUMENT", "资料与片段的正文请在资料库中修改；这里只能调整关键词、问题和启停。")
        dataset_id, _ = self._owned_document(principal, kind, document_id)
        fields = {k: payload[k] for k in ("content", "important_keywords", "questions", "available") if k in payload}
        if not fields:
            raise DomainError(422, "VALIDATION_ERROR", "没有要修改的字段。")
        try:
            self._client(principal).update_chunk(dataset_id, document_id, chunk_id, **fields)
        except Exception as exc:
            raise self._wrap(exc, "修改分块") from None
        self._audit(principal, "chunk.update", chunk_id, {"kind": kind, "document_id": document_id,
                                                          "fields": sorted(fields)})
        return {"chunk_id": chunk_id, "updated": sorted(fields)}

    # ---------- 检索试查 ----------

    def retrieval_test(self, principal: Principal, payload: dict[str, Any]) -> dict[str, Any]:
        require_kb_role(principal, "read")
        query = str(payload.get("query") or "").strip()
        if not query:
            raise DomainError(422, "VALIDATION_ERROR", "请输入试查问题。")
        overrides = {k: payload[k] for k in ("similarity_threshold", "keywords_weight", "rerank_id")
                     if payload.get(k) is not None}
        kinds = set(payload.get("kinds") or ["evidence", "snippet", "history"])
        if not kinds <= {"evidence", "snippet", "history"}:
            raise DomainError(422, "VALIDATION_ERROR", "kinds 只能是 evidence、snippet、history。")
        limit = max(1, min(int(payload.get("limit") or 8), 20))
        try:
            hits, reason = self.kb.search(principal.user.company_id, query, limit=limit, kinds=kinds,
                                          user=principal.user, overrides=overrides)
        except Exception as exc:
            raise self._wrap(exc, "检索试查") from None
        return {"query": query, "parameters": {**self._public_settings(read_settings(self.repository.read(),
                                                                                      principal.user.company_id)),
                                               **overrides},
                "items": [h.to_public() for h in hits], "skipped_reason": reason}

    # ---------- 证书附件 → 资料草稿 ----------

    def certificate_draft(self, principal: Principal, document_id: str) -> dict[str, Any]:
        """用证书流程抽取的字段生成“待核验”资料。只填字段、不确认：确认必须由资料管理员在资料库完成。"""
        require_kb_role(principal, "write")
        dataset_id, entry = self._owned_document(principal, "certificate", document_id)
        if entry is None:
            raise DomainError(404, "NOT_FOUND", "该文档不是本系统上传的证书附件。")
        try:
            document = self._client(principal).get_document_status(dataset_id, document_id)
        except Exception as exc:
            raise self._wrap(exc, "读取抽取结果") from None
        if document.sync_status != "synced":
            raise DomainError(409, "KB_DOCUMENT_NOT_READY", "证书仍在解析或解析失败，暂不能生成资料草稿。")
        meta = {**(entry.get("user_meta") or {}), **{k: v for k, v in document.meta_fields.items()
                                                    if k not in ("company_id", "source_type", "source_id", "knowledge_kind")}}
        name = str(meta.get("cert_name") or entry["name"]).strip()[:200]
        valid = str(meta.get("valid_to") or "").strip()
        lines = [f"{label}：{meta[key]}" for key, label in (("cert_no", "证书编号"), ("issuer", "发证机构"),
                                                            ("holder", "持有人"), ("scope", "范围/等级"))
                 if str(meta.get(key) or "").strip()]
        lines.append(f"来源附件：{entry['name']}（知识库自动抽取，须人工核对原件）")
        payload: dict[str, Any] = {"name": name, "type": "qualification", "content": "\n".join(lines),
                                   "status": "pending"}
        if valid == "long_term":
            payload["is_long_term"] = True
        elif len(valid) == 10 and valid[4] == "-" and valid[7] == "-":
            payload["valid_until"] = valid
        revision = self.repository.read().library_revisions.get(principal.user.company_id, 1)
        from .parsing import LocalTextParser
        from .workflow import WorkflowService
        result = WorkflowService(self.demo, LocalTextParser()).write_library(principal, payload, str(revision),
                                                                            new_id("kbdraft"))
        self._audit(principal, "certificate.draft", document_id, {"library_id": result["item"]["id"]})
        return {"library_item": result["item"], "extracted": meta}

    def audit(self, principal: Principal, limit: int = 100) -> dict[str, Any]:
        require_kb_role(principal, "read")
        rows = (self.repository.read().service_stores.get(AUDIT_STORE) or {}).get(principal.user.company_id) or []
        return {"items": list(reversed(rows[-max(1, min(limit, AUDIT_LIMIT)):]))}


__all__ = ["KbAdminService", "require_kb_role", "default_settings"]
