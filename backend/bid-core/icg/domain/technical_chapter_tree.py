# 为什么有这个文件：技术分册目录由归纳后的响应要点编排，而不是格式锁或六章骨架。
# 它解决什么问题：章名走服务方案写法，不照抄要点；废标不成章；模型可编树，无模型时用同规则替身。

from __future__ import annotations

import json
import re
from typing import Any

from icg.domain.domain import new_id
from icg.domain.technical_clause_extract import FORMAT_HEAD, NUMBERED_CHILD, SPEC_LINE
from icg.domain.technical_clause_role import assign_clause_role

BANNED_TITLES = frozenset({
    "评分响应", "评分应答", "投标响应", "技术响应正文", "响应说明", "本章内容", "总结",
})
PERSONNEL_WORDS = ("人员", "团队", "资质", "证书", "商务")
SCHEME_TAIL = ("方案", "措施", "体系", "计划", "预案")
NUMBER_PREFIX = re.compile(r"^(?:\d+(?:\.\d+)*|[一二三四五六七八九十]+)[、.．]\s*")
ORDER_PHRASE = re.compile(r"按以下顺序编制|应按以下顺序|按下列顺序")
TREE_SYSTEM = (
    "根据归纳后的响应要点编排技术服务方案目录。输出 JSON 数组，每项含 level(1-3)、title、mount_ids。"
    "章名用常规服务方案写法，禁止照抄要点原文，禁止一条要点单独成章。"
    "禁用标题：评分响应、评分应答、投标响应、技术响应正文、响应说明、本章内容、总结。"
    "废标不是章。人员、证书、商务不成章。父子标题不得相同。每个 mount_id 恰好挂到一个叶子。"
    "若提示里给出招标编制顺序，只作参考，可增删改章名并调整先后，不必照抄清单。"
)

# 兼容旧测试引用；目录不再强制输出这六章。
BACKBONE_FRONT = ("项目理解", "总体方案")
BACKBONE_BACK = ("难点与对策", "质量保证", "进度资源", "风险应对")


def strip_heading_number(text: str) -> str:
    return NUMBER_PREFIX.sub("", (text or "").strip()).strip()


PLACEHOLDER_TITLE = re.compile(r"^(?:规范\s*[\d.]+方案|.+方案方案)$")


def _scheme_title(name: str) -> str:
    """仅保留兼容导出；目录替身不再用它硬拼「规范 N方案」。"""
    title = strip_heading_number(name)
    if not title or title in BANNED_TITLES:
        return ""
    if any(word in title for word in PERSONNEL_WORDS):
        return ""
    if PLACEHOLDER_TITLE.match(title):
        return ""
    if title.endswith(SCHEME_TAIL):
        return title
    return f"{title}方案"


def _numbered_children(lines: list[str], start: int) -> list[str]:
    children: list[str] = []
    for line in lines[start + 1:]:
        if NUMBERED_CHILD.match(line) or SPEC_LINE.match(line):
            title = strip_heading_number(line)
            if title and title not in children:
                children.append(title)
            continue
        if FORMAT_HEAD.search(line) or ORDER_PHRASE.search(line):
            break
        if children:
            break
    return children


def detect_format_lock(lines: list[str] | None) -> list[str]:
    """抽出招标编制顺序，仅作模型参考，不强制照抄。"""
    raw = [str(line).strip() for line in (lines or []) if str(line).strip()]
    if not raw:
        return []
    run: list[str] = []
    best: list[str] = []
    for line in raw:
        if NUMBERED_CHILD.match(line) or SPEC_LINE.match(line):
            title = strip_heading_number(line)
            if title:
                run.append(title)
                if len(run) > len(best):
                    best = list(run)
            continue
        run = []
    if len(best) >= 3:
        return best
    for index, line in enumerate(raw):
        if FORMAT_HEAD.search(line) or ORDER_PHRASE.search(line):
            children = _numbered_children(raw, index)
            if children:
                return children
    return []


def _is_mount(row: dict) -> bool:
    return assign_clause_role(row) != "rejection_constraint"


def _theme_of(task: dict) -> str:
    theme = str(task.get("theme") or "").strip()
    if theme in BANNED_TITLES or theme == "评分响应":
        return ""
    return theme


