# 为什么有这个文件：技术卷「开始生成」登记为服务端生成会话（PR-A）。
# 它解决什么问题：进度原先只活在编辑台的一条连接里，切页即断开、断开即取消。现在会话在后台线程里跑，
# 任务记录（recoverable_jobs，type=technical_volume）带已完成 x/y 节，任意页可查、可停；
# 节流事件留在进程内积压里，订阅者从头重放再跟随，离开编辑台只断订阅，不取消会话；「停止」走 cancelJob。
# 积压只在本进程内（部署为单进程）；同一项目只留最近一次会话的积压，更早的会话按任务终态补一条结束事件。
# 后续覆盖视图的实时行更新可往同一积压追加事件，订阅方式不变。

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Iterator

from .domain import DomainError, iso_time, new_id
from .parse_jobs import _mirror

KIND = "technical_volume"
TERMINAL = {"completed", "failed", "cancelled"}
INTERRUPTED = "生成会话已中断（服务重启或线程丢失），本次没有写入；请重新开始生成。"
KEEPALIVE_SECONDS = 10.0
log = logging.getLogger(__name__)


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


class ProgressBarrier:
    """写卷生产侧提交正文前的进度落库同步确认边界。

    生成事件由生产线程发出、消费线程（_run）逐个落库。生产线程在 commit_volume 之前必须确认
    消费侧已把 write_volume 期间发出的全部事件处理完毕（含最后一节的进度行同步）；
    任何落库失败或消费侧丢失都视为未确认，正文不得提交。计数即可，因为消费严格按 FIFO 顺序：
    第 k 个事件处理完意味着 1..k 的进度落库全部完成（或已失败）。"""

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._emitted = 0
        self._consumed = 0
        self._failure: Exception | None = None
        self._released = False

    def emitted(self) -> None:
        with self._cond:
            self._emitted += 1

    def consumed(self) -> None:
        with self._cond:
            self._consumed += 1
            self._cond.notify_all()

    def fail(self, error: Exception) -> None:
        with self._cond:
            if self._failure is None:
                self._failure = error
            self._cond.notify_all()

    def release(self) -> None:
        """消费侧无论因何结束都必须调用，保证生产侧不会空等。"""
        with self._cond:
            self._released = True
            self._cond.notify_all()

    def wait_caught_up(self) -> None:
        """阻塞到消费侧处理完调用时已发出的全部事件；落库失败或消费侧丢失则抛出。"""
        with self._cond:
            target = self._emitted
            while self._consumed < target and self._failure is None and not self._released:
                self._cond.wait(timeout=0.5)
            if self._failure is not None:
                raise DomainError(500, "INTERNAL_ERROR", "生成进度未能写入任务存储，正文不予提交。",
                                  {"reason": "job_persistence", "cause": str(self._failure)[:200]}) from self._failure
            if self._consumed < target:
                raise DomainError(500, "INTERNAL_ERROR", "生成进度确认通道已中断，正文不予提交。",
                                  {"reason": "job_persistence", "cause": "consumer_released"})


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
                try:
                    self.repository.save_job({
                        "id": job_id, "job_type": KIND, "project_id": project_id,
                        "status": created.get("status", "queued"), "progress": int(created.get("progress") or 0),
                        "step_name": created.get("message"), "created_by": principal.user.id,
                        "created_at": created.get("created_at"), "recoverable": True,
                    })
                except Exception as exc:
                    # 生成线程尚未开始，但条目态里已登记 queued；把它落成失败，避免留下永远“进行中”的孤儿。
                    try:
                        self._finish(job_id, "failed", "生成任务行写入失败，未开始生成。", {"done": 0, "total": 0, "failed": 0},
                                     error="INTERNAL_ERROR")
                    except Exception:
                        log.exception("failed to mark technical volume job %s failed after initial save failure", job_id)
                    raise self._job_persistence_error(type(exc).__name__) from exc
            backlog = _Backlog(job_id)
            superseded = self._latest.get(project_id)
            if superseded:
                self._backlogs.pop(superseded, None)
            self._latest[project_id] = job_id
            self._backlogs[job_id] = backlog
        threading.Thread(target=self._run, args=(job_id, prepared, backlog), daemon=True,
                         name="technical-volume").start()
        return job_id

    def _sync_job_row(self, job_id: str, *, missing_ok: bool = False) -> None:
        if not hasattr(self.repository, "update_job_progress"):
            return
        job = self.repository.read().recoverable_jobs.get(job_id) or {}
        if not job:
            if missing_ok:
                return
            raise self._job_persistence_error("任务在内存条目态缺失。")
        try:
            updated = self.repository.update_job_progress(
                job_id, int(job.get("progress") or 0), status=job.get("status"),
                step_name=job.get("message"), error_json=job.get("error"),
                result_json={"sections": job.get("sections")} if job.get("sections") else None,
            )
        except Exception as exc:
            raise self._job_persistence_error(type(exc).__name__) from exc
        if updated is False:
            raise self._job_persistence_error("任务行不存在或未完成更新。")

    @staticmethod
    def _job_persistence_error(cause: str) -> DomainError:
        return DomainError(500, "INTERNAL_ERROR", "生成进度未能写入任务存储，已停止生成。",
                           {"reason": "job_persistence", "cause": cause})

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
        self._sync_job_row(job_id, missing_ok=job is None)
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
        failure: Exception | None = None
        barrier = ProgressBarrier()
        self._live_stage[job_id] = {}
        try:
            self._update(job_id, self._begin)
            for event in self.workflow.iter_technical_stream(prepared, backlog.cancel, progress_barrier=barrier):
                # 落库先导：先持久化进度/终态，成功后才向订阅者发布事件。
                # 终态事件（volume.done 等）严禁在终态落库前到达订阅者，否则会出现
                # 「任务已失败但客户端已收到完成」的状态分裂。
                ended = self._track(job_id, tally, event) or ended
                backlog.push(event)
                barrier.consumed()
        except Exception as exc:
            # 进度/终态落库失败也属于生成失败：先停住写卷循环，再补一条失败事件。
            failure = exc
            barrier.fail(exc)
            backlog.cancel.set()
        finally:  # 未预料的异常也如实记失败，不留在“进行中”
            barrier.release()
            if not ended:
                current = self.repository.read().recoverable_jobs.get(job_id) or {}
                if current.get("status") == "completed":
                    # 终态事务已把 completed 写进条目态、但任务行同步失败：正文很可能已提交，
                    # 严禁继续声称完成；如实改记失败并说明正文去向，且必须覆盖未落库的完成态。
                    message = "正文已写入本卷，但完成状态未能写入任务存储；请核对编辑台正文，必要时重新生成。"
                else:
                    persistence = isinstance(failure, DomainError) and (failure.details or {}).get("reason") == "job_persistence"
                    message = str(failure) if persistence else "生成异常中断，本次不写入。"
                try:
                    # 终态落库先导：失败终态先落库再发布 volume.failed；二次落库失败也不能阻断
                    # 订阅者收到终结事件（生成确已失败是事实），但绝不能覆盖第一现场。
                    self._finish(job_id, "failed", message, tally, error="INTERNAL_ERROR", force=True)
                except Exception:
                    log.exception("failed to persist final failure state for technical volume job %s", job_id)
                backlog.push({"event": "volume.failed", "message": message})
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
                force: bool = False, **result: Any) -> None:
        def change(state, job):
            job.update({key: value for key, value in result.items() if value is not None})
            # force 只用于落库失败后的纠偏：completed/failed 的内存终态若是未同步成功事务行的残影，
            # 必须允许覆盖（否则任务永远声称完成）；cancelled 由用户取消路径独立落库，严禁覆盖。
            overridable = force and job["status"] in {"completed", "failed"} and status == "failed"
            if job["status"] in TERMINAL and not overridable:
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
        self._sync_job_row(job_id)
