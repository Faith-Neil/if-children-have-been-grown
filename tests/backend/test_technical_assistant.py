from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from icg.domain.assistant_qa import _user_content
from icg.domain.technical_assistant import splice_section
from icg_demo.main import create_app
from test_technical_coverage_view import _generate
from test_reference_flow import login

NEW_BODY = "按季度开展健康检查，出具书面报告并跟踪整改闭环，整改结果纳入月度服务报告。"


class RewriteModel:
    is_real_model = True
    name = "stub-rewrite"

    def suggest(self, *_args, **_kwargs):
        return NEW_BODY


@pytest.fixture()
def client():
    with TestClient(create_app()) as value:
        yield value


def test_splice_section_replaces_only_that_section():
    content = "1 服务内容\n1.1 健康检查\n旧正文\n1.2 应急响应\n应急正文\n"
    merged = splice_section(content, "1.1", "健康检查", "新正文")
    assert "新正文" in merged and "旧正文" not in merged and "1.2 应急响应\n应急正文" in merged


def test_section_context_goes_into_question_prompt():
    context = {"heading": {"number": "1.1", "title": "健康检查"}, "points": ["季度检查"],
               "criteria": ["健康检查方案完整得 5 分"], "rejections": ["R-01 未承诺 7×24 小时响应"]}
    text = _user_content("服务方案", [], [], [], [], "这节怎么写", context)
    assert "季度检查" in text and "R-01" in text and "健康检查方案完整" in text


def _first_section(client, headers, project_id):
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    return workspace, workspace["coverage_rows"][0]["outline_title"]


def test_rewrite_section_returns_checked_candidate(client):
    headers, project_id, _events = _generate(client)
    workspace, title = _first_section(client, headers, project_id)
    client.app.state.workflow.demo.resolve_model_provider = lambda *_a, **_k: RewriteModel()
    path = f"/api/v1/projects/{project_id}/technical-sections/rewrite"
    response = client.post(path, json={"section": title, "instruction": "补充季度健康检查"}, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    chapter = next(item for item in workspace["chapters"] if item["id"] == workspace["technical_outline"]["chapter_id"])
    assert body["section_body"] == NEW_BODY and NEW_BODY in body["content"]
    assert body["base_revision"] == chapter["revision"] and body["source_scope"] == "section"
    assert body["precheck"]["status"] in ("passed", "needs_confirm", "failed")
    assert body["rag"]["status"] in ("hit", "empty", "skipped", "failed")
    others = [line for line in chapter["content"].splitlines() if line.strip() and line.strip() != "需要核对"
              and body["original_body"] not in line]
    assert all(line in body["content"] for line in others)

    task_id = workspace["coverage_rows"][0]["task_id"]
    by_key = client.post(path, json={"section": task_id, "instruction": "补充季度健康检查"}, headers=headers)
    assert by_key.status_code == 200 and by_key.json()["section"] == title, by_key.text

    missing = client.post(path, json={"section": "不存在的节", "instruction": "改"}, headers=headers)
    assert missing.status_code == 404


def test_readonly_member_cannot_rewrite(client):
    headers, project_id, _events = _generate(client)
    workspace, title = _first_section(client, headers, project_id)
    team = client.put(f"/api/v1/projects/{project_id}/team", headers={
        **headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())}, json={
        "members": [{"user_id": "alpha-manager", "project_role": "lead", "volumes": ["technical"]},
                    {"user_id": "alpha-editor", "project_role": "readonly", "volumes": ["technical"]}],
        "volumes": [{"volume": "technical", "owner_id": "alpha-manager"}], "assembly_owner_id": "alpha-manager"})
    assert team.status_code == 200, team.text
    client.app.state.workflow.demo.resolve_model_provider = lambda *_a, **_k: RewriteModel()
    reader = login(client, "alpha-editor")
    denied = client.post(f"/api/v1/projects/{project_id}/technical-sections/rewrite",
                         json={"section": title, "instruction": "改"}, headers=reader)
    assert denied.status_code == 403, denied.text


def test_rewrite_respects_company_assistant_switch(client, monkeypatch):
    from icg.domain.selection_rewrite import SelectionRewriteService

    headers, project_id, _events = _generate(client)
    _workspace, title = _first_section(client, headers, project_id)
    client.app.state.workflow.demo.resolve_model_provider = lambda *_a, **_k: RewriteModel()
    monkeypatch.setattr(SelectionRewriteService, "_policy", staticmethod(lambda *_a: {"enabled": False}))
    denied = client.post(f"/api/v1/projects/{project_id}/technical-sections/rewrite",
                         json={"section": title, "instruction": "改"}, headers=headers)
    assert denied.status_code == 403, denied.text


