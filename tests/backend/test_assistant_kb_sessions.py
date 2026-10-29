# 为什么有这个文件：验证对话助手第二步（PRD v1.8 §5.11.2、§5.11.5、§5.11.8、§5.11.11；APP-M2-T176、T177、T178）。
# 它解决什么问题：知识库打开时样例必须引用本次检索结果、无结果不调用模型、未连接如实报错；公司可要求不能关知识库；
# 每次提问和写入记入本人会话，接着提问时带上之前的要求；会话只本人、负责人、公司管理员可看；流式接口按完成先后推送样例。

import json

import pytest
from fastapi.testclient import TestClient

from icg.domain.knowledge_base import KnowledgeHit
from icg_demo.main import create_app
from test_reference_flow import ProjectFlow, login
from test_selection_rewrite import SENTENCE, _apply, _lease, _technical

HIT = KnowledgeHit(source_type="library", source_id="lib-kb-1", name="巡检服务规范", item_type="qualification", revision=2,
                   score=0.82, content="例行巡检每月 1 次，巡检报告 3 个工作日内提交。", document_id="doc-1", chunk_ids=["chunk-9"],
                   attachable=True, reference_only=False)


class CitingModel:
    name, is_real_model, is_local, model = "citing", True, True, "citing-1"

    def __init__(self):
        self.calls = []
        self.replies = {"正式、规范": "每月开展 1 次例行巡检，报告 3 个工作日内提交 [片:lib-kb-1]",
                        "删去冗余": "每月巡检",                       # 没有引用：不展示
                        "实质性响应": "按月巡检 [片:lib-other]"}       # 引用了检索结果之外的资料：不展示

    def suggest(self, system, user):
        self.calls.append((system, user))
        return next((text for hint, text in self.replies.items() if hint in system), "每月巡检一次 [片:lib-kb-1]")


@pytest.fixture()
def model():
    return CitingModel()


@pytest.fixture()
def client(model):
    with TestClient(create_app(model_provider=model)) as actual:
        yield actual


def _body(chapter, **extra):
    start = chapter["content"].index(SENTENCE)
    return {"base_revision": chapter["revision"], "start": start, "end": start + len(SENTENCE), "selected_text": SENTENCE, **extra}


def _post(flow, chapter, expected=200, **extra):
    resp = flow.client.post(f"{flow.path}/chapters/{chapter['id']}/selection-rewrites", headers=flow.headers, json=_body(chapter, **extra))
    assert resp.status_code == expected, resp.text
    return resp.json()


def _kb(client, monkeypatch, hits, reason=""):
    kb = client.app.state.service.knowledge_base
    seen = {}

    def search(company_id, query, *, limit=6, user=None, **_):
        seen.update(company_id=company_id, query=query, user=user)
        return list(hits), reason
    monkeypatch.setattr(kb, "search", search)
    return seen


def test_knowledge_base_on_requires_each_sample_to_cite_this_retrieval(client, model, monkeypatch):
    seen = _kb(client, monkeypatch, [HIT])
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    batch = _post(flow, chapter, knowledge_base_enabled=True)
    assert seen["company_id"] == "alpha" and SENTENCE in seen["query"] and seen["user"].id == "alpha-manager"
    system, user = model.calls[0]
    assert "【可引用的资料】" in user and "[片:lib-kb-1] 巡检服务规范（v2）" in user and "至少引用 1 条" in system
    assert batch["retrieval"]["status"] == "found" and batch["knowledge_base_enabled"] is True
    assert [s["style_label"] for s in batch["samples"]] == ["严谨规范"]
    sample = batch["samples"][0]
    assert "[片:lib-kb-1]" in sample["text"] and "【待补" not in sample["text"]  # 数值出自引用资料，不算无来源
    assert sample["sources"][0]["source_id"] == "lib-kb-1" and sample["sources"][0]["chunk_ids"] == ["chunk-9"]
    reasons = {d["style"]: d["reason"] for d in batch["dropped"]}
    assert "没有引用" in reasons["简洁精炼"] and "检索结果之外" in reasons["突出响应"]
    lease = _lease(flow, chapter["id"])
    result = _apply(flow, chapter["id"], batch, sample, lease)
    operation = result["operation"]
    assert operation["knowledge_base_enabled"] is True and operation["source_note"] == "引用本公司知识库"
    assert operation["sources"][0]["source_id"] == "lib-kb-1" and "[片:lib-kb-1]" in result["content"]
    workflow = client.app.state.service.repository.read().workflows[flow.id]
    assert workflow["assistant_citations"][chapter["id"]] == ["lib-kb-1"]


def test_no_retrieval_results_do_not_call_the_model_and_unconnected_kb_is_reported(client, model, monkeypatch):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    unconnected = _post(flow, chapter, expected=409, knowledge_base_enabled=True)
    assert unconnected["code"] == "KNOWLEDGE_BASE_NOT_CONFIGURED" and "可关闭知识库后重试" in unconnected["message"]
    _kb(client, monkeypatch, [], "knowledge base has no synced documents")
    empty = _post(flow, chapter, knowledge_base_enabled=True)
    assert empty["status"] == "no_results" and empty["samples"] == [] and empty["retrieval"]["status"] == "empty"
    assert "没有找到相关内容" in empty["source_note"] and model.calls == []
    # 只作参考的资料（历史标书等）不能作为引用
    _kb(client, monkeypatch, [KnowledgeHit(**{**HIT.__dict__, "source_id": "hist-1", "reference_only": True})])
    assert _post(flow, chapter, knowledge_base_enabled=True)["status"] == "no_results"


