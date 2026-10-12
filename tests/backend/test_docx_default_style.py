# 为什么有这个文件：用合成数据打开生成的 docx，核对默认版式是否真的写进文件。
# 它解决什么问题：避免只看导出函数的字符串，却漏掉标题、字体三属性、目录、页码和页边距。
from dataclasses import replace
from io import BytesIO
from inspect import signature
from xml.etree import ElementTree
from zipfile import ZipFile

from icg_demo import workflow as workflow_module
from icg_demo.adapters import build_docx
from icg_demo.domain import Export

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def sample(content: str | None = None) -> Export:
    body = content if content is not None else (
        "# 技术方案\n"
        "合成正文第一句，仅用于版式测试。\n"
        "## 实施步骤\n"
        "合成正文第二句。\n"
        "### 巡检安排\n"
        "合成正文第三句。\n"
    )
    return Export("export-style", "chapter-style", 1, "hash", "check-style",
                  "icg-style.docx", "合成投标文件", body)


def package(payload: bytes):
    with ZipFile(BytesIO(payload)) as archive:
        names = set(archive.namelist())
        parts = {name: ElementTree.fromstring(archive.read(name))
                 for name in names if name.endswith((".xml", ".rels"))}
    return names, parts


def style(styles, style_id: str):
    found = next((item for item in styles.iter(W + "style") if item.get(W + "styleId") == style_id), None)
    assert found is not None, style_id
    return found


def attr(node, name: str):
    assert node is not None
    return node.get(W + name)


def paragraph_style(paragraph) -> str | None:
    marker = paragraph.find(f"{W}pPr/{W}pStyle")
    return None if marker is None else marker.get(W + "val")


def paragraph_text(paragraph) -> str:
    return "".join(node.text or "" for node in paragraph.iter(W + "t"))


def rfonts(node):
    fonts = node.find(f".//{W}rFonts")
    assert fonts is not None
    return {key: fonts.get(W + key) for key in ("ascii", "hAnsi", "eastAsia")}


def generated(**kwargs):
    accepted = signature(build_docx).parameters
    options = {key: value for key, value in {"project_name": "合成项目名称", **kwargs}.items() if key in accepted}
    payload = build_docx(sample(), [["列甲", "列乙"], ["合成甲", "合成乙"]], **options)
    return package(payload)


def test_heading_styles_levels_and_multilevel_numbering():
    names, parts = generated()
    styles = parts["word/styles.xml"]
    expected = (("Heading1", "heading 1", "0"), ("Heading2", "heading 2", "1"), ("Heading3", "heading 3", "2"))
    for style_id, style_name, level in expected:
        item = style(styles, style_id)
        assert attr(item.find(f"{W}name"), "val") == style_name
        assert attr(item.find(f".//{W}outlineLvl"), "val") == level
        assert attr(item.find(f".//{W}ilvl"), "val") == level
    assert "word/numbering.xml" in names
    levels = [attr(item.find(f"{W}lvlText"), "val") for item in parts["word/numbering.xml"].iter(W + "lvl")]
    assert levels[:3] == ["%1", "%1.%2", "%1.%2.%3"]
    paragraphs = list(parts["word/document.xml"].iter(W + "p"))
    styled = {paragraph_style(item): paragraph_text(item) for item in paragraphs}
    assert styled["Heading1"] == "技术方案"
    assert styled["Heading2"] == "实施步骤"
    assert styled["Heading3"] == "巡检安排"


def test_every_font_setting_writes_ascii_hansi_and_eastasia():
    names, parts = generated()
    fonts = [node for name in names if name.endswith(".xml") for node in parts[name].iter(W + "rFonts")]
    assert fonts
    for node in fonts:
        assert node.get(W + "ascii")
        assert node.get(W + "hAnsi")
        assert node.get(W + "eastAsia")
    defaults = parts["word/styles.xml"].find(f".//{W}docDefaults//{W}rFonts")
    assert defaults.get(W + "ascii") == "仿宋_GB2312"
    assert defaults.get(W + "hAnsi") == "仿宋_GB2312"
    assert defaults.get(W + "eastAsia") == "仿宋_GB2312"


