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
            "score_refs": list(item.get("score_refs") or []),
            "mount_ids": list(item.get("mount_ids") or []),
            "constraint_ids": list(item.get("constraint_ids") or []),
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


def apply_technical_outline(state: Any, project_id: str, workflow: dict, model=None) -> None:
    """抽出条款后建 ResponseTask + 主题目录草稿。已写的正文不覆盖。"""
    if model is not None:
        workflow["tree_model"] = model
    try:
        _fill_technical_outline(state, project_id, workflow)
    finally:
        # 工作流整份进 JSON。模型对象留下去时，MySQL 编码会抛 TypeError。
        workflow.pop("tree_model", None)


def _fill_technical_outline(state: Any, project_id: str, workflow: dict) -> None:
    rows = _clauses(workflow)
    if not rows:
        workflow.pop("technical_outline", None)
        workflow.pop("response_tasks", None)
        return
    title = detect_title(workflow)
    from icg.domain.technical_digest_outline import plan_technical_outline
    plan = plan_technical_outline(workflow, model=workflow.get("tree_model"))
    headings = plan["headings"]
    if not headings:
        # 模型两阶段规划明确失败：绝不以空骨架覆盖已有目录草稿/正文，失败原因已落在 workflow 上。
        outline = workflow.get("technical_outline")
        if isinstance(outline, dict):
            outline["outline_source"] = workflow.get("outline_source") or outline.get("outline_source") or ""
            outline["tree_model_failed"] = bool(workflow.get("tree_model_failed"))
            outline["outline_reason"] = workflow.get("outline_reason") or ""
        return
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
        "outline_source": workflow.get("outline_source") or "rule",
        "tree_model_failed": bool(workflow.get("tree_model_failed")),
        "outline_reason": workflow.get("outline_reason") or "",
    }


def _leaf_titles(content: str) -> set[str]:
    found = set()
    for line in (content or "").splitlines():
        matched = HEADING_LINE.match(line.strip())
        if matched:
            found.add(matched.group(2).strip())
    return found


def _mountable_clauses(workflow: dict) -> list[dict]:
    from icg.domain.technical_constraint_context import is_business_clause
    from icg.domain.technical_clause_cleaning import row_excluded_from_technical
    return [
        row for row in _clauses(workflow)
        if row.get("clause_role") != "rejection_constraint"
        and row.get("section_kind") not in ("business", "qualification")
        and row.get("requirement_type") not in ("qualification", "rejection_item")
        and not is_business_clause(row)
        and not row.get("clause_fragment")
        and not row_excluded_from_technical(row)
    ]


def unassigned_pool(workflow: dict, headings: list[dict] | None = None) -> list[dict]:
    """返回当前目录中尚未挂载的评分点与技术要求（未挂载池）。"""
    items = headings if headings is not None else ((workflow.get("technical_outline") or {}).get("headings") or [])
    mounted: set[str] = set()
    for item in items:
        if item.get("requirement_id"):
            mounted.add(str(item["requirement_id"]))
        for rid in item.get("requirement_ids") or []:
            if rid:
                mounted.add(str(rid))
    out: list[dict] = []
    for row in _mountable_clauses(workflow):
        rid = str(row.get("id") or "")
        if not rid or rid in mounted:
            continue
        source = row.get("source") or {}
        out.append({
            "requirement_id": rid,
            "digest_id": str(row.get("digest_id") or ""),
            "kind": "scoring" if row.get("section_kind") == "scoring" else "tech",
            "text": str(row.get("extracted_summary") or row.get("text") or ""),
            "score_item": str(row.get("score_item") or ""),
            "score": row.get("score") if isinstance(row.get("score"), (int, float)) else None,
            "source_page": source.get("page") or row.get("page"),
        })
    return out


def uncovered(state: Any, project_id: str, workflow: dict) -> list[dict]:
    """目录正文和保存的条目一致时，改名仍算覆盖。正文被改掉后，以正文里的标题为准。"""
    outline = workflow.get("technical_outline") or {}
    chapter = state.chapters.get(outline.get("chapter_id") or "")
    content = chapter.content if chapter is not None else ""
    stored = (outline.get("text") or "").strip()
    clauses = _mountable_clauses(workflow)
    if content.strip() == stored and stored:
        linked: set[str] = set()
        for item in outline.get("headings") or []:
            if item.get("requirement_id"):
                linked.add(item["requirement_id"])
            for rid in item.get("requirement_ids") or []:
                linked.add(rid)
        return [row for row in clauses if row.get("id") not in linked]
    titles = _leaf_titles(content)
    return [row for row in clauses if (row.get("text") or "") not in titles]


