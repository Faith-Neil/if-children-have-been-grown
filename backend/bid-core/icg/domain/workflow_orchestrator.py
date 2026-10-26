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

from icg.domain.export_service import ExportServiceMixin, CheckBlockerError, chapter_export_block, DOCX_MEDIA_TYPE, WORD_DEFAULT_FORMAT_METADATA, SHANGHAI
from icg.domain.outline_service import OutlineServiceMixin
from icg.domain.generation_service import GenerationServiceMixin
from icg.domain.volume_finalize import VolumeFinalizeMixin
from icg.domain.compliance_rules import ComplianceRulesMixin

SAMPLE_TENDER = """合成招标文件：星河数据库维保服务项目
招标编号：DEMO-2026-001
投标截止时间：2026-12-31T17:00:00+08:00
服务期限：12个月
采购人：星河科技（虚构）
★技术要求：提供数据库日常巡检，每月提交巡检报告。
技术要求：重大故障响应不超过30分钟，处理方案由双方核对。
商务要求：投标人应提供有效企业资质证明。
商务要求：提供同类项目业绩证明，所有资料仅使用合成测试数据。
"""


def _blank_workflow() -> dict:
    return {"files": {}, "requirements": {}, "facts": {}, "conflicts": {},
            "candidates": {}, "checks": {}, "exports": {}, "parse_confirmed": False,
            "plan_confirmed": False, "chapter_order": [], "sla": None, "sla_commitments": {}, "writing_plan": {}}


