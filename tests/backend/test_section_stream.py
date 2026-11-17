# 为什么有这个文件：核对技术节流式生成（PR5）。
# 它解决什么问题：假模型分多段吐字时，正文等于各段拼接；取消后这一节不改原文；
# SSE 帧带 section_id 和本次新增文字；多节并行时同时进行的模型调用不超过 3。
# 非流式仍只走 suggest。编辑台逐字展示不在这里。

from __future__ import annotations

import json
import threading
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from icg.infra.openai_model import ModelCancelled
from icg_demo.main import create_app
from test_reference_flow import login
from test_technical_sources import _confirm_plan, _parse_clause

PIECES = ("每月开展一次例行巡检，", "按响应要点留下运行记录，", "记录供验收核对，过程可追溯。本节完成。")
BODY = "".join(PIECES)
SUFFIX = "按本次招标要求逐条写巡检步骤，并留下运行记录供验收核对，过程可追溯。本节完成。"


def _frames(raw: str) -> list[dict]:
    return [json.loads(block.split("data: ", 1)[1]) for block in raw.split("\n\n") if "data: " in block]


def _local(**extra):
    class Model:
        is_real_model = True
        is_local = True
        stream_enabled = True
        base_url = "http://127.0.0.1:9"

    model = Model()
    for key, value in extra.items():
        setattr(model, key, value)
    return model


def _volume(titles: list[str], content: str = ""):
    headings = []
    requirements = {}
    tasks = {}
    for index, title in enumerate(titles, start=1):
        rid, tid = f"r{index}", f"t{index}"
        headings.append({
            "level": 1, "number": str(index), "title": title,
            "task_id": tid, "requirement_id": rid, "requirement_ids": [rid],
        })
        requirements[rid] = {
            "id": rid, "technical_clause": True, "text": f"{title}的招标要求",
            "extracted_summary": f"{title}的招标要求", "status": "confirmed",
            "response": "按招标执行", "response_type": "comply",
        }
        tasks[tid] = {"task_id": tid, "requirement_ids": [rid], "response_points": [f"{title}的招标要求"]}
    workflow = {
        "plan_confirmed": True,
        "technical_outline": {"chapter_id": "c1", "headings": headings},
        "requirements": requirements,
        "response_tasks": tasks,
        "files": {},
    }
    chapter = SimpleNamespace(id="c1", content=content, revision=1)
    state = SimpleNamespace(
        chapters={"c1": chapter},
        projects={"p": SimpleNamespace(id="p", name="合成项目", company_id="alpha")},
    )
    return state, workflow, chapter


def test_section_sse_frame_names_the_section_and_the_new_text():
    from icg.domain.technical_volume import format_section_sse

    raw = format_section_sse({"event": "section.delta", "section_id": "t1", "text": "每月"})
    assert raw.startswith("event: section.delta\n")
    assert _frames(raw) == [{"event": "section.delta", "section_id": "t1", "text": "每月"}]


def test_produce_section_relays_deltas_and_still_suggests_when_not_streaming():
    from icg.domain.technical_volume import produce_section

    assert len(BODY) >= 40
    row = {"text": "每月巡检", "response": "按招标执行", "response_type": "comply"}
    streamed = _local()
    seen = []

    def stream_suggest(instruction, content, *, on_delta, cancel=None):
        for piece in PIECES:
            on_delta(piece)
        return BODY

    streamed.stream_suggest = stream_suggest
    streamed.suggest = lambda *_args: (_ for _ in ()).throw(AssertionError("流式路径不应整段 suggest"))
    text = produce_section("运维保障与巡检", row, streamed, on_delta=seen.append)
    assert text == BODY and seen == list(PIECES)

    plain = _local()
    plain.suggest_calls = 0

    def suggest(system, user):
        plain.suggest_calls += 1
        return BODY

    plain.suggest = suggest
    plain.stream_suggest = lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("未要求流式"))
    assert produce_section("运维保障与巡检", row, plain) == BODY
    assert plain.suggest_calls == 1

    once = []
    fallback = _local(stream_enabled=False)
    fallback.suggest = lambda system, user: BODY
    assert produce_section("运维保障与巡检", row, fallback, on_delta=once.append) == BODY
    assert once == [BODY]