def _sync_response_tasks(workflow: dict, headings: list[dict], chapter_id: str) -> None:
    """按最新目录节点同步维护 response_tasks：删掉的章节移出孤儿任务，新挂接章节补建任务。"""
    reqs = workflow.get("requirements") or {}
    existing_tasks = dict(workflow.get("response_tasks") or {})
    rejection_ids = [
        row["id"] for row in reqs.values()
        if row.get("is_rejection_criterion") and row.get("technical_clause")
        and row.get("requirement_type") != "qualification" and row.get("status") != "rejected"
    ]
    next_tasks: dict[str, dict] = {}
    used_task_ids: set[str] = set()

    for idx, item in enumerate(headings):
        is_leaf = idx + 1 >= len(headings) or headings[idx + 1]["level"] <= item["level"]
        rids = list(item.get("requirement_ids") or [])
        if not rids and item.get("requirement_id"):
            rids = [item["requirement_id"]]
        if not rids and not (is_leaf and item.get("task_id") in existing_tasks):
            item["task_id"] = None
            continue
        candidate_tid = str(item.get("task_id") or "").strip()
        if not candidate_tid or candidate_tid in used_task_ids:
            candidate_tid = new_id("task")
        used_task_ids.add(candidate_tid)
        item["task_id"] = candidate_tid
        item["requirement_ids"] = rids
        item["requirement_id"] = rids[0] if rids else None
        old = existing_tasks.get(candidate_tid)
        default_points = [
            str((reqs.get(rid) or {}).get("extracted_summary") or (reqs.get(rid) or {}).get("text") or "")[:60]
            for rid in rids if reqs.get(rid)
        ]
        if old is not None and set(old.get("requirement_ids") or []) == set(rids):
            next_tasks[candidate_tid] = {
                **old,
                "title": item["title"],
                "theme": item["title"],
                "outline_number": item["number"],
                "requirement_ids": rids,
                "chapter_id": chapter_id,
            }
        else:
            next_tasks[candidate_tid] = {
                "task_id": candidate_tid,
                "title": item["title"],
                "theme": item["title"],
                "requirement_ids": rids,
                "response_strategy": "point_by_point",
                "response_points": default_points,
                "digest_refs": sorted({
                    str((reqs.get(rid) or {}).get("digest_id") or "")
                    for rid in rids if (reqs.get(rid) or {}).get("digest_id")
                }),
                "rejection_requirement_ids": list(rejection_ids),
                "constraint_ids": [],
                "generation_status": "pending",
                "response_status": "not_started",
                "verification_status": "unchecked",
                "outline_number": item["number"],
                "chapter_id": chapter_id,
            }
    workflow["response_tasks"] = next_tasks


def replace_outline(state: Any, project_id: str, workflow: dict, headings: list[dict], title: str | None = None) -> Chapter:
    """按页面上的顺序和级别重排目录（1～4 级），同步更新 response_tasks 与未挂载池。已确认的目录改过之后要重新确认。"""
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
        requirement_ids: list[str] = []
        for rid in item.get("requirement_ids") or []:
            if rid in known and rid not in requirement_ids:
                requirement_ids.append(rid)
        if requirement_id and requirement_id not in requirement_ids:
            requirement_ids = [requirement_id, *requirement_ids]
        if not requirement_id and requirement_ids:
            requirement_id = requirement_ids[0]
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
    _sync_response_tasks(workflow, cleaned, chapter.id)
    if title and title.strip():
        chapter.title = title.strip()
    text = render(cleaned)
    # 已生成正文保留：目录重排/重挂不得静默丢弃节体（真机数据丢失根因）。
    # 按 task_id（优先）或标题从旧正文提取节体，注入新骨架对应标题行之后。
    from icg.domain.technical_volume import section_body
    previous_outline = workflow.get("technical_outline") or {}
    old_content = chapter.content or ""
    old_headings = {
        str(item.get("task_id") or ""): item
        for item in (previous_outline.get("headings") or [])
        if item.get("task_id")
    }
    old_by_title = {
        str(item.get("title") or ""): item
        for item in (previous_outline.get("headings") or [])
    }
    preserved: dict[str, str] = {}
    for item in cleaned:
        source = old_headings.get(str(item.get("task_id") or "")) or old_by_title.get(str(item.get("title") or ""))
        if not source:
            continue
        body = section_body(old_content, str(source.get("number") or ""), str(source.get("title") or ""))
        if body and body.strip() and body.strip() != "待补":
            preserved[str(item.get("number") or "") + " " + str(item.get("title") or "")] = body
    if preserved:
        lines = text.splitlines()
        merged: list[str] = []
        for line in lines:
            merged.append(line)
            body = preserved.get(line.strip())
            if body:
                merged.append(body)
                merged.append("")
        text = "\n".join(merged).strip() + "\n"
    chapter.content = text
    workflow["plan_confirmed"] = False
    previous = workflow.get("technical_outline") or {}
    workflow["technical_outline"] = {
        "title": chapter.title,
        "chapter_id": chapter.id,
        "text": text,
        "headings": cleaned,
        "outline_source": previous.get("outline_source") or workflow.get("outline_source") or "",
        "tree_model_failed": bool(previous.get("tree_model_failed") or workflow.get("tree_model_failed")),
        "outline_reason": previous.get("outline_reason") or workflow.get("outline_reason") or "",
    }
    return chapter


