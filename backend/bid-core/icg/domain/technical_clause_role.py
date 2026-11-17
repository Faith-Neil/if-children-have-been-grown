# 为什么有这个文件：技术条款在进目录之前先分成两种角色。
# 它解决什么问题：废标项只当写作约束，响应项才进入要写进正文的要点。

from __future__ import annotations


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
        or any(marker in text for marker in _BID_PACKAGING_MARKERS)
    ):
        return "rejection_constraint"
    return "response_mount"
