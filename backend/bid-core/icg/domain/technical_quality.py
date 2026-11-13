# 为什么有这个文件：技术分册全文质量八条规则抽检（最短路径验收硬门槛）。
# 它解决什么问题：生成后标「需核对」可见警告，不恢复矩阵确认闸门，不挡内部稿导出。

from __future__ import annotations

import re
from typing import Any

HEADING = re.compile(r"^(\d+(?:\.\d+)*)\s+(\S.*)$")
TABLE_LINE = re.compile(r"^\|.+\|$")
COMMERCIAL = re.compile(r"报价|投标保证金|营业执照|资质证书|业绩证明|开标一览")


def _leaves(outline: dict) -> list[dict]:
    return [item for item in outline.get("headings") or [] if item.get("requirement_id")]


def _section_body(content: str, number: str, title: str) -> str:
    lines = (content or "").splitlines()
    marker = f"{number} {title}"
    start = next((index + 1 for index, line in enumerate(lines) if line.strip() == marker), None)
    if start is None:
        return ""
    end = next((index for index in range(start, len(lines)) if HEADING.match(lines[index].strip())), len(lines))
    return "\n".join(lines[start:end]).strip()


def _clauses(workflow: dict) -> dict[str, dict]:
    return {
        row["id"]: row
        for row in (workflow.get("requirements") or {}).values()
        if row.get("technical_clause") and row.get("status") != "rejected"
    }


def evaluate_quality(workflow: dict, content: str) -> dict[str, Any]:
    """返回八条抽检结果；failed 的规则会把相关节标需核对。"""
    outline = workflow.get("technical_outline") or {}
    headings = list(outline.get("headings") or [])
    leaves = _leaves(outline)
    rows = _clauses(workflow)
    linked = {item.get("requirement_id") for item in leaves if item.get("requirement_id")}
    missing = [row for row in rows.values() if row["id"] not in linked]
    scoring = [row for row in rows.values() if row.get("section_kind") == "scoring"]
    scoring_thin = []
    for leaf in leaves:
        row = rows.get(leaf.get("requirement_id") or "")
        if not row or row.get("section_kind") != "scoring":
            continue
        body = _section_body(content, leaf.get("number") or "", leaf.get("title") or "")
        if len(body) < 40 or body.strip() in ("待补", "需要核对"):
            scoring_thin.append(leaf.get("title") or row.get("text") or "")
    levels = [int(item.get("level") or 0) for item in headings]
    depth_ok = all(1 <= level <= 4 for level in levels) if levels else False
    has_l1 = any(level == 1 for level in levels)
    thin_open_close = []
    tables = 0
    commercial_noise = []
    project_touch = []
    for leaf in leaves:
        body = _section_body(content, leaf.get("number") or "", leaf.get("title") or "")
        title = leaf.get("title") or ""
        if not body or body.strip() == "待补":
            thin_open_close.append(title)
            continue
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        if len(lines) < 3:
            thin_open_close.append(title)
        tables += sum(1 for line in lines if TABLE_LINE.match(line))
        if COMMERCIAL.search(body) and not COMMERCIAL.search(title):
            commercial_noise.append(title)
        row = rows.get(leaf.get("requirement_id") or "") or {}
        clause = str(row.get("text") or "")
        if clause and clause[:4] not in body and "本项目" not in body and "招标" not in body:
            project_touch.append(title)
    rules = [
        {
            "id": 1, "name": "大纲覆盖与一一响应",
            "passed": not missing and bool(leaves),
            "detail": f"未挂目录条款 {len(missing)} 条" if missing else "挂接完整",
        },
        {
            "id": 2, "name": "评分得分点有实质段落",
            "passed": not scoring_thin,
            "detail": ("薄弱：" + "、".join(scoring_thin[:5])) if scoring_thin else (
                "无评分叶子" if not scoring else "得分点已写"),
        },
        {
            "id": 3, "name": "结合客户实际",
            "passed": not project_touch,
            "detail": ("缺结合：" + "、".join(project_touch[:5])) if project_touch else "已体现项目结合",
        },
        {
            "id": 4, "name": "目录层级 1～4 合理",
            "passed": depth_ok and has_l1 and bool(headings),
            "detail": "层级合法" if depth_ok and has_l1 else "层级缺失或越界",
        },
        {
            "id": 5, "name": "开收与图文总结",
            "passed": not thin_open_close and tables >= max(1, len(leaves) // 4),
            "detail": f"薄弱节 {len(thin_open_close)} · 表格行 {tables}",
        },
        {
            "id": 6, "name": "措施可落到招标场景",
            "passed": not project_touch,
            "detail": ("偏套话：" + "、".join(project_touch[:5])) if project_touch else "可落地",
        },
        {
            "id": 7, "name": "规范书条款体现",
            "passed": not [row for row in missing if row.get("section_kind") == "spec"],
            "detail": "规范书映射无大面积缺口" if not [row for row in missing if row.get("section_kind") == "spec"] else "规范书条款未进目录",
        },
        {
            "id": 8, "name": "扣住项目核心",
            "passed": not commercial_noise,
            "detail": ("商务灌水：" + "、".join(commercial_noise[:5])) if commercial_noise else "未跑题",
        },
    ]
    failed = [rule for rule in rules if not rule["passed"]]
    review_titles = sorted({*scoring_thin, *thin_open_close, *project_touch, *commercial_noise})
    return {
        "rules": rules,
        "passed": not failed,
        "failed_count": len(failed),
        "review_titles": review_titles,
        "warning": ("质量八条未全部通过：" + "；".join(f"{r['id']}.{r['name']}" for r in failed)) if failed else "",
    }


def apply_quality_markers(content: str, review_titles: list[str], outline: dict) -> str:
    """给需核对的叶子节末尾补「需要核对」标记（已有则不重复）。"""
    if not review_titles:
        return content
    wanted = set(review_titles)
    lines = (content or "").splitlines()
    out: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        matched = HEADING.match(line.strip())
        out.append(line)
        index += 1
        if not matched:
            continue
        number, title = matched.group(1), matched.group(2).strip()
        leaf = next((item for item in _leaves(outline) if item.get("title") == title and item.get("number") == number), None)
        body_lines: list[str] = []
        while index < len(lines) and not HEADING.match(lines[index].strip()):
            body_lines.append(lines[index])
            index += 1
        out.extend(body_lines)
        if leaf and title in wanted and "需要核对" not in body_lines:
            out.append("需要核对")
    return "\n".join(out).rstrip() + ("\n" if content else "")
