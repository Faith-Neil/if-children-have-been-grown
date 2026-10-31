# 为什么有这个文件：项目在“技术+商务两册（合标）”与“只写技术标（不合标）”之间切换（用户 2026-10-29 要求）。
# 它解决什么问题：切换不能丢正文——商务分册已有正文或已定稿时拒绝；切回两册时补建商务分册并恢复被标为不在范围的条款。

from __future__ import annotations

from icg.domain.domain import Chapter, DomainError, Principal, iso_time, new_id


def switch_volume_mode(state, principal: Principal, project, workflow: dict, mode: str | None, *, now: float) -> None:
    """两册 ↔ 只写技术标。不删除任何已有正文：商务分册有正文或已定稿时拒绝切换。"""
    from icg.domain.project_access import project_volume_mode
    current = project_volume_mode(state, project.id)
    if mode is None or mode == current:
        return
    team = state.project_teams[project.id]
    business = [c for c in state.chapters.values() if c.project_id == project.id and c.volume == "business"]
    if mode == "technical_only":
        if any((c.content or "").strip() for c in business) or workflow.get("volumes", {}).get("business", {}).get("is_finalized"):
            raise DomainError(409, "CHAPTER_HAS_CONTENT", "商务分册已有正文或已定稿，不能改为只写技术标；请先清空商务章节。")
        for chapter in business:
            del state.chapters[chapter.id]
        workflow["chapter_order"] = [cid for cid in workflow.get("chapter_order", []) if cid in state.chapters]
        team["owners"].pop("business", None)
        for item in team["members"].values():
            item["volumes"] = [v for v in item.get("volumes", []) if v != "business"] or ["technical"]
        for row in workflow.get("requirements", {}).values():
            if row.get("volume") == "business" and row.get("status") != "rejected":
                row.update(status="rejected", out_of_scope=True, chapter_id=None,
                           reason="本项目只写技术标：商务/资格条款不在本项目编写范围，由商务标负责人另行响应。")
    else:
        lead_id = next((uid for uid, m in team["members"].items() if m.get("project_role") == "lead"), principal.user.id)
        team["owners"].setdefault("business", lead_id)
        for item in team["members"].values():
            if item.get("project_role") == "lead" and "business" not in item.get("volumes", []):
                item["volumes"] = [*item.get("volumes", []), "business"]
        if not business:
            chapter = Chapter(new_id("chapter"), project.id, "商务响应", "business", "")
            chapter.versions.append({"revision": 1, "content": "", "actor_id": principal.user.id,
                                     "created_at": iso_time(now)})
            state.chapters[chapter.id] = chapter
            if workflow.get("chapter_order"):
                workflow["chapter_order"].append(chapter.id)
        for row in workflow.get("requirements", {}).values():
            if row.get("out_of_scope"):
                row.update(status="pending", out_of_scope=False, reason="")
    team["volume_mode"] = mode
    workflow["parse_confirmed"] = False
    workflow["plan_confirmed"] = False

