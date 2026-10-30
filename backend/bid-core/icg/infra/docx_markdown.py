# 为什么有这个文件：导出时把正文里的 Markdown 转成 Word 样式（PRD v1.8 §5.9.1 规则 1、6；平台默认模板预置一至八级标题；APP-M2-T196）。
# 它解决什么问题：
# 1. “#”～“########”转成一至八级标题（一至三级进目录，四至八级只用标题样式）；
# 2. 系统生成章节（点对点应答、评审索引表、偏离表、年度服务计划表、证明材料清单）是 Markdown 表格，转成真正的 Word 表格，
#    原先导出后是一行行“| … |”文字；
# 3. “- ”“* ”“1. ”列表转成带项目符号或编号的段落；“**加粗**”转成加粗文字，其余残留的 Markdown 符号去掉；
# 4. 每个块记下它覆盖的正文行号，附件扫描件按行号插在对应块之后（表格中间的行号也排到表格之后）。

from __future__ import annotations

import re
from dataclasses import dataclass, field

_HEADING = re.compile(r"^(#{1,8})\s+(.+?)\s*#*\s*$")
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_RULE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
_BULLET = re.compile(r"^\s*[-*+]\s+(.+)$")
_ORDERED = re.compile(r"^\s*(\d{1,3})[.)、]\s+(.+)$")
_BOLD = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
_LEFTOVER = re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])|`([^`]+)`")


@dataclass
class Block:
    kind: str                      # heading / para / bullet / ordered / table
    lines: tuple[int, int]         # 覆盖的正文行号（含两端）
    level: int = 0
    runs: list[tuple[str, bool]] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    number: str = ""

    @property
    def text(self) -> str:
        return "".join(text for text, _ in self.runs)


def runs(text: str) -> list[tuple[str, bool]]:
    """“**加粗**”拆成加粗片段；单个 * 包着的强调和 `代码` 去掉符号保留文字。"""
    text = _LEFTOVER.sub(lambda m: m.group(1) or m.group(2), text)
    out, last = [], 0
    for match in _BOLD.finditer(text):
        if match.start() > last:
            out.append((text[last:match.start()], False))
        out.append((match.group(1) or match.group(2), True))
        last = match.end()
    if last < len(text):
        out.append((text[last:], False))
    return [(t, b) for t, b in out if t] or [("", False)]


def _cells(line: str) -> list[str]:
    inner = line.strip()
    inner = inner[1:] if inner.startswith("|") else inner
    inner = inner[:-1] if inner.endswith("|") else inner
    return [cell.strip() for cell in inner.split("|")]


def blocks(content: str) -> list[Block]:
    lines = [] if content == "" else content.splitlines()
    result: list[Block] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        heading = _HEADING.match(line)
        if heading:
            result.append(Block("heading", (index, index), level=len(heading.group(1)), runs=runs(heading.group(2))))
            index += 1
            continue
        if _TABLE_ROW.match(line) and index + 1 < len(lines) and _TABLE_RULE.match(lines[index + 1]):
            start, rows = index, [_cells(line)]
            index += 2
            while index < len(lines) and _TABLE_ROW.match(lines[index]):
                rows.append(_cells(lines[index]))
                index += 1
            width = max(len(r) for r in rows)
            result.append(Block("table", (start, index - 1), rows=[r + [""] * (width - len(r)) for r in rows]))
            continue
        bullet, ordered = _BULLET.match(line), _ORDERED.match(line)
        if bullet:
            result.append(Block("bullet", (index, index), runs=runs(bullet.group(1))))
        elif ordered:
            result.append(Block("ordered", (index, index), runs=runs(ordered.group(2)), number=ordered.group(1)))
        else:
            result.append(Block("para", (index, index), runs=runs(line)))
        index += 1
    return result
