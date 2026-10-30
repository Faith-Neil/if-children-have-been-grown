# 为什么有这个文件：把公司权限、编辑锁、草稿、版本和导出条件放在同一业务边界内。
# 它解决什么问题：确保每次写入都重新核对权限与版本，失败时不留下部分正文或审计。

from __future__ import annotations

import re

import hashlib
import os
import json
import secrets
import time
from dataclasses import asdict, dataclass, field, replace
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


def _production_mode() -> bool:
    # 只认显式的 ICG_ENV=production。ICG_REQUIRE_MYSQL 只表示“必须连 MySQL”，CI 的 MySQL 用例仍用合成种子数据。
    return os.environ.get("ICG_ENV") == "production"


@dataclass(frozen=True)
class Account:
    id: str
    name: str
    company_id: str
    role: str
    _DEMO_ONLY: bool = False
    password_hash: str = ""
    salt: str = ""
    display_name: str = ""
    status: str = "active"
    is_locked: bool = False
    failed_login_attempts: int = 0
    created_at: float | None = None
    updated_at: float | None = None


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
    tender_type: str = "comprehensive"
    budget_amount_cents: int | None = None
    deadline_at: float | None = None
    security_level: str = "internal"
    industry: str = "it"
    is_archived: bool = False
    created_by: str | None = None
    created_at: float | None = None
    updated_by: str | None = None
    updated_at: float | None = None
    record_version: int = 1
    is_deleted: bool = False

    @property
    def is_sensitive(self) -> bool:
        return self.sensitive

    @is_sensitive.setter
    def is_sensitive(self, val: bool) -> None:
        self.sensitive = val


@dataclass
class Lease:
    token: str
    owner_id: str = ""
    session_token: str = ""
    expires_at: float = 0.0
    acquired_at: float | None = None
    heartbeat_at: float | None = None
    lock_reason: str | None = None
    taken_over_from_user_id: str | None = None
    takeover_reason: str | None = None
    released_at: float | None = None
    release_reason: str | None = None
    company_id: str | None = None
    record_version: int = 1
    user_id: str | None = None

    def __post_init__(self):
        if self.user_id is not None and not self.owner_id:
            self.owner_id = self.user_id
        elif self.owner_id and self.user_id is None:
            self.user_id = self.owner_id


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
    input_fingerprint: str = ""


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
    input_fingerprint: str = ""


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
    # 可恢复生成任务只在本进程内存。重启后消失。不写入同步任务列表。
    recoverable_jobs: dict[str, dict] = field(default_factory=dict)
    workflow_receipts: dict[tuple[str, str, str], dict] = field(default_factory=dict)
    project_teams: dict[str, dict] = field(default_factory=dict)
    # 合作方协议和资料授权先留在内存。正式表对齐不在本次挂接规则里做。
    project_partners: dict[str, list] = field(default_factory=dict)
    resource_acl: list[dict] = field(default_factory=list)
    model_configs: dict[str, Any] = field(default_factory=dict)
    project_model_configs: dict[str, str] = field(default_factory=dict)
    # RAGFlow 租户配置与各服务（公司设置、字典、方案片段）的存储；与其他状态同一事务、同一持久化。
    ragflow_configs: dict[str, Any] = field(default_factory=dict)
    service_stores: dict[str, dict] = field(default_factory=dict)
    # 内存仓库仍按 2048 条裁剪回执。MySQL 路径在事务里把它设为 False，避免未过期回执被提前删掉。
    cap_receipts: bool = True



def lock_view(state, lease) -> dict:
    """章节编辑锁的公开视图：其他成员看到持锁人姓名与到期时刻（APP-M2-T173）。"""
    owner = state.accounts.get(lease.owner_id)
    return {"owner_id": lease.owner_id, "owner_name": owner.name if owner else None,
            "expires_at": iso_time(lease.expires_at)}

