# 为什么有这个文件：资料的附件扫描件与导出插入计划（PRD v1.8 §5.4.7 附件库、§5.9.1 规则 7 与 9、R14、R38、R42；
# 字典 attachment / attachment_link：页码范围、敏感、功能点标签；APP-M2-T059、T198）。
# 它解决什么问题：
# 1. 资料库每条资料可挂多份扫描件（PDF、PNG、JPG）；按文件头判断类型、读出页数，坏文件当场拒收；
# 2. 扫描件一律用 ICG_SECRET_KEY 加密后再进文件存储（证照、身份证件都是高敏资料），下载原件要登录、同公司并记审计；
# 3. 同一公司内按内容指纹去重：同一资料重复上传返回已有附件；公司之间互不可见；
# 4. 每份附件可设：插入页码范围、是否敏感（导出时加水印）、是否带公司名称或标志（暗标分册不插）、功能点标签（R38 用）；
# 5. 导出时按条款挂接的证据，把附件排到“对应位置”：条款对应章节之后；没有对应章节时放本册证明材料清单之后，
#    再没有就放本册末尾；同一册同一附件只插一次。

from __future__ import annotations

import hashlib
from typing import Any

from .domain import DemoState, DomainError, Principal, iso_time, new_id

STORE = "attachments"
MAX_TAGS = 30


def _items(state: DemoState) -> dict:
    return (state.service_stores.get(STORE) or {}).get("items") or {}


def _fernet():
    from icg.infra.model_config_storage import _fernet_from_secret, get_master_key
    try:
        return _fernet_from_secret(get_master_key())
    except DomainError as error:
        raise DomainError(503, "SECRET_KEY_UNAVAILABLE", "附件扫描件需加密保存，服务器未配置主密钥 ICG_SECRET_KEY，请联系平台管理员。") from error


def plain_bytes(record: dict) -> bytes:
    from icg.infra.blob_store import get_blob
    return _fernet().decrypt(get_blob(record["blob"]))


def public(record: dict) -> dict:
    keys = ("id", "library_id", "filename", "kind", "size_bytes", "sha256", "page_count", "page_from", "page_to",
            "is_sensitive", "shows_identity", "feature_tags", "uploaded_by", "uploaded_at", "revision")
    return {k: record[k] for k in keys}


def for_library(state: DemoState, company_id: str, library_id: str) -> list[dict]:
    rows = [r for r in _items(state).values() if r["company_id"] == company_id and r["library_id"] == library_id]
    return sorted(rows, key=lambda r: r["uploaded_at"])


