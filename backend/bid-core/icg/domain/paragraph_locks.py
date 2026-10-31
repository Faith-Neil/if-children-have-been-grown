# 为什么有这个文件：编辑台的段落锁定（APP-M2-T163，PRD v1.8 §5.11.8“锁定段落”、§5.7 验收③）。
# 它解决什么问题：
# 1. 有本节编辑权的人可以把一个段落锁住；锁住后手改提交、对话助手改写/插入、AI 建议采纳、答案卡、锁释放时的草稿自动提交都不能改动或删除它，后台拒绝；
#    章节循环里落在锁定段落上的问题不自动修，转人工（原因“段落已被人工锁定”）。
# 2. 解锁只能由锁定人或项目负责人操作。
# 3. 锁按段落文字的哈希识别：段落挪了位置仍算同一段；段落键跟着当前正文重新对上。
# 锁记录放在项目工作流 workflow["paragraph_locks"][章节]，随工作流持久化。

from __future__ import annotations

from collections import Counter
from typing import Any

from .domain import DemoState, DomainError, Principal, iso_time
from .paragraph_keys import current as current_paragraphs, split


def _store(workflow: dict, chapter_id: str) -> dict:
    return workflow.setdefault("paragraph_locks", {}).setdefault(chapter_id, {})


def locks(workflow: dict, chapter_id: str) -> list[dict]:
    return list(((workflow.get("paragraph_locks") or {}).get(chapter_id) or {}).values())


def public_locks(state: DemoState, chapter: Any, workflow: dict, user_id: str) -> list[dict]:
    """当前正文中的锁：带当前段落键、行号、锁定人，以及本人能否解锁。"""
    from .project_access import lead
    by_hash: dict[str, list[dict]] = {}
    for paragraph in current_paragraphs(chapter):
        by_hash.setdefault(paragraph["hash"], []).append(paragraph)
    out = []
    for record in sorted(locks(workflow, chapter.id), key=lambda r: r["locked_at"]):
        matches = by_hash.get(record["hash"]) or []
        here = matches.pop(0) if matches else None
        out.append({**record, "paragraph_key": here["key"] if here else record["paragraph_key"],
                    "line_start": here["line_start"] if here else None,
                    "line_end": here["line_end"] if here else None,
                    "present": here is not None,
                    "can_unlock": record["locked_by"] == user_id or lead(state, chapter.project_id, user_id)})
    return out


def locked_lines(chapter: Any, workflow: dict) -> set[int]:
    """锁定段落在当前正文中占的行号（0 起），供章节循环跳过自动修正。"""
    wanted = Counter(r["hash"] for r in locks(workflow, chapter.id))
    lines: set[int] = set()
    for paragraph in current_paragraphs(chapter):
        if wanted.get(paragraph["hash"]):
            wanted[paragraph["hash"]] -= 1
            lines.update(range(paragraph["line_start"], paragraph["line_end"] + 1))
    return lines


def mark_locked(paragraphs: list[dict], workflow: dict, chapter_id: str) -> list[dict]:
    """章节接口里的段落表加上锁定标记与锁定人。"""
    pending: dict[str, list[dict]] = {}
    for record in sorted(locks(workflow, chapter_id), key=lambda r: r["locked_at"]):
        pending.setdefault(record["hash"], []).append(record)
    out = []
    for paragraph in paragraphs:
        records = pending.get(paragraph["hash"]) or []
        record = records.pop(0) if records else None
        out.append({**paragraph, "locked": record is not None,
                    "locked_by_name": record["locked_by_name"] if record else None})
    return out


def violations(workflow: dict, chapter_id: str, new_content: str) -> list[dict]:
    """新正文里找不到原样的锁定段落（被改动或删除）。"""
    records = locks(workflow, chapter_id)
    if not records:
        return []
    available = Counter(block["hash"] for block in split(new_content))
    missing = []
    for record in records:
        if available.get(record["hash"]):
            available[record["hash"]] -= 1
        else:
            missing.append(record)
    return missing


def refuse_locked_change(state: DemoState, chapter: Any, new_content: str) -> None:
    """写入前核对：锁定段落必须原样保留（可以挪位置），否则 409 PARAGRAPH_LOCKED。"""
    workflow = state.workflows.get(chapter.project_id) or {}
    missing = violations(workflow, chapter.id, new_content)
    if missing:
        names = "、".join(sorted({r["locked_by_name"] for r in missing}))
        raise DomainError(409, "PARAGRAPH_LOCKED",
                          f"本次修改改动或删除了 {len(missing)} 个已锁定段落（锁定人：{names}）；请保留锁定段落原文，或先由锁定人、项目负责人解除锁定。",
                          {"paragraphs": [{"paragraph_key": r["paragraph_key"], "excerpt": r["excerpt"],
                                           "locked_by_name": r["locked_by_name"]} for r in missing]})


