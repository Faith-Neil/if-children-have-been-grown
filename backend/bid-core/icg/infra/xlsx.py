# 为什么有这个文件：生成真实可用 Excel/WPS 打开的 .xlsx（合标核对清单 APP-M2-T200，后续响应追溯表 T201 复用）。
# 它解决什么问题：内网离线部署不额外引入 openpyxl；与 docx_style.py 一样直接写 OOXML 压缩包，
# 只用内联字符串、冻结表头、自动换行与列宽，足够人工逐项核对。

from __future__ import annotations

import io
import zipfile
from xml.sax.saxutils import escape


def _column(index: int) -> str:
    name = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        name = chr(65 + rem) + name
    return name


def _clean(value: object) -> str:
    text = "" if value is None else str(value)
    # XML 1.0 不允许的控制字符（换页符等）去掉，换行保留
    return "".join(ch for ch in text if ch in "\t\n\r" or ord(ch) >= 0x20)


def _sheet_xml(rows: list[list[object]], widths: list[int], header_rows: int) -> str:
    cols = "".join(f'<col min="{i + 1}" max="{i + 1}" width="{w}" customWidth="1"/>' for i, w in enumerate(widths))
    body = []
    for r, row in enumerate(rows, start=1):
        cells = []
        for c, value in enumerate(row):
            ref = f"{_column(c)}{r}"
            style = 1 if r == header_rows else 2
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                cells.append(f'<c r="{ref}" s="{style}"><v>{value}</v></c>')
            else:
                text = escape(_clean(value))
                cells.append(f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>')
        body.append(f'<row r="{r}">{"".join(cells)}</row>')
    pane = (f'<sheetViews><sheetView workbookViewId="0"><pane ySplit="{header_rows}" topLeftCell="A{header_rows + 1}" '
            f'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>') if header_rows else ""
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'{pane}<cols>{cols}</cols><sheetData>{"".join(body)}</sheetData></worksheet>')


_STYLES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
           '<fonts count="2"><font><sz val="11"/><name val="宋体"/></font><font><b/><sz val="11"/><name val="宋体"/></font></fonts>'
           '<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
           '<fill><patternFill patternType="solid"><fgColor rgb="FFE8EEF7"/><bgColor indexed="64"/></patternFill></fill></fills>'
           '<borders count="2"><border/><border><left style="thin"/><right style="thin"/><top style="thin"/><bottom style="thin"/></border></borders>'
           '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
           '<cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
           '<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment wrapText="1" vertical="center"/></xf>'
           '<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>'
           '</cellXfs></styleSheet>')


def build_xlsx(sheets: list[dict]) -> bytes:
    """sheets: [{"name": str, "rows": [[...], ...], "widths": [int,...], "header_rows": int}]；header_rows 为冻结并加粗的行号。"""
    buffer = io.BytesIO()
    names = [str(s["name"])[:31] for s in sheets]
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        overrides = "".join(
            f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for i in range(len(sheets)))
        archive.writestr("[Content_Types].xml",
                         '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                         '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                         '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                         '<Default Extension="xml" ContentType="application/xml"/>'
                         '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                         '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
                         f'{overrides}</Types>')
        archive.writestr("_rels/.rels",
                         '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                         '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                         '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                         '</Relationships>')
        sheet_entries = "".join(f'<sheet name="{escape(n)}" sheetId="{i + 1}" r:id="rId{i + 1}"/>' for i, n in enumerate(names))
        archive.writestr("xl/workbook.xml",
                         '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                         '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                         'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                         f'<sheets>{sheet_entries}</sheets></workbook>')
        rels = "".join(f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                       f'Target="worksheets/sheet{i + 1}.xml"/>' for i in range(len(sheets)))
        rels += (f'<Relationship Id="rId{len(sheets) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
                 'Target="styles.xml"/>')
        archive.writestr("xl/_rels/workbook.xml.rels",
                         '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                         f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{rels}</Relationships>')
        archive.writestr("xl/styles.xml", _STYLES)
        for i, sheet in enumerate(sheets):
            rows = sheet["rows"]
            width = max((len(r) for r in rows), default=1)
            widths = list(sheet.get("widths") or [20] * width)
            archive.writestr(f"xl/worksheets/sheet{i + 1}.xml", _sheet_xml(rows, widths, int(sheet.get("header_rows") or 0)))
    return buffer.getvalue()


def read_xlsx_rows(data: bytes, sheet: int = 1) -> list[list[str]]:
    """测试与自检用：读回内联字符串表格（只支持本模块写出的格式）。"""
    import re
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        xml = archive.read(f"xl/worksheets/sheet{sheet}.xml").decode("utf-8")
    from xml.sax.saxutils import unescape
    rows = []
    for row in re.findall(r"<row [^>]*>(.*?)</row>", xml, re.S):
        cells = re.findall(r"<c [^>]*?(?:/>|>(.*?)</c>)", row, re.S)
        values = []
        for cell in cells:
            text = re.search(r"<t[^>]*>(.*?)</t>", cell or "", re.S)
            number = re.search(r"<v>(.*?)</v>", cell or "", re.S)
            values.append(unescape(text.group(1)) if text else (number.group(1) if number else ""))
        rows.append(values)
    return rows