def test_produce_section_cancel_stops_the_rest_of_the_stream():
    from icg.domain.technical_volume import produce_section

    cancel = threading.Event()
    seen = []
    model = _local()

    def stream_suggest(instruction, content, *, on_delta, cancel=None):
        for piece in PIECES:
            on_delta(piece)
        return BODY

    model.stream_suggest = stream_suggest

    def on_delta(piece: str) -> None:
        seen.append(piece)
        cancel.set()

    with pytest.raises(ModelCancelled):
        produce_section(
            "运维保障与巡检",
            {"text": "每月巡检", "response": "按招标执行", "response_type": "comply"},
            model,
            on_delta=on_delta,
            cancel=cancel,
        )
    assert seen == [PIECES[0]]


def test_write_volume_streams_each_section_and_keeps_suggest_for_the_whole_chapter():
    from icg.domain.technical_volume import write_volume

    state, workflow, chapter = _volume(["总体说明", "巡检方案"])
    events = []
    model = _local()

    def stream_suggest(instruction, content, *, on_delta, cancel=None):
        title = content.split("章节任务：", 1)[1].split("\n", 1)[0]
        text = f"针对「{title}」{SUFFIX}"
        on_delta(text[:8])
        on_delta(text[8:])
        return text

    model.stream_suggest = stream_suggest
    model.suggest = lambda *_args: (_ for _ in ()).throw(AssertionError("流式写卷不应整段 suggest"))
    result = write_volume(state, "p", workflow, None, model, on_event=events.append)
    assert result["failed"] == []
    fanout = next(item for item in events if item["event"] == "sections.fanout")
    assert fanout["concurrency"] == 3
    assert fanout["section_ids"] == ["t1", "t2"]
    for section_id, title in (("t1", "总体说明"), ("t2", "巡检方案")):
        deltas = [item["text"] for item in events if item["event"] == "section.delta" and item["section_id"] == section_id]
        done = next(item for item in events if item["event"] == "section.done" and item["section_id"] == section_id)
        assert "".join(deltas) == done["text"]
        assert title in done["text"] and done["text"] in chapter.content
        assert any(item["event"] == "section.started" and item["section_id"] == section_id for item in events)
    assert "针对「总体说明」" in chapter.content and "针对「巡检方案」" in chapter.content

    quiet, quiet_workflow, _chapter = _volume(["总体说明"])
    quiet_model = _local()
    quiet_model.stream_calls = 0

    def suggest(system, user):
        return f"针对「总体说明」{SUFFIX}"

    def stream_suggest_unused(*_args, **_kwargs):
        quiet_model.stream_calls += 1
        raise AssertionError("未订阅事件时不走流式")

    quiet_model.suggest = suggest
    quiet_model.stream_suggest = stream_suggest_unused
    assert write_volume(quiet, "p", quiet_workflow, None, quiet_model)["failed"] == []
    assert quiet_model.stream_calls == 0


def test_write_volume_cancel_leaves_the_previous_section_body():
    from icg.domain.technical_volume import write_volume

    previous = "1 巡检方案\n原来的正文保留在这里，取消后不应被半截流式结果替换掉。\n"
    state, workflow, chapter = _volume(["巡检方案"], content=previous)
    cancel = threading.Event()
    events = []
    model = _local()

    def stream_suggest(instruction, content, *, on_delta, cancel=None):
        on_delta("流式半截不应落盘。")
        on_delta(SUFFIX)
        return "流式半截不应落盘。" + SUFFIX

    model.stream_suggest = stream_suggest

    def on_event(event: dict) -> None:
        events.append(event)
        if event["event"] == "section.delta":
            cancel.set()

    result = write_volume(state, "p", workflow, None, model, on_event=on_event, cancel=cancel)
    assert result["failed"] == []
    assert any(item["event"] == "section.cancelled" and item["section_id"] == "t1" for item in events)
    assert not any(item["event"] == "section.done" for item in events)
    assert "原来的正文保留在这里" in chapter.content
    assert "流式半截不应落盘" not in chapter.content
    assert workflow["response_tasks"]["t1"].get("generation_status") != "failed"


