# 为什么有这个文件：PRD §5.8 领域子编排服务细化：大纲与结构编排服务。
# 它解决什么问题：
# 1. 负责大纲树构建、多级编号规范化（1.0, 1.1 等）与树型结构呈现；
# 2. 负责章节增删改、标题唯一性、负责人分派交接与正文草稿保护；
# 3. 负责分册定稿前置检查与编辑台段落/持锁/★标星条款识别元数据装配；
# 4. 从巨石 workflow_orchestrator 剥离，降低复杂度，保持 100% 行为兼容。

from __future__ import annotations

import re
import time
from copy import deepcopy
from typing import Any

from icg.domain.domain import Chapter, DemoState, DomainError, Principal, iso_time, new_id
from icg.domain.generation_context import (
    build_generation_context,
    chapter_plan,
    plan_is_current,
    project_facts,
    public_plan,
    require_ready,
    writing_source_fingerprint,
)
from icg.domain.project_access import (
    VOLUMES,
    chapter_edit,
    chapter_permissions,
    writable,
)
from icg.domain.outline_plan import infer_chapter_type
from icg.domain.outline_auto_tree import check_tree_finalization_readiness


class OutlineOrchestratorMixin:
    """大纲与章节结构编排领域能力 Mixin。"""

    def get_outline_plan(self, project_id: str, volume_id: str | None = None) -> dict[str, Any]:
        return self.outline.get_outline_plan(project_id, volume_id=volume_id)

    def confirm_outline_plan(
        self,
        project_id: str,
        chapter_id: str | None = None,
        plan_data: dict[str, Any] | None = None,
        principal: Principal | None = None,
        volume_id: str | None = None,
    ) -> dict[str, Any]:
        return self.outline.confirm_outline_plan(
            project_id=project_id,
            chapter_id=chapter_id,
            plan_data=plan_data,
            principal=principal,
            volume_id=volume_id,
        )

    def auto_build_outline_tree(
        self,
        principal: Principal,
        project_id: str,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """招标文件解析驱动的大纲树自动规划构建入口。"""
        return self.outline.auto_build_outline_tree(
            project_id=project_id,
            principal=principal,
            options=options,
        )

    def plan(self, principal, project_id, payload, expected, key):
        """确认与更新大纲章节规划（增删改、两册约束、事实与要点校验）。"""
        def operation(state, project, workflow):
            if not workflow["parse_confirmed"]:
                raise DomainError(409, "PARSE_NOT_CONFIRMED", "请先确认解析结果，再确认写作大纲。")
            from icg.domain.sla import sla_issues
            issues = sla_issues(state, project_id)
            if issues:
                raise DomainError(409, "SLA_NOT_READY", "服务承诺或必备事实仍待处理，请先逐条核对。", {"issues": issues})
            requested = payload["chapters"]
            scope = payload.get("scope", "all")
            expected_volumes = set(VOLUMES) if scope == "all" else {scope}
            if {c["volume"] for c in requested} != expected_volumes:
                raise DomainError(422, "TWO_VOLUMES_REQUIRED", "本期大纲必须同时包含技术和商务两册。")
            all_old = {c.id: c for c in state.chapters.values() if c.project_id == project_id}
            old = {identity: c for identity, c in all_old.items() if c.volume in expected_volumes}
            seen, retained, planned = set(), [], {}
            facts = {fact["id"]: fact for fact in project_facts(state, project_id)}
            if any(fact["required"] and fact["status"] != "confirmed" for fact in facts.values()):
                raise DomainError(409, "FACT_NOT_READY", "全部必备事实确认后才能确认写作方案。")
            for item in requested:
                ids = item.get("fact_ids", [])
                if len(ids) != len(set(ids)):
                    raise DomainError(422, "DUPLICATE_FACT", "本章同一事实不能重复选择。")
                if any(identity not in facts for identity in ids):
                    raise DomainError(409, "FACT_NOT_FOUND", "所选事实不属于本项目或已经删除。")
                if any(facts[identity]["status"] != "confirmed" for identity in ids):
                    raise DomainError(409, "FACT_NOT_READY", "本章所选事实须先确认取值。")
                from icg.domain.parsing import LocalTextParser
                LocalTextParser._validate_text(item.get("writing_points", ""))
                if not item["title"].strip():
                    raise DomainError(422, "EMPTY_CHAPTER_TITLE", "章节标题不能为空。")
                identity = item.get("id")
                if identity:
                    chapter = old.get(identity)
                    if chapter is None:
                        raise DomainError(404, "NOT_FOUND", "大纲章节不属于本项目。")
                else:
                    chapter = next((c for c in old.values() if c.id not in seen and c.title == item["title"] and c.volume == item["volume"]), None)
                    if chapter is None:
                        # 默认两册可按分册复用空章节，不丢弃旧正文。
                        chapter = next((c for c in old.values() if c.id not in seen and c.volume == item["volume"] and not c.content.strip() and not c.drafts and c.lock is None), None)
                    if chapter is None:
                        chapter = Chapter(new_id("chapter"), project_id, item["title"], item["volume"], "")
                        chapter.versions.append({"revision": 1, "content": "", "actor_id": principal.user.id, "created_at": iso_time(self.demo._now())})
                        state.chapters[chapter.id] = chapter
                if chapter.id in seen:
                    raise DomainError(422, "DUPLICATE_CHAPTER", "同一章节不能重复出现在大纲。")
                if chapter.title != item["title"] or chapter.volume != item["volume"]:
                    if chapter.drafts or (chapter.lock and chapter.lock.expires_at > self.demo._now()):
                        raise DomainError(409, "CHAPTER_IN_USE", "章节有草稿或编辑权，不能改动大纲。")
                    if chapter.volume != item["volume"] and chapter.content.strip():
                        raise DomainError(409, "CHAPTER_HAS_CONTENT", "有正文的章节不能直接改分册。")
                    chapter.title, chapter.volume = item["title"], item["volume"]
                if "assignee_id" in item:
                    self.team.eligible(state, project_id, item["assignee_id"], chapter.volume)
                    if chapter.assignee_id != item["assignee_id"]:
                        self.team.handoff(state, principal, project_id, [chapter], payload.get("reason", ""), [chapter.assignee_id])
                        chapter.assignee_id = item["assignee_id"]
                self.team.eligible(state, project_id, chapter.assignee_id, chapter.volume)
                seen.add(chapter.id)
                retained.append(chapter)
                planned[chapter.id] = {"id": chapter.id, "fact_ids": list(ids),
                                       "writing_points": item.get("writing_points", ""), "target_length": item.get("target_length")}
            removed = set(old) - seen
            for identity in removed:
                chapter = old[identity]
                if (chapter.content.strip() or any(version["content"].strip() for version in chapter.versions)
                        or chapter.drafts or (chapter.lock and chapter.lock.expires_at > self.demo._now())):
                    raise DomainError(409, "CHAPTER_HAS_CONTENT", "不能删除有正文、草稿或有效编辑权的章节。")
                if any(r["chapter_id"] == identity for r in workflow["requirements"].values()):
                    raise DomainError(409, "CHAPTER_MAPPED", "章节已关联矩阵条款，先解除映射。")
                del state.chapters[identity]
                workflow["candidates"].pop(identity, None)
            workflow["plan_confirmed"] = True
            workflow["outline_revision"] = int(workflow.get("outline_revision") or 0) + 1
            old_order = workflow.get("chapter_order", [])
            unaffected = [identity for identity in old_order if identity in all_old and all_old[identity].volume not in expected_volumes]
            unaffected += [identity for identity, c in all_old.items() if c.volume not in expected_volumes and identity not in unaffected]
            workflow["chapter_order"] = [c.id for c in retained] + unaffected
            previous_plan = workflow.get("writing_plan", {}).get("chapters", {})
            preserved = {identity: item for identity, item in previous_plan.items() if identity not in old}
            workflow["writing_plan"] = {"confirmed_by": principal.user.id, "confirmed_by_name": principal.user.name,
                                        "confirmed_at": iso_time(self.demo._now()), "chapters": {**preserved, **planned}}
            for chapter in retained:
                self._confirm_chapter_plan(state, principal, project_id, chapter, workflow)
            for chapter in retained:
                require_ready(build_generation_context(state, project_id, chapter, self.demo._now()))
            return {"plan_confirmed": plan_is_current(state, project_id), "writing_plan": public_plan(workflow, state, project_id),
                    "chapters": [self._chapter_summary(state, workflow, c, principal.user.id) for c in retained]}
        return self._write(principal, project_id, "plan.confirm", payload, expected, key, operation)

    def _confirm_chapter_plan(self, state, principal, project_id, chapter, workflow):
        if not writable(state, project_id, state.project_teams[project_id]["owners"].get(chapter.volume)):
            raise DomainError(403, "VOLUME_OWNER_REQUIRED", "本册尚未指定负责人，不能确认写作方案。")
        unmapped = [r["id"] for r in workflow["requirements"].values()
                    if r["volume"] == chapter.volume and r["status"] != "rejected" and
                    (r["chapter_id"] not in state.chapters or state.chapters[r["chapter_id"]].project_id != project_id
                     or state.chapters[r["chapter_id"]].volume != chapter.volume)]
        if unmapped:
            raise DomainError(409, "MATRIX_MAPPING_MISSING", "本册还有未分配章节的招标条款，请先完成响应矩阵映射。", {"requirement_ids": unmapped})
        saved = workflow.setdefault("writing_plan", {}).setdefault("chapters", {}).setdefault(chapter.id, chapter_plan(workflow, chapter.id))
        saved.update(confirmed_by=principal.user.id, confirmed_by_name=principal.user.name,
                     confirmed_at=iso_time(self.demo._now()), confirmation_pending=False)
        saved["confirmed_input_fingerprint"] = writing_source_fingerprint(state, project_id, chapter.id)
        require_ready(build_generation_context(state, project_id, chapter, self.demo._now()))
        self._audit(state, principal, project_id, "chapter-plan.confirmed", {"chapter_id": chapter.id,
                    "confirmed_input_fingerprint": saved["confirmed_input_fingerprint"], "confirmed_by": principal.user.id})

    def chapter_plan_save(self, principal, project_id, chapter_id, payload, expected, key):
        def operation(state, project, workflow):
            chapter = self.demo._chapter(state, principal, chapter_id)
            facts = {fact["id"] for fact in project_facts(state, project_id)}
            ids = payload["fact_ids"]
            if len(ids) != len(set(ids)):
                raise DomainError(422, "DUPLICATE_FACT", "本章同一事实不能重复选择。")
            if set(ids) - facts:
                raise DomainError(409, "FACT_NOT_FOUND", "所选事实不属于本项目或已经删除。")
            old = chapter_plan(workflow, chapter_id)
            workflow.setdefault("writing_plan", {}).setdefault("chapters", {})[chapter_id] = {**old, **payload, "confirmation_pending": True}
            return {"chapter": self._chapter_summary(state, workflow, chapter, principal.user.id), "writing_plan": public_plan(workflow, state, project_id)}
        return self._write(principal, project_id, "chapter.plan.save:" + chapter_id, payload, expected, key, operation)

    def chapter_plan_confirm(self, principal, project_id, chapter_id, payload, expected, key):
        def operation(state, project, workflow):
            chapter = self.demo._chapter(state, principal, chapter_id)
            self._confirm_chapter_plan(state, principal, project_id, chapter, workflow)
            return {"chapter": self._chapter_summary(state, workflow, chapter, principal.user.id), "writing_plan": public_plan(workflow, state, project_id)}
        return self._write(principal, project_id, "chapter.plan.confirm:" + chapter_id, payload, expected, key, operation)

    def chapter_edit_detail(self, principal: Principal, project_id: str, chapter_id: str) -> dict[str, Any]:
        """获取编辑台所需的章节详情、段落结构、持锁人与权限元数据。"""
        state = self.repository.read()
        self.demo._project(state, principal, project_id)
        chapter = state.chapters.get(chapter_id)
        if chapter is None:
            raise DomainError(404, "NOT_FOUND", "未找到有权访问的章节。")
        if chapter.project_id != project_id:
            raise DomainError(404, "NOT_FOUND", "章节不属于当前项目。")

        now = self.demo._now() if hasattr(self.demo, "_now") else time.time()

        # 1. 持锁状态感知（结合 ChapterLock 与 ProjectLock）
        active_chapter_lock = chapter.lock is not None and chapter.lock.expires_at > now
        if active_chapter_lock:
            locked_by = chapter.lock.owner_id
            lock_expires_at = iso_time(chapter.lock.expires_at)
        else:
            workflow = state.workflows.get(project_id, {})
            p_lock = workflow.get("project_lock") or workflow.get("lock")
            if p_lock and isinstance(p_lock, dict):
                p_exp = p_lock.get("expires_at")
                p_active = False
                if isinstance(p_exp, (int, float)) and p_exp > now:
                    p_active = True
                    lock_expires_at = iso_time(p_exp)
                elif isinstance(p_exp, str):
                    p_active = True
                    lock_expires_at = p_exp
                if p_active:
                    locked_by = p_lock.get("owner_id") or p_lock.get("locked_by")
                else:
                    locked_by = None
                    lock_expires_at = None
            else:
                locked_by = None
                lock_expires_at = None

        workflow = state.workflows.get(project_id, {})
        outline_plans = workflow.get("outline_plans", {})
        meta = outline_plans.get(chapter_id, {})
        requirements = list(workflow.get("requirements", {}).values())
        matched_reqs = [r for r in requirements if r.get("chapter_id") == chapter.id]

        # 2. 星号条款 (★) 与废标条款识别
        has_asterisk = any(
            r.get("mandatory") or r.get("asterisk") or "★" in r.get("clause", "") or "★" in r.get("text", "")
            for r in matched_reqs
        )
        has_disqualified = any(
            r.get("disqualified") or "废标" in r.get("clause", "") or "废标" in r.get("text", "")
            for r in matched_reqs
        )
        is_mandatory = bool(has_asterisk or has_disqualified or meta.get("is_mandatory", False))

        # 3. 章节编号与大纲类型推断
        chapter_number = meta.get("section_number") or meta.get("chapter_number")
        if not chapter_number:
            chapters_in_proj = [c for c in state.chapters.values() if c.project_id == project_id and c.volume == chapter.volume]
            order_map = {cid: idx for idx, cid in enumerate(workflow.get("chapter_order", []))}
            chapters_in_proj.sort(key=lambda c: order_map.get(c.id, len(order_map)))
            try:
                idx = [c.id for c in chapters_in_proj].index(chapter.id)
                chapter_number = f"{idx + 1}.0"
            except ValueError:
                chapter_number = "1.0"

        outline_type = meta.get("chapter_type") or infer_chapter_type(chapter.title)

        # 4. 组装段落结构与 citations
        stored_paragraphs = workflow.get("chapter_paragraphs", {}).get(chapter.id)
        if stored_paragraphs and isinstance(stored_paragraphs, list):
            paragraphs = []
            for idx, p in enumerate(stored_paragraphs, start=1):
                paragraphs.append({
                    "id": p.get("id") or f"{chapter.id}-p{idx}",
                    "order": p.get("order", idx),
                    "text": p.get("text", ""),
                    "citations": p.get("citations", []),
                    "created_at": p.get("created_at") or iso_time(now),
                    "updated_at": p.get("updated_at") or iso_time(now),
                })
        else:
            all_citations = []
            seen_cite_ids = set()
            for v in getattr(chapter, "versions", []):
                cite = v.get("citation")
                if cite and isinstance(cite, dict) and cite.get("id") not in seen_cite_ids:
                    all_citations.append(cite)
                    seen_cite_ids.add(cite.get("id"))
            for r in matched_reqs:
                for ev_id in r.get("evidence_ids", []):
                    if ev_id not in seen_cite_ids:
                        item = state.library.get(ev_id)
                        if item:
                            cite_entry = {
                                "id": item.get("id", ev_id),
                                "name": item.get("name", "证据资料"),
                                "tag": "[证]",
                                "source_type": "company_library",
                                "revision": item.get("revision", 1),
                            }
                            all_citations.append(cite_entry)
                            seen_cite_ids.add(ev_id)

            created_at_str = iso_time(now)
            updated_at_str = iso_time(now)
            if chapter.versions:
                first_v = chapter.versions[0]
                latest_v = chapter.versions[-1]
                if first_v.get("created_at"):
                    created_at_str = first_v["created_at"]
                if latest_v.get("created_at"):
                    updated_at_str = latest_v["created_at"]

            from icg.infra.database import decompose_paragraphs
            paragraphs = decompose_paragraphs(
                chapter.content or "",
                chapter.id,
                citations=all_citations,
                created_at=created_at_str,
                updated_at=updated_at_str,
            )

        can_edit = chapter_edit(state, chapter, principal.user.id)
        permissions = chapter_permissions(state, chapter, principal.user.id)

        return {
            "id": chapter.id,
            "project_id": chapter.project_id,
            "title": chapter.title,
            "volume": chapter.volume,
            "chapter_number": chapter_number,
            "outline_type": outline_type,
            "is_mandatory": is_mandatory,
            "locked_by": locked_by,
            "lock_expires_at": lock_expires_at,
            "revision": chapter.revision,
            "paragraphs": paragraphs,
            "can_edit": can_edit,
            "permissions": permissions,
        }

    def build_outline_tree(self, state: DemoState, project_id: str, volume: str = "all") -> list[dict[str, Any]]:
        """构建规范化的大纲树状与分层结构。"""
        workflow = state.workflows.get(project_id, {})
        order_map = {cid: idx for idx, cid in enumerate(workflow.get("chapter_order", []))}
        chapters = [c for c in state.chapters.values() if c.project_id == project_id and (volume == "all" or c.volume == volume)]
        chapters.sort(key=lambda c: order_map.get(c.id, len(order_map)))
        outline_plans = workflow.get("outline_plans", {})
        requirements = list(workflow.get("requirements", {}).values())

        tree_nodes = []
        for idx, c in enumerate(chapters, start=1):
            meta = outline_plans.get(c.id, {})
            sec_num = meta.get("section_number") or f"{idx}.0"
            matched_reqs = [r for r in requirements if r.get("chapter_id") == c.id]
            bound_ids = meta.get("bound_requirement_ids") or [r["id"] for r in matched_reqs]
            has_asterisk = meta.get("has_asterisk") if "has_asterisk" in meta else any(
                r.get("mandatory") or r.get("asterisk") or "★" in r.get("clause", "") for r in matched_reqs
            )
            has_disqualified = meta.get("has_disqualified") if "has_disqualified" in meta else any(
                r.get("disqualified") or "废标" in r.get("clause", "") for r in matched_reqs
            )

            tree_nodes.append({
                "id": c.id,
                "chapter_id": c.id,
                "title": c.title,
                "volume": c.volume,
                "section_number": sec_num,
                "level": meta.get("level", 2 if "." in sec_num and not sec_num.endswith(".0") else 1),
                "chapter_type": meta.get("chapter_type") or infer_chapter_type(c.title),
                "system_subtype": meta.get("system_subtype"),
                "has_content": bool(c.content.strip()),
                "has_pending": "待补" in c.content,
                "assignee_id": getattr(c, "assignee_id", None),
                "versions_count": len(getattr(c, "versions", [])),
                "bound_requirement_ids": bound_ids,
                "associated_clause_ids": bound_ids,
                "has_asterisk": has_asterisk,
                "has_disqualified": has_disqualified,
                "is_mandatory": has_asterisk or has_disqualified,
                "writing_points": meta.get("writing_points", ""),
                "target_length": meta.get("target_length"),
            })
        return tree_nodes

    def check_outline_finalization_readiness(self, state: DemoState, project_id: str, volume: str) -> dict[str, Any]:
        """核验大纲是否满足分册定稿锁定的前置要求。"""
        return check_tree_finalization_readiness(state, project_id, volume)


class OutlineOrchestrator(OutlineOrchestratorMixin):
    """独立大纲编排领域服务。"""

    def __init__(self, workflow: Any = None):
        self._workflow_service = workflow

    def __getattr__(self, name: str) -> Any:
        if hasattr(self, "_workflow_service") and self._workflow_service is not None and hasattr(self._workflow_service, name):
            return getattr(self._workflow_service, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
