# 为什么有这个文件：把片段草稿、发布和同步放在独立内存存储里。
# 它解决什么问题：避免片段状态进入 DemoState 的整包读写，同时仍复用已有的幂等回执。

from __future__ import annotations

from copy import deepcopy
import json
import re
from threading import RLock

from .domain import DomainError, content_hash, iso_time, new_id
from .idempotency import fingerprint, lookup, remember, validate_key


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
    """方案片段存储。

    绑定仓储后，片段与审计保存在 DemoState.service_stores["snippets"]：写操作在 SnippetPublicationService
    的仓储事务里绑定工作状态完成，读操作读取仓储快照，因此与其他状态一起持久化（ISSUE-041）。
    未绑定仓储（单元测试直接构造）时退回进程内字典。
    """

    def __init__(self, clock, repository=None):
        self._clock = clock
        self._lock = RLock()
        self._repository = repository
        self._bound: dict | None = None
        self._local = {"records": {}, "audits": {}}

    def _data(self) -> dict:
        if self._bound is not None:
            return self._bound
        if self._repository is not None:
            return self._repository.read().service_stores.get("snippets") or {"records": {}, "audits": {}}
        return self._local

    @property
    def records(self) -> dict[str, dict]:
        return self._data()["records"]

    @property
    def audits(self) -> dict[str, list]:
        return self._data()["audits"]

    def bind(self, state) -> None:
        self._bound = state.service_stores.setdefault("snippets", {"records": {}, "audits": {}})

    def unbind(self) -> None:
        self._bound = None

    def snapshot(self) -> dict:
        with self._lock:
            data = self._data()
            return {"records": deepcopy(data["records"]), "audits": deepcopy(data["audits"])}

    def transaction(self, operation):
        # 序列化整个回执/片段操作。绑定仓储时由仓储事务负责回滚；未绑定时恢复进程内字典。
        with self._lock:
            before = self.snapshot() if self._repository is None else None
            try:
                return operation()
            except Exception:
                if before is not None:
                    self._local = before
                raise
            finally:
                self.unbind()

    def update_kb_status(self, snippet_id: str, status: str, **extra) -> dict | None:
        """写回知识库同步状态（及 document_id 等附加字段）。

        绑定仓储时在仓储事务里改 DemoState.service_stores，保证持久化；读快照上的改动会丢失。
        """
        def apply_to(data: dict) -> dict | None:
            record = data["records"].get(snippet_id)
            if record is None:
                return None
            record["kb_sync_status"] = status
            for key, value in extra.items():
                record[key] = value
            record["updated_at"] = iso_time(self._clock())
            return _public(record)

        with self._lock:
            if self._repository is None:
                return apply_to(self._local)

            def apply(state):
                return apply_to(state.service_stores.setdefault("snippets", {"records": {}, "audits": {}}))

            return self._repository.transaction(apply)

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

    def sync(self, company_id: str, snippet_id: str, published_revision: int, kb_status: str | None = None) -> dict:
        """记录一次同步结果。kb_status 是知识库服务的真实结果；None 表示未配置知识库。

        未配置知识库时不再假装同步成功：状态保持/记为 unsynced，synced=False（ISSUE-039 同类：不伪造结果）。
        """
        with self._lock:
            record = self._owned(company_id, snippet_id)
            _version(record["published_revision"], published_revision)
            if record["published_revision"] == 0:
                record["kb_sync_status"] = "failed"
                record["updated_at"] = iso_time(self._clock())
                return {"item": _public(record), "synced": False}
            record["kb_sync_status"] = kb_status or "unsynced"
            record["updated_at"] = iso_time(self._clock())
            synced = record["kb_sync_status"] == "synced"
            if synced:
                self.audits[snippet_id].append({
                    "action": "sync", "published_revision": record["published_revision"],
                    "at": record["updated_at"]})
            return {"item": _public(record), "synced": synced}

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
    def __init__(self, store: MemorySnippetPublicationStore, repository, clock, writer, knowledge_base=None):
        self.store = store
        self.repository = repository
        self._clock = clock
        self._writer = writer
        self.knowledge_base = knowledge_base

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
        result = self._receipt(principal, "snippet.publish:" + snippet_id, payload, if_match, key,
                               lambda: self.store.publish(principal.user.company_id, snippet_id, expected))
        if not result.get("blocked") and self.knowledge_base is not None:
            self.knowledge_base.schedule(principal.user.company_id)
        return result

    def sync(self, principal, snippet_id: str, payload: dict, if_match: str | None, key: str | None) -> dict:
        self._writer(principal)
        validate_key(key)
        expected = _expected_revision(if_match)
        company_id = principal.user.company_id
        kb_status = None
        current = self.store.get(company_id, snippet_id)
        if current["published_revision"] == expected and expected > 0 and self.knowledge_base is not None \
                and self.knowledge_base.enabled(company_id):
            # 真同步：上传/解析在仓储事务之外完成，再把知识库返回的真实状态记入回执。
            entry_key = "snippet:" + snippet_id
            self.knowledge_base.sync_company(company_id, keys=[entry_key])
            row = next((r for r in self.knowledge_base.status(company_id)["items"] if r["key"] == entry_key), None)
            kb_status = {"synced": "synced", "failed": "failed"}.get((row or {}).get("status"), "unsynced")
        return self._receipt(principal, "snippet.sync:" + snippet_id, payload, if_match, key,
                             lambda: self.store.sync(company_id, snippet_id, expected, kb_status))

    def _receipt(self, principal, action: str, payload: dict, if_match: str | None, key: str | None, mutate):
        # 回执仍写在既有 DemoState.workflow_receipts，作用域与公司资料相同。
        # 片段记录仍不进入DemoState；独立存储外层锁和回滚覆盖整个回执事务。
        key = validate_key(key)
        scope_id = "library:" + principal.user.company_id
        request_fingerprint = fingerprint(action, payload, if_match)

        def apply(state):
            self.store.bind(state)
            now = self._clock()
            replay = lookup(state, scope_id, principal.user.id, key, request_fingerprint, now)
            if replay is not None:
                return replay
            result = mutate()
            remember(state, scope_id, principal.user.id, key, request_fingerprint, result, now)
            return result

        return self.store.transaction(lambda: self.repository.transaction(apply))


# HTTP 路由在 icg/api/library.py（唯一注册点）。


def _list_etag(items: list) -> str:
    return content_hash(json.dumps(items, ensure_ascii=False, sort_keys=True))
