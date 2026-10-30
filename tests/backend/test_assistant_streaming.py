# 为什么有这个文件：验证对话助手逐字流式、备用模型降级与停止（PRD v1.8 §5.11.3、§6.4、§6.5 规则 2、3；APP-M2-T177）。
# 它解决什么问题：真实 OpenAI 兼容接口（用 httpx MockTransport 模拟内网服务）逐段返回文字时页面收到 delta；
# 主模型 503/超时/限流改用备用模型并标明，4xx 不降级；已输出一部分后断流不重试同一模型；停止后不保存；
# 本地主模型只能配本地备用，备用后来被改成云端时运行时不再使用，敏感项目只用本地备用。

import json
import threading

import httpx
import pytest
from fastapi.testclient import TestClient

from icg.app.main import create_app
from icg.domain.selection_rewrite import STYLES
from icg.infra.model_fallback import call_model, degradable
from icg.infra.openai_model import (ModelCallError, ModelCancelled, OpenAICompatibleConfig,
                                    OpenAICompatibleModelProvider, RetryableModelError)
from test_reference_flow import ProjectFlow, login

SENTENCE = "每月安排巡检"
REPLIES = ["每月开展一次例行巡检", "每月巡检", "按月巡检并提交报告", "每月按计划巡检设备", "每个月去现场巡检"]


def sse(pieces: list[str]) -> bytes:
    lines = [f"data: {json.dumps({'choices': [{'delta': {'content': p}}]}, ensure_ascii=False)}\n\n" for p in pieces]
    return ("".join(lines) + "data: [DONE]\n\n").encode()


def reply_for(request: httpx.Request) -> str:
    system = json.loads(request.content)["messages"][0]["content"]
    return next(text for (_, _, hint), text in zip(STYLES, REPLIES) if hint in system)


def provider(handler, **extra) -> OpenAICompatibleModelProvider:
    config = OpenAICompatibleConfig(base_url="http://model.local", model="qwen-test", stream_enabled=True, **extra)
    return OpenAICompatibleModelProvider(config, transport=httpx.MockTransport(handler))


def test_stream_suggest_relays_each_piece_and_handles_plain_json():
    pieces = []
    streamed = provider(lambda r: httpx.Response(200, headers={"content-type": "text/event-stream"}, content=sse(["每月", "开展", "巡检"])))
    assert streamed.stream_suggest("s", "u", on_delta=pieces.append) == "每月开展巡检" and pieces == ["每月", "开展", "巡检"]
    pieces.clear()
    plain = provider(lambda r: httpx.Response(200, json={"choices": [{"message": {"content": "整段返回"}}]}))
    assert plain.stream_suggest("s", "u", on_delta=pieces.append) == "整段返回" and pieces == ["整段返回"]


def test_stream_stops_on_cancel_and_does_not_retry_after_partial_output():
    cancel = threading.Event()
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=sse(["一", "二", "三"]))
    model = provider(handler, retries=2)
    with pytest.raises(ModelCancelled):
        model.stream_suggest("s", "u", on_delta=lambda piece: cancel.set(), cancel=cancel)
    assert len(calls) == 1

    class Broken(httpx.SyncByteStream):
        def __iter__(self):
            yield sse(["已输出"])[:-len("data: [DONE]\n\n")]
            raise httpx.ReadError("cut")
    broken = provider(lambda r: httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=Broken()), retries=2)
    with pytest.raises(ModelCallError) as info:
        broken.stream_suggest("s", "u", on_delta=lambda piece: None)
    # 同一模型不重试（避免前后两段拼接）；属于健康类失败，可清空预览后改用备用模型
    assert "partial" in str(info.value) and degradable(info.value)


def test_fallback_only_for_health_failures_and_reports_the_model_used():
    backup = provider(lambda r: httpx.Response(200, headers={"content-type": "text/event-stream"}, content=sse(["备用", "输出"])))
    backup.model = "qwen-backup"
    for status in (503, 429):
        primary = provider(lambda r, s=status: httpx.Response(s, json={}), retries=0)
        primary.fallback = backup
        resets, pieces = [], []
        result = call_model(primary, "s", "u", on_delta=pieces.append, on_reset=lambda name, why: resets.append((name, why)))
        assert (result.text, result.model, result.is_fallback) == ("备用输出", "qwen-backup", True)
        assert resets and resets[0][0] == "qwen-backup" and ("限流" in resets[0][1] if status == 429 else "503" in resets[0][1])
    bad_request = provider(lambda r: httpx.Response(400, json={}), retries=0)
    bad_request.fallback = backup
    with pytest.raises(ModelCallError):
        call_model(bad_request, "s", "u", on_delta=lambda p: None)
    assert degradable(RetryableModelError("timeout")) and not degradable(ModelCancelled("x"))


