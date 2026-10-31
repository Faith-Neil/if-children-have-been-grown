# 为什么有这个文件：公司 Word 模板（PRD v1.8 §5.6.1 Word 模板、§5.9.1 规则 1；APP-M2-T086、T196）。
# 它解决什么问题：公司管理员上传自己的 .docx 模板后，从模板里读出标题、正文、表格、页眉、目录的字体字号、
# 一级标题对齐、正文行距与首行缩进、页边距，换成导出用的 DocxStyle；没读到的项沿用平台默认并逐项说明。
# 只读样式，不把模板里的文档属性、自定义属性、批注或宏带进导出文件（§5.9.1 规则 10、R25）。
# 模板是外部文件：限制大小、拒绝宏文档和带 DOCTYPE 的 XML（防实体膨胀），解析失败给出可读原因。

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import asdict, replace
from io import BytesIO
from zipfile import BadZipFile, ZipFile

from .docx_style import DEFAULT_DOCX_STYLE, DocxStyle, FontFace

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
MAX_TEMPLATE_BYTES = 20 * 1024 * 1024
MAX_PART_BYTES = 10 * 1024 * 1024

# 导出样式项 → 模板里的样式名（Word 内部英文名，中文版 Word 也一样）；按顺序取第一个存在的
TARGETS = {
    "h1": ("heading 1",), "h2": ("heading 2",), "h3": ("heading 3",),
    "body": ("body text", "normal"), "table": ("table text", "normal"),
    "header": ("header",), "toc": ("toc 1",), "cover_title": ("title",), "cover_project": ("subtitle",),
}
LABELS = {"h1": "一级标题", "h2": "二级标题", "h3": "三级标题", "body": "正文", "table": "表格文字",
          "header": "页眉", "toc": "目录", "cover_title": "封面标题", "cover_project": "封面项目名称"}
ALIGN = {"center": "居中", "left": "左对齐", "start": "左对齐", "both": "两端对齐", "right": "右对齐", "end": "右对齐"}


class TemplateError(ValueError):
    """模板不能用：原因写给公司管理员看。"""


def _xml(archive: ZipFile, name: str) -> ET.Element | None:
    if name not in archive.namelist():
        return None
    info = archive.getinfo(name)
    if info.file_size > MAX_PART_BYTES:
        raise TemplateError(f"模板中的 {name} 过大，无法读取。")
    data = archive.read(name)
    if b"<!DOCTYPE" in data[:4096].upper() or b"<!ENTITY" in data.upper():
        raise TemplateError("模板含有不允许的 XML 声明，请在 Word 中另存为普通 .docx 后再上传。")
    try:
        return ET.fromstring(data)
    except ET.ParseError as error:
        raise TemplateError(f"模板中的 {name} 已损坏（{error}）。") from error


def _theme_fonts(theme: ET.Element | None) -> dict[str, str]:
    """主题字体：major/minor 的西文与中文（Hans 或 ea）字体，供 asciiTheme/eastAsiaTheme 引用。"""
    fonts: dict[str, str] = {}
    if theme is None:
        return fonts
    for kind in ("major", "minor"):
        node = theme.find(f".//{A}{kind}Font")
        if node is None:
            continue
        latin, ea = node.find(f"{A}latin"), node.find(f"{A}ea")
        hans = next((f.get("typeface") for f in node.findall(f"{A}font") if f.get("script") == "Hans"), None)
        fonts[f"{kind}HAnsi"] = fonts[f"{kind}Ascii"] = (latin.get("typeface") if latin is not None else "") or ""
        fonts[f"{kind}EastAsia"] = hans or ((ea.get("typeface") if ea is not None else "") or "")
    return fonts


def _run_props(rpr: ET.Element | None, theme: dict[str, str]) -> dict:
    found: dict = {}
    if rpr is None:
        return found
    fonts = rpr.find(f"{W}rFonts")
    if fonts is not None:
        for key in ("eastAsia", "ascii", "hAnsi"):
            value = fonts.get(W + key) or theme.get(fonts.get(W + key + "Theme") or "", "")
            if value:
                found[key] = value
    size = rpr.find(f"{W}sz")
    if size is not None and (size.get(W + "val") or "").isdigit():
        found["pt"] = int(size.get(W + "val")) / 2
    return found


def _para_props(ppr: ET.Element | None) -> dict:
    found: dict = {}
    if ppr is None:
        return found
    jc = ppr.find(f"{W}jc")
    if jc is not None and jc.get(W + "val") in ALIGN:
        found["align"] = "left" if jc.get(W + "val") == "start" else "right" if jc.get(W + "val") == "end" else jc.get(W + "val")
    spacing = ppr.find(f"{W}spacing")
    if spacing is not None and spacing.get(W + "lineRule") in ("exact", "atLeast") and (spacing.get(W + "line") or "").isdigit():
        found["line_pt"] = int(spacing.get(W + "line")) / 20
    ind = ppr.find(f"{W}ind")
    if ind is not None:
        chars, twips = ind.get(W + "firstLineChars"), ind.get(W + "firstLine")
        if chars and chars.isdigit():
            found["first_chars"] = int(chars)
        if twips and twips.isdigit():
            found["first_twips"] = int(twips)
    return found


