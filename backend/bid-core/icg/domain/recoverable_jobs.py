# 为什么有这个文件：让选定的生成请求先返回 202，再按事件查询进度。
# 它解决什么问题：断线后仍能按任务编号查看状态；同步解析和同步生成保持原样。

from __future__ import annotations

import json
import os
import time

from fastapi import APIRouter, Depends, Header, Response
from fastapi.responses import StreamingResponse

from .domain import DomainError, Lease, iso_time, new_id
from .generation_context import plan_is_current
from .idempotency import IDEMPOTENCY_HEADER_DESCRIPTION, fingerprint, lookup, remember, validate_key
from .project_access import (
    READONLY_SYSTEM_ROLES, ROLE_COMPANY_ADMIN, ROLE_PLATFORM_ADMIN,
    lead, normalize_role, volume_owner, writable,
)
from .workflow_schemas import (
    CancelledEvent, CancelledPayload, CompletedEvent, CompletedPayload, FailedEvent, FailedPayload,
    JobStatus, ModelCallEvent, ProgressEvent, ProgressPayload, StartGenerationRequest, StatusChange,
    StatusChangedEvent, V1Error, v1_error_responses,
)

PUBLIC_FIELDS = (
    "id", "project_id", "type", "status", "progress", "message",
    "created_at", "completed_at", "error", "events", "recoverable",
    "allowed_actions", "allowedActions",
)
TERMINAL = {"completed", "failed", "cancelled"}

START_DESCRIPTION = (
    "只启动 confirmation 为 current 的章。未点名的未确认分册不阻断。"
    "点名了未确认章返回 409 PLAN_NOT_CONFIRMED；点名了过期章或来源已变的章返回 409 PLAN_STALE。"
    "If-Match 核对已确认大纲计划的 revision，与 getOutlinePlan 的 ETag 相同；不符返回 409 VERSION_CONFLICT。"
    "非本分册负责人返回 403 VOLUME_OWNER_REQUIRED。"
    "同一 Idempotency-Key 与同一指纹再次发送时，返回同一个 job id、同一个 Location 和 202。"
    "同键不同指纹返回 409 IDEMPOTENCY_CONFLICT。"
    "缺少或格式不符的 Idempotency-Key 返回 428 IDEMPOTENCY_KEY_REQUIRED。"
    "缺少 If-Match 返回 428 IF_MATCH_REQUIRED。"
    "模型在任务执行中失败时，已返回的 202 不变，失败记在 job.model_call.error_code，使用已冻结的 MODEL_UNAVAILABLE。"
    "尚未创建任务 id 时，模型不可用返回 502 MODEL_UNAVAILABLE。"
    "任务开始时对模型配置做快照，job.model_call 事件里的 provider 和 model 取自这份快照。"
    "敏感项目使用云端配置时，在创建任务前返回 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL。"
    "主密钥不可用时返回 503 SECRET_KEY_UNAVAILABLE。"
    "这两个 code 只引用 ISSUE-024 的冻结错误码表，本卡不保存模型配置。"
    "503 SECRET_KEY_UNAVAILABLE 不是瞬时故障，客户端不要自动重试，与 MODEL_UNAVAILABLE 相同。"
    "章节被锁返回 423 LOCK_HELD，锁丢失返回 423 LOCK_LOST，与旧路由一致。"
    "没有 fingerprint 字段。"
    "正式正文仍由同步 POST /generate 写入。本任务只在当前进程内存中，重启后消失。"
)
GET_DESCRIPTION = (
    "返回任务状态和 events。不属于调用者本公司或本项目的任务返回 404 NOT_FOUND，不区分不存在与无权。"
    "查询会把仍在排队的任务在本进程内推进到终态。这不是多进程恢复，也没有改同步解析。"
)
STREAM_DESCRIPTION = (
    "事件流。每条事件的 id 为 <job_id>:<seq>。请求头 Last-Event-ID 使用该 id 时，只发送更大的 seq。"
    "断线后也可 GET /api/v1/jobs/{job_id}。不新增 SSE 库。"
    "后台正在执行的任务（如招标解析任务）连接最多保持 ICG_SSE_HOLD_SECONDS（默认 25）秒：期间有新事件即推送，"
    "每 10 秒发一行注释保活，任务结束或到时后关闭，客户端带 Last-Event-ID 重连；其他任务发完已有事件即关闭。"
)
PARSE_JOB_DESCRIPTION = (
    "启动招标文件解析任务，立即返回 202 与任务（Location 为 GET /api/v1/jobs/{job_id}）。"
    "后台按 parseFiles 同一流程解析；交给 RAGFlow 识别的文件会反复取回，直到全部取回、失败、取消或等满 ICG_PARSE_JOB_MAX_WAIT_SECONDS（默认 1800）秒。"
    "权限与 parseFiles 相同（项目负责人）；If-Match 为项目版本；同一项目已有进行中的解析任务时返回该任务。"
    "进度经 streamJobEvents 推送：job.status_changed、job.progress、job.completed / job.failed / job.cancelled。"
)
CANCEL_DESCRIPTION = (
    "取消后的任务状态。已经结束的任务返回 409 VERSION_CONFLICT。"
    "缺少或格式不符的 Idempotency-Key 返回 428 IDEMPOTENCY_KEY_REQUIRED。"
    "同键不同指纹返回 409 IDEMPOTENCY_CONFLICT。成功响应不返回 Location。"
)


