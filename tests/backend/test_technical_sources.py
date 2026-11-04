# 为什么有这个文件：核对技术分册的项目文件规则。
# 它解决什么问题：两册旧项目仍可上传文本和补遗；新建技术分册只收三种文件，同一批文件不能再抽。

from __future__ import annotations

import base64
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from test_reference_flow import login


@pytest.fixture()
def client():
    with TestClient(create_app()) as actual:
        yield actual


def _docx(text: str) -> bytes:
    from xml.sax.saxutils import escape
    # WordprocessingML 不允许多数控制字符；换页符改成换行后再切段。
    cleaned = "".join(ch if ch in "\t\n\r" or ord(ch) >= 32 else "\n" for ch in text)
    paragraphs = "".join(
        f"<w:p><w:r><w:t>{escape(line)}</w:t></w:r></w:p>" for line in cleaned.split("\n")
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{paragraphs}</w:body></w:document>"
    )
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types/>')
        archive.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships/>')
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


def _project(client, headers):
    created = client.post("/api/v1/projects", headers=headers, json={"name": "合成技术分册文件", "volume_mode": "technical_only"})
    assert created.status_code == 200, created.text
    project_id = created.json()["id"]
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers)
    assert workspace.status_code == 200, workspace.text
    return project_id, workspace.json()["revision"]


def _upload(client, headers, project_id, revision, filename, role="tender", content=b"x"):
    return client.post(
        f"/api/v1/projects/{project_id}/files",
        headers={**headers, "If-Match": str(revision), "Idempotency-Key": str(uuid4())},
        json={"filename": filename, "file_role": role, "content_base64": base64.b64encode(content).decode()},
    )


def test_file_change_keeps_existing_body():
    from icg.domain.technical_sources import invalidate_after_file_change
    chapter = SimpleNamespace(id="c1", project_id="p", content="已有正文")
    state = SimpleNamespace(chapters={"c1": chapter}, project_teams={"p": {"volume_mode": "technical_only"}})
    workflow = {"requirements": {"r": {"volume_confirmed_at": "2026-11-03", "volume_confirmed_by": "u"}}, "files": {}}
    invalidate_after_file_change(state, "p", workflow)
    assert chapter.content == "已有正文"
    assert workflow["needs_regeneration"] == ["c1"]
    assert workflow["plan_confirmed"] is False
    assert workflow["requirements"]["r"]["volume_confirmed_at"] is None


def test_technical_upload_accepts_three_roles_only(client):
    headers = login(client)
    project_id, revision = _project(client, headers)
    text = _upload(client, headers, project_id, revision, "招标.txt", content="招标".encode())
    assert text.status_code == 422 and text.json()["code"] == "FILE_TYPE_UNSUPPORTED"
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    addendum = _upload(client, headers, project_id, workspace["revision"], "补遗.docx", role="addendum", content=_docx("补遗"))
    assert addendum.status_code == 422 and addendum.json()["code"] == "VALIDATION_ERROR"
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    missing = client.post(
        f"/api/v1/projects/{project_id}/parse",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={},
    )
    assert missing.status_code == 422 and missing.json()["code"] == "FILES_REQUIRED"
    for role, name in (("tender", "招标.docx"), ("tech_spec", "规范.docx"), ("attachment", "辅助.docx")):
        workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
        uploaded = _upload(client, headers, project_id, workspace["revision"], name, role=role, content=_docx(name))
        assert uploaded.status_code == 200, uploaded.text
        assert uploaded.json()["file"]["file_role"] == role


