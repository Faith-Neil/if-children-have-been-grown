# 为什么有这个文件：验证编辑台选区改写（PRD v1.8 §5.11.4～5.11.8，APP-M2-T178、T180、T185、T187）。
# 它解决什么问题：模型只拿到选区及前后段、本章条款和项目事实；样例经预检；写入只改选区、生成新版本并记编辑操作；
# 选区变化时重新定位或失效；没有编辑锁、系统章节、未接入真实模型时都不写入。

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from test_reference_flow import ProjectFlow, login

SENTENCE = "每月安排巡检"


class ScriptedModel:
    """按写法返回不同样例，并记录收到的提示词；视为真实模型。"""
    name, is_real_model, is_local, model = "scripted", True, True, "scripted-1"

    def __init__(self):
        self.calls, self.replies = [], {
            "严谨规范": "以下是改写后的内容：每月开展一次例行巡检",
            "简洁精炼": "**每月巡检**",
            "突出响应": "按月巡检并配备 5 名工程师",
            "条理分明": "每月开展一次例行巡检",            # 与第一条相同，应合并
            "平实易读": "每月去现场巡检，联系 13812345678",  # 含手机号，应过滤
        }

    def suggest(self, system, user):
        self.calls.append((system, user))
        return next(text for label, text in self.replies.items() if label in system or self._hint(label) in system)

    @staticmethod
    def _hint(label):
        from icg.domain.selection_rewrite import STYLES
        return next(hint for _, name, hint in STYLES if name == label)


@pytest.fixture()
def model():
    return ScriptedModel()


@pytest.fixture()
def client(model):
    with TestClient(create_app(model_provider=model)) as actual:
        yield actual


def _technical(flow):
    return next(c for c in flow.state()["chapters"] if c["volume"] == "technical")


def _lease(flow, chapter_id):
    lock = flow.client.post(f"/api/chapters/{chapter_id}/lock", headers=flow.headers, json={})
    assert lock.status_code == 200, lock.text
    return lock.json()["lease_token"]


def _ask(flow, chapter, text=SENTENCE, expected=200, **extra):
    content = chapter["content"]
    start = content.index(text)
    body = {"base_revision": chapter["revision"], "start": start, "end": start + len(text), "selected_text": text,
            "knowledge_base_enabled": False, **extra}
    resp = flow.client.post(f"{flow.path}/chapters/{chapter['id']}/selection-rewrites", headers=flow.headers, json=body)
    assert resp.status_code == expected, resp.text
    return resp.json()


def _apply(flow, chapter_id, batch, sample, lease, action="replace", expected=200, **extra):
    resp = flow.client.post(f"{flow.path}/chapters/{chapter_id}/selection-rewrites/{batch['id']}/apply", headers=flow.headers,
                            json={"lease_token": lease, "sample_id": sample["id"], "action": action, **extra})
    assert resp.status_code == expected, resp.text
    return resp.json()


def test_samples_are_generated_from_the_selection_only_and_prechecked(client, model):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    batch = _ask(flow, chapter, count=5)
    system, user = model.calls[0]
    assert len(model.calls) == 5
    assert f"【选中的文字】\n{SENTENCE}" in user and "只修改用户选中的那段文字" in system
    assert "商务正文验收标记" not in user  # 别的章节不进模型
    texts = {s["style_label"]: s for s in batch["samples"]}
    assert texts["严谨规范"]["text"] == "每月开展一次例行巡检"          # 去掉“以下是…：”
    assert texts["简洁精炼"]["text"] == "每月巡检"                       # 去掉 Markdown
    assert "【待补：数值来源】" in texts["突出响应"]["text"] and texts["突出响应"]["warnings"]
    assert "条理分明" not in texts and "平实易读" not in texts
    reasons = " ".join(d["reason"] for d in batch["dropped"])
    assert "手机号" in reasons and "合并" in reasons
    assert batch["knowledge_base_enabled"] is False and "无知识库来源" in batch["source_note"]
    assert batch["retrieval"]["status"] == "off" and batch["session_id"]
    assert all(s["status"] == "proposed" and s["sources"] == [] for s in batch["samples"])


