# 为什么有这个文件：技术卷「开始生成」登记为服务端生成会话（PR-A）。
# 它解决什么问题：进度原先只活在编辑台的一条连接里，切页即断开、断开即取消。现在会话在后台线程里跑，
# 任务记录（recoverable_jobs，type=technical_volume）带已完成 x/y 节，任意页可查、可停；
# 节流事件留在进程内积压里，订阅者从头重放再跟随，离开编辑台只断订阅，不取消会话；「停止」走 cancelJob。
# 积压只在本进程内（部署为单进程）；同一项目只留最近一次会话的积压，更早的会话按任务终态补一条结束事件。
# 后续覆盖视图的实时行更新可往同一积压追加事件，订阅方式不变。

from __future__ import annotations

import threading
import time
from typing import Any, Iterator

from .domain import iso_time, new_id
from .parse_jobs import _mirror

KIND = "technical_volume"
TERMINAL = {"completed", "failed", "cancelled"}
INTERRUPTED = "生成会话已中断（服务重启或线程丢失），本次没有写入；请重新开始生成。"
KEEPALIVE_SECONDS = 10.0


class _Backlog:
    """一次会话的节流事件与取消信号。"""

    def __init__(self, job_id: str) -> None:
        self.events: list[dict] = [{"event": "session.started", "job_id": job_id}]
        self.closed = False
        self.cancel = threading.Event()
        self.cond = threading.Condition()

    def push(self, event: dict) -> None:
        with self.cond:
            self.events.append(event)
            self.cond.notify_all()

    def close(self) -> None:
        with self.cond:
            self.closed = True
            self.cond.notify_all()


def _tally_message(tally: dict, *, stage: str | None = None, title: str | None = None) -> str:
    from .technical_section_stages import stage_progress_message

    return stage_progress_message(tally, stage=stage, title=title)


