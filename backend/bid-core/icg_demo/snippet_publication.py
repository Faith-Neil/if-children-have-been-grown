# 为什么有这个文件：把片段草稿、发布和同步放在独立内存存储里。
# 它解决什么问题：避免片段状态进入 DemoState 的整包读写，同时仍复用已有的幂等回执。

from __future__ import annotations

from copy import deepcopy
import json
import re
from threading import RLock

from fastapi import APIRouter, Depends, Header, Response

from .domain import DomainError, content_hash, iso_time, new_id
from .idempotency import IDEMPOTENCY_HEADER_DESCRIPTION, fingerprint, lookup, remember, validate_key
from .schemas import EmptyRequest
from .workflow_schemas import (
    SnippetPublication, SnippetPublicationCreate, SnippetPublicationDraft, SnippetPublicationList,
    SnippetPublishResult, SnippetSyncResult, v1_error_responses)


VARIABLE = re.compile(r"\{\{([A-Za-z0-9_.-]+)\}\}")
SNIPPET_REF = re.compile(r"snippet:([A-Za-z0-9_-]+)")
DRAFT_FIELDS = ("product", "snippet_type", "variables", "source_group", "boilerplate_group", "draft_body")
REASON_TEXT = {
    "real_report": "正文提到报告，但没有来源组，不能当作真实报告发布。",
    "hardcoded_promise": "正文把承诺写成了固定数字，请改成变量。",
    "unknown_variable": "正文使用了未声明的变量。",
    "unpublished_body": "没有可发布的正文，或引用的本公司片段尚未发布。",
    "cross_company_reference": "正文引用了其他公司的片段。",
}


def _version(actual: int, expected: int) -> None:
    if expected != actual:
        raise DomainError(409, "VERSION_CONFLICT", "数据已被更新，请刷新核对后再保存。", {"current_revision": actual})


def _expected_revision(header: str | None) -> int:
    if header is None:
        raise DomainError(428, "IF_MATCH_REQUIRED", "此操作需要最新版本号，请刷新页面再保存。")
    raw = header.strip().strip('"')
    if not raw.isdigit():
        raise DomainError(409, "VERSION_CONFLICT", "数据已被更新，请刷新核对后再保存。")
    return int(raw)


def _public(record: dict) -> dict:
    return {key: deepcopy(record[key]) for key in (
        "id", "company_id", "product", "snippet_type", "variables", "source_group",
        "boilerplate_group", "draft_body", "published_body", "draft_revision",
        "published_revision", "kb_sync_status", "updated_at")}


