# 为什么有这个文件：验证编辑台自由提问与本地模型排队（PRD v1.8 §5.11.3、§5.11.11、§5.11.14 第 18 项、§6.4；APP-M2-T179、T177）。
# 它解决什么问题：不选中正文时只回答不写入；问到本项目数据时直接给答案卡、不调用模型；知识库关闭时不检索并注明；
# 回答里检索结果以外的引用标记被去掉；未接入真实模型返回 502；只读角色不能提问；问答记入本人会话；
# 敏感项目本地模型不可用时排队重试、发“本地任务排队”提醒、绝不改走云端。

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from icg.app.main import create_app
from test_reference_flow import ProjectFlow, login


class Answering:
    name, is_real_model, is_local, model = "scripted", True, True, "scripted-qa"

    def __init__(self, reply="建议按招标要求写明每月巡检的范围与报告提交方式。[片:lib-9]"):
        self.reply, self.calls = reply, []

    def suggest(self, system, user):
        self.calls.append((system, user))
        return self.reply


def _ask(client, flow, chapter_id, question, **extra):
    resp = client.post(f"{flow.path}/chapters/{chapter_id}/assistant-questions/stream", headers=flow.headers,
                       json={"question": question, "knowledge_base_enabled": False, **extra})
    if resp.status_code != 200:
        return resp.status_code, resp.json()
    return 200, [json.loads(block.split("data: ", 1)[1]) for block in resp.text.split("\n\n") if "data: " in block]


def _chapter(flow):
    return next(c for c in flow.state()["chapters"] if c["volume"] == "technical")


def test_free_question_answers_for_copy_only_and_is_recorded():
    model = Answering()
    with TestClient(create_app(model_provider=model)) as client:
        flow = ProjectFlow(client).ready()
        chapter = _chapter(flow)
        status, events = _ask(client, flow, chapter["id"], "巡检这一节应该怎么写？")
        assert status == 200 and [e["event"] for e in events][0] == "started" and events[-1]["event"] == "done"
        answer = events[-1]["answer"]
        assert answer["route"] == "model" and answer["can_insert"] is False and answer["action"] == "copy_only"
        assert "[片:lib-9]" not in answer["answer"] and answer["warnings"]  # 知识库关闭，引用标记不可能来自检索
        system, user = model.calls[0]
        assert "【问题】巡检这一节应该怎么写？" in user and "每月完成巡检并提交报告" in user
        assert _chapter(flow)["revision"] == chapter["revision"]  # 不写正文
        session = client.get(f"{flow.path}/assistant-sessions/{answer['session_id']}", headers=flow.headers).json()
        assert [m["kind"] for m in session["messages"]] == ["question", "answer"]
        status, events = _ask(client, flow, chapter["id"], "再短一点", session_id=answer["session_id"])
        assert "【本会话之前的问答】" in model.calls[-1][1]
        viewer = login(client, "alpha-viewer")
        resp = client.post(f"{flow.path}/chapters/{chapter['id']}/assistant-questions/stream", headers=viewer,
                           json={"question": "x", "knowledge_base_enabled": False})
        assert resp.status_code in (403, 404)


def test_project_data_questions_get_an_answer_card_without_the_model():
    model = Answering()
    with TestClient(create_app(model_provider=model)) as client:
        flow = ProjectFlow(client).ready()
        status, events = _ask(client, flow, _chapter(flow)["id"], "服务期限是多少")
        assert status == 200
        done = events[-1]["answer"]
        assert done["route"] == "direct_query" and done["answer_card"]["records"] and model.calls == []


def test_no_real_model_means_502():
    with TestClient(create_app()) as client:
        flow = ProjectFlow(client).ready()
        status, body = _ask(client, flow, _chapter(flow)["id"], "巡检这一节应该怎么写？")
        assert status == 502 and body["code"] == "MODEL_UNAVAILABLE"


def test_sensitive_project_queues_for_the_local_model_and_never_goes_to_cloud(monkeypatch):
    from icg.domain import selection_rewrite
    monkeypatch.setattr(selection_rewrite, "LOCAL_QUEUE_SECONDS", 0.3)
    monkeypatch.setattr(selection_rewrite, "LOCAL_QUEUE_STEPS", (0.1,))
    hosts = []

    def handler(request):
        hosts.append(request.url.host)
        return httpx.Response(503, json={})
    with TestClient(create_app(model_transport=httpx.MockTransport(handler))) as client:
        admin = login(client, "alpha-company-admin")
        assert client.post("/api/v1/model-configs", headers=admin, json={
            "id": "local-down", "base_url": "http://local.intranet", "model": "qwen-local", "is_local": True,
            "allow_sensitive": True}).status_code == 200
        flow = ProjectFlow(client).ready()
        flow.write("", {"sensitive": True}, "PATCH")
        assert client.post(f"{flow.path}/model-config", headers=flow.headers, json={"model_config_id": "local-down"}).status_code == 200
        status, events = _ask(client, flow, _chapter(flow)["id"], "巡检这一节应该怎么写？")
        kinds = [e["event"] for e in events]
        assert status == 200 and "queued" in kinds and kinds[-1] == "error"
        queued = next(e for e in events if e["event"] == "queued")
        assert "不改走云端" in queued["message"]
        assert set(hosts) == {"local.intranet"}
        notices = client.get("/api/v1/notifications", headers=flow.headers).json()["items"]
        assert any(n["type"] == "local_task_queued" for n in notices)


def test_selection_rewrite_also_queues_for_sensitive_projects(monkeypatch):
    from icg.domain import selection_rewrite
    monkeypatch.setattr(selection_rewrite, "LOCAL_QUEUE_SECONDS", 0.3)
    monkeypatch.setattr(selection_rewrite, "LOCAL_QUEUE_STEPS", (0.1,))
    with TestClient(create_app(model_transport=httpx.MockTransport(lambda r: httpx.Response(503, json={})))) as client:
        admin = login(client, "alpha-company-admin")
        client.post("/api/v1/model-configs", headers=admin, json={
            "id": "local-down", "base_url": "http://local.intranet", "model": "qwen-local", "is_local": True, "allow_sensitive": True})
        flow = ProjectFlow(client).ready()
        flow.write("", {"sensitive": True}, "PATCH")
        client.post(f"{flow.path}/model-config", headers=flow.headers, json={"model_config_id": "local-down"})
        chapter = _chapter(flow)
        start = chapter["content"].index("每月安排巡检")
        resp = client.post(f"{flow.path}/chapters/{chapter['id']}/selection-rewrites/stream", headers=flow.headers, json={
            "base_revision": chapter["revision"], "start": start, "end": start + 6, "selected_text": "每月安排巡检",
            "knowledge_base_enabled": False, "count": 3})
        events = [json.loads(b.split("data: ", 1)[1]) for b in resp.text.split("\n\n") if "data: " in b]
        kinds = [e["event"] for e in events]
        assert "queued" in kinds and kinds.count("dropped") == 3
        assert all("未改走云端" in e["reason"] for e in events if e["event"] == "dropped")