def _node(level: int, title: str, **extra: Any) -> dict:
    return {
        "level": level,
        "title": title,
        "requirement_id": extra.get("requirement_id"),
        "task_id": extra.get("task_id"),
        "requirement_ids": list(extra.get("requirement_ids") or []),
        "score_refs": list(extra.get("score_refs") or []),
        "constraint_ids": list(extra.get("constraint_ids") or []),
        "mount_ids": list(extra.get("mount_ids") or []),
    }


def _combined_task(title: str, theme: str, source_tasks: list[dict], reqs: dict[str, dict]) -> dict:
    requirement_ids: list[str] = []
    points: list[str] = []
    constraints: list[str] = []
    rejections: list[str] = []
    for task in source_tasks:
        for rid in task.get("requirement_ids") or []:
            if rid not in requirement_ids:
                requirement_ids.append(rid)
        for point in task.get("response_points") or []:
            if point not in points:
                points.append(point)
        for rid in task.get("constraint_ids") or []:
            if rid not in constraints:
                constraints.append(rid)
        for rid in task.get("rejection_requirement_ids") or []:
            if rid not in rejections:
                rejections.append(rid)
    mounts = [rid for rid in requirement_ids if _is_mount(reqs.get(rid) or {"id": rid, "text": ""})]
    return {
        "task_id": source_tasks[0]["task_id"] if len(source_tasks) == 1 else new_id("task"),
        "title": title,
        "theme": theme,
        "requirement_ids": requirement_ids,
        "response_strategy": "point_by_point",
        "response_points": points,
        "rejection_requirement_ids": rejections,
        "constraint_ids": constraints,
        "generation_status": "pending",
        "response_status": "not_started",
        "verification_status": "unchecked",
        "outline_number": None,
        "chapter_id": None,
        "_mount_ids": mounts,
    }


def _fill_leaf(node: dict, task: dict, reqs: dict[str, dict]) -> None:
    mounts = list(task.get("_mount_ids") or [])
    constraints = list(task.get("constraint_ids") or [])
    scoring = [
        rid for rid in mounts
        if (reqs.get(rid) or {}).get("section_kind") == "scoring"
    ]
    node["task_id"] = task["task_id"]
    node["requirement_ids"] = list(dict.fromkeys([*mounts, *constraints]))
    node["requirement_id"] = mounts[0] if mounts else None
    node["score_refs"] = scoring
    node["constraint_ids"] = constraints
    node["mount_ids"] = mounts


def _usable_tree_model(model: Any) -> bool:
    if not (model and getattr(model, "is_real_model", False) and getattr(model, "is_local", None) is not False):
        return False
    url = getattr(model, "base_url", "") or ""
    if not url:
        return True
    from icg.infra.openai_model import is_public_model_url
    return not is_public_model_url(url)


def _parse_tree_payload(text: str) -> list[dict]:
    raw = (text or "").strip()
    if "```" in raw:
        fenced = raw.split("```", 2)[1]
        raw = fenced[4:] if fenced.startswith("json") else fenced
    start, end = raw.find("["), raw.rfind("]")
    if start < 0 or end < 0:
        return []
    data = json.loads(raw[start:end + 1])
    return data if isinstance(data, list) else []


def summarize_points(tasks: list[dict], reqs: dict[str, dict]) -> list[dict]:
    """把响应要点收成短条，供模型或替身编排，不把原文当章名。"""
    rows: list[dict] = []
    for task in tasks:
        theme = _theme_of(task)
        for rid in task.get("requirement_ids") or []:
            row = reqs.get(rid) or {"id": rid, "text": ""}
            if not _is_mount(row):
                continue
            point = str(row.get("extracted_summary") or row.get("text") or "").strip()
            rows.append({
                "id": rid,
                "theme": theme,
                "point": point,
                "task": task,
            })
        if not any(_is_mount(reqs.get(rid) or {}) for rid in (task.get("requirement_ids") or [])):
            for point in task.get("response_points") or []:
                rows.append({"id": task.get("task_id") or "", "theme": theme, "point": str(point), "task": task})
    return rows