def _styles(styles: ET.Element, theme: dict[str, str]) -> dict[str, dict]:
    """按样式名解析，沿 basedOn 链继承，最后叠在文档默认字体之上。"""
    by_id = {s.get(W + "styleId"): s for s in styles.findall(f"{W}style")}
    defaults = _run_props(styles.find(f"{W}docDefaults/{W}rPrDefault/{W}rPr"), theme)

    def resolve(node: ET.Element, depth: int = 0) -> dict:
        based_on = node.find(f"{W}basedOn")  # 没有子节点的 Element 判真为假，必须和 None 比较
        base = by_id.get(based_on.get(W + "val")) if based_on is not None else None
        merged = resolve(base, depth + 1) if base is not None and depth < 10 else {}
        return {**merged, **_para_props(node.find(f"{W}pPr")), **_run_props(node.find(f"{W}rPr"), theme)}

    named = {}
    for node in by_id.values():
        name = node.find(f"{W}name")
        if name is not None and name.get(W + "val"):
            named[name.get(W + "val").strip().lower()] = {**defaults, **resolve(node)}
    return named


def _face(found: dict, fallback: FontFace) -> FontFace | None:
    east = found.get("eastAsia")
    latin = found.get("ascii") or found.get("hAnsi")
    if not east and not latin:
        return None
    return FontFace(east or fallback.east_asia, latin or east or fallback.ascii, found.get("hAnsi") or latin or east or fallback.h_ansi)


def _margins(document: ET.Element | None) -> dict[str, float]:
    if document is None:
        return {}
    sections = document.findall(f".//{W}sectPr")
    margin = sections[-1].find(f"{W}pgMar") if sections else None
    if margin is None:
        return {}
    found = {}
    for edge in ("top", "bottom", "left", "right"):
        value = (margin.get(W + edge) or "").lstrip("-")
        if value.isdigit() and 0 < int(value) < 11906:
            found[f"margin_{edge}_cm"] = round(int(value) * 2.54 / 1440, 2)
    return found


def parse_template(data: bytes) -> tuple[DocxStyle, list[str], list[str]]:
    """返回（导出样式，读到的项说明，沿用平台默认的项）；模板不可用时抛 TemplateError。"""
    if len(data) > MAX_TEMPLATE_BYTES:
        raise TemplateError("Word 模板不能超过 20MB。")
    try:
        archive = ZipFile(BytesIO(data))
    except BadZipFile as error:
        raise TemplateError("不是有效的 .docx 文件。") from error
    with archive:
        names = set(archive.namelist())
        if "word/document.xml" not in names:
            raise TemplateError("不是有效的 .docx 文件（缺少正文部分）。")
        types = archive.read("[Content_Types].xml") if "[Content_Types].xml" in names else b""
        if "word/vbaProject.bin" in names or b"macroEnabled" in types:
            raise TemplateError("模板含宏，请另存为不含宏的 .docx 后再上传。")
        styles = _xml(archive, "word/styles.xml")
        theme = _theme_fonts(_xml(archive, "word/theme/theme1.xml"))
        document = _xml(archive, "word/document.xml")
    named = _styles(styles, theme) if styles is not None else {}
    base = DEFAULT_DOCX_STYLE
    changes: dict = {}
    applied, defaults = [], []
    for target, names_ in TARGETS.items():
        found = next((named[n] for n in names_ if n in named), None)
        prefix = target
        old_face = getattr(base, f"{prefix}_font")
        new_face = _face(found or {}, old_face)
        detail = []
        if new_face is not None:
            changes[f"{prefix}_font"] = new_face
            detail.append(new_face.east_asia if new_face.east_asia == new_face.ascii else f"{new_face.east_asia} / {new_face.ascii}")
        if found and found.get("pt") and 5 <= found["pt"] <= 72:
            changes[f"{prefix}_pt"] = found["pt"]
            detail.append(f"{found['pt']:g} 磅")
        if target == "h1" and found and found.get("align"):
            changes["h1_align"] = found["align"]
            detail.append(ALIGN[found["align"]])
        if target == "body" and found:
            if found.get("line_pt") and 8 <= found["line_pt"] <= 72:
                changes["body_line_pt"] = found["line_pt"]
                detail.append(f"固定行距 {found['line_pt']:g} 磅")
            if "first_chars" in found:
                changes["body_first_line_chars"] = found["first_chars"]
            if "first_twips" in found:
                changes["body_first_line_twips"] = found["first_twips"]
            if "first_chars" in found or "first_twips" in found:
                detail.append("首行缩进 " + (f"{found['first_chars'] / 100:g} 字符" if "first_chars" in found
                                          else f"{found['first_twips'] / 567:.2f} 厘米"))
        (applied if detail else defaults).append(f"{LABELS[target]}：{'，'.join(detail)}" if detail else LABELS[target])
    margins = _margins(document)
    changes.update(margins)
    if margins:
        applied.append("页边距：" + "，".join(f"{label} {margins[k]:g} 厘米" for k, label in
                                            (("margin_top_cm", "上"), ("margin_bottom_cm", "下"),
                                             ("margin_left_cm", "左"), ("margin_right_cm", "右")) if k in margins))
    else:
        defaults.append("页边距")
    return replace(base, **changes), applied, defaults


def style_to_dict(style: DocxStyle) -> dict:
    return asdict(style)


def style_from_dict(data: dict | None) -> DocxStyle | None:
    """导出快照里保存的样式字典 → DocxStyle；未知字段忽略（模板快照比代码旧或新时都能读）。"""
    if not data:
        return None
    fields = {name: value for name, value in data.items() if name in DocxStyle.__dataclass_fields__}
    for name, value in list(fields.items()):
        if isinstance(value, dict):
            fields[name] = FontFace(**value)
    return replace(DEFAULT_DOCX_STYLE, **fields)