def test_candidate_numbers_checked_before_apply():
    from icg.domain.technical_assistant import number_check
    context = {"rows": [], "points": ["7×24 小时响应"], "criteria": ["2 小时到场得 5 分"]}
    original = "接到报修后 2 小时到场，季度巡检 1 次。"
    passed = number_check(context, "接到报修后 2 小时内到场处理。", original, "", [], [])
    assert passed == {"status": "passed", "mismatched_requirements": [], "unsupported": []}
    flagged = number_check(context, "接到报修后 30 分钟到场，配备 6 名工程师。", original, "", [], [])
    assert flagged["status"] == "needs_confirm" and flagged["unsupported"] == ["30分钟", "6名"]
    grounded = number_check(context, "配备 6 名工程师。", original, "", [{"content": "历史项目配备 6 名驻场工程师"}], [])
    assert grounded["status"] == "passed"
    from_fact = number_check(context, "配备 6 名工程师。", original, "", [], [{"value": "6", "unit": "名"}])
    assert from_fact["status"] == "passed"
    per = number_check(context, "每年巡检 2 次/月，30 自然日内整改。", "每年巡检 2 次/年，15 自然日内整改。", "", [], [])
    assert per["unsupported"] == ["2次/月", "30自然日"]


def test_label_free_rewrite_is_not_flagged_when_original_is_label_free_too():
    from icg.domain.technical_assistant import number_check
    row = {"id": "R-1", "response_type": "comply", "text": "2 小时到场"}
    original = "接到报修后 2 小时到场。"
    result = number_check({"rows": [row]}, "接到报修后 2 小时内到场处理。", original, "", [], [])
    assert result["mismatched_requirements"] == []
    wrong = number_check({"rows": [row]}, "负偏离。接到报修后 2 小时内到场处理。", original, "", [], [])
    assert wrong["mismatched_requirements"] == ["R-1"]
    negated = number_check({"rows": [row]}, "接到报修后 2 小时内到场处理，不产生负偏离。", original, "", [], [])
    assert negated["mismatched_requirements"] == []


def test_rewrite_candidate_carries_number_check(client):
    headers, project_id, _events = _generate(client)
    _workspace, title = _first_section(client, headers, project_id)

    class NumberModel(RewriteModel):
        def suggest(self, *_args, **_kwargs):
            return NEW_BODY + "故障 15 分钟响应，现场配备 9 名工程师。"

    client.app.state.workflow.demo.resolve_model_provider = lambda *_a, **_k: NumberModel()
    response = client.post(f"/api/v1/projects/{project_id}/technical-sections/rewrite",
                           json={"section": title, "instruction": "加承诺"}, headers=headers)
    assert response.status_code == 200, response.text
    numbers = response.json()["numbers"]
    assert numbers["status"] == "needs_confirm" and {"15分钟", "9名"} <= set(numbers["unsupported"])


def test_question_sessions_are_kept_per_section(client):
    from icg.domain.assistant_qa import AssistantQAService
    from icg.domain.assistant_sessions import list_sessions, record_question
    from icg.domain.domain import DomainError, Principal

    headers, project_id, _events = _generate(client)
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    rows = workspace["coverage_rows"]
    first, second = rows[0], next(row for row in rows if row["task_id"] != rows[0]["task_id"])
    chapter_id = workspace["technical_outline"]["chapter_id"]
    demo = client.app.state.workflow.demo
    state = demo.repository.read()
    token = headers["Authorization"].split(" ", 1)[1]
    principal = Principal(state.accounts[state.sessions[token]], token)
    record = {"question": "这节怎么写", "knowledge_base_enabled": True, "route": "model", "answer": "答"}

    def write(state):
        chapter = state.chapters[chapter_id]
        flow = state.workflows.setdefault(project_id, {})
        return record_question(flow, principal, chapter, record, None, "2026-11-24T00:00:00Z",
                               {"key": first["task_id"], "title": first["outline_title"]})

    session_id = demo.repository.transaction(write)
    listed = list_sessions(demo, principal, project_id, chapter_id, first["task_id"])["sessions"]
    assert [item["id"] for item in listed] == [session_id] and listed[0]["section_title"] == first["outline_title"]
    assert list_sessions(demo, principal, project_id, chapter_id, second["task_id"])["sessions"] == []

    qa = AssistantQAService(demo, client.app.state.selection_rewrite)
    with pytest.raises(DomainError) as other:
        qa.prepare(principal, project_id, chapter_id, {"question": "续问", "session_id": session_id, "section": second["task_id"]})
    assert other.value.status == 403 and "别的小节" in other.value.message
    with pytest.raises(DomainError) as same:
        qa.prepare(principal, project_id, chapter_id, {"question": "续问", "session_id": session_id, "section": first["task_id"]})
    assert same.value.code != "FORBIDDEN"  # 同一小节通过会话校验，后面才因未接知识库/模型停下
