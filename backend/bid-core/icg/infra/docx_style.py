# 为什么有这个文件：把已批准的 Word 默认版式写成真实 docx，并允许单个投标覆盖。
# 它解决什么问题：导出不再只有普通段落，标题、目录、页码和三种字体属性都能被打开文件核对。
# 分册版式（PRD v1.8 §5.9.1 规则 2、3、10；APP-M2-T197）：每册独立封面（投标文件、项目名称、招标编号、分册、投标人、日期）；
# 目录单独一节、页码用罗马数字；正文一节、页码从 1 起；目录预先列出各级标题（带书签和页码域），打开时 Word/WPS 提示更新域补页码；
# 页眉按导出类型：递交版写项目名称和投标人，内部稿写“内部评审稿”；文档属性作者取投标人（内部稿留空），不写系统账号。
# 公司 Word 模板（APP-M2-T086/T196）读出的样式通过 style 传入；附件扫描件（APP-M2-T198）通过 inserts 与 media 插到正文指定行之后。
# 正文 Markdown（一至八级标题、表格、列表、加粗）由 docx_markdown 转成 Word 样式（§5.9.1 规则 1、6）。

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
    body_line_multiple: float | None = None  # 招标要求“1.5 倍行距”等时用倍数行距，否则用固定值 body_line_pt
    body_first_line_chars: int = 200
    body_first_line_twips: int = 560
    table_font: FontFace = field(default_factory=lambda: face("宋体"))
    table_pt: float = 10.5
    header_font: FontFace = field(default_factory=lambda: face("宋体"))
    header_pt: float = 10.5
    toc_font: FontFace = field(default_factory=lambda: face("宋体"))
    toc_pt: float = 12
    heading_space_lines: int = 50
    header_text: str = "内部评审稿 · 不可作为正式递交文件"


DEFAULT_DOCX_STYLE = DocxStyle()


@dataclass(frozen=True)
class DocxMeta:
    """一册投标文件的封面与页眉信息；缺项不写（不编造编号或投标人）。"""
    kind: str = "internal"            # submission / internal / internal_review
    volume_name: str = ""             # 技术分册 / 商务分册
    tender_number: str = ""
    bidder: str = ""
    date: str = ""                    # YYYY年M月D日
    dark_bid: bool = False            # 暗标分册：页眉和文档属性不出现投标人

    @property
    def submission(self) -> bool:
        return self.kind == "submission"


def header_text(meta: DocxMeta | None, style: DocxStyle, project_name: str | None) -> str:
    if meta is None:
        return style.header_text
    if meta.submission:
        parts = [project_name or "", "" if meta.dark_bid else meta.bidder]
        return "　".join(p for p in parts if p) or (meta.volume_name or "")
    return "　".join(p for p in ("内部评审稿 · 不可作为正式递交文件", project_name or "") if p)



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


def _runs(parts: list[tuple[str, bool]], item: FontFace, pt: float, *, bold: bool = False) -> str:
    return "".join(_run(text, item, pt, bold=bold or strong) for text, strong in parts)


