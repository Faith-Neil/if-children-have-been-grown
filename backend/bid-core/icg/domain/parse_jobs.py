# 为什么有这个文件：招标文件解析作为后台任务运行，页面按任务进度显示（APP-M2-T020 / PRD v1.8 §5.12.4、§5.2.1）。
# 它解决什么问题：原先“开始解析”在一次请求里同步做完；扫描件交给 RAGFlow DeepDOC 后要几分钟，请求等满 ICG_TENDER_REMOTE_WAIT
# 仍没结果就返回“RAGFlow 解析中”，要人隔一会儿再点一次。现在启动后立即返回任务编号（202），后台线程按原解析流程反复取 RAGFlow 结果，
# 直到全部文件取回、失败、被取消或等满上限；每一步写入任务事件，页面经 SSE 实时看到，断线时改为轮询同一任务。
# 解析本身仍走 TenderOrchestrator.parse（同一套权限、版本、事务与抽取），这里只负责编排与进度，不另写一份解析。

from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .domain import DomainError, Principal, iso_time, new_id
from .idempotency import fingerprint, lookup, remember, validate_key

TERMINAL = {"completed", "failed", "cancelled"}


def poll_seconds() -> float:
    try:
        return max(0.05, float(os.environ.get("ICG_PARSE_JOB_POLL_SECONDS", "10")))
    except ValueError:
        return 10.0


def max_wait_seconds() -> float:
    try:
        return max(1.0, float(os.environ.get("ICG_PARSE_JOB_MAX_WAIT_SECONDS", "1800")))
    except ValueError:
        return 1800.0


def _mirror(job: dict) -> dict:
    """任务列表（GET /api/v1/jobs、工作区 jobs）用的摘要，与同步任务同一形状。"""
    return {key: job.get(key) for key in ("id", "project_id", "type", "status", "progress", "message",
                                          "created_at", "completed_at", "error")} | {"recoverable": False}