def test_cover_heading_body_and_toc_sizes_spacing_and_indent():
    _, parts = generated()
    styles = parts["word/styles.xml"]
    cover = style(styles, "CoverTitle")
    assert rfonts(cover) == {"ascii": "方正小标宋", "hAnsi": "方正小标宋", "eastAsia": "方正小标宋"}
    assert attr(cover.find(f".//{W}sz"), "val") == "44"
    assert cover.find(f".//{W}b") is not None
    assert attr(cover.find(f".//{W}jc"), "val") == "center"
    project = style(styles, "CoverProject")
    assert rfonts(project) == {"ascii": "黑体", "hAnsi": "黑体", "eastAsia": "黑体"}
    assert attr(project.find(f".//{W}sz"), "val") == "32"
    assert attr(project.find(f".//{W}jc"), "val") == "center"
    headings = {
        "Heading1": ("黑体", "32", "center", False),
        "Heading2": ("楷体_GB2312", "30", "left", True),
        "Heading3": ("仿宋_GB2312", "28", "left", True),
    }
    for style_id, (face, size, align, bold) in headings.items():
        item = style(styles, style_id)
        assert rfonts(item) == {"ascii": face, "hAnsi": face, "eastAsia": face}
        assert attr(item.find(f".//{W}sz"), "val") == size
        assert attr(item.find(f".//{W}jc"), "val") == align
        spacing = item.find(f".//{W}spacing")
        assert attr(spacing, "beforeLines") == "50"
        assert attr(spacing, "afterLines") == "50"
        assert (item.find(f".//{W}b") is not None) is bold
    body = style(styles, "BodyText")
    assert rfonts(body) == {"ascii": "仿宋_GB2312", "hAnsi": "仿宋_GB2312", "eastAsia": "仿宋_GB2312"}
    assert attr(body.find(f".//{W}sz"), "val") == "28"
    spacing = body.find(f".//{W}spacing")
    assert attr(spacing, "before") == "0"
    assert attr(spacing, "after") == "0"
    assert attr(spacing, "line") == "560"
    assert attr(spacing, "lineRule") == "exact"
    assert attr(body.find(f".//{W}ind"), "firstLineChars") == "200"
    assert attr(body.find(f".//{W}jc"), "val") == "both"
    toc = style(styles, "TOC")
    assert rfonts(toc) == {"ascii": "宋体", "hAnsi": "宋体", "eastAsia": "宋体"}
    assert attr(toc.find(f".//{W}sz"), "val") == "24"
    paragraphs = list(parts["word/document.xml"].iter(W + "p"))
    assert any(paragraph_style(item) == "CoverTitle" and paragraph_text(item) == "合成投标文件" for item in paragraphs)
    assert any(paragraph_style(item) == "CoverProject" and paragraph_text(item) == "合成项目名称" for item in paragraphs)
    assert any(paragraph_style(item) == "BodyText" and paragraph_text(item) == "合成正文第一句，仅用于版式测试。" for item in paragraphs)


def test_table_header_row_is_bold_songti():
    _, parts = generated()
    table = next(parts["word/document.xml"].iter(W + "tbl"))
    rows = list(table.findall(W + "tr"))
    header, data = rows[0], rows[1]
    assert header.find(f".//{W}tblHeader") is not None
    assert header.find(f".//{W}b") is not None
    assert data.find(f".//{W}b") is None
    assert rfonts(header) == {"ascii": "宋体", "hAnsi": "宋体", "eastAsia": "宋体"}
    assert attr(header.find(f".//{W}sz"), "val") == "21"
    assert attr(data.find(f".//{W}sz"), "val") == "21"


def test_toc_field_uses_heading_levels():
    _, parts = generated()
    instructions = [node.text or "" for node in parts["word/document.xml"].iter(W + "instrText")]
    assert any("TOC" in item and '1-3' in item for item in instructions)


def test_settings_ask_word_to_update_fields_on_open():
    _, parts = generated()
    update = parts["word/settings.xml"].find(f"{W}updateFields")
    assert attr(update, "val") == "true"


def test_cover_section_starts_the_body_on_the_next_page():
    _, parts = generated()
    sections = list(parts["word/document.xml"].iter(W + "sectPr"))
    cover, body = sections
    assert attr(cover.find(f"{W}type"), "val") == "nextPage"
    assert cover.find(f"{W}pgNumType") is None
    assert attr(body.find(f"{W}pgNumType"), "start") == "1"


def test_body_without_headings_does_not_repeat_the_cover_title():
    _, parts = package(build_docx(sample("合成正文没有标题标记。\n第二行仍在。"), project_name="合成项目名称"))
    paragraphs = list(parts["word/document.xml"].iter(W + "p"))
    headings = [paragraph_text(item) for item in paragraphs if paragraph_style(item) == "Heading1"]
    assert headings == []
    assert any(paragraph_style(item) == "CoverTitle" and paragraph_text(item) == "合成投标文件" for item in paragraphs)
    exported = [paragraph_text(item) for item in paragraphs]
    assert "合成正文没有标题标记。" in exported
    assert "第二行仍在。" in exported


