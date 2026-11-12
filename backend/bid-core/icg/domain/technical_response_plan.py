# 为什么有这个文件：把招标要求库 enrich 成 ResponseTask，并排出主题目录与计划校验。
# 它解决什么问题：禁止「一条要求原文 = 一节目录标题」；建立 要求→任务→章节 映射。

from __future__ import annotations

import re
from typing import Any

from icg.domain.domain import new_id
from icg.domain.technical_clause_role import assign_clause_role

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
        for item in members:
            item["clause_role"] = assign_clause_role(item)
        tech_rejection = [
            item["id"] for item in members
            if item.get("is_rejection_criterion") and item.get("requirement_type") not in ("qualification",)
        ]
        constraint_ids = [item["id"] for item in members if item.get("clause_role") == "rejection_constraint"]
        tasks.append({
            "task_id": new_id("task"),
            "title": title,
            "theme": theme,
            "requirement_ids": [item["id"] for item in members],
            "response_strategy": "point_by_point",
            "response_points": [
                item.get("extracted_summary") or clip_summary(item.get("text") or "")
                for item in members
                if item.get("clause_role") != "rejection_constraint"
            ],
            "rejection_requirement_ids": tech_rejection,
            "constraint_ids": constraint_ids,
            "generation_status": "pending",
            "response_status": "not_started",
            "verification_status": "unchecked",
            "outline_number": None,
            "chapter_id": None,
        })
    return tasks


def _fold_constraint_only_tasks(tasks: list[dict], requirements: list[dict]) -> list[dict]:
    """纯废标任务不成章，约束并进最近的有挂载任务。"""
    from icg.domain.technical_clause_role import assign_clause_role

    by_id = {row["id"]: row for row in requirements if row.get("id")}
    kept: list[dict] = []
    pending: list[dict] = []

    def absorb(host: dict, other: dict) -> None:
        host["requirement_ids"] = list(dict.fromkeys([
            *(host.get("requirement_ids") or []),
            *(other.get("requirement_ids") or []),
        ]))
        host["constraint_ids"] = list(dict.fromkeys([
            *(host.get("constraint_ids") or []),
            *(other.get("constraint_ids") or []),
            *(other.get("requirement_ids") or []),
        ]))
        host["rejection_requirement_ids"] = list(dict.fromkeys([
            *(host.get("rejection_requirement_ids") or []),
            *(other.get("rejection_requirement_ids") or []),
        ]))

    for task in tasks:
        mounts = [
            rid for rid in (task.get("requirement_ids") or [])
            if assign_clause_role(by_id.get(rid) or {"id": rid, "text": ""}) != "rejection_constraint"
        ]
        if not mounts:
            pending.append(task)
            continue
        for other in pending:
            absorb(task, other)
        pending = []
        kept.append(task)
    if pending and kept:
        for other in pending:
            absorb(kept[-1], other)
    elif pending:
        # 整卷只有废标时仍保留一行，避免任务列表被掏空。
        kept.extend(pending)
    return kept


def arrange_from_tasks(tasks: list[dict], workflow: dict | None = None, model=None) -> list[dict]:
    """归纳要点后编目录。评分项名不再做一级标题。"""
    if not tasks:
        return []
    from icg.domain.technical_chapter_tree import build_chapter_tree
    reqs = list((workflow or {}).get("requirements", {}).values()) if workflow else []
    folded = _fold_constraint_only_tasks(list(tasks), reqs)
    tasks[:] = folded
    numbered, rewritten = build_chapter_tree(tasks, workflow or {}, model=model)
    tasks[:] = rewritten
    return numbered


def validate_plan(requirements: list[dict], tasks: list[dict], headings: list[dict]) -> dict[str, Any]:
    """确定性计划校验；不通过则 callers 可回退重建任务。"""
    req_ids = {row["id"] for row in requirements if row.get("technical_clause") and row.get("status") != "rejected"}
    mapped = {
        rid
        for task in tasks
        for rid in (
            *(task.get("requirement_ids") or []),
            *(task.get("constraint_ids") or []),
            *(task.get("rejection_requirement_ids") or []),
        )
    }
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
    from icg.domain.technical_chapter_tree import tree_issues
    issues.extend(tree_issues(headings, requirements, tasks))
    return {
        "passed": not issues,
        "issues": issues,
        "unmapped_requirement_ids": unmapped,
        "missing_rejection_ids": missing_rejection,
        "duplicate_titles": duplicates,
    }


def apply_response_plan(workflow: dict, model=None) -> dict[str, Any]:
    """从当前技术条款建任务与主题目录；写回 workflow。"""
    rows = [
        enrich_requirement(row)
        for row in (workflow.get("requirements") or {}).values()
        if row.get("technical_clause") and row.get("status") != "rejected"
    ]
    tree_model = model or workflow.get("tree_model")
    tasks = build_response_tasks(rows)
    headings = arrange_from_tasks(tasks, workflow, model=tree_model)
    check = validate_plan(rows, tasks, headings)
    if not check["passed"]:
        headings = arrange_from_tasks(tasks, workflow, model=tree_model)
        check = validate_plan(rows, tasks, headings)
    if not check["passed"]:
        for task in tasks:
            task["theme"] = ""
        headings = arrange_from_tasks(tasks, workflow, model=tree_model)
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
                "clause_role": req.get("clause_role") or "response_mount",
                "source_page": source.get("page"),
                "source_filename": source.get("filename") or source.get("file_name"),
                "outline_number": heading.get("number") or task.get("outline_number"),
                "outline_title": heading.get("title") or task.get("title"),
                "response_status": task.get("response_status") or "not_started",
                "generation_status": task.get("generation_status") or "pending",
            })
    return rows