def _settings(client, **values):
    admin = login(client, "alpha-company-admin")
    current = client.get("/api/v1/companies/alpha/settings", headers=admin)
    assert current.status_code == 200, current.text
    resp = client.patch("/api/v1/companies/alpha/settings", headers=admin, json=values)
    assert resp.status_code == 200, resp.text


def test_company_policy_decides_the_default_and_whether_kb_can_be_turned_off(client, monkeypatch):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    policy = client.get(f"{flow.path}/chapters/{chapter['id']}/assistant-policy", headers=flow.headers).json()
    assert policy["kb_default"] is True and policy["allow_kb_off"] is True and policy["count"] == 3
    assert policy["model"] == "citing-1" and policy["is_real_model"] is True and policy["knowledge_base_connected"] is False
    _settings(client, assistant_allow_kb_off=False, assistant_suggestion_count=4)
    refused = _post(flow, chapter, expected=422, knowledge_base_enabled=False)
    assert "不能关闭" in refused["message"]
    _kb(client, monkeypatch, [HIT])
    batch = _post(flow, chapter)  # 不传开关：取公司默认（打开）
    assert batch["knowledge_base_enabled"] is True
    assert len(client.app.state.service.model_provider.calls) == 4  # 取公司设置的 4 条
    _settings(client, assistant_enabled=False)
    assert _post(flow, chapter, expected=403, knowledge_base_enabled=True)["code"] == "FORBIDDEN"


def test_sessions_record_turns_carry_history_and_stay_private(client, model):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    model.replies = {"正式、规范": "每月开展一次例行巡检", "删去冗余": "每月巡检", "实质性响应": "按月巡检并提交报告"}
    first = _post(flow, chapter, knowledge_base_enabled=False)
    session_id = first["session_id"]
    model.calls.clear()
    second = _post(flow, chapter, knowledge_base_enabled=False, session_id=session_id, mode="instruction", instruction="再短一点")
    assert second["session_id"] == session_id
    assert "【本会话之前对这段文字的要求与样例】" in model.calls[0][1] and "每月开展一次例行巡检" in model.calls[0][1]
    lease = _lease(flow, chapter["id"])
    _apply(flow, chapter["id"], second, second["samples"][0], lease)
    path = f"{flow.path}/chapters/{chapter['id']}/assistant-sessions"
    mine = client.get(path, headers=flow.headers).json()["sessions"]
    assert [s["id"] for s in mine] == [session_id] and mine[0]["message_count"] == 5
    detail = client.get(f"{flow.path}/assistant-sessions/{session_id}", headers=flow.headers).json()
    assert [m["kind"] for m in detail["messages"]] == ["selection_request", "samples", "selection_request", "samples", "applied"]
    assert detail["messages"][1]["batch"]["id"] == first["id"] and detail["read_only"] is False
    assert detail["messages"][1]["library_query_skipped"] is True
    admin = login(client, "alpha-company-admin")
    seen = client.get(f"{flow.path}/assistant-sessions/{session_id}", headers=admin)
    assert seen.status_code == 200 and seen.json()["read_only"] is True
    other = client.get(f"{flow.path}/assistant-sessions/{session_id}", headers=login(client, "alpha-editor"))
    assert other.status_code == 404
    assert client.get(path, headers=login(client, "alpha-editor")).json()["sessions"] == []
    assert client.get(f"{flow.path}/assistant-sessions/{session_id}", headers=login(client, "beta-manager")).status_code == 404
    # 别人的会话不能拿来继续提问
    workflow = client.app.state.service.repository
    workflow.transaction(lambda st: st.workflows[flow.id]["assistant_sessions"][session_id].update(owner_id="alpha-editor"))
    current = _technical(flow)
    phrase = "报告由负责人复核"
    start = current["content"].index(phrase)
    refused = client.post(f"{flow.path}/chapters/{chapter['id']}/selection-rewrites", headers=flow.headers, json={
        "base_revision": current["revision"], "start": start, "end": start + len(phrase), "selected_text": phrase,
        "knowledge_base_enabled": False, "session_id": session_id})
    assert refused.status_code == 403 and refused.json()["code"] == "FORBIDDEN"


def test_stream_pushes_samples_as_they_finish_then_the_stored_batch(client, model):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    model.replies = {"正式、规范": "每月开展一次例行巡检", "删去冗余": "每月巡检", "实质性响应": "按月巡检并提交报告"}
    resp = client.post(f"{flow.path}/chapters/{chapter['id']}/selection-rewrites/stream", headers=flow.headers,
                       json=_body(chapter, knowledge_base_enabled=False))
    assert resp.status_code == 200 and resp.headers["content-type"].startswith("text/event-stream")
    events = [json.loads(block.split("data: ", 1)[1]) for block in resp.text.strip().split("\n\n") if "data: " in block]
    assert events[0]["event"] == "started" and events[0]["styles"] == ["严谨规范", "简洁精炼", "突出响应"]
    assert [e["event"] for e in events[1:-1]] == ["sample"] * 3 and events[-1]["event"] == "done"
    batch = events[-1]["batch"]
    assert len(batch["samples"]) == 3 and batch["session_id"]
    stored = client.app.state.service.repository.read().workflows[flow.id]["assistant_suggestions"]
    assert batch["id"] in stored
    # 开始前的核对失败按 HTTP 状态返回，不进入事件流
    stale = client.post(f"{flow.path}/chapters/{chapter['id']}/selection-rewrites/stream", headers=flow.headers,
                        json={**_body(chapter, knowledge_base_enabled=False), "base_revision": chapter["revision"] - 1})
    assert stale.status_code == 409 and stale.json()["code"] == "REVISION_CONFLICT"
