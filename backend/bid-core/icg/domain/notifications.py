# 为什么有这个文件：站内提醒（PRD v1.8 §5.12.2 G-02；APP-M2-T029～T032）。
# 它解决什么问题：
# 1. 17 类提醒（字典 notification_type）统一存放：发给谁、类型、标题、摘要、所属项目、跳转目标、已读；按公司隔离，
#    集团管理员和平台管理员的提醒不属于任何公司（company_id 为空）；
# 2. 同一对象、同一类型的提醒在未读期间不重复发送，只更新时间、内容和次数（合并显示）；提醒不能删除；
# 3. 跳转时再次核对对象是否还在、本人是否仍有权限；不在或无权时提示“对象已不存在或你没有查看权限”，提醒仍标已读；
# 4. 只有站内提醒，没有邮件、短信等渠道。
# 由各业务事件调用 notify()；资料到期提醒在读取提醒时按公司每天扫描一次。

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from typing import Any, Iterable

from .domain import DemoState, DomainError, Principal, iso_time, new_id

STORE = "notifications"

# 类型 → (中文名, 跳转方式)。跳转方式：project_tab:<tab>、chapter、library、jobs、workbench、platform
TYPES: dict[str, tuple[str, str]] = {
    "library_expiring": ("资料到期提醒", "library"),
    "project_missing_material": ("在投项目缺资料", "project_tab:matrix"),
    "similarity_alert": ("相似度提醒", "project_tab:checks"),
    "volume_deadline": ("分册内部截止提醒", "project_tab:overview"),
    "cross_review": ("交叉复核提醒", "project_tab:export"),
    "export_expired": ("导出文件已过期", "project_tab:export"),
    "lock_taken_over": ("编辑锁被接管", "chapter"),
    "draft_expired": ("草稿已过期", "chapter"),
    "volume_unlock_request": ("分册解锁申请", "project_tab:export"),
    "chapter_pending_human": ("章节待人工处理", "project_tab:manual"),
    "related_bid_conflict": ("关联投标冲突", "workbench"),
    "local_task_queued": ("本地任务排队", "jobs"),
    "material_reminder": ("资料催办", "library"),
    "job_completed": ("后台任务完成", "jobs"),
    "job_failed": ("后台任务失败", "jobs"),
    "parse_pending": ("解析结果待处理", "project_tab:parse"),
    "service_error": ("服务异常", "platform"),
}
NOT_AVAILABLE = "对象已不存在或你没有查看权限"
EXPIRY_DAYS = 30


def _store(state: DemoState) -> dict:
    return state.service_stores.setdefault(STORE, {"items": {}, "sweeps": {}})


def _company_of(state: DemoState, user_id: str) -> str | None:
    from .project_access import normalize_role
    account = state.accounts.get(user_id)
    if account is None:
        return None
    if normalize_role(account.role) in ("group_admin", "platform_admin") or account.company_id in ("system", "group"):
        return None
    return account.company_id


def notify(state: DemoState, user_ids: Iterable[str | None], kind: str, title: str, body: str, *, now: str,
           project_id: str | None = None, target_id: str | None = None, dedupe_key: str | None = None,
           exclude: Iterable[str] = ()) -> list[str]:
    """给每个收件人发一条提醒；同人、同类型、同对象仍未读时只更新时间、内容和次数。返回提醒编号。"""
    if kind not in TYPES:
        raise ValueError(f"unknown notification type {kind}")
    items = _store(state)["items"]
    skip = set(exclude)
    key = dedupe_key or f"{project_id or ''}:{target_id or ''}"
    ids = []
    for user_id in dict.fromkeys(u for u in user_ids if u and u not in skip and u in state.accounts):
        existing = next((n for n in items.values() if n["user_id"] == user_id and n["type"] == kind
                         and n["dedupe_key"] == key and n["read_at"] is None), None)
        if existing:
            existing.update(title=title, body=body, updated_at=now, count=existing.get("count", 1) + 1)
            ids.append(existing["id"])
            continue
        record = {"id": new_id("notice"), "user_id": user_id, "company_id": _company_of(state, user_id), "type": kind,
                  "type_label": TYPES[kind][0], "title": title, "body": body[:500], "project_id": project_id,
                  "target_id": target_id, "dedupe_key": key, "read_at": None, "created_at": now, "updated_at": now,
                  "count": 1}
        items[record["id"]] = record
        ids.append(record["id"])
    return ids