def test_toc_has_non_heading_title_and_placeholder():
    _, parts = generated()
    styles = parts["word/styles.xml"]
    paragraphs = list(parts["word/document.xml"].iter(W + "p"))
    title = next(item for item in paragraphs if paragraph_text(item) == "目录")
    style_id = paragraph_style(title)
    assert style_id not in {"Heading1", "Heading2", "Heading3"}
    defined = style(styles, style_id)
    assert defined.find(f".//{W}outlineLvl") is None
    assert rfonts(title) == {"ascii": "宋体", "hAnsi": "宋体", "eastAsia": "宋体"}
    field = next(item for item in paragraphs if item.find(f".//{W}instrText") is not None
                 and "TOC" in (item.find(f".//{W}instrText").text or ""))
    assert paragraphs.index(title) < paragraphs.index(field)
    visible = [node.text or "" for node in field.iter(W + "t")]
    assert "右键更新域以生成目录" in visible


def test_heading_one_defaults_to_center_and_can_align_left():
    from icg_demo.docx_style import DEFAULT_DOCX_STYLE

    _, default = generated()
    default_heading = style(default["word/styles.xml"], "Heading1")
    assert attr(default_heading.find(f".//{W}jc"), "val") == "center"
    _, custom = package(build_docx(sample(), style=replace(DEFAULT_DOCX_STYLE, h1_align="left")))
    custom_heading = style(custom["word/styles.xml"], "Heading1")
    assert attr(custom_heading.find(f".//{W}jc"), "val") == "left"


def test_page_number_starts_on_body_and_cover_has_none():
    names, parts = generated()
    sections = list(parts["word/document.xml"].iter(W + "sectPr"))
    assert len(sections) == 2
    cover, body = sections
    assert cover.find(f"{W}pgNumType") is None
    assert attr(body.find(f"{W}pgNumType"), "start") == "1"
    assert attr(body.find(f"{W}pgSz"), "w") == "11906"
    assert attr(body.find(f"{W}pgSz"), "h") == "16838"
    targets = {}
    for item in parts["word/_rels/document.xml.rels"]:
        if item.tag == REL + "Relationship":
            targets[item.get("Id")] = item.get("Target")
    cover_footer = "word/" + targets[cover.find(f"{W}footerReference").get(R + "id")]
    body_footer = "word/" + targets[body.find(f"{W}footerReference").get(R + "id")]
    assert "PAGE" not in "".join(node.text or "" for node in parts[cover_footer].iter(W + "instrText"))
    body_instructions = [node.text or "" for node in parts[body_footer].iter(W + "instrText")]
    assert any("PAGE" in item for item in body_instructions)
    assert attr(parts[body_footer].find(f".//{W}jc"), "val") == "center"
    assert "word/header1.xml" in names
    header = parts["word/header1.xml"]
    assert rfonts(header) == {"ascii": "宋体", "hAnsi": "宋体", "eastAsia": "宋体"}
    assert attr(header.find(f".//{W}sz"), "val") == "21"
    assert attr(header.find(f".//{W}jc"), "val") == "center"
    assert "本地演示内部稿，不可正式递交" in "".join(header.itertext())


def test_a4_margins_match_the_approved_centimetres():
    _, parts = generated()
    for section in parts["word/document.xml"].iter(W + "sectPr"):
        margin = section.find(W + "pgMar")
        assert attr(margin, "top") == "1417"
        assert attr(margin, "bottom") == "1417"
        assert attr(margin, "left") == "1587"
        assert attr(margin, "right") == "1474"


def test_one_tender_can_override_the_default_style():
    from icg_demo import adapters

    assert "style" in signature(adapters.build_docx).parameters
    assert hasattr(adapters, "DEFAULT_DOCX_STYLE")
    style_override = replace(adapters.DEFAULT_DOCX_STYLE, margin_left_cm=3.0)
    _, custom = package(build_docx(sample("合成覆盖正文。"), style=style_override))
    _, default = package(build_docx(sample("合成默认正文。")))
    custom_left = attr(next(custom["word/document.xml"].iter(W + "pgMar")), "left")
    default_left = attr(next(default["word/document.xml"].iter(W + "pgMar")), "left")
    assert custom_left == "1701"
    assert default_left == "1587"


def test_volume_chapter_title_is_a_heading_and_body_text_remains():
    assert hasattr(workflow_module, "chapter_export_block")
    content = workflow_module.chapter_export_block("技术方案", "合成正文第一句。\n第二行仍在。")
    _, parts = package(build_docx(sample(content)))
    paragraphs = list(parts["word/document.xml"].iter(W + "p"))
    assert any(paragraph_style(item) == "Heading1" and paragraph_text(item) == "技术方案" for item in paragraphs)
    exported = [paragraph_text(item) for item in paragraphs]
    assert "合成正文第一句。" in exported
    assert "第二行仍在。" in exported
