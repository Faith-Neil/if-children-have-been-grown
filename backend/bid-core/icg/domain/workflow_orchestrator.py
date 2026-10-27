# 为什么有这个文件：由原巨石 workflow.py 解耦收敛形成的高内聚工作流门面（Façade）（BE-TECH-DEBT-03）。
# 它解决什么问题：
# 1. 组合大纲编排（outline）、生成编排（generation）、合规检查编排（check）、导出编排（export/volume_finalize）、招标文件解析（tender）与企业资料库（library）领域子编排服务；
# 2. 统一管理工作流事务（_write）、前置校验（_preflight）、乐观锁与幂等机制，代码行数严格控制在 350 行以内；
# 3. 对外暴露 100% 行为与签名兼容的工作流门面。

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable

from icg.domain.domain import Chapter, DemoService, DemoState, DomainError, Principal, iso_time, new_id
from icg.domain.ports import ParserProvider
from icg.domain.input_snapshot import project_input_fingerprint
from icg.domain.sla import SlaService, public_sla
from icg.domain.generation_context import build_generation_context, chapter_plan, plan_is_current, project_facts, public_plan
from icg.domain.project_access import (
    VOLUMES, writable, lead, volume_owner, require_lead, require_chapter,
    chapter_structure, chapter_edit, chapter_permissions, project_permissions,
    public_team, normalize_role,
)
from icg.domain.outline_plan import OutlinePlanService
from icg.domain.answer_card import AnswerCardService
from icg.infra.tender_retrieval import TenderRetrievalService
from icg.domain.idempotency import lookup, remember

from icg.domain.outline_orchestrator import OutlineOrchestratorMixin, OutlineOrchestrator
from icg.domain.generation_orchestrator import GenerationOrchestratorMixin, GenerationOrchestrator
from icg.domain.check_orchestrator import CheckOrchestratorMixin, CheckOrchestrator
from icg.domain.export_service import ExportServiceMixin
from icg.domain.volume_finalize import VolumeFinalizeMixin
from icg.domain.tender_orchestrator import TenderOrchestratorMixin, TenderOrchestrator
from icg.domain.library_orchestrator import LibraryOrchestratorMixin, LibraryOrchestrator

SAMPLE_TENDER: bytes = b""


def _blank_workflow() -> dict:
    return {
        "files": {},
        "requirements": {},
        "facts": {},
        "conflicts": {},
        "candidates": {},
        "checks": {},
        "exports": {},
        "parse_confirmed": False,
        "plan_confirmed": False,
        "chapter_order": [],
        "sla": None,
        "sla_commitments": {},
        "writing_plan": {},
    }


