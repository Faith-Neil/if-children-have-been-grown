# 为什么有这个文件：核对技术卷生成会话（PR-A）。
# 它解决什么问题：「开始生成」登记为后台任务，任意页能查到已完成 x/y 节；
# 客户端断开订阅不取消服务端会话；「停止」走任务取消；回到编辑台可重新订阅同一会话的节流事件。

from __future__ import annotations

import json
import threading
import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from test_reference_flow import login
from test_technical_sources import _confirm_plan, _parse_clause

SUFFIX = "按本次招标要求逐条写巡检步骤，并留下运行记录供验收核对，过程可追溯。本节完成。"


def _frames(raw: str) -> list[dict]:
    return [json.loads(block.split("data: ", 1)[1]) for block in raw.split("\n\n") if "data: " in block]


class GatedModel:
    """每节先吐一段，再等 gate 放行；取消时立即停。"""
    is_real_model = True
    is_local = True
    stream_enabled = True
    base_url = "http://127.0.0.1:9"

    def __init__(self) -> None:
        self.gate = threading.Event()
        self.started = threading.Event()

    def suggest(self, *_args):
        raise AssertionError("流式生成不应整段 suggest")

    def stream_suggest(self, instruction, content, *, on_delta, cancel=None):
        from icg.infra.openai_model import ModelCancelled
        title = content.split("章节任务：", 1)[1].split("\n", 1)[0]
        text = f"针对「{title}」{SUFFIX}"
        on_delta(text[:6])
        self.started.set()
        deadline = time.monotonic() + 10
        while not self.gate.is_set():
            if cancel is not None and cancel.is_set():
                raise ModelCancelled("cancelled")
            if time.monotonic() > deadline:
                raise AssertionError("gate 没有放行")
            time.sleep(0.02)
        on_delta(text[6:])
        return text


@pytest.fixture()
def client():
    with TestClient(create_app()) as actual:
        yield actual


def _ready(client):
    headers = login(client)
    project_id, _workspace = _parse_clause(client, headers, "服务方案中应包含数据库的健康检查、故障处理、标准服务等。")
    workspace = _confirm_plan(client, headers, project_id)
    model = GatedModel()
    client.app.state.workflow.demo.resolve_model_provider = lambda *_args, **_kwargs: model
    return headers, project_id, workspace, model


def _start(client, headers, project_id, workspace, sink: list):
    def run():
        response = client.post(
            f"/api/v1/projects/{project_id}/technical-volume/stream",
            headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
            json={},
        )
        sink.append(response)

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    return worker