class AttachmentService:
    def __init__(self, demo: Any) -> None:
        self.demo = demo

    def _item(self, state: DemoState, principal: Principal, library_id: str) -> dict:
        item = state.library.get(library_id)
        if item is None or item["company_id"] != principal.user.company_id:
            raise DomainError(404, "NOT_FOUND", "未找到本公司资料。")
        from .library_orchestrator import LibraryOrchestratorMixin
        if item.get("is_restricted") and not LibraryOrchestratorMixin._restricted_allowed(state, principal, item):
            raise DomainError(403, "FORBIDDEN", "受限资料的附件只有公司管理员、资料管理员或被授权人可以查看。")
        return item

    def _record(self, state: DemoState, principal: Principal, attachment_id: str) -> dict:
        record = _items(state).get(attachment_id)
        if record is None or record["company_id"] != principal.user.company_id:
            raise DomainError(404, "NOT_FOUND", "未找到本公司的这份附件。")
        self._item(state, principal, record["library_id"])
        return record

    def list(self, principal: Principal, library_id: str) -> dict:
        state = self.demo.repository.read()
        self._item(state, principal, library_id)
        return {"items": [public(r) for r in for_library(state, principal.user.company_id, library_id)]}

    def upload(self, principal: Principal, library_id: str, filename: str, data: bytes) -> dict:
        from icg.infra.blob_store import put_blob
        from icg.infra.docx_media import AttachmentRenderError, page_count, sniff
        self.demo._writer(principal)
        kind = sniff(data)
        if kind is None:
            raise DomainError(422, "ATTACHMENT_TYPE_UNSUPPORTED", "附件扫描件只支持 PDF、PNG、JPG。")
        try:
            pages = page_count(data)
        except AttachmentRenderError as error:
            raise DomainError(422, "ATTACHMENT_UNREADABLE", f"附件无法读取：{error}") from error
        if pages < 1:
            raise DomainError(422, "ATTACHMENT_UNREADABLE", "附件没有任何页面。")
        digest = hashlib.sha256(data).hexdigest()
        company = principal.user.company_id
        state = self.demo.repository.read()
        self._item(state, principal, library_id)
        existing = next((r for r in for_library(state, company, library_id) if r["sha256"] == digest), None)
        if existing is not None:
            return {"attachment": public(existing), "duplicate": True}
        blob = put_blob(_fernet().encrypt(data))
        now = iso_time(self.demo._now())

        def write(state: DemoState):
            item = self._item(state, principal, library_id)
            again = next((r for r in for_library(state, company, library_id) if r["sha256"] == digest), None)
            if again is not None:
                return {"attachment": public(again), "duplicate": True}
            record = {"id": new_id("attachment"), "company_id": company, "library_id": library_id, "filename": filename,
                      "kind": kind, "blob": blob, "sha256": digest, "size_bytes": len(data), "page_count": pages,
                      "page_from": 1, "page_to": pages, "is_sensitive": True, "shows_identity": True,
                      "feature_tags": [], "uploaded_by": principal.user.id, "uploaded_at": now, "revision": 1}
            state.service_stores.setdefault(STORE, {}).setdefault("items", {})[record["id"]] = record
            state.audit.append({"id": new_id("event"), "action": "attachment.upload", "actor_id": principal.user.id,
                                "company_id": company, "at": now,
                                "details": {"attachment_id": record["id"], "library_id": item["id"], "sha256": digest}})
            return {"attachment": public(record), "duplicate": False}
        return self.demo.repository.transaction(write)

    def update(self, principal: Principal, attachment_id: str, payload: dict, expected: int | None) -> dict:
        self.demo._writer(principal)

        def write(state: DemoState):
            record = self._record(state, principal, attachment_id)
            if expected is not None and expected != record["revision"]:
                raise DomainError(409, "VERSION_CONFLICT", "附件设置已被其他人修改，请刷新后再改。")
            first = payload.get("page_from", record["page_from"])
            last = payload.get("page_to", record["page_to"])
            if not 1 <= first <= last <= record["page_count"]:
                raise DomainError(422, "ATTACHMENT_PAGE_RANGE", f"页码范围须在第 1～{record['page_count']} 页之间，且起始页不大于结束页。")
            if "feature_tags" in payload:
                tags = []
                for tag in payload["feature_tags"]:
                    value = str(tag).strip()
                    if value and value not in tags:
                        tags.append(value)
                if len(tags) > MAX_TAGS:
                    raise DomainError(422, "VALIDATION_ERROR", f"功能点标签最多 {MAX_TAGS} 个。")
                record["feature_tags"] = tags
            for key in ("is_sensitive", "shows_identity"):
                if key in payload:
                    record[key] = bool(payload[key])
            record.update(page_from=first, page_to=last, revision=record["revision"] + 1)
            state.audit.append({"id": new_id("event"), "action": "attachment.update", "actor_id": principal.user.id,
                                "company_id": record["company_id"], "at": iso_time(self.demo._now()),
                                "details": {"attachment_id": attachment_id, **{k: payload[k] for k in payload}}})
            return {"attachment": public(record)}
        return self.demo.repository.transaction(write)

    def delete(self, principal: Principal, attachment_id: str) -> dict:
        self.demo._writer(principal)

        def write(state: DemoState):
            record = self._record(state, principal, attachment_id)
            del state.service_stores[STORE]["items"][attachment_id]
            state.audit.append({"id": new_id("event"), "action": "attachment.delete", "actor_id": principal.user.id,
                                "company_id": record["company_id"], "at": iso_time(self.demo._now()),
                                "details": {"attachment_id": attachment_id, "library_id": record["library_id"]}})
            return {"deleted": True}
        return self.demo.repository.transaction(write)

    def original(self, principal: Principal, attachment_id: str) -> tuple[dict, bytes]:
        record = self._record(self.demo.repository.read(), principal, attachment_id)
        data = plain_bytes(record)

        def audit(state: DemoState):
            state.audit.append({"id": new_id("event"), "action": "attachment.download", "actor_id": principal.user.id,
                                "company_id": record["company_id"], "at": iso_time(self.demo._now()),
                                "details": {"attachment_id": attachment_id}})
        self.demo.repository.transaction(audit)
        return record, data


def export_plan(state: DemoState, project: Any, workflow: dict, volume: str, chapters: list, line_ends: dict[str, int],
                *, default_volume: str, blind: bool, watermark: str) -> tuple[list[dict], list[dict]]:
    """本册要插的附件（含插在正文第几行之后）与因暗标跳过的附件；不读文件内容。"""
    from .system_chapters import kind_of
    ids = {c.id for c in chapters}
    proof = next((c.id for c in chapters if kind_of(c.title) == "proof_list"), None)
    last_line = max(line_ends.values()) if line_ends else -1
    files = list((workflow.get("files") or {}).keys())

    def order(row: dict):
        source = row.get("source") or {}
        return (files.index(source.get("file_id")) if source.get("file_id") in files else 99, source.get("page") or 0)

    plan, skipped, seen = [], [], set()
    rows = [r for r in (workflow.get("requirements") or {}).values()
            if r.get("status") != "rejected" and not r.get("out_of_scope") and r.get("evidence_ids")]
    for row in sorted(rows, key=order):
        if row.get("chapter_id") in ids:
            after = line_ends[row["chapter_id"]]
        elif row.get("chapter_id") and any(c.id == row["chapter_id"] for c in state.chapters.values()):
            continue  # 条款对应的章节在另一册
        elif proof is not None:
            after = line_ends[proof]
        elif (row.get("volume") or default_volume) == volume:
            after = last_line
        else:
            continue
        for library_id in row["evidence_ids"]:
            item = state.library.get(library_id)
            if item is None or item["company_id"] != project.company_id:
                continue
            for record in for_library(state, project.company_id, library_id):
                if record["id"] in seen:
                    continue
                seen.add(record["id"])
                if blind and record["shows_identity"]:
                    skipped.append({"attachment_id": record["id"], "name": item["name"], "filename": record["filename"],
                                    "reason": "暗标分册不插入带公司名称或标志的附件"})
                    continue
                plan.append({"attachment_id": record["id"], "library_id": library_id, "name": item["name"],
                             "filename": record["filename"], "blob": record["blob"], "sha256": record["sha256"],
                             "page_from": record["page_from"], "page_to": record["page_to"],
                             "page_count": record["page_count"], "after_line": after,
                             "watermark": watermark if record["is_sensitive"] else None})
    return plan, skipped