def refuse_locked_selection(state: DemoState, chapter: Any, start: int, end: int) -> None:
    """对话助手选区落在锁定段落上时不调用模型（§5.11.8 异常处理前两行）。"""
    workflow = state.workflows.get(chapter.project_id) or {}
    lines = locked_lines(chapter, workflow)
    if not lines:
        return
    content = chapter.content or ""
    first = content.count("\n", 0, start)
    last = content.count("\n", 0, max(start, end - 1))
    selected = set(range(first, last + 1))
    hit = selected & lines
    if not hit:
        return
    if hit == selected:
        raise DomainError(409, "PARAGRAPH_LOCKED", "段落已锁定，不能用对话助手改写；请先由锁定人或项目负责人解除锁定。",
                          {"partial": False})
    raise DomainError(409, "PARAGRAPH_LOCKED", "选区包含已锁定的段落，请只选可编辑部分后再问。", {"partial": True})


class ParagraphLockService:
    def __init__(self, demo: Any) -> None:
        self.demo = demo

    def _load(self, state: DemoState, principal: Principal, project_id: str, chapter_id: str, *, write: bool = False):
        chapter = self.demo._chapter(state, principal, chapter_id)
        if chapter.project_id != project_id:
            raise DomainError(404, "NOT_FOUND", "未找到有权访问的章节。")
        if not write:
            return chapter, state.workflows.get(project_id) or {}
        # 项目还没有工作流时按完整的空工作流建，不能只建一个空字典（其他模块读 candidates 等键）
        from .workflow_orchestrator import _blank_workflow
        return chapter, state.workflows.setdefault(project_id, _blank_workflow())

    def list(self, principal: Principal, project_id: str, chapter_id: str) -> dict:
        state = self.demo.repository.read()
        chapter, workflow = self._load(state, principal, project_id, chapter_id)
        return {"chapter_id": chapter_id, "revision": chapter.revision,
                "locks": public_locks(state, chapter, workflow, principal.user.id)}

    def lock(self, principal: Principal, project_id: str, chapter_id: str, payload: dict) -> dict:
        def operation(state: DemoState):
            chapter, workflow = self._load(state, principal, project_id, chapter_id, write=True)
            self.demo._chapter_writer(state, principal, chapter)
            from .system_chapters import refuse_manual_edit
            refuse_manual_edit(state, chapter)
            if chapter.revision != int(payload["base_revision"]):
                raise DomainError(409, "REVISION_CONFLICT", f"正文已更新到 r{chapter.revision}，请刷新后再锁定。")
            paragraph = next((p for p in current_paragraphs(chapter) if p["key"] == payload["paragraph_key"]), None)
            if paragraph is None:
                raise DomainError(404, "NOT_FOUND", "当前正文中没有这个段落。")
            store = _store(workflow, chapter_id)
            if paragraph["key"] in store or any(r["hash"] == paragraph["hash"] and r["paragraph_key"] == paragraph["key"] for r in store.values()):
                raise DomainError(409, "PARAGRAPH_ALREADY_LOCKED", "这个段落已经锁定。")
            lines = (chapter.content or "").splitlines()
            text = "\n".join(lines[paragraph["line_start"]:paragraph["line_end"] + 1]).strip()
            record = {"paragraph_key": paragraph["key"], "hash": paragraph["hash"],
                      "excerpt": text[:60] + ("…" if len(text) > 60 else ""),
                      "reason": (payload.get("reason") or "").strip(),
                      "locked_by": principal.user.id, "locked_by_name": principal.user.name,
                      "locked_at": iso_time(self.demo._now()), "revision": chapter.revision}
            store[paragraph["key"]] = record
            self.demo._audit(state, principal, chapter, "paragraph.lock",
                             {"paragraph_key": paragraph["key"], "reason": record["reason"]})
            return {"chapter_id": chapter_id, "revision": chapter.revision,
                    "locks": public_locks(state, chapter, workflow, principal.user.id)}
        return self.demo.repository.transaction(operation)

    def unlock(self, principal: Principal, project_id: str, chapter_id: str, paragraph_key: str) -> dict:
        def operation(state: DemoState):
            chapter, workflow = self._load(state, principal, project_id, chapter_id, write=True)
            from .project_access import ensure_not_readonly, lead
            ensure_not_readonly(principal)
            store = _store(workflow, chapter_id)
            current = {item["paragraph_key"]: item for item in public_locks(state, chapter, workflow, principal.user.id)}
            target = current.get(paragraph_key)
            if target is None:
                raise DomainError(404, "NOT_FOUND", "没有找到这个锁定段落。")
            record_key = next(k for k, r in store.items() if r["locked_at"] == target["locked_at"] and r["hash"] == target["hash"])
            if not (store[record_key]["locked_by"] == principal.user.id or lead(state, project_id, principal.user.id)):
                raise DomainError(403, "FORBIDDEN", "只有锁定人或项目负责人可以解除锁定。")
            store.pop(record_key)
            self.demo._audit(state, principal, chapter, "paragraph.unlock", {"paragraph_key": paragraph_key})
            return {"chapter_id": chapter_id, "revision": chapter.revision,
                    "locks": public_locks(state, chapter, workflow, principal.user.id)}
        return self.demo.repository.transaction(operation)