def confirm_directory(
    state: Any,
    principal: Any,
    project_id: str,
    workflow: dict,
    *,
    now: float,
    allow_unassigned: bool = False,
    auto_mount_unassigned: bool = False,
) -> Chapter:
    if not _clauses(workflow):
        raise DomainError(409, "REQUIREMENTS_EMPTY", "还没有抽出技术条款，不能确认目录。")
    outline = workflow.get("technical_outline") or {}
    chapter = state.chapters.get(outline.get("chapter_id") or "")
    if chapter is None:
        raise DomainError(409, "REQUIREMENT_NOT_READY", "目录还没有排出来。")

    pool = unassigned_pool(workflow, outline.get("headings") or [])
    if pool:
        if auto_mount_unassigned:
            from icg.domain.technical_digest_outline import FALLBACK_TITLE

            rids_to_mount = [item["requirement_id"] for item in pool]
            current_headings = [dict(h) for h in (outline.get("headings") or [])]
            target_idx = next(
                (i for i in range(len(current_headings) - 1, -1, -1) if current_headings[i].get("title") == FALLBACK_TITLE),
                None,
            )
            if target_idx is not None:
                merged = list(current_headings[target_idx].get("requirement_ids") or [])
                for rid in rids_to_mount:
                    if rid not in merged:
                        merged.append(rid)
                current_headings[target_idx]["requirement_ids"] = merged
                current_headings[target_idx]["requirement_id"] = merged[0] if merged else None
            else:
                current_headings.append({
                    "level": 1,
                    "title": FALLBACK_TITLE,
                    "requirement_id": rids_to_mount[0],
                    "task_id": None,
                    "requirement_ids": rids_to_mount,
                })
            chapter = replace_outline(state, project_id, workflow, current_headings, outline.get("title"))
            outline = workflow.get("technical_outline") or {}
        elif not allow_unassigned:
            raise DomainError(
                409,
                "MATRIX_MAPPING_MISSING",
                f"还有 {len(pool)} 条评分点或技术要求未挂载到目录，请先挂载到章节、自动归入「其他服务承诺」或确认忽略。",
                {"unassigned_requirements": pool},
            )

    from icg.domain.technical_fact_sheet import freeze_global_fact_sheet

    freeze_global_fact_sheet(state, project_id, workflow, now=now)
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


def public_rag_audit(workflow: dict) -> list[dict]:
    return [item for item in (workflow.get("technical_rag_audit") or []) if isinstance(item, dict)]


def public_tender_index(raw: Any) -> dict[str, Any] | None:
    """工作区只带索引名和片数。页正文留在 workflow，不进响应。"""
    if not isinstance(raw, dict):
        return None
    chunks = raw.get("chunks") if isinstance(raw.get("chunks"), list) else []
    count = raw.get("chunk_count")
    if not isinstance(count, int) or isinstance(count, bool):
        count = len(chunks)
    return {
        "backend": str(raw.get("backend") or ""),
        "dataset_name": str(raw.get("dataset_name") or ""),
        "chunk_count": count,
        "skip_reason": str(raw.get("skip_reason") or ""),
    }