RETRY_DESCRIPTION = (
    "重试失败或已取消的长任务。仅项目负责人或管理员可触发，只读角色拦截 403。"
    "非终态失败（如 running/queued/completed）返回 409 VERSION_CONFLICT。"
    "缺少或格式不符的 Idempotency-Key 返回 428 IDEMPOTENCY_KEY_REQUIRED。"
)


def _public(job: dict) -> dict:
    res = {key: job[key] for key in PUBLIC_FIELDS if key in job}
    status = job.get("status")
    if status in ("queued", "running", "pending"):
        actions = ["cancel"]
    elif status in ("failed", "cancelled"):
        actions = ["retry"]
    else:
        actions = []
    res["allowed_actions"] = actions
    res["allowedActions"] = actions
    return res


def _sse(event: dict) -> str:
    payload = json.dumps(event, ensure_ascii=False)
    return f"id: {event['id']}\nevent: {event['type']}\ndata: {payload}\n\n"


def _resume_after(job_id: str, header: str | None) -> int:
    if not header:
        return 0
    prefix = job_id + ":"
    if not header.startswith(prefix):
        return 0
    raw = header[len(prefix):]
    return int(raw) if raw.isdigit() else 0


class RecoverableJobs:
    def __init__(self, workflow):
        self.workflow = workflow
        self.demo = workflow.demo
        self.repository = workflow.repository
        # 有真实后台执行的任务类型（APP-M2-T020）：重试后交回对应执行器
        self.runners: dict[str, object] = {}

    def start(self, principal, project_id: str, payload: dict, expected: str | None, key: str | None) -> dict:
        key = validate_key(key)
        if expected is None or not expected.strip():
            raise DomainError(428, "IF_MATCH_REQUIRED", "此操作需要最新版本号，请刷新页面再保存。")
        request_fingerprint = fingerprint("generation.start", payload, expected)

        def operation(state):
            project = self.demo._project(state, principal, project_id)
            if not writable(state, project_id, principal.user.id):
                raise DomainError(403, "PROJECT_WRITER_REQUIRED", "当前公司角色和项目角色只允许查看，不能办理此操作。")
            replay = lookup(state, project_id, principal.user.id, key, request_fingerprint, self.demo._now())
            if replay is not None:
                return replay
            workflow = state.workflows.get(project_id, {})
            revision = workflow.get("outline_revision")
            if not isinstance(revision, int) or revision < 1:
                raise DomainError(409, "PLAN_NOT_CONFIRMED", "大纲计划尚未确认，不能启动生成。")
            raw = expected.strip().strip('"')
            if not raw.isdigit() or int(raw) != revision:
                raise DomainError(409, "VERSION_CONFLICT", "数据已被更新，请刷新核对后再保存。", {"current_revision": revision})
            chapters = self._chapters(state, project_id, payload.get("chapter_ids"))
            self._owners_and_locks(state, principal, project_id, chapters)
            self._model_gate(project, state=state)
            now = iso_time(self.demo._now())
            job_id = new_id("job")
            provider = self.demo.model_provider

            bound_id = state.project_model_configs.get(project_id)
            active_config = None
            if bound_id and bound_id in state.model_configs:
                active_config = state.model_configs[bound_id]
            else:
                default_id = f"default-{project.company_id}"
                if default_id in state.model_configs:
                    active_config = state.model_configs[default_id]

            if active_config is not None:
                stream_enabled = active_config.stream_enabled
                json_mode_enabled = active_config.json_mode_enabled
                config_provider = active_config.provider
                config_model = active_config.model
                config_local = active_config.is_local
                config_real = (active_config.provider != "demo")
                config_base_url = active_config.base_url
                config_timeout = active_config.timeout_seconds
                config_tokens = active_config.max_tokens
                config_key = active_config.encrypted_api_key
            else:
                stream_enabled = bool(getattr(provider, "stream_enabled", True))
                json_mode_enabled = bool(getattr(provider, "json_mode_enabled", False))
                config_provider = str(getattr(provider, "name", "demo"))
                config_model = str(getattr(provider, "model", None) or getattr(provider, "model_name", None) or "demo")
                config_local = bool(getattr(provider, "is_local", False))
                config_real = bool(getattr(provider, "is_real_model", False))
                config_base_url = getattr(provider, "base_url", "")
                config_timeout = getattr(provider, "timeout_seconds", 60.0)
                config_tokens = getattr(provider, "max_tokens", 1024)
                config_key = None

            job = {
                "id": job_id, "project_id": project_id, "type": "generate", "status": "queued",
                "progress": 0, "message": "已排队。断线后查询 GET /api/v1/jobs/" + job_id + "。",
                "created_at": now, "completed_at": None, "error": None, "events": [],
                "recoverable": True, "chapter_ids": [chapter.id for chapter in chapters],
                "model_snapshot": {
                    "provider": config_provider,
                    "model": config_model,
                    "is_real_model": config_real,
                    "is_local": config_local,
                    "stream_enabled": stream_enabled,
                    "json_mode_enabled": json_mode_enabled,
                    "base_url": config_base_url,
                    "timeout_seconds": config_timeout,
                    "max_tokens": config_tokens,
                    "encrypted_api_key": config_key,
                },
            }
            state.recoverable_jobs[job_id] = job
            self.repository.save_job({
                "id": job_id,
                "job_type": "generate",
                "project_id": project_id,
                "status": "pending",
                "progress": 0,
                "step_name": "已排队。断线后查询 GET /api/v1/jobs/" + job_id + "。",
                "created_by": principal.user.id,
                "created_at": now,
                "recoverable": True,
            })
            body = _public(job)
            remember(state, project_id, principal.user.id, key, request_fingerprint, body, self.demo._now())
            return body
        return self.repository.transaction(operation)

    def get(self, principal, job_id: str) -> dict:
        def operation(state):
            job = self._visible(state, principal, job_id)
            self._advance(job)
            return _public(job)
        return self.repository.transaction(operation)

    def events(self, principal, job_id: str, last_event_id: str | None) -> list[str]:
        return self.events_since(principal, job_id, _resume_after(job_id, last_event_id))[0]

    def events_since(self, principal, job_id: str, after: int) -> tuple[list[str], int, bool]:
        """(新事件帧, 最后序号, 是否须保持连接)。只有后台正在执行、尚未结束的任务需要保持连接。"""
        def operation(state):
            job = self._visible(state, principal, job_id)
            self._advance(job)
            fresh = [event for event in job["events"] if event["seq"] > after]
            last = fresh[-1]["seq"] if fresh else after
            hold = bool(job.get("live")) and job["status"] not in TERMINAL
            return [_sse(event) for event in fresh], last, hold
        return self.repository.transaction(operation)

    def stream(self, principal, job_id: str, last_event_id: str | None):
        """先发已有事件；后台任务未结束时保持连接，期间推送新事件并保活。"""
        chunks, last, hold = self.events_since(principal, job_id, _resume_after(job_id, last_event_id))

        def frames():
            yield from chunks
            if not hold:
                return
            nonlocal last
            try:
                limit = max(1.0, float(os.environ.get("ICG_SSE_HOLD_SECONDS", "25")))
            except ValueError:
                limit = 25.0
            started = time.monotonic()
            quiet_since = started
            while time.monotonic() - started < limit:
                time.sleep(0.5)
                try:
                    fresh, last, keep = self.events_since(principal, job_id, last)
                except DomainError:
                    return  # 权限或任务已不可见：结束本次连接
                if fresh:
                    yield from fresh
                    quiet_since = time.monotonic()
                elif time.monotonic() - quiet_since >= 10:
                    yield ": keep-alive\n\n"
                    quiet_since = time.monotonic()
                if not keep:
                    return
        return frames()

    def cancel(self, principal, job_id: str, key: str | None) -> dict:
        key = validate_key(key)
        request_fingerprint = fingerprint("job.cancel:" + job_id, {}, None)

        def operation(state):
            job = self._visible(state, principal, job_id)
            if not writable(state, job["project_id"], principal.user.id):
                raise DomainError(403, "PROJECT_WRITER_REQUIRED", "当前公司角色和项目角色只允许查看，不能取消任务。")
            replay = lookup(state, job["project_id"], principal.user.id, key, request_fingerprint, self.demo._now())
            if replay is not None:
                return replay
            if job["status"] in TERMINAL:
                raise DomainError(409, "VERSION_CONFLICT", "任务已经结束，不能取消。")
            previous = job["status"]
            now = iso_time(self.demo._now())
            job["status"] = "cancelled"
            job["progress"] = 100
            job["message"] = "任务已取消。正式正文没有修改。"
            job["completed_at"] = now
            job["error"] = None
            self._append(job, "job.status_changed", payload={"from": previous, "to": "cancelled"})
            self._append(job, "job.cancelled", payload={"status": "cancelled", "completed_at": now, "error": None})
            self.repository.update_job_progress(job_id, progress=100, status="cancelled", step_name="任务已取消。正式正文没有修改。")
            if job_id in state.jobs:
                state.jobs[job_id]["status"] = "cancelled"
                state.jobs[job_id]["progress"] = 100
                state.jobs[job_id]["message"] = "任务已取消。正式正文没有修改。"
                state.jobs[job_id]["completed_at"] = now
            body = _public(job)
            remember(state, job["project_id"], principal.user.id, key, request_fingerprint, body, self.demo._now())
            return body
        return self.repository.transaction(operation)

    def retry(self, principal, job_id: str, key: str | None) -> dict:
        key = validate_key(key)
        request_fingerprint = fingerprint("job.retry:" + job_id, {}, None)

        def operation(state):
            job = self._visible(state, principal, job_id)
            norm = normalize_role(principal.user.role)
            is_lead = lead(state, job["project_id"], principal.user.id)
            is_admin = norm in (ROLE_COMPANY_ADMIN, ROLE_PLATFORM_ADMIN)
            if not (is_lead or is_admin) or norm in READONLY_SYSTEM_ROLES:
                raise DomainError(403, "PROJECT_LEAD_REQUIRED", "仅项目负责人或管理员可重试任务。")

            replay = lookup(state, job["project_id"], principal.user.id, key, request_fingerprint, self.demo._now())
            if replay is not None:
                return replay

            if job["status"] not in ("failed", "cancelled"):
                raise DomainError(409, "VERSION_CONFLICT", "只有失败或已取消的任务可以重试。")

            previous = job["status"]
            now = iso_time(self.demo._now())
            job["status"] = "queued"
            job["progress"] = 0
            job["message"] = "任务已重置排队，准备重新执行。"
            job["completed_at"] = None
            job["error"] = None
            self._append(job, "job.status_changed", payload={"from": previous, "to": "queued"})
            self._append(job, "job.progress", payload={"progress": 0, "message": "任务已重置排队，准备重新执行。"})

            self.repository.update_job_progress(
                job_id,
                progress=0,
                status="pending",
                step_name="任务已重新排队",
                error_json=None,
                result_json=None,
            )
            if job_id in state.jobs:
                state.jobs[job_id]["status"] = "queued"
                state.jobs[job_id]["progress"] = 0
                state.jobs[job_id]["message"] = "任务已重新排队。"
                state.jobs[job_id]["error"] = None
                state.jobs[job_id]["completed_at"] = None

            body = _public(job)
            remember(state, job["project_id"], principal.user.id, key, request_fingerprint, body, self.demo._now())
            return body
        body = self.repository.transaction(operation)
        runner = self.runners.get(body.get("type"))
        if runner is not None and body.get("status") == "queued":
            runner.submit(job_id, principal)
        return body

    def _chapters(self, state, project_id, selected):
        known = [chapter for chapter in state.chapters.values() if chapter.project_id == project_id]
        by_id = {chapter.id: chapter for chapter in known}
        if selected:
            if len(selected) != len(set(selected)) or set(selected) - set(by_id):
                raise DomainError(404, "NOT_FOUND", "所选章节不存在或不属于本项目。")
            chosen = [by_id[identity] for identity in selected]
            for chapter in chosen:
                kind = self._confirmation(state, project_id, chapter.id)
                if kind == "unconfirmed":
                    raise DomainError(409, "PLAN_NOT_CONFIRMED", "点名的章节尚未确认，整次请求不接受。")
                if kind != "current":
                    raise DomainError(409, "PLAN_STALE", "点名的章节方案已过期或来源已变，整次请求不接受。")
            return chosen
        current = [chapter for chapter in known if self._confirmation(state, project_id, chapter.id) == "current"]
        if not current:
            raise DomainError(409, "PLAN_NOT_CONFIRMED", "没有 confirmation 为 current 的章节可启动。")
        return current

    @staticmethod
    def _confirmation(state, project_id, chapter_id) -> str:
        workflow = state.workflows.get(project_id, {})
        saved = workflow.get("writing_plan", {}).get("chapters", {}).get(chapter_id, {})
        if not saved.get("confirmed_at"):
            return "unconfirmed"
        if plan_is_current(state, project_id, chapter_id):
            return "current"
        return "stale"

    def _owners_and_locks(self, state, principal, project_id, chapters):
        now = self.demo._now()
        for chapter in chapters:
            if not volume_owner(state, project_id, chapter.volume, principal.user.id):
                raise DomainError(403, "VOLUME_OWNER_REQUIRED", "只能启动自己负责的分册。")
            lock = chapter.lock
            if not isinstance(lock, Lease):
                continue
            if lock.expires_at <= now and lock.owner_id == principal.user.id:
                raise DomainError(423, "LOCK_LOST", "编辑权已失效，请重新取得后再启动生成。")
            if lock.expires_at > now and lock.owner_id != principal.user.id:
                raise DomainError(423, "LOCK_HELD", "章节正在被其他人编辑。")

    def _model_gate(self, project, state=None):
        if state is not None:
            bound_id = state.project_model_configs.get(project.id)
            cfg = None
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
                        raise DomainError(503, "SECRET_KEY_UNAVAILABLE", "主密钥不可用，任务尚未创建。")
        provider = self.demo.model_provider
        if getattr(provider, "secret_key_available", True) is False:
            raise DomainError(503, "SECRET_KEY_UNAVAILABLE", "主密钥不可用，任务尚未创建。")
        if (project.sensitive and getattr(provider, "is_real_model", None) is not False
                and not getattr(provider, "is_local", False)):
            raise DomainError(403, "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL", "敏感项目只能使用本地模型。")
        if getattr(provider, "available", True) is False:
            raise DomainError(502, "MODEL_UNAVAILABLE", "模型不可用，任务尚未创建。")

    def _visible(self, state, principal, job_id: str) -> dict:
        job = state.recoverable_jobs.get(job_id)
        if job is None:
            persisted = self.repository.read_job(job_id) or state.jobs.get(job_id)
            if persisted:
                try:
                    self.demo._project(state, principal, persisted["project_id"])
                except DomainError as error:
                    if error.code == "NOT_FOUND":
                        raise DomainError(404, "NOT_FOUND", "未找到有权访问的任务。") from error
                    raise
                now_str = iso_time(self.demo._now())
                raw_status = persisted.get("status", "queued")
                status = "queued" if raw_status == "pending" else raw_status
                progress = int(persisted.get("progress", 0))
                message = persisted.get("step_name") or "后台任务处理中"
                error = persisted.get("error_json") or persisted.get("error")
                completed_at = str(persisted.get("updated_at") or now_str) if status in TERMINAL else None
                job = {
                    "id": persisted["id"],
                    "project_id": persisted["project_id"],
                    "type": persisted.get("job_type", persisted.get("type", "generate")),
                    "status": status,
                    "progress": progress,
                    "message": message,
                    "created_at": str(persisted.get("created_at") or now_str),
                    "completed_at": completed_at,
                    "error": error,
                    "events": [],
                    "recoverable": True,
                }
                job["events"].append({
                    "seq": 1,
                    "id": f"{job['id']}:1",
                    "occurred_at": str(persisted.get("created_at") or now_str),
                    "type": "job.progress",
                    "payload": {"progress": progress, "message": message},
                })
                state.recoverable_jobs[job_id] = job
                return job
            raise DomainError(404, "NOT_FOUND", "未找到有权访问的任务。")
        try:
            self.demo._project(state, principal, job["project_id"])
        except DomainError as error:
            if error.code == "NOT_FOUND":
                raise DomainError(404, "NOT_FOUND", "未找到有权访问的任务。") from error
            raise
        return job

    def _advance(self, job: dict) -> None:
        # 只推进生成任务的进程内占位流程；有后台执行器的任务（如解析）由执行器自己推进
        if job["status"] != "queued" or job.get("type") in self.runners:
            return
        now = iso_time(self.demo._now())
        job["status"] = "running"
        job["message"] = "正在记录生成任务。正式正文不在这里写入。"
        self._append(job, "job.status_changed", payload={"from": "queued", "to": "running"})
        self._append(job, "job.progress", payload={"progress": 40, "message": "已读取任务开始时的模型快照。"})
        job["progress"] = 40
        self.repository.update_job_progress(job["id"], progress=40, status="running", step_name="已读取任务开始时的模型快照。")
        snapshot = job.get("model_snapshot")
        if snapshot is None:
            finished = iso_time(self.demo._now())
            job["status"] = "completed"
            job["progress"] = 100
            job["message"] = "生成任务已结束。"
            job["completed_at"] = finished
            job["error"] = None
            self._append(job, "job.progress", payload={"progress": 100, "message": job["message"]})
            self._append(job, "job.completed", payload={"status": "completed", "completed_at": finished, "error": None})
            self.repository.update_job_progress(job["id"], progress=100, status="completed", step_name=job["message"])
            return

        started = self.demo._now()
        error_code = None
        provider = self.demo.resolve_provider_from_snapshot(snapshot)
        try:
            provider.suggest(
                "按已确认方案组织候选；不能编造证据。本调用只用于任务事件，不写入正文。",
                job["id"])
        except Exception:
            error_code = "MODEL_UNAVAILABLE"
        duration_ms = max(0, int((self.demo._now() - started) * 1000))
        model_call_kwargs = {
            "provider": snapshot["provider"],
            "model": snapshot["model"],
            "is_real_model": snapshot.get("is_real_model", False),
            "is_local": snapshot.get("is_local", False),
        }
        self._append(job, "job.model_call", **model_call_kwargs, duration_ms=duration_ms, error_code=error_code)
        if error_code:
            self._finish_failed(job, error_code, "候选生成失败，正式正文没有修改。")
            return
        finished = iso_time(self.demo._now())
        job["status"] = "completed"
        job["progress"] = 100
        job["message"] = "生成任务已结束。正式正文仍由同步生成入口写入，本章正文没有在本任务中修改。"
        job["completed_at"] = finished
        job["error"] = None
        self._append(job, "job.progress", payload={"progress": 100, "message": job["message"]})
        self._append(job, "job.completed", payload={"status": "completed", "completed_at": finished, "error": None})
        self.repository.update_job_progress(job["id"], progress=100, status="completed", step_name=job["message"])

    def _finish_failed(self, job, code, message):
        finished = iso_time(self.demo._now())
        job["status"] = "failed"
        job["progress"] = 100
        job["message"] = message
        job["completed_at"] = finished
        job["error"] = {"code": code, "message": message}
        self._append(job, "job.failed", payload={"status": "failed", "completed_at": finished, "error": code})
        self.repository.update_job_progress(job["id"], progress=100, status="failed", step_name=message, error_json=job["error"])

    def _append(self, job: dict, kind: str, payload: dict | None = None, **fields) -> None:
        seq = len(job["events"]) + 1
        event = {"seq": seq, "id": f"{job['id']}:{seq}", "occurred_at": iso_time(self.demo._now()), "type": kind}
        if payload is not None:
            event["payload"] = payload
        event.update(fields)
        models = {
            "job.model_call": ModelCallEvent,
            "job.status_changed": StatusChangedEvent,
            "job.progress": ProgressEvent,
            "job.completed": CompletedEvent,
            "job.failed": FailedEvent,
            "job.cancelled": CancelledEvent,
        }
        dumped = models[kind].model_validate(event).model_dump(mode="json", by_alias=True)
        if kind == "job.status_changed":
            StatusChange.model_validate(dumped["payload"])
        elif kind == "job.progress":
            ProgressPayload.model_validate(dumped["payload"])
        elif kind == "job.completed":
            CompletedPayload.model_validate(dumped["payload"])
        elif kind == "job.failed":
            FailedPayload.model_validate(dumped["payload"])
        elif kind == "job.cancelled":
            CancelledPayload.model_validate(dumped["payload"])
        job["events"].append(dumped)