class TechnicalVolumeSessions:
    def __init__(self, workflow: Any, jobs: Any) -> None:
        self.workflow = workflow
        self.jobs = jobs
        self.demo = workflow.demo
        self.repository = workflow.repository
        self._backlogs: dict[str, _Backlog] = {}
        self._latest: dict[str, str] = {}
        self._live_stage: dict[str, dict[str, str]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------ 启动与停止

    def start(self, prepared: dict) -> str:
        """同一项目已有进行中的会话时回到该会话；否则登记任务并在后台开写。返回任务编号。"""
        project_id = prepared["project_id"]
        principal = prepared["principal"]
        with self._lock:
            def operation(state):
                active = next((job for job in state.recoverable_jobs.values()
                               if job.get("project_id") == project_id and job.get("type") == KIND
                               and job.get("status") not in TERMINAL), None)
                if active is not None:
                    backlog = self._backlogs.get(active["id"])
                    if backlog is not None and not backlog.closed:
                        return active["id"], False
                    self._interrupt(active)
                    state.jobs[active["id"]] = _mirror(active)
                job_id = new_id("job")
                job = {
                    "id": job_id, "project_id": project_id, "type": KIND, "status": "queued", "progress": 0,
                    "message": "已排队：技术卷生成。", "created_at": iso_time(self.demo._now()),
                    "completed_at": None, "error": None, "events": [], "recoverable": True, "live": True,
                    "retryable": False, "created_by": principal.user.id,
                    "sections": {"done": 0, "total": 0, "failed": 0},
                }
                state.recoverable_jobs[job_id] = job
                state.jobs[job_id] = _mirror(job)
                return job_id, True

            job_id, fresh = self.repository.transaction(operation)
            if not fresh:
                return job_id
            if hasattr(self.repository, "save_job"):
                created = self.repository.read().recoverable_jobs.get(job_id) or {}
                self.repository.save_job({
                    "id": job_id, "job_type": KIND, "project_id": project_id,
                    "status": created.get("status", "queued"), "progress": int(created.get("progress") or 0),
                    "step_name": created.get("message"), "created_by": principal.user.id,
                    "created_at": created.get("created_at"), "recoverable": True,
                })
            backlog = _Backlog(job_id)
            superseded = self._latest.get(project_id)
            if superseded:
                self._backlogs.pop(superseded, None)
            self._latest[project_id] = job_id
            self._backlogs[job_id] = backlog
        threading.Thread(target=self._run, args=(job_id, prepared, backlog), daemon=True,
                         name="technical-volume").start()
        return job_id

    def _sync_job_row(self, job_id: str) -> None:
        if not hasattr(self.repository, "update_job_progress"):
            return
        job = self.repository.read().recoverable_jobs.get(job_id) or {}
        if not job:
            return
        self.repository.update_job_progress(
            job_id, int(job.get("progress") or 0), status=job.get("status"),
            step_name=job.get("message"), error_json=job.get("error"),
            result_json={"sections": job.get("sections")} if job.get("sections") else None,
        )

    def cancel(self, job_id: str) -> None:
        """cancelJob 已把任务记为取消；这里让模型停下，本次不写入。"""
        backlog = self._backlogs.get(job_id)
        if backlog is not None:
            backlog.cancel.set()

    # ------------------------------------------------------------ 订阅

    def frames(self, job_id: str) -> Iterator[str]:
        """先重放积压，再发 session.live，之后跟随实时事件直到会话结束。
        空串是让路由检查断开的节拍，不是事件。关闭本迭代器只结束订阅。"""
        from .technical_volume import format_section_sse

        backlog = self._backlogs.get(job_id)
        if backlog is None:
            for event in self._ended(job_id):
                yield format_section_sse(event)
            return
        with backlog.cond:
            index = len(backlog.events)
            sent = backlog.events[:index]
        for event in sent:
            yield format_section_sse(event)
        yield format_section_sse({"event": "session.live"})
        quiet = time.monotonic()
        while True:
            with backlog.cond:
                if index >= len(backlog.events) and not backlog.closed:
                    backlog.cond.wait(timeout=1.0)
                fresh = backlog.events[index:]
                index += len(fresh)
                closed = backlog.closed
            for event in fresh:
                yield format_section_sse(event)
            if fresh:
                quiet = time.monotonic()
            elif closed:
                return
            elif time.monotonic() - quiet >= KEEPALIVE_SECONDS:
                yield ": keep-alive\n\n"
                quiet = time.monotonic()
            else:
                yield ""

    def _ended(self, job_id: str) -> list[dict]:
        """积压已不在本进程：按任务终态补一条结束事件；仍标进行中的就是孤儿，如实记中断。"""
        def operation(state):
            job = state.recoverable_jobs.get(job_id)
            if job is None:
                return None
            if job["status"] not in TERMINAL:
                self._interrupt(job)
                state.jobs[job_id] = _mirror(job)
            return dict(job)

        job = self.repository.transaction(operation)
        events: list[dict] = [{"event": "session.started", "job_id": job_id}, {"event": "session.live"}]
        if job is None:
            return events
        if job["status"] == "completed":
            events.append({"event": "volume.done", "replay": True, "chapter_id": job.get("chapter_id") or "",
                           "revision": job.get("revision"), "failed": list(job.get("failed_sections") or [])})
        elif job["status"] == "cancelled":
            events.append({"event": "volume.cancelled", "chapter_id": job.get("chapter_id") or ""})
        else:
            events.append({"event": "volume.failed", "message": job.get("message") or INTERRUPTED})
        return events

    # ------------------------------------------------------------ 后台执行

    def _run(self, job_id: str, prepared: dict, backlog: _Backlog) -> None:
        tally = {"done": 0, "total": 0, "failed": 0}
        ended = False
        self._live_stage[job_id] = {}
        self._update(job_id, self._begin)
        try:
            for event in self.workflow.iter_technical_stream(prepared, backlog.cancel):
                backlog.push(event)
                ended = self._track(job_id, tally, event) or ended
        finally:  # 未预料的异常也如实记失败，不留在“进行中”
            if not ended:
                backlog.push({"event": "volume.failed", "message": "生成异常中断，本次不写入。"})
                self._finish(job_id, "failed", "生成异常中断，本次不写入。", tally, error="INTERNAL_ERROR")
            backlog.close()

    def _begin(self, state, job: dict) -> None:
        if job["status"] != "queued":
            return
        job["status"] = "running"
        job["progress"] = 5
        job["message"] = "正在按确认目录生成技术卷。"
        self.jobs._append(job, "job.status_changed", payload={"from": "queued", "to": "running"})
        self.jobs._append(job, "job.progress", payload={"progress": 5, "message": job["message"]})

    def _track(self, job_id: str, tally: dict, event: dict) -> bool:
        """节计数进任务记录；返回是否已是整卷结束事件。"""
        kind = event.get("event")
        if kind == "sections.fanout":
            tally["total"] = len(event.get("section_ids") or [])
        elif kind == "section.done":
            tally["done"] += 1
        elif kind == "section.failed":
            tally["failed"] += 1
        elif kind == "volume.done":
            failed = list(event.get("failed") or [])
            message = "技术卷已写入：" + _tally_message(tally) + "。"
            self._finish(job_id, "completed", message, tally, chapter_id=event.get("chapter_id"),
                         revision=event.get("revision"), failed_sections=failed)
            return True
        elif kind == "volume.cancelled":
            self._finish(job_id, "cancelled", "已停止。本次生成没有写入章节。", tally)
            return True
        elif kind == "volume.failed":
            self._finish(job_id, "failed", str(event.get("message") or "生成失败"), tally, error="GENERATION_FAILED")
            return True
        elif kind == "section.started":
            live = self._live_stage.setdefault(job_id, {})
            if event.get("title"):
                live["title"] = str(event["title"])
            live["stage"] = "retrieve"
        elif kind == "task.patched" and event.get("stage"):
            live = self._live_stage.setdefault(job_id, {})
            live["stage"] = str(event["stage"])
            if event.get("section_title"):
                live["title"] = str(event["section_title"])
        else:
            return False
        self._progress(job_id, tally)
        return False

    def _progress(self, job_id: str, tally: dict) -> None:
        live = self._live_stage.get(job_id) or {}

        def change(state, job):
            if job["status"] in TERMINAL:
                return
            settled = tally["done"] + tally["failed"]
            share = settled / tally["total"] if tally["total"] else 0.0
            job["sections"] = dict(tally)
            job["progress"] = max(job.get("progress", 0), min(95, 5 + int(share * 90)))
            job["message"] = _tally_message(tally, stage=live.get("stage"), title=live.get("title"))
            self.jobs._append(job, "job.progress", payload={"progress": job["progress"], "message": job["message"]})
        self._update(job_id, change)

    def _finish(self, job_id: str, status: str, message: str, tally: dict, error: str | None = None,
                **result: Any) -> None:
        def change(state, job):
            job.update({key: value for key, value in result.items() if value is not None})
            if job["status"] in TERMINAL:
                if job["status"] == "cancelled" and status == "completed":
                    job["message"] = "停止请求到达前本次正文已写入。"
                return
            previous = job["status"]
            now = iso_time(self.demo._now())
            job.update(status=status, progress=100, message=message, completed_at=now, sections=dict(tally),
                       error={"code": error, "message": message} if error else None)
            self.jobs._append(job, "job.status_changed", payload={"from": previous, "to": status})
            if status == "completed":
                self.jobs._append(job, "job.progress", payload={"progress": 100, "message": message})
                self.jobs._append(job, "job.completed",
                                  payload={"status": "completed", "completed_at": now, "error": None, "message": message})
            elif status == "cancelled":
                self.jobs._append(job, "job.cancelled", payload={"status": "cancelled", "completed_at": now, "error": None})
            else:
                self.jobs._append(job, "job.failed", payload={"status": "failed", "completed_at": now, "error": error})
        self._update(job_id, change)

    def _interrupt(self, job: dict) -> None:
        previous = job["status"]
        now = iso_time(self.demo._now())
        job.update(status="failed", progress=100, message=INTERRUPTED, completed_at=now,
                   error={"code": "GENERATION_INTERRUPTED", "message": INTERRUPTED})
        self.jobs._append(job, "job.status_changed", payload={"from": previous, "to": "failed"})
        self.jobs._append(job, "job.failed", payload={"status": "failed", "completed_at": now,
                                                       "error": "GENERATION_INTERRUPTED"})

    def _update(self, job_id: str, change) -> None:
        def operation(state):
            job = state.recoverable_jobs.get(job_id)
            if job is None:
                return
            change(state, job)
            state.jobs[job_id] = _mirror(job)
        self.repository.transaction(operation)
