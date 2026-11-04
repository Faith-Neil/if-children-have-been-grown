# 为什么有这个文件：技术分册抽出条款后，排成一章服务方案目录。
# 它解决什么问题：二级、三级写在同一章里，评分要点和规格书条款都有标题才能确认。创建项目时的「技术方案」不是这份目录。

from __future__ import annotations

import re
from typing import Any

from icg.domain.domain import Chapter, DomainError, iso_time, new_id
from icg.domain.generation_context import plan_is_current, public_plan, writing_source_fingerprint

TITLE_LINE = re.compile(r"^(?:第[0-9一二三四五六七八九十]+[章节篇]\s*)?(技术服务方案|服务方案|技术方案)$")
HEADING_LINE = re.compile(r"^(\d+(?:\.\d+)*)\s+(\S.*)$")
BUCKETS = (
    ("服务方式", ("标准服务", "现场服务", "主动式服务", "主动式", "服务方式", "远程服务")),
    ("质量管理", ("质量管理", "质量考核", "考核")),
    ("实施计划", ("实施计划", "进度", "工期")),
    ("应急", ("应急",)),
    ("培训", ("知识转移", "培训")),
    ("保密", ("保密",)),
    ("质保", ("质保", "售后", "保修")),
)
BUCKET_ORDER = ("服务方式", "服务内容", "质量管理", "实施计划", "应急", "培训", "保密", "质保")
EARLY = ("健康检查", "故障", "巡检", "例行", "升级", "性能")


def detect_title(workflow: dict) -> str:
    """招标文件单独成行的标题优先。没有时用「服务方案」。"""
    for record in (workflow.get("files") or {}).values():
        for page in record.get("pages") or []:
            text = page if isinstance(page, str) else str(page.get("text") or "")
            for line in text.splitlines():
                matched = TITLE_LINE.match(line.strip())
                if matched:
                    return matched.group(1)
    return "服务方案"


def _bucket(text: str) -> str:
    for name, words in BUCKETS:
        if any(word in text for word in words):
            return name
    return "服务内容"


def _sort_key(row: dict) -> tuple:
    text = row.get("text") or ""
    early = next((index for index, word in enumerate(EARLY) if word in text), len(EARLY))
    kind = 0 if row.get("section_kind") == "scoring" else 1
    return (early, kind, text)


def arrange(rows: list[dict]) -> list[dict]:
    """一条条款一个三级标题。没有对应条款的二级块不补。"""
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(_bucket(row.get("text") or ""), []).append(row)
    headings: list[dict] = []
    section = 0
    for name in BUCKET_ORDER:
        items = grouped.get(name) or []
        if not items:
            continue
        section += 1
        number = f"1.{section}"
        headings.append({"level": 2, "number": number, "title": name, "requirement_id": None})
        for index, row in enumerate(sorted(items, key=_sort_key), start=1):
            headings.append({
                "level": 3,
                "number": f"{number}.{index}",
                "title": row.get("text") or "",
                "requirement_id": row.get("id"),
            })
    return headings


def render(headings: list[dict]) -> str:
    lines = [f"{item['number']} {item['title']}" for item in headings]
    return ("\n".join(lines) + "\n") if lines else ""


def _clauses(workflow: dict) -> list[dict]:
    return [
        row for row in (workflow.get("requirements") or {}).values()
        if row.get("technical_clause") and row.get("status") != "rejected"
    ]


def _chapter(state: Any, project_id: str, title: str) -> Chapter:
    chapters = [chapter for chapter in state.chapters.values()
                if chapter.project_id == project_id and chapter.volume == "technical"]
    if chapters:
        return chapters[0]
    chapter = Chapter(new_id("chapter"), project_id, title, "technical", "")
    state.chapters[chapter.id] = chapter
    return chapter


def apply_technical_outline(state: Any, project_id: str, workflow: dict) -> None:
    """抽出条款后改成一章。空的「技术方案」会被改名，已写的正文不覆盖。"""
    rows = _clauses(workflow)
    if not rows:
        workflow.pop("technical_outline", None)
        return
    title = detect_title(workflow)
    headings = arrange(rows)
    text = render(headings)
    chapter = _chapter(state, project_id, title)
    previous = (workflow.get("technical_outline") or {}).get("text") or ""
    current = chapter.content or ""
    if current.strip() and current != previous:
        pending = list(workflow.get("needs_regeneration") or [])
        if chapter.id not in pending:
            pending.append(chapter.id)
        workflow["needs_regeneration"] = pending
    else:
        chapter.content = text
    chapter.title = title
    for row in rows:
        row["chapter_id"] = chapter.id
    workflow["chapter_order"] = [chapter.id]
    workflow["technical_outline"] = {
        "title": title,
        "chapter_id": chapter.id,
        "text": text,
        "headings": headings,
    }


def _level3(content: str) -> set[str]:
    found = set()
    for line in (content or "").splitlines():
        matched = HEADING_LINE.match(line.strip())
        if matched and matched.group(1).count(".") >= 2:
            found.add(matched.group(2).strip())
    return found


