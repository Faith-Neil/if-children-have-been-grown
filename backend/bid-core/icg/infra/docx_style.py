# 为什么有这个文件：把已批准的 Word 默认版式写成真实 docx，并允许单个投标覆盖。
# 它解决什么问题：导出不再只有普通段落，标题、目录、页码和三种字体属性都能被打开文件核对。

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from icg.domain.domain import Export


@dataclass(frozen=True)
class FontFace:
    east_asia: str
    ascii: str
    h_ansi: str


def face(east_asia: str, ascii: str | None = None, h_ansi: str | None = None) -> FontFace:
    return FontFace(east_asia, east_asia if ascii is None else ascii, east_asia if h_ansi is None else h_ansi)


@dataclass(frozen=True)
class DocxStyle:
    margin_top_cm: float = 2.5
    margin_bottom_cm: float = 2.5
    margin_left_cm: float = 2.8
    margin_right_cm: float = 2.6
    cover_title_font: FontFace = field(default_factory=lambda: face("方正小标宋"))
    cover_title_pt: float = 22
    cover_project_font: FontFace = field(default_factory=lambda: face("黑体"))
    cover_project_pt: float = 16
    h1_font: FontFace = field(default_factory=lambda: face("黑体"))
    h1_pt: float = 16
    h1_align: str = "center"
    h2_font: FontFace = field(default_factory=lambda: face("楷体_GB2312"))
    h2_pt: float = 15
    h3_font: FontFace = field(default_factory=lambda: face("仿宋_GB2312"))
    h3_pt: float = 14
    body_font: FontFace = field(default_factory=lambda: face("仿宋_GB2312"))
    body_pt: float = 14
    body_line_pt: float = 28
    body_first_line_chars: int = 200
    body_first_line_twips: int = 560
    table_font: FontFace = field(default_factory=lambda: face("宋体"))
    table_pt: float = 10.5
    header_font: FontFace = field(default_factory=lambda: face("宋体"))
    header_pt: float = 10.5
    toc_font: FontFace = field(default_factory=lambda: face("宋体"))
    toc_pt: float = 12
    heading_space_lines: int = 50
    header_text: str = "本地演示内部稿，不可正式递交"


DEFAULT_DOCX_STYLE = DocxStyle()

_HEADINGS = (("### ", "Heading3"), ("## ", "Heading2"), ("# ", "Heading1"))


def _attr(value: str) -> str:
    return escape(value, {'"': "&quot;"})


def _half(pt: float) -> str:
    return str(int(round(pt * 2)))


def _twips(cm: float) -> str:
    return str(int(round(cm * 1440 / 2.54)))


def _fonts(item: FontFace) -> str:
    return (f'<w:rFonts w:ascii="{_attr(item.ascii)}" w:hAnsi="{_attr(item.h_ansi)}" '
            f'w:eastAsia="{_attr(item.east_asia)}"/>')


def _size(pt: float) -> str:
    half = _half(pt)
    return f'<w:sz w:val="{half}"/><w:szCs w:val="{half}"/>'


def _run(text: str, item: FontFace, pt: float, *, bold: bool = False) -> str:
    weight = "<w:b/>" if bold else ""
    return (f'<w:r><w:rPr>{_fonts(item)}{_size(pt)}{weight}</w:rPr>'
            f'<w:t xml:space="preserve">{escape(text)}</w:t></w:r>')


def _paragraph(style_id: str, text: str, item: FontFace, pt: float, *, bold: bool = False) -> str:
    return f'<w:p><w:pPr><w:pStyle w:val="{style_id}"/></w:pPr>{_run(text, item, pt, bold=bold)}</w:p>'


def _classify(line: str) -> tuple[str, str, bool]:
    for marker, style_id in _HEADINGS:
        if line.startswith(marker):
            return style_id, line[len(marker):], style_id != "Heading1"
    return "BodyText", line, False


def _blocks(record: Export) -> list[tuple[str, str, bool]]:
    lines = [] if record.content == "" else record.content.splitlines()
    return [_classify(line) for line in lines]