def stand_in_chapter_tree(tasks: list[dict], reqs: dict[str, dict]) -> list[dict]:
    """无可用模型时按任务列目录。一任务一主题章，单条挂载时二级用短标题。不插空的项目理解。"""
    from icg.domain.technical_response_plan import short_chapter_title

    nodes: list[dict] = []
    for task in tasks:
        mounts = [rid for rid in (task.get("requirement_ids") or []) if _is_mount(reqs.get(rid) or {})]
        if not mounts:
            # 纯废标/约束任务不成章，留给有挂载的任务挂 constraint_ids。
            continue
        theme = _theme_of(task)
        # 只用归纳主题作一级；禁题（评分响应）不回落到条款短名当一级。
        label = str(theme or "").strip()
        point = ""
        for rid in mounts:
            point = str((reqs.get(rid) or {}).get("text") or "").strip()
            if point:
                break
        task_title = str(task.get("title") or "").strip()
        if label and label not in BANNED_TITLES and not any(word in label for word in PERSONNEL_WORDS):
            h1 = label
        else:
            h1 = "综合技术响应"
        if h1 in BANNED_TITLES or any(word in h1 for word in PERSONNEL_WORDS):
            continue
        host = _node(1, h1)
        short = ""
        if len(mounts) == 1:
            short = short_chapter_title(point or task_title or h1, fallback=h1)
        # 长条款原文不得当二级章名；已是短名（含规范编号下的条款名）可以。
        copies_long_clause = bool(point) and short == point and len(point) > 16
        use_child = (
            len(mounts) == 1
            and short
            and short != h1
            and not copies_long_clause
            and short not in BANNED_TITLES
            and not any(word in short for word in PERSONNEL_WORDS)
        )
        if use_child:
            nodes.append(host)
            leaf = _node(2, short)
            combined = _combined_task(short, h1, [task], reqs)
            _fill_leaf(leaf, combined, reqs)
            leaf["_task"] = combined
            nodes.append(leaf)
        else:
            combined = _combined_task(h1, h1, [task], reqs)
            _fill_leaf(host, combined, reqs)
            host["_task"] = combined
            nodes.append(host)
    return nodes


def compose_tree_with_model(
    tasks: list[dict], reqs: dict[str, dict], workflow: dict, model: Any,
) -> list[dict] | None:
    if not _usable_tree_model(model):
        return None
    points = summarize_points(tasks, reqs)
    lines = [f"{item['id']}\t{item['theme'] or '综合'}\t{item['point'][:80]}" for item in points if item.get("id")]
    if not lines:
        return None
    sidecar = workflow.get("technical_sidecars") or {}
    order = detect_format_lock(sidecar.get("format_lines"))
    user = "归纳后的响应要点（id、主题、摘要）：\n" + "\n".join(lines)
    if order:
        user += "\n招标编制顺序（仅参考，不必照抄）：" + "、".join(order)
    try:
        raw = model.suggest(TREE_SYSTEM, user)
        items = _parse_tree_payload(str(raw or ""))
    except Exception:
        return None
    if not items:
        return None
    by_id = {item["id"]: item["task"] for item in points if item.get("id")}
    nodes: list[dict] = []
    used: set[str] = set()
    for item in items:
        title = strip_heading_number(str(item.get("title") or ""))
        level = int(item.get("level") or 1)
        if not title or title in BANNED_TITLES or any(word in title for word in PERSONNEL_WORDS):
            continue
        if level < 1 or level > 3:
            continue
        mount_ids = [str(rid) for rid in (item.get("mount_ids") or []) if str(rid) in by_id and str(rid) not in used]
        node = _node(level, title, mount_ids=mount_ids)
        if mount_ids:
            group = []
            for rid in mount_ids:
                used.add(rid)
                task = by_id[rid]
                if task not in group:
                    group.append(task)
            combined = _combined_task(title, title, group, reqs)
            combined["_mount_ids"] = [rid for rid in mount_ids if _is_mount(reqs.get(rid) or {})]
            _fill_leaf(node, combined, reqs)
            node["_task"] = combined
        nodes.append(node)
    leftover = [item["task"] for item in points if item.get("id") and item["id"] not in used]
    if leftover:
        host = next((node for node in nodes if node.get("title") == "总体方案"), None)
        if host is None:
            host = _node(1, "总体方案")
            nodes.append(host)
        extra = _combined_task(host["title"], host["title"], leftover, reqs)
        _fill_leaf(host, extra, reqs)
        host["_task"] = extra
    if not any(int(node.get("level") or 0) == 1 and node.get("title") == "项目理解" for node in nodes):
        nodes.insert(0, _node(1, "项目理解"))
    return nodes or None


