# 为什么有这个文件：技术条款在进目录之前先分成两种角色，废标句再分成约束种类。
# 它解决什么问题：废标项只当写作约束，响应项才进入要写进正文的要点；资格和商务不进技术硬约束。

from __future__ import annotations

import re


_REJECTION_WORD = re.compile(r"废标|否决|无效")

_BID_PACKAGING_MARKERS = (
    "注册资金",
    "办事处",
    "社保",
    "失信",
    "报价",
    "有效期",
    "正本",
    "副本",
    "装订",
    "U盘",
    "授权委托",
)


def is_bid_packaging(text: str) -> bool:
    """注册资金、失信、装订等投标包装。不新增第三种条款角色。"""
    return any(marker in str(text or "") for marker in _BID_PACKAGING_MARKERS)


def assign_clause_role(row: dict) -> str:
    """返回 response_mount 或 rejection_constraint。

    否决、废标条件，以及注册资金、社保、报价、装订这类投标包装，只作约束。
    带★的评分响应点仍可挂载成章。
    不读取检查问题的 severity，也不读取矩阵行的 critical。
    """
    if row.get("requirement_type") == "qualification" and not row.get("technical_clause"):
        return "response_mount"
    text = str(row.get("text") or "")
    if (
        row.get("category") == "disqualification"
        or "否决" in text
        or "废标条件" in text
        or is_bid_packaging(text)
    ):
        return "rejection_constraint"
    return "response_mount"


def is_section_constraint_row(row: dict) -> bool:
    """本章要遵守的技术废标行。资格行不是。"""
    if row.get("is_rejection_criterion") and row.get("requirement_type") != "qualification":
        return True
    return row.get("clause_role") == "rejection_constraint"


def classify_constraint(text: str, row: dict | None = None) -> dict:
    """先分种类再定级别。缺席不在这里判。

    kind：tech_hard 技术废标；non_tech_risk 资格、保证金、信用、商务包装；unclear 说不清。
    level：L0 废标条件，L1 挂在本章的技术废标，L2 一般，L3 文风或包装格式。
    """
    blob = str(text or "")
    if row:
        blob = f"{blob} {row.get('text') or ''} {row.get('extracted_summary') or ''}"
    if _looks_non_tech(blob, row):
        kind = "non_tech_risk"
    elif _REJECTION_WORD.search(blob):
        kind = "tech_hard"
    else:
        kind = "unclear"
    if kind == "tech_hard" and row and is_section_constraint_row(row):
        level = "L1"
    elif _REJECTION_WORD.search(blob):
        level = "L0"
    elif kind == "non_tech_risk":
        level = "L3"
    else:
        level = "L2"
    return {"kind": kind, "level": level}


def _looks_non_tech(blob: str, row: dict | None) -> bool:
    from icg.domain.technical_constraint_context import row_is_non_tech, text_is_non_tech

    if row and row_is_non_tech(row):
        return True
    return text_is_non_tech(blob)
