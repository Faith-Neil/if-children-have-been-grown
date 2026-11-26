# 为什么有这个文件：验证 TV-M0-T22 招标文件跨页评分表保真、DOCX/HTML 合并单元格展开、重叠切块与精确页码/chunk_id 溯源锚点。
from __future__ import annotations

import json
from io import BytesIO
from zipfile import ZipFile

from icg.domain.parsing import LocalTextParser
from icg.domain.technical_clause_extract import apply_technical_extract
from icg.domain.technical_digest import build_digest
from icg.domain.technical_model_extract import build_extract_windows, extract_with_model
from icg.domain.technical_tender_index import build_local_index
from icg.domain.tender_remote import html_to_text


class RecordingModel:
    is_real_model = True
    is_local = True
    base_url = ""

    def __init__(self, replies):
        self.replies = list(replies)
        self.users = []

    def suggest(self, system, user, profile=None):
        self.users.append(user)
        reply = self.replies.pop(0)
        return reply if isinstance(reply, str) else json.dumps(reply, ensure_ascii=False)


def _docx_with_merged_scoring_table() -> bytes:
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        "<w:p><w:r><w:t>第三章 评分办法</w:t></w:r></w:p>"
        "<w:tbl>"
        "<w:tr>"
        "<w:tc><w:p><w:r><w:t>评分项</w:t></w:r></w:p></w:tc>"
        "<w:tc><w:p><w:r><w:t>分值</w:t></w:r></w:p></w:tc>"
        "<w:tc><w:p><w:r><w:t>评分细则</w:t></w:r></w:p></w:tc>"
        "</w:tr>"
        "<w:tr>"
        '<w:tc><w:tcPr><w:vMerge w:val="restart"/></w:tcPr><w:p><w:r><w:t>运维服务方案</w:t></w:r></w:p></w:tc>'
        '<w:tc><w:tcPr><w:vMerge w:val="restart"/></w:tcPr><w:p><w:r><w:t>20</w:t></w:r></w:p></w:tc>'
        "<w:tc><w:p><w:r><w:t>日常巡检计划完整得10分</w:t></w:r></w:p></w:tc>"
        "</w:tr>"
        "<w:tr>"
        "<w:tc><w:tcPr><w:vMerge/></w:tcPr><w:p/></w:tc>"
        "<w:tc><w:tcPr><w:vMerge/></w:tcPr><w:p/></w:tc>"
        "<w:tc><w:p><w:r><w:t>突发故障应急预案完整得10分</w:t></w:r></w:p></w:tc>"
        "</w:tr>"
        "</w:tbl>"
        "</w:body></w:document>"
    )
    buf = BytesIO()
    with ZipFile(buf, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        )
        archive.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/></Relationships>',
        )
        archive.writestr("word/document.xml", xml)
    return buf.getvalue()


def test_html_to_text_expands_rowspan_and_colspan_in_scoring_tables():
    html_table = (
        "<table>"
        "<tr><th>评分大项</th><th>分值</th><th>评分标准</th></tr>"
        '<tr><td rowspan="2">售后服务方案</td><td rowspan="2">15</td><td>7×24小时故障响应得8分</td></tr>'
        "<tr><td>备品备件库保障得7分</td></tr>"
        "</table>"
    )
    rendered = html_to_text(html_table)
    lines = rendered.splitlines()
    assert lines == [
        "评分大项 | 分值 | 评分标准",
        "售后服务方案 | 15 | 7×24小时故障响应得8分",
        "售后服务方案 | 15 | 备品备件库保障得7分",
    ]


def test_docx_parser_preserves_table_rows_and_vertical_merges():
    parsed = LocalTextParser().parse("招标文件.docx", _docx_with_merged_scoring_table())
    text = parsed.pages[0]
    assert "评分项 | 分值 | 评分细则" in text
    assert "运维服务方案 | 20 | 日常巡检计划完整得10分" in text
    assert "运维服务方案 | 20 | 突发故障应急预案完整得10分" in text