class WorkflowService(OutlineServiceMixin, GenerationServiceMixin, ExportServiceMixin, VolumeFinalizeMixin, ComplianceRulesMixin):
    MAX_UPLOAD = 5 * 1024 * 1024
    IMPLEMENTED_RULES = ["parse-confirmation", "fact-conflicts", "matrix-completeness",
                         "evidence-company-and-review", "evidence-validity", "committed-content",
                         "pending-markers", "two-volumes", "input-fingerprint", "export-permission",
                         "sla-values-and-capability-subset", "sla-variables-and-labelled-numbers-subset",
                         "R01", "R02", "R03", "R04", "R09", "R10", "R15", "R23", "R34", "R35", "R37"]
    UNIMPLEMENTED_RULES = ["参考合规规则尚未逐条完成（按一期完整/一期简化/二期分组）", "语义事实与承诺核对",
                           "公司全文查重", "结构化敏感变量", "交叉复核和完整分册定稿"]

    def __init__(self, demo: DemoService, parser: ParserProvider):
        self.demo = demo
        self.repository = demo.repository
        self.parser = parser
        self.sla = SlaService(self)
        from icg.domain.project_team import ProjectTeamService
        self.team = ProjectTeamService(self)
        from icg.domain.answer_card import AnswerCardService
        self.answer_card = AnswerCardService(demo)
        from icg.domain.outline_plan import OutlinePlanService
        self.outline = OutlinePlanService(demo)
        from icg.infra.tender_retrieval import TenderRetrievalService
        self.tender_retrieval = TenderRetrievalService(demo)

    @staticmethod
    def _workflow(state: DemoState, project_id: str, *, create=False) -> dict:
        if create:
            return state.workflows.setdefault(project_id, _blank_workflow())
        return state.workflows.get(project_id, _blank_workflow())

    @staticmethod
    def _version(actual: int, expected: str | None):
        if expected is None:
            raise DomainError(428, "IF_MATCH_REQUIRED", "此操作需要最新版本号，请刷新页面再保存。")
        raw = expected.strip().strip('"')
        if not raw.isdigit() or int(raw) != actual:
            raise DomainError(409, "VERSION_CONFLICT", "数据已被更新，请刷新核对后再保存。", {"current_revision": actual})

    @staticmethod
    def _idempotency(key: str | None) -> str:
        from icg.domain.idempotency import validate_key
        return validate_key(key)

    @staticmethod
    def _request_hash(action: str, payload: dict, expected: str | None) -> str:
        from icg.domain.idempotency import fingerprint
        return fingerprint(action, payload, expected)

    def _preflight(self, principal, project_id, action, payload, expected, key):
        from icg.domain.idempotency import lookup
        key = self._idempotency(key)
        state = self.repository.read()
        project = self.demo._project(state, principal, project_id)
        self._authorize(state, principal, project_id, action, payload)
        replay = lookup(state, project_id, principal.user.id, key,
                        self._request_hash(action, payload, expected), self.demo._now())
        if replay is not None:
            return state, replay
        self._version(project.revision, expected)
        return state, None

    @staticmethod
    def _ordered_chapters(state, project_id, workflow):
        chapters = [c for c in state.chapters.values() if c.project_id == project_id]
        positions = {identity: index for index, identity in enumerate(workflow.get("chapter_order", []))}
        return sorted(chapters, key=lambda c: positions.get(c.id, len(positions)))

    def _audit(self, state: DemoState, principal: Principal, project_id: str, action: str, details=None):
        state.audit.append({"id": new_id("event"), "action": action, "actor_id": principal.user.id,
                            "project_id": project_id, "chapter_id": "", "revision": state.projects[project_id].revision,
                            "at": iso_time(self.demo._now()), "details": details or {}})

    def _write(self, principal: Principal, project_id: str, action: str, payload: dict,
               expected: str | None, key: str | None, operation: Callable, audit_details: dict | None = None) -> dict:
        from icg.domain.idempotency import lookup, remember
        key = self._idempotency(key)
        request_fingerprint = self._request_hash(action, payload, expected)

        def transaction(state: DemoState):
            project = self.demo._project(state, principal, project_id)
            self._authorize(state, principal, project_id, action, payload)
            replay = lookup(state, project_id, principal.user.id, key, request_fingerprint, self.demo._now())
            if replay is not None:
                return replay
            self._version(project.revision, expected)
            workflow = self._workflow(state, project_id, create=True)
            result = operation(state, project, workflow)
            project.revision += 1
            self._audit(state, principal, project_id, action, audit_details)
            result = {"revision": project.revision, **result}
            if "project" in result:
                result["project"] = asdict(project)
            remember(state, project_id, principal.user.id, key, request_fingerprint, result, self.demo._now())
            return result
        return self.repository.transaction(transaction)

    def _authorize(self, state, principal, project_id, action, payload):
        identity = principal.user.id
        name, _, resource_id = action.partition(":")
        if name in ("volume.finalize", "volume.unlock"):
            from icg.domain.project_access import normalize_role
            project = state.projects.get(project_id)
            if project and project.company_id != principal.user.company_id:
                raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")
            norm_role = normalize_role(principal.user.role)
            if norm_role == "company_admin":
                return
            if not lead(state, project_id, identity):
                raise DomainError(403, "FORBIDDEN", "分册定稿仅限当前项目负责人或公司管理员办理。")
            return
        if not writable(state, project_id, identity):
            raise DomainError(403, "PROJECT_WRITER_REQUIRED", "当前公司角色和项目角色只允许查看，不能办理此操作。")
        name, _, resource_id = action.partition(":")
        if name in ("team.update", "project.update", "file.upload", "file.delete", "parse.run", "parse.confirm", "conflict.resolve") or name.startswith("sla."):
            require_lead(state, principal, project_id)
        elif name in ("chapter.plan.save", "chapter.plan.confirm", "chapter.assignment"):
            chapter = self.demo._chapter(state, principal, resource_id)
            if chapter.project_id != project_id:
                raise DomainError(404, "NOT_FOUND", "章节不属于当前项目。")
            if name == "chapter.assignment":
                if not chapter_structure(state, chapter, identity):
                    raise DomainError(403, "CHAPTER_STRUCTURE_REQUIRED", "只有项目负责人或本册负责人可以分配本节。")
            else:
                require_chapter(state, principal, chapter)
        elif name == "chapter.generate":
            chapters = [c for c in state.chapters.values() if c.project_id == project_id]
            selected = payload.get("chapter_ids")
            if selected is not None:
                known = {c.id for c in chapters}
                if not selected or len(selected) != len(set(selected)) or set(selected) - known:
                    raise DomainError(404, "NOT_FOUND", "所选章节不存在或不属于本项目。")
                chapters = [c for c in chapters if c.id in selected]
            for chapter in chapters:
                require_chapter(state, principal, chapter)
        elif name == "plan.confirm":
            scope = payload.get("scope", "all")
            if scope == "all":
                require_lead(state, principal, project_id)
            elif not (lead(state, project_id, identity) or volume_owner(state, project_id, scope, identity)):
                raise DomainError(403, "VOLUME_OWNER_REQUIRED", "只能调整和批量确认自己负责的分册。")
        elif name in ("project.check", "project.export"):
            volume = payload.get("volume", "all")
            if volume == "all" or payload.get("kind") == "submission":
                require_lead(state, principal, project_id)
            elif not (lead(state, project_id, identity) or volume_owner(state, project_id, volume, identity)):
                raise DomainError(403, "VOLUME_OWNER_REQUIRED", "只能检查或导出自己负责的分册。")
        elif name == "fact.update":
            fact = self._workflow(state, project_id)["facts"].get(resource_id, {})
            if resource_id.startswith("sla:") or fact.get("required") or "status" in payload:
                require_lead(state, principal, project_id)
        elif name == "requirement.update":
            row = self._workflow(state, project_id)["requirements"].get(resource_id)
            if row is None:
                raise DomainError(404, "NOT_FOUND", "未找到本项目条款。")
            if set(payload) - {"response", "evidence_ids", "reason", "deviation_type", "deviation_reason"}:
                require_lead(state, principal, project_id)
            elif not lead(state, project_id, identity):
                chapter = state.chapters.get(row["chapter_id"] or "")
                if not (volume_owner(state, project_id, row["volume"], identity)
                        or chapter and chapter_edit(state, chapter, identity)):
                    raise DomainError(403, "MATRIX_RESPONSE_FORBIDDEN", "只能填写本人负责分册或章节的响应和证据。")

    def _chapter_summary(self, state: DemoState, workflow: dict, chapter: Chapter, user_id=None) -> dict:
        active = chapter.lock and chapter.lock.expires_at > self.demo._now()
        candidate = workflow["candidates"].get(chapter.id)
        if candidate:
            candidate = {**candidate, "status": "valid" if candidate.get("input_fingerprint") == self._fingerprint(state, chapter.project_id) else "stale"}
        return {**self.demo._summary(chapter), "content": chapter.content,
                "lock": {"owner_id": chapter.lock.owner_id, "expires_at": iso_time(chapter.lock.expires_at)} if active else None,
                "candidate": candidate, "writing_input": {**chapter_plan(workflow, chapter.id), "is_current": plan_is_current(state, chapter.project_id, chapter.id)},
                "assignee_id": chapter.assignee_id,
                "assignee_name": state.accounts[chapter.assignee_id].name if chapter.assignee_id in state.accounts else None,
                "permissions": chapter_permissions(state, chapter, user_id) if user_id else {},
                "requirement_ids": [r["id"] for r in workflow["requirements"].values() if r["chapter_id"] == chapter.id]}

    def _fingerprint(self, state: DemoState, project_id: str) -> str:
        return project_input_fingerprint(state, project_id)

    def _public_check(self, state: DemoState, project_id: str, check: dict) -> dict:
        result = dict(check)
        if check["fingerprint"] != self._fingerprint(state, project_id):
            result["status"] = "stale"
        return result

    def _public_export(self, state: DemoState, project_id: str, record: dict) -> dict:
        return {k: v for k, v in record.items() if k != "documents"} | {
            "status": "valid" if record["fingerprint"] == self._fingerprint(state, project_id) else "stale"}

    @staticmethod
    def _public_file(record: dict) -> dict:
        return {key: value for key, value in record.items() if key not in ("content", "pages")}

    def workspace(self, principal: Principal, project_id: str) -> dict:
        state = self.repository.read()
        project = self.demo._project(state, principal, project_id)
        workflow = self._workflow(state, project_id)
        chapters = [self._chapter_summary(state, workflow, c, principal.user.id) for c in self._ordered_chapters(state, project_id, workflow)]
        stage = ("exported" if any(e["fingerprint"] == self._fingerprint(state, project_id) for e in workflow["exports"].values()) else "writing" if plan_is_current(state, project_id) else
                 "matrix" if workflow["parse_confirmed"] else "review" if workflow["requirements"] else "upload")
        return {"revision": project.revision, "input_fingerprint": self._fingerprint(state, project_id),
                "project": asdict(project), "stage": stage,
                "files": [self._public_file(f) for f in workflow["files"].values()],
                "requirements": [{**row, "permissions": {"edit": lead(state, project_id, principal.user.id),
                                   "route": lead(state, project_id, principal.user.id),
                                   "response": lead(state, project_id, principal.user.id) or volume_owner(state, project_id, row["volume"], principal.user.id)
                                   or bool(row["chapter_id"] in state.chapters and chapter_edit(state, state.chapters[row["chapter_id"]], principal.user.id))}}
                                 for row in workflow["requirements"].values()], "facts": project_facts(state, project_id),
                "conflicts": list(workflow["conflicts"].values()), "chapters": chapters,
                "checks": [self._public_check(state, project_id, c) for c in workflow["checks"].values()],
                "exports": [self._public_export(state, project_id, e) for e in workflow["exports"].values()],
                "jobs": [j for j in state.jobs.values() if j["project_id"] == project_id],
                "parse_confirmed": workflow["parse_confirmed"], "plan_confirmed": workflow["parse_confirmed"] and plan_is_current(state, project_id),
                "writing_plan": public_plan(workflow, state, project_id),
                "team": public_team(state, project_id, principal.user.id), "permissions": project_permissions(state, project_id, principal.user.id),
                "sla": public_sla(state, project_id)}

    def writing_input(self, principal, project_id, chapter_id):
        state = self.repository.read()
        self.demo._project(state, principal, project_id)
        chapter = self.demo._chapter(state, principal, chapter_id)
        if chapter.project_id != project_id:
            raise DomainError(404, "NOT_FOUND", "章节不属于当前项目。")
        return build_generation_context(state, project_id, chapter, self.demo._now(),
                                        evidence_service=self.demo.evidence_service)

    def chapter_edit_detail(self, principal: Principal, project_id: str, chapter_id: str) -> dict[str, Any]:
        """获取编辑台所需的章节详情、段落结构、持锁人与权限元数据。"""
        import time
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

        # 3. 章节编号与大纲类型
        chapter_number = meta.get("section_number") or meta.get("chapter_number")
        if not chapter_number:
            chapters_in_proj = [c for c in state.chapters.values() if c.project_id == project_id]
            order_map = {cid: idx for idx, cid in enumerate(workflow.get("chapter_order", []))}
            chapters_in_proj.sort(key=lambda c: order_map.get(c.id, len(order_map)))
            try:
                idx = [c.id for c in chapters_in_proj].index(chapter.id)
                chapter_number = f"{idx + 1}.0"
            except ValueError:
                chapter_number = "1.0"

        from icg.domain.outline_plan import infer_chapter_type
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

        from icg.domain.project_access import chapter_edit, chapter_permissions
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

    def patch_project(self, principal, project_id, payload, expected, key):
        def operation(state, project, workflow):
            partners = payload.pop("project_partners", None)
            if partners is not None:
                state.project_partners[project.id] = partners
            for field, value in payload.items():
                if value is None:
                    raise DomainError(422, "INVALID_PROJECT_FIELD", "项目字段不能设为空值，请使用空字符串清空文本。")
                if field == "name" and not value.strip():
                    raise DomainError(422, "INVALID_PROJECT_NAME", "项目名称不能为空。")
                if field == "deadline" and value:
                    self._date(value)
                setattr(project, field, value.strip() if isinstance(value, str) else value)
            return {"project": asdict(project)}
        return self._write(principal, project_id, "project.update", payload, expected, key, operation)

    def _job(self, state, project_id, kind, message, error=None) -> dict:
        now = iso_time(self.demo._now())
        job = {"id": new_id("job"), "project_id": project_id, "type": kind,
               "status": "failed" if error else "completed", "progress": 100,
               "message": message, "created_at": now, "completed_at": now, "error": error,
               "recoverable": False}
        state.jobs[job["id"]] = job
        return job

    def upload(self, principal, project_id, payload, expected, key):
        filename = payload["filename"]
        if filename != PurePosixPath(filename.replace("\\", "/")).name or any(c in filename for c in '\r\n\x00'):
            raise DomainError(422, "INVALID_FILENAME", "请提供文件名，不包含目录或控制字符。")
        suffix = PurePosixPath(filename).suffix.lower()
        if suffix not in (".txt", ".md", ".docx", ".pdf"):
            raise DomainError(422, "FILE_TYPE_UNSUPPORTED", "当前可上传文本、DOCX 与 PDF。")
        try:
            content = base64.b64decode(payload["content_base64"], validate=True)
        except (binascii.Error, ValueError) as error:
            raise DomainError(422, "INVALID_FILE_ENCODING", "文件编码不正确，请重新选择文件。") from error
        if not content or len(content) > self.MAX_UPLOAD:
            raise DomainError(413, "FILE_SIZE_LIMIT", "文件须有内容且不超过 5MB。")
        def operation(state, project, workflow):
            identity = new_id("file")
            media_type = DOCX_MEDIA_TYPE if suffix == ".docx" else "application/pdf" if suffix == ".pdf" else "text/plain; charset=utf-8"
            record = {"id": identity, "filename": filename, "size": len(content),
                      "sha256": hashlib.sha256(content).hexdigest(), "media_type": media_type,
                      "status": "uploaded", "page_count": 0, "pagination": "not_parsed", "warnings": [],
                      "download_url": f"/api/v1/projects/{project_id}/files/{identity}",
                      "content": content, "pages": []}
            workflow["files"][identity] = record
            workflow["parse_confirmed"] = False
            workflow["plan_confirmed"] = False
            job = self._job(state, project_id, "upload", "原件已保存到演示内存，尚未解析。")
            return {"file": self._public_file(record), "job": job}
        return self._write(principal, project_id, "file.upload", payload, expected, key, operation)

    def file(self, principal, project_id, file_id, *, preview=False):
        state = self.repository.read()
        self.demo._project(state, principal, project_id)
        record = self._workflow(state, project_id)["files"].get(file_id)
        if record is None:
            raise DomainError(404, "NOT_FOUND", "未找到有权访问的文件。")
        if preview:
            if record["status"] != "parsed":
                raise DomainError(409, "FILE_NOT_PARSED", "文件尚未成功解析，暂时没有原文预览。")
            return {"file_id": record["id"], "filename": record["filename"], "pagination": record["pagination"],
                    "warnings": record["warnings"], "pages": [{"page": i + 1, "text": t} for i, t in enumerate(record["pages"])]}
        return record

    def delete_file(self, principal, project_id, file_id, payload, expected, key):
        reason = payload["reason"].strip()
        if not reason:
            raise DomainError(422, "REASON_REQUIRED", "移除无法解析或误传文件必须填写理由。")

        def operation(state, project, workflow):
            record = workflow["files"].get(file_id)
            if record is None:
                raise DomainError(404, "NOT_FOUND", "未找到本项目文件。")
            referenced = any(item["source"]["file_id"] == file_id
                             for collection in (workflow["requirements"], workflow["facts"])
                             for item in collection.values())
            if record["status"] not in ("uploaded", "failed") or referenced:
                raise DomainError(409, "FILE_IN_USE", "已有解析结果或条款来源的文件不能移除。")
            del workflow["files"][file_id]
            workflow["parse_confirmed"] = False
            workflow["plan_confirmed"] = False
            return {"deleted_file_id": file_id}

        # 解析适配器在事务外运行；文件移除会增加项目版本，旧解析快照无法写回。
        return self._write(principal, project_id, "file.delete:" + file_id, payload, expected, key,
                           operation, {"file_id": file_id, "reason": reason})

    def parse(self, principal, project_id, payload, expected, key):
        initial, previous = self._preflight(principal, project_id, "parse.run", payload, expected, key)
        if previous:
            return previous
        workflow = self._workflow(initial, project_id)
        selected = payload.get("file_ids")
        selected = list(workflow["files"]) if selected is None else selected
        if not selected or len(selected) != len(set(selected)):
            raise DomainError(422, "FILES_REQUIRED", "请选择至少一份未重复的招标文件。")
        if any(identity not in workflow["files"] for identity in selected):
            raise DomainError(404, "NOT_FOUND", "所选文件不存在或不属于本项目。")
        parsed, errors = {}, {}
        for identity in selected:
            record = workflow["files"][identity]
            try:
                result = self.parser.parse(record["filename"], record["content"])
                parsed[identity] = result
            except DomainError as error:
                errors[identity] = error
            except Exception:
                errors[identity] = DomainError(502, "PARSER_UNAVAILABLE", "解析适配器失败，原件仍保留。")

        def operation(state, project, actual):
            actual["parse_confirmed"] = False
            actual["plan_confirmed"] = False
            if errors:
                for identity, error in errors.items():
                    actual["files"][identity]["status"] = "failed"
                    actual["files"][identity]["warnings"] = [error.message]
                first = next(iter(errors.values()))
                job = self._job(state, project_id, "parse", "解析未完成，请根据错误重新提供文件。",
                                {"code": first.code, "message": first.message})
                return {"job": job}
            for identity, result in parsed.items():
                record = actual["files"][identity]
                record.update(status="parsed", page_count=len(result.pages), pagination=result.pagination,
                              pages=result.pages, warnings=result.warnings)
                existing = {(r["source"]["file_id"], r["source"]["page"], r["source"]["quote"])
                            for r in actual["requirements"].values()}
                existing_facts = {(f["key"], f["value"], f["source"]["file_id"], f["source"]["page"])
                                  for f in actual["facts"].values()}
                for page, text in enumerate(result.pages, start=1):
                    for raw in text.splitlines():
                        line = raw.strip()
                        if not line:
                            continue
                        source = {"file_id": identity, "page": page, "quote": line}
                        match = re.match(r"^(招标编号|投标截止时间|服务期限|采购人|项目名称|服务地点|响应时间)\s*[:：]\s*(.+)$", line)
                        if match:
                            fact_key, value = match.groups()
                            fact_key_tuple = (fact_key, value, identity, page)
                            if fact_key_tuple not in existing_facts:
                                fact = {"id": new_id("fact"), "key": fact_key, "value": value,
                                        "status": "pending", "reason": "", "source": source}
                                actual["facts"][fact["id"]] = fact
                                existing_facts.add(fact_key_tuple)
                            continue
                        if line.startswith(("合成招标文件", "招标文件：", "招标文件:")):
                            continue
                        source_key = (identity, page, line)
                        if source_key in existing:
                            continue
                        business = any(word in line for word in ("商务", "资质", "报价", "业绩", "授权", "证书"))
                        references = re.findall(r"(?:见|详见|参照)(?:附件|第)[^，。；\n]{0,40}", line)
                        requirement = {"id": new_id("req"), "text": line,
                                       "category": "mandatory" if "★" in line or "废标" in line or "必须" in line else "business" if business else "technical",
                                       "volume": "business" if business else "technical", "chapter_id": None,
                                       "status": "pending", "response": "", "reason": "", "evidence_ids": [],
                                       "source": source, "references": references,
                                       "reference_status": "unresolved" if references else "none"}
                        actual["requirements"][requirement["id"]] = requirement
                        existing.add(source_key)
            groups = {}
            for fact in actual["facts"].values():
                groups.setdefault(fact["key"], []).append(fact)
            for fact_key, group in groups.items():
                if len({f["value"] for f in group}) > 1:
                    previous = next((c for c in actual["conflicts"].values() if c["key"] == fact_key), None)
                    ids = [f["id"] for f in group]
                    if previous is None:
                        conflict = {"id": new_id("conflict"), "key": fact_key, "fact_ids": ids,
                                    "selected_fact_id": None, "status": "pending", "reason": ""}
                        actual["conflicts"][conflict["id"]] = conflict
                    elif set(previous["fact_ids"]) != set(ids):
                        previous.update(fact_ids=ids, selected_fact_id=None, status="pending", reason="")
            job = self._job(state, project_id, "parse", "真实文字提取完成；条款、事实及引用仍需人工核对。")
            return {"job": job, "requirements": list(actual["requirements"].values()),
                    "facts": list(actual["facts"].values()), "conflicts": list(actual["conflicts"].values())}
        result = self._write(principal, project_id, "parse.run", payload, expected, key, operation)
        if result["job"]["status"] == "failed":
            from icg.domain.errors import status_for
            error = result["job"]["error"]
            raise DomainError(status_for(error["code"]), error["code"], error["message"],
                              {"job_id": result["job"]["id"], "revision": result["revision"]})
        return result

    def patch_requirement(self, principal, project_id, requirement_id, payload, expected, key):
        def operation(state, project, workflow):
            requirement = workflow["requirements"].get(requirement_id)
            if requirement is None:
                raise DomainError(404, "NOT_FOUND", "未找到本项目条款。")
            if any(v is None and k != "chapter_id" for k, v in payload.items()):
                raise DomainError(422, "INVALID_REQUIREMENT", "条款字段不能设为空值。")
            if payload.get("text") is not None and not payload["text"].strip():
                raise DomainError(422, "EMPTY_REQUIREMENT", "条款原文不能为空。")
            chapter_id = payload.get("chapter_id", requirement["chapter_id"])
            volume = payload.get("volume", requirement["volume"])
            if chapter_id:
                chapter = self.demo._chapter(state, principal, chapter_id)
                if chapter.project_id != project_id or chapter.volume != volume:
                    raise DomainError(409, "CHAPTER_VOLUME_MISMATCH", "条款只能映射到本项目同分册章节。")
            for evidence_id in payload.get("evidence_ids", requirement["evidence_ids"]):
                evidence = state.library.get(evidence_id)
                if evidence is None or evidence["company_id"] != principal.user.company_id:
                    raise DomainError(404, "NOT_FOUND", "证据不存在或不属于当前公司。")
                if evidence["type"] == "history" or evidence["status"] != "confirmed":
                    raise DomainError(409, "EVIDENCE_NOT_USABLE", "历史标书仅可参考；其他证据必须先确认。")
                self._reject_unusable_mount(state, principal, project, evidence)
            if "evidence_ids" in payload and len(payload["evidence_ids"]) != len(set(payload["evidence_ids"])):
                raise DomainError(422, "DUPLICATE_EVIDENCE", "同一证据不能重复挂接。")
            updated = {**requirement, **payload}
            if requirement["category"] == "sla" or payload.get("category") == "sla":
                updated["sla_required"] = True
            text_changed = "text" in payload and payload["text"] != requirement["text"]
            if text_changed:
                # 新原文不能继承旧引用的人工确认，也不能同一次改字时顺便假确认。
                references = re.findall(r"(?:见|详见|参照)(?:附件|第)[^，。；\n]{0,40}", updated["text"])
                updated.update(references=references, reference_status="unresolved" if references else "none",
                               status="pending", reason="")
            if updated["status"] == "rejected" and not updated["reason"].strip():
                raise DomainError(422, "REASON_REQUIRED", "忽略条款必须填写理由。")
            if updated["reference_status"] == "unresolved" and updated["status"] == "confirmed":
                if not updated["reason"].strip():
                    raise DomainError(409, "REFERENCE_REASON_REQUIRED", "存在未解析交叉引用，请在理由中写明人工核对结果。")
                updated["reference_status"] = "resolved"
            if text_changed or any(k in payload and payload[k] != requirement[k] for k in ("category", "volume", "status")):
                workflow["parse_confirmed"] = False
                workflow["plan_confirmed"] = False
            if any(k in payload and payload[k] != requirement[k] for k in ("chapter_id", "response", "evidence_ids")):
                workflow["plan_confirmed"] = False
            requirement.update(updated)
            return {"requirement": requirement}
        return self._write(principal, project_id, "requirement.update:" + requirement_id, payload, expected, key, operation)

    def patch_fact(self, principal, project_id, fact_id, payload, expected, key):
        def operation(state, project, workflow):
            if fact_id.startswith("sla:"):
                return self.sla.confirm_fact(state, principal, project_id, workflow, fact_id[4:], payload)
            fact = workflow["facts"].get(fact_id)
            if fact is None:
                raise DomainError(404, "NOT_FOUND", "未找到本项目事实。")
            if fact.get("required") and principal.user.role != "manager":
                raise DomainError(403, "FACT_MANAGER_REQUIRED", "必备事实的维护和确认仅限本公司项目负责人。")
            if any(v is None for v in payload.values()):
                raise DomainError(422, "INVALID_FACT", "事实字段不能设为空值。")
            updated = {**fact, **payload}
            if not lead(state, project_id, principal.user.id) and "value" in payload and payload["value"] != fact["value"]:
                updated["status"] = "pending"
            if not updated["value"].strip():
                raise DomainError(422, "EMPTY_FACT", "事实取值不能为空。")
            if updated["status"] == "rejected" and not updated["reason"].strip():
                raise DomainError(422, "REASON_REQUIRED", "忽略事实必须填写理由。")
            for conflict in workflow["conflicts"].values():
                if fact_id in conflict["fact_ids"] and any(k in payload and payload[k] != fact[k] for k in ("value", "status")):
                    conflict.update(status="pending", selected_fact_id=None, reason="")
            fact.update(updated)
            workflow["plan_confirmed"] = False
            return {"fact": fact}
        return self._write(principal, project_id, "fact.update:" + fact_id, payload, expected, key, operation)

    def resolve_conflict(self, principal, project_id, conflict_id, payload, expected, key):
        def operation(state, project, workflow):
            conflict = workflow["conflicts"].get(conflict_id)
            if conflict is None:
                raise DomainError(404, "NOT_FOUND", "未找到本项目冲突。")
            selected = payload["selected_fact_id"]
            if selected not in conflict["fact_ids"]:
                raise DomainError(409, "INVALID_CONFLICT_SELECTION", "只能选择本冲突中的事实取值。")
            if not payload["reason"].strip():
                raise DomainError(422, "REASON_REQUIRED", "选择冲突取值必须说明依据。")
            conflict.update(selected_fact_id=selected, reason=payload["reason"].strip(), status="resolved")
            for fact_id in conflict["fact_ids"]:
                workflow["facts"][fact_id].update(status="confirmed" if fact_id == selected else "rejected", reason=payload["reason"].strip())
            workflow["parse_confirmed"] = False
            workflow["plan_confirmed"] = False
            return {"conflict": conflict, "facts": list(workflow["facts"].values())}
        return self._write(principal, project_id, "conflict.resolve:" + conflict_id, payload, expected, key, operation)

    def confirm_parse(self, principal, project_id, payload, expected, key):
        def operation(state, project, workflow):
            if not workflow["files"] or any(f["status"] != "parsed" for f in workflow["files"].values()):
                raise DomainError(409, "PARSE_INCOMPLETE", "所有上传文件必须成功解析后才能确认。")
            if not workflow["requirements"]:
                raise DomainError(409, "REQUIREMENTS_EMPTY", "没有招标条款，不能确认解析。")
            if any(r["status"] == "pending" for r in workflow["requirements"].values()) or any(f["status"] == "pending" for f in workflow["facts"].values()):
                raise DomainError(409, "REVIEW_PENDING", "请先逐条确认或填写理由忽略全部条款和事实。")
            if not any(r["status"] == "confirmed" for r in workflow["requirements"].values()):
                raise DomainError(409, "CONFIRMED_REQUIREMENTS_EMPTY", "至少需要一条已确认条款。")
            if any(c["status"] != "resolved" for c in workflow["conflicts"].values()):
                raise DomainError(409, "CONFLICTS_PENDING", "存在事实冲突，请先选择有效取值并填写依据。")
            for conflict in workflow["conflicts"].values():
                selected = conflict["selected_fact_id"]
                if (selected not in conflict["fact_ids"]
                        or workflow["facts"].get(selected, {}).get("status") != "confirmed"
                        or any(workflow["facts"].get(identity, {}).get("status") != "rejected"
                               for identity in conflict["fact_ids"] if identity != selected)):
                    raise DomainError(409, "CONFLICT_SELECTION_INVALID", "冲突必须有且只有一个确认取值，其余候选需忽略。")
            workflow["parse_confirmed"] = True
            return {"parse_confirmed": True}
        return self._write(principal, project_id, "parse.confirm", payload, expected, key, operation)

    def jobs(self, principal):
        state = self.repository.read()
        allowed = {p.id for p in state.projects.values() if p.company_id == principal.user.company_id
                   and principal.user.id in state.project_teams.get(p.id, {}).get("members", {})}
        return {"jobs": [j for j in state.jobs.values() if j["project_id"] in allowed]}

    @staticmethod
    def _public_library(item):
        public = {"reason": "", "source_tier": "own", "is_restricted": False, "is_long_term": False,
                  "valid_to": None, "partner_entity_id": None, **item,
                  "usable_as_evidence": item["status"] == "confirmed" and item["type"] != "history"}
        public.pop("acl_user_ids", None)
        public.pop("restricted", None)
        return public

    @staticmethod
    def _replace_library_acl(state, company_id, evidence_id, user_ids):
        state.resource_acl = [row for row in state.resource_acl
                              if not (row["ref_type"] == "library" and row["ref_id"] == evidence_id)]
        seen = set()
        for user_id in user_ids:
            if user_id in seen:
                continue
            seen.add(user_id)
            account = state.accounts.get(user_id)
            if account is None or account.company_id != company_id:
                raise DomainError(422, "INVALID_LIBRARY_FIELD", "授权用户必须属于本公司。")
            state.resource_acl.append({"ref_type": "library", "ref_id": evidence_id,
                                       "user_id": user_id, "company_id": company_id})

    @staticmethod
    def _agreement_present(state, project_id, evidence):
        partner_id = evidence.get("partner_entity_id")
        if not partner_id:
            return False
        for row in state.project_partners.get(project_id, []):
            if row.get("partner_entity_id") == partner_id and str(row.get("agreement_attachment_id") or "").strip():
                return True
        return False

    @staticmethod
    def _restricted_allowed(state, principal, evidence):
        if principal.user.role in ("company_admin", "data_admin"):
            return True
        company_id = principal.user.company_id
        return any(row["ref_type"] == "library" and row["ref_id"] == evidence["id"]
                   and row["user_id"] == principal.user.id and row["company_id"] == company_id
                   for row in state.resource_acl)

    def _reject_unusable_mount(self, state, principal, project, evidence):
        if evidence.get("is_restricted") and not self._restricted_allowed(state, principal, evidence):
            raise DomainError(403, "FORBIDDEN", "受限资料需公司管理员、资料管理员或资源授权后才能挂接。")
        if evidence.get("source_tier") == "reference":
            raise DomainError(409, "EVIDENCE_NOT_USABLE", "仅供参考资料不能作为投标证据挂接。")
        if evidence.get("source_tier") == "partner" and not self._agreement_present(state, project.id, evidence):
            raise DomainError(409, "EVIDENCE_NOT_USABLE", "合作方资料缺协议，不能作为投标证据挂接。")
        if evidence_expired(evidence, project.deadline):
            raise DomainError(409, "EVIDENCE_EXPIRED", "证据不能覆盖投标截止时间。")

    def library(self, principal):
        state = self.repository.read()
        return {"revision": state.library_revisions.get(principal.user.company_id, 1),
                "items": [self._public_library(item) for item in state.library.values() if item["company_id"] == principal.user.company_id]}

    def write_library(self, principal, payload, expected, key, item_id=None):
        from icg.domain.idempotency import lookup, remember
        self.demo._writer(principal)
        key = self._idempotency(key)
        company = principal.user.company_id
        scope_id = "library:" + company
        action = "library.update:" + item_id if item_id else "library.create"
        request_fingerprint = self._request_hash(action, payload, expected)
        def operation(state):
            revision = state.library_revisions.get(company, 1)
            replay = lookup(state, scope_id, principal.user.id, key, request_fingerprint, self.demo._now())
            if replay is not None:
                return replay
            self._version(revision, expected)
            for date_key in ("valid_until", "valid_to"):
                if payload.get(date_key):
                    if len(payload[date_key]) != 10:
                        raise DomainError(422, "INVALID_DATE", "资料有效期请使用 YYYY-MM-DD。")
                    self._date(payload[date_key])
            replace_acl = "acl_user_ids" in payload
            acl_user_ids = payload.pop("acl_user_ids", None)
            if any(v is None and k not in ("valid_until", "valid_to", "partner_entity_id") for k, v in payload.items()):
                raise DomainError(422, "INVALID_LIBRARY_FIELD", "资料字段不能设为空值。")
            if any(k in payload and not payload[k].strip() for k in ("name", "content")):
                raise DomainError(422, "EMPTY_LIBRARY_FIELD", "资料名称和正文不能为空。")
            if item_id:
                item = state.library.get(item_id)
                if item is None or item["company_id"] != company:
                    raise DomainError(404, "NOT_FOUND", "未找到本公司资料。")
                updated_fields = dict(payload)
                changed = any(k in payload and payload[k] != item.get(k) for k in (
                    "name", "type", "content", "valid_until", "valid_to", "is_long_term",
                    "source_tier", "partner_entity_id", "is_restricted"))
                if changed:
                    if payload.get("status") == "confirmed":
                        if not payload.get("reason", "").strip():
                            raise DomainError(409, "REVIEW_REASON_REQUIRED", "资料实质内容已变化；重新确认时请填写本次核对依据。")
                    else:
                        updated_fields.update(status="pending", reason="")
                item.update(updated_fields)
                item["revision"] += 1
            else:
                item = {"id": new_id("evidence"), "company_id": company, **payload, "revision": 1}
                state.library[item["id"]] = item
            if replace_acl:
                self._replace_library_acl(state, company, item["id"], acl_user_ids or [])
            state.library_revisions[company] = revision + 1
            result = {"revision": revision + 1, "item": self._public_library(item)}
            remember(state, scope_id, principal.user.id, key, request_fingerprint, result, self.demo._now())
            # 资料变更使用同一仓储，旧检查通过内容指纹自动过期。
            return result
        return self.repository.transaction(operation)