def test_replace_writes_only_the_selection_as_a_new_version_with_an_edit_record(client):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    batch = _ask(flow, chapter)
    sample = next(s for s in batch["samples"] if s["style_label"] == "严谨规范")
    lease = _lease(flow, chapter["id"])
    result = _apply(flow, chapter["id"], batch, sample, lease)
    expected = chapter["content"].replace(SENTENCE, "每月开展一次例行巡检", 1)
    assert result["content"] == expected and result["revision"] == chapter["revision"] + 1
    operation = result["operation"]
    assert operation["edit_mode"] == "assistant_replace" and operation["edit_mode_label"] == "对话助手替换"
    assert operation["base_revision"] == chapter["revision"] and operation["result_revision"] == result["revision"]
    assert operation["original_text"] == SENTENCE and operation["source_note"] == "无知识库来源"
    assert operation["recheck"]["scope"] == "changed_paragraphs"
    assert {s["status"] for s in result["batch"]["samples"]} == {"adopted", "not_adopted"}
    listed = client.get(f"{flow.path}/chapters/{chapter['id']}/edit-operations", headers=flow.headers).json()["operations"]
    assert [o["id"] for o in listed] == [operation["id"]]
    versions = client.get(f"/api/chapters/{chapter['id']}/versions", headers=flow.headers).json()["versions"]
    assert versions[-1]["content"] == expected
    # 同一组样例不能再写一次
    again = _apply(flow, chapter["id"], batch, sample, lease, expected=409)
    assert again["code"] == "REVISION_CONFLICT"


def test_insert_after_keeps_the_original_and_recheck_flags_placeholders(client):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    batch = _ask(flow, chapter)
    sample = next(s for s in batch["samples"] if s["style_label"] == "突出响应")
    lease = _lease(flow, chapter["id"])
    result = _apply(flow, chapter["id"], batch, sample, lease, action="insert_after")
    assert SENTENCE in result["content"] and sample["text"] in result["content"]
    assert result["content"].index(sample["text"]) == result["content"].index(SENTENCE) + len(SENTENCE)
    rules = {i["rule_id"] for i in result["operation"]["recheck"]["issues"]}
    assert "R15" in rules and result["operation"]["edit_mode"] == "assistant_insert"


def test_moved_selection_is_relocated_after_confirmation_and_ambiguous_one_invalidates(client):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    batch = _ask(flow, chapter)
    sample = batch["samples"][0]
    flow.commit(chapter["id"], "新增开头一句。\n" + chapter["content"])
    lease = _lease(flow, chapter["id"])
    moved = _apply(flow, chapter["id"], batch, sample, lease, expected=409)
    assert moved["details"]["relocated"] is True
    start = moved["details"]["start"]
    done = _apply(flow, chapter["id"], batch, sample, lease, confirm_start=start)
    assert done["operation"]["selection"]["relocated"] is True and sample["text"] in done["content"]
    client.post(f"/api/chapters/{chapter['id']}/lock/release", headers=flow.headers, json={"lease_token": lease})
    # 原文位置变了且出现两次：无法唯一定位，整组样例失效
    current = _technical(flow)
    batch2 = _ask(flow, current, text="新增开头一句")
    flow.commit(chapter["id"], "前置说明：新增开头一句。\n" + current["content"])
    lease = _lease(flow, chapter["id"])
    gone = _apply(flow, chapter["id"], batch2, batch2["samples"][0], lease, expected=409)
    assert gone["details"]["relocated"] is False
    retry = _apply(flow, chapter["id"], batch2, batch2["samples"][0], lease, expected=409)
    assert "已采纳或已失效" in retry["message"]