def _finish_tree(nodes: list[dict]) -> tuple[list[dict], list[dict]]:
    rewritten: list[dict] = []
    for node in nodes:
        task = node.pop("_task", None)
        if task:
            rewritten.append(task)
            task.pop("_mount_ids", None)
    from icg.domain.technical_outline import assign_numbers
    numbered = assign_numbers(nodes)
    id_to_number = {row["task_id"]: row["number"] for row in numbered if row.get("task_id")}
    for task in rewritten:
        task["outline_number"] = id_to_number.get(task["task_id"])
    return numbered, rewritten


def build_chapter_tree(tasks: list[dict], workflow: dict | None = None, model: Any = None) -> tuple[list[dict], list[dict]]:
    """归纳要点后编目录。优先本地模型；否则用挂载列表替身。"""
    workflow = workflow or {}
    reqs = {
        row["id"]: row
        for row in (workflow.get("requirements") or {}).values()
        if row.get("id")
    }
    # tree_model 仅在同一次 outline 调用内临时存在，禁止持久化进 MySQL。
    model = model or workflow.get("tree_model")
    nodes = compose_tree_with_model(tasks, reqs, workflow, model)
    if not nodes:
        nodes = stand_in_chapter_tree(tasks, reqs)
    numbered, rewritten = _finish_tree(nodes)
    issues = tree_issues(numbered, list(reqs.values()), rewritten)
    if issues:
        nodes = stand_in_chapter_tree(tasks, reqs)
        numbered, rewritten = _finish_tree(nodes)
    return numbered, rewritten


def tree_issues(headings: list[dict], requirements: list[dict], tasks: list[dict]) -> list[str]:
    """目录合法性。结构错误在这里拦住。"""
    issues: list[str] = []
    h1 = [item for item in headings if int(item.get("level") or 0) == 1]
    by_number = {item.get("number"): item for item in headings}
    clause_text = {
        str(row.get("text") or "").strip()
        for row in requirements
        if row.get("id")
    }
    clause_text.update(str(row.get("extracted_summary") or "").strip() for row in requirements)
    clause_text.discard("")
    for item in headings:
        title = str(item.get("title") or "")
        if title in BANNED_TITLES:
            issues.append(f"禁用标题 {title}")
        if any(word in title for word in PERSONNEL_WORDS):
            issues.append(f"人员或商务标题 {title}")
        if PLACEHOLDER_TITLE.match(title):
            issues.append(f"占位拼接标题 {title}")
        # 短名条款（≤16）允许作章名；拦住把长条款原文直接贴成标题。
        if title in clause_text and len(title) > 16:
            issues.append(f"照抄要点 {title}")
        parent_number = ".".join(str(item.get("number") or "").split(".")[:-1])
        parent = by_number.get(parent_number)
        if parent and parent.get("title") == title:
            issues.append(f"同名嵌套 {title}")
        if int(item.get("level") or 0) > 3:
            issues.append("超过三级标题")
    if not h1:
        issues.append("缺少一级标题")
    seen: set[str] = set()
    for item in headings:
        for rid in item.get("requirement_ids") or []:
            role = assign_clause_role(next((row for row in requirements if row.get("id") == rid), {"id": rid}))
            if role == "rejection_constraint":
                if title_is_constraint(item.get("title") or "", requirements, rid):
                    issues.append(f"废标项成章 {rid}")
                continue
            if rid in seen:
                issues.append(f"重复挂载 {rid}")
            seen.add(rid)
    scoring = [
        row["id"] for row in requirements
        if row.get("section_kind") == "scoring" and row.get("status") != "rejected" and _is_mount(row)
    ]
    refs = {rid for item in headings for rid in (item.get("score_refs") or [])}
    missing_score = [rid for rid in scoring if rid not in refs]
    if missing_score:
        issues.append(f"评分点未索引 {len(missing_score)} 条")
    return issues


def title_is_constraint(title: str, requirements: list[dict], rid: str) -> bool:
    row = next((item for item in requirements if item.get("id") == rid), None)
    if row is None:
        return False
    text = str(row.get("text") or "")
    return bool(text) and text == title
