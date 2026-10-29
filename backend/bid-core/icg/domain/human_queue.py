# 为什么有这个文件：实现 PRD v1.8 §5.7.6～5.7.7 章节循环进度与人工处理队列的读取、处理、驳回和重新检查。
# 它解决什么问题：
# 1. 把各章节自动修不了的问题按章节集中展示，带停止原因、轮次、转人工原因和修改建议；
# 2. 处理与驳回按 PRD 权限执行：阻断级不能驳回；规则警告只能由项目负责人驳回；额外承诺/披露类只能由项目负责人处理；
# 3. 重新检查以当前正式版本为起点开始新一次循环，只做不编造的确定性修正；修正产生新章节版本并留痕；
# 4. 本节全部待人工问题处理完后章节自动变为“人工已处理”，处理记录不可删除并写审计。

from __future__ import annotations

from typing import Any

from .chapter_loop import (
    CLOSED_STATUSES, HUMAN_REASONS, OPEN_STATUSES, REJECT_REASONS, RESOLVE_METHODS, STOP_REASONS,
    LoopContext, queue_store, record_loop, refresh_chapter_status, run_chapter_loop,
)
from .domain import DemoState, DomainError, Principal, iso_time
from .generation_context import previous_chapter_relay, project_facts
from .project_access import chapter_edit, lead, member, normalize_role

LEAD_ONLY_REASONS = ("EXTRA_COMMITMENT", "DISCLOSURE")
LOOP_STATUS_LABELS = {
    "completed": "已完成",
    "pending_human": "待人工处理",
    "human_handled": "人工已处理",
}


def _volume_finalized(workflow: dict, volume: str) -> bool:
    return bool(workflow.get("volumes", {}).get(volume, {}).get("is_finalized"))