def test_extract_keeps_scoring_points_and_spec_clauses_on_one_row(client):
    from icg.domain.technical_clause_extract import extract_technical_clauses
    pages = ["\n".join([
        "封面",
        "1 技术规范定义",
        "1.1 术语",
        "2.3.1 标准服务",
        "服务方案中应包含数据库的健康检查、故障处理、标准服务等。",
        "客观分：企业资质 10 分",
        "报价得分按最低价计算",
    ])]
    clauses = extract_technical_clauses(pages)
    texts = [item.text for item in clauses]
    assert "健康检查" in texts and "故障处理" in texts
    assert "术语" not in texts and not any("客观" in item or "报价" in item for item in texts)
    standard = next(item for item in clauses if item.text == "标准服务")
    assert len(standard.sources) == 2

    headers = login(client)
    project_id, revision = _project(client, headers)
    uploaded = _upload(client, headers, project_id, revision, "招标.docx", content=_docx(pages[0]))
    assert uploaded.status_code == 200, uploaded.text
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    parsed = client.post(
        f"/api/v1/projects/{project_id}/parse",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={},
    )
    assert parsed.status_code == 200, parsed.text
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    assert workspace["technical_extract_empty"] is False
    rows = [row["text"] for row in workspace["requirements"] if row.get("technical_clause")]
    assert "健康检查" in rows and "标准服务" in rows
    assert workspace["technical_outline"]["title"] == "服务方案"
    titles = [item["title"] for item in workspace["technical_outline"]["headings"]]
    assert titles[:4] == ["服务方式", "标准服务", "服务内容", "健康检查"]
    chapter = next(item for item in workspace["chapters"] if item["volume"] == "technical")
    assert chapter["title"] == "服务方案"
    assert "1.2.1 健康检查" in chapter["content"]


def test_empty_technical_extract_stops(client):
    headers = login(client)
    project_id, revision = _project(client, headers)
    uploaded = _upload(client, headers, project_id, revision, "招标.docx", content=_docx("封面\n目录\n报价一览表"))
    assert uploaded.status_code == 200, uploaded.text
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    parsed = client.post(
        f"/api/v1/projects/{project_id}/parse",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={},
    )
    assert parsed.status_code == 200, parsed.text
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    assert workspace["technical_extract_empty"] is True
    assert workspace["technical_outline"] is None
    assert not [row for row in workspace["requirements"] if row.get("technical_clause")]
    assert next(item for item in workspace["chapters"] if item["volume"] == "technical")["title"] == "技术方案"


def test_same_files_cannot_be_extracted_twice(client):
    headers = login(client)
    project_id, revision = _project(client, headers)
    uploaded = _upload(client, headers, project_id, revision, "招标.docx", content=_docx("合成招标文件技术要求每月巡检"))
    assert uploaded.status_code == 200, uploaded.text
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    first = client.post(
        f"/api/v1/projects/{project_id}/parse",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={},
    )
    assert first.status_code == 200, first.text
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    assert workspace["parsed_source_fingerprint"] == workspace["source_fingerprint"]
    again = client.post(
        f"/api/v1/projects/{project_id}/parse",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={},
    )
    assert again.status_code == 409 and again.json()["code"] == "SAME_SOURCE_FILES"


def test_outline_uses_tender_title_and_blocks_confirm_until_each_clause_has_a_heading(client):
    headers = login(client)
    project_id, revision = _project(client, headers)
    before = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    assert before["technical_outline"] is None
    assert next(item["title"] for item in before["chapters"] if item["volume"] == "technical") == "技术方案"
    text = "\n".join([
        "技术服务方案",
        "服务方案中应包含数据库的健康检查、故障处理、培训等。",
    ])
    uploaded = _upload(client, headers, project_id, revision, "招标.docx", content=_docx(text))
    assert uploaded.status_code == 200, uploaded.text
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    parsed = client.post(
        f"/api/v1/projects/{project_id}/parse",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={},
    )
    assert parsed.status_code == 200, parsed.text
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    assert workspace["technical_outline"]["title"] == "技术服务方案"
    titles = [item["title"] for item in workspace["technical_outline"]["headings"] if item["level"] == 3]
    assert titles == ["健康检查", "故障处理", "培训"]
    groups = [item["title"] for item in workspace["technical_outline"]["headings"] if item["level"] == 2]
    assert groups == ["服务内容", "培训"]
    chapter = next(item for item in workspace["chapters"] if item["id"] == workspace["technical_outline"]["chapter_id"])
    confirmed = client.post(
        f"/api/v1/projects/{project_id}/plan",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={"scope": "technical", "chapters": [{"id": chapter["id"], "title": "技术服务方案", "volume": "technical"}]},
    )
    assert confirmed.status_code == 200, confirmed.text
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    assert workspace["plan_confirmed"] is True
    assert [item["title"] for item in workspace["chapters"] if item["volume"] == "technical"] == ["技术服务方案"]
    locked = client.post(f"/api/chapters/{chapter['id']}/lock", headers=headers, json={})
    assert locked.status_code == 200, locked.text
    saved = client.post(
        f"/api/chapters/{chapter['id']}/versions",
        headers=headers,
        json={
            "lease_token": locked.json()["lease_token"],
            "base_revision": chapter["revision"],
            "content": chapter["content"].replace("1.2.1 培训\n", ""),
            "input_fingerprint": workspace["input_fingerprint"],
            "idempotency_key": str(uuid4()),
        },
    )
    assert saved.status_code == 200, saved.text
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    assert workspace["plan_confirmed"] is True
    again = client.post(
        f"/api/v1/projects/{project_id}/plan",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={"scope": "technical", "chapters": [{"id": chapter["id"], "title": "技术服务方案", "volume": "technical"}]},
    )
    assert again.status_code == 200, again.text


