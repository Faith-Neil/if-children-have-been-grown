# 为什么有这个文件：把招标要求库 enrich 成 ResponseTask，并排出主题目录与计划校验。
# 它解决什么问题：禁止「一条要求原文 = 一节目录标题」；建立 要求→任务→章节 映射。

from __future__ import annotations

import re
from typing import Any

from icg.domain.domain import new_id

THEME_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("运维保障与巡检", ("巡检", "健康检查", "例行", "故障", "宕机", "监控")),
    ("现场与远程支持", ("现场", "驻场", "远程", "电话支持", "7*", "7×", "响应时间")),
    ("备份恢复与容灾", ("备份", "恢复", "容灾", "切换")),
    ("性能与容量", ("性能", "容量", "扩容", "调优")),
    ("安全与合规", ("安全", "保密", "等保", "审计", "权限")),
    ("实施与交付", ("实施", "部署", "交付", "上线", "迁移")),
    ("验收与培训", ("验收", "培训", "文档")),
    ("原厂与维保服务", ("原厂", "维保", "保修", "备件")),
    ("方案设计", ("方案", "设计", "架构")),
]

TYPE_MAP = {
    "scoring": "technical_service",
    "spec": "technical_parameter",
}

RISK_WORDS = ("废标", "无效", "否决", "必须", "应当", "★", "*")


def clip_summary(text: str, limit: int = 48) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if len(cleaned) <= limit:
        return cleaned
    cut = cleaned[: limit - 1]
    for sep in ("。", "；", "，", "、", " "):
        pos = cut.rfind(sep)
        if pos >= 12:
            return cut[:pos]
    return cut + "…"


def short_chapter_title(text: str, *, fallback: str = "技术响应") -> str:
    """目录用短标题：去掉编号前缀与过长原文。"""
    raw = re.sub(r"\s+", "", (text or "").strip())
    raw = re.sub(r"^(?:\d+(?:\.\d+)*|[一二三四五六七八九十]+[、.．]|（\d+）|\(\d+\))", "", raw)
    if not raw:
        return fallback
    if len(raw) <= 16:
        return raw
    return clip_summary(raw, 16)


def infer_requirement_type(row: dict) -> str:
    if row.get("requirement_type"):
        return str(row["requirement_type"])
    kind = row.get("section_kind") or ""
    text = str(row.get("text") or "")
    if row.get("category") in ("disqualification", "star") or any(word in text for word in ("废标", "否决")):
        return "rejection_item"
    if "资质" in text or "证书" in text:
        return "qualification"
    return TYPE_MAP.get(kind, "other_constraint")


def enrich_requirement(row: dict) -> dict:
    """补齐架构字段；不覆盖人工已确认状态。"""
    text = str(row.get("text") or "")
    requirement_type = infer_requirement_type(row)
    is_rejection = bool(
        row.get("is_rejection_criterion")
        or requirement_type == "rejection_item"
        or row.get("category") in ("disqualification", "star")
        or "废标" in text
    )
    risk = row.get("risk_level")
    if not risk:
        if is_rejection:
            risk = "critical"
        elif any(word in text for word in ("必须", "应当", "★")):
            risk = "high"
        else:
            risk = "medium"
    row["requirement_type"] = requirement_type
    row["risk_level"] = risk
    row["is_rejection_criterion"] = is_rejection
    row["criticality"] = bool(row.get("criticality") or is_rejection or risk in ("critical", "high"))
    row["extracted_summary"] = row.get("extracted_summary") or clip_summary(text, 80)
    row["response_mode"] = row.get("response_mode") or "explicit"
    row["review_status"] = row.get("review_status") or row.get("status") or "pending"
    return row


def _theme_for(row: dict) -> str:
    text = str(row.get("text") or "")
    for name, words in THEME_RULES:
        if any(word in text for word in words):
            return name
    path = row.get("section_path") or []
    if path:
        return f"规范 {path[0]}"
    if row.get("section_kind") == "scoring":
        return "评分响应"
    return "综合技术响应"


def build_response_tasks(rows: list[dict]) -> list[dict]:
    """多条要求可合并进同一主题任务；任务标题是短章节名。"""
    buckets: dict[str, list[dict]] = {}
    for row in rows:
        enrich_requirement(row)
        # 资格/商务类废标不进技术任务正文，但仍保留在要求库。
        if row.get("requirement_type") == "qualification" and not row.get("technical_clause"):
            continue
        if row.get("volume") == "business" and not row.get("technical_clause"):
            continue
        theme = _theme_for(row)
        buckets.setdefault(theme, []).append(row)

    tasks: list[dict] = []
    for theme, members in buckets.items():
        if len(members) == 1:
            title = short_chapter_title(members[0].get("extracted_summary") or members[0].get("text") or theme, fallback=theme)
        else:
            title = theme
        tech_rejection = [
            item["id"] for item in members
            if item.get("is_rejection_criterion") and item.get("requirement_type") not in ("qualification",)
        ]
        tasks.append({
            "task_id": new_id("task"),
            "title": title,
            "theme": theme,
            "requirement_ids": [item["id"] for item in members],
            "response_strategy": "point_by_point",
            "response_points": [item.get("extracted_summary") or clip_summary(item.get("text") or "") for item in members],
            "rejection_requirement_ids": tech_rejection,
            "generation_status": "pending",
            "response_status": "not_started",
            "verification_status": "unchecked",
            "outline_number": None,
            "chapter_id": None,
        })
    return tasks