@pytest.fixture
def routed():
    """两台合成“内网模型”：primary 返回 503，backup 逐字流式返回各写法的样例。"""
    seen = {"primary": 0, "backup": 0}

    def handler(request: httpx.Request):
        if request.url.host == "primary.local":
            seen["primary"] += 1
            return httpx.Response(503, json={"error": "busy"})
        seen["backup"] += 1
        text = reply_for(request)
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=sse([text[:2], text[2:]]))
    with TestClient(create_app(model_transport=httpx.MockTransport(handler))) as client:
        yield client, seen


def _configs(client, *, backup_local=True):
    admin = login(client, "alpha-company-admin")
    made = client.post("/api/v1/model-configs", headers=admin, json={
        "id": "cfg-backup", "name": "备用", "base_url": "http://backup.local", "model": "qwen-backup",
        "is_local": backup_local, "allow_sensitive": backup_local}).json()
    assert made["id"] == "cfg-backup", made
    return admin


def _ask_stream(flow, chapter):
    content = chapter["content"]
    start = content.index(SENTENCE)
    body = {"base_revision": chapter["revision"], "start": start, "end": start + len(SENTENCE), "selected_text": SENTENCE,
            "knowledge_base_enabled": False, "count": 3}
    resp = flow.client.post(f"{flow.path}/chapters/{chapter['id']}/selection-rewrites/stream", headers=flow.headers, json=body)
    assert resp.status_code == 200, resp.text
    return [json.loads(block.split("data: ", 1)[1]) for block in resp.text.split("\n\n") if "data: " in block]


def test_cloud_backup_is_refused_for_a_local_primary(routed):
    client, _ = routed
    admin = _configs(client, backup_local=False)
    refused = client.post("/api/v1/model-configs", headers=admin, json={
        "id": "cfg-primary", "base_url": "http://primary.local", "model": "qwen-primary", "is_local": True,
        "fallback_config_id": "cfg-backup"})
    assert refused.status_code == 422 and "本地主模型的备用只能是本地模型" in refused.json()["message"]
    missing = client.post("/api/v1/model-configs", headers=admin, json={"id": "cfg-x", "fallback_config_id": "nope"})
    assert missing.status_code == 422


def test_stream_uses_backup_when_primary_is_down_and_marks_each_sample(routed):
    client, seen = routed
    admin = _configs(client)
    created = client.post("/api/v1/model-configs", headers=admin, json={
        "id": "cfg-primary", "base_url": "http://primary.local", "model": "qwen-primary", "is_local": True,
        "fallback_config_id": "cfg-backup"})
    assert created.status_code == 200 and created.json()["fallback_config_id"] == "cfg-backup"
    flow = ProjectFlow(client).ready()
    bound = client.post(f"{flow.path}/model-config", headers=flow.headers, json={"model_config_id": "cfg-primary"})
    assert bound.status_code == 200, bound.text
    chapter = next(c for c in flow.state()["chapters"] if c["volume"] == "technical")
    policy = client.get(f"{flow.path}/chapters/{chapter['id']}/assistant-policy", headers=flow.headers).json()
    assert (policy["model"], policy["fallback_model"], policy["streaming"]) == ("qwen-primary", "qwen-backup", True)

    events = _ask_stream(flow, chapter)
    kinds = [e["event"] for e in events]
    assert kinds[0] == "started" and events[0]["fallback_model"] == "qwen-backup" and kinds[-1] == "done"
    assert kinds.count("fallback") == 3 and kinds.count("delta") == 6 and kinds.count("sample") == 3
    fallback = next(e for e in events if e["event"] == "fallback")
    assert fallback["model"] == "qwen-backup" and "503" in fallback["reason"]
    batch = events[-1]["batch"]
    assert all(s["is_fallback"] and s["model"] == "qwen-backup" for s in batch["samples"])
    assert len(batch["fallback_used"]) == 3 and batch["models_used"] == ["qwen-backup"]
    assert seen["primary"] == 3 * 2 and seen["backup"] == 3  # 主模型每种写法重试一次后降级

    # 备用模型后来被改成云端：本地主模型的备用不能改成非本地
    cfg = client.get("/api/v1/model-configs/cfg-backup", headers=admin).json()
    changed = client.put("/api/v1/model-configs/cfg-backup", headers={**admin, "If-Match": str(cfg["revision"])},
                         json={"is_local": False})
    assert changed.status_code == 422