class MemorySnippetPublicationStore:
    """进程内字典。重启丢失。不经过 Repository.read 或 transaction。"""

    def __init__(self, clock):
        self._clock = clock
        self._lock = RLock()
        self.records: dict[str, dict] = {}
        self.audits: dict[str, list] = {}

    def snapshot(self) -> dict:
        with self._lock:
            return {"records": deepcopy(self.records), "audits": deepcopy(self.audits)}

    def transaction(self, operation):
        # 序列化整个回执/片段操作；回执提交失败时恢复独立片段与审计。
        # 仍只保障本进程，不能把内存片段说成跨进程持久化。
        with self._lock:
            before = self.snapshot()
            try:
                return operation()
            except Exception:
                self.records = before["records"]
                self.audits = before["audits"]
                raise

    def list(self, company_id: str) -> list:
        with self._lock:
            items = [_public(item) for item in self.records.values() if item["company_id"] == company_id]
        return sorted(items, key=lambda item: item["id"])

    def get(self, company_id: str, snippet_id: str) -> dict:
        with self._lock:
            return _public(self._owned(company_id, snippet_id))

    def create(self, company_id: str, payload: dict) -> dict:
        with self._lock:
            record = {
                "id": new_id("snippet"),
                "company_id": company_id,
                "product": payload["product"],
                "snippet_type": payload["snippet_type"],
                "variables": list(payload.get("variables", [])),
                "source_group": payload.get("source_group", ""),
                "boilerplate_group": payload.get("boilerplate_group", ""),
                "draft_body": payload.get("draft_body", ""),
                "published_body": "",
                "draft_revision": 1,
                "published_revision": 0,
                "kb_sync_status": "unsynced",
                "updated_at": iso_time(self._clock()),
            }
            self.records[record["id"]] = record
            self.audits[record["id"]] = []
            return _public(record)

    def save_draft(self, company_id: str, snippet_id: str, payload: dict, draft_revision: int) -> dict:
        with self._lock:
            record = self._owned(company_id, snippet_id)
            _version(record["draft_revision"], draft_revision)
            for key in DRAFT_FIELDS:
                if key in payload and payload[key] is not None:
                    record[key] = deepcopy(payload[key])
            record["draft_revision"] += 1
            record["updated_at"] = iso_time(self._clock())
            return _public(record)

    def publish(self, company_id: str, snippet_id: str, draft_revision: int) -> dict:
        with self._lock:
            record = self._owned(company_id, snippet_id)
            _version(record["draft_revision"], draft_revision)
            reasons = self._block_reasons(company_id, record)
            if reasons:
                return {"item": _public(record), "blocked": True, "reasons": reasons}
            record["published_body"] = record["draft_body"]
            record["published_revision"] += 1
            record["kb_sync_status"] = "unsynced"
            record["updated_at"] = iso_time(self._clock())
            self.audits[snippet_id].append({
                "action": "publish", "published_revision": record["published_revision"],
                "at": record["updated_at"]})
            return {"item": _public(record), "blocked": False, "reasons": []}

    def sync(self, company_id: str, snippet_id: str, published_revision: int) -> dict:
        with self._lock:
            record = self._owned(company_id, snippet_id)
            _version(record["published_revision"], published_revision)
            if record["published_revision"] == 0 or "[[sync-fail]]" in record["published_body"]:
                record["kb_sync_status"] = "failed"
                record["updated_at"] = iso_time(self._clock())
                return {"item": _public(record), "synced": False}
            record["kb_sync_status"] = "synced"
            record["updated_at"] = iso_time(self._clock())
            self.audits[snippet_id].append({
                "action": "sync", "published_revision": record["published_revision"],
                "at": record["updated_at"]})
            return {"item": _public(record), "synced": True}

    def _owned(self, company_id: str, snippet_id: str) -> dict:
        record = self.records.get(snippet_id)
        if record is None or record["company_id"] != company_id:
            raise DomainError(404, "NOT_FOUND", "未找到本公司片段。")
        return record

    def _block_reasons(self, company_id: str, record: dict) -> list[dict]:
        body = record["draft_body"]
        declared = set(record["variables"])
        plain = VARIABLE.sub("", body)
        unknown = [name for name in VARIABLE.findall(body) if name not in declared]
        unpublished = not body.strip()
        cross_company = False
        for snippet_id in SNIPPET_REF.findall(body):
            other = self.records.get(snippet_id)
            if other is None or other["company_id"] != company_id:
                cross_company = True
                continue
            if not other["published_body"].strip():
                unpublished = True
        reasons = []
        if "报告" in body and not record["source_group"].strip():
            reasons.append("real_report")
        if "承诺" in body and re.search(r"\d", plain):
            reasons.append("hardcoded_promise")
        if unknown:
            reasons.append("unknown_variable")
        if unpublished:
            reasons.append("unpublished_body")
        if cross_company:
            reasons.append("cross_company_reference")
        rendered = []
        for code in reasons:
            message = REASON_TEXT[code]
            if code == "unknown_variable":
                message += "：" + "、".join(unknown)
            rendered.append({"code": code, "message": message})
        return rendered


class SnippetPublicationService:
    def __init__(self, store: MemorySnippetPublicationStore, repository, clock, writer):
        self.store = store
        self.repository = repository
        self._clock = clock
        self._writer = writer

    def list(self, principal) -> dict:
        return {"items": self.store.list(principal.user.company_id)}

    def get(self, principal, snippet_id: str) -> dict:
        return self.store.get(principal.user.company_id, snippet_id)

    def create(self, principal, payload: dict, key: str | None, if_match: str | None) -> dict:
        self._writer(principal)
        return self._receipt(principal, "snippet.create", payload, if_match, key,
                             lambda: self.store.create(principal.user.company_id, payload))

    def save_draft(self, principal, snippet_id: str, payload: dict, if_match: str | None, key: str | None) -> dict:
        self._writer(principal)
        validate_key(key)
        expected = _expected_revision(if_match)
        return self._receipt(principal, "snippet.save:" + snippet_id, payload, if_match, key,
                             lambda: self.store.save_draft(
                                 principal.user.company_id, snippet_id, payload, expected))

    def publish(self, principal, snippet_id: str, payload: dict, if_match: str | None, key: str | None) -> dict:
        self._writer(principal)
        validate_key(key)
        expected = _expected_revision(if_match)
        return self._receipt(principal, "snippet.publish:" + snippet_id, payload, if_match, key,
                             lambda: self.store.publish(principal.user.company_id, snippet_id, expected))

    def sync(self, principal, snippet_id: str, payload: dict, if_match: str | None, key: str | None) -> dict:
        self._writer(principal)
        validate_key(key)
        expected = _expected_revision(if_match)
        return self._receipt(principal, "snippet.sync:" + snippet_id, payload, if_match, key,
                             lambda: self.store.sync(principal.user.company_id, snippet_id, expected))

    def _receipt(self, principal, action: str, payload: dict, if_match: str | None, key: str | None, mutate):
        # 回执仍写在既有 DemoState.workflow_receipts，作用域与公司资料相同。
        # 片段记录仍不进入DemoState；独立存储外层锁和回滚覆盖整个回执事务。
        key = validate_key(key)
        scope_id = "library:" + principal.user.company_id
        request_fingerprint = fingerprint(action, payload, if_match)

        def apply(state):
            now = self._clock()
            replay = lookup(state, scope_id, principal.user.id, key, request_fingerprint, now)
            if replay is not None:
                return replay
            result = mutate()
            remember(state, scope_id, principal.user.id, key, request_fingerprint, result, now)
            return result

        return self.store.transaction(lambda: self.repository.transaction(apply))