def arrange_from_tasks(tasks: list[dict]) -> list[dict]:
    """主题一级 + 任务叶子；标题不用条款原文。"""
    if not tasks:
        return []
    by_theme: dict[str, list[dict]] = {}
    for task in tasks:
        by_theme.setdefault(task.get("theme") or "综合技术响应", []).append(task)
    drafted: list[dict] = []
    for theme, group in by_theme.items():
        drafted.append({"level": 1, "title": theme, "requirement_id": None, "task_id": None})
        for task in group:
            drafted.append({
                "level": 2,
                "title": task["title"],
                "requirement_id": (task.get("requirement_ids") or [None])[0],
                "task_id": task["task_id"],
                "requirement_ids": list(task.get("requirement_ids") or []),
            })
    from icg.domain.technical_outline import assign_numbers
    numbered = assign_numbers(drafted)
    id_to_number = {row["task_id"]: row["number"] for row in numbered if row.get("task_id")}
    for task in tasks:
        task["outline_number"] = id_to_number.get(task["task_id"])
    return numbered


def validate_plan(requirements: list[dict], tasks: list[dict], headings: list[dict]) -> dict[str, Any]:
    """确定性计划校验；不通过则 callers 可回退重建任务。"""
    req_ids = {row["id"] for row in requirements if row.get("technical_clause") and row.get("status") != "rejected"}
    mapped = {rid for task in tasks for rid in (task.get("requirement_ids") or [])}
    unmapped = sorted(req_ids - mapped)
    leaf_tasks = {row.get("task_id") for row in headings if row.get("task_id")}
    orphan_tasks = [task["task_id"] for task in tasks if task["task_id"] not in leaf_tasks]
    tech_rejection = [
        row["id"] for row in requirements
        if row.get("is_rejection_criterion")
        and row.get("technical_clause")
        and row.get("requirement_type") != "qualification"
        and row.get("status") != "rejected"
    ]
    rejection_covered = {
        rid for task in tasks for rid in (task.get("rejection_requirement_ids") or [])
    }
    missing_rejection = sorted(set(tech_rejection) - rejection_covered)
    empty_tasks = [task["task_id"] for task in tasks if not task.get("requirement_ids")]
    titles = [row.get("title") for row in headings if row.get("task_id")]
    duplicates = sorted({title for title in titles if titles.count(title) > 1})
    issues = []
    if unmapped:
        issues.append(f"未映射技术要求 {len(unmapped)} 条")
    if orphan_tasks:
        issues.append(f"未进目录任务 {len(orphan_tasks)} 个")
    if missing_rejection:
        issues.append(f"技术废标未挂任务 {len(missing_rejection)} 条")
    if empty_tasks:
        issues.append(f"空任务 {len(empty_tasks)} 个")
    if duplicates:
        issues.append(f"重复章节标题 {len(duplicates)} 个")
    return {
        "passed": not issues,
        "issues": issues,
        "unmapped_requirement_ids": unmapped,
        "missing_rejection_ids": missing_rejection,
        "duplicate_titles": duplicates,
    }


def apply_response_plan(workflow: dict) -> dict[str, Any]:
    """从当前技术条款建任务与主题目录；写回 workflow。"""
    rows = [
        enrich_requirement(row)
        for row in (workflow.get("requirements") or {}).values()
        if row.get("technical_clause") and row.get("status") != "rejected"
    ]
    tasks = build_response_tasks(rows)
    headings = arrange_from_tasks(tasks)
    check = validate_plan(rows, tasks, headings)
    if not check["passed"]:
        # 回退：每条要求单独成任务，避免合并导致漏挂。
        solo = []
        for row in rows:
            solo.append({
                "task_id": new_id("task"),
                "title": short_chapter_title(row.get("extracted_summary") or row.get("text") or "技术响应"),
                "theme": _theme_for(row),
                "requirement_ids": [row["id"]],
                "response_strategy": "point_by_point",
                "response_points": [row.get("extracted_summary") or clip_summary(row.get("text") or "")],
                "rejection_requirement_ids": [row["id"]] if row.get("is_rejection_criterion") and row.get("requirement_type") != "qualification" else [],
                "generation_status": "pending",
                "response_status": "not_started",
                "verification_status": "unchecked",
                "outline_number": None,
                "chapter_id": None,
            })
        tasks = solo
        headings = arrange_from_tasks(tasks)
        check = validate_plan(rows, tasks, headings)
    workflow["response_tasks"] = {task["task_id"]: task for task in tasks}
    workflow["plan_validation"] = check
    return {"tasks": tasks, "headings": headings, "validation": check}


def coverage_rows(workflow: dict, outline: dict | None = None) -> list[dict]:
    """覆盖视图五列数据。"""
    outline = outline or workflow.get("technical_outline") or {}
    headings = {item.get("task_id"): item for item in (outline.get("headings") or []) if item.get("task_id")}
    reqs = workflow.get("requirements") or {}
    rows = []
    for task in (workflow.get("response_tasks") or {}).values():
        heading = headings.get(task["task_id"]) or {}
        for rid in task.get("requirement_ids") or []:
            req = reqs.get(rid) or {}
            source = req.get("source") or {}
            rows.append({
                "requirement_id": rid,
                "task_id": task["task_id"],
                "text": req.get("extracted_summary") or req.get("text") or "",
                "risk_level": req.get("risk_level") or "medium",
                "is_rejection_criterion": bool(req.get("is_rejection_criterion")),
                "source_page": source.get("page"),
                "source_filename": source.get("filename") or source.get("file_name"),
                "outline_number": heading.get("number") or task.get("outline_number"),
                "outline_title": heading.get("title") or task.get("title"),
                "response_status": task.get("response_status") or "not_started",
                "generation_status": task.get("generation_status") or "pending",
            })
    return rows
