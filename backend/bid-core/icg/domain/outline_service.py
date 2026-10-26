# 为什么有这个文件：由原 workflow.py 模块化解耦生成的领域服务。
# 它解决什么问题：按领域上下文治理巨石 workflow.py，保持 100% 行为兼容。

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import time
from copy import deepcopy
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import Any, Callable

from icg.domain.domain import Chapter, DemoService, DemoState, DomainError, Principal, iso_time, new_id
from icg.domain.ports import ParserProvider
from icg.domain.input_snapshot import project_input_fingerprint
from icg.domain.sla import SlaService, public_sla, resolve_variables, sla_facts, sla_issues
from icg.domain.generation_context import (
    build_generation_context,
    chapter_plan,
    evidence_expired,
    plan_is_current,
    project_facts,
    public_plan,
    refuse_source_change,
    render_model_input,
    require_ready,
    resolve_fact_variables,
    validate_model_output,
    writing_source_fingerprint,
)
from icg.domain.project_access import (
    VOLUMES,
    writable,
    lead,
    volume_owner,
    require_lead,
    require_chapter,
    chapter_structure,
    chapter_edit,
    chapter_permissions,
    project_permissions,
    public_team,
)
from icg.domain.outline_plan import OutlinePlanService, OutlinePlanError, infer_chapter_type
from icg.domain.answer_card import AnswerCardService
from icg.infra.tender_retrieval import TenderRetrievalService
from icg.domain.editor_ai_context import build_editor_prompt_context
from icg.domain.parsing import LocalTextParser
from icg.domain.idempotency import lookup, remember

class OutlineServiceMixin:
    def get_outline_plan(self, project_id: str, volume_id: str | None = None) -> dict[str, Any]:
        return self.outline.get_outline_plan(project_id, volume_id=volume_id)

    def confirm_outline_plan(self, project_id: str, chapter_id: str | None = None,
                             plan_data: dict[str, Any] | None = None,
                             principal: Principal | None = None,
                             volume_id: str | None = None) -> dict[str, Any]:
        return self.outline.confirm_outline_plan(
            project_id=project_id,
            chapter_id=chapter_id,
            plan_data=plan_data,
            principal=principal,
            volume_id=volume_id,
        )

    def plan(self, principal, project_id, payload, expected, key):
        def operation(state, project, workflow):
            if not workflow["parse_confirmed"]:
                raise DomainError(409, "PARSE_NOT_CONFIRMED", "请先确认解析结果，再确认写作大纲。")
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
            # 方案确认检查实际来源资格；不把证据过期等缺项留到模型输出以后。
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


class OutlineService(OutlineServiceMixin):
    def __init__(self, workflow=None):
        self._workflow = workflow
