# 为什么有这个文件：验证本地取不出文字的招标文件经 RAGFlow DeepDOC 解析后继续条款与事实抽取（扫描件、.doc、.xls、图片）。
# 它解决什么问题：解析不能假装成功——未连 RAGFlow 时如实报错；RAGFlow 慢时文件标“解析中”，再次解析接着取结果、不重复上传；
# 页码按版面位置还原，条款原句仍逐字可回查；完成后删除 RAGFlow 里的临时文档。

import pytest
from fastapi.testclient import TestClient

from fake_ragflow_v1 import FakeRagflowV1
from icg.domain.tender_remote import html_to_text, pages_from_chunks
from icg_demo.main import create_app
from test_reference_flow import ProjectFlow, pdf_bytes

TENDER_DOC = ("第一章 招标公告\n项目名称：合成扫描件项目\n项目编号：SCAN-001\n\n一、投标人资格要求\n"
              "1. 具有独立承担民事责任的能力，提供营业执照。\n\f"
              "第二章 评标办法\n一、评分标准\n1. 技术方案（30分）：方案完整的得30分。\n\n"
              "2. 投标文件未按要求盖章的，视为无效投标。")


@pytest.fixture()
def fake(monkeypatch):
    monkeypatch.setenv("ICG_TENDER_REMOTE_WAIT", "0")
    return FakeRagflowV1()


@pytest.fixture()
def wired(fake):
    app = create_app()
    kb = app.state.service.knowledge_base
    kb._client_factory = lambda state, company_id: fake.client()
    kb.background = False
    with TestClient(app) as test_client:
        yield test_client


def test_pages_rebuilt_from_positions_and_tables_flattened():
    chunks = [{"content": "第二页下", "positions": [[2, 0, 0, 500, 520]]},
              {"content": "第一页", "positions": [[1, 0, 0, 10, 20]]},
              {"content": "第二页上", "positions": [[2, 0, 0, 100, 120]]},
              {"content": "<table><tr><td>评分因素</td><td>分值</td></tr><tr><td>技术方案</td><td>30</td></tr></table>",
               "positions": [[3, 0, 0, 1, 2]]}]
    pages, positioned = pages_from_chunks(chunks)
    assert positioned and pages[0] == "第一页" and pages[1] == "第二页上\n第二页下"
    assert pages[2] == "评分因素 | 分值\n技术方案 | 30"
    assert html_to_text("A&amp;B<br>C") == "A&B\nC"
    unplaced, ok = pages_from_chunks([{"content": "甲方条款"}, {"content": "乙方条款"}])
    assert not ok and unplaced == ["甲方条款\n乙方条款"]
    # 扫描件水印与页边残字去掉，正文短行保留
    noisy, _ = pages_from_chunks([{"content": "全波\nTV\n试用水\n第一页正文", "positions": [[1, 0, 0, 1, 2]]}])
    assert noisy == ["第一页正文"]


def test_doc_file_is_parsed_by_ragflow_and_requirements_keep_page_numbers(wired, fake):
    flow = ProjectFlow(wired)
    flow.upload(TENDER_DOC.encode("utf-8"), "合成招标.doc")
    flow.write("/parse", {})
    state = flow.state()
    record = state["files"][0]
    assert record["status"] == "parsed" and record["pagination"] == "ragflow_deepdoc_positions"
    assert record["page_count"] == 2 and "DeepDOC" in record["warnings"][0]
    texts = {r["text"]: r for r in state["requirements"]}
    star = next(r for t, r in texts.items() if "视为无效投标" in t)
    assert star["source"]["page"] == 2 and star["category"] == "mandatory"
    assert any(r["source"]["page"] == 1 and "营业执照" in t for t, r in texts.items())
    assert ("招标编号", "SCAN-001") in {(f["key"], f["value"]) for f in state["facts"]}
    preview = wired.get(f"{flow.path}/files/{record['id']}/preview", headers=flow.headers).json()
    for row in state["requirements"]:
        assert row["source"]["quote"] in preview["pages"][row["source"]["page"] - 1]["text"]
    # 解析完成后删除 RAGFlow 里的临时文档
    dataset = next(d for d in fake.datasets.values() if d["name"].endswith("::icg-tender"))
    assert fake.docs_in(dataset["id"]) == []