def test_sensitive_projects_ignore_a_backup_that_does_not_allow_sensitive_data(routed):
    client, _ = routed
    admin = login(client, "alpha-company-admin")
    client.post("/api/v1/model-configs", headers=admin, json={
        "id": "cfg-backup", "base_url": "http://backup.local", "model": "qwen-backup", "is_local": True, "allow_sensitive": False})
    client.post("/api/v1/model-configs", headers=admin, json={
        "id": "cfg-primary", "base_url": "http://primary.local", "model": "qwen-primary", "is_local": True,
        "allow_sensitive": True, "fallback_config_id": "cfg-backup"})
    state = client.app.state.service.repository.read()
    from icg.infra.model_config_storage import usable_fallback
    primary = state.model_configs["cfg-primary"]
    assert usable_fallback(state, primary, project_sensitive=False).id == "cfg-backup"
    assert usable_fallback(state, primary, project_sensitive=True) is None


def test_stopping_saves_nothing(routed):
    client, _ = routed
    admin = _configs(client)
    client.post("/api/v1/model-configs", headers=admin, json={
        "id": "cfg-primary", "base_url": "http://primary.local", "model": "qwen-primary", "fallback_config_id": "cfg-backup"})
    flow = ProjectFlow(client).ready()
    client.post(f"{flow.path}/model-config", headers=flow.headers, json={"model_config_id": "cfg-primary"})
    chapter = next(c for c in flow.state()["chapters"] if c["volume"] == "technical")
    service = client.app.state.selection_rewrite
    principal = client.app.state.service.authenticate(flow.headers["Authorization"].split(" ", 1)[1])
    start = chapter["content"].index(SENTENCE)
    prepared = service.prepare(principal, flow.id, chapter["id"], {
        "base_revision": chapter["revision"], "start": start, "end": start + len(SENTENCE), "selected_text": SENTENCE,
        "knowledge_base_enabled": False, "count": 3})
    cancel = threading.Event()
    seen = []
    for event in service.stream(prepared, cancel=cancel):
        seen.append(event["event"])
        if event["event"] == "delta":
            cancel.set()
    assert seen[-1] == "cancelled" and "done" not in seen
    sessions = client.get(f"{flow.path}/chapters/{chapter['id']}/assistant-sessions", headers=flow.headers).json()
    assert sessions["sessions"] == [] if "sessions" in sessions else sessions.get("items", []) == []


def test_ragflow_quirks_seen_on_the_real_service():
    """2026-10-30 实测 RAGFlow（OpenAI 兼容接口）：限流时仍回 HTTP 200；普通模式正文是“**ERROR**: Error 429…”，
    流式只有一个空的结束块；有的块是到目前为止的全文；模型名不对时回 {"code":101,"message":…}。"""
    quota = "**ERROR**: Error 429, Message: You exceeded your current quota, please check your plan and billing details."
    plain = provider(lambda r: httpx.Response(200, json={"choices": [{"message": {"content": quota}}]}), retries=0)
    plain.stream_enabled = False
    with pytest.raises(ModelCallError) as info:
        plain.suggest("s", "u")
    assert degradable(info.value) and str(info.value.__cause__) == "HTTP 429"

    shown = []
    empty = provider(lambda r: httpx.Response(200, headers={"content-type": "text/event-stream"},
                                              content=b'data: {"choices":[{"delta":{"content":null},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'),
                     retries=0)
    with pytest.raises(ModelCallError) as info:
        empty.stream_suggest("s", "u", on_delta=shown.append)
    assert degradable(info.value) and shown == []

    split = provider(lambda r: httpx.Response(200, headers={"content-type": "text/event-stream"},
                                              content=sse(["**ERR", "OR**: Error 503 ", "overloaded"])), retries=0)
    with pytest.raises(ModelCallError) as info:
        split.stream_suggest("s", "u", on_delta=shown.append)
    assert degradable(info.value) and shown == []  # 错误文字不推给页面

    cumulative = provider(lambda r: httpx.Response(200, headers={"content-type": "text/event-stream"},
                                                   content=sse(["每月开展", "每月开展一次例行", "巡检"])))
    pieces = []
    assert cumulative.stream_suggest("s", "u", on_delta=pieces.append) == "每月开展一次例行巡检"
    assert pieces == ["每月开展", "一次例行", "巡检"]

    bold = provider(lambda r: httpx.Response(200, headers={"content-type": "text/event-stream"}, content=sse(["**", "重点**说明"])))
    assert bold.stream_suggest("s", "u", on_delta=lambda p: None) == "**重点**说明"  # 普通 Markdown 开头不误判

    envelope = provider(lambda r: httpx.Response(200, json={"code": 101, "data": None, "message": "`llm_id` m doesn't exist"}), retries=0)
    with pytest.raises(ModelCallError) as info:
        envelope.stream_suggest("s", "u", on_delta=lambda p: None)
    assert "doesn't exist" in str(info.value) and not degradable(info.value)
