# 为什么有这个文件：验证任务与模型对应表（PRD v1.8 §6.4、§6.5；APP-M2-T040）。
# 它解决什么问题：只有公司管理员能改；首选本地时备用不能是云端、备用不能与首选相同、只能选本公司真实模型（表格驱动）；
# 没有单独绑定模型的项目，各任务按对应表取首选与备用，主模型失败时改用表里的备用；敏感项目首选不是本地时拒绝。

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from icg.app.main import create_app
from test_reference_flow import ProjectFlow, login


@pytest.fixture
def routed():
    calls = []

    def handler(request):
        calls.append(request.url.host)
        if request.url.host == "down.local":
            return httpx.Response(503, json={})
        return httpx.Response(200, json={"choices": [{"message": {"content": "每月开展一次例行巡检"}}]})
    with TestClient(create_app(model_transport=httpx.MockTransport(handler))) as client:
        admin = login(client, "alpha-company-admin")
        for ident, host, local in (("local-a", "down.local", True), ("local-b", "local-b.local", True), ("cloud-c", "cloud.example", False)):
            assert client.post("/api/v1/model-configs", headers=admin, json={
                "id": ident, "base_url": f"http://{host}", "model": ident, "is_local": local, "allow_sensitive": local,
                "stream_enabled": False}).status_code == 200
        yield client, admin, calls


def _put(client, headers, routes, revision=None):
    extra = {"If-Match": str(revision)} if revision is not None else {}
    return client.put("/api/v1/task-model-routes", headers={**headers, **extra}, json={"routes": routes})


@pytest.mark.parametrize("primary,fallback,message", [
    ("local-a", "cloud-c", "备用只能是本地模型"),
    ("local-a", "local-a", "不能与首选相同"),
    (None, "local-b", "先选首选模型"),
    ("nope", None, "不存在或不属于本公司"),
])
def test_invalid_routes_are_refused(routed, primary, fallback, message):
    client, admin, _ = routed
    resp = _put(client, admin, [{"task": "assistant_suggest", "primary_config_id": primary, "fallback_config_id": fallback}])
    assert resp.status_code == 422 and message in resp.json()["message"]


def test_only_company_admin_saves_and_revision_is_checked(routed):
    client, admin, _ = routed
    listed = client.get("/api/v1/task-model-routes", headers=admin).json()
    assert {t["task"] for t in listed["tasks"]} == {"chapter_generation", "assistant_qa", "assistant_suggest"}
    assert _put(client, login(client, "alpha-manager"), []).status_code == 403
    ok = _put(client, admin, [{"task": "assistant_suggest", "primary_config_id": "cloud-c", "fallback_config_id": "local-b"}], 0)
    assert ok.status_code == 200 and ok.json()["revision"] == 1
    assert _put(client, admin, [], 0).status_code == 409


def test_unbound_projects_follow_the_route_and_fall_back_to_its_backup(routed):
    client, admin, calls = routed
    assert _put(client, admin, [{"task": "assistant_suggest", "primary_config_id": "local-a", "fallback_config_id": "local-b"}]).status_code == 200
    flow = ProjectFlow(client).ready()
    chapter = next(c for c in flow.state()["chapters"] if c["volume"] == "technical")
    start = chapter["content"].index("每月安排巡检")
    resp = client.post(f"{flow.path}/chapters/{chapter['id']}/selection-rewrites/stream", headers=flow.headers, json={
        "base_revision": chapter["revision"], "start": start, "end": start + 6, "selected_text": "每月安排巡检",
        "knowledge_base_enabled": False, "count": 3})
    events = [json.loads(b.split("data: ", 1)[1]) for b in resp.text.split("\n\n") if "data: " in b]
    assert events[0]["model"] == "local-a" and events[0]["fallback_model"] == "local-b"
    batch = events[-1]["batch"]
    assert {s["model"] for s in batch["samples"]} == {"local-b"} and "cloud.example" not in calls

    _put(client, admin, [{"task": "assistant_suggest", "primary_config_id": "cloud-c", "fallback_config_id": None}])
    flow.write("", {"sensitive": True}, "PATCH")
    chapter = next(c for c in flow.state()["chapters"] if c["volume"] == "technical")
    refused = client.post(f"{flow.path}/chapters/{chapter['id']}/selection-rewrites/stream", headers=flow.headers, json={
        "base_revision": chapter["revision"], "start": start, "end": start + 6, "selected_text": "每月安排巡检",
        "knowledge_base_enabled": False, "count": 3})
    assert refused.status_code == 403 and refused.json()["code"] == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"