def test_writing_requires_the_lock_and_drafts_become_a_manual_version_first(client):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    batch = _ask(flow, chapter)
    lost = _apply(flow, chapter["id"], batch, batch["samples"][0], "not-my-lease", expected=423)
    assert lost["code"] == "LOCK_LOST"
    lease = _lease(flow, chapter["id"])
    draft = client.put(f"/api/chapters/{chapter['id']}/draft", headers=flow.headers, json={
        "lease_token": lease, "base_revision": chapter["revision"], "sequence": 1,
        "content": chapter["content"] + "\n草稿里补的一句。", "input_fingerprint": flow.state()["input_fingerprint"]})
    assert draft.status_code == 200, draft.text
    result = _apply(flow, chapter["id"], batch, batch["samples"][0], lease)
    assert result["revision"] == chapter["revision"] + 2 and "草稿里补的一句。" in result["content"]
    versions = client.get(f"/api/chapters/{chapter['id']}/versions", headers=flow.headers).json()["versions"]
    assert [v.get("edit_mode") for v in versions[-2:]] == ["manual", "assistant_replace"]


def test_selection_must_match_committed_text_and_permissions_are_enforced(client):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    start = chapter["content"].index(SENTENCE)
    wrong = client.post(f"{flow.path}/chapters/{chapter['id']}/selection-rewrites", headers=flow.headers, json={
        "base_revision": chapter["revision"], "start": start, "end": start + 3, "selected_text": SENTENCE, "knowledge_base_enabled": False})
    assert wrong.status_code == 409 and wrong.json()["code"] == "REVISION_CONFLICT"
    stale = client.post(f"{flow.path}/chapters/{chapter['id']}/selection-rewrites", headers=flow.headers, json={
        "base_revision": chapter["revision"] - 1, "start": start, "end": start + len(SENTENCE), "selected_text": SENTENCE,
        "knowledge_base_enabled": False})
    assert stale.status_code == 409
    need = client.post(f"{flow.path}/chapters/{chapter['id']}/selection-rewrites", headers=flow.headers, json={
        "base_revision": chapter["revision"], "start": start, "end": start + len(SENTENCE), "selected_text": SENTENCE,
        "mode": "instruction", "knowledge_base_enabled": False})
    assert need.status_code == 422
    body = {"base_revision": chapter["revision"], "start": start, "end": start + len(SENTENCE), "selected_text": SENTENCE,
            "knowledge_base_enabled": False}
    viewer = client.post(f"{flow.path}/chapters/{chapter['id']}/selection-rewrites", headers=login(client, "alpha-viewer"), json=body)
    assert viewer.status_code in (403, 404)
    beta = client.post(f"{flow.path}/chapters/{chapter['id']}/selection-rewrites", headers=login(client, "beta-manager"), json=body)
    assert beta.status_code == 404
    # 指令要求改项目事实取值：不生成样例
    facts = flow.state()["facts"]
    if facts:
        refused = client.post(f"{flow.path}/chapters/{chapter['id']}/selection-rewrites", headers=flow.headers, json={
            **body, "mode": "instruction", "instruction": f"把{facts[0]['key']}改成另一个值"})
        assert refused.status_code == 409 and refused.json()["code"] == "FACT_SOURCE_CHANGE_REQUIRED"


def test_variables_must_survive_and_new_ones_are_rejected(client, model):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    fact = next(f for f in flow.state()["facts"] if f["status"] == "confirmed")
    token = "{{fact:" + fact["id"] + "}}"
    flow.commit(chapter["id"], f"项目编号为{token}，每月安排巡检。")
    chapter = _technical(flow)
    model.replies = {"严谨规范": "项目编号为本项目编号，每月巡检。", "简洁精炼": f"编号{token}，每月巡检。",
                     "突出响应": f"编号{token}，每月巡检，见{{{{fact:other}}}}。"}
    batch = _ask(flow, chapter, text=f"项目编号为{token}，每月安排巡检。")
    assert [s["style_label"] for s in batch["samples"]] == ["简洁精炼"]
    reasons = " ".join(d["reason"] for d in batch["dropped"])
    assert "丢失了选区中的变量" in reasons and "选区以外的变量" in reasons


