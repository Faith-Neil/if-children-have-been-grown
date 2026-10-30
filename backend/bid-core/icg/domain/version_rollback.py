# 为什么有这个文件：编辑台版本回退（APP-M2-T175，PRD v1.8 §5.11.9；修改方式“版本回退”）。
# 它解决什么问题：把正文回退到某个历史版本时生成一个新版本，历史版本一个不删；回退与手改提交走同样的核对——
# 须持有本章编辑锁、有本节编辑权、分册未定稿、正文版本是最新、来源依据是当前的；系统生成章节不能回退，锁定段落不能被回退覆盖。
# 回来的段落沿用目标版本里的段落键与来源（paragraph_keys.assign 的 rollback_paragraphs）。

from __future__ import annotations

from typing import Any

from .domain import DemoState, DomainError, Principal, iso_time


class VersionRollbackService:
    def __init__(self, demo: Any) -> None:
        self.demo = demo

    def rollback(self, principal: Principal, project_id: str, chapter_id: str, payload: dict) -> dict:
        def operation(state: DemoState):
            demo = self.demo
            chapter = demo._chapter(state, principal, chapter_id)
            if chapter.project_id != project_id:
                raise DomainError(404, "NOT_FOUND", "未找到有权访问的章节。")
            demo._chapter_writer(state, principal, chapter)
            demo._lease(chapter, principal, payload["lease_token"])
            demo._revision(chapter, int(payload["base_revision"]))
            from .system_chapters import refuse_manual_edit
            refuse_manual_edit(state, chapter)
            target_revision = int(payload["target_revision"])
            from .paragraph_keys import ensure
            ensure(chapter)
            target = next((v for v in chapter.versions if int(v.get("revision") or 0) == target_revision), None)
            if target is None:
                raise DomainError(404, "NOT_FOUND", f"没有 v{target_revision} 这个版本。")
            content = target.get("content") or ""
            if target_revision == chapter.revision or content == chapter.content:
                raise DomainError(409, "ROLLBACK_NOOP", "目标版本与当前正文相同，不需要回退。")
            from .paragraph_locks import refuse_locked_change
            refuse_locked_change(state, chapter, content)
            from .variable_nodes import refuse_new_invalid
            refuse_new_invalid(state, chapter, content)
            demo._writing_input(state, chapter, payload.get("input_fingerprint"))
            draft = chapter.drafts.get(principal.user.id)
            if draft is not None and draft.content != chapter.content:
                raise DomainError(409, "DRAFT_PENDING", "你有未提交的编辑草稿；请先提交或放弃草稿，再回退版本。")
            chapter.drafts.pop(principal.user.id, None)
            previous_revision = chapter.revision
            chapter.content = content
            chapter.revision += 1
            state.projects[project_id].revision += 1
            chapter.versions.append({"revision": chapter.revision, "content": content, "actor_id": principal.user.id,
                                     "created_at": iso_time(demo._now()), "version_origin": "rollback",
                                     "edit_mode": "rollback", "rollback_from": target_revision,
                                     "note": f"回退到 v{target_revision}",
                                     "rollback_paragraphs": [{"key": p["key"], "hash": p["hash"], "source": p.get("source", "manual")}
                                                             for p in target.get("paragraphs") or []]})
            stale = [uid for uid, item in chapter.drafts.items() if item.base_revision < chapter.revision]
            if stale:
                from .notifications import notify
                notify(state, stale, "draft_expired", f"「{chapter.title}」已回退到 v{target_revision}",
                       f"{principal.user.name} 把正文回退到 v{target_revision}（新版本 v{chapter.revision}）；你的草稿基于旧版本，不会覆盖新正文。",
                       now=iso_time(demo._now()), project_id=project_id, target_id=chapter.id)
            demo._audit(state, principal, chapter, "version.rollback",
                        {"from_revision": previous_revision, "target_revision": target_revision})
            return {"revision": chapter.revision, "content": content, "rollback_from": target_revision}
        return self.demo.repository.transaction(operation)