def writer_model_label(stored: Any) -> dict[str, Any] | None:
    """读出名称和本地/真实标记。不把 provider 写回 workflow。"""
    if isinstance(stored, dict):
        name = str(stored.get("name") or stored.get("model") or "").strip()
        is_real = stored.get("is_real", stored.get("is_real_model", False))
        is_local = stored.get("is_local", stored.get("is_local_model", False))
    elif stored is None:
        return None
    else:
        name = str(
            getattr(stored, "display_name", "") or getattr(stored, "model", "") or getattr(stored, "name", "") or ""
        ).strip()
        is_real = bool(getattr(stored, "is_real_model", False) or getattr(stored, "is_real", False))
        is_local = bool(getattr(stored, "is_local", False) or getattr(stored, "is_local_model", False))
    if not name:
        return None
    return {"name": name, "is_real": bool(is_real), "is_local": bool(is_local)}


def workspace_fields(state: Any, project_id: str, workflow: dict) -> dict[str, Any]:
    from icg.domain.technical_sources import technical_only
    from icg.domain.technical_fact_sheet import build_global_fact_sheet
    if not technical_only(state, project_id):
        return {
            "plan_confirmed": bool(workflow.get("parse_confirmed")) and plan_is_current(state, project_id),
            "technical_outline": None,
            "global_fact_sheet": build_global_fact_sheet(state, project_id, workflow),
            "technical_deviation_note": "",
            "technical_needs_review": [],
            "extract_degraded": False,
            "extract_timeout_count": 0,
            "extract_pages_read": 0,
            "outline_source": "",
            "tree_model_failed": False,
            "outline_reason": "",
        }
    stored = workflow.get("technical_outline")
    outline = None
    missing: list[str] = []
    if stored:
        pool = unassigned_pool(workflow, stored.get("headings") or [])
        missing = [row["id"] for row in uncovered(state, project_id, workflow)]
        outline = {
            "title": stored.get("title") or "",
            "chapter_id": stored.get("chapter_id") or "",
            "headings": list(stored.get("headings") or []),
            "missing": missing,
            "unassigned_requirements": pool,
            "outline_source": stored.get("outline_source") or workflow.get("outline_source") or "",
            "tree_model_failed": bool(stored.get("tree_model_failed") or workflow.get("tree_model_failed")),
            "outline_reason": stored.get("outline_reason") or workflow.get("outline_reason") or "",
        }
    confirmed = bool(workflow.get("plan_confirmed")) and outline is not None
    from icg.domain.technical_volume import deviation_note, review_titles
    from icg.domain.technical_rag import dataset_presence
    from icg.domain.technical_quality import evaluate_quality
    from icg.domain.technical_fact_sheet import build_global_fact_sheet
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
        "global_fact_sheet": build_global_fact_sheet(state, project_id, workflow),
        "technical_deviation_note": deviation_note(workflow) if stored else "",
        "technical_needs_review": review,
        "technical_kb": dataset_presence(state, company_id, workflow),
        "technical_quality": quality,
        "response_tasks": list((workflow.get("response_tasks") or {}).values()) if stored else [],
        "coverage_rows": coverage_rows(workflow, outline, content) if stored else [],
        "tender_digest": workflow.get("tender_digest"),
        "plan_validation": (stored or {}).get("plan_validation") or workflow.get("plan_validation"),
        "technical_rag_audit": public_rag_audit(workflow),
        "tender_index": public_tender_index(workflow.get("tender_index")),
        "writer_model": writer_model_label(workflow.get("writer_model")),
        "constraint_check": workflow.get("constraint_check"),
        "extract_degraded": bool(workflow.get("extract_degraded")),
        "chapter_summaries": dict(workflow.get("chapter_summaries") or {}),
        "technical_model_error": str(workflow.get("technical_model_error") or ""),
        "extract_timeout_count": int(workflow.get("extract_timeout_count") or 0),
        "extract_pages_read": int((workflow.get("technical_extract_model") or {}).get("pages_read") or 0),
        "outline_source": (stored or {}).get("outline_source") or workflow.get("outline_source") or "",
        "tree_model_failed": bool((stored or {}).get("tree_model_failed") or workflow.get("tree_model_failed")),
        "outline_reason": (stored or {}).get("outline_reason") or workflow.get("outline_reason") or "",
    }


def plan_result(state: Any, project_id: str, workflow: dict, chapter: Chapter, principal: Any, summary) -> dict:
    return {
        "plan_confirmed": True,
        "writing_plan": public_plan(workflow, state, project_id),
        "chapters": [summary(state, workflow, chapter, principal.user.id)],
    }
