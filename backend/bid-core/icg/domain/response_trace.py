# 为什么有这个文件：导出内部用“响应追溯表”Excel（PRD v1.8 §5.9.1 规则 12，APP-M2-T201）。
# 它解决什么问题：内部审核时要一眼看出每条招标条款在哪个文件第几页、怎么响应、落在哪个分册哪一章哪一段、
# 引了哪些证据（版本）与知识片段、谁负责、谁确认。只供内部审核，不进入投标文件，任何时候都可导出。
# 分册负责人只导出本册；项目负责人导出全部。

from __future__ import annotations

import re
from typing import Any

from .scope_rules import BREAK, normalize

VOLUME_NAMES = {"technical": "技术分册", "business": "商务分册"}
CATEGORY_NAMES = {"mandatory": "实质性条款", "qualification": "资格要求", "technical": "技术服务", "business": "商务要求",
                  "commercial": "商务要求", "sla": "SLA 要求", "star": "星号条款", "disqualification": "废标条款",
                  "scoring": "评分要点", "score": "评分要点", "other": "其他要求"}
STATUS_NAMES = {"confirmed": "已确认", "pending": "待确认", "rejected": "已忽略"}
_CITATION = re.compile(r"\[(证|片)(?::([^\]]+))?\]")


def _grams(text: str) -> set[str]:
    value = normalize(text).replace(BREAK, "")
    return {value[i:i + 2] for i in range(len(value) - 1)}


def best_paragraph(content: str, query: str) -> tuple[int | None, str]:
    """按字面重合找条款在本章最可能对应的段落（1 起）；重合太低返回 None（交 R30 判定）。"""
    want = _grams(query)
    best, best_score, best_text = None, 0.0, ""
    for index, paragraph in enumerate((content or "").split("\n")):
        text = paragraph.strip()
        if not text or text.startswith("#"):
            continue
        own = _grams(text)
        if not own or not want:
            continue
        score = len(own & want) / min(len(own), len(want))
        if score > best_score:
            best, best_score, best_text = index + 1, score, text
    return (best, best_text) if best_score >= 0.2 else (None, "")


def build_trace_rows(state: Any, project: Any, workflow: dict, volumes: set[str]) -> list[list[object]]:
    files = workflow.get("files") or {}
    chapters = {c.id: c for c in state.chapters.values() if c.project_id == project.id}
    order = {cid: i + 1 for i, cid in enumerate(workflow.get("chapter_order") or [])}
    owners = (state.project_teams.get(project.id) or {}).get("owners", {})
    names = {aid: a.name for aid, a in state.accounts.items()}
    rows: list[list[object]] = []
    requirements = sorted((workflow.get("requirements") or {}).values(),
                          key=lambda r: (r.get("volume", ""), (r.get("source") or {}).get("page") or 0))
    for number, req in enumerate((r for r in requirements if r.get("volume") in volumes), start=1):
        source = req.get("source") or {}
        file = files.get(source.get("file_id")) or {}
        chapter = chapters.get(req.get("chapter_id"))
        paragraph, text = best_paragraph(chapter.content if chapter else "", f"{req.get('text', '')}{req.get('response', '')}")
        evidence = []
        for eid in req.get("evidence_ids") or []:
            item = state.library.get(eid) or {}
            evidence.append(f"{item.get('name', eid)}（v{item.get('revision', '?')}）")
        snippets = sorted({ref for kind, ref in _CITATION.findall(text) if kind == "片" and ref})
        cited = sorted({ref for kind, ref in _CITATION.findall(text) if kind == "证" and ref})
        owner_id = (chapter.assignee_id if chapter and chapter.assignee_id else owners.get(req.get("volume")))
        rows.append([
            number,
            str(req.get("text", "")),
            file.get("filename") or "招标文件",
            source.get("page") or "",
            CATEGORY_NAMES.get(req.get("category"), req.get("category") or ""),
            str(req.get("response", "")),
            VOLUME_NAMES.get(req.get("volume"), req.get("volume") or ""),
            (f"{order.get(chapter.id, '')} {chapter.title}".strip() if chapter else "未对应章节"),
            paragraph or "",
            "；".join(evidence) + (f"；正文引用 [证] {', '.join(cited)}" if cited else ""),
            "、".join(snippets),
            names.get(owner_id, owner_id or ""),
            req.get("confirmed_by_name") or "",
            STATUS_NAMES.get(req.get("status"), req.get("status") or ""),
        ])
    return rows


HEADER = ["序号", "招标条款", "所属文件", "页码", "条款类别", "响应方式与要点", "所在分册", "对应章节", "段落",
          "证据（版本）", "知识片段来源", "负责人", "确认人", "条款状态"]


def trace_sheets(project: Any, rows: list[list[object]], *, scope: str, generated_at: str) -> list[dict]:
    head = [
        [f"响应追溯表（内部用，不进入投标文件）· {project.name}"],
        [f"范围：{scope} · 生成：{generated_at} · 共 {len(rows)} 条"],
        [],
        HEADER,
    ]
    return [{"name": "响应追溯表", "rows": head + rows, "header_rows": 4,
             "widths": [6, 48, 18, 6, 12, 40, 10, 22, 6, 28, 18, 12, 12, 10]}]
