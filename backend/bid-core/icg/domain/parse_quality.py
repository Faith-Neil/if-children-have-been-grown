# 为什么有这个文件：解析条目的置信度与“原文不可读”标记（PRD v1.8 §5.2.2 规则 2、异常与边界；字典 tender_requirement.confidence；
# APP-M2-T104、T105）。
# 它解决什么问题：
# 1. 每条条款和事实带 0～1 的置信度：文字版 PDF/Word 抽出的文字可信（1.0 起），扫描件经文字识别的打 0.9 起；
#    摘录里有乱码字符、所在页乱码多、只抽到很短的片段都会降低置信度；低于公司阈值（默认 0.8）的条目在解析页高亮；
# 2. 扫描件识别质量差、摘录乱码时条目标“原文不可读”：不能直接确认或批量确认，须对照原页补录（改正文字）或填写理由删除；
# 3. 乱码按字符类别判断：替换字符、控制字符、私用区、西欧扩展字母（典型的编码错乱）算乱码；中文、英文数字和常用标点算正常。
# 文字识别把字认错成另一个正确的汉字时无法从字符上发现，所以扫描件条目一律不给满分置信度，并保留“对照原件核对”提示。

from __future__ import annotations

import re
import unicodedata

RECOGNIZED_BASE = 0.9
UNREADABLE_RATIO = 0.25
_SPACE = re.compile(r"\s+")


def _bad(char: str) -> bool:
    code = ord(char)
    if char == "\ufffd" or (0xE000 <= code <= 0xF8FF) or unicodedata.category(char) in ("Cc", "Cs", "Co", "Cn"):
        return True
    return 0x00C0 <= code <= 0x024F  # À～ɏ：中文招标文件里出现基本都是编码错乱


def garble_ratio(text: str) -> float:
    chars = [c for c in _SPACE.sub("", text or "")]
    if not chars:
        return 1.0
    return sum(_bad(c) for c in chars) / len(chars)


def page_ratios(pages: list[str]) -> list[float]:
    return [garble_ratio(page) if page.strip() else 1.0 for page in pages]


def assess(quote: str, *, recognized: bool, page_ratio: float = 0.0) -> dict:
    """返回 confidence、unreadable、unreadable_reason（可直接并入条目）。"""
    ratio = garble_ratio(quote)
    core = _SPACE.sub("", quote or "")
    score = (RECOGNIZED_BASE - min(0.2, page_ratio)) if recognized else 1.0
    score -= ratio * 2
    if len(core) < 6:
        score -= 0.1
    unreadable = ratio >= UNREADABLE_RATIO or core.count("\ufffd") >= 2 or (recognized and not core)
    reason = ""
    if unreadable:
        reason = "扫描件文字识别质量差，原文摘录乱码，请对照原页补录" if recognized else "原文摘录含乱码，请对照原页补录"
    return {"confidence": round(max(0.0, min(1.0, score)), 2), "unreadable": unreadable, "unreadable_reason": reason}


def unresolved_unreadable(row: dict) -> bool:
    """标了原文不可读、还没人工补录（改文字/取值）也没删除的条目。"""
    return bool(row.get("unreadable")) and not row.get("manually_edited") and row.get("status") != "rejected"


def low_confidence(row: dict, threshold: float) -> bool:
    value = row.get("confidence")
    return isinstance(value, (int, float)) and value < threshold and row.get("status") != "rejected"