def test_cross_page_table_carries_header_and_splits_with_header_preserved():
    page1 = (
        "评标办法前附表\n"
        "评分因素 | 分值 | 评分细则\n"
        "架构设计 | 10 | 总体架构清晰合理得10分\n"
        "性能优化 | 10 | 数据库SQL调优方案完整得10分"
    )
    page2 = (
        "应急响应 | 15 | 重大故障15分钟响应、2小时修复得15分\n"
        "培训移交 | 5 | 提供每年2次现场培训得5分"
    )
    windows = build_extract_windows([page1, page2], limit=140, overlap=40)
    assert len(windows) >= 2
    second_blob = windows[-1][1]
    assert "评分因素 | 分值 | 评分细则" in second_blob
    assert "| --- |" in second_blob
    assert "应急响应 | 15 | 重大故障15分钟响应、2小时修复得15分" in second_blob


def test_extract_resolves_exact_page_and_chunk_id_anchor_across_multi_page_window():
    pages = [
        "第一页：采购人：星河市政务大数据局\n项目名称：核心数据库运维项目",
        "第二页：服务期自合同签订之日起3年，质保期1年。\n提供每月1次数据库深度巡检。",
        "第三页：评分项 | 分值 | 评分细则\n故障应急 | 12 | 建立三级故障分级响应机制得12分\n★投标人未承诺7×24小时响应的作废标处理。",
    ]
    reply = {
        "who": "星河市政务大数据局",
        "what": "核心数据库运维项目",
        "period": "3年",
        "warranty": "1年",
        "models": ["OceanBase-V4"],
        "requirements": [
            {"text": "每月1次数据库深度巡检", "quote": "提供每月1次数据库深度巡检。"},
        ],
        "scoring": [
            {
                "item": "故障应急",
                "score": 12,
                "criteria": "建立三级故障分级响应机制得12分",
                "points": ["三级故障分级响应机制"],
                "quote": "建立三级故障分级响应机制得12分",
            }
        ],
        "rejections": [
            {
                "text": "未承诺7×24小时响应废标",
                "quote": "★投标人未承诺7×24小时响应的作废标处理。",
                "category": "技术",
            }
        ],
    }
    model = RecordingModel([reply])
    payload = extract_with_model(pages, model)
    assert "[第 2 页]" in model.users[0] and "[第 3 页]" in model.users[0]

    workflow = {
        "files": {"file-1": {"id": "file-1", "filename": "招标.pdf", "pages": pages}},
        "requirements": {},
    }
    build_local_index(workflow)
    apply_technical_extract(workflow, "file-1", pages, set(), model_payload=payload)
    digest = build_digest(workflow)

    assert digest["tech"][0]["page"] == 2
    assert digest["tech"][0]["chunk_id"] == "file-1:2:0"
    assert digest["scoring"][0]["page"] == 3
    assert digest["scoring"][0]["chunk_id"] == "file-1:3:0"
    assert digest["rejection"][0]["page"] == 3
    assert digest["rejection"][0]["chunk_id"] == "file-1:3:0"
    assert workflow["technical_facts"]["质保期"] == "1年"
    assert workflow["technical_facts"]["目标型号"] == ["OceanBase-V4"]


def test_prefer_deepdoc_env_routes_docx_through_ragflow_when_enabled(monkeypatch):
    from fastapi.testclient import TestClient
    from fake_ragflow_v1 import FakeRagflowV1
    from icg_demo.main import create_app
    from test_reference_flow import ProjectFlow

    monkeypatch.setenv("ICG_TENDER_PREFER_DEEPDOC", "1")
    monkeypatch.setenv("ICG_TENDER_REMOTE_WAIT", "0")
    monkeypatch.setenv("ICG_KB_EMBEDDING_MODEL", "bge-m3:latest@qwen@OpenAI-API-Compatible")
    fake = FakeRagflowV1()
    app = create_app()
    kb = app.state.service.knowledge_base
    kb._client_factory = lambda state, company_id: fake.client()
    kb.background = False
    with TestClient(app) as client:
        flow = ProjectFlow(client)
        flow.upload(_docx_with_merged_scoring_table(), "评分表.docx")
        flow.write("/parse", {})
        record = flow.state()["files"][0]
        assert record["status"] == "parsed"
        assert record["parse_service"] == "ragflow-deepdoc"

