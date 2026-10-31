# 为什么有这个文件：验证分册封面、目录与页码（PRD v1.8 §5.9.1 规则 2、3、10，验收①②⑤⑦；APP-M2-T197）。
# 它解决什么问题：每册独立封面（投标文件、项目名称、招标编号、分册、投标人、日期），目录单独一节且预先列出标题，
# 正文页码每册从 1 起；递交版页眉写项目名称和投标人、内部稿写“内部评审稿”；文档属性不含系统账号或编写人；
# 评审索引表页码列为“合标后由商务填写”；直接检查导出的 Word 文件。

import re
from io import BytesIO
from zipfile import ZipFile

from test_merge_checklist import _submission
from test_reference_flow import ProjectFlow, client  # noqa: F401

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _parts(data: bytes) -> dict[str, str]:
    archive = ZipFile(BytesIO(data))
    return {name: archive.read(name).decode("utf-8") for name in archive.namelist() if name.endswith((".xml", ".rels"))}


def _texts(xml: str) -> list[str]:
    return [t for t in re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", xml)]


def _download(client, flow, export):
    return {v["volume"]: client.get(v["download_url"], headers=flow.headers).content for v in export["volumes"]}


def test_submission_volumes_have_cover_toc_pages_and_bidder_header(client):
    flow, _, export = _submission(client)
    project = flow.state()["project"]
    for volume, data in _download(client, flow, export).items():
        parts = _parts(data)
        document = parts["word/document.xml"]
        texts = _texts(document)
        name = "技术分册" if volume == "technical" else "商务分册"
        cover = texts[:texts.index("目录")] if "目录" in texts else texts[:8]
        assert cover[0] == "投标文件" and f"分册：{name}" in cover and "投标人：Alpha 科技（盖章）" in cover
        assert any(re.fullmatch(r"\d{4}年\d{1,2}月\d{1,2}日", t) for t in cover)
        if project.get("tender_number"):
            assert f"招标编号：{project['tender_number']}" in cover
        assert "内部评审稿 · 不可作为正式递交文件" not in cover
        formats = re.findall(r'<w:pgNumType w:fmt="(\w+)" w:start="1"/>', document)
        assert formats[-1] == "decimal"  # 正文每册从 1 起
        header = parts["word/header1.xml"]
        assert "Alpha 科技" in "".join(_texts(header)) and "内部" not in "".join(_texts(header))
        assert _texts(parts["word/header2.xml"]) == []  # 封面不带页眉
        core = parts["docProps/core.xml"]
        assert "<dc:creator>Alpha 科技</dc:creator>" in core
        assert not any(account in core for account in ("alpha-manager", "alpha-editor", "admin", "甲公司"))


def test_internal_drafts_say_so_in_header_and_leave_author_empty(client):
    flow = ProjectFlow(client).ready()
    check = flow.write("/checks", {"volume": "all"})["check"]
    export = flow.write("/exports", {"check_id": check["id"], "kind": "internal", "volume": "all"})["export"]
    for data in _download(client, flow, export).values():
        parts = _parts(data)
        assert "内部评审稿 · 不可作为正式递交文件" in "".join(_texts(parts["word/header1.xml"]))
        assert "内部评审稿 · 不可作为正式递交文件" in _texts(parts["word/document.xml"])
        assert "<dc:creator></dc:creator>" in parts["docProps/core.xml"]


def test_toc_lists_each_heading_with_a_bookmark_and_page_field():
    from icg.domain.domain import Export
    from icg.infra.docx_style import DocxMeta, build_docx
    data = build_docx(Export("e", "", 1, "", "", "f.docx", "合成项目 — 技术分册", "# 第一章 总体方案\n正文\n## 1.1 架构\n内容\n# 第二章 运维\n内容"),
                      project_name="合成项目", meta=DocxMeta(kind="submission", volume_name="技术分册", bidder="Alpha 科技"))
    document = _parts(data)["word/document.xml"]
    bookmarks = re.findall(r'<w:bookmarkStart w:id="\d+" w:name="(_Toc\d+)"/>', document)
    refs = re.findall(r"PAGEREF (_Toc\d+) ", document)
    anchors = re.findall(r'<w:hyperlink w:anchor="(_Toc\d+)"', document)
    assert len(bookmarks) == 3 and refs == bookmarks == anchors
    assert document.index("目录") < document.index("第一章 总体方案")
    assert 'w:fmt="lowerRoman"' in document and "右键更新域" not in document
    assert "<w:updateFields w:val=\"true\"/>" in _parts(data)["word/settings.xml"]


def test_dark_bid_volume_has_no_bidder_on_cover_header_or_properties():
    from icg.domain.domain import Export
    from icg.infra.docx_style import DocxMeta, build_docx
    parts = _parts(build_docx(Export("e", "", 1, "", "", "f.docx", "t", "# 一\n正文"), project_name="合成项目",
                              meta=DocxMeta(kind="submission", volume_name="技术分册", bidder="Alpha 科技", dark_bid=True)))
    assert not any("Alpha 科技" in part for part in parts.values())


def test_review_index_page_column_is_left_for_business_assembly():
    from icg.domain import system_chapters
    source = open(system_chapters.__file__, encoding="utf-8").read()
    assert '"合标后由商务填写"' in source and '"页码"' in source
