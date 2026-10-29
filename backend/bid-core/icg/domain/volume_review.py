# 为什么有这个文件：实现 PRD v1.8 §2.3、§4.2、§5.8.5 的“定稿前交叉复核确认”和分册定稿快照。
# 它解决什么问题：
# 1. 分册负责人或项目负责人指定一名不是本分册编写人的项目成员做交叉复核；复核人只确认或退回，留痕不可删除；
# 2. 复核通过时绑定本分册各章节的版本快照；正文之后有任何改动，复核即失效，定稿被拦下；
# 3. 定稿还要求本分册没有待人工处理的问题；定稿记录保存章节快照；
# 4. 解锁分册时复核作废、解锁轮次加一，已有检查和导出随之过期，须重新检查、复核后再定稿。

from __future__ import annotations

import hashlib
from .chapter_loop import OPEN_STATUSES
from .domain import DemoState, DomainError, Principal, iso_time
from .project_access import VOLUMES, lead, project_volumes, member, normalize_role, volume_owner, writable

REVIEW_DECISIONS = {"approved": "复核通过", "returned": "退回修改"}
VOLUME_LABELS = {"technical": "技术分册", "business": "商务分册"}


def volume_chapters(state: DemoState, project_id: str, volume: str) -> list:
    return sorted((c for c in state.chapters.values() if c.project_id == project_id and c.volume == volume),
                  key=lambda c: c.id)


def volume_snapshot(state: DemoState, project_id: str, volume: str) -> list[dict]:
    return [{"chapter_id": c.id, "revision": int(c.revision),
             "content_hash": hashlib.sha256((c.content or "").encode("utf-8")).hexdigest()}
            for c in volume_chapters(state, project_id, volume)]


def volume_editors(state: DemoState, project_id: str, volume: str) -> set[str]:
    """本分册的编写人：分册负责人、被分配章节的人和实际提交过正文版本的人。"""
    team = state.project_teams.get(project_id, {})
    editors = {team.get("owners", {}).get(volume)} - {None, ""}
    for chapter in volume_chapters(state, project_id, volume):
        if chapter.assignee_id:
            editors.add(chapter.assignee_id)
        for version in chapter.versions:
            actor = version.get("actor_id")
            if actor and version.get("source") != "chapter_loop" and (version.get("content") or "").strip():
                editors.add(actor)
    return editors


def pending_human_issues(workflow: dict, state: DemoState, project_id: str, volume: str) -> list[dict]:
    ids = {c.id for c in volume_chapters(state, project_id, volume)}
    store = workflow.get("human_queue", {})
    return [i for i in store.get("issues", {}).values() if i["chapter_id"] in ids and i["status"] in OPEN_STATUSES]


def public_review(state: DemoState, project_id: str, volume: str, workflow: dict) -> dict:
    review = dict(workflow.get("volume_reviews", {}).get(volume) or {"status": "none"})
    if review.get("status") == "approved":
        review["stale"] = review.get("snapshot") != volume_snapshot(state, project_id, volume)
    else:
        review["stale"] = False
    reviewer = review.get("reviewer_id")
    review["reviewer_name"] = state.accounts[reviewer].name if reviewer in state.accounts else None
    review.pop("snapshot", None)
    review["history"] = list(review.get("history", []))[-10:]
    return review


def require_cross_review(state: DemoState, project_id: str, volume: str, workflow: dict) -> list[dict]:
    """定稿前置：本分册没有待人工问题，且交叉复核已通过、对应的仍是当前正文。返回章节快照。"""
    pending = pending_human_issues(workflow, state, project_id, volume)
    if pending:
        raise DomainError(409, "HUMAN_ISSUES_PENDING",
                          f"{VOLUME_LABELS.get(volume, volume)}还有 {len(pending)} 个待人工处理的问题，处理完才能定稿。",
                          {"pending": len(pending), "chapter_ids": sorted({i["chapter_id"] for i in pending})})
    review = workflow.get("volume_reviews", {}).get(volume) or {}
    snapshot = volume_snapshot(state, project_id, volume)
    if review.get("status") != "approved":
        raise DomainError(409, "CROSS_REVIEW_REQUIRED",
                          f"{VOLUME_LABELS.get(volume, volume)}须由非本册编写人完成交叉复核后才能定稿。",
                          {"status": review.get("status", "none")})
    if review.get("snapshot") != snapshot:
        raise DomainError(409, "CROSS_REVIEW_REQUIRED", "复核之后正文有改动，须重新交叉复核后再定稿。",
                          {"status": "stale"})
    return snapshot


def _can_manage(state: DemoState, principal: Principal, project_id: str, volume: str) -> bool:
    identity = principal.user.id
    return (normalize_role(principal.user.role) == "company_admin" and writable(state, project_id, identity)) \
        or lead(state, project_id, identity) or volume_owner(state, project_id, volume, identity)