def _styled(style_id: str, parts: list[tuple[str, bool]], item: FontFace, pt: float, *, bold: bool = False) -> str:
    return f'<w:p><w:pPr><w:pStyle w:val="{style_id}"/></w:pPr>{_runs(parts, item, pt, bold=bold)}</w:p>'


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

    line = (f'w:line="{int(round(style.body_line_multiple * 240))}" w:lineRule="auto"' if style.body_line_multiple
            else f'w:line="{int(round(style.body_line_pt * 20))}" w:lineRule="exact"')
    body_paragraph = (f'<w:pPr><w:spacing w:before="0" w:after="0" {line}/><w:ind w:firstLineChars="{style.body_first_line_chars}" '
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
    toc_tab = '<w:tabs><w:tab w:val="right" w:leader="dot" w:pos="8820"/></w:tabs>'
    toc = paragraph_style("TOC", "toc 1", f"<w:pPr>{toc_tab}</w:pPr>",
                          f'<w:rPr>{_fonts(style.toc_font)}{_size(style.toc_pt)}</w:rPr>')
    toc2 = paragraph_style("TOC2", "toc 2", f'<w:pPr>{toc_tab}<w:ind w:left="420"/></w:pPr>',
                           f'<w:rPr>{_fonts(style.toc_font)}{_size(style.toc_pt)}</w:rPr>')
    toc3 = paragraph_style("TOC3", "toc 3", f'<w:pPr>{toc_tab}<w:ind w:left="840"/></w:pPr>',
                           f'<w:rPr>{_fonts(style.toc_font)}{_size(style.toc_pt)}</w:rPr>')
    hanging = (f'<w:pPr><w:spacing w:before="0" w:after="0" {line}/>'
               '<w:ind w:left="420" w:hanging="420"/><w:jc w:val="both"/></w:pPr>')
    lists = "".join(paragraph_style(style_id, name, hanging, f'<w:rPr>{_fonts(style.body_font)}{_size(style.body_pt)}</w:rPr>')
                    for style_id, name in (("ListBullet", "List Bullet"), ("ListNumber", "List Number")))
    cover_line = paragraph_style(
        "CoverLine", "Cover Line", '<w:pPr><w:spacing w:before="120" w:after="120"/><w:jc w:val="center"/></w:pPr>',
        f'<w:rPr>{_fonts(style.cover_project_font)}{_size(style.toc_pt + 2)}</w:rPr>')
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr>{_fonts(style.body_font)}{_size(style.body_pt)}</w:rPr></w:rPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr>{_fonts(style.body_font)}{_size(style.body_pt)}</w:rPr></w:style>
{cover}{project}
{heading("Heading1", "heading 1", 0, style.h1_font, style.h1_pt, style.h1_align, False)}
{heading("Heading2", "heading 2", 1, style.h2_font, style.h2_pt, "left", True)}
{heading("Heading3", "heading 3", 2, style.h3_font, style.h3_pt, "left", True)}
{"".join(heading(f"Heading{n}", f"heading {n}", n - 1, *_low_heading(style, n), "left", True) for n in range(4, 9))}
{body}{toc_title}{toc}{toc2}{toc3}{cover_line}{lists}
</w:styles>'''


def _numbering_xml() -> str:
    levels = []
    for index, text in enumerate(".".join(f"%{n}" for n in range(1, level + 1)) for level in range(1, 9)):
        levels.append(f'<w:lvl w:ilvl="{index}"><w:start w:val="1"/><w:numFmt w:val="decimal"/>'
                      f'<w:lvlText w:val="{text}"/><w:lvlJc w:val="left"/></w:lvl>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="multilevel"/>'
            + "".join(levels) + '</w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>')


def _section(style: DocxStyle, footer_id: str, *, start: str | None, next_page: bool = False,
             header_id: str = "rId3", fmt: str | None = None) -> str:
    fmt_attr = f' w:fmt="{fmt}"' if fmt else ""
    page = f'<w:pgNumType{fmt_attr} w:start="{start}"/>' if start else ""
    break_type = '<w:type w:val="nextPage"/>' if next_page else ""
    return ('<w:sectPr>'
            f'<w:headerReference w:type="default" r:id="{header_id}"/>'
            f'<w:footerReference w:type="default" r:id="{footer_id}"/>'
            f'{break_type}'
            '<w:pgSz w:w="11906" w:h="16838"/>'
            f'<w:pgMar w:top="{_twips(style.margin_top_cm)}" w:right="{_twips(style.margin_right_cm)}" '
            f'w:bottom="{_twips(style.margin_bottom_cm)}" w:left="{_twips(style.margin_left_cm)}" '
            'w:header="851" w:footer="851" w:gutter="0"/>'
            f'{page}</w:sectPr>')


def _header(style: DocxStyle, text: str | None = None) -> str:
    content = style.header_text if text is None else text
    run = _run(content, style.header_font, style.header_pt) if content else ""
    border = '<w:pBdr><w:bottom w:val="single" w:sz="4" w:space="1" w:color="auto"/></w:pBdr>' if content else ""
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f'<w:p><w:pPr>{border}<w:jc w:val="center"/></w:pPr>{run}'
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


def _toc(style: DocxStyle, entries: list[tuple[int, str, str]] | None = None) -> str:
    """目录：一个 TOC 域，域结果预先列出各级标题（链接到标题书签，页码为 PAGEREF 域，打开时更新）。"""
    instruction = ' TOC \\o "1-3" \\h \\z \\u '
    fonts = f'{_fonts(style.toc_font)}{_size(style.toc_pt)}'
    title = _paragraph("TocTitle", "目录", style.toc_font, style.toc_pt)
    begin = (f'<w:r><w:rPr>{fonts}</w:rPr><w:fldChar w:fldCharType="begin"/></w:r>'
             f'<w:r><w:rPr>{fonts}</w:rPr><w:instrText xml:space="preserve">{instruction}</w:instrText></w:r>'
             '<w:r><w:fldChar w:fldCharType="separate"/></w:r>')
    end = f'<w:r><w:rPr>{fonts}</w:rPr><w:fldChar w:fldCharType="end"/></w:r>'
    if not entries:
        return (title + f'<w:p><w:pPr><w:pStyle w:val="TOC"/></w:pPr>{begin}'
                f'<w:r><w:rPr>{fonts}</w:rPr><w:t>右键更新域以生成目录</w:t></w:r>{end}</w:p>')
    paragraphs = []
    for index, (level, text, bookmark) in enumerate(entries):
        style_id = ("TOC", "TOC2", "TOC3")[min(level, 3) - 1]
        page = (f'<w:r><w:rPr>{fonts}</w:rPr><w:fldChar w:fldCharType="begin"/></w:r>'
                f'<w:r><w:rPr>{fonts}</w:rPr><w:instrText xml:space="preserve"> PAGEREF {bookmark} \\h </w:instrText></w:r>'
                '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
                f'<w:r><w:rPr>{fonts}</w:rPr><w:t></w:t></w:r>'
                f'<w:r><w:rPr>{fonts}</w:rPr><w:fldChar w:fldCharType="end"/></w:r>')
        link = (f'<w:hyperlink w:anchor="{bookmark}" w:history="1">'
                f'<w:r><w:rPr>{fonts}</w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'
                f'<w:r><w:rPr>{fonts}</w:rPr><w:tab/></w:r>{page}</w:hyperlink>')
        paragraphs.append(f'<w:p><w:pPr><w:pStyle w:val="{style_id}"/></w:pPr>'
                          f'{begin if index == 0 else ""}{link}{end if index == len(entries) - 1 else ""}</w:p>')
    return title + "".join(paragraphs)


def _cover(record: Export, style: DocxStyle, project_name: str | None, meta: DocxMeta | None) -> str:
    """封面：标题、项目名称；有分册信息时再写招标编号、分册、投标人（盖章）和日期，缺项不写。"""
    blank = '<w:p><w:pPr><w:spacing w:before="0" w:after="0"/></w:pPr></w:p>'
    title = "投标文件" if meta is not None else record.title  # 分册信息另起一行，不和项目名混在标题里
    parts = [blank * 4, _paragraph("CoverTitle", title, style.cover_title_font, style.cover_title_pt, bold=True)]
    if project_name:
        parts.append(_paragraph("CoverProject", project_name, style.cover_project_font, style.cover_project_pt))
    if meta is not None:
        parts.append(blank * 6)
        lines = [f"招标编号：{meta.tender_number}" if meta.tender_number else "",
                 f"分册：{meta.volume_name}" if meta.volume_name else "",
                 "" if meta.dark_bid else (f"投标人：{meta.bidder}（盖章）" if meta.bidder else ""),
                 meta.date,
                 "" if meta.submission else "内部评审稿 · 不可作为正式递交文件"]
        parts += [_paragraph("CoverLine", line, style.cover_project_font, style.toc_pt + 2) for line in lines if line]
    return "".join(parts)


def _core_properties(record: Export, meta: DocxMeta | None) -> str:
    """文档属性（§5.9.1 规则 10）：作者取投标主体，内部稿和暗标留空；不写系统账号、编写人或模板作者。"""
    creator = meta.bidder if meta is not None and meta.submission and not meta.dark_bid else ""
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{escape(record.title)}</dc:title><dc:creator>{escape(creator)}</dc:creator>'
            '<cp:lastModifiedBy></cp:lastModifiedBy></cp:coreProperties>')


def _plain(cell: str) -> str:
    from .docx_markdown import runs
    return "".join(text for text, _ in runs(cell))


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


def caption(style: DocxStyle, text: str) -> str:
    """附件标题行：居中加粗，不进目录。"""
    return (f'<w:p><w:pPr><w:keepNext/><w:spacing w:before="240" w:after="120"/><w:jc w:val="center"/></w:pPr>'
            f'{_run(text, style.body_font, style.body_pt, bold=True)}</w:p>')


def text_area_cm(style: DocxStyle) -> tuple[float, float]:
    """A4 正文区宽、高（厘米），附件图片按此缩放。"""
    return 21.0 - style.margin_left_cm - style.margin_right_cm, 29.7 - style.margin_top_cm - style.margin_bottom_cm


def _low_heading(style: DocxStyle, level: int) -> tuple[FontFace, float]:
    """四至八级标题（平台默认模板预置一至八级，§5.6.1）：沿用三级标题字体，四级同三级字号，五级起同正文字号。"""
    return style.h3_font, style.h3_pt if level == 4 else style.body_pt


def _heading_face(style: DocxStyle, level: int) -> tuple[FontFace, float, bool]:
    if level == 1:
        return style.h1_font, style.h1_pt, False
    if level == 2:
        return style.h2_font, style.h2_pt, True
    if level == 3:
        return style.h3_font, style.h3_pt, True
    return (*_low_heading(style, level), True)


def build_docx(record: Export, table_rows: list[list[str]] | None = None, *,
               style: DocxStyle | None = None, project_name: str | None = None,
               meta: DocxMeta | None = None, inserts: dict[int, str] | None = None,
               media: list[tuple[str, str, bytes]] | None = None) -> bytes:
    """inserts：正文第 n 行之后追加的段落 XML（附件扫描件，n 为 -1 表示正文最前）；media：(关系 ID, 文件名, 字节)。"""
    chosen = style or DEFAULT_DOCX_STYLE
    inserts = inserts or {}
    # 节：封面（无页眉页码）→ 目录（罗马数字页码，有标题时才有）→ 正文（页码从 1 起）
    cover = _cover(record, chosen, project_name, meta)
    cover += f'<w:p><w:pPr>{_section(chosen, "rId5", start=None, next_page=True, header_id="rId7")}</w:pPr></w:p>'
    from .docx_markdown import blocks as markdown_blocks
    entries: list[tuple[int, str, str]] = []
    body = inserts.get(-1, "")
    for block in markdown_blocks(record.content):
        first, last = block.lines
        if block.kind == "heading":
            face_, pt, bold = _heading_face(chosen, block.level)
            bookmark = f"_Toc{first + 1:06d}"
            if block.level <= 3:  # 目录列一至三级
                entries.append((block.level, block.text, bookmark))
            body += (f'<w:p><w:pPr><w:pStyle w:val="Heading{block.level}"/></w:pPr>'
                     f'<w:bookmarkStart w:id="{first + 1}" w:name="{bookmark}"/>{_runs(block.runs, face_, pt, bold=bold)}'
                     f'<w:bookmarkEnd w:id="{first + 1}"/></w:p>')
        elif block.kind == "table":
            body += _table([[_plain(cell) for cell in row] for row in block.rows], chosen)
        elif block.kind == "bullet":
            body += _styled("ListBullet", [("• ", False), *block.runs], chosen.body_font, chosen.body_pt)
        elif block.kind == "ordered":
            body += _styled("ListNumber", [(f"{block.number}. ", False), *block.runs], chosen.body_font, chosen.body_pt)
        else:
            body += _styled("BodyText", block.runs, chosen.body_font, chosen.body_pt)
        for line in range(first, last + 1):  # 附件插在覆盖这些行的块之后（表格中间的行号排到表格之后）
            body += inserts.get(line, "")
    if table_rows:
        body += _table(table_rows, chosen)
    toc = ""
    if entries:
        toc = _toc(chosen, entries) + (f'<w:p><w:pPr>{_section(chosen, "rId4", start="1", next_page=True, fmt="lowerRoman")}'
                                       '</w:pPr></w:p>')
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
                'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
                'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
                f'<w:body>{cover}{toc}{body}{_section(chosen, "rId4", start="1", fmt="decimal")}</w:body></w:document>')
    contents = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="jpeg" ContentType="image/jpeg"/>
<Default Extension="png" ContentType="image/png"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>
<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
<Override PartName="/word/footer2.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
<Override PartName="/word/header2.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>'''
    root_relationships = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>'''
    document_relationships = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>
<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
<Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer2.xml"/>
<Relationship Id="rId6" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>
<Relationship Id="rId7" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header2.xml"/>
</Relationships>'''
    image_type = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
    document_relationships = document_relationships.replace("</Relationships>", "".join(
        f'<Relationship Id="{rid}" Type="{image_type}" Target="media/{name}"/>' for rid, name, _ in media or []) + "</Relationships>")
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
        archive.writestr("word/header1.xml", _header(chosen, header_text(meta, chosen, project_name)))
        archive.writestr("word/header2.xml", _header(chosen, ""))  # 封面不带页眉
        archive.writestr("docProps/core.xml", _core_properties(record, meta))
        archive.writestr("word/footer1.xml", _footer(chosen, page_number=True))
        archive.writestr("word/footer2.xml", _footer(chosen, page_number=False))
        for _rid, name, data in media or []:
            archive.writestr(f"word/media/{name}", data)
    return target.getvalue()
