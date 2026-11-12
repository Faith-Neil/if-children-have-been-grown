# 为什么有这个文件：技术条款在进目录之前先分成两种角色。
# 它解决什么问题：废标项只当写作约束，响应项才进入要写进正文的要点。

from __future__ import annotations


def assign_clause_role(row: dict) -> str:
    """返回 response_mount 或 rejection_constraint。

    真正否决/废标条件才是约束；带★的评分响应点仍可挂载成章。
    不读取检查问题的 severity，也不读取矩阵行的 critical。
    """
    if row.get("requirement_type") == "qualification" and not row.get("technical_clause"):
        return "response_mount"
    text = str(row.get("text") or "")
    if (
        row.get("category") == "disqualification"
        or "否决" in text
        or "废标条件" in text
    ):
        return "rejection_constraint"
    return "response_mount"