def _finish(worker: threading.Thread, sink: list, *, timeout: float = 30):
    """等流式响应落盘。知识库不可用时检索会拖慢整卷，10 秒不够。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if sink and not worker.is_alive():
            return sink[-1]
        time.sleep(0.05)
    worker.join(0)
    raise AssertionError(f"stream unfinished alive={worker.is_alive()} responses={len(sink)}")


def _active_session(client, headers, project_id, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        jobs = client.get("/api/v1/jobs", headers=headers).json()["jobs"]
        for job in jobs:
            if job["project_id"] == project_id and job["type"] == "technical_volume":
                return job
        time.sleep(0.05)
    raise AssertionError("没有登记技术卷生成任务")


def _wait_status(client, headers, job_id, statuses, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = client.get(f"/api/v1/jobs/{job_id}", headers=headers).json()
        if job["status"] in statuses:
            return job
        time.sleep(0.05)
    raise AssertionError(f"任务没有进入 {statuses}")


def _chapter(client, headers, project_id, chapter_id):
    saved = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    return next(item for item in saved["chapters"] if item["id"] == chapter_id)


def test_generation_registers_a_session_job_with_section_progress(client):
    headers, project_id, workspace, model = _ready(client)
    responses: list = []
    worker = _start(client, headers, project_id, workspace, responses)
    assert model.started.wait(10)

    running = _active_session(client, headers, project_id)
    assert running["status"] in ("queued", "running")
    live = client.get(f"/api/v1/jobs/{running['id']}", headers=headers).json()
    assert live["sections"]["done"] == 0 and live["sections"]["total"] >= 1
    assert live["allowed_actions"] == ["cancel"]

    model.gate.set()
    events = _frames(_finish(worker, responses).text)
    assert events[0] == {"event": "session.started", "job_id": running["id"]}
    assert events[-1]["event"] == "volume.done"

    done = _wait_status(client, headers, running["id"], {"completed"})
    total = done["sections"]["total"]
    assert total >= 1 and done["sections"] == {"done": total, "total": total, "failed": 0}


def test_dropping_the_subscription_does_not_cancel_the_session(client):
    headers, project_id, workspace, model = _ready(client)
    responses: list = []
    worker = _start(client, headers, project_id, workspace, responses)
    assert model.started.wait(10)
    job = _active_session(client, headers, project_id)

    sessions = client.app.state.volume_sessions
    subscription = sessions.frames(job["id"])
    first = next(subscription)
    assert "session.started" in first
    subscription.close()

    model.gate.set()
    _finish(worker, responses)
    done = _wait_status(client, headers, job["id"], {"completed", "cancelled", "failed"})
    assert done["status"] == "completed"
    chapter = _chapter(client, headers, project_id, workspace["technical_outline"]["chapter_id"])
    assert SUFFIX in chapter["content"]


def test_stop_cancels_the_session_and_keeps_the_chapter(client):
    headers, project_id, workspace, model = _ready(client)
    chapter_id = workspace["technical_outline"]["chapter_id"]
    before = _chapter(client, headers, project_id, chapter_id)["content"]
    responses: list = []
    worker = _start(client, headers, project_id, workspace, responses)
    assert model.started.wait(10)
    job = _active_session(client, headers, project_id)

    cancelled = client.post(f"/api/v1/jobs/{job['id']}/cancel",
                            headers={**headers, "Idempotency-Key": str(uuid4())})
    assert cancelled.status_code == 200, cancelled.text
    assert _frames(_finish(worker, responses).text)[-1]["event"] == "volume.cancelled"
    assert not worker.is_alive()

    final = client.get(f"/api/v1/jobs/{job['id']}", headers=headers).json()
    assert final["status"] == "cancelled" and final["allowed_actions"] == []
    assert _chapter(client, headers, project_id, chapter_id)["content"] == before
    retried = client.post(f"/api/v1/jobs/{job['id']}/retry", headers={**headers, "Idempotency-Key": str(uuid4())})
    assert retried.status_code == 409


def test_resubscribing_replays_the_section_backlog_then_follows_live(client):
    headers, project_id, workspace, model = _ready(client)
    responses: list = []
    worker = _start(client, headers, project_id, workspace, responses)
    assert model.started.wait(10)
    job = _active_session(client, headers, project_id)

    resumed: list = []

    def attach():
        resumed.append(client.get(f"/api/v1/jobs/{job['id']}/section-events", headers=headers))

    follower = threading.Thread(target=attach, daemon=True)
    follower.start()
    time.sleep(0.3)
    model.gate.set()
    _finish(follower, resumed)
    _finish(worker, responses)

    events = _frames(resumed[0].text)
    names = [item["event"] for item in events]
    assert names[0] == "session.started" and "session.live" in names
    assert names[-1] == "volume.done"
    live_at = names.index("session.live")
    assert "section.delta" in names[:live_at]
    for done in (item for item in events if item["event"] == "section.done"):
        deltas = [item["text"] for item in events
                  if item["event"] == "section.delta" and item["section_id"] == done["section_id"]]
        assert "".join(deltas) == done["text"]


def test_starting_again_while_running_attaches_to_the_same_session(client):
    headers, project_id, workspace, model = _ready(client)
    first: list = []
    second: list = []
    worker = _start(client, headers, project_id, workspace, first)
    assert model.started.wait(10)
    job = _active_session(client, headers, project_id)
    again = _start(client, headers, project_id, workspace, second)
    time.sleep(0.3)
    model.gate.set()
    _finish(worker, first)
    _finish(again, second)
    assert _frames(first[0].text)[0]["job_id"] == job["id"]
    assert _frames(second[0].text)[0]["job_id"] == job["id"]
    sessions = [item for item in client.get("/api/v1/jobs", headers=headers).json()["jobs"]
                if item["project_id"] == project_id and item["type"] == "technical_volume"]
    assert len(sessions) == 1


def test_session_patches_each_task_from_generating_to_responded(client):
    from icg.domain.technical_matrix import bind_deviation_judge, bind_history_search, reset_deviation_judge, reset_history_search
    headers = login(client)
    search = bind_history_search(lambda query: [
        {"filename": "2023合成.docx", "quote": "健康检查每30分钟一次", "score": 0.9},
    ] if "健康检查" in query else [])
    judge = bind_deviation_judge(lambda _clause, quote: {
        "deviation": "正偏离", "reason": "历史巡检为每30分钟一次。",
    } if "30" in quote else {"deviation": "无偏离", "reason": ""})
    try:
        project_id, _ = _parse_clause(client, headers, "服务方案中应包含数据库的健康检查、故障处理、标准服务等。")
    finally:
        reset_history_search(search)
        reset_deviation_judge(judge)
    workspace = _confirm_plan(client, headers, project_id)
    model = GatedModel()
    client.app.state.workflow.demo.resolve_model_provider = lambda *_args, **_kwargs: model
    rows = workspace["coverage_rows"]
    exceed = next(row for row in rows if row["text"] == "健康检查")
    assert exceed["response_type"] == "exceed"

    responses: list = []
    worker = _start(client, headers, project_id, workspace, responses)
    assert model.started.wait(10)
    model.gate.set()
    events = _frames(_finish(worker, responses).text)
    tasks = {row["task_id"] for row in rows}
    assert len(tasks) >= 3

    for task_id in tasks:
        patches = [item for item in events if item["event"] == "task.patched" and item["task_id"] == task_id]
        assert [item["generation_status"] for item in patches] == ["generating", "generated"]
        done_at = next(index for index, item in enumerate(events)
                       if item["event"] == "section.done" and item["section_id"] == task_id)
        assert events.index(patches[0]) < done_at < events.index(patches[1])
    started = next(item for item in events if item["event"] == "task.patched" and item["task_id"] == exceed["task_id"])
    assert started["response_types"][exceed["requirement_id"]] == "exceed"

    saved = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()["coverage_rows"]
    assert {row["generation_status"] for row in saved} == {"generated"}


def test_superseded_session_reports_its_end_state_without_backlog(client):
    headers, project_id, workspace, model = _ready(client)
    model.gate.set()
    responses: list = []
    first = _start(client, headers, project_id, workspace, responses)
    older = _frames(_finish(first, responses).text)[0]["job_id"]
    _wait_status(client, headers, older, {"completed"})

    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    second = _start(client, headers, project_id, workspace, responses)
    newer = _frames(_finish(second, responses).text)[0]["job_id"]
    assert newer != older

    replay = _frames(client.get(f"/api/v1/jobs/{older}/section-events", headers=headers).text)
    assert [item["event"] for item in replay] == ["session.started", "session.live", "volume.done"]
    assert replay[-1]["replay"] is True