def project_leads(state: DemoState, project_id: str) -> list[str]:
    members = state.project_teams.get(project_id, {}).get("members", {})
    return [uid for uid, m in members.items() if m.get("project_role") == "lead"]


def chapter_people(state: DemoState, chapter: Any) -> list[str]:
    owner = state.project_teams.get(chapter.project_id, {}).get("owners", {}).get(chapter.volume)
    return [uid for uid in (chapter.assignee_id, owner) if uid]


def notify_pending_human(state: DemoState, chapter: Any, now: str) -> None:
    """章节循环后仍有待人工处理的问题：提醒本节编写人和本册负责人。"""
    from .chapter_loop import OPEN_STATUSES
    store = (state.workflows.get(chapter.project_id) or {}).get("human_queue") or {}
    pending = [i for i in (store.get("issues") or {}).values()
               if i.get("chapter_id") == chapter.id and i.get("status") in OPEN_STATUSES]
    if pending:
        blockers = sum(1 for i in pending if i.get("level") == "blocker")
        notify(state, chapter_people(state, chapter), "chapter_pending_human", f"「{chapter.title}」有 {len(pending)} 项待人工处理",
               f"其中阻断 {blockers} 项；请到人工处理队列逐项处理。", now=now, project_id=chapter.project_id,
               target_id=chapter.id)


def sweep_key(state: DemoState, company_id: str, now_ts: float) -> str:
    """扫描标记：日期变了或本公司资料有增改（数量、版本、有效期）时才重新扫描。"""
    items = [(i.get("id"), i.get("revision"), i.get("valid_until") or i.get("valid_to"), i.get("status"))
             for i in state.library.values() if i.get("company_id") == company_id]
    digest = hashlib.sha256(json.dumps(sorted(map(str, items))).encode("utf-8")).hexdigest()[:16]
    return f"{datetime.fromtimestamp(now_ts).date().isoformat()}:{digest}"


def sweep_library_expiry(state: DemoState, company_id: str, now_ts: float) -> None:
    """资料到期提醒：本公司已确认资料 30 天内到期的，提醒公司管理员、资料管理员和录入人（同一资料同一到期日只提醒一次）。"""
    from .project_access import normalize_role
    store = _store(state)
    today = datetime.fromtimestamp(now_ts).date()
    key = sweep_key(state, company_id, now_ts)
    if store["sweeps"].get(company_id) == key:
        return
    store["sweeps"][company_id] = key
    admins = [a.id for a in state.accounts.values() if a.company_id == company_id
              and normalize_role(a.role) in ("company_admin", "data_admin")]
    now = iso_time(now_ts)
    for item in state.library.values():
        if item.get("company_id") != company_id or item.get("status") != "confirmed" or item.get("is_long_term"):
            continue
        raw = item.get("valid_until") or item.get("valid_to")
        try:
            until = date.fromisoformat(str(raw)[:10]) if raw else None
        except ValueError:
            until = None
        if until is None or not (today <= until <= today + timedelta(days=EXPIRY_DAYS)):
            continue
        days = (until - today).days
        key = f"library:{item['id']}:{until.isoformat()}"
        already = {n["user_id"] for n in store["items"].values() if n["type"] == "library_expiring" and n["dedupe_key"] == key}
        notify(state, [u for u in admins + [item.get("created_by")] if u not in already], "library_expiring", f"资料将于 {until.isoformat()} 到期",
               f"「{item.get('name', '资料')}」还有 {days} 天到期，到期后不能作为投标证据，请及时更新。",
               now=now, target_id=item["id"], dedupe_key=key)


# ---------------------------------------------------------------- 读取与操作

def _visible(state: DemoState, principal: Principal, record: dict) -> bool:
    return record["user_id"] == principal.user.id and record["company_id"] == _company_of(state, principal.user.id)