class ParseJobRunner:
    """每个进程一个；部署为单进程（/health 的 single_process）。"""

    def __init__(self, workflow: Any, jobs: Any) -> None:
        self.workflow = workflow
        self.jobs = jobs
        self.demo = workflow.demo
        self.repository = workflow.repository
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="parse-job")
        self._running: set[str] = set()
        self._lock = threading.Lock()

    # ------------------------------------------------------------ 启动

    def start(self, principal: Principal, project_id: str, payload: dict, expected: str | None, key: str | None) -> dict:
        key = validate_key(key)
        request_fingerprint = fingerprint("parse.job", payload, expected)

        def operation(state):
            project = self.demo._project(state, principal, project_id)
            self.workflow._authorize(state, principal, project_id, "parse.run", payload)
            replay = lookup(state, project_id, principal.user.id, key, request_fingerprint, self.demo._now())
            if replay is not None:
                return replay
            active = next((j for j in state.recoverable_jobs.values()
                           if j.get("project_id") == project_id and j.get("type") == "parse"
                           and j.get("status") not in TERMINAL), None)
            if active is not None:
                return self._public(active)  # 同一项目只跑一个解析任务，重复点击回到原任务
            self.workflow._version(project.revision, expected)
            workflow = state.workflows.get(project_id) or {}
            files = workflow.get("files") or {}
            selected = payload.get("file_ids")
            selected = list(files) if selected is None else selected
            if not selected or len(selected) != len(set(selected)):
                raise DomainError(422, "FILES_REQUIRED", "请选择至少一份未重复的招标文件。")
            if any(identity not in files for identity in selected):
                raise DomainError(404, "NOT_FOUND", "所选文件不存在或不属于本项目。")
            now = iso_time(self.demo._now())
            job_id = new_id("job")
            job = {"id": job_id, "project_id": project_id, "type": "parse", "status": "queued", "progress": 0,
                   "message": f"已排队：解析 {len(selected)} 份招标文件。", "created_at": now, "completed_at": None,
                   "error": None, "events": [], "recoverable": True, "live": True,
                   "created_by": principal.user.id, "file_ids": payload.get("file_ids")}
            state.recoverable_jobs[job_id] = job
            state.jobs[job_id] = _mirror(job)
            body = self._public(job)
            remember(state, project_id, principal.user.id, key, request_fingerprint, body, self.demo._now())
            return body

        body = self.repository.transaction(operation)
        self.submit(body["id"], principal)
        return body

    def submit(self, job_id: str, principal: Principal) -> None:
        with self._lock:
            if job_id in self._running:
                return
            self._running.add(job_id)
        self._executor.submit(self._run, job_id, principal)

    def _public(self, job: dict) -> dict:
        from .recoverable_jobs import _public
        return _public(job)

    # ------------------------------------------------------------ 后台执行

    def _update(self, job_id: str, change) -> dict | None:
        """在一个事务里改任务并同步任务列表摘要；返回改后的任务副本。"""
        def operation(state):
            job = state.recoverable_jobs.get(job_id)
            if job is None:
                return None
            change(state, job)
            state.jobs[job_id] = _mirror(job)
            return dict(job)
        return self.repository.transaction(operation)

    def _progress(self, job_id: str, progress: int, message: str) -> dict | None:
        def change(state, job):
            if job["status"] in TERMINAL:
                return
            job["progress"] = max(job.get("progress", 0), min(99, progress))
            job["message"] = message
            self.jobs._append(job, "job.progress", payload={"progress": job["progress"], "message": message})
        return self._update(job_id, change)

    def _finish(self, job_id: str, status: str, message: str, error: dict | None = None) -> None:
        def change(state, job):
            if job["status"] in TERMINAL:
                return
            previous = job["status"]
            now = iso_time(self.demo._now())
            job.update(status=status, progress=100, message=message, completed_at=now, error=error)
            self.jobs._append(job, "job.status_changed", payload={"from": previous, "to": status})
            if status == "completed":
                self.jobs._append(job, "job.progress", payload={"progress": 100, "message": message})
                self.jobs._append(job, "job.completed", payload={"status": "completed", "completed_at": now, "error": None})
            else:
                self.jobs._append(job, "job.failed", payload={"status": "failed", "completed_at": now,
                                                               "error": (error or {}).get("code", "INTERNAL_ERROR")})
        self._update(job_id, change)

    def _status(self, job_id: str) -> str | None:
        job = self.repository.read().recoverable_jobs.get(job_id)
        return job.get("status") if job else None

    def _run(self, job_id: str, principal: Principal) -> None:
        try:
            self._loop(job_id, principal)
        except Exception:  # 未预料的异常：任务如实记失败，不留在“进行中”
            self._finish(job_id, "failed", "解析任务异常中断，请重试；已取回的结果保留。",
                         {"code": "INTERNAL_ERROR", "message": "解析任务异常中断。"})
        finally:
            with self._lock:
                self._running.discard(job_id)
            if self._status(job_id) == "queued":
                self.submit(job_id, principal)  # 结束前恰好被重试：接着执行，不留在排队

    def _loop(self, job_id: str, principal: Principal) -> None:
        def begin(state, job):
            if job["status"] != "queued":
                return
            job["status"] = "running"
            job["message"] = "正在提取文字与抽取条款。"
            self.jobs._append(job, "job.status_changed", payload={"from": "queued", "to": "running"})
            self.jobs._append(job, "job.progress", payload={"progress": 5, "message": job["message"]})
            job["progress"] = 5
        job = self._update(job_id, begin)
        if job is None or job["status"] != "running":
            return
        project_id = job["project_id"]
        payload = {"file_ids": job["file_ids"]} if job.get("file_ids") is not None else {}
        started = time.monotonic()
        attempt = 0
        while True:
            if self._status(job_id) != "running":
                return  # 已取消
            attempt += 1
            try:
                result = self._parse_once(principal, project_id, payload)
            except DomainError as error:
                self._drop_inner_job({"job": {"id": (error.details or {}).get("job_id")}})
                self._finish(job_id, "failed", error.message, {"code": error.code, "message": error.message})
                return
            self._drop_inner_job(result)
            pending = self._pending_files(project_id, payload)
            if not pending:
                requirements = len(result.get("requirements") or [])
                facts = len(result.get("facts") or [])
                self._finish(job_id, "completed",
                             f"解析完成：{requirements} 条条款、{facts} 项事实，须人工逐项核对后确认。")
                return
            waited = time.monotonic() - started
            if waited >= max_wait_seconds():
                message = (f"{len(pending)} 份文件在 RAGFlow 识别已超过 {int(waited // 60)} 分钟仍未完成，任务停止；"
                           "可稍后重试接着取回结果。")
                self._finish(job_id, "failed", message, {"code": "PARSER_UNAVAILABLE", "message": message})
                return
            share = min(1.0, waited / max_wait_seconds())
            self._progress(job_id, 10 + int(share * 80),
                           f"RAGFlow 正在识别 {len(pending)} 份文件的版面与文字（已等待 {int(waited)} 秒，第 {attempt} 次取回）。")
            time.sleep(poll_seconds())

    def _parse_once(self, principal: Principal, project_id: str, payload: dict) -> dict:
        """按当前项目版本调用一次原解析；期间别人改了项目（版本冲突）时用新版本重试。"""
        for _ in range(3):
            revision = self.repository.read().projects[project_id].revision
            try:
                return self.workflow.parse(principal, project_id, dict(payload), str(revision), new_id("parse-job-call"))
            except DomainError as error:
                if error.code != "VERSION_CONFLICT":
                    raise
        raise DomainError(409, "VERSION_CONFLICT", "解析期间项目被反复修改，请稍后重试。")

    def _drop_inner_job(self, result: dict) -> None:
        """每次调用原解析会记一条同步解析任务；后台任务已代表这次解析，任务列表里不重复显示。"""
        inner = (result.get("job") or {}).get("id")
        if inner:
            self.repository.transaction(lambda state: state.jobs.pop(inner, None))

    def _pending_files(self, project_id: str, payload: dict) -> list[str]:
        files = (self.repository.read().workflows.get(project_id) or {}).get("files") or {}
        selected = payload.get("file_ids") or list(files)
        return [identity for identity in selected if (files.get(identity) or {}).get("status") == "parsing_remote"]