def include_recoverable_routes(application, workflow, current_user):
    from .parse_jobs import ParseJobRunner
    from .workflow_schemas import ParseRequest
    jobs = RecoverableJobs(workflow)
    parse_runner = ParseJobRunner(workflow, jobs)
    jobs.runners["parse"] = parse_runner
    application.state.parse_job_runner = parse_runner
    router = APIRouter(prefix="/api/v1")
    start_errors = v1_error_responses(401, 403, 404, 409, 422, 428, 500, 502, 423, 503)
    start_errors[503] = {
        "model": V1Error,
        "description": (
            "主密钥不可用返回 SECRET_KEY_UNAVAILABLE。不是瞬时故障，客户端不要自动重试，与 MODEL_UNAVAILABLE 相同。"
            "该码引用 ISSUE-024 的冻结错误码表，本卡不保存模型配置。"
        ),
    }
    start_errors[423] = {
        "model": V1Error,
        "description": "章节被锁返回 LOCK_HELD，锁丢失返回 LOCK_LOST。这两个 code 已在冻结码表中，对应 423。",
    }
    start_errors[202] = {
        "description": "已接受。生成是长任务。Location 指向 GET /api/v1/jobs/{job_id}。同一幂等键重放时 Location 与 job id 不变，状态仍是 202。",
        "headers": {"Location": {
            "required": True,
            "description": "任务状态地址，形式为 /api/v1/jobs/{job_id}，job_id 与响应体 id 相同。",
            "schema": {"type": "string"},
        }},
    }

    @router.post("/projects/{project_id}/generation/start", status_code=202, response_model=JobStatus,
                 operation_id="startGeneration", description=START_DESCRIPTION, summary="Start Generation",
                 responses=start_errors)
    def start_generation(project_id: str, body: StartGenerationRequest, response: Response,
                         user=Depends(current_user), if_match: str | None = Header(default=None),
                         idempotency_key: str | None = Header(default=None, alias="Idempotency-Key",
                                                              description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        result = jobs.start(user, project_id, body.model_dump(), if_match, idempotency_key)
        response.headers["Location"] = "/api/v1/jobs/" + result["id"]
        response.status_code = 202
        return result

    @router.post("/projects/{project_id}/parse/jobs", status_code=202, response_model=JobStatus,
                 operation_id="startParseJob", description=PARSE_JOB_DESCRIPTION, summary="Start Parse Job",
                 responses={202: {"description": "已接受。Location 指向 GET /api/v1/jobs/{job_id}。",
                                  "headers": {"Location": {"required": True, "schema": {"type": "string"},
                                                           "description": "任务状态地址 /api/v1/jobs/{job_id}"}}},
                            **v1_error_responses(401, 403, 404, 409, 422, 428, 500)})
    def start_parse_job(project_id: str, body: ParseRequest, response: Response, user=Depends(current_user),
                        if_match: str | None = Header(default=None),
                        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key",
                                                             description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        result = parse_runner.start(user, project_id, body.model_dump(), if_match, idempotency_key)
        response.headers["Location"] = "/api/v1/jobs/" + result["id"]
        response.status_code = 202
        return result

    @router.get("/jobs/{job_id}", response_model=JobStatus, operation_id="getJob", description=GET_DESCRIPTION,
                summary="Get Job", responses=v1_error_responses(401, 404, 422, 500))
    def get_job(job_id: str, user=Depends(current_user)):
        return jobs.get(user, job_id)

    @router.get("/jobs/{job_id}/events", operation_id="streamJobEvents", description=STREAM_DESCRIPTION,
                summary="Stream Job Events", response_class=StreamingResponse,
                responses={200: {"description": "text/event-stream。id 为 <job_id>:<seq>。",
                                 "content": {"text/event-stream": {"schema": {"type": "string"}}}},
                           **v1_error_responses(401, 404, 422, 500)})
    def stream_job_events(job_id: str, user=Depends(current_user),
                          last_event_id: str | None = Header(default=None, alias="Last-Event-ID")):
        return StreamingResponse(jobs.stream(user, job_id, last_event_id), media_type="text/event-stream",
                                 headers={"X-Accel-Buffering": "no"})

    @router.post("/jobs/{job_id}/cancel", response_model=JobStatus, operation_id="cancelJob",
                 description=CANCEL_DESCRIPTION, summary="Cancel Job",
                 responses=v1_error_responses(401, 403, 404, 409, 422, 428, 500))
    def cancel_job(job_id: str, user=Depends(current_user),
                   idempotency_key: str | None = Header(default=None, alias="Idempotency-Key",
                                                        description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return jobs.cancel(user, job_id, idempotency_key)

    @router.post("/jobs/{job_id}/retry", response_model=JobStatus, operation_id="retryJob",
                 description=RETRY_DESCRIPTION, summary="Retry Job",
                 responses=v1_error_responses(401, 403, 404, 409, 422, 428, 500))
    def retry_job(job_id: str, user=Depends(current_user),
                  idempotency_key: str | None = Header(default=None, alias="Idempotency-Key",
                                                       description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return jobs.retry(user, job_id, idempotency_key)

    application.include_router(router)