class VolumeReviewMixin:
    """WorkflowService 的交叉复核能力。"""

    def assign_cross_reviewer(self, principal: Principal, project_id: str, volume: str, payload: dict,
                              expected: str | None, key: str | None) -> dict:
        if volume not in project_volumes(self.repository.read(), project_id):
            raise DomainError(404, "NOT_FOUND", f"未找到指定分册：{volume}")
        reviewer_id = str(payload.get("reviewer_id") or "").strip()

        def operation(state: DemoState, project, workflow):
            if not _can_manage(state, principal, project_id, volume):
                raise DomainError(403, "VOLUME_OWNER_REQUIRED", "只有项目负责人或本册负责人可以指定交叉复核人。")
            if workflow.get("volumes", {}).get(volume, {}).get("is_finalized"):
                raise DomainError(409, "VOLUME_FINALIZED", "分册已定稿，须先解锁再重新复核。")
            account = state.accounts.get(reviewer_id)
            if not account or not member(state, project_id, reviewer_id) or not writable(state, project_id, reviewer_id):
                raise DomainError(422, "VALIDATION_ERROR", "复核人须是本项目可编辑的成员。",
                                  {"fields": {"reviewer_id": "invalid"}})
            if reviewer_id in volume_editors(state, project_id, volume):
                raise DomainError(409, "CROSS_REVIEWER_IS_EDITOR", "复核人不能是本分册的编写人，请另选一名成员。")
            now = iso_time(self.demo._now())
            reviews = workflow.setdefault("volume_reviews", {})
            history = list((reviews.get(volume) or {}).get("history", []))
            history.append({"at": now, "action": "assigned", "actor_id": principal.user.id, "reviewer_id": reviewer_id})
            reviews[volume] = {"volume_id": volume, "status": "pending", "reviewer_id": reviewer_id,
                               "assigned_by": principal.user.id, "assigned_at": now,
                               "decided_at": None, "decision_note": "", "snapshot": None, "history": history}
            from .notifications import notify
            notify(state, [reviewer_id], "cross_review", f"请交叉复核{'技术' if volume == 'technical' else '商务'}分册",
                   f"{principal.user.name} 指定你复核「{project.name}」的{'技术' if volume == 'technical' else '商务'}分册，复核通过后才能定稿。",
                   now=now, project_id=project_id, target_id=volume)
            return {"volume_id": volume, "cross_review": public_review(state, project_id, volume, workflow)}

        return self._write(principal, project_id, f"volume.review.assign:{volume}", payload, expected, key,
                           operation, {"volume_id": volume, "reviewer_id": reviewer_id})

    def confirm_cross_review(self, principal: Principal, project_id: str, volume: str, payload: dict,
                             expected: str | None, key: str | None) -> dict:
        if volume not in project_volumes(self.repository.read(), project_id):
            raise DomainError(404, "NOT_FOUND", f"未找到指定分册：{volume}")
        decision = payload.get("decision")
        note = str(payload.get("note") or "").strip()
        if decision not in REVIEW_DECISIONS:
            raise DomainError(422, "VALIDATION_ERROR", "请选择复核结论。", {"fields": {"decision": "invalid"}})
        if decision == "returned" and not note:
            raise DomainError(422, "REASON_REQUIRED", "退回修改须写明原因。")

        def operation(state: DemoState, project, workflow):
            review = workflow.get("volume_reviews", {}).get(volume)
            if not review or review.get("status") != "pending":
                raise DomainError(409, "CROSS_REVIEW_REQUIRED", "当前没有等待确认的交叉复核，请先指定复核人。")
            if review.get("reviewer_id") != principal.user.id:
                raise DomainError(403, "CROSS_REVIEWER_REQUIRED", "只有被指定的复核人可以确认本次交叉复核。")
            if principal.user.id in volume_editors(state, project_id, volume):
                raise DomainError(409, "CROSS_REVIEWER_IS_EDITOR", "复核人已参与本分册编写，不能再做交叉复核。")
            now = iso_time(self.demo._now())
            review["status"] = decision
            review["decided_at"] = now
            review["decision_note"] = note
            review["snapshot"] = volume_snapshot(state, project_id, volume) if decision == "approved" else None
            review.setdefault("history", []).append({"at": now, "action": decision, "actor_id": principal.user.id,
                                                     "note": note})
            return {"volume_id": volume, "cross_review": public_review(state, project_id, volume, workflow)}

        return self._write(principal, project_id, f"volume.review.confirm:{volume}", payload, expected, key,
                           operation, {"volume_id": volume, "decision": decision})


def reset_review_on_unlock(workflow: dict, volume: str, actor_id: str, now_iso: str, reason: str) -> None:
    """解锁后复核作废，解锁轮次加一（写入输入指纹，让已有检查与导出过期）。"""
    epochs = workflow.setdefault("volume_epochs", {})
    epochs[volume] = int(epochs.get(volume, 0)) + 1
    review = workflow.setdefault("volume_reviews", {}).get(volume)
    if review:
        review.setdefault("history", []).append({"at": now_iso, "action": "voided_by_unlock", "actor_id": actor_id,
                                                 "note": reason})
        review.update({"status": "none", "snapshot": None, "decided_at": None, "decision_note": ""})
