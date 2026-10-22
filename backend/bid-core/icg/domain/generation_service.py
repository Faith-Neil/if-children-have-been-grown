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

from icg_demo.domain import Chapter, DemoService, DemoState, DomainError, Principal, iso_time, new_id
from icg_demo.ports import ParserProvider
from icg_demo.input_snapshot import project_input_fingerprint
from icg_demo.sla import SlaService, public_sla, resolve_variables, sla_facts, sla_issues
from icg_demo.generation_context import (
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
from icg_demo.project_access import (
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
from icg_demo.outline_service import OutlinePlanService, OutlinePlanError, infer_chapter_type
from icg_demo.answer_card import AnswerCardService
from icg_demo.tender_retrieval import TenderRetrievalService
from icg_demo.editor_ai_context import build_editor_prompt_context
from icg_demo.parsing import LocalTextParser
from icg_demo.idempotency import lookup, remember
from icg.infra.repositories.chapters import decompose_paragraphs

class GenerationServiceMixin:
    def assistant_query(self, principal: Principal, project_id: str, query: str,
                        knowledge_base_enabled: bool = True) -> dict:
        return self.answer_card.process_query(principal, project_id, query, knowledge_base_enabled)

    def insert_answer_card(self, principal: Principal, project_id: str, chapter_id: str,
                           card_data: dict[str, Any], lease_token: str,
                           item_id: str | None = None,
                           insert_mode: str = "append",
                           target_paragraph: str | None = None) -> dict[str, Any]:
        return self.answer_card.insert_answer_card(
            principal=principal,
            project_id=project_id,
            chapter_id=chapter_id,
            card_data=card_data,
            lease_token=lease_token,
            item_id=item_id,
            insert_mode=insert_mode,
            target_paragraph=target_paragraph,
        )

    def general_chat(self, principal: Principal, project_id: str, query: str,
                     knowledge_base_enabled: bool = True,
                     chapter_id: str | None = None,
                     history: list[dict[str, str]] | None = None,
                     chapter_title: str | None = None,
                     selected_text: str | None = None,
                     scene: str | None = None,
                     lease_token: str | None = None,
                     injected_tender_clauses: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        return self.answer_card.general_chat(
            principal=principal,
            project_id=project_id,
            query=query,
            knowledge_base_enabled=knowledge_base_enabled,
            chapter_id=chapter_id,
            history=history,
            chapter_title=chapter_title,
            selected_text=selected_text,
            scene=scene,
            lease_token=lease_token,
            injected_tender_clauses=injected_tender_clauses,
        )

    def ask_assistant(self, principal: Principal, project_id: str, query: str,
                      knowledge_base_enabled: bool = True,
                      chapter_id: str | None = None,
                      history: list[dict[str, str]] | None = None,
                      chapter_title: str | None = None,
                      selected_text: str | None = None,
                      scene: str | None = None,
                      lease_token: str | None = None,
                      injected_tender_clauses: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        return self.general_chat(
            principal=principal,
            project_id=project_id,
            query=query,
            knowledge_base_enabled=knowledge_base_enabled,
            chapter_id=chapter_id,
            history=history,
            chapter_title=chapter_title,
            selected_text=selected_text,
            scene=scene,
            lease_token=lease_token,
            injected_tender_clauses=injected_tender_clauses,
        )

    def editor_ai_chat(self, principal: Principal, project_id: str, query: str,
                       chapter_id: str, chapter_title: str | None = None,
                       selected_text: str | None = None, scene: str | None = None,
                       lease_token: str | None = None,
                       knowledge_base_enabled: bool = True,
                       history: list[dict[str, str]] | None = None,
                       injected_tender_clauses: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        return self.demo.chat_editor_context(
            principal=principal,
            project_id=project_id,
            query=query,
            chapter_id=chapter_id,
            chapter_title=chapter_title,
            selected_text=selected_text,
            scene=scene,
            lease_token=lease_token,
            knowledge_base_enabled=knowledge_base_enabled,
            history=history,
            injected_tender_clauses=injected_tender_clauses,
        )

    def accept_ai_suggestion(
        self,
        principal: Principal,
        project_id: str,
        chapter_id: str,
        lease_token: str,
        base_revision: int,
        suggested_text: str,
        paragraph_id: str | None = None,
        original_text: str | None = None,
        citations: list[dict[str, Any]] | None = None,
        input_fingerprint: str | None = None,
    ) -> dict[str, Any]:
        return self.demo.accept_ai_suggestion(
            principal=principal,
            project_id=project_id,
            chapter_id=chapter_id,
            lease_token=lease_token,
            base_revision=base_revision,
            suggested_text=suggested_text,
            paragraph_id=paragraph_id,
            original_text=original_text,
            citations=citations,
            input_fingerprint=input_fingerprint,
        )

    def compliance_cross_check(
        self,
        principal: Principal,
        project_id: str,
        chapter_id: str,
        model_config_id: str | None = None,
        strict_mode: bool = True,
    ) -> dict[str, Any]:
        return self.demo.compliance_cross_check(
            principal=principal,
            project_id=project_id,
            chapter_id=chapter_id,
            model_config_id=model_config_id,
            strict_mode=strict_mode,
        )

    def search_tender_slices(self, principal: Principal, project_id: str, query: str,
                             enabled: bool | None = None, top_k: int = 10,
                             clause_type: str | None = None) -> dict[str, Any]:
        return self.tender_retrieval.search(
            principal=principal,
            project_id=project_id,
            query=query,
            enabled=enabled,
            top_k=top_k,
            clause_type=clause_type,
        ).to_dict()

    def inject_tender_clauses(self, principal: Principal, project_id: str, chapter_id: str,
                              slice_ids: list[str] | None = None,
                              slices: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        return self.tender_retrieval.inject_clauses_to_chapter(
            principal=principal,
            project_id=project_id,
            chapter_id=chapter_id,
            slice_ids=slice_ids,
            slices=slices,
        )

    def get_injected_tender_clauses(self, principal: Principal, project_id: str, chapter_id: str) -> list[dict[str, Any]]:
        return self.tender_retrieval.get_injected_clauses(principal, project_id, chapter_id)

    def clear_injected_tender_clauses(self, principal: Principal, project_id: str, chapter_id: str) -> bool:
        return self.tender_retrieval.clear_injected_clauses(principal, project_id, chapter_id)

    def set_tender_indexing_switch(self, principal: Principal, project_id: str, enabled: bool) -> bool:
        return self.tender_retrieval.set_feature_switch(principal, project_id, enabled)

    def get_tender_indexing_switch(self, project_id: str) -> bool:
        return self.tender_retrieval.get_feature_switch(project_id)

    def build_editor_prompt_context(self, project_id: str, chapter_id: str, query: str,
                                    selected_text: str | None = None, chapter_title: str | None = None,
                                    scene: str | None = None, knowledge_base_enabled: bool = True,
                                    injected_tender_clauses: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        from icg_demo.editor_ai_context import build_editor_prompt_context
        state = self.demo.repository.read()
        return build_editor_prompt_context(
            state=state,
            project_id=project_id,
            chapter_id=chapter_id,
            query=query,
            selected_text=selected_text,
            chapter_title=chapter_title,
            scene=scene,
            knowledge_base_enabled=knowledge_base_enabled,
            evidence_service=getattr(self.demo, "evidence_service", None),
            injected_tender_clauses=injected_tender_clauses,
        )

    def start_chapter_generation(self, project_id: str, chapter_id: str, principal: Principal,
                                 sync_execute: bool = False) -> dict[str, Any]:
        return self.demo.start_chapter_generation(
            project_id=project_id,
            chapter_id=chapter_id,
            principal=principal,
            sync_execute=sync_execute,
        )

    def assemble_writing_prompt_plan(self, project_id: str, chapter_id: str,
                                     principal: Principal | None = None) -> dict[str, Any]:
        return self.demo.assemble_writing_prompt_plan(
            project_id=project_id,
            chapter_id=chapter_id,
            principal=principal,
        )

    def generate(self, principal, project_id, payload, expected, key):
        snapshot, previous = self._preflight(principal, project_id, "chapter.generate", payload, expected, key)
        if previous:
            return previous
        project = self.demo._project(snapshot, principal, project_id)
        self.demo.require_allowed_model(project, state=snapshot)
        workflow = self._workflow(snapshot, project_id)
        if not workflow["parse_confirmed"]:
            raise DomainError(409, "PARSE_NOT_CONFIRMED", "解析确认后才能生成章节候选。")
        chapters = self._ordered_chapters(snapshot, project_id, workflow)
        selected = payload.get("chapter_ids")
        if selected is not None:
            if not selected or len(selected) != len(set(selected)) or set(selected) - {c.id for c in chapters}:
                raise DomainError(404, "NOT_FOUND", "所选章节不存在或不属于本项目。")
            chapters = [c for c in chapters if c.id in selected]
        candidates = {}
        def check_model_access():
            current = self.repository.read()
            actual_project = self.demo._project(current, principal, project_id)
            self._authorize(current, principal, project_id, "chapter.generate", payload)
            self.demo.require_allowed_model(actual_project, state=current)
            if self._fingerprint(current, project_id) != self._fingerprint(snapshot, project_id):
                raise DomainError(409, "VERSION_CONFLICT", "项目输入在生成期间发生变化，不能继续把旧资料交给模型或保存候选。")
        for chapter in chapters:
            assembled = build_generation_context(snapshot, project_id, chapter, self.demo._now(),
                                                 evidence_service=self.demo.evidence_service)
            require_ready(assembled)
            input_snapshot = assembled["input_snapshot"]
            context = render_model_input(input_snapshot)
            instruction = "按本章已确认条款、响应、证据和事实组织候选；不能编造证据与承诺。引用事实保留变量，不能改取值。"
            refuse_source_change(input_snapshot["plan"]["writing_points"], input_snapshot)
            check_model_access()
            provider = self.demo.resolve_model_provider(snapshot, project_id)
            try:
                content = provider.suggest(instruction, context)
            except DomainError:
                raise
            except Exception as error:
                raise DomainError(502, "MODEL_UNAVAILABLE", "候选生成失败，正式正文没有修改。") from error
            check_model_access()
            validate_model_output(snapshot, project_id, content, input_snapshot)
            input_snapshot.update(model_input=context, model_instruction=instruction)
            candidates[chapter.id] = {"id": new_id("candidate"), "content": content,
                                      "base_revision": chapter.revision,
                                      "input_fingerprint": self._fingerprint(snapshot, project_id),
                                      "provider": getattr(provider, "name", "injected"),
                                      "is_real_model": bool(getattr(provider, "is_real_model", False)),
                                      "created_at": iso_time(self.demo._now()), "source_scope": "whole_chapter",
                                      "input_snapshot": input_snapshot}
        def operation(state, project, current):
            self.demo.require_allowed_model(project, state=state)
            if self._fingerprint(state, project_id) != self._fingerprint(snapshot, project_id):
                raise DomainError(409, "VERSION_CONFLICT", "项目资料在生成期间更新，请重新生成候选。")
            # 旧编辑接口也可能在模型调用期间提交版本，必须重新核对。
            for chapter in chapters:
                actual = state.chapters.get(chapter.id)
                if actual is None or actual.revision != chapter.revision:
                    raise DomainError(409, "VERSION_CONFLICT", "正文在生成期间更新，请重新生成候选。")
                require_ready(build_generation_context(state, project_id, actual, self.demo._now()))
            current["candidates"].update(candidates)
            job = self._job(state, project_id, "generate", "章节候选已生成；需在编辑台人工核对、取得编辑权后提交。")
            return {"job": job, "chapters": [self._chapter_summary(state, current, state.chapters[c.id], principal.user.id) for c in chapters]}
        return self._write(principal, project_id, "chapter.generate", payload, expected, key, operation)

class GenerationService(GenerationServiceMixin):
    def __init__(self, workflow=None):
        self._workflow = workflow
