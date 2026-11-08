# 为什么有这个文件：技术分册抽出条款后，排成可确认的动态目录（1～4 级）。
# 它解决什么问题：按本次招标条款与规范编号拟草稿，不写死教程六块/单章硬模板；确认目录是生成前唯一用户闸门。

from __future__ import annotations

import re
from typing import Any

from icg.domain.domain import Chapter, DomainError, iso_time, new_id
from icg.domain.generation_context import plan_is_current, public_plan, writing_source_fingerprint

TITLE_LINE = re.compile(r"^(?:第[0-9一二三四五六七八九十]+[章节篇]\s*)?(技术服务方案|服务方案|技术方案)$")
HEADING_LINE = re.compile(r"^(\d+(?:\.\d+)*)\s+(\S.*)$")
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


def _sort_key(row: dict) -> tuple:
    text = row.get("text") or ""
    early = next((index for index, word in enumerate(EARLY) if word in text), len(EARLY))
    kind = 0 if row.get("section_kind") == "scoring" else 1
    return (early, kind, text)


def _spec_number(row: dict) -> str:
    path = row.get("section_path") or []
    return str(path[0]).strip() if path and path[0] else ""


def _number_key(value: str) -> tuple:
    parts = []
    for piece in value.split("."):
        try:
            parts.append((0, int(piece)))
        except ValueError:
            parts.append((1, piece))
    return tuple(parts)


def assign_numbers(items: list[dict]) -> list[dict]:
    """按 1～4 级顺序重新编号；跳级时自动补齐中间计数。"""
    counters = [0, 0, 0, 0]
    cleaned: list[dict] = []
    for item in items:
        level = int(item.get("level") or 0)
        if level not in (1, 2, 3, 4):
            raise DomainError(422, "VALIDATION_ERROR", "目录级别只能是一至四级。")
        for ancestor in range(level - 1):
            if counters[ancestor] == 0:
                counters[ancestor] = 1
        counters[level - 1] += 1
        for deeper in range(level, 4):
            counters[deeper] = 0
        number = ".".join(str(counters[index]) for index in range(level))
        cleaned.append({
            "level": level,
            "number": number,
            "title": item["title"],
            "requirement_id": item.get("requirement_id"),
            "task_id": item.get("task_id"),
            "requirement_ids": list(item.get("requirement_ids") or ([] if not item.get("requirement_id") else [item["requirement_id"]])),
        })
    return cleaned


def arrange(rows: list[dict]) -> list[dict]:
    """动态 1～4 级目录：规范编号按树展开，评分主观分作叶子；不写死教程六块。"""
    numbered = [row for row in rows if _spec_number(row)]
    scoring = [row for row in rows if not _spec_number(row)]
    drafted: list[dict] = []
    seen_ancestors: set[str] = set()

    if numbered:
        drafted.append({"level": 1, "title": "技术规范响应", "requirement_id": None})
        for row in sorted(numbered, key=lambda item: _number_key(_spec_number(item))):
            number = _spec_number(row)
            parts = number.split(".")
            for depth in range(1, len(parts)):
                ancestor = ".".join(parts[:depth])
                if ancestor in seen_ancestors:
                    continue
                seen_ancestors.add(ancestor)
                drafted.append({
                    "level": min(depth + 1, 3),
                    "title": ancestor,
                    "requirement_id": None,
                })
            drafted.append({
                "level": min(len(parts) + 1, 4),
                "title": row.get("text") or number,
                "requirement_id": row.get("id"),
            })
            seen_ancestors.add(number)

    if scoring:
        drafted.append({
            "level": 1,
            "title": "评分主观分响应",
            "requirement_id": None,
        })
        for row in sorted(scoring, key=_sort_key):
            drafted.append({
                "level": 2,
                "title": row.get("text") or "",
                "requirement_id": row.get("id"),
            })

    if not drafted:
        return []
    return assign_numbers(drafted)


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
    """抽出条款后建 ResponseTask + 主题目录草稿。已写的正文不覆盖。"""
    rows = _clauses(workflow)
    if not rows:
        workflow.pop("technical_outline", None)
        workflow.pop("response_tasks", None)
        return
    title = detect_title(workflow)
    from icg.domain.technical_response_plan import apply_response_plan
    plan = apply_response_plan(workflow)
    headings = plan["headings"]
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
    for task in (workflow.get("response_tasks") or {}).values():
        task["chapter_id"] = chapter.id
    workflow["chapter_order"] = [chapter.id]
    workflow["technical_outline"] = {
        "title": title,
        "chapter_id": chapter.id,
        "text": text,
        "headings": headings,
        "plan_validation": plan["validation"],
    }