def test_parallel_sections_stay_within_the_concurrency_cap():
    from icg.domain.technical_volume import write_volume

    titles = ["总体说明", "巡检方案", "故障处理", "备份恢复"]
    state, workflow, chapter = _volume(titles)
    gate = threading.Event()
    lock = threading.Lock()
    current = 0
    peak = 0
    model = _local()

    def stream_suggest(instruction, content, *, on_delta, cancel=None):
        nonlocal current, peak
        title = content.split("章节任务：", 1)[1].split("\n", 1)[0]
        with lock:
            current += 1
            peak = max(peak, current)
        gate.wait(3)
        with lock:
            current -= 1
        text = f"针对「{title}」{SUFFIX}"
        on_delta(text)
        return text

    model.stream_suggest = stream_suggest
    events = []
    errors = []

    def run():
        try:
            write_volume(state, "p", workflow, None, model, on_event=events.append)
        except Exception as exc:
            errors.append(exc)

    worker = threading.Thread(target=run)
    worker.start()
    deadline = time.time() + 3
    while time.time() < deadline and peak < 3:
        time.sleep(0.02)
    assert peak == 3 and current == 3
    gate.set()
    worker.join(5)
    assert not errors and not worker.is_alive()
    fanout = next(item for item in events if item["event"] == "sections.fanout")
    assert fanout["concurrency"] == 3 and fanout["section_ids"] == ["t1", "t2", "t3", "t4"]
    for title in titles:
        assert f"针对「{title}」" in chapter.content
        assert chapter.content.count(f"针对「{title}」") == 1


@pytest.fixture()
def client():
    with TestClient(create_app()) as actual:
        yield actual


def test_technical_volume_stream_persists_the_same_text_as_the_deltas(client):
    headers = login(client)
    project_id, workspace = _parse_clause(client, headers, "服务方案中应包含数据库的健康检查、故障处理、标准服务等。")
    workspace = _confirm_plan(client, headers, project_id)
    leaf = next(
        item for item in workspace["technical_outline"]["headings"]
        if item.get("task_id") or item.get("requirement_id")
    )
    title = leaf["title"]
    section_id = leaf.get("task_id") or leaf.get("requirement_id")
    text = f"针对「{title}」{SUFFIX}"
    demo = client.app.state.workflow.demo
    model = _local()

    def stream_suggest(instruction, content, *, on_delta, cancel=None):
        on_delta(text[:6])
        on_delta(text[6:])
        return text

    model.stream_suggest = stream_suggest
    model.suggest = lambda *_args: (_ for _ in ()).throw(AssertionError("接口流式不应整段 suggest"))
    demo.resolve_model_provider = lambda *_args, **_kwargs: model
    key = str(uuid4())
    response = client.post(
        f"/api/v1/projects/{project_id}/technical-volume/stream",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": key},
        json={"section": title},
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _frames(response.text)
    deltas = [item["text"] for item in events if item["event"] == "section.delta" and item["section_id"] == section_id]
    done = next(item for item in events if item["event"] == "section.done" and item["section_id"] == section_id)
    finished = next(item for item in events if item["event"] == "volume.done")
    assert "".join(deltas) == done["text"] == text
    assert finished["replay"] is False
    saved = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    chapter = next(item for item in saved["chapters"] if item["id"] == workspace["technical_outline"]["chapter_id"])
    assert text in chapter["content"]
    replay = client.post(
        f"/api/v1/projects/{project_id}/technical-volume/stream",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": key},
        json={"section": title},
    )
    assert replay.status_code == 200, replay.text
    replayed = _frames(replay.text)
    assert replayed[-1]["event"] == "volume.done" and replayed[-1]["replay"] is True
    assert not any(item["event"] == "section.delta" for item in replayed)