def test_system_chapter_never_produces_samples(client, model, monkeypatch):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    import icg.domain.system_chapters as system_chapters
    monkeypatch.setattr(system_chapters, "is_system_chapter", lambda wf, ch: ch.id == chapter["id"])
    blocked = _ask(flow, chapter, expected=409)
    assert blocked["code"] == "SYSTEM_CHAPTER_READONLY" and model.calls == []


def test_demo_model_is_refused_instead_of_returning_fake_samples():
    with TestClient(create_app()) as plain:
        flow = ProjectFlow(plain).ready()
        chapter = _technical(flow)
        refused = _ask(flow, chapter, expected=502)
        assert refused["code"] == "MODEL_UNAVAILABLE" and "不提供模拟样例" in refused["message"]


def test_project_without_tender_keeps_a_complete_workspace_after_writing(client):
    """新建项目尚无工作流记录：写入样例后工作区仍能读取（曾因新建空工作流缺字段而 500）。"""
    headers = login(client, "alpha-manager")
    project_id = client.post("/api/v1/projects", headers=headers, json={"name": "无招标文件的项目"}).json()["id"]
    path = f"/api/v1/projects/{project_id}"
    chapter = next(c for c in client.get(path + "/workspace", headers=headers).json()["chapters"] if c["volume"] == "technical")
    lease = client.post(f"/api/chapters/{chapter['id']}/lock", headers=headers, json={}).json()["lease_token"]
    body = f"技术方案：{SENTENCE}，报告由负责人复核。"
    assert client.post(f"/api/chapters/{chapter['id']}/versions", headers=headers, json={
        "lease_token": lease, "base_revision": chapter["revision"], "content": body, "idempotency_key": str(uuid4())}).status_code == 200
    start = body.index(SENTENCE)
    batch = client.post(f"{path}/chapters/{chapter['id']}/selection-rewrites", headers=headers, json={
        "base_revision": chapter["revision"] + 1, "start": start, "end": start + len(SENTENCE), "selected_text": SENTENCE,
        "knowledge_base_enabled": False}).json()
    applied = client.post(f"{path}/chapters/{chapter['id']}/selection-rewrites/{batch['id']}/apply", headers=headers,
                          json={"lease_token": lease, "sample_id": batch["samples"][0]["id"], "action": "replace"})
    assert applied.status_code == 200, applied.text
    workspace = client.get(path + "/workspace", headers=headers)
    assert workspace.status_code == 200, workspace.text


def test_precheck_rejects_real_model_failure_modes():
    """2026-10-29 用真实模型（经 RAGFlow 的 OpenAI 兼容接口）试跑时遇到的情况。"""
    from icg.domain.selection_rewrite import precheck
    pick = "我方配备驻场工程师，按招标要求提供运维服务。"
    quota = "**ERROR**: Error 429, Message: You exceeded your current quota, please check your plan"
    assert "错误信息" in precheck(quota, pick, "replace", set())[2]
    whole_chapter = "### 技术方案\n" + "我方承诺全面响应招标要求并配备专业团队。" * 40
    assert "超出选区改写范围" in precheck(whole_chapter, pick, "replace", set())[2]
    assert "没有变短" in precheck("我方配备驻场工程师，严格按照招标文件要求提供运维服务。", pick, "replace", set(), mode="shorten")[2]
    token = "{{fact:fact-1}}"
    ok, _, reason = precheck(f"我方为本项目（编号 {token}）配备驻场工程师。", pick, "replace", set(), allowed_vars={token})
    assert ok and token in ok and not reason
    assert "选区以外的变量" in precheck("编号 {{fact:unknown}}，配备驻场工程师。", pick, "replace", set(), allowed_vars={token})[2]
    cleaned, _, _ = precheck("基于您提供的要求，改写如下：\n---\n**我方安排驻场工程师**，按要求开展运维。", pick, "replace", set())
    assert cleaned == "我方安排驻场工程师，按要求开展运维。"