class HumanQueueMixin:
    """WorkflowService 的人工处理队列能力。"""

    def _queue_viewable(self, state: DemoState, principal: Principal, project_id: str) -> None:
        self.demo._project(state, principal, project_id)
        if lead(state, project_id, principal.user.id) or member(state, project_id, principal.user.id):
            return
        if normalize_role(principal.user.role) == "company_admin":
            return
        raise DomainError(403, "FORBIDDEN", "只有本项目成员可以查看人工处理队列。")

    def _chapter_number(self, state: DemoState, project_id: str, workflow: dict, chapter_id: str) -> int:
        ordered = [c.id for c in self._ordered_chapters(state, project_id, workflow)]
        return ordered.index(chapter_id) + 1 if chapter_id in ordered else 1

    def _issue_permissions(self, state: DemoState, principal: Principal, project_id: str, chapter, issue: dict,
                           workflow: dict) -> dict:
        identity = principal.user.id
        is_lead = lead(state, project_id, identity)
        can_edit = chapter_edit(state, chapter, identity)
        locked = _volume_finalized(workflow, chapter.volume)
        open_ = issue["status"] in OPEN_STATUSES
        lead_only = issue.get("human_reason") in LEAD_ONLY_REASONS
        resolve = open_ and not locked and (is_lead or (can_edit and not lead_only))
        if issue.get("level") == "blocker":
            reject = False
        elif issue.get("source") == "model_review":
            reject = open_ and not locked and (is_lead or can_edit)
        else:
            reject = open_ and not locked and is_lead
        return {"resolve": resolve, "reject": reject}

    def _public_issue(self, state, principal, project_id, chapter, issue, workflow) -> dict:
        public = {k: v for k, v in issue.items() if k != "fingerprint"}
        public["human_reason_label"] = HUMAN_REASONS.get(issue.get("human_reason") or "", "")
        public["permissions"] = self._issue_permissions(state, principal, project_id, chapter, issue, workflow)
        return public

    def _public_loop(self, state, chapter, loop: dict | None) -> dict | None:
        if not loop:
            return None
        return {
            **{k: v for k, v in loop.items() if k != "history"},
            "status_label": LOOP_STATUS_LABELS.get(loop.get("status"), loop.get("status")),
            "stale": loop.get("kind") == "recheck" and loop.get("checked_revision") != chapter.revision,
            "loop_count": len(loop.get("history", [])) + 1,
        }

    def list_human_queue(self, principal: Principal, project_id: str, volume: str | None = None) -> dict:
        state = self.repository.read()
        self._queue_viewable(state, principal, project_id)
        project = state.projects[project_id]
        workflow = self._workflow(state, project_id)
        store = workflow.get("human_queue", {"loops": {}, "issues": {}})
        groups = []
        by_reason: dict[str, int] = {}
        pending_total = 0
        for chapter in self._ordered_chapters(state, project_id, workflow):
            if volume and volume != "all" and chapter.volume != volume:
                continue
            loop = store.get("loops", {}).get(chapter.id)
            issues = [i for i in store.get("issues", {}).values()
                      if i["chapter_id"] == chapter.id and i["status"] in OPEN_STATUSES]
            if not issues:
                continue
            issues.sort(key=lambda i: (0 if i.get("level") == "blocker" else 1, i.get("number", "")))
            for issue in issues:
                reason = issue.get("human_reason") or "LOOP_STOPPED"
                by_reason[reason] = by_reason.get(reason, 0) + 1
            pending_total += len(issues)
            groups.append({
                "chapter_id": chapter.id, "title": chapter.title, "volume": chapter.volume,
                "number": self._chapter_number(state, project_id, workflow, chapter.id),
                "assignee_id": chapter.assignee_id,
                "assignee_name": state.accounts[chapter.assignee_id].name if chapter.assignee_id in state.accounts else None,
                "volume_finalized": _volume_finalized(workflow, chapter.volume),
                "can_recheck": chapter_edit(state, chapter, principal.user.id) and not _volume_finalized(workflow, chapter.volume),
                "loop": self._public_loop(state, chapter, loop),
                "issues": [self._public_issue(state, principal, project_id, chapter, i, workflow) for i in issues],
            })
        return {
            "revision": project.revision, "project_id": project_id, "volume": volume or "all",
            "deadline": project.deadline,
            "summary": {
                "pending": pending_total, "chapters": len(groups),
                "by_reason": [{"reason": key, "label": HUMAN_REASONS.get(key, key), "count": count}
                              for key, count in sorted(by_reason.items(), key=lambda item: -item[1])],
            },
            "chapters": groups,
        }

    def list_chapter_loops(self, principal: Principal, project_id: str, volume: str | None = None) -> dict:
        """全部章节的循环进度（含没有待处理问题的章节）：哪些章已生成并检查、停在哪、还剩什么。"""
        state = self.repository.read()
        self._queue_viewable(state, principal, project_id)
        project = state.projects[project_id]
        workflow = self._workflow(state, project_id)
        store = workflow.get("human_queue", {"loops": {}, "issues": {}})
        rows = []
        totals = {"chapters": 0, "not_started": 0, "completed": 0, "pending_human": 0, "human_handled": 0, "stale": 0}
        for chapter in self._ordered_chapters(state, project_id, workflow):
            if volume and volume != "all" and chapter.volume != volume:
                continue
            loop = self._public_loop(state, chapter, store.get("loops", {}).get(chapter.id))
            issues = [i for i in store.get("issues", {}).values() if i["chapter_id"] == chapter.id]
            pending = len([i for i in issues if i["status"] in OPEN_STATUSES])
            totals["chapters"] += 1
            totals[loop["status"] if loop else "not_started"] = totals.get(loop["status"] if loop else "not_started", 0) + 1
            if loop and loop.get("stale"):
                totals["stale"] += 1
            rows.append({
                "chapter_id": chapter.id, "title": chapter.title, "volume": chapter.volume,
                "number": self._chapter_number(state, project_id, workflow, chapter.id),
                "chapter_revision": chapter.revision, "has_content": bool((chapter.content or "").strip()),
                "assignee_name": state.accounts[chapter.assignee_id].name if chapter.assignee_id in state.accounts else None,
                "volume_finalized": _volume_finalized(workflow, chapter.volume),
                "can_recheck": (chapter_edit(state, chapter, principal.user.id) and not _volume_finalized(workflow, chapter.volume)
                                and bool((chapter.content or "").strip())),
                "loop": loop, "pending": pending,
                "resolved": len([i for i in issues if i["status"] in ("resolved", "human_handled")]),
            })
        return {"revision": project.revision, "project_id": project_id, "volume": volume or "all",
                "totals": totals, "chapters": rows}

    def get_chapter_loop(self, principal: Principal, project_id: str, chapter_id: str) -> dict:
        state = self.repository.read()
        self._queue_viewable(state, principal, project_id)
        chapter = state.chapters.get(chapter_id)
        if chapter is None or chapter.project_id != project_id:
            raise DomainError(404, "NOT_FOUND", "章节不存在或不属于当前项目。")
        workflow = self._workflow(state, project_id)
        store = workflow.get("human_queue", {"loops": {}, "issues": {}})
        loop = store.get("loops", {}).get(chapter_id)
        issues = [i for i in store.get("issues", {}).values() if i["chapter_id"] == chapter_id]
        issues.sort(key=lambda i: i.get("number", ""))
        counts = {status: len([i for i in issues if i["status"] == status])
                  for status in (*OPEN_STATUSES, *CLOSED_STATUSES)}
        return {
            "revision": state.projects[project_id].revision, "chapter_id": chapter_id, "title": chapter.title,
            "volume": chapter.volume, "chapter_revision": chapter.revision,
            "loop": self._public_loop(state, chapter, loop),
            "history": (loop or {}).get("history", []),
            "counts": counts,
            "issues": [self._public_issue(state, principal, project_id, chapter, i, workflow) for i in issues],
        }

    def _issue_for_write(self, state: DemoState, project_id: str, issue_id: str):
        workflow = self._workflow(state, project_id, create=True)
        issue = queue_store(workflow)["issues"].get(issue_id)
        if issue is None:
            raise DomainError(404, "NOT_FOUND", "未找到本项目的人工处理问题。")
        chapter = state.chapters.get(issue["chapter_id"])
        if chapter is None or chapter.project_id != project_id:
            raise DomainError(404, "NOT_FOUND", "问题所在章节不存在。")
        if issue["status"] not in OPEN_STATUSES:
            raise DomainError(409, "HUMAN_ISSUE_NOT_PENDING", "该问题已处理或已驳回，请刷新后查看最新状态。",
                              {"status": issue["status"]})
        if _volume_finalized(workflow, chapter.volume):
            raise DomainError(409, "VOLUME_FINALIZED", "所在分册已定稿，须先解锁分册再处理。")
        return workflow, issue, chapter

    def resolve_human_issue(self, principal: Principal, project_id: str, issue_id: str, payload: dict,
                            expected: str | None, key: str | None) -> dict:
        method = payload.get("method")
        if method not in RESOLVE_METHODS:
            raise DomainError(422, "VALIDATION_ERROR", "请选择处理方式。", {"fields": {"method": "invalid"}})
        note = str(payload.get("note") or "").strip()
        also = [i for i in payload.get("also_issue_ids", []) if i != issue_id]

        def operation(state: DemoState, project, workflow):
            _, issue, chapter = self._issue_for_write(state, project_id, issue_id)
            targets = [issue]
            for other_id in also:
                _, other, other_chapter = self._issue_for_write(state, project_id, other_id)
                if other_chapter.id != chapter.id or other.get("paragraph_index") != issue.get("paragraph_index"):
                    raise DomainError(422, "VALIDATION_ERROR", "只能合并处理同一段落的问题。")
                targets.append(other)
            now = iso_time(self.demo._now())
            for target in targets:
                allowed = self._issue_permissions(state, principal, project_id, chapter, target, workflow)
                if not allowed["resolve"]:
                    if target.get("human_reason") in LEAD_ONLY_REASONS:
                        raise DomainError(403, "PROJECT_LEAD_REQUIRED", "额外承诺和披露类问题只能由项目负责人处理。")
                    raise DomainError(403, "CHAPTER_EDITOR_REQUIRED", "只有本节负责人或项目负责人可以处理本节问题。")
                target["status"] = "human_handled"
                target["resolution"] = {"method": method, "method_label": RESOLVE_METHODS[method], "note": note,
                                        "actor_id": principal.user.id, "at": now}
                target["updated_at"] = now
                target.setdefault("history", []).append({"at": now, "action": "human_handled", "method": method,
                                                         "actor_id": principal.user.id, "note": note})
            status = refresh_chapter_status(workflow, chapter.id)
            return {"issue_ids": [t["id"] for t in targets], "chapter_id": chapter.id, "chapter_status": status}

        return self._write(principal, project_id, f"human.resolve:{issue_id}", payload, expected, key, operation,
                           {"issue_id": issue_id, "method": method, "also_issue_ids": also})

    def reject_human_issue(self, principal: Principal, project_id: str, issue_id: str, payload: dict,
                           expected: str | None, key: str | None) -> dict:
        reason_type = payload.get("reason_type")
        reason = str(payload.get("reason") or "").strip()
        if reason_type not in REJECT_REASONS:
            raise DomainError(422, "VALIDATION_ERROR", "请选择驳回类型（误报 / 不采纳）。", {"fields": {"reason_type": "invalid"}})
        if not reason:
            raise DomainError(422, "REASON_REQUIRED", "驳回须填写理由。")

        def operation(state: DemoState, project, workflow):
            _, issue, chapter = self._issue_for_write(state, project_id, issue_id)
            if issue.get("level") == "blocker":
                raise DomainError(409, "BLOCKER_NOT_REJECTABLE", "阻断级问题不能驳回，只能修改正文或补齐资料。")
            allowed = self._issue_permissions(state, principal, project_id, chapter, issue, workflow)
            if not allowed["reject"]:
                raise DomainError(403, "PROJECT_LEAD_REQUIRED", "规则警告级问题只能由项目负责人驳回。")
            now = iso_time(self.demo._now())
            issue["status"] = "rejected"
            issue["rejection"] = {"reason_type": reason_type, "reason_label": REJECT_REASONS[reason_type],
                                  "reason": reason, "actor_id": principal.user.id, "at": now}
            issue["updated_at"] = now
            issue.setdefault("history", []).append({"at": now, "action": "rejected", "actor_id": principal.user.id,
                                                    "reason_type": reason_type, "reason": reason})
            status = refresh_chapter_status(workflow, chapter.id)
            return {"issue_ids": [issue["id"]], "chapter_id": chapter.id, "chapter_status": status}

        return self._write(principal, project_id, f"human.reject:{issue_id}", payload, expected, key, operation,
                           {"issue_id": issue_id, "reason_type": reason_type})

    def recheck_chapter(self, principal: Principal, project_id: str, chapter_id: str, payload: dict,
                        expected: str | None, key: str | None) -> dict:
        def operation(state: DemoState, project, workflow):
            chapter = state.chapters.get(chapter_id)
            if chapter is None or chapter.project_id != project_id:
                raise DomainError(404, "NOT_FOUND", "章节不存在或不属于当前项目。")
            if _volume_finalized(workflow, chapter.volume):
                raise DomainError(409, "VOLUME_FINALIZED", "所在分册已定稿，须先解锁分册再重新检查。")
            now_ts = self.demo._now()
            if chapter.lock and chapter.lock.expires_at > now_ts:
                raise DomainError(409, "CHAPTER_IN_USE", "本节正在被编辑，请先保存并释放编辑权后再重新检查。")
            if not (chapter.content or "").strip():
                raise DomainError(409, "CHAPTER_CONTENT_EMPTY", "本节还没有正式正文，不能重新检查。")
            plan = workflow.get("writing_plan", {}).get("chapters", {}).get(chapter_id, {})
            rows = [r for r in workflow.get("requirements", {}).values() if r.get("chapter_id") == chapter_id]
            evidence_ids = {e.get("id") for e in plan.get("evidence", []) if isinstance(e, dict) and e.get("id")}
            for row in rows:
                evidence_ids.update(eid for eid in row.get("evidence_ids", []) if eid)
            snippet_ids = {c.get("chunk_id") or c.get("id") for c in plan.get("retrieved_evidence", []) if isinstance(c, dict)}
            snippet_ids.update(workflow.get("assistant_citations", {}).get(chapter_id, []))  # 对话助手写入时已核对的引用
            critical = any(str(r.get("importance", "")).lower() in ("star", "critical")
                           or str(r.get("category", "")).lower() in ("star", "disqualification")
                           or "★" in str(r.get("text", "")) for r in rows)
            facts = [f for f in project_facts(state, project_id) if f.get("status") == "confirmed"]
            from .scope_rules import tender_number_basis
            context = LoopContext(title=chapter.title, allowed_evidence_ids=evidence_ids,
                                  allowed_snippet_ids={s for s in snippet_ids if s}, facts=facts, critical=critical,
                                  tender_numbers=tender_number_basis(state, project, workflow))
            max_rounds = int(payload.get("max_rounds") or 3)
            base_revision = int(chapter.revision or 0)
            outcome = run_chapter_loop(chapter.content, context, max_rounds=max_rounds)
            fixed = outcome["content"] != chapter.content
            now = iso_time(now_ts)
            if fixed:
                chapter.content = outcome["content"]
                chapter.revision += 1
                chapter.versions.append({"revision": chapter.revision, "content": chapter.content,
                                         "actor_id": principal.user.id, "created_at": now,
                                         "source": "chapter_loop", "note": "章节循环定位修正"})
            loop = record_loop(workflow, chapter, self._chapter_number(state, project_id, workflow, chapter_id),
                               outcome, actor_id=principal.user.id, now_iso=now,
                               checked_revision=chapter.revision, kind="recheck",
                               meta={"task": "recheck", "task_label": "重新检查", "model": None,
                                     "fixer": "规则修正（不调用模型）", "base_revision": base_revision,
                                     "inputs": {"requirements": len(rows), "evidence": len(evidence_ids),
                                                "snippets": len({s for s in snippet_ids if s}),
                                                "facts": len(facts), "critical": critical},
                                     "summary_relay": previous_chapter_relay(state, project_id, chapter)})
            from .notifications import notify_pending_human
            notify_pending_human(state, chapter, now)
            return {"chapter_id": chapter_id, "chapter_revision": chapter.revision, "content_fixed": fixed,
                    "loop": self._public_loop(state, chapter, loop),
                    "stop_reason": outcome["stop_reason"], "stop_reason_label": STOP_REASONS[outcome["stop_reason"]],
                    "pending_issues": len([i for i in outcome["issues"]])}

        return self._write(principal, project_id, f"chapter.loop.recheck:{chapter_id}", payload, expected, key,
                           operation, {"chapter_id": chapter_id})