def uncovered(state: Any, project_id: str, workflow: dict) -> list[dict]:
    """目录正文和保存的条目一致时，改名仍算覆盖。正文被改掉后，以正文里的标题为准。"""
    outline = workflow.get("technical_outline") or {}
    chapter = state.chapters.get(outline.get("chapter_id") or "")
    content = chapter.content if chapter is not None else ""
    stored = (outline.get("text") or "").strip()
    clauses = _clauses(workflow)
    if content.strip() == stored and stored:
        linked = {item.get("requirement_id") for item in outline.get("headings") or [] if item.get("requirement_id")}
        titles = {str(item.get("title") or "").strip() for item in outline.get("headings") or []}
        return [row for row in clauses if row.get("id") not in linked and (row.get("text") or "") not in titles]
    titles = _level3(content)
    return [row for row in clauses if (row.get("text") or "") not in titles]


def replace_outline(state: Any, project_id: str, workflow: dict, headings: list[dict], title: str | None = None) -> Chapter:
    """按页面上的顺序和级别重排目录，写回这一章。已确认的目录改过之后要重新确认。"""
    outline = workflow.get("technical_outline") or {}
    chapter = state.chapters.get(outline.get("chapter_id") or "")
    if chapter is None:
        raise DomainError(409, "REQUIREMENT_NOT_READY", "目录还没有排出来。")
    known = {row.get("id") for row in _clauses(workflow)}
    cleaned: list[dict] = []
    section = 0
    sub = 0
    for item in headings:
        text = str(item.get("title") or "").strip()
        if not text:
            raise DomainError(422, "VALIDATION_ERROR", "目录标题不能为空。")
        level = int(item.get("level") or 0)
        if level not in (2, 3):
            raise DomainError(422, "VALIDATION_ERROR", "目录级别只能是二级或三级。")
        requirement_id = item.get("requirement_id") or None
        if requirement_id not in known:
            requirement_id = None
        if level == 2:
            section += 1
            sub = 0
            number = f"1.{section}"
        else:
            if section == 0:
                section = 1
            sub += 1
            number = f"1.{section}.{sub}"
        cleaned.append({"level": level, "number": number, "title": text, "requirement_id": requirement_id})
    if not cleaned:
        raise DomainError(422, "VALIDATION_ERROR", "目录至少留一条。")
    if title and title.strip():
        chapter.title = title.strip()
    text = render(cleaned)
    chapter.content = text
    workflow["plan_confirmed"] = False
    workflow["technical_outline"] = {
        "title": chapter.title,
        "chapter_id": chapter.id,
        "text": text,
        "headings": cleaned,
    }
    return chapter


def confirm_directory(state: Any, principal: Any, project_id: str, workflow: dict, *, now: float) -> Chapter:
    if not _clauses(workflow):
        raise DomainError(409, "REQUIREMENTS_EMPTY", "还没有抽出技术条款，不能确认目录。")
    outline = workflow.get("technical_outline") or {}
    chapter = state.chapters.get(outline.get("chapter_id") or "")
    if chapter is None:
        raise DomainError(409, "REQUIREMENT_NOT_READY", "目录还没有排出来。")
    stamped = iso_time(now)
    fingerprint = writing_source_fingerprint(state, project_id, chapter.id)
    saved = {
        "id": chapter.id, "fact_ids": [], "writing_points": "", "target_length": None,
        "confirmed_by": principal.user.id, "confirmed_by_name": principal.user.name,
        "confirmed_at": stamped, "confirmed_input_fingerprint": fingerprint,
        "confirmation_pending": False,
    }
    workflow["plan_confirmed"] = True
    workflow["writing_plan"] = {
        "confirmed_by": principal.user.id,
        "confirmed_by_name": principal.user.name,
        "confirmed_at": stamped,
        "chapters": {chapter.id: saved},
    }
    return chapter


def workspace_fields(state: Any, project_id: str, workflow: dict) -> dict[str, Any]:
    from icg.domain.technical_sources import technical_only
    if not technical_only(state, project_id):
        return {
            "plan_confirmed": bool(workflow.get("parse_confirmed")) and plan_is_current(state, project_id),
            "technical_outline": None,
            "technical_deviation_note": "",
            "technical_needs_review": [],
        }
    stored = workflow.get("technical_outline")
    outline = None
    missing: list[str] = []
    if stored:
        missing = [row["id"] for row in uncovered(state, project_id, workflow)]
        outline = {
            "title": stored.get("title") or "",
            "chapter_id": stored.get("chapter_id") or "",
            "headings": list(stored.get("headings") or []),
            "missing": missing,
        }
    confirmed = bool(workflow.get("plan_confirmed")) and outline is not None
    from icg.domain.technical_volume import deviation_note, review_titles
    content = ""
    if stored:
        chapter = state.chapters.get(stored.get("chapter_id") or "")
        content = chapter.content if chapter is not None else ""
    return {
        "plan_confirmed": confirmed,
        "technical_outline": outline,
        "technical_deviation_note": deviation_note(workflow) if stored else "",
        "technical_needs_review": review_titles(workflow, content) if stored else [],
    }


def plan_result(state: Any, project_id: str, workflow: dict, chapter: Chapter, principal: Any, summary) -> dict:
    return {
        "plan_confirmed": True,
        "writing_plan": public_plan(workflow, state, project_id),
        "chapters": [summary(state, workflow, chapter, principal.user.id)],
    }
