#!/usr/bin/env python3
"""Batch TASK_BOARD + delivery ISSUE-046 sections for rule realignment."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "docs/TASK_BOARD.md"

MISALIGNED = [
    "T203", "T204", "T206", "T207", "T208", "T210", "T214", "T215", "T217", "T218",
    "T220", "T221", "T222", "T223", "T225", "T232", "T233", "T234", "T240", "T242",
]

ALIGNED_SECTION = """

## ISSUE-046：编号对齐状态

**编号已对齐**（2026-11-02，`BE-ISSUE-046-RULE-REALIGN`）：`check_rXX` 已按 [PRD v1.8 §5.8.1](../reference/product/prd-mvp-v1.8.md) 重挂；原错位逻辑迁入 `EXT-*` 扩展规则。证据：`tests/backend/test_compliance_rules*.py`（46 passed，本机 2026-11-02）；映射见 [决策矩阵](../decisions/2026-11-02-issue-046-realignment-matrix.md)。
"""

board = BOARD.read_text(encoding="utf-8")
for tid in MISALIGNED:
    old = f"APP-M2-{tid}](tasks/APP-M2.md#app-m2-{tid.lower()})"
    board = board.replace(
        f"| in-review（2026-10-28 重定：规则检查已实现并有测试，见 compliance_rules.py） | APP-M2-T",
        f"| in-progress（2026-11-02：ISSUE-046 PRD 编号已重挂，待 QA 签署） | APP-M2-T",
        1,
    )

# targeted replace per row
import re

def demote_line(text: str, tid: str) -> str:
    pat = rf"(\[APP-M2-{tid}\][^\|]+\| [^\|]+ \| )in-review（2026-10-28 重定：规则检查已实现并有测试，见 compliance_rules\.py）"
    rep = r"\1in-progress（2026-11-02：ISSUE-046 PRD 编号已重挂，pytest 46 项，待 QA 签署）"
    return re.sub(pat, rep, text, count=1)


for tid in MISALIGNED:
    board = demote_line(board, tid)

# PM done four cards
for tid, note in [
    ("T260", "2026-11-02：PM 队列确认，合入 main @ cfdf5ad，见 pm-done-queue"),
    ("T166", "2026-11-02：PM 队列确认，合入 main @ cfdf5ad"),
    ("T020", "2026-11-02：PM 队列确认，合入 main @ cfdf5ad"),
    ("T096", "2026-11-02：PM 队列确认，R19 已对齐，合入 main @ cfdf5ad"),
]:
    pat = rf"(\[APP-M2-{tid}\][^\|]+\| [^\|]+ \| )in-review（[^）]+）"
    board = re.sub(pat, rf"\1done（{note}）", board, count=1)

board = board.replace(
    "**约 19 条规则编号与 PRD 不符（R01、R02、R04～R06、R08、R10、R12、R13、R15～R18、R20、R26～R28、R32、R34，[ISSUE-046](../issues/ISSUE-046.md)），看板里这些规则卡的 in-review 不成立，待 PM 决定**",
    "**ISSUE-046 已关闭（2026-11-02）**：19 条规则 PRD 编号已重挂，错位逻辑在 `EXT-*`；规则单卡 in-progress 待 QA 产品签署（见 [矩阵](../docs/decisions/2026-11-02-issue-046-realignment-matrix.md)）**",
)
BOARD.write_text(board, encoding="utf-8")

for tid in MISALIGNED:
    path = ROOT / f"docs/delivery/APP-M2-{tid}.md"
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8")
    if "ISSUE-046：编号对齐状态" in text:
        continue
    path.write_text(text.rstrip() + ALIGNED_SECTION, encoding="utf-8")

print("patched board and", len(MISALIGNED), "deliveries")
