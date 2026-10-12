# 为什么有这个文件：把公司权限、编辑锁、草稿、版本和导出条件放在同一业务边界内。
# 它解决什么问题：确保每次写入都重新核对权限与版本，失败时不留下部分正文或审计。

from __future__ import annotations

import re

import hashlib
import json
import secrets
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from .ports import ModelProvider, Repository
from .input_snapshot import project_input_fingerprint


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def iso_time(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


class DomainError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        from .errors import status_for
        try:
            expected = status_for(code)
        except KeyError as error:
            raise ValueError(str(error)) from error
        if status != expected:
            raise ValueError(f"{code} 已冻结为 HTTP {expected}，不能返回 {status}")
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


@dataclass(frozen=True)
class Account:
    id: str
    name: str
    company_id: str
    role: str


@dataclass(frozen=True)
class Principal:
    user: Account
    session_token: str


@dataclass
class Project:
    id: str
    name: str
    company_id: str
    revision: int = 1
    tender_number: str = ""
    deadline: str = ""
    sensitive: bool = False


@dataclass
class Lease:
    token: str
    owner_id: str
    session_token: str
    expires_at: float


@dataclass
class Draft:
    sequence: int
    content: str
    base_revision: int
    input_fingerprint: str | None = None


@dataclass
class Chapter:
    id: str
    project_id: str
    title: str
    volume: str
    content: str
    revision: int = 1
    lock: Lease | None = None
    drafts: dict[str, Draft] = field(default_factory=dict)
    versions: list[dict] = field(default_factory=list)
    # 旧章节提交的回执已并入 DemoState.workflow_receipts。字段保留，避免已有内存对象缺属性。
    committed_requests: dict[tuple[str, str], dict] = field(default_factory=dict)
    assignee_id: str | None = None


@dataclass
class Check:
    id: str
    chapter_id: str
    passed: bool
    revision: int
    content_hash: str
    issues: list[dict]


@dataclass
class Export:
    id: str
    chapter_id: str
    revision: int
    content_hash: str
    check_id: str
    filename: str
    title: str
    content: str


@dataclass
class DemoState:
    accounts: dict[str, Account] = field(default_factory=dict)
    sessions: dict[str, str] = field(default_factory=dict)
    projects: dict[str, Project] = field(default_factory=dict)
    chapters: dict[str, Chapter] = field(default_factory=dict)
    checks: dict[str, Check] = field(default_factory=dict)
    exports: dict[str, Export] = field(default_factory=dict)
    audit: list[dict] = field(default_factory=list)
    # 工作流数据与旧章节共用一个事务边界，不使用独立的全局字典。
    workflows: dict[str, dict] = field(default_factory=dict)
    library: dict[str, dict] = field(default_factory=dict)
    sla_templates: dict[str, dict] = field(default_factory=dict)
    library_revisions: dict[str, int] = field(default_factory=dict)
    jobs: dict[str, dict] = field(default_factory=dict)
    workflow_receipts: dict[tuple[str, str, str], dict] = field(default_factory=dict)
    project_teams: dict[str, dict] = field(default_factory=dict)
    # 内存仓库仍按 2048 条裁剪回执。MySQL 路径在事务里把它设为 False，避免未过期回执被提前删掉。
    cap_receipts: bool = True


class DemoService:
    LEASE_SECONDS = 120

    def __init__(self, repository: Repository, model_provider: ModelProvider,
                 clock: Callable[[], float | datetime] | None = None):
        self.repository = repository
        self.model_provider = model_provider
        self.clock = clock or time.time

    def _now(self) -> float:
        value = self.clock()
        if isinstance(value, datetime):
            if value.tzinfo is None:
                raise ValueError("测试时钟的 datetime 必须包含时区")
            return value.timestamp()
        return float(value)

    def accounts(self) -> dict:
        state = self.repository.read()
        return {"accounts": [asdict(user) for user in state.accounts.values()]}

    def login(self, account_id: str) -> dict:
        def operation(state: DemoState):
            user = state.accounts.get(account_id)
            if user is None:
                raise DomainError(401, "INVALID_ACCOUNT", "请选择有效的合成演示账号。")
            token = secrets.token_urlsafe(32)
            state.sessions[token] = user.id
            return {"access_token": token, "token_type": "bearer", "user": asdict(user)}
        return self.repository.transaction(operation)

    def authenticate(self, token: str) -> Principal:
        state = self.repository.read()
        user = state.accounts.get(state.sessions.get(token, ""))
        if user is None:
            raise DomainError(401, "UNAUTHENTICATED", "请先选择演示账号登录。")
        return Principal(user, token)

    @staticmethod
    def _writer(principal: Principal) -> None:
        if principal.user.role not in ("editor", "manager"):
            raise DomainError(403, "FORBIDDEN", "当前演示账号只能查看，不能执行此操作。")

    @staticmethod
    def _project(state: DemoState, principal: Principal, project_id: str) -> Project:
        from .project_access import member
        project = state.projects.get(project_id)
        account = state.accounts.get(principal.user.id)
        if (project is None or account is None or project.company_id != account.company_id
                or state.sessions.get(principal.session_token) != account.id
                or member(state, project_id, account.id) is None):
            raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")
        return project

    @staticmethod
    def _legacy_flow_guard(state: DemoState, chapter: Chapter) -> None:
        workflow = state.workflows.get(chapter.project_id, {})
        # 接入原文/矩阵的项目一律走主流程；没有选模板也不能绕过尚未绑定的承诺。
        if (workflow.get("requirements") or workflow.get("sla")
                or any(re.search(r"\{\{\s*(?:sla|fact)\s*:", c.content)
                       for c in state.chapters.values() if c.project_id == chapter.project_id)):
            raise DomainError(409, "SLA_PROJECT_EXPORT_REQUIRED", "本项目已有招标要求或服务变量，请从主流程检查并导出两册。旧单章入口仅验证独立演示。")

    def _chapter(self, state: DemoState, principal: Principal, chapter_id: str) -> Chapter:
        chapter = state.chapters.get(chapter_id)
        if chapter is None:
            raise DomainError(404, "NOT_FOUND", "未找到有权访问的章节。")
        self._project(state, principal, chapter.project_id)
        return chapter

    def require_allowed_model(self, project: Project) -> None:
        if (project.sensitive and getattr(self.model_provider, "is_real_model", None) is not False
                and not getattr(self.model_provider, "is_local", False)):
            raise DomainError(409, "LOCAL_MODEL_REQUIRED", "敏感项目只能使用本地模型适配器。")

    def _audit(self, state: DemoState, principal: Principal, chapter: Chapter,
               action: str, details: dict | None = None) -> None:
        state.audit.append({"id": new_id("event"), "action": action,
                            "actor_id": principal.user.id, "chapter_id": chapter.id,
                            "revision": chapter.revision, "at": iso_time(self._now()),
                            "details": details or {}})

    @staticmethod
    def _summary(chapter: Chapter) -> dict:
        return {"id": chapter.id, "title": chapter.title,
                "volume": chapter.volume, "revision": chapter.revision}

    def projects(self, principal: Principal) -> dict:
        state = self.repository.read()
        from .project_access import member
        return {"projects": [asdict(project) for project in state.projects.values()
                             if project.company_id == principal.user.company_id
                             and member(state, project.id, principal.user.id)]}

    def create_project(self, principal: Principal, name: str) -> dict:
        def operation(state: DemoState):
            from .project_access import initial_team
            actual = state.accounts.get(principal.user.id)
            if actual is None or actual.role != "manager" or state.sessions.get(principal.session_token) != actual.id:
                raise DomainError(403, "PROJECT_CREATE_FORBIDDEN", "普通编写人不能新建项目，请由公司项目经理建立并邀请成员。")
            project = Project(new_id("project"), name, actual.company_id)
            state.projects[project.id] = project
            state.project_teams[project.id] = initial_team(principal.user.id)
            for volume, title in (("technical", "技术方案"), ("business", "商务响应")):
                chapter = Chapter(new_id("chapter"), project.id, title, volume, "")
                chapter.versions.append({"revision": 1, "content": "",
                                         "actor_id": principal.user.id,
                                         "created_at": iso_time(self._now())})
                state.chapters[chapter.id] = chapter
                self._audit(state, principal, chapter, "project.create")
            return asdict(project)
        return self.repository.transaction(operation)

    def chapters(self, principal: Principal, project_id: str) -> dict:
        state = self.repository.read()
        self._project(state, principal, project_id)
        return {"chapters": [self._summary(chapter) for chapter in state.chapters.values()
                             if chapter.project_id == project_id]}

    def chapter(self, principal: Principal, chapter_id: str) -> dict:
        state = self.repository.read()
        chapter = self._chapter(state, principal, chapter_id)
        active_lock = chapter.lock and chapter.lock.expires_at > self._now()
        lock = ({"owner_id": chapter.lock.owner_id,
                 "expires_at": iso_time(chapter.lock.expires_at)} if active_lock else None)
        draft = chapter.drafts.get(principal.user.id)
        from .project_access import chapter_permissions
        return {**self._summary(chapter), "project_id": chapter.project_id,
                "content": chapter.content, "lock": lock,
                "draft": asdict(draft) if draft else None, "assignee_id": chapter.assignee_id,
                "permissions": chapter_permissions(state, chapter, principal.user.id)}

    @staticmethod
    def _chapter_writer(state, principal, chapter):
        from .project_access import require_chapter
        require_chapter(state, principal, chapter)

    def _lease(self, chapter: Chapter, principal: Principal, token: str) -> Lease:
        lease = chapter.lock
        if (lease is None or lease.expires_at <= self._now()
                or lease.token != token or lease.owner_id != principal.user.id
                or lease.session_token != principal.session_token):
            raise DomainError(423, "LOCK_LOST", "编辑权已失效，请重新取得编辑权后再操作。")
        return lease

    @staticmethod
    def _revision(chapter: Chapter, base_revision: int) -> None:
        if chapter.revision != base_revision:
            raise DomainError(409, "REVISION_CONFLICT", "章节已更新，请刷新并核对最新版本。")

    @staticmethod
    def _lease_response(lease: Lease) -> dict:
        return {"lease_token": lease.token, "expires_at": iso_time(lease.expires_at),
                "owner_id": lease.owner_id}

    def acquire_lock(self, principal: Principal, chapter_id: str,
                     takeover_reason: str | None) -> dict:
        def operation(state: DemoState):
            chapter = self._chapter(state, principal, chapter_id)
            self._chapter_writer(state, principal, chapter)
            old_lease = chapter.lock
            active = old_lease is not None and old_lease.expires_at > self._now()
            if active and old_lease.owner_id == principal.user.id \
                    and old_lease.session_token == principal.session_token:
                return self._lease_response(old_lease)
            if active:
                from .project_access import chapter_structure
                if not chapter_structure(state, chapter, principal.user.id):
                    if takeover_reason is not None:
                        raise DomainError(403, "FORBIDDEN", "普通编写人没有接管其他会话的权限。")
                    raise DomainError(423, "LOCK_HELD", "其他会话正在编辑；项目负责人或本册负责人可以填写理由接管。")
                if not takeover_reason or not takeover_reason.strip():
                    raise DomainError(409, "TAKEOVER_REASON_REQUIRED", "接管前必须填写理由。")
            lease = Lease(secrets.token_urlsafe(32), principal.user.id,
                          principal.session_token, self._now() + self.LEASE_SECONDS)
            chapter.lock = lease
            details = ({"reason": takeover_reason.strip(), "previous_owner_id": old_lease.owner_id}
                       if active else {})
            self._audit(state, principal, chapter, "lock.takeover" if active else "lock.acquire", details)
            # 接管时保留旧用户已经收到的草稿，不宣称保存了断网设备尚未上传的文字。
            return self._lease_response(lease)
        return self.repository.transaction(operation)

    def renew_lock(self, principal: Principal, chapter_id: str, lease_token: str) -> dict:
        def operation(state: DemoState):
            chapter = self._chapter(state, principal, chapter_id)
            self._chapter_writer(state, principal, chapter)
            lease = self._lease(chapter, principal, lease_token)
            lease.expires_at = self._now() + self.LEASE_SECONDS
            self._audit(state, principal, chapter, "lock.renew")
            return self._lease_response(lease)
        return self.repository.transaction(operation)

    def release_lock(self, principal: Principal, chapter_id: str, lease_token: str) -> dict:
        def operation(state: DemoState):
            chapter = self._chapter(state, principal, chapter_id)
            self._chapter_writer(state, principal, chapter)
            self._lease(chapter, principal, lease_token)
            chapter.lock = None
            self._audit(state, principal, chapter, "lock.release")
            return {"released": True}
        return self.repository.transaction(operation)

    def save_draft(self, principal: Principal, chapter_id: str, lease_token: str,
                   base_revision: int, sequence: int, content: str, input_fingerprint: str | None = None) -> dict:
        def operation(state: DemoState):
            chapter = self._chapter(state, principal, chapter_id)
            self._chapter_writer(state, principal, chapter)
            self._lease(chapter, principal, lease_token)
            self._revision(chapter, base_revision)
            self._writing_input(state, chapter, input_fingerprint)
            old = chapter.drafts.get(principal.user.id)
            if old and old.base_revision == base_revision and sequence <= old.sequence:
                raise DomainError(409, "DRAFT_SEQUENCE_CONFLICT", "较旧的草稿请求不能覆盖较新的草稿。")
            draft = Draft(sequence, content, base_revision, input_fingerprint)
            chapter.drafts[principal.user.id] = draft
            self._audit(state, principal, chapter, "draft.save", {"sequence": sequence})
            return asdict(draft)
        return self.repository.transaction(operation)

    def commit_version(self, principal: Principal, chapter_id: str, lease_token: str,
                       base_revision: int, content: str, idempotency_key: str,
                       input_fingerprint: str | None = None, *, header_key: str | None = None) -> dict:
        # 旧接口保留正文 idempotency_key。存储规则与 /api/v1 相同：项目+用户+标记、24 小时、失败不登记。
        from .idempotency import fingerprint, lookup, remember, resolve_legacy_key
        key = resolve_legacy_key(idempotency_key, header_key)
        payload = {"lease_token": lease_token, "base_revision": base_revision, "content": content,
                   "input_fingerprint": input_fingerprint}
        action = "chapter.version.commit:" + chapter_id
        request_fingerprint = fingerprint(action, payload, None)

        def operation(state: DemoState):
            chapter = self._chapter(state, principal, chapter_id)
            self._chapter_writer(state, principal, chapter)
            self._lease(chapter, principal, lease_token)
            previous = lookup(state, chapter.project_id, principal.user.id, key, request_fingerprint, self._now())
            if previous is not None:
                return previous
            self._revision(chapter, base_revision)
            self._writing_input(state, chapter, input_fingerprint)
            chapter.content = content
            chapter.revision += 1
            state.projects[chapter.project_id].revision += 1
            result = {"revision": chapter.revision, "content": chapter.content}
            chapter.versions.append({**result, "actor_id": principal.user.id,
                                     "created_at": iso_time(self._now())})
            chapter.drafts.pop(principal.user.id, None)
            self._audit(state, principal, chapter, "version.commit")
            remember(state, chapter.project_id, principal.user.id, key, request_fingerprint, result, self._now())
            return result
        return self.repository.transaction(operation)

    @staticmethod
    def _writing_input(state: DemoState, chapter: Chapter, input_fingerprint: str | None):
        # 检查和正文写入共用事务快照，不能用浏览器先前的一次读取替代原子校验。
        workflow = state.workflows.get(chapter.project_id, {})
        has_sources = bool(workflow.get("requirements") or workflow.get("facts") or workflow.get("sla"))
        if has_sources and input_fingerprint is None:
            raise DomainError(409, "INPUT_FINGERPRINT_REQUIRED", "请先核对项目来源，再保存草稿或提交正文；本次内容缺少来源基准。")
        if input_fingerprint is not None and input_fingerprint != project_input_fingerprint(state, chapter.project_id):
            raise DomainError(409, "INPUT_FINGERPRINT_STALE", "项目条款、事实、证据或正文已变化，不能保存或提交旧来源内容；请重新核对来源。")

    def versions(self, principal: Principal, chapter_id: str) -> dict:
        state = self.repository.read()
        chapter = self._chapter(state, principal, chapter_id)
        return {"versions": chapter.versions}

    def discard_draft(self, principal, chapter_id, sequence):
        def operation(state):
            chapter = self._chapter(state, principal, chapter_id)
            draft = chapter.drafts.get(principal.user.id)
            if draft is None:
                return {"discarded": False}
            if draft.sequence != sequence:
                raise DomainError(409, "DRAFT_SEQUENCE_CONFLICT", "草稿已更新，请先查看最新草稿再明确丢弃。")
            del chapter.drafts[principal.user.id]
            self._audit(state, principal, chapter, "draft.discard", {"sequence": sequence})
            return {"discarded": True}
        return self.repository.transaction(operation)

    def audit(self, principal: Principal, chapter_id: str) -> dict:
        state = self.repository.read()
        self._chapter(state, principal, chapter_id)
        return {"events": [event for event in state.audit if event["chapter_id"] == chapter_id]}

    def suggest(self, principal: Principal, chapter_id: str, instruction: str) -> dict:
        state = self.repository.read()
        chapter = self._chapter(state, principal, chapter_id)
        self._chapter_writer(state, principal, chapter)
        self.require_allowed_model(self._project(state, principal, chapter.project_id))
        fingerprint = project_input_fingerprint(state, chapter.project_id)
        # 独立旧demo保持正文建议；接入项目资料后必须与主流程使用同一输入和门禁。
        workflow = state.workflows.get(chapter.project_id, {})
        input_snapshot = None
        model_input = chapter.content
        if workflow.get("requirements") or workflow.get("facts") or workflow.get("sla"):
            from .generation_context import (build_generation_context, refuse_source_change,
                                             render_model_input, require_ready)
            context = build_generation_context(state, chapter.project_id, chapter, self._now())
            require_ready(context)
            input_snapshot = context["input_snapshot"]
            refuse_source_change(instruction, input_snapshot)
            refuse_source_change(input_snapshot["plan"]["writing_points"], input_snapshot)
            model_input = render_model_input(input_snapshot)
        # 模型调用在事务外执行，只取得当前有权章节的正文，不持有全局写锁。
        current = self.repository.read()
        actual = self._chapter(current, principal, chapter_id)
        self._chapter_writer(current, principal, actual)
        self.require_allowed_model(self._project(current, principal, actual.project_id))
        if project_input_fingerprint(current, chapter.project_id) != fingerprint:
            raise DomainError(409, "VERSION_CONFLICT", "项目资料在准备建议期间更新，请核对来源后重新请求。")
        try:
            suggestion = self.model_provider.suggest(instruction, model_input)
            if not isinstance(suggestion, str):
                raise TypeError("模型接口必须返回字符串")
        except Exception as error:
            raise DomainError(502, "MODEL_UNAVAILABLE", "演示建议服务失败，正文没有修改。") from error
        if input_snapshot is not None:
            from .generation_context import validate_model_output
            validate_model_output(state, chapter.project_id, suggestion, input_snapshot)
            input_snapshot.update(model_input=model_input, model_instruction=instruction)

        def operation(current: DemoState):
            actual = self._chapter(current, principal, chapter_id)
            self._chapter_writer(current, principal, actual)
            self.require_allowed_model(self._project(current, principal, actual.project_id))
            if project_input_fingerprint(current, chapter.project_id) != fingerprint:
                raise DomainError(409, "VERSION_CONFLICT", "正文或项目资料在建议生成期间更新，请重新请求建议。")
            self._audit(current, principal, actual, "suggestion.generate",
                        {"base_revision": chapter.revision})
            return {"content": suggestion, "base_revision": chapter.revision,
                    "provider": getattr(self.model_provider, "name", "demo"),
                    "is_real_model": bool(getattr(self.model_provider, "is_real_model", False)),
                    "input_fingerprint": fingerprint, "source_scope": "whole_chapter" if input_snapshot else None,
                    "input_snapshot": input_snapshot}
        return self.repository.transaction(operation)

    def check(self, principal: Principal, chapter_id: str) -> dict:
        def operation(state: DemoState):
            chapter = self._chapter(state, principal, chapter_id)
            self._legacy_flow_guard(state, chapter)
            from .project_access import chapter_structure
            if not chapter_structure(state, chapter, principal.user.id):
                raise DomainError(403, "VOLUME_OWNER_REQUIRED", "章节检查须由本项目负责人或本册负责人办理。")
            issues = []
            if not chapter.content.strip():
                issues.append({"code": "EMPTY_CONTENT", "message": "已提交正文为空。"})
            if "待补" in chapter.content:
                issues.append({"code": "PENDING_CONTENT", "message": "已提交正文仍含待补内容。"})
            check = Check(new_id("check"), chapter.id, not issues, chapter.revision,
                          content_hash(chapter.content), issues)
            state.checks[check.id] = check
            self._audit(state, principal, chapter, "check.run", {"check_id": check.id, "passed": check.passed})
            return {"id": check.id, "passed": check.passed, "revision": check.revision, "issues": check.issues}
        return self.repository.transaction(operation)

    def export(self, principal: Principal, chapter_id: str, check_id: str) -> dict:
        def operation(state: DemoState):
            chapter = self._chapter(state, principal, chapter_id)
            from .project_access import chapter_structure
            if not chapter_structure(state, chapter, principal.user.id):
                raise DomainError(403, "VOLUME_OWNER_REQUIRED", "内部稿导出须由本项目负责人或本册负责人办理。")
            self._legacy_flow_guard(state, chapter)
            check = state.checks.get(check_id)
            if check is None or check.chapter_id != chapter.id:
                raise DomainError(404, "NOT_FOUND", "未找到本章节的检查记录。")
            if not check.passed:
                raise DomainError(409, "CHECK_FAILED", "基础检查未通过，不能生成演示 Word。")
            if check.revision != chapter.revision or check.content_hash != content_hash(chapter.content):
                raise DomainError(409, "CHECK_STALE", "正文已修改，请重新检查后再导出。")
            record = Export(new_id("export"), chapter.id, chapter.revision, check.content_hash,
                            check.id, f"icg-demo-{chapter.id}-r{chapter.revision}.docx",
                            chapter.title, chapter.content)
            state.exports[record.id] = record
            self._audit(state, principal, chapter, "export.create", {"export_id": record.id, "check_id": check.id})
            return {"id": record.id, "filename": record.filename,
                    "download_url": f"/api/exports/{record.id}/file", "excludes_drafts": True}
        return self.repository.transaction(operation)

    def download(self, principal: Principal, export_id: str) -> Export:
        def operation(state: DemoState):
            record = state.exports.get(export_id)
            if record is None:
                raise DomainError(404, "NOT_FOUND", "未找到有权访问的导出文件。")
            chapter = self._chapter(state, principal, record.chapter_id)
            self._legacy_flow_guard(state, chapter)
            if record.revision != chapter.revision or record.content_hash != content_hash(chapter.content):
                raise DomainError(409, "EXPORT_STALE", "正文已修改，旧导出文件已过期。")
            self._audit(state, principal, chapter, "export.download", {"export_id": record.id})
            return record
        return self.repository.transaction(operation)