def _style_xml(style: DocxStyle) -> str:
    space = style.heading_space_lines

    def paragraph_style(style_id: str, name: str, paragraph: str, run: str) -> str:
        return (f'<w:style w:type="paragraph" w:styleId="{style_id}"><w:name w:val="{name}"/>'
                f'<w:basedOn w:val="Normal"/>{paragraph}{run}</w:style>')

    def heading(style_id: str, name: str, level: int, item: FontFace, pt: float, align: str, bold: bool) -> str:
        weight = "<w:b/>" if bold else ""
        paragraph = (f'<w:pPr><w:numPr><w:ilvl w:val="{level}"/><w:numId w:val="1"/></w:numPr>'
                     f'<w:spacing w:beforeLines="{space}" w:afterLines="{space}"/>'
                     f'<w:jc w:val="{align}"/><w:outlineLvl w:val="{level}"/></w:pPr>')
        run = f'<w:rPr>{_fonts(item)}{_size(pt)}{weight}</w:rPr>'
        return paragraph_style(style_id, name, paragraph, run)

    body_paragraph = (f'<w:pPr><w:spacing w:before="0" w:after="0" w:line="{int(round(style.body_line_pt * 20))}" '
                      f'w:lineRule="exact"/><w:ind w:firstLineChars="{style.body_first_line_chars}" '
                      f'w:firstLine="{style.body_first_line_twips}"/>'
                      '<w:jc w:val="both"/></w:pPr>')
    cover = paragraph_style(
        "CoverTitle", "Cover Title",
        '<w:pPr><w:jc w:val="center"/></w:pPr>',
        f'<w:rPr>{_fonts(style.cover_title_font)}{_size(style.cover_title_pt)}<w:b/></w:rPr>')
    project = paragraph_style(
        "CoverProject", "Cover Project",
        '<w:pPr><w:jc w:val="center"/></w:pPr>',
        f'<w:rPr>{_fonts(style.cover_project_font)}{_size(style.cover_project_pt)}</w:rPr>')
    body = paragraph_style("BodyText", "Body Text", body_paragraph,
                           f'<w:rPr>{_fonts(style.body_font)}{_size(style.body_pt)}</w:rPr>')
    toc_title = paragraph_style(
        "TocTitle", "TOC Title",
        '<w:pPr><w:jc w:val="center"/></w:pPr>',
        f'<w:rPr>{_fonts(style.toc_font)}{_size(style.toc_pt)}</w:rPr>')
    toc = paragraph_style("TOC", "toc 1", "<w:pPr/>",
                          f'<w:rPr>{_fonts(style.toc_font)}{_size(style.toc_pt)}</w:rPr>')
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr>{_fonts(style.body_font)}{_size(style.body_pt)}</w:rPr></w:rPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr>{_fonts(style.body_font)}{_size(style.body_pt)}</w:rPr></w:style>
{cover}{project}
{heading("Heading1", "heading 1", 0, style.h1_font, style.h1_pt, style.h1_align, False)}
{heading("Heading2", "heading 2", 1, style.h2_font, style.h2_pt, "left", True)}
{heading("Heading3", "heading 3", 2, style.h3_font, style.h3_pt, "left", True)}
{body}{toc_title}{toc}
</w:styles>'''


def _numbering_xml() -> str:
    levels = []
    for index, text in enumerate(("%1", "%1.%2", "%1.%2.%3")):
        levels.append(f'<w:lvl w:ilvl="{index}"><w:start w:val="1"/><w:numFmt w:val="decimal"/>'
                      f'<w:lvlText w:val="{text}"/><w:lvlJc w:val="left"/></w:lvl>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="multilevel"/>'
            + "".join(levels) + '</w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>')


def _section(style: DocxStyle, footer_id: str, *, start: str | None, next_page: bool = False) -> str:
    page = f'<w:pgNumType w:start="{start}"/>' if start else ""
    break_type = '<w:type w:val="nextPage"/>' if next_page else ""
    return ('<w:sectPr>'
            '<w:headerReference w:type="default" r:id="rId3"/>'
            f'<w:footerReference w:type="default" r:id="{footer_id}"/>'
            f'{break_type}'
            '<w:pgSz w:w="11906" w:h="16838"/>'
            f'<w:pgMar w:top="{_twips(style.margin_top_cm)}" w:right="{_twips(style.margin_right_cm)}" '
            f'w:bottom="{_twips(style.margin_bottom_cm)}" w:left="{_twips(style.margin_left_cm)}" '
            'w:header="851" w:footer="851" w:gutter="0"/>'
            f'{page}</w:sectPr>')


def _header(style: DocxStyle) -> str:
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f'<w:p><w:pPr><w:jc w:val="center"/></w:pPr>{_run(style.header_text, style.header_font, style.header_pt)}'
            '</w:p></w:hdr>')


def _footer(style: DocxStyle, *, page_number: bool) -> str:
    if page_number:
        run = (f'<w:r><w:rPr>{_fonts(style.header_font)}{_size(style.header_pt)}</w:rPr>'
               '<w:fldChar w:fldCharType="begin"/></w:r>'
               f'<w:r><w:rPr>{_fonts(style.header_font)}{_size(style.header_pt)}</w:rPr>'
               '<w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
               f'<w:r><w:rPr>{_fonts(style.header_font)}{_size(style.header_pt)}</w:rPr>'
               '<w:fldChar w:fldCharType="end"/></w:r>')
    else:
        run = _run("", style.header_font, style.header_pt)
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f'<w:p><w:pPr><w:jc w:val="center"/></w:pPr>{run}</w:p></w:ftr>')


def _toc(style: DocxStyle) -> str:
    instruction = ' TOC \\o "1-3" \\h \\z \\u '
    fonts = f'{_fonts(style.toc_font)}{_size(style.toc_pt)}'
    title = _paragraph("TocTitle", "目录", style.toc_font, style.toc_pt)
    return (title
            + '<w:p><w:pPr><w:pStyle w:val="TOC"/></w:pPr>'
            f'<w:r><w:rPr>{fonts}</w:rPr><w:fldChar w:fldCharType="begin"/></w:r>'
            f'<w:r><w:rPr>{fonts}</w:rPr>'
            f'<w:instrText xml:space="preserve">{instruction}</w:instrText></w:r>'
            '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
            f'<w:r><w:rPr>{fonts}</w:rPr><w:t>右键更新域以生成目录</w:t></w:r>'
            f'<w:r><w:rPr>{fonts}</w:rPr><w:fldChar w:fldCharType="end"/></w:r></w:p>')


def _table(rows: list[list[str]], style: DocxStyle) -> str:
    borders = "".join(f'<w:{edge} w:val="single" w:sz="4" w:color="777777"/>'
                      for edge in ("top", "left", "bottom", "right", "insideH", "insideV"))
    body = '<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:tblBorders>' + borders + '</w:tblBorders></w:tblPr>'
    for index, row in enumerate(rows):
        body += "<w:tr>" + ('<w:trPr><w:tblHeader/></w:trPr>' if index == 0 else "")
        for cell in row:
            body += ('<w:tc><w:tcPr><w:tcW w:w="1800" w:type="dxa"/></w:tcPr><w:p>'
                     + _run(cell, style.table_font, style.table_pt, bold=index == 0) + "</w:p></w:tc>")
        body += "</w:tr>"
    return body + "</w:tbl>"


def _faces(style: DocxStyle, style_id: str) -> tuple[FontFace, float, bool]:
    if style_id == "Heading1":
        return style.h1_font, style.h1_pt, False
    if style_id == "Heading2":
        return style.h2_font, style.h2_pt, True
    if style_id == "Heading3":
        return style.h3_font, style.h3_pt, True
    return style.body_font, style.body_pt, False


def build_docx(record: Export, table_rows: list[list[str]] | None = None, *,
               style: DocxStyle | None = None, project_name: str | None = None) -> bytes:
    chosen = style or DEFAULT_DOCX_STYLE
    cover = _paragraph("CoverTitle", record.title, chosen.cover_title_font, chosen.cover_title_pt, bold=True)
    if project_name:
        cover += _paragraph("CoverProject", project_name, chosen.cover_project_font, chosen.cover_project_pt)
    cover += f'<w:p><w:pPr>{_section(chosen, "rId5", start=None, next_page=True)}</w:pPr></w:p>'
    blocks = _blocks(record)
    body = _toc(chosen) if any(style_id.startswith("Heading") for style_id, _, _ in blocks) else ""
    for style_id, text, bold in blocks:
        face, pt, heading_bold = _faces(chosen, style_id)
        body += _paragraph(style_id, text, face, pt, bold=bold or heading_bold)
    if table_rows:
        body += _table(table_rows, chosen)
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                f'<w:body>{cover}{body}{_section(chosen, "rId4", start="1")}</w:body></w:document>')
    contents = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>
<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
<Override PartName="/word/footer2.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
</Types>'''
    root_relationships = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
    document_relationships = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>
<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
<Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer2.xml"/>
<Relationship Id="rId6" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>
</Relationships>'''
    settings = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:updateFields w:val="true"/></w:settings>'''
    target = BytesIO()
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", contents)
        archive.writestr("_rels/.rels", root_relationships)
        archive.writestr("word/document.xml", document)
        archive.writestr("word/_rels/document.xml.rels", document_relationships)
        archive.writestr("word/styles.xml", _style_xml(chosen))
        archive.writestr("word/numbering.xml", _numbering_xml())
        archive.writestr("word/settings.xml", settings)
        archive.writestr("word/header1.xml", _header(chosen))
        archive.writestr("word/footer1.xml", _footer(chosen, page_number=True))
        archive.writestr("word/footer2.xml", _footer(chosen, page_number=False))
    return target.getvalue()