def _parse_clause(client, headers, text):
    project_id, revision = _project(client, headers)
    uploaded = _upload(client, headers, project_id, revision, "招标.docx", content=_docx(text))
    assert uploaded.status_code == 200, uploaded.text
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    parsed = client.post(
        f"/api/v1/projects/{project_id}/parse",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={},
    )
    assert parsed.status_code == 200, parsed.text
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    return project_id, workspace


def test_history_hit_defaults_to_no_deviation_and_model_rows_confirm_one_by_one(client):
    from icg.domain.technical_matrix import bind_deviation_judge, bind_history_search, reset_deviation_judge, reset_history_search
    headers = login(client)
    search = bind_history_search(lambda query: [
        {"filename": "2023合成.docx", "quote": "《其他项目》健康检查每30分钟一次", "score": 0.9},
        {"filename": "次近.docx", "quote": "另一条", "score": 0.2},
    ] if "健康检查" in query else [])
    judge = bind_deviation_judge(lambda _clause, quote: {
        "deviation": "正偏离",
        "reason": "历史巡检为每30分钟一次，高于本次招标没有写明间隔的要求。",
    } if "30" in quote else {"deviation": "无偏离", "reason": ""})
    try:
        project_id, workspace = _parse_clause(client, headers, "服务方案中应包含数据库的健康检查、故障处理等。")
    finally:
        reset_history_search(search)
        reset_deviation_judge(judge)
    rows = {row["text"]: row for row in workspace["requirements"] if row.get("technical_clause")}
    hit = rows["健康检查"]
    assert hit["response_origin"] == "history" and hit["history_filename"] == "2023合成.docx"
    assert hit["response_type"] == "exceed" and "正偏离" in hit["response"] and "30" in hit["deviation_reason"]
    assert "《其他项目》" not in hit["response"] and "《其他项目》" not in hit["history_quote"]
    drafted = rows["故障处理"]
    assert drafted["response_origin"] == "model" and drafted["history_filename"] == ""
    mixed = client.post(
        f"/api/v1/projects/{project_id}/requirements/batch-confirm",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={"requirement_ids": [hit["id"], drafted["id"]]},
    )
    assert mixed.status_code == 409 and mixed.json()["code"] == "REQUIREMENT_NOT_READY"
    accepted = client.post(
        f"/api/v1/projects/{project_id}/requirements/batch-confirm",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={"requirement_ids": [hit["id"]]},
    )
    assert accepted.status_code == 409 and accepted.json()["code"] == "REQUIREMENT_NOT_READY"
    one_history = client.patch(
        f"/api/v1/projects/{project_id}/requirements/{hit['id']}",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={"status": "confirmed"},
    )
    assert one_history.status_code == 200, one_history.text
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    rows = {row["text"]: row for row in workspace["requirements"] if row.get("technical_clause")}
    assert rows["健康检查"]["status"] == "confirmed" and rows["故障处理"]["status"] == "pending"
    exceeded = client.patch(
        f"/api/v1/projects/{project_id}/requirements/{rows['故障处理']['id']}",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={"response_type": "exceed"},
    )
    assert exceeded.status_code == 422 and exceeded.json()["code"] == "REASON_REQUIRED"
    one = client.patch(
        f"/api/v1/projects/{project_id}/requirements/{rows['故障处理']['id']}",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={"status": "confirmed"},
    )
    assert one.status_code == 200, one.text

    def broken_search(_query):
        raise RuntimeError("检索中断")

    failed_search = bind_history_search(broken_search)
    try:
        failed_id, failed_workspace = _parse_clause(client, headers, "服务方案中应包含数据库的健康检查、故障处理等。")
    finally:
        reset_history_search(failed_search)
    failed = next(row for row in failed_workspace["requirements"] if row.get("technical_clause"))
    assert failed["response_origin"] == "retrieval_failed" and failed["response"] == ""
    refused = client.patch(
        f"/api/v1/projects/{failed_id}/requirements/{failed['id']}",
        headers={**headers, "If-Match": str(failed_workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={"status": "confirmed"},
    )
    assert refused.status_code == 409 and refused.json()["code"] == "REQUIREMENT_NOT_READY"


def test_matching_history_stays_no_deviation_and_lower_history_is_negative():
    from icg.domain.technical_matrix import fill_technical_responses, parse_judgment
    assert parse_judgment('{"deviation":"负偏离","reason":"响应时限做不到招标的15分钟"}')["deviation"] == "负偏离"
    workflow = {"requirements": {
        "same": {"id": "same", "text": "每月巡检一次", "technical_clause": True, "status": "pending"},
        "lower": {"id": "lower", "text": "故障15分钟内响应", "technical_clause": True, "status": "pending"},
    }}

    def judge(clause, _quote):
        if "15" in clause:
            return {"deviation": "负偏离", "reason": "历史做法是30分钟响应，低于招标要求的15分钟。"}
        return {"deviation": "无偏离", "reason": ""}

    from icg.domain.technical_matrix import bind_deviation_judge, bind_history_search, reset_deviation_judge, reset_history_search
    search = bind_history_search(lambda query: [{"filename": "2023合成.docx", "quote": query, "score": 1}])
    token = bind_deviation_judge(judge)
    try:
        fill_technical_responses(SimpleNamespace(projects={}), workflow)
    finally:
        reset_history_search(search)
        reset_deviation_judge(token)
    assert workflow["requirements"]["same"]["response_type"] == "comply"
    assert workflow["requirements"]["lower"]["response_type"] == "deviate"
    assert "30分钟" in workflow["requirements"]["lower"]["deviation_reason"]
    blocked = {"requirements": {"r": {"id": "r", "text": "健康检查", "technical_clause": True, "status": "pending"}}}

    class PublicModel:
        is_real_model = True
        is_local = False

        def suggest(self, *_args):
            raise AssertionError("不能把条款发给公网模型")

    again = bind_history_search(lambda _query: [{"filename": "a.docx", "quote": "每30分钟", "score": 1}])
    try:
        fill_technical_responses(SimpleNamespace(projects={}), blocked, model=PublicModel())
    finally:
        reset_history_search(again)
    assert blocked["requirements"]["r"]["response_origin"] == "draft_failed"
    assert blocked["requirements"]["r"]["response"] == ""
    assert blocked["requirements"]["r"]["history_filename"] == "a.docx"


def _confirm_plan(client, headers, project_id):
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    chapter = next(item for item in workspace["chapters"] if item["volume"] == "technical" and item["id"] == workspace["technical_outline"]["chapter_id"])
    confirmed = client.post(
        f"/api/v1/projects/{project_id}/plan",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={"scope": "technical", "chapters": [{"id": chapter["id"], "title": chapter["title"], "volume": "technical"}]},
    )
    assert confirmed.status_code == 200, confirmed.text
    return client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()


def _patch_requirement(client, headers, project_id, revision, requirement_id, payload):
    result = client.patch(
        f"/api/v1/projects/{project_id}/requirements/{requirement_id}",
        headers={**headers, "If-Match": str(revision), "Idempotency-Key": str(uuid4())},
        json=payload,
    )
    assert result.status_code == 200, result.text
    return result.json()["revision"]


def _document_xml(content: bytes) -> str:
    with ZipFile(BytesIO(content)) as archive:
        return archive.read("word/document.xml").decode("utf-8")


def test_draft_failure_does_not_write_a_satisfied_response():
    from icg.domain.technical_matrix import bind_history_draft, fill_technical_responses, reset_history_draft
    workflow = {"requirements": {"r": {"id": "r", "text": "健康检查", "technical_clause": True, "status": "pending"}}}

    def broken(_text):
        raise RuntimeError("拟写中断")

    token = bind_history_draft(broken)
    try:
        fill_technical_responses(SimpleNamespace(projects={}), workflow)
    finally:
        reset_history_draft(token)
    assert workflow["requirements"]["r"]["response_origin"] == "draft_failed"
    assert workflow["requirements"]["r"]["response"] == ""


def test_section_text_follows_write_order_and_one_section_can_fail():
    from icg.domain.domain import DomainError
    from icg.domain.technical_volume import assert_ready, produce_section
    blocked = {"plan_confirmed": False, "technical_outline": {"headings": []}, "technical_retrieval": "done", "requirements": {}}
    with pytest.raises(DomainError) as caught:
        assert_ready(SimpleNamespace(chapters={}), "p", blocked)
    assert caught.value.code == "REQUIREMENT_NOT_READY"

    class PublicModel:
        is_real_model = True
        is_local = False

        def suggest(self, *_args):
            raise AssertionError("不能把正文发给公网模型")

    drafted = produce_section("健康检查", {
        "text": "健康检查", "response": "每30分钟巡检一次", "response_type": "exceed",
        "deviation_reason": "高于招标要求", "status": "confirmed", "response_origin": "history",
    }, PublicModel())
    assert "响应说明" in drafted and "服务目标" in drafted and "每30分钟" in drafted


def test_generate_writes_six_parts_without_blocking_internal_export(client):
    from icg.domain.technical_volume import bind_section_writer, reset_section_writer, stand_in
    headers = login(client)
    project_id, workspace = _parse_clause(client, headers, "服务方案中应包含数据库的健康检查、故障处理、标准服务等。")
    early = client.post(
        f"/api/v1/projects/{project_id}/generate",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={},
    )
    assert early.status_code == 409 and early.json()["code"] == "REQUIREMENT_NOT_READY"
    workspace = _confirm_plan(client, headers, project_id)
    chapter = next(item for item in workspace["chapters"] if item["id"] == workspace["technical_outline"]["chapter_id"])
    assert "响应说明" not in chapter["content"]
    rows = {row["text"]: row for row in workspace["requirements"] if row.get("technical_clause")}
    revision = workspace["revision"]
    for name in ("健康检查", "标准服务"):
        revision = _patch_requirement(client, headers, project_id, revision, rows[name]["id"], {"status": "confirmed"})
    calls = []

    def writer(title, row):
        calls.append(title)
        return stand_in(title, row)

    token = bind_section_writer(writer)
    try:
        generated = client.post(
            f"/api/v1/projects/{project_id}/generate",
            headers={**headers, "If-Match": str(revision), "Idempotency-Key": str(uuid4())},
            json={},
        )
        assert generated.status_code == 200, generated.text
        assert calls == ["健康检查", "标准服务"]
        workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
        chapter = next(item for item in workspace["chapters"] if item["id"] == workspace["technical_outline"]["chapter_id"])
        assert chapter["content"].index("1.1 ") < chapter["content"].index("1.2 ")
        assert "响应说明" in chapter["content"] and "交付物与记录" in chapter["content"]
        assert "待补" in chapter["content"]
        health = chapter["content"].split("1.2.1 健康检查", 1)[1].split("1.2.2 故障处理", 1)[0]
        calls.clear()

        def rewrite(title, row):
            calls.append(title)
            if title == "健康检查":
                raise RuntimeError("这一节失败")
            return stand_in(title, row) + "\n本节已重写"
        reset_section_writer(token)
        token = bind_section_writer(rewrite)
        again = client.post(
            f"/api/v1/projects/{project_id}/generate",
            headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
            json={"section": "标准服务"},
        )
        assert again.status_code == 200, again.text
        assert calls == ["标准服务"]
        workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
        chapter = next(item for item in workspace["chapters"] if item["id"] == workspace["technical_outline"]["chapter_id"])
        assert "本节已重写" in chapter["content"]
        assert health in chapter["content"]
        calls.clear()

        def partial(title, _row):
            calls.append(title)
            return "响应说明\n半截"
        reset_section_writer(token)
        token = bind_section_writer(partial)
        kept = client.post(
            f"/api/v1/projects/{project_id}/generate",
            headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
            json={"section": "标准服务"},
        )
        assert kept.status_code == 200, kept.text
        workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
        chapter = next(item for item in workspace["chapters"] if item["id"] == workspace["technical_outline"]["chapter_id"])
        assert "本节已重写" in chapter["content"] and "半截" not in chapter["content"]
    finally:
        reset_section_writer(token)
    assert workspace["technical_deviation_note"] == "这份招标文件没有提供偏离表格式。"
    exported = client.post(
        f"/api/v1/projects/{project_id}/exports",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={"check_id": "technical-internal", "kind": "internal", "volume": "technical"},
    )
    assert exported.status_code == 200, exported.text
    assert "deviation_download_url" not in exported.json()["export"]
    downloaded = client.get(exported.json()["export"]["volumes"][0]["download_url"], headers=headers)
    assert downloaded.status_code == 200, downloaded.text
    xml = _document_xml(downloaded.content)
    assert "Heading1" in xml and "Heading2" in xml
    assert "响应说明" in xml and "待补" in xml
    assert "技术偏离表" not in xml
    missing = client.get(exported.json()["export"]["volumes"][0]["download_url"].rsplit("/", 1)[0] + "/deviation", headers=headers)
    assert missing.status_code == 404


def test_deviation_table_copies_the_tender_sample(client):
    from icg.domain.technical_volume import bind_section_writer, find_samples, reset_section_writer, stand_in, table_rows
    tender = "\n".join([
        "服务方案中应包含数据库的健康检查、故障处理、★废标响应时限、培训等。",
        "技术偏离表",
        "序号|招标文件条目|投标响应|偏离|说明|页码",
        "逐条填写",
        "商务偏离表",
        "序号|报价|偏离",
        "附件",
        "技术偏离表",
        "序号|招标文件条目|投标响应|偏离|说明|页码",
        "只列出偏离项",
    ])
    headers = login(client)
    project_id, workspace = _parse_clause(client, headers, tender)
    assert workspace["technical_deviation_note"] == ""
    samples = find_samples({"files": {"f": {"file_role": "tender", "pages": [tender]}}})
    assert [item["attachment"] for item in samples] == [False, True]
    assert [item["mode"] for item in samples] == ["all", "deviations"]
    workspace = _confirm_plan(client, headers, project_id)
    rows = {row["text"]: row for row in workspace["requirements"] if row.get("technical_clause")}
    revision = _patch_requirement(client, headers, project_id, workspace["revision"], rows["健康检查"]["id"], {
        "response_type": "exceed", "deviation_reason": "巡检频次高于招标要求", "response": "每30分钟巡检一次", "status": "confirmed",
    })
    revision = _patch_requirement(client, headers, project_id, revision, rows["故障处理"]["id"], {"status": "confirmed"})
    revision = _patch_requirement(client, headers, project_id, revision, rows["★废标响应时限"]["id"], {"status": "confirmed"})
    filled = {
        "requirements": {
            row["id"]: row for row in client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()["requirements"]
            if row.get("technical_clause")
        },
        "technical_outline": {"headings": workspace["technical_outline"]["headings"]},
    }
    # 确认后重新取目录，标题编号以确认后的工作区为准
    current = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    filled["technical_outline"] = current["technical_outline"]
    filled["requirements"] = {row["id"]: row for row in current["requirements"] if row.get("technical_clause")}
    inline_rows = table_rows(samples[0], filled)
    titles = [row[1] for row in inline_rows]
    assert "健康检查" in titles and "故障处理" in titles and "★废标响应时限" in titles and "培训" not in titles
    assert all(row[-1] == "" for row in inline_rows)
    fault = next(row for row in inline_rows if row[1] == "故障处理")
    assert fault[3] == "无偏离" and fault[4] == ""
    health = next(row for row in inline_rows if row[1] == "健康检查")
    assert health[2] == "每30分钟巡检一次" and health[3] == "正偏离" and "高于" in health[4]
    deviation_titles = [row[1] for row in table_rows(samples[1], filled)]
    assert "健康检查" in deviation_titles and "★废标响应时限" in deviation_titles and "故障处理" not in deviation_titles
    token = bind_section_writer(lambda title, row: stand_in(title, row))
    try:
        generated = client.post(
            f"/api/v1/projects/{project_id}/generate",
            headers={**headers, "If-Match": str(current["revision"]), "Idempotency-Key": str(uuid4())},
            json={},
        )
        assert generated.status_code == 200, generated.text
    finally:
        reset_section_writer(token)
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    chapter = next(item for item in workspace["chapters"] if item["id"] == workspace["technical_outline"]["chapter_id"])
    assert "技术偏离表" not in chapter["content"]
    assert "每30分钟巡检一次" in chapter["content"]
    exported = client.post(
        f"/api/v1/projects/{project_id}/exports",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={"check_id": "technical-internal", "kind": "internal", "volume": "technical"},
    )
    assert exported.status_code == 200, exported.text
    body = exported.json()["export"]
    main = client.get(body["volumes"][0]["download_url"], headers=headers)
    extra = client.get(body["deviation_download_url"], headers=headers)
    assert main.status_code == 200 and extra.status_code == 200
    main_xml = _document_xml(main.content)
    extra_xml = _document_xml(extra.content)
    assert "每30分钟巡检一次" in main_xml and "故障处理" in main_xml and "商务偏离表" not in main_xml
    assert "每30分钟巡检一次" in extra_xml and "故障处理" not in extra_xml
    revision = _patch_requirement(client, headers, project_id, client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()["revision"], rows["健康检查"]["id"], {
        "response": "每15分钟巡检一次", "status": "confirmed",
    })
    changed = client.post(
        f"/api/v1/projects/{project_id}/exports",
        headers={**headers, "If-Match": str(revision), "Idempotency-Key": str(uuid4())},
        json={"check_id": "technical-internal", "kind": "internal", "volume": "technical"},
    )
    assert changed.status_code == 200, changed.text
    changed_xml = _document_xml(client.get(changed.json()["export"]["volumes"][0]["download_url"], headers=headers).content)
    kept = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    kept_chapter = next(item for item in kept["chapters"] if item["id"] == kept["technical_outline"]["chapter_id"])
    assert "每15分钟巡检一次" in changed_xml
    assert "每30分钟巡检一次" in kept_chapter["content"]
    locked = client.post(f"/api/chapters/{kept_chapter['id']}/lock", headers=headers, json={})
    assert locked.status_code == 200, locked.text
    saved = client.post(
        f"/api/chapters/{kept_chapter['id']}/versions",
        headers=headers,
        json={
            "lease_token": locked.json()["lease_token"],
            "base_revision": kept_chapter["revision"],
            "content": kept_chapter["content"].replace("正偏离", "无偏离", 1),
            "input_fingerprint": kept["input_fingerprint"],
            "idempotency_key": str(uuid4()),
        },
    )
    assert saved.status_code == 200, saved.text
    reviewed = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    assert "健康检查" in reviewed["technical_needs_review"]
    reviewed_export = client.post(
        f"/api/v1/projects/{project_id}/exports",
        headers={**headers, "If-Match": str(reviewed["revision"]), "Idempotency-Key": str(uuid4())},
        json={"check_id": "technical-internal", "kind": "internal", "volume": "technical"},
    )
    assert reviewed_export.status_code == 200, reviewed_export.text
    reviewed_xml = _document_xml(client.get(reviewed_export.json()["export"]["volumes"][0]["download_url"], headers=headers).content)
    assert "无偏离" in reviewed_xml and "正偏离" in reviewed_xml


def test_extract_keeps_service_lines_and_drops_bid_procedure():
    from icg.domain.technical_clause_extract import extract_technical_clauses
    pages = ["\n".join([
        "乙方将提供每季度1次的现场服务。",
        "1.2.38 开标会记录",
        "1.2.45 操作系统环境健康检查",
        "评标委员会成员认真研究招标文件",
        "1.2.79 | 商务、技术偏离表",
        "1.2.86 | 招标代理机构 | 联系人",
        "故障分析报告",
    ])]
    texts = [item.text for item in extract_technical_clauses(pages)]
    assert "现场服务" in "".join(texts)
    assert any("健康检查" in item for item in texts)
    assert any("故障分析" in item for item in texts)
    assert not any("开标" in item or "评标" in item or "招标代理" in item for item in texts)


def test_outline_can_be_renamed_reordered_and_relevelled(client):
    headers = login(client)
    project_id, workspace = _parse_clause(client, headers, "服务方案中应包含数据库的健康检查、故障处理、培训等。")
    rows = {row["text"]: row for row in workspace["requirements"] if row.get("technical_clause")}
    chapter_id = workspace["technical_outline"]["chapter_id"]
    saved = client.post(
        f"/api/v1/projects/{project_id}/plan",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={
            "scope": "technical",
            "chapters": [{"id": chapter_id, "title": "技术服务方案", "volume": "technical", "fact_ids": [], "writing_points": ""}],
            "outline_title": "技术服务方案",
            "confirm_outline": False,
            "outline_headings": [
                {"level": 2, "title": "运行维护", "requirement_id": None},
                {"level": 3, "title": "季度巡检", "requirement_id": rows["健康检查"]["id"]},
                {"level": 2, "title": "应急处理", "requirement_id": None},
                {"level": 3, "title": "故障处理", "requirement_id": rows["故障处理"]["id"]},
                {"level": 3, "title": "培训", "requirement_id": rows["培训"]["id"]},
            ],
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["plan_confirmed"] is False
    current = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    titles = [(item["number"], item["title"]) for item in current["technical_outline"]["headings"]]
    assert titles == [("1.1", "运行维护"), ("1.1.1", "季度巡检"), ("1.2", "应急处理"), ("1.2.1", "故障处理"), ("1.2.2", "培训")]
    assert current["technical_outline"]["title"] == "技术服务方案"
    assert current["plan_confirmed"] is False


def test_merged_deviation_table_is_technical_only():
    from icg.domain.technical_volume import find_samples, table_rows
    pages = "\n".join([
        "商务、技术偏离表",
        "序号|招标文件条目|商务偏离|技术偏离|说明",
        "逐条响应",
        "商务偏离表",
        "序号|商务条款|偏离",
        "技术偏差表",
        "序号|招标文件条目|偏离|说明",
    ])
    samples = find_samples({"files": {"f": {"file_role": "tender", "pages": [pages]}}})
    assert [item["title"] for item in samples] == ["商务、技术偏离表", "技术偏差表"]
    merged = samples[0]
    workflow = {"technical_outline": {"headings": [
        {"level": 3, "number": "1.1.1", "title": "健康检查", "requirement_id": "r"},
    ]}, "requirements": {"r": {
        "id": "r", "technical_clause": True, "status": "confirmed", "response_origin": "model",
        "response": "每月巡检", "response_type": "comply", "deviation_reason": "",
    }}}
    row = table_rows(merged, workflow)[0]
    assert row[2] == ""
    assert row[3] == "无偏离"


def test_local_switch_refuses_public_endpoint_without_calling_it():
    from icg.infra.openai_model import OpenAICompatibleConfig, OpenAICompatibleModelProvider, is_public_model_url
    assert is_public_model_url("https://api.highwayapi.ai/openai") is True
    assert is_public_model_url("http://127.0.0.1:8000") is False
    assert is_public_model_url("http://10.1.2.3:8000") is False
    model = OpenAICompatibleModelProvider(OpenAICompatibleConfig(
        base_url="https://api.highwayapi.ai/openai", model="qwen", is_local=True, api_key="x",
    ))
    try:
        model.suggest("写正文", "招标条款")
    except Exception as error:
        assert "公网" in str(error)
    else:
        raise AssertionError("公网地址不应收到正文")