def include_snippet_routes(application, service, current_user) -> None:
    store = MemorySnippetPublicationStore(clock=service._now)
    application.state.snippet_publications = store
    publications = SnippetPublicationService(store, service.repository, service._now, service._writer)
    application.state.snippet_publication_service = publications
    router = APIRouter(prefix="/api/v1", responses=v1_error_responses(401, 403, 404, 409, 422, 428, 500))

    @router.get("/snippet-publications", response_model=SnippetPublicationList, operation_id="listSnippetPublications")
    def list_publications(response: Response, user=Depends(current_user)):
        """列出本公司片段。响应头 ETag 是这份列表的指纹，不是单条草稿版本。"""
        result = publications.list(user)
        response.headers["ETag"] = '"' + _list_etag(result["items"]) + '"'
        return result

    @router.post("/snippet-publications", response_model=SnippetPublication, operation_id="createSnippetPublication")
    def create_publication(body: SnippetPublicationCreate, response: Response, user=Depends(current_user),
                           if_match: str | None = Header(default=None),
                           idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        """服务端分配片段 id。公司来自登录身份。不需要 If-Match。"""
        result = publications.create(user, body.model_dump(), idempotency_key, if_match)
        response.headers["ETag"] = f'"{result["draft_revision"]}"'
        return result

    @router.get("/snippet-publications/{snippet_id}", response_model=SnippetPublication, operation_id="getSnippetPublication")
    def get_publication(snippet_id: str, response: Response, user=Depends(current_user)):
        """读取一条。ETag 是 draft_revision，供保存草稿和发布的 If-Match 使用。详情里的 kb_sync_status 就是同步状态，不再另设 GET .../sync。"""
        result = publications.get(user, snippet_id)
        response.headers["ETag"] = f'"{result["draft_revision"]}"'
        return result

    @router.put("/snippet-publications/{snippet_id}", response_model=SnippetPublication, operation_id="saveSnippetPublicationDraft")
    def save_publication(snippet_id: str, body: SnippetPublicationDraft, response: Response, user=Depends(current_user),
                         if_match: str | None = Header(default=None),
                         idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        """保存草稿。If-Match 核对 draft_revision。不替换已发布正文。"""
        result = publications.save_draft(user, snippet_id, body.model_dump(exclude_unset=True), if_match, idempotency_key)
        response.headers["ETag"] = f'"{result["draft_revision"]}"'
        return result

    @router.post("/snippet-publications/{snippet_id}/publish", response_model=SnippetPublishResult, operation_id="publishSnippetPublication")
    def publish_publication(snippet_id: str, body: EmptyRequest, user=Depends(current_user),
                            if_match: str | None = Header(default=None),
                            idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        """发布。If-Match 核对 draft_revision。被拦截时返回 200 和原因，记录与审计不变，但仍记下幂等回执。"""
        return publications.publish(user, snippet_id, body.model_dump(), if_match, idempotency_key)

    @router.post("/snippet-publications/{snippet_id}/sync", response_model=SnippetSyncResult, operation_id="syncSnippetPublication")
    def sync_publication(snippet_id: str, body: EmptyRequest, user=Depends(current_user),
                         if_match: str | None = Header(default=None),
                         idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        """重新同步。If-Match 核对 published_revision。失败不把 kb_sync_status 写成 synced。正文含 [[sync-fail]] 时模拟知识库拒绝。"""
        return publications.sync(user, snippet_id, body.model_dump(), if_match, idempotency_key)

    application.include_router(router)


def _list_etag(items: list) -> str:
    return content_hash(json.dumps(items, ensure_ascii=False, sort_keys=True))