def public(record: dict) -> dict:
    return {k: record[k] for k in ("id", "type", "type_label", "title", "body", "project_id", "target_id", "read_at",
                                   "created_at", "updated_at", "count")} | {"read": record["read_at"] is not None}


class NotificationService:
    def __init__(self, demo: Any) -> None:
        self.demo = demo

    def _sweep(self, principal: Principal) -> None:
        state = self.demo.repository.read()
        company = _company_of(state, principal.user.id)
        if company is None:
            return
        store = state.service_stores.get(STORE) or {}
        if (store.get("sweeps") or {}).get(company) == sweep_key(state, company, self.demo._now()):
            return
        self.demo.repository.transaction(lambda state: sweep_library_expiry(state, company, self.demo._now()))

    def list(self, principal: Principal, *, status: str = "all", kind: str | None = None, project_id: str | None = None,
             since: str | None = None, until: str | None = None, limit: int = 50, offset: int = 0) -> dict:
        self._sweep(principal)
        state = self.demo.repository.read()
        mine = [r for r in (state.service_stores.get(STORE) or {}).get("items", {}).values() if _visible(state, principal, r)]
        unread = sum(1 for r in mine if r["read_at"] is None)
        rows = [r for r in mine
                if (status == "all" or (status == "unread") == (r["read_at"] is None))
                and (kind is None or r["type"] == kind) and (project_id is None or r["project_id"] == project_id)
                and (since is None or r["updated_at"] >= since) and (until is None or r["updated_at"] <= until)]
        rows.sort(key=lambda r: r["updated_at"], reverse=True)
        return {"items": [public(r) for r in rows[offset:offset + limit]], "total": len(rows), "unread": unread,
                "types": [{"value": k, "label": v[0]} for k, v in TYPES.items()]}

    def unread_count(self, principal: Principal) -> dict:
        self._sweep(principal)
        state = self.demo.repository.read()
        items = (state.service_stores.get(STORE) or {}).get("items", {}).values()
        return {"unread": sum(1 for r in items if _visible(state, principal, r) and r["read_at"] is None)}

    def mark(self, principal: Principal, notice_id: str, read: bool) -> dict:
        def operation(state: DemoState):
            record = _store(state)["items"].get(notice_id)
            if record is None or not _visible(state, principal, record):
                raise DomainError(404, "NOT_FOUND", "未找到发给你的这条提醒。")
            record["read_at"] = (record["read_at"] or iso_time(self.demo._now())) if read else None
            return public(record)
        return self.demo.repository.transaction(operation)

    def mark_all(self, principal: Principal) -> dict:
        def operation(state: DemoState):
            now = iso_time(self.demo._now())
            changed = 0
            for record in _store(state)["items"].values():
                if _visible(state, principal, record) and record["read_at"] is None:
                    record["read_at"] = now
                    changed += 1
            return {"updated": changed}
        return self.demo.repository.transaction(operation)

    def open(self, principal: Principal, notice_id: str) -> dict:
        """点击提醒：标为已读，并重新核对对象与权限后给出跳转地址。"""
        record = self.mark(principal, notice_id, True)
        state = self.demo.repository.read()
        mode = TYPES[record["type"]][1]
        path = self._resolve(state, principal, mode, record)
        return {"notification": record, "ok": path is not None, "path": path,
                "message": None if path else NOT_AVAILABLE}

    def _resolve(self, state: DemoState, principal: Principal, mode: str, record: dict) -> str | None:
        pid = record.get("project_id")
        try:
            if mode.startswith("project_tab:") or mode == "chapter":
                if not pid:
                    return None
                self.demo._project(state, principal, pid)
                if mode == "chapter":
                    chapter = state.chapters.get(record.get("target_id") or "")
                    if chapter is None or chapter.project_id != pid:
                        return None
                    return f"/projects/{pid}/editor/{chapter.id}"
                return f"/projects/{pid}/{mode.split(':', 1)[1]}"
        except DomainError:
            return None
        if mode == "library":
            item = state.library.get(record.get("target_id") or "")
            if record.get("target_id") and (item is None or item.get("company_id") != principal.user.company_id):
                return None
            return "/library"
        return {"jobs": "/jobs", "workbench": "/workbench", "platform": "/platform"}.get(mode)