def test_slow_parse_marks_file_pending_and_next_parse_resumes_without_reupload(monkeypatch):
    monkeypatch.setenv("ICG_TENDER_REMOTE_WAIT", "0")
    fake = FakeRagflowV1(async_parse=True)
    app = create_app()
    kb = app.state.service.knowledge_base
    kb._client_factory = lambda state, company_id: fake.client()
    kb.background = False
    with TestClient(app) as client:
        flow = ProjectFlow(client)
        flow.upload(TENDER_DOC.encode("utf-8"), "合成招标.xls")
        flow.write("/parse", {})
        record = flow.state()["files"][0]
        assert record["status"] == "parsing_remote" and "RAGFlow 正在解析" in record["warnings"][0]
        uploads = sum(1 for c in fake.calls if c[0] == "POST" and c[1].endswith("/documents"))
        fake.finish_parsing()
        flow.write("/parse", {})
        record = flow.state()["files"][0]
        assert record["status"] == "parsed" and flow.state()["requirements"]
        assert sum(1 for c in fake.calls if c[0] == "POST" and c[1].endswith("/documents")) == uploads


def test_scanned_pdf_without_ragflow_fails_honestly(client_without_kb):
    flow = ProjectFlow(client_without_kb)
    flow.upload(pdf_bytes(False), "扫描件.pdf")
    error = flow.write("/parse", {}, expected=422)
    assert error["code"] == "OCR_REQUIRED" and "RAGFlow" in error["message"]
    assert flow.state()["files"][0]["status"] == "failed"


def test_ragflow_parse_failure_is_reported(wired, fake):
    flow = ProjectFlow(wired)
    flow.upload("内容 [[fake-parse-fail]]".encode("utf-8"), "坏扫描.doc")
    error = flow.write("/parse", {}, expected=422)
    assert error["code"] == "OCR_REQUIRED" and "RAGFlow 解析失败" in error["message"]


@pytest.fixture()
def client_without_kb():
    with TestClient(create_app()) as client:
        yield client


# —— 真实扫描件：贵阳银行通用 OCR 技术中台招标文件（35 页，无文字层）——
# 分块取自用户自建 RAGFlow v1.0.0-rc2 内置 DeepDOC 实际解析结果（tests/fixtures/tenders/guiyang-2025-scan.chunks.json）。

def test_real_scanned_tender_from_deepdoc_chunks():
    import json
    from pathlib import Path
    from icg.domain.tender_extraction import extract_facts, extract_requirements

    raw = json.loads((Path(__file__).parents[1] / "fixtures" / "tenders" / "guiyang-2025-scan.chunks.json").read_text(encoding="utf-8"))
    pages, positioned = pages_from_chunks(raw["chunks"])
    assert positioned and len(pages) == 35
    rows, summary = extract_requirements(pages)
    kinds = summary["by_section_kind"]
    # 扫描件丢了“采购需求”章标题：规格条目按内容归为技术，评审程序不进矩阵
    assert kinds["technical"] >= 60 and kinds.get("scoring", 0) <= 25 and summary["skipped_items"]["procedure"] >= 30
    scores = {r.score for r in rows if r.score}
    assert {15.0, 8.0, 16.0, 5.0} <= scores
    assert not any(r.text.endswith(("场景配置", "数据标注", "评审标准")) for r in rows)
    assert any("否决其投标" in r.text and r.mandatory for r in rows)
    assert any("国密算法" in r.text and r.section_kind == "technical" for r in rows)
    for row in rows:
        assert row.quote in pages[row.page - 1], row
    facts = {(f.key, f.value) for f in extract_facts(pages)}
    assert ("招标编号", "GBF2025-1161") in facts and ("采购人", "贵阳银行股份有限公司") in facts