class DemoService:
    LEASE_SECONDS = 30 * 60  # 无操作 30 分钟释放（PRD §5.11.9，公司设置 edit_lock_timeout_minutes 可调）

    def __init__(self, repository: Repository, model_provider: ModelProvider,
                 clock: Callable[[], float | datetime] | None = None,
                 model_transport: Any | None = None,
                 evidence_service: Any | None = None):
        self.repository = repository
        self.model_provider = model_provider
        self.clock = clock or time.time
        self.model_transport = model_transport
        from .knowledge_base import KnowledgeBaseService, KnowledgeEvidenceService
        self.knowledge_base = KnowledgeBaseService(self)
        # 未显式注入时，证据候选走公司知识库（未配置 RAGFlow 时只有路径 A，B/C 记为跳过）。
        self.evidence_service = evidence_service if evidence_service is not None else KnowledgeEvidenceService(self.knowledge_base)
        from .chapter_generation import ChapterGenerationService
        self.chapter_generation = ChapterGenerationService(self)
        from .editor_ai_context import EditorAIContextService
        self.editor_context = EditorAIContextService(self)
        from icg.infra.tender_retrieval import TenderRetrievalService
        self.tender_retrieval = TenderRetrievalService(self)
        from .compliance_cross_check import ComplianceCrossCheckService
        self.compliance_cross_check_service = ComplianceCrossCheckService(self)
        from .snippet_retrieval import SnippetRetrievalService
        self.snippet_retrieval_service = SnippetRetrievalService(self)

    def start_chapter_generation(
        self,
        project_id: str,
        chapter_id: str,
        principal: Principal,
        sync_execute: bool = False,
        max_context_tokens: int | None = None,
        snippet_matches: list[dict] | None = None,
        auto_remediate: bool = False,
    ) -> dict:
        return self.chapter_generation.start_chapter_generation(
            project_id,
            chapter_id,
            principal,
            sync_execute=sync_execute,
            max_context_tokens=max_context_tokens,
            snippet_matches=snippet_matches,
            auto_remediate=auto_remediate,
        )

    def batch_generate_chapters(
        self,
        project_id: str,
        chapter_ids: list[str],
        principal: Principal,
        sync_execute: bool = False,
        max_context_tokens: int | None = None,
        snippet_matches_by_chapter: dict[str, list[dict]] | None = None,
    ) -> dict[str, Any]:
        return self.chapter_generation.batch_generate_chapters(
            project_id=project_id,
            chapter_ids=chapter_ids,
            principal=principal,
            sync_execute=sync_execute,
            max_context_tokens=max_context_tokens,
            snippet_matches_by_chapter=snippet_matches_by_chapter,
        )

    def schedule_batch_pipeline(
        self,
        project_id: str,
        principal: Principal,
        concurrency_limit: int = 2,
        priority_threshold: str | None = None,
        sync_execute: bool = False,
        chapter_ids: list[str] | None = None,
        max_context_tokens: int | None = None,
    ) -> dict[str, Any]:
        return self.chapter_generation.schedule_batch_pipeline(
            project_id=project_id,
            principal=principal,
            concurrency_limit=concurrency_limit,
            priority_threshold=priority_threshold,
            sync_execute=sync_execute,
            chapter_ids=chapter_ids,
            max_context_tokens=max_context_tokens,
        )

    def validate_chapter_content(
        self,
        project_id: str,
        chapter_id: str,
        principal: Principal,
        content: str | None = None,
    ) -> dict[str, Any]:
        return self.chapter_generation.validate_chapter_content(
            project_id=project_id,
            chapter_id=chapter_id,
            principal=principal,
            content=content,
        )

    def remediate_chapter_candidate(
        self,
        project_id: str,
        chapter_id: str,
        principal: Principal,
        content: str | None = None,
        candidate: dict[str, Any] | None = None,
        max_rounds: int = 3,
        auto_save: bool = True,
        provider: Any | None = None,
    ) -> dict[str, Any]:
        return self.chapter_generation.remediate_chapter_candidate(
            project_id=project_id,
            chapter_id=chapter_id,
            principal=principal,
            content=content,
            candidate=candidate,
            max_rounds=max_rounds,
            auto_save=auto_save,
            provider=provider,
        )

    def assemble_writing_prompt_plan(
        self,
        project_id: str,
        chapter_id: str,
        principal: Principal | None = None,
        max_context_tokens: int | None = None,
        snippet_matches: list[dict] | None = None,
    ) -> dict:
        return self.chapter_generation.assemble_writing_prompt_plan(
            project_id,
            chapter_id,
            principal=principal,
            max_context_tokens=max_context_tokens,
            snippet_matches=snippet_matches,
        )

    def chat_editor_context(self, principal: Principal, project_id: str, query: str,
                            chapter_id: str, chapter_title: str | None = None,
                            selected_text: str | None = None, scene: str | None = None,
                            lease_token: str | None = None, knowledge_base_enabled: bool = True,
                            history: list[dict[str, str]] | None = None,
                            injected_tender_clauses: list[dict[str, Any]] | None = None) -> dict:
        return self.editor_context.chat_editor_context(
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
        return self.editor_context.accept_ai_suggestion(
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
        return self.compliance_cross_check_service.cross_check_chapter(
            principal=principal,
            project_id=project_id,
            chapter_id=chapter_id,
            model_config_id=model_config_id,
            strict_mode=strict_mode,
        )

    def match_snippets(
        self,
        principal: Principal,
        project_id: str,
        chapter_id: str | None = None,
        chapter_title: str | None = None,
        scoring_points: list[str] | None = None,
        query: str | None = None,
        limit: int = 5,
        min_score: float = 0.05,
        model_config_id: str | None = None,
        snippet_store: Any | None = None,
    ) -> dict[str, Any]:
        return self.snippet_retrieval_service.match_snippets(
            principal=principal,
            project_id=project_id,
            chapter_id=chapter_id,
            chapter_title=chapter_title,
            scoring_points=scoring_points,
            query=query,
            limit=limit,
            min_score=min_score,
            model_config_id=model_config_id,
            snippet_store=snippet_store,
        )

    def resolve_model_provider(self, state: DemoState, project_id: str, task: str | None = None) -> ModelProvider:
        """项目单独绑定的模型 → 本公司任务与模型对应表（APP-M2-T040）→ 本公司默认模型 → 进程内置模型。"""
        bound_id = state.project_model_configs.get(project_id)
        cfg = None
        route_backup = None
        project = state.projects.get(project_id)
        if bound_id and bound_id in state.model_configs:
            cfg = state.model_configs[bound_id]
        elif project is not None and task:
            from .task_model_routes import resolve as resolve_route
            routed = resolve_route(state, project.company_id, task)
            if routed is not None:
                cfg, route_backup = routed
                if project.sensitive and (not cfg.is_local or not cfg.allow_sensitive):
                    raise DomainError(403, "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL",
                                      "敏感项目只能使用本地模型：任务与模型对应表里该任务的首选模型不是允许处理敏感数据的本地模型。")
        if cfg is None:
            project = state.projects.get(project_id)
            if project:
                default_id = f"default-{project.company_id}"
                if default_id in state.model_configs:
                    cfg = state.model_configs[default_id]
        if cfg is not None:
            from icg.infra.model_config_storage import provider_from_model_config, usable_fallback
            provider = provider_from_model_config(cfg, transport=self.model_transport, default_provider=self.model_provider)
            backup = usable_fallback(state, cfg, bool(project and project.sensitive))
            if route_backup is not None and (not (project and project.sensitive)
                                             or (route_backup.is_local and route_backup.allow_sensitive)):
                backup = route_backup  # 任务表里填的备用优先于模型配置自带的
            if backup is not None and getattr(provider, "is_real_model", False) and provider is not self.model_provider:
                # 备用模型（PRD §6.5 规则 2、3）：所有任务的 suggest() 在主模型健康类失败时改用备用（APP-M2-T040）
                from icg.infra.model_fallback import WithFallback
                return WithFallback(provider, provider_from_model_config(backup, transport=self.model_transport))
            return provider
        return self.model_provider

    def resolve_provider_from_snapshot(self, snapshot: dict) -> ModelProvider:
        from icg.infra.model_config_storage import provider_from_model_snapshot
        return provider_from_model_snapshot(snapshot, transport=self.model_transport, default_provider=self.model_provider)

    def _now(self) -> float:
        value = self.clock()
        if isinstance(value, datetime):
            if value.tzinfo is None:
                raise ValueError("测试时钟的 datetime 必须包含时区")
            return value.timestamp()
        return float(value)

    def auth_login(self, username: str, password: str) -> dict:
        if not username or not password:
            raise DomainError(401, "INVALID_CREDENTIALS", "用户名或密码错误，请核实后重试。")

        state = self.repository.read()
        user = state.accounts.get(username)
        production = _production_mode()
        if production and user is not None and getattr(user, "_DEMO_ONLY", False) and username == "admin":
            user = None  # 生产环境忽略种子管理员，按部署设定的初始密码重新初始化
        if user is None and username == "admin":
            # 超级管理员首次登录时初始化。生产环境必须由部署方经 ICG_ADMIN_INITIAL_PASSWORD 设定初始密码，
            # 不存在内置默认口令；开发与自动化测试环境才回落到固定初始密码。
            initial = os.environ.get("ICG_ADMIN_INITIAL_PASSWORD", "")
            if not initial and production:
                raise DomainError(401, "INVALID_CREDENTIALS", "用户名或密码错误，请核实后重试。")
            initial = initial or "X_2026"
            if password != initial:
                raise DomainError(401, "INVALID_CREDENTIALS", "用户名或密码错误，请核实后重试。")
            from icg.domain.auth_service import hash_password
            def init_admin(s: DemoState):
                existing = s.accounts.get("admin")
                if existing is None or getattr(existing, "_DEMO_ONLY", False):
                    p_hash, p_salt = hash_password(initial)
                    s.accounts["admin"] = Account(
                        id="admin",
                        name="系统超级管理员",
                        company_id="system",
                        role="platform_admin",
                        _DEMO_ONLY=False,
                        password_hash=p_hash,
                        salt=p_salt,
                        display_name="系统超级管理员",
                    )
            self.repository.transaction(init_admin)
            state = self.repository.read()
            user = state.accounts.get(username)

        if user is None:
            raise DomainError(401, "INVALID_CREDENTIALS", "用户名或密码错误，请核实后重试。")
        if production and getattr(user, "_DEMO_ONLY", False):
            # 内存仓储预置的合成账号只用于开发与自动化测试，生产环境一律拒绝。
            raise DomainError(401, "INVALID_CREDENTIALS", "用户名或密码错误，请核实后重试。")

        if getattr(user, "is_locked", False) or getattr(user, "status", "active") == "locked":
            raise DomainError(423, "ACCOUNT_LOCKED", "账号因连续登录失败已被锁定，请联系管理员解锁。")

        if getattr(user, "status", "active") == "disabled":
            raise DomainError(401, "INVALID_CREDENTIALS", "该账号已被停用，请联系企业管理员。")

        from icg.domain.auth_service import verify_password
        # 没有密码摘要的账号不能登录（不再接受固定明文口令）。
        valid = bool(user.password_hash) and verify_password(password, user.password_hash, user.salt)

        if not valid:
            attempts = getattr(user, "failed_login_attempts", 0) + 1
            max_attempts = 5
            if hasattr(self, "company_settings_service") and self.company_settings_service and user.company_id:
                st = getattr(self.company_settings_service, "_store", {}).get(user.company_id)
                if st and getattr(st, "max_login_attempts", None):
                    max_attempts = st.max_login_attempts
            is_now_locked = (attempts >= max_attempts)

            def record_failure(s: DemoState):
                u = s.accounts.get(username)
                if u:
                    if is_now_locked:
                        s.accounts[username] = replace(u, failed_login_attempts=attempts, is_locked=True, status="locked", updated_at=time.time())
                        s.audit.append({"action": "user.locked", "user_id": username, "attempts": attempts, "timestamp": time.time()})
                    else:
                        s.accounts[username] = replace(u, failed_login_attempts=attempts, updated_at=time.time())

            self.repository.transaction(record_failure)

            if is_now_locked:
                raise DomainError(423, "ACCOUNT_LOCKED", f"密码连续错误达到上限（{max_attempts}次），账号已被锁定，请联系管理员解锁。")
            else:
                raise DomainError(401, "INVALID_CREDENTIALS", f"用户名或密码错误，还剩 {max_attempts - attempts} 次尝试机会。")

        def record_success(s: DemoState):
            u = s.accounts.get(username)
            if u and getattr(u, "failed_login_attempts", 0) > 0:
                s.accounts[username] = replace(u, failed_login_attempts=0, updated_at=time.time())
                u = s.accounts[username]
            token = secrets.token_urlsafe(32)
            s.sessions[token] = u.id
            user_data = asdict(u)
            user_data.pop("password_hash", None)
            user_data.pop("salt", None)
            user_data["username"] = u.id
            user_data["display_name"] = u.display_name or u.name
            return {"access_token": token, "token_type": "bearer", "user": user_data}

        return self.repository.transaction(record_success)

    def authenticate(self, token: str) -> Principal:
        state = self.repository.read()
        user = state.accounts.get(state.sessions.get(token, ""))
        if user is None:
            raise DomainError(401, "UNAUTHENTICATED", "登录已失效，请重新登录。")
        if getattr(user, "status", "active") == "disabled":
            raise DomainError(401, "UNAUTHENTICATED", "当前账号已被停用。")
        if getattr(user, "is_locked", False):
            raise DomainError(401, "UNAUTHENTICATED", "当前账号已被锁定。")
        return Principal(user, token)

    @staticmethod
    def _writer(principal: Principal) -> None:
        from icg.domain.auth_service import is_super_admin
        if is_super_admin(principal):
            return
        from .project_access import normalize_role, READONLY_SYSTEM_ROLES
        role = normalize_role(principal.user.role)
        if role in READONLY_SYSTEM_ROLES or role not in (
            "editor", "manager", "company_admin", "data_admin", "project_lead", "bid_writer"
        ):
            raise DomainError(403, "FORBIDDEN", "当前账号只能查看，不能执行此操作。")

    @staticmethod
    def _project(state: DemoState, principal: Principal, project_id: str) -> Project:
        from .project_access import member
        project = state.projects.get(project_id)
        account = state.accounts.get(principal.user.id)
        if project is None or project.is_deleted or account is None:
            raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")
        from icg.domain.auth_service import is_super_admin
        if is_super_admin(principal):
            return project
        if (project.company_id != account.company_id
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

    def require_allowed_model(self, project: Project, state: DemoState | None = None) -> None:
        cfg = None
        if state is not None:
            bound_id = state.project_model_configs.get(project.id)
            if bound_id and bound_id in state.model_configs:
                cfg = state.model_configs[bound_id]
            else:
                default_id = f"default-{project.company_id}"
                if default_id in state.model_configs:
                    cfg = state.model_configs[default_id]

        if cfg is not None:
            if project.sensitive and (not cfg.is_local or not cfg.allow_sensitive):
                raise DomainError(403, "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL", "敏感项目只能使用本地模型配置。")
            if cfg.encrypted_api_key:
                from icg.infra.model_config_storage import get_master_key
                try:
                    get_master_key()
                except DomainError:
                    raise DomainError(503, "SECRET_KEY_UNAVAILABLE", "主密钥不可用。")
            return

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

    @staticmethod
    def _project_response(project: Project) -> dict:
        data = asdict(project)
        if isinstance(data.get("deadline_at"), (int, float)):
            data["deadline_at"] = iso_time(data["deadline_at"])
        if isinstance(data.get("created_at"), (int, float)):
            data["created_at"] = iso_time(data["created_at"])
        if isinstance(data.get("updated_at"), (int, float)):
            data["updated_at"] = iso_time(data["updated_at"])
        return data

    def projects(self, principal: Principal) -> dict:
        state = self.repository.read()
        from .project_access import member
        return {"projects": [self._project_response(project) for project in state.projects.values()
                             if project.company_id == principal.user.company_id
                             and member(state, project.id, principal.user.id)
                             and not project.is_deleted]}

    def project(self, principal: Principal, project_id: str) -> dict:
        state = self.repository.read()
        return self._project_response(self._project(state, principal, project_id))

    def create_project(self, principal: Principal, name: str, *,
                       idempotency_key: str | None = None, volume_mode: str = "both") -> dict:
        from .idempotency import fingerprint, lookup, remember, validate_key
        from .project_access import volumes_for_mode
        key = validate_key(idempotency_key) if idempotency_key is not None else None
        scope_id = f"company:{principal.user.company_id}"
        # 原有两册项目的指纹保持不变（只有技术标模式才把模式写进指纹）
        req_fp = fingerprint("project.create", {"name": name} if volume_mode == "both" else {"name": name, "volume_mode": volume_mode}, None) if key else ""

        def operation(state: DemoState):
            if key:
                cached = lookup(state, scope_id, principal.user.id, key, req_fp, self._now())
                if cached is not None:
                    return cached
            from .project_access import initial_team, normalize_role, LEAD_COMPANY_ROLES
            actual = state.accounts.get(principal.user.id)
            if (actual is None
                    or normalize_role(actual.role) not in LEAD_COMPANY_ROLES
                    or state.sessions.get(principal.session_token) != actual.id):
                raise DomainError(403, "PROJECT_CREATE_FORBIDDEN", "普通编写人不能新建项目，请由公司项目经理建立并邀请成员。")
            now_ts = self._now()
            project = Project(
                id=new_id("project"),
                name=name,
                company_id=actual.company_id,
                created_by=principal.user.id,
                created_at=now_ts,
                updated_by=principal.user.id,
                updated_at=now_ts,
                record_version=1,
            )
            state.projects[project.id] = project
            state.project_teams[project.id] = initial_team(principal.user.id, volume_mode)
            active = volumes_for_mode(volume_mode)
            for volume, title in (("technical", "技术方案"), ("business", "商务响应")):
                if volume not in active:
                    continue
                chapter = Chapter(new_id("chapter"), project.id, title, volume, "")
                chapter.versions.append({"revision": 1, "content": "",
                                         "actor_id": principal.user.id,
                                         "created_at": iso_time(now_ts)})
                state.chapters[chapter.id] = chapter
                self._audit(state, principal, chapter, "project.create")
            res = {**self._project_response(project), "volume_mode": volume_mode}
            if key:
                remember(state, scope_id, principal.user.id, key, req_fp, res, self._now())
            return res
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
        lock = lock_view(state, chapter.lock) if active_lock else None
        draft = chapter.drafts.get(principal.user.id)
        from .project_access import chapter_permissions
        from .paragraph_keys import current as current_paragraphs, public as public_paragraphs
        from .paragraph_locks import mark_locked
        return {**self._summary(chapter), "project_id": chapter.project_id,
                "content": chapter.content, "lock": lock,
                "paragraphs": mark_locked(public_paragraphs(current_paragraphs(chapter)),
                                          state.workflows.get(chapter.project_id) or {}, chapter.id),
                "draft": asdict(draft) if draft else None, "assignee_id": chapter.assignee_id,
                "permissions": chapter_permissions(state, chapter, principal.user.id)}

    @staticmethod
    def _chapter_writer(state, principal, chapter):
        from .project_access import require_chapter
        require_chapter(state, principal, chapter)
        # 已定稿分册的正文只读（PRD v1.8 §5.7.5 规则 5）；不能只靠页面禁用按钮。
        volumes = state.workflows.get(chapter.project_id, {}).get("volumes", {})
        if volumes.get(chapter.volume, {}).get("is_finalized"):
            raise DomainError(409, "VOLUME_FINALIZED", "所在分册已定稿，须先解锁分册再修改。")

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
        data = {"lease_token": lease.token, "expires_at": iso_time(lease.expires_at),
                "owner_id": lease.owner_id}
        if lease.acquired_at is not None:
            data["acquired_at"] = iso_time(lease.acquired_at)
        if lease.heartbeat_at is not None:
            data["heartbeat_at"] = iso_time(lease.heartbeat_at)
        return data

    def _lease_seconds(self, state: DemoState, company_id: str) -> float:
        stored = (state.service_stores.get("company_settings") or {}).get(company_id) or {}
        minutes = stored.get("edit_lock_timeout_minutes")
        try:
            return max(60.0, float(minutes) * 60) if minutes else float(self.LEASE_SECONDS)
        except (TypeError, ValueError):
            return float(self.LEASE_SECONDS)

    def _auto_commit_draft(self, state: DemoState, chapter: Chapter, user_id: str, why: str) -> int | None:
        """锁释放（主动离开、超时、被接管）时，把持锁人未提交的草稿自动提交为“手改”版本（PRD §5.11.9 第 1 点）。

        草稿基于旧版本、来源已变化或含对话残留时不提交，草稿原样保留（之后标“已过期”，由本人对比合并）。返回新版本号。"""
        draft = chapter.drafts.get(user_id)
        if draft is None or draft.content == chapter.content or draft.base_revision != chapter.revision:
            return None
        from .system_chapters import is_system_chapter
        workflow = state.workflows.get(chapter.project_id, {})
        if is_system_chapter(workflow, chapter):
            return None
        has_sources = bool(workflow.get("requirements") or workflow.get("facts") or workflow.get("sla"))
        if has_sources and draft.input_fingerprint != project_input_fingerprint(state, chapter.project_id):
            return None
        from .chapter_generation import AI_CONVERSATION_RESIDUALS
        if any(residual in draft.content for residual in AI_CONVERSATION_RESIDUALS):
            return None
        from .paragraph_locks import violations
        if violations(workflow, chapter.id, draft.content):
            return None  # 草稿改动了锁定段落：不自动提交，草稿保留由本人处理
        chapter.content = draft.content
        chapter.revision += 1
        state.projects[chapter.project_id].revision += 1
        chapter.versions.append({"revision": chapter.revision, "content": chapter.content, "actor_id": user_id,
                                 "created_at": iso_time(self._now()), "version_origin": "manual", "edit_mode": "manual",
                                 "note": f"自动提交（{why}）"})
        chapter.drafts.pop(user_id, None)
        state.audit.append({"id": new_id("event"), "action": "version.autocommit", "actor_id": user_id,
                            "chapter_id": chapter.id, "created_at": iso_time(self._now()),
                            "details": {"revision": chapter.revision, "reason": why}})
        return chapter.revision

    def acquire_lock(self, principal: Principal, chapter_id: str,
                     takeover_reason: str | None, *,
                     idempotency_key: str | None = None) -> dict:
        from .idempotency import fingerprint, lookup, remember, validate_key
        key = validate_key(idempotency_key) if idempotency_key is not None else None
        req_fp = fingerprint("chapter.lock.acquire:" + chapter_id, {"takeover_reason": takeover_reason}, None) if key else ""

        def operation(state: DemoState):
            chapter = self._chapter(state, principal, chapter_id)
            if key:
                cached = lookup(state, chapter.project_id, principal.user.id, key, req_fp, self._now())
                if cached is not None:
                    return cached
            self._chapter_writer(state, principal, chapter)
            old_lease = chapter.lock
            active = old_lease is not None and old_lease.expires_at > self._now()
            if active and old_lease.owner_id == principal.user.id \
                    and old_lease.session_token == principal.session_token:
                res = self._lease_response(old_lease)
                if key:
                    remember(state, chapter.project_id, principal.user.id, key, req_fp, res, self._now())
                return res
            if active:
                from .project_access import chapter_structure
                if not chapter_structure(state, chapter, principal.user.id):
                    if takeover_reason is not None:
                        raise DomainError(403, "FORBIDDEN", "普通编写人没有接管其他会话的权限。")
                    raise DomainError(423, "LOCK_HELD", "其他会话正在编辑；项目负责人或本册负责人可以填写理由接管。")
                if not takeover_reason or not takeover_reason.strip():
                    raise DomainError(409, "TAKEOVER_REASON_REQUIRED", "接管前必须填写理由。")
            committed = None
            if old_lease is not None and old_lease.owner_id != principal.user.id:
                committed = self._auto_commit_draft(state, chapter, old_lease.owner_id,
                                                    "编辑权被接管" if active else "编辑锁超时释放")
            now = self._now()
            lease = Lease(token=secrets.token_urlsafe(32),
                          owner_id=principal.user.id,
                          session_token=principal.session_token,
                          expires_at=now + self._lease_seconds(state, principal.user.company_id),
                          acquired_at=now,
                          heartbeat_at=now,
                          lock_reason=None,
                          taken_over_from_user_id=old_lease.owner_id if active and old_lease else None,
                          takeover_reason=takeover_reason.strip() if active and takeover_reason else None,
                          company_id=principal.user.company_id,
                          record_version=1)
            chapter.lock = lease
            details = ({"reason": takeover_reason.strip(), "previous_owner_id": old_lease.owner_id}
                       if active and old_lease else {})
            self._audit(state, principal, chapter, "lock.takeover" if active else "lock.acquire", details)
            if active and old_lease and old_lease.owner_id != principal.user.id:
                from .notifications import notify
                notify(state, [old_lease.owner_id], "lock_taken_over", f"「{chapter.title}」的编辑权已被接管",
                       f"{principal.user.name} 接管了编辑权，理由：{takeover_reason.strip()}。"
                       + (f"你的草稿已自动提交为 v{committed}。" if committed else "你已保存的草稿仍保留，未提交的修改不会覆盖新版本。"),
                       now=iso_time(now), project_id=chapter.project_id, target_id=chapter.id)
            # 接管或超时：旧持锁人已保存的草稿先自动提交；断网设备尚未上传的文字无法替其保存。
            res = self._lease_response(lease)
            if key:
                remember(state, chapter.project_id, principal.user.id, key, req_fp, res, self._now())
            return res
        return self.repository.transaction(operation)

    def renew_lock(self, principal: Principal, chapter_id: str, lease_token: str, *,
                   idempotency_key: str | None = None) -> dict:
        from .idempotency import fingerprint, lookup, remember, validate_key
        key = validate_key(idempotency_key) if idempotency_key is not None else None
        req_fp = fingerprint("chapter.lock.renew:" + chapter_id, {"lease_token": lease_token}, None) if key else ""

        def operation(state: DemoState):
            chapter = self._chapter(state, principal, chapter_id)
            if key:
                cached = lookup(state, chapter.project_id, principal.user.id, key, req_fp, self._now())
                if cached is not None:
                    return cached
            self._chapter_writer(state, principal, chapter)
            lease = self._lease(chapter, principal, lease_token)
            now = self._now()
            lease.expires_at = now + self._lease_seconds(state, chapter.lock.company_id or principal.user.company_id)
            lease.heartbeat_at = now
            lease.record_version += 1
            self._audit(state, principal, chapter, "lock.renew")
            res = self._lease_response(lease)
            if key:
                remember(state, chapter.project_id, principal.user.id, key, req_fp, res, self._now())
            return res
        return self.repository.transaction(operation)

    def release_lock(self, principal: Principal, chapter_id: str, lease_token: str, *,
                     idempotency_key: str | None = None) -> dict:
        from .idempotency import fingerprint, lookup, remember, validate_key
        key = validate_key(idempotency_key) if idempotency_key is not None else None
        req_fp = fingerprint("chapter.lock.release:" + chapter_id, {"lease_token": lease_token}, None) if key else ""

        def operation(state: DemoState):
            chapter = self._chapter(state, principal, chapter_id)
            if key:
                cached = lookup(state, chapter.project_id, principal.user.id, key, req_fp, self._now())
                if cached is not None:
                    return cached
            self._chapter_writer(state, principal, chapter)
            lease = self._lease(chapter, principal, lease_token)
            self._auto_commit_draft(state, chapter, principal.user.id, "主动释放编辑权")
            now = self._now()
            lease.released_at = now
            lease.release_reason = "manual"
            chapter.lock = None
            self._audit(state, principal, chapter, "lock.release")
            res = {"released": True}
            if key:
                remember(state, chapter.project_id, principal.user.id, key, req_fp, res, self._now())
            return res
        return self.repository.transaction(operation)

    def save_draft(self, principal: Principal, chapter_id: str, lease_token: str,
                   base_revision: int, sequence: int, content: str,
                   input_fingerprint: str | None = None, *,
                   idempotency_key: str | None = None) -> dict:
        from .idempotency import fingerprint, lookup, remember, validate_key
        key = validate_key(idempotency_key) if idempotency_key is not None else None
        req_fp = fingerprint(
            "chapter.draft.save:" + chapter_id,
            {"lease_token": lease_token, "base_revision": base_revision, "sequence": sequence,
             "content": content, "input_fingerprint": input_fingerprint},
            None,
        ) if key else ""

        def operation(state: DemoState):
            chapter = self._chapter(state, principal, chapter_id)
            if key:
                cached = lookup(state, chapter.project_id, principal.user.id, key, req_fp, self._now())
                if cached is not None:
                    return cached
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
            res = asdict(draft)
            if key:
                remember(state, chapter.project_id, principal.user.id, key, req_fp, res, self._now())
            return res
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
            from .system_chapters import refuse_manual_edit
            refuse_manual_edit(state, chapter)
            from .paragraph_locks import refuse_locked_change
            refuse_locked_change(state, chapter, content)
            self._writing_input(state, chapter, input_fingerprint)
            # 粘贴识别（APP-M2-T188）：与本章近期对话助手输出高度重合的新段落，来源记为“对话助手撰写（粘贴）”并复查
            from .paste_detection import review as paste_review
            pasted = paste_review(state, chapter, state.workflows.get(chapter.project_id) or {}, chapter.content, content, self._now())
            chapter.content = content
            chapter.revision += 1
            state.projects[chapter.project_id].revision += 1
            result = {"revision": chapter.revision, "content": chapter.content}
            if pasted:
                result["paste_detected"] = pasted
            chapter.versions.append({**{k: v for k, v in result.items() if k != "paste_detected"}, "actor_id": principal.user.id,
                                     "created_at": iso_time(self._now()),
                                     **({"paragraph_sources": [{k: v for k, v in p.items() if k != "issues"} for p in pasted]} if pasted else {})})
            chapter.drafts.pop(principal.user.id, None)
            stale = [uid for uid, draft in chapter.drafts.items() if draft.base_revision < chapter.revision]
            if stale:
                from .notifications import notify
                notify(state, stale, "draft_expired", f"「{chapter.title}」有新版本，你的草稿已过期",
                       f"{principal.user.name} 提交了 v{chapter.revision}；你的草稿基于旧版本，不会覆盖新正文，请核对后再改。",
                       now=iso_time(self._now()), project_id=chapter.project_id, target_id=chapter.id)
            self._audit(state, principal, chapter, "version.commit",
                        {"pasted_paragraphs": [p["paragraph_index"] for p in pasted]} if pasted else None)
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
        from .paragraph_keys import ensure as ensure_paragraphs, public as public_paragraphs
        ensure_paragraphs(chapter)
        return {"versions": [{**v, "paragraphs": public_paragraphs(v.get("paragraphs") or [])} for v in chapter.versions]}

    def discard_draft(self, principal, chapter_id, sequence, *,
                      idempotency_key: str | None = None):
        from .idempotency import fingerprint, lookup, remember, validate_key
        key = validate_key(idempotency_key) if idempotency_key is not None else None
        req_fp = fingerprint("chapter.draft.discard:" + chapter_id, {"sequence": sequence}, None) if key else ""

        def operation(state):
            chapter = self._chapter(state, principal, chapter_id)
            if key:
                cached = lookup(state, chapter.project_id, principal.user.id, key, req_fp, self._now())
                if cached is not None:
                    return cached
            draft = chapter.drafts.get(principal.user.id)
            if draft is None:
                res = {"discarded": False}
                if key:
                    remember(state, chapter.project_id, principal.user.id, key, req_fp, res, self._now())
                return res
            if draft.sequence != sequence:
                raise DomainError(409, "DRAFT_SEQUENCE_CONFLICT", "草稿已更新，请先查看最新草稿再明确丢弃。")
            del chapter.drafts[principal.user.id]
            self._audit(state, principal, chapter, "draft.discard", {"sequence": sequence})
            res = {"discarded": True}
            if key:
                remember(state, chapter.project_id, principal.user.id, key, req_fp, res, self._now())
            return res
        return self.repository.transaction(operation)

    def audit(self, principal: Principal, chapter_id: str) -> dict:
        state = self.repository.read()
        self._chapter(state, principal, chapter_id)
        return {"events": [event for event in state.audit if event["chapter_id"] == chapter_id]}

    def suggest(self, principal: Principal, chapter_id: str, instruction: str) -> dict:
        state = self.repository.read()
        chapter = self._chapter(state, principal, chapter_id)
        self._chapter_writer(state, principal, chapter)
        self.require_allowed_model(self._project(state, principal, chapter.project_id), state=state)
        fingerprint = project_input_fingerprint(state, chapter.project_id)
        # 独立旧demo保持正文建议；接入项目资料后必须与主流程使用同一输入和门禁。
        workflow = state.workflows.get(chapter.project_id, {})
        input_snapshot = None
        model_input = chapter.content
        if workflow.get("requirements") or workflow.get("facts") or workflow.get("sla"):
            from .generation_context import (build_generation_context, refuse_source_change,
                                             render_model_input, require_ready)
            context = build_generation_context(state, chapter.project_id, chapter, self._now(),
                                                evidence_service=self.evidence_service)
            require_ready(context)
            input_snapshot = context["input_snapshot"]
            refuse_source_change(instruction, input_snapshot)
            refuse_source_change(input_snapshot["plan"]["writing_points"], input_snapshot)
            model_input = render_model_input(input_snapshot)
        # 模型调用在事务外执行，只取得当前有权章节的正文，不持有全局写锁。
        current = self.repository.read()
        actual = self._chapter(current, principal, chapter_id)
        self._chapter_writer(current, principal, actual)
        self.require_allowed_model(self._project(current, principal, actual.project_id), state=current)
        if project_input_fingerprint(current, chapter.project_id) != fingerprint:
            raise DomainError(409, "VERSION_CONFLICT", "项目资料在准备建议期间更新，请核对来源后重新请求。")
        provider = self.resolve_model_provider(current, actual.project_id, "chapter_generation")
        try:
            suggestion = provider.suggest(instruction, model_input)
            if not isinstance(suggestion, str):
                raise TypeError("模型接口必须返回字符串")
        except DomainError:
            raise
        except Exception as error:
            raise DomainError(502, "MODEL_UNAVAILABLE", "演示建议服务失败，正文没有修改。") from error
        if input_snapshot is not None:
            from .generation_context import validate_model_output
            validate_model_output(state, chapter.project_id, suggestion, input_snapshot)
            input_snapshot.update(model_input=model_input, model_instruction=instruction)

        def operation(current: DemoState):
            actual = self._chapter(current, principal, chapter_id)
            self._chapter_writer(current, principal, actual)
            self.require_allowed_model(self._project(current, principal, actual.project_id), state=current)
            if project_input_fingerprint(current, chapter.project_id) != fingerprint:
                raise DomainError(409, "VERSION_CONFLICT", "正文或项目资料在建议生成期间更新，请重新请求建议。")
            self._audit(current, principal, actual, "suggestion.generate",
                        {"base_revision": chapter.revision})
            return {"content": suggestion, "base_revision": chapter.revision,
                    "provider": getattr(provider, "name", "demo"),
                    "is_real_model": bool(getattr(provider, "is_real_model", False)),
                    "input_fingerprint": fingerprint, "source_scope": "whole_chapter" if input_snapshot else None,
                    "input_snapshot": input_snapshot}
        return self.repository.transaction(operation)

    def check(self, principal: Principal, chapter_id: str, *,
              idempotency_key: str | None = None) -> dict:
        from .idempotency import fingerprint, lookup, remember, validate_key
        key = validate_key(idempotency_key) if idempotency_key is not None else None
        req_fp = fingerprint("chapter.check:" + chapter_id, {}, None) if key else ""

        def operation(state: DemoState):
            chapter = self._chapter(state, principal, chapter_id)
            if key:
                cached = lookup(state, chapter.project_id, principal.user.id, key, req_fp, self._now())
                if cached is not None:
                    return cached
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
                          content_hash(chapter.content), issues,
                          input_fingerprint=project_input_fingerprint(state, chapter.project_id))
            state.checks[check.id] = check
            self._audit(state, principal, chapter, "check.run", {"check_id": check.id, "passed": check.passed})
            res = {"id": check.id, "passed": check.passed, "revision": check.revision, "issues": check.issues}
            if key:
                remember(state, chapter.project_id, principal.user.id, key, req_fp, res, self._now())
            return res
        return self.repository.transaction(operation)

    def export(self, principal: Principal, chapter_id: str, check_id: str, *,
               idempotency_key: str | None = None) -> dict:
        from .idempotency import fingerprint, lookup, remember, validate_key
        key = validate_key(idempotency_key) if idempotency_key is not None else None
        req_fp = fingerprint("chapter.export:" + chapter_id, {"check_id": check_id}, None) if key else ""

        def operation(state: DemoState):
            chapter = self._chapter(state, principal, chapter_id)
            if key:
                cached = lookup(state, chapter.project_id, principal.user.id, key, req_fp, self._now())
                if cached is not None:
                    return cached
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
            fingerprint = project_input_fingerprint(state, chapter.project_id)
            if check.input_fingerprint != fingerprint:
                raise DomainError(409, "CHECK_STALE", "项目输入已更新，请重新检查后再导出。")
            record = Export(new_id("export"), chapter.id, chapter.revision, check.content_hash,
                            check.id, f"icg-demo-{chapter.id}-r{chapter.revision}.docx",
                            chapter.title, chapter.content, input_fingerprint=fingerprint)
            state.exports[record.id] = record
            self._audit(state, principal, chapter, "export.create", {"export_id": record.id, "check_id": check.id})
            res = {"id": record.id, "filename": record.filename,
                   "download_url": f"/api/exports/{record.id}/file", "excludes_drafts": True,
                   "check_id": record.check_id, "revision": record.revision,
                   "content_hash": record.content_hash, "input_fingerprint": record.input_fingerprint}
            if key:
                remember(state, chapter.project_id, principal.user.id, key, req_fp, res, self._now())
            return res
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
            if record.input_fingerprint != project_input_fingerprint(state, chapter.project_id):
                raise DomainError(409, "EXPORT_STALE", "项目输入已更新，旧导出文件已过期。")
            self._audit(state, principal, chapter, "export.download", {"export_id": record.id})
            return record
        return self.repository.transaction(operation)
