# 为什么有这个文件：人工处理队列的单段编辑（APP-M2-T134，PRD v1.8 §5.7.7）。
# 它解决什么问题：
# 1. 负责人在队列里直接改写问题所在的那一段，不必跳到编辑台；只改这一段，其余段落逐字不变；
# 2. 沿用编辑台的保护：系统章节只读、分册定稿只读、他人正在编辑时拒绝、锁定段落不能动、基于旧正文的问题不能改；
# 3. 修改生成新章节版本并留痕，同时把该问题标为“人工已处理（已修改正文）”；改动不代替重新检查，循环记录仍显示需复查。

from __future__ import annotations

from .chapter_loop import queue_store, refresh_chapter_status
from .domain import DemoState, DomainError, Principal, iso_time

MAX_PARAGRAPH_CHARS = 5000


def queue_edit_problem(chapter, issue: dict, loop: dict | None) -> str | None:
    """问题是否还能在队列里改：返回不能的原因，能则返回 None。"""
    lines = (chapter.content or "").split("\n")
    index = issue.get("paragraph_index")
    if not isinstance(index, int) or index < 0 or index >= len(lines):
        return "问题所在段落已不存在，请重新检查本节。"
    checked = (loop or {}).get("checked_revision")
    fresh = checked in (None, chapter.revision) or (loop or {}).get("queue_edit_revision") == chapter.revision
    if not fresh:
        return "本节正文在这次检查后已变化，请先重新检查本节再编辑。"
    quote = str(issue.get("quote") or "").strip()[:20]
    if quote and quote not in lines[index]:
        return "问题所在段落与检查时不一致，请重新检查本节。"
    return None


class QueueParagraphEditMixin:
    def edit_human_issue_paragraph(self, principal: Principal, project_id: str, issue_id: str, payload: dict,
                                   expected: str | None, key: str | None) -> dict:
        new_text = str(payload.get("new_text") or "").strip()
        note = str(payload.get("note") or "").strip()
        if not new_text:
            raise DomainError(422, "VALIDATION_ERROR", "改写后的段落不能为空。", {"fields": {"new_text": "required"}})
        if "\n" in new_text or "\r" in new_text:
            raise DomainError(422, "VALIDATION_ERROR", "单段编辑只能改写一个段落，不能包含换行。", {"fields": {"new_text": "multiline"}})
        if len(new_text) > MAX_PARAGRAPH_CHARS:
            raise DomainError(422, "VALIDATION_ERROR", f"单段不能超过 {MAX_PARAGRAPH_CHARS} 字。", {"fields": {"new_text": "too_long"}})

        def operation(state: DemoState, project, workflow):
            _, issue, chapter = self._issue_for_write(state, project_id, issue_id)
            allowed = self._issue_permissions(state, principal, project_id, chapter, issue, workflow)
            if not allowed["resolve"]:
                if issue.get("human_reason") in ("EXTRA_COMMITMENT", "DISCLOSURE"):
                    raise DomainError(403, "PROJECT_LEAD_REQUIRED", "额外承诺和披露类问题只能由项目负责人处理。")
                raise DomainError(403, "CHAPTER_EDITOR_REQUIRED", "只有本节负责人或项目负责人可以修改本节。")
            from .system_chapters import refuse_manual_edit
            refuse_manual_edit(state, chapter)
            if chapter.revision != payload["chapter_revision"]:
                raise DomainError(409, "REVISION_CONFLICT", "本节正文已有新版本，请刷新队列后再编辑。",
                                  {"current_revision": chapter.revision})
            now_ts = self.demo._now()
            if chapter.lock and chapter.lock.expires_at > now_ts:
                raise DomainError(409, "CHAPTER_IN_USE", "本节正在被编辑，请先保存并释放编辑权后再修改。")
            store = queue_store(workflow)
            loop = store["loops"].get(chapter.id)
            problem = queue_edit_problem(chapter, issue, loop)
            if problem:
                raise DomainError(409, "HUMAN_ISSUE_STALE", problem)
            lines = chapter.content.split("\n")
            index = issue["paragraph_index"]
            before = lines[index]
            if before.strip() == new_text:
                raise DomainError(422, "VALIDATION_ERROR", "改写后的内容与原段落相同。", {"fields": {"new_text": "unchanged"}})
            lines[index] = new_text
            new_content = "\n".join(lines)
            from .paragraph_locks import refuse_locked_change
            refuse_locked_change(state, chapter, new_content)
            now = iso_time(now_ts)
            chapter.content = new_content
            chapter.revision += 1
            chapter.versions.append({"revision": chapter.revision, "content": new_content, "actor_id": principal.user.id,
                                     "actor_name": principal.user.name, "created_at": now, "version_origin": "manual",
                                     "edit_mode": "queue_paragraph", "paragraph_index": index, "issue_id": issue_id,
                                     "note": "人工处理队列单段修改"})
            chapter.incremental_check_status = "pending"
            chapter.drafts.pop(principal.user.id, None)
            if loop is not None:
                loop["queue_edit_revision"] = chapter.revision
            issue["status"] = "human_handled"
            issue["resolution"] = {"method": "edited", "method_label": "已修改正文", "note": note,
                                   "actor_id": principal.user.id, "at": now, "chapter_revision": chapter.revision}
            issue["updated_at"] = now
            issue.setdefault("history", []).append({"at": now, "action": "paragraph_edited", "method": "edited",
                                                    "actor_id": principal.user.id, "note": note,
                                                    "chapter_revision": chapter.revision})
            status = refresh_chapter_status(workflow, chapter.id)
            return {"issue_ids": [issue_id], "chapter_id": chapter.id, "chapter_status": status,
                    "chapter_revision": chapter.revision, "paragraph_index": index, "paragraph_text": new_text}

        return self._write(principal, project_id, f"human.edit:{issue_id}", payload, expected, key, operation,
                           {"issue_id": issue_id, "chapter_revision": payload["chapter_revision"]})