class WorkflowService(
    OutlineOrchestratorMixin,
    GenerationOrchestratorMixin,
    ExportServiceMixin,
    CheckOrchestratorMixin,
    VolumeFinalizeMixin,
    TenderOrchestratorMixin,
    LibraryOrchestratorMixin,
):
    """投标工作流统一领域门面服务。"""

    MAX_UPLOAD = 5 * 1024 * 1024
    IMPLEMENTED_RULES = [
        "parse-confirmation", "fact-conflicts", "matrix-completeness",
        "evidence-company-and-review", "evidence-validity", "committed-content",
        "pending-markers", "two-volumes", "input-fingerprint", "export-permission",
        "sla-values-and-capability-subset", "sla-variables-and-labelled-numbers-subset",
        "R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09", "R10",
        "R11", "R12", "R13", "R14", "R15", "R16", "R18", "R20", "R23", "R24",
        "R25", "R31", "R32", "R34", "R35", "R37",
    ]
    UNIMPLEMENTED_RULES = [
        "参考合规规则尚未逐条完成（按一期完整/一期简化/二期分组）", "语义事实与承诺核对",
        "公司全文查重", "结构化敏感变量", "交叉复核和完整分册定稿",
    ]

    def __init__(self, demo: DemoService, parser: ParserProvider):
        self.demo = demo
        self.repository = demo.repository
        self.parser = parser
        self.sla = SlaService(self)
        from icg.domain.project_team import ProjectTeamService
        self.team = ProjectTeamService(self)
        self.answer_card = AnswerCardService(demo)
        self.outline = OutlinePlanService(demo)
        self.tender_retrieval = TenderRetrievalService(demo)

        # 挂载独立领域编排服务实例，支持直接或通过门面调用
        self.outline_orchestrator = OutlineOrchestrator(self)
        self.generation_orchestrator = GenerationOrchestrator(self)
        self.check_orchestrator = CheckOrchestrator(self)
        self.tender_orchestrator = TenderOrchestrator(self)
        self.library_orchestrator = LibraryOrchestrator(self)

    @staticmethod
    def _workflow(state: DemoState, project_id: str, *, create: bool = False) -> dict:
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

    def _preflight(self, principal: Principal, project_id: str, action: str, payload: dict, expected: str | None, key: str | None):
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
        state.audit.append({
            "id": new_id("event"), "action": action, "actor_id": principal.user.id,
            "project_id": project_id, "chapter_id": "", "revision": state.projects[project_id].revision,
            "at": iso_time(self.demo._now()), "details": details or {},
        })

    def _write(self, principal: Principal, project_id: str, action: str, payload: dict,
               expected: str | None, key: str | None, operation: Callable, audit_details: dict | None = None) -> dict:
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

    def _job(self, state: DemoState, project_id: str, kind: str, message: str, error: dict | None = None) -> dict:
        now = iso_time(self.demo._now())
        job = {
            "id": new_id("job"), "project_id": project_id, "type": kind,
            "status": "failed" if error else "completed", "progress": 100,
            "message": message, "created_at": now, "completed_at": now, "error": error,
            "recoverable": False,
        }
        state.jobs[job["id"]] = job
        return job

    def workspace(self, principal: Principal, project_id: str) -> dict:
        state = self.repository.read()
        project = self.demo._project(state, principal, project_id)
        workflow = self._workflow(state, project_id)
        chapters = [self._chapter_summary(state, workflow, c, principal.user.id) for c in self._ordered_chapters(state, project_id, workflow)]
        stage = ("exported" if any(e["fingerprint"] == self._fingerprint(state, project_id) for e in workflow["exports"].values()) else "writing" if plan_is_current(state, project_id) else
                 "matrix" if workflow["parse_confirmed"] else "review" if workflow["requirements"] else "upload")
        return {
            "revision": project.revision, "input_fingerprint": self._fingerprint(state, project_id),
            "project": asdict(project), "stage": stage,
            "files": [self._public_file(f) for f in workflow["files"].values()],
            "requirements": [{**row, "permissions": {
                "edit": lead(state, project_id, principal.user.id),
                "route": lead(state, project_id, principal.user.id),
                "response": lead(state, project_id, principal.user.id) or volume_owner(state, project_id, row["volume"], principal.user.id)
                or bool(row["chapter_id"] in state.chapters and chapter_edit(state, state.chapters[row["chapter_id"]], principal.user.id)),
            }} for row in workflow["requirements"].values()],
            "facts": project_facts(state, project_id),
            "conflicts": list(workflow["conflicts"].values()),
            "chapters": chapters,
            "checks": [self._public_check(state, project_id, c) for c in workflow["checks"].values()],
            "exports": [self._public_export(state, project_id, e) for e in workflow["exports"].values()],
            "jobs": [j for j in state.jobs.values() if j["project_id"] == project_id],
            "parse_confirmed": workflow["parse_confirmed"],
            "plan_confirmed": workflow["parse_confirmed"] and plan_is_current(state, project_id),
            "writing_plan": public_plan(workflow, state, project_id),
            "team": public_team(state, project_id, principal.user.id),
            "permissions": project_permissions(state, project_id, principal.user.id),
            "sla": public_sla(state, project_id),
        }

    def patch_project(self, principal: Principal, project_id: str, payload: dict, expected: str | None, key: str | None):
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

    def writing_input(self, principal: Principal, project_id: str, chapter_id: str) -> dict:
        state = self.repository.read()
        self.demo._project(state, principal, project_id)
        chapter = self.demo._chapter(state, principal, chapter_id)
        if chapter.project_id != project_id:
            raise DomainError(404, "NOT_FOUND", "章节不属于当前项目。")
        return build_generation_context(
            state, project_id, chapter, self.demo._now(), evidence_service=self.demo.evidence_service
        )