def _leaf_titles(content: str) -> set[str]:
    found = set()
    for line in (content or "").splitlines():
        matched = HEADING_LINE.match(line.strip())
        if matched:
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
        linked: set[str] = set()
        for item in outline.get("headings") or []:
            if item.get("requirement_id"):
                linked.add(item["requirement_id"])
            for rid in item.get("requirement_ids") or []:
                linked.add(rid)
        titles = {str(item.get("title") or "").strip() for item in outline.get("headings") or []}
        return [row for row in clauses if row.get("id") not in linked and (row.get("text") or "") not in titles]
    titles = _leaf_titles(content)
    return [row for row in clauses if (row.get("text") or "") not in titles]


def replace_outline(state: Any, project_id: str, workflow: dict, headings: list[dict], title: str | None = None) -> Chapter:
    """按页面上的顺序和级别重排目录（1～4 级）。已确认的目录改过之后要重新确认。"""
    outline = workflow.get("technical_outline") or {}
    chapter = state.chapters.get(outline.get("chapter_id") or "")
    if chapter is None:
        raise DomainError(409, "REQUIREMENT_NOT_READY", "目录还没有排出来。")
    known = {row.get("id") for row in _clauses(workflow)}
    drafted: list[dict] = []
    for item in headings:
        text = str(item.get("title") or "").strip()
        if not text:
            raise DomainError(422, "VALIDATION_ERROR", "目录标题不能为空。")
        level = int(item.get("level") or 0)
        if level not in (1, 2, 3, 4):
            raise DomainError(422, "VALIDATION_ERROR", "目录级别只能是一至四级。")
        requirement_id = item.get("requirement_id") or None
        if requirement_id not in known:
            requirement_id = None
        requirement_ids = [rid for rid in (item.get("requirement_ids") or []) if rid in known]
        if requirement_id and requirement_id not in requirement_ids:
            requirement_ids = [requirement_id, *requirement_ids]
        drafted.append({
            "level": level,
            "title": text,
            "requirement_id": requirement_id,
            "task_id": item.get("task_id"),
            "requirement_ids": requirement_ids,
        })
    if not drafted:
        raise DomainError(422, "VALIDATION_ERROR", "目录至少留一条。")
    cleaned = assign_numbers(drafted)
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
    workflow["outline_revision"] = int(workflow.get("outline_revision") or 0) + 1
    workflow["writing_plan"] = {
        "confirmed_by": principal.user.id,
        "confirmed_by_name": principal.user.name,
        "confirmed_at": stamped,
        "chapters": {chapter.id: saved},
    }
    # 确认时冻结节点 ↔ 挂接要求快照，供生成阶段使用。
    workflow["technical_outline_snapshot"] = {
        "title": outline.get("title") or chapter.title,
        "chapter_id": chapter.id,
        "headings": list(outline.get("headings") or []),
        "confirmed_at": stamped,
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
    from icg.domain.technical_rag import dataset_presence
    from icg.domain.technical_quality import evaluate_quality
    content = ""
    if stored:
        chapter = state.chapters.get(stored.get("chapter_id") or "")
        content = chapter.content if chapter is not None else ""
    company_id = getattr(state.projects.get(project_id), "company_id", "") or ""
    quality = evaluate_quality(workflow, content) if stored and content else workflow.get("technical_quality")
    review = list(review_titles(workflow, content) if stored else [])
    if quality:
        for title in quality.get("review_titles") or []:
            if title and title not in review:
                review.append(title)
    from icg.domain.technical_response_plan import coverage_rows
    return {
        "plan_confirmed": confirmed,
        "technical_outline": outline,
        "technical_deviation_note": deviation_note(workflow) if stored else "",
        "technical_needs_review": review,
        "technical_kb": dataset_presence(state, company_id),
        "technical_quality": quality,
        "response_tasks": list((workflow.get("response_tasks") or {}).values()) if stored else [],
        "coverage_rows": coverage_rows(workflow, outline) if stored else [],
        "plan_validation": (stored or {}).get("plan_validation") or workflow.get("plan_validation"),
    }


def plan_result(state: Any, project_id: str, workflow: dict, chapter: Chapter, principal: Any, summary) -> dict:
    return {
        "plan_confirmed": True,
        "writing_plan": public_plan(workflow, state, project_id),
        "chapters": [summary(state, workflow, chapter, principal.user.id)],
    }
