# 为什么有这个文件：验证公司 Word 模板与附件扫描件插入（PRD v1.8 §5.6.2、§5.9.1 规则 1、7、9，R14、R42；
# APP-M2-T086、T196、T059、T198）。
# 它解决什么问题：模板读出的字体字号、对齐、行距、页边距真的进了导出的 Word；只有公司管理员能换模板；
# 扫描件加密保存、同资料去重、只插指定页码、敏感附件带水印、暗标分册不插带公司标识的附件、坏页码定位到附件和页；
# 全部使用合成模板与合成扫描件，不用真实客户原件。

import glob
import os
import re
from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile

import pytest
from cryptography.fernet import Fernet

from test_reference_flow import ProjectFlow, client, login  # noqa: F401

W_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
A_NS = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'


def _font_for_tests() -> str:
    found = sorted(glob.glob("/usr/share/fonts/**/*.tt[fc]", recursive=True)) + sorted(glob.glob("C:/Windows/Fonts/sim*.tt[fc]"))
    assert found, "测试机需要至少一个 TrueType 字体用于水印"
    return found[0]


@pytest.fixture(autouse=True)
def _keys(monkeypatch):
    monkeypatch.setenv("ICG_SECRET_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("ICG_WATERMARK_FONT", _font_for_tests())


def template_docx(*, macro: bool = False, doctype: bool = False) -> bytes:
    styles = (f'<?xml version="1.0" encoding="UTF-8"?>{"<!DOCTYPE x>" if doctype else ""}<w:styles {W_NS}>'
              '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:eastAsiaTheme="minorEastAsia" w:asciiTheme="minorHAnsi"/>'
              '<w:sz w:val="21"/></w:rPr></w:rPrDefault></w:docDefaults>'
              '<w:style w:type="paragraph" w:default="1" w:styleId="a"><w:name w:val="Normal"/>'
              '<w:pPr><w:spacing w:line="480" w:lineRule="exact"/><w:ind w:firstLineChars="200"/></w:pPr>'
              '<w:rPr><w:sz w:val="24"/></w:rPr></w:style>'
              '<w:style w:type="paragraph" w:styleId="1"><w:name w:val="heading 1"/><w:basedOn w:val="a"/>'
              '<w:pPr><w:jc w:val="left"/></w:pPr><w:rPr><w:rFonts w:eastAsia="宋体" w:ascii="Arial"/><w:sz w:val="36"/></w:rPr></w:style>'
              '</w:styles>')
    theme = (f'<?xml version="1.0" encoding="UTF-8"?><a:theme {A_NS}><a:themeElements><a:fontScheme>'
             '<a:majorFont><a:latin typeface="Cambria"/><a:ea typeface=""/></a:majorFont>'
             '<a:minorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:font script="Hans" typeface="楷体"/></a:minorFont>'
             '</a:fontScheme></a:themeElements></a:theme>')
    document = (f'<?xml version="1.0" encoding="UTF-8"?><w:document {W_NS}><w:body><w:p/>'
                '<w:sectPr><w:pgMar w:top="1701" w:bottom="1417" w:left="1588" w:right="1588"/></w:sectPr></w:body></w:document>')
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types/>')
        archive.writestr("word/document.xml", document)
        archive.writestr("word/styles.xml", styles)
        archive.writestr("word/theme/theme1.xml", theme)
        if macro:
            archive.writestr("word/vbaProject.bin", b"\0")
    return buffer.getvalue()


def scan_pdf(pages: int = 3) -> bytes:
    from PIL import Image, ImageDraw
    images = []
    for number in range(pages):
        image = Image.new("RGB", (1240, 1754), "white")
        ImageDraw.Draw(image).rectangle((100, 100 + number * 200, 1100, 300 + number * 200), outline="black", width=8)
        images.append(image)
    buffer = BytesIO()
    images[0].save(buffer, "PDF", save_all=True, append_images=images[1:])
    return buffer.getvalue()


def scan_png(size=(4000, 3000)) -> bytes:
    from PIL import Image
    buffer = BytesIO()
    Image.new("RGB", size, (240, 240, 240)).save(buffer, "PNG")
    return buffer.getvalue()


TEMPLATE = template_docx()


def _put_template(client, headers, data=None, filename="公司模板.docx"):
    return client.put("/api/v1/companies/alpha/word-template", params={"filename": filename},
                      content=TEMPLATE if data is None else data,
                      headers={**headers, "Content-Type": "application/octet-stream"})


def _upload(client, headers, item_id, data, filename="营业执照.pdf"):
    return client.post(f"/api/v1/library/{item_id}/attachments/raw", params={"filename": filename}, content=data,
                       headers={**headers, "Content-Type": "application/octet-stream"})


def _parts(data: bytes) -> dict[str, bytes]:
    archive = ZipFile(BytesIO(data))
    return {name: archive.read(name) for name in archive.namelist()}


def _export(flow, client, **options):
    check = flow.write("/checks", {"volume": "all"})["check"]
    export = flow.write("/exports", {"check_id": check["id"], "kind": "internal", "volume": "all", **options})["export"]
    files = {v["volume"]: client.get(v["download_url"], headers=flow.headers).content for v in export["volumes"]}
    return export, files


def _business_item(client, flow):
    rows = flow.state()["requirements"]
    ids = [eid for row in rows if row.get("volume") == "business" for eid in row.get("evidence_ids") or []]
    assert ids, "合成项目应有挂接证据的商务条款"
    return ids[0]


def test_template_styles_fonts_alignment_spacing_and_margins_are_read():
    from icg.infra.docx_template import parse_template
    style, applied, defaults = parse_template(template_docx())
    assert (style.h1_font.east_asia, style.h1_font.ascii, style.h1_pt, style.h1_align) == ("宋体", "Arial", 18, "left")
    assert (style.body_font.east_asia, style.body_font.ascii, style.body_pt) == ("楷体", "Calibri", 12)  # 主题字体
    assert (style.body_line_pt, style.body_first_line_chars) == (24, 200)
    assert (style.margin_top_cm, style.margin_bottom_cm, style.margin_left_cm) == (3.0, 2.5, 2.8)
    assert any(line.startswith("一级标题：宋体 / Arial，18 磅，左对齐") for line in applied)
    assert "三级标题" in defaults and not any(line.startswith("页边距") for line in defaults)


@pytest.mark.parametrize("data,message", [(b"not a zip", "不是有效的 .docx"), (template_docx(macro=True), "含宏"),
                                          (template_docx(doctype=True), "不允许的 XML")])
def test_unusable_templates_are_refused_with_a_reason(data, message):
    from icg.infra.docx_template import TemplateError, parse_template
    with pytest.raises(TemplateError, match=message):
        parse_template(data)


def test_only_company_admin_replaces_the_template_and_export_uses_it(client):
    admin = login(client, "alpha-company-admin")
    assert _put_template(client, login(client, "alpha-manager")).status_code == 403
    assert _put_template(client, admin, filename="模板.doc").json()["code"] == "WORD_TEMPLATE_INVALID"
    saved = _put_template(client, admin)
    assert saved.status_code == 200, saved.text
    assert saved.json()["template"]["filename"] == "公司模板.docx"
    assert client.get("/api/v1/companies/alpha/word-template", headers=login(client, "alpha-editor")).json()["template"]["applied"]
    assert client.get("/api/v1/companies/alpha/word-template", headers=login(client, "beta-manager")).status_code == 404
    assert client.get("/api/v1/companies/alpha/word-template/file", headers=admin).content == TEMPLATE

    flow = ProjectFlow(client).ready()
    export, files = _export(flow, client)
    assert all(v["template"] == {"source": "company", "filename": "公司模板.docx", "sha256": saved.json()["template"]["sha256"]}
               for v in export["volumes"])
    parts = _parts(files["technical"])
    styles, document = parts["word/styles.xml"].decode(), parts["word/document.xml"].decode()
    heading = re.search(r'<w:style w:type="paragraph" w:styleId="Heading1">.*?</w:style>', styles).group(0)
    assert 'w:eastAsia="宋体"' in heading and '<w:sz w:val="36"/>' in heading and '<w:jc w:val="left"/>' in heading
    assert 'w:top="1701"' in document and 'w:line="480"' in styles
    assert not any(name.startswith("word/theme") for name in parts)  # 不带模板残留部件

    platform, files = _export(flow, client, template="platform")
    assert platform["volumes"][0]["template"]["source"] == "platform"
    assert 'w:top="1417"' in _parts(files["technical"])["word/document.xml"].decode()  # 平台默认 2.5cm
    assert client.delete("/api/v1/companies/alpha/word-template", headers=admin).json() == {"template": None}
    check = flow.write("/checks", {"volume": "all"})["check"]
    error = flow.write("/exports", {"check_id": check["id"], "kind": "internal", "template": "company"}, expected=409)
    assert error["code"] == "WORD_TEMPLATE_MISSING"


def test_scans_are_encrypted_deduplicated_and_page_ranges_validated(client, monkeypatch):
    flow = ProjectFlow(client).ready()
    item_id = _business_item(client, flow)
    assert _upload(client, flow.headers, item_id, b"hello").json()["code"] == "ATTACHMENT_TYPE_UNSUPPORTED"
    assert _upload(client, flow.headers, item_id, b"%PDF-1.4 broken").json()["code"] == "ATTACHMENT_UNREADABLE"
    pdf = scan_pdf()  # Pillow 生成的 PDF 带创建时间，同一份内容只生成一次
    first = _upload(client, flow.headers, item_id, pdf).json()
    attachment = first["attachment"]
    assert (attachment["kind"], attachment["page_count"], attachment["page_to"], first["duplicate"]) == ("pdf", 3, 3, False)
    assert attachment["is_sensitive"] and attachment["shows_identity"]
    assert _upload(client, flow.headers, item_id, pdf).json() == {"attachment": attachment, "duplicate": True}
    from icg.infra.blob_store import blob_dir
    from icg.domain.attachments import plain_bytes
    state = client.app.state.service.repository.read()
    record = state.service_stores["attachments"]["items"][attachment["id"]]
    stored = (blob_dir() / record["blob"][:2] / record["blob"]).read_bytes()
    assert not stored.startswith(b"%PDF") and plain_bytes(record) == pdf
    path = f"/api/v1/library/attachments/{attachment['id']}"
    bad = client.patch(path, json={"page_from": 2, "page_to": 4}, headers=flow.headers)
    assert bad.status_code == 422 and bad.json()["code"] == "ATTACHMENT_PAGE_RANGE"
    stale = client.patch(path, json={"page_from": 2}, headers={**flow.headers, "If-Match": "9"})
    assert stale.status_code == 409
    patched = client.patch(path, json={"page_from": 2, "feature_tags": ["Java", "Java", " 监控 "]}, headers=flow.headers).json()
    assert (patched["attachment"]["page_from"], patched["attachment"]["feature_tags"]) == (2, ["Java", "监控"])
    assert client.get(path + "/file", headers=login(client, "beta-manager")).status_code == 404
    download = client.get(path + "/file", headers=flow.headers)
    assert download.content == pdf and download.headers["content-type"] == "application/pdf"
    monkeypatch.delenv("ICG_SECRET_KEY")
    assert _upload(client, flow.headers, item_id, scan_png()).status_code == 503


def test_export_inserts_only_the_chosen_pages_with_watermark_after_the_mapped_chapter(client):
    flow = ProjectFlow(client).ready()
    item_id = _business_item(client, flow)
    pdf = _upload(client, flow.headers, item_id, scan_pdf()).json()["attachment"]
    client.patch(f"/api/v1/library/attachments/{pdf['id']}", json={"page_from": 2, "page_to": 3}, headers=flow.headers)
    png = _upload(client, flow.headers, item_id, scan_png(), "授权书.png").json()["attachment"]
    client.patch(f"/api/v1/library/attachments/{png['id']}", json={"is_sensitive": False}, headers=flow.headers)
    export, files = _export(flow, client, attachment_watermark="FOR SYNTHETIC BID ONLY")
    business = next(v for v in export["volumes"] if v["volume"] == "business")
    assert [(a["page_from"], a["page_to"], a["watermarked"]) for a in business["attachments"]] == [(2, 3, True), (1, 1, False)]
    parts = _parts(files["business"])
    media = sorted(name for name in parts if name.startswith("word/media/"))
    assert media == ["word/media/attachment1.jpeg", "word/media/attachment2.jpeg", "word/media/attachment3.jpeg"]
    document = parts["word/document.xml"].decode()
    assert document.count("<w:drawing>") == 3 and "（第 2～3 页）" in document
    assert 'Target="media/attachment1.jpeg"' in parts["word/_rels/document.xml.rels"].decode()
    assert b'Extension="jpeg"' in parts["[Content_Types].xml"]
    from PIL import Image
    big = Image.open(BytesIO(parts["word/media/attachment3.jpeg"]))
    assert max(big.size) <= 2339 and len(parts["word/media/attachment3.jpeg"]) < len(scan_png())  # 过大图片已压缩
    technical = _parts(files["technical"])
    assert not any(name.startswith("word/media/") for name in technical)  # 技术册条款没有挂这份资料

    _, plain = _export(flow, client, insert_attachments=False)
    assert not any(name.startswith("word/media/") for name in _parts(plain["business"]))


def test_watermark_is_burned_into_sensitive_pages_and_missing_font_is_reported(monkeypatch):
    from PIL import Image
    from icg.infra.docx_media import AttachmentRenderError, render_pages
    plain = render_pages(scan_pdf(1), 1, 1, None, "营业执照")[0]
    # 测试机的字体不一定含中文，水印像素用西文文字验证；中文字形缺失必须报错而不是静默无水印
    marked = render_pages(scan_pdf(1), 1, 1, "ONLY FOR SYNTHETIC BID", "营业执照")[0]
    assert plain.data != marked.data
    pixels = Image.open(BytesIO(marked.data)).convert("RGB")
    raw = pixels.tobytes()
    assert any(raw[i] > raw[i + 1] + 40 for i in range(0, len(raw), 3))  # 红色水印
    with pytest.raises(AttachmentRenderError, match="只有 1 页，指定的第 1～2 页超出范围"):
        render_pages(scan_pdf(1), 1, 2, None, "营业执照")
    from PIL import ImageFont
    font = ImageFont.truetype(os.environ["ICG_WATERMARK_FONT"], 40)
    if font.getmask("仅用于").getbbox() is None:
        with pytest.raises(AttachmentRenderError, match="不含水印文字的字形"):
            render_pages(scan_pdf(1), 1, 1, "仅用于合成项目投标", "营业执照")
    monkeypatch.setenv("ICG_WATERMARK_FONT", "/nonexistent/font.ttf")
    with pytest.raises(AttachmentRenderError, match="营业执照”第 1 页：找不到可写中文水印的字体"):
        render_pages(scan_pdf(1), 1, 1, "仅用于合成项目投标", "营业执照")


def test_blind_volume_skips_attachments_that_show_the_company():
    from types import SimpleNamespace
    from icg.domain.attachments import export_plan
    from icg.domain.domain import DemoState
    state = DemoState()
    state.library["ev"] = {"id": "ev", "company_id": "alpha", "name": "营业执照"}
    state.service_stores["attachments"] = {"items": {
        "a1": {"id": "a1", "company_id": "alpha", "library_id": "ev", "filename": "执照.pdf", "blob": "x", "sha256": "s",
               "page_from": 1, "page_to": 1, "page_count": 1, "is_sensitive": True, "shows_identity": True, "uploaded_at": "1"},
        "a2": {"id": "a2", "company_id": "alpha", "library_id": "ev", "filename": "截图.png", "blob": "y", "sha256": "t",
               "page_from": 1, "page_to": 1, "page_count": 1, "is_sensitive": False, "shows_identity": False, "uploaded_at": "2"}}}
    chapter = SimpleNamespace(id="c1", title="技术方案", volume="technical")
    state.chapters["c1"] = chapter
    workflow = {"requirements": {"r": {"id": "r", "status": "confirmed", "chapter_id": "c1", "evidence_ids": ["ev"]}}}
    project = SimpleNamespace(company_id="alpha")
    plan, skipped = export_plan(state, project, workflow, "technical", [chapter], {"c1": 4}, default_volume="business",
                                blind=True, watermark="仅用于合成项目投标")
    assert [p["attachment_id"] for p in plan] == ["a2"] and plan[0]["after_line"] == 4 and plan[0]["watermark"] is None
    assert skipped == [{"attachment_id": "a1", "name": "营业执照", "filename": "执照.pdf", "reason": "暗标分册不插入带公司名称或标志的附件"}]
    plan, _ = export_plan(state, project, workflow, "business", [], {}, default_volume="business", blind=False, watermark="w")
    assert plan == []  # 条款对应章节在另一册


def test_template_comments_revisions_and_custom_properties_never_reach_the_export(client):
    """§5.9.1 规则 10、R25（APP-M2-T199）：模板带批注、修订、隐藏文字、自定义属性和作者时，导出文件一样都不带。"""
    buffer = BytesIO()
    with ZipFile(BytesIO(TEMPLATE)) as source, ZipFile(buffer, "w") as target:
        for name in source.namelist():
            data = source.read(name)
            if name == "word/document.xml":
                data = data.replace(b"<w:p/>", b'<w:p><w:ins w:id="1" w:author="Template Author"><w:r><w:t>INSERTED</w:t></w:r></w:ins>'
                                    b'<w:r><w:rPr><w:vanish/></w:rPr><w:t>HIDDEN</w:t></w:r></w:p>')
            target.writestr(name, data)
        target.writestr("word/comments.xml", f'<w:comments {W_NS}><w:comment w:id="0" w:author="Template Author"/></w:comments>')
        target.writestr("docProps/custom.xml", '<Properties><property name="ClientSecret">X</property></Properties>')
        target.writestr("docProps/core.xml", '<cp:coreProperties xmlns:cp="c" xmlns:dc="d"><dc:creator>Template Author</dc:creator></cp:coreProperties>')
    admin = login(client, "alpha-company-admin")
    assert _put_template(client, admin, buffer.getvalue(), "带残留模板.docx").status_code == 200
    flow = ProjectFlow(client).ready()
    _, files = _export(flow, client)
    for data in files.values():
        parts = _parts(data)
        assert not {"word/comments.xml", "docProps/custom.xml", "docProps/app.xml"} & set(parts)
        joined = b"".join(parts[name] for name in parts if name.endswith((".xml", ".rels")))
        for residue in (b"Template Author", b"INSERTED", b"HIDDEN", b"ClientSecret", b"<w:ins ", b"<w:del ", b"<w:vanish"):
            assert residue not in joined, residue
