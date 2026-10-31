# 为什么有这个文件：招标文件的格式要求覆盖 Word 模板（PRD v1.8 §5.9.1 规则 5，抽取项第 8 类“字体字号、页边距…”；APP-M2-T196）。
# 它解决什么问题：从已确认的格式类招标条款（没有时从招标原文）读出正文、一至三级标题、表格的字体字号，正文行距和页边距，
# 导出时按“招标要求 > 公司模板 > 平台默认”叠加；每一项记下依据的原文，写进导出记录供核对。读不出的项不猜。

from __future__ import annotations

import re
from typing import Any

FONTS = ("仿宋_GB2312", "楷体_GB2312", "方正小标宋", "微软雅黑", "宋体", "仿宋", "黑体", "楷体")
SIZES = {"初号": 42, "小初": 36, "一号": 26, "小一": 24, "二号": 22, "小二": 18, "三号": 16, "小三": 15,
         "四号": 14, "小四": 12, "五号": 10.5, "小五": 9}
TARGETS = (("一级标题", "h1"), ("章标题", "h1"), ("二级标题", "h2"), ("节标题", "h2"), ("三级标题", "h3"),
           ("表格", "table"), ("正文", "body"))
LABELS = {"h1": "一级标题", "h2": "二级标题", "h3": "三级标题", "table": "表格文字", "body": "正文"}
_SENTENCE = re.compile(r"[^。；;\n]+")
_SIZE = re.compile(r"(小初|初号|小一|一号|小二|二号|小三|三号|小四|四号|小五|五号)|(\d{1,2}(?:\.5)?)\s*(?:磅|pt|PT)(?!\s*行距)")
_MULTIPLE = re.compile(r"(\d(?:\.\d{1,2})?)\s*倍\s*行距|行距[^，,\d]{0,6}(\d(?:\.\d{1,2})?)\s*倍")
_EXACT = re.compile(r"(?:固定值|行距)[^，,\d]{0,6}(\d{1,2}(?:\.5)?)\s*(?:磅|pt)")
_MARGIN = re.compile(r"(上|下|左|右)(?:边距|侧|页边距)?\s*[:：为]?\s*(\d(?:\.\d{1,2})?)\s*(?:cm|厘米|CM)")
_MARGIN_ALL = re.compile(r"页边距[^，,\d上下左右]{0,6}(\d(?:\.\d{1,2})?)\s*(?:cm|厘米|CM)")
_FORMAT_WORDS = re.compile(r"字体|字号|号字|行距|边距|磅|小?[初一二三四五]号|宋体|仿宋|黑体|楷体|雅黑")


def _sentences(workflow: dict) -> list[tuple[str, str | None]]:
    """（句子，来源条款 ID）：先取已确认的格式类条款；没有时退回招标原文中提到字体字号行距页边距的句子。"""
    from .parse_review import requirement_category
    rows = [r for r in (workflow.get("requirements") or {}).values()
            if r.get("status") == "confirmed" and requirement_category(r) == "format" and _FORMAT_WORDS.search(str(r.get("text")))]
    if rows:
        return [(s.strip(), r["id"]) for r in rows for s in _SENTENCE.findall(str(r["text"])) if _FORMAT_WORDS.search(s)]
    from .scope_rules import tender_text
    return [(s.strip(), None) for s in _SENTENCE.findall(tender_text(workflow)) if _FORMAT_WORDS.search(s)][:40]


def overrides(workflow: dict) -> tuple[dict[str, Any], list[dict]]:
    """返回（DocxStyle 字段覆盖值，逐项说明）。"""
    changes: dict[str, Any] = {}
    applied: list[dict] = []

    def put(field: str, value: Any, label: str, quote: str, source: str | None):
        if field in changes:
            return  # 同一项以先出现（条款顺序靠前）的为准
        changes[field] = value
        applied.append({"item": label, "value": value if not isinstance(value, dict) else value["east_asia"],
                        "quote": quote[:120], "requirement_id": source})

    for sentence, source in _sentences(workflow):
        target = next((key for word, key in TARGETS if word in sentence), None)
        if target:
            font = next((f for f in FONTS if f in sentence), None)
            size = _SIZE.search(sentence)
            if font:
                put(f"{target}_font", {"east_asia": font, "ascii": font, "h_ansi": font}, f"{LABELS[target]}字体", sentence, source)
            if size:
                pt = float(SIZES[size.group(1)]) if size.group(1) else float(size.group(2))
                if 5 <= pt <= 72:
                    put(f"{target}_pt", pt, f"{LABELS[target]}字号", sentence, source)
            if target == "body":
                multiple, exact = _MULTIPLE.search(sentence), _EXACT.search(sentence)
                if multiple:
                    value = float(multiple.group(1) or multiple.group(2))
                    if 1 <= value <= 3:
                        put("body_line_multiple", value, "正文行距（倍数）", sentence, source)
                elif exact:
                    put("body_line_pt", float(exact.group(1)), "正文行距（固定值，磅）", sentence, source)
        if "边距" in sentence:
            sides = {"上": "top", "下": "bottom", "左": "left", "右": "right"}
            found = {sides[m.group(1)]: float(m.group(2)) for m in _MARGIN.finditer(sentence)}
            whole = _MARGIN_ALL.search(sentence)
            if not found and whole:
                found = {side: float(whole.group(1)) for side in sides.values()}
            for side, cm in found.items():
                if 0.5 <= cm <= 6:
                    put(f"margin_{side}_cm", cm, f"{'上下左右'['top bottom left right'.split().index(side)]}页边距（厘米）", sentence, source)
    return changes, applied


def apply(style: dict | None, changes: dict[str, Any]) -> dict | None:
    """叠在模板样式（或平台默认）之上；没有覆盖时原样返回。"""
    if not changes:
        return style
    from icg.infra.docx_style import DEFAULT_DOCX_STYLE
    from icg.infra.docx_template import style_to_dict
    merged = dict(style) if style else style_to_dict(DEFAULT_DOCX_STYLE)
    merged.update(changes)
    if "body_line_pt" in changes:
        merged["body_line_multiple"] = None
    return merged
