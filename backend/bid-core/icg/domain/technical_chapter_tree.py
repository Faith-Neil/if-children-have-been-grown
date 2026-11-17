# 为什么有这个文件：技术分册目录由归纳后的响应要点编排，而不是格式锁或六章骨架。
# 它解决什么问题：章名走服务方案写法，不照抄要点；废标不成章；模型可编树，无模型时用同规则替身。

from __future__ import annotations

import copy
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
NUMBER_PREFIX = re.compile(
    r"^(?:"
    r"\d+(?:\.\d+)*[、.．](?!\d)\s*"
    r"|\d+(?:\.\d+)*\s+"
    r"|[一二三四五六七八九十]+[、.．]\s*"
    r")"
)
CHAPTER_PREFIX = re.compile(r"^第[\d一二三四五六七八九十百]+[章节篇][、.．\s]*")
ORDER_PHRASE = re.compile(r"按以下顺序编制|应按以下顺序|按下列顺序")
TREE_SYSTEM = (
    "根据归纳后的响应要点编排技术服务方案目录。"
    "只输出 JSON 数组，不要 markdown 代码围栏，不要写 // 注释。"
    "每项含 level(1-3)、title、mount_ids。每个对象单独一条，不要把两个对象粘在一起。"
    "先排若干一级服务章，每章下面写多个二级，必要时再写三级。"
    "mount_ids 只挂在叶子（二级或三级）上，一级章用 []。"
    "mount_ids 只能是带引号的 m 代号，例如 \"m12\"。不要写 null，不要发明 w 代号或裸数字，只能使用提示列表里的代号。"
    "title 用服务方案名称，不要带「第N章」或「第N节」前缀，禁止照抄要点原文，禁止一条要点单独成章。"
    "禁用标题：评分响应、评分应答、投标响应、技术响应正文、响应说明、本章内容、总结。"
    "废标不是章。人员、证书、商务不成章。父子标题不得相同。每个代号恰好挂到一个叶子。"
    "若提示里给出招标编制顺序，只作参考，可增删改章名并调整先后，不必照抄清单。"
)

# 兼容旧测试引用；目录不再强制输出这六章。
BACKBONE_FRONT = ("项目理解", "总体方案")
BACKBONE_BACK = ("难点与对策", "质量保证", "进度资源", "风险应对")


def strip_heading_number(text: str) -> str:
    cleaned = (text or "").strip()
    while True:
        nxt = CHAPTER_PREFIX.sub("", NUMBER_PREFIX.sub("", cleaned)).strip()
        if nxt == cleaned:
            return cleaned
        cleaned = nxt


PLACEHOLDER_TITLE = re.compile(r"^(?:规范\s*[\d.]+(?:方案)?|.+方案方案)$")
SPEC_NUMBER_THEME = re.compile(r"^规范\s*[\d.]+")
SPEC_NUMBER_COMPACT = re.compile(r"^规范[\d.]+")


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


def _usable_chapter_label(label: str) -> str:
    text = str(label or "").strip()
    if (
        text
        and text not in BANNED_TITLES
        and not any(word in text for word in PERSONNEL_WORDS)
        and not SPEC_NUMBER_THEME.match(text)
        and not PLACEHOLDER_TITLE.match(text)
    ):
        return text
    return ""


def _title_copies_point(title: str, point: str) -> bool:
    """章名等于要点，或是长要点被截下来的开头。"""
    title = title.strip()
    point = point.strip()
    if not title or not point:
        return False
    if title == point:
        return True
    return len(point) > 16 and len(title) > 16 and point.startswith(title)


def _scheme_heading(theme: str, point: str) -> str:
    """照抄要点时改成可用主题；否则用短标题加服务方案写法，不编规范编号。"""
    usable = _usable_chapter_label(theme)
    if usable and not _title_copies_point(usable, point):
        return usable
    from icg.domain.technical_response_plan import short_chapter_title

    short = short_chapter_title(point, fallback="综合技术响应")
    schemed = _scheme_title(short)
    if schemed and not _title_copies_point(schemed, point):
        return schemed
    return "综合技术响应"


def _heading_for_model_title(title: str, mount_ids: list[str], points: list[dict]) -> str:
    ordered: list[dict] = []
    seen: set[str] = set()
    by_id = {str(item.get("id")): item for item in points if item.get("id")}
    for rid in mount_ids:
        item = by_id.get(rid)
        if item is not None and rid not in seen:
            ordered.append(item)
            seen.add(rid)
    for item in points:
        key = str(item.get("id") or "")
        if key in seen:
            continue
        ordered.append(item)
        if key:
            seen.add(key)
    for item in ordered:
        point = str(item.get("point") or "")
        if _title_copies_point(title, point):
            return _scheme_heading(str(item.get("theme") or ""), point)
    return title


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


def _strip_code_fence(raw: str) -> str:
    if "```" not in raw:
        return raw
    body = raw.split("```", 2)[1]
    stripped = body.lstrip()
    if stripped[:4].lower() == "json" and (len(stripped) == 4 or stripped[4] in "\r\n \t"):
        return stripped[4:]
    return body


def _strip_js_comments(raw: str) -> str:
    out: list[str] = []
    index = 0
    in_string = False
    escaped = False
    while index < len(raw):
        char = raw[index]
        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            out.append(char)
            index += 1
            continue
        if char == "/" and index + 1 < len(raw) and raw[index + 1] == "/":
            while index < len(raw) and raw[index] not in "\r\n":
                index += 1
            continue
        out.append(char)
        index += 1
    return "".join(out)


_M_CODE = re.compile(r"m\d+")
_OBJECT_HEAD = re.compile(r'\{\s*"?(?:level|title)"?\s*:')
_TITLE_FIELD = re.compile(r'"title"\s*:\s*"([^"]*)"')
_LEVEL_FIELD = re.compile(r'"level"\s*:\s*(\d+)')


def _m_codes(blob: str) -> list[str]:
    found: list[str] = []
    for code in _M_CODE.findall(blob or ""):
        if code not in found:
            found.append(code)
    return found


def _codes_from_mounts(mounts: Any) -> list[str]:
    if isinstance(mounts, list):
        found: list[str] = []
        for entry in mounts:
            for code in _codes_from_mounts(entry):
                if code not in found:
                    found.append(code)
        return found
    if isinstance(mounts, str):
        return _m_codes(mounts)
    if mounts is None or isinstance(mounts, (int, float, bool)):
        return []
    return _m_codes(json.dumps(mounts, ensure_ascii=False))


def _normalize_tree_item(item: dict) -> dict:
    cleaned = dict(item)
    cleaned["mount_ids"] = _codes_from_mounts(item.get("mount_ids"))
    return cleaned


def _repair_mount_field(chunk: str) -> str:
    match = re.search(r'"mount_ids"\s*:\s*', chunk)
    if not match:
        return chunk
    return chunk[:match.end()] + json.dumps(_m_codes(chunk), ensure_ascii=False) + "}"


def _synthesize_tree_object(chunk: str) -> dict | None:
    title_match = _TITLE_FIELD.search(chunk)
    level_match = _LEVEL_FIELD.search(chunk)
    if not title_match or not level_match:
        return None
    title = title_match.group(1).strip()
    if not title:
        return None
    return {"level": int(level_match.group(1)), "title": title, "mount_ids": _m_codes(chunk)}


def _usable_parsed_item(item: dict) -> dict | None:
    title = item.get("title")
    if not isinstance(title, str) or not title.strip():
        return None
    level = item.get("level")
    if isinstance(level, bool) or not isinstance(level, (int, str)):
        return None
    if isinstance(level, str):
        if not level.isdigit():
            return None
        item = dict(item)
        item["level"] = int(level)
    return item


def _load_tree_object(chunk: str) -> dict | None:
    text = chunk.strip()
    candidates = [text if text.endswith("}") else f"{text}}}"]
    repaired = _repair_mount_field(text)
    if repaired not in candidates:
        candidates.append(repaired if repaired.endswith("}") else f"{repaired}}}")
    for candidate in candidates:
        try:
            item = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            usable = _usable_parsed_item(item)
            if usable is not None:
                return usable
    return _synthesize_tree_object(text)


def _tree_object_slices(body: str) -> list[str]:
    starts = [match.start() for match in _OBJECT_HEAD.finditer(body)]
    slices: list[str] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(body)
        chunk = body[start:end].strip().rstrip(",").strip()
        if not chunk.startswith("{"):
            continue
        # 文件末尾没写完的对象丢掉；中间缺右括号的对象仍可按 title/level 抢救。
        if index == len(starts) - 1 and "}" not in chunk:
            continue
        slices.append(chunk)
    return slices


def _salvage_tree_objects(body: str) -> list[dict]:
    found: list[dict] = []
    for chunk in _tree_object_slices(body):
        item = _load_tree_object(chunk)
        if isinstance(item, dict):
            found.append(item)
    return found


def _closed_object_dicts(body: str) -> list[dict]:
    """截断的尾巴丢掉，不补一个半截节点。"""
    return _salvage_tree_objects(body)


def _load_json_array(raw: str) -> list:
    start = raw.find("[")
    if start < 0:
        return []
    body = raw[start:]
    end = body.rfind("]")
    if end > 0:
        try:
            data = json.loads(body[:end + 1])
        except json.JSONDecodeError:
            data = None
        if isinstance(data, list):
            return data
    return _closed_object_dicts(body)


def _parse_tree_payload(text: str) -> list[dict]:
    raw = _strip_js_comments(_strip_code_fence((text or "").strip()))
    raw = re.sub(r'("mount_ids"\s*:\s*)null\b', r"\1[]", raw)
    data = _load_json_array(raw)
    return [_normalize_tree_item(item) for item in data if isinstance(item, dict)]


def _prompt_aliases(points: list[dict]) -> tuple[list[str], dict[str, str]]:
    lines: list[str] = []
    alias_to_id: dict[str, str] = {}
    for item in points:
        rid = str(item.get("id") or "")
        if not rid:
            continue
        alias = f"m{len(lines) + 1}"
        alias_to_id[alias] = rid
        theme = item.get("theme") or "综合"
        point = str(item.get("point") or "")[:80]
        lines.append(f"{alias}\t{theme}\t{point}")
    return lines, alias_to_id


def _ids_for_aliases(tokens: list, alias_to_id: dict[str, str]) -> list[str]:
    mapped: list[str] = []
    for token in tokens:
        if not isinstance(token, str):
            continue
        rid = alias_to_id.get(token)
        if rid and rid not in mapped:
            mapped.append(rid)
    return mapped


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


def _merge_tasks_onto_host(host: dict, source_tasks: list[dict], reqs: dict[str, dict]) -> None:
    """把要求 id 并进已有叶子任务，避免跳过或覆盖时丢掉映射。"""
    sources: list[dict] = []
    prior = host.get("_task")
    if prior:
        sources.append(prior)
    for task in source_tasks:
        if task not in sources:
            sources.append(task)
    if not sources:
        return
    title = str(host.get("title") or sources[0].get("title") or "总体方案")
    combined = _combined_task(title, title, sources, reqs)
    _fill_leaf(host, combined, reqs)
    host["_task"] = combined


def _chapters_for_mounts(task: dict, h1: str, mounts: list[str], reqs: dict[str, dict]) -> list[dict]:
    """多条挂载时一级只留主题，每条短标题单独做二级。"""
    from icg.domain.technical_response_plan import short_chapter_title

    host = _node(1, h1)
    groups: list[list] = []
    held: list[str] = []
    for rid in mounts:
        row = reqs.get(rid) or {}
        point = str(row.get("extracted_summary") or row.get("text") or "").strip()
        short = short_chapter_title(point or str(task.get("title") or "") or h1, fallback=h1)
        # 整句要点即使未超过 16 字也不是章名；几个字的短名可以。
        copies_long_clause = bool(point) and short == point and len(point) > 8
        if (
            not short
            or short == h1
            or copies_long_clause
            or short in BANNED_TITLES
            or any(word in short for word in PERSONNEL_WORDS)
        ):
            held.append(rid)
            continue
        if groups and groups[-1][0] == short:
            groups[-1][1].append(rid)
        else:
            groups.append([short, [rid]])
    if not groups:
        combined = _combined_task(h1, h1, [task], reqs)
        _fill_leaf(host, combined, reqs)
        host["_task"] = combined
        return [host]
    if held:
        groups[-1][1].extend(held)
    nodes = [host]
    for index, (short, rids) in enumerate(groups):
        points = []
        for rid in rids:
            row = reqs.get(rid) or {}
            point = str(row.get("extracted_summary") or row.get("text") or "").strip()
            if point and point not in points:
                points.append(point)
        leaf_task = {
            **task,
            "task_id": task.get("task_id") if index == 0 else new_id("task"),
            "requirement_ids": list(rids),
            "response_points": points,
            "constraint_ids": list(task.get("constraint_ids") or []) if index == 0 else [],
            "rejection_requirement_ids": list(task.get("rejection_requirement_ids") or []) if index == 0 else [],
        }
        leaf = _node(2, short)
        combined = _combined_task(short, h1, [leaf_task], reqs)
        _fill_leaf(leaf, combined, reqs)
        leaf["_task"] = combined
        nodes.append(leaf)
    return nodes


def stand_in_chapter_tree(tasks: list[dict], reqs: dict[str, dict]) -> list[dict]:
    """无可用模型时按任务列目录。多条挂载时一级只作主题，二级用短标题。不插空的项目理解。"""
    from icg.domain.technical_response_plan import short_chapter_title

    nodes: list[dict] = []
    deferred: list[dict] = []
    for task in tasks:
        mounts = [rid for rid in (task.get("requirement_ids") or []) if _is_mount(reqs.get(rid) or {})]
        if not mounts:
            # 纯约束不成章，但要求 id 必须并进活着的任务，否则 plan_validation 未映射钉死。
            deferred.append(task)
            continue
        theme = _theme_of(task)
        # 只用归纳主题作一级；禁题（评分响应）与「规范 N」编号指纹不成章名。
        label = _usable_chapter_label(theme)
        point = ""
        for rid in mounts:
            point = str((reqs.get(rid) or {}).get("extracted_summary") or (reqs.get(rid) or {}).get("text") or "").strip()
            if point:
                break
        task_title = str(task.get("title") or "").strip()
        if label:
            h1 = label
        else:
            h1 = short_chapter_title(point or task_title, fallback="综合技术响应")
            if (
                SPEC_NUMBER_THEME.match(h1)
                or SPEC_NUMBER_COMPACT.match(h1)
                or PLACEHOLDER_TITLE.match(h1)
                or h1 in BANNED_TITLES
            ):
                h1 = "综合技术响应"
        # 人员/禁用词不得当章名，改挂「综合技术响应」，不能整任务丢掉 requirement_ids。
        if h1 in BANNED_TITLES or any(word in h1 for word in PERSONNEL_WORDS):
            h1 = "综合技术响应"
        if len(mounts) > 1:
            nodes.extend(_chapters_for_mounts(task, h1, mounts, reqs))
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
    if deferred:
        host = next((node for node in nodes if node.get("_task")), None)
        if host is None:
            host = _node(1, "总体方案")
            nodes.append(host)
        _merge_tasks_onto_host(host, deferred, reqs)
    return nodes


def _has_child(nodes: list[dict], index: int) -> bool:
    if index + 1 >= len(nodes):
        return False
    return int(nodes[index + 1].get("level") or 1) > int(nodes[index].get("level") or 1)


def _too_flat(nodes: list[dict]) -> bool:
    if len(nodes) < 2:
        return False
    level_one = [node for node in nodes if int(node.get("level") or 1) == 1]
    deeper = [node for node in nodes if int(node.get("level") or 1) >= 2]
    if len(level_one) >= 2 and not deeper:
        return True
    return len(level_one) >= 4 and len(deeper) < 2


def _hosted_parent_count(nodes: list[dict]) -> int:
    count = 0
    index = 0
    while index < len(nodes):
        if int(nodes[index].get("level") or 1) != 1:
            index += 1
            continue
        cursor = index + 1
        hosted = False
        while cursor < len(nodes) and int(nodes[cursor].get("level") or 1) > 1:
            hosted = True
            cursor += 1
        if hosted:
            count += 1
        index = cursor
    return count


def _theme_label(node: dict, by_id: dict[str, dict]) -> str:
    for rid in list(node.get("mount_ids") or []) + list(node.get("requirement_ids") or []):
        label = _usable_chapter_label(str((by_id.get(str(rid)) or {}).get("theme") or ""))
        if label:
            return label
    return "综合技术响应"


def _child_under_theme(leaf: dict, theme: str, by_id: dict[str, dict]) -> dict:
    from icg.domain.technical_response_plan import short_chapter_title

    title = str(leaf.get("title") or "").strip() or theme
    if title == theme:
        point = ""
        for rid in leaf.get("mount_ids") or []:
            point = str((by_id.get(str(rid)) or {}).get("point") or "").strip()
            if point:
                break
        title = short_chapter_title(point, fallback="服务内容") if point else "服务内容"
        if title == theme:
            title = "服务内容"
    child = dict(leaf)
    child["level"] = 2
    child["title"] = title
    return child


def _insert_under_host(nodes: list[dict], host: dict, child: dict) -> None:
    index = nodes.index(host)
    insert_at = index + 1
    while insert_at < len(nodes) and int(nodes[insert_at].get("level") or 1) > 1:
        insert_at += 1
    nodes.insert(insert_at, child)


def _reshape_flat_leaves(nodes: list[dict], points: list[dict]) -> list[dict]:
    """扁平的一级叶子按主题收进一级章，原标题降为二级。"""
    if not _too_flat(nodes):
        return nodes
    by_id = {str(item.get("id")): item for item in points if item.get("id")}
    structured: list[dict] = []
    flat: list[dict] = []
    index = 0
    while index < len(nodes):
        node = nodes[index]
        level = int(node.get("level") or 1)
        if level == 1 and _has_child(nodes, index):
            structured.append(node)
            index += 1
            while index < len(nodes) and int(nodes[index].get("level") or 1) > 1:
                structured.append(nodes[index])
                index += 1
            continue
        if level == 1 and (node.get("mount_ids") or node.get("requirement_ids")):
            flat.append(node)
            index += 1
            continue
        structured.append(node)
        index += 1
    if len(flat) < 2:
        return nodes
    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for node in flat:
        theme = _theme_label(node, by_id)
        if theme not in groups:
            groups[theme] = []
            order.append(theme)
        groups[theme].append(node)
    rebuilt = list(structured)
    for theme in order:
        host = next(
            (node for node in rebuilt if int(node.get("level") or 1) == 1 and node.get("title") == theme),
            None,
        )
        if host is None:
            host = _node(1, theme)
            rebuilt.append(host)
        for leaf in groups[theme]:
            _insert_under_host(rebuilt, host, _child_under_theme(leaf, theme, by_id))
    return rebuilt


def _split_hard_issues(issues: list[str]) -> tuple[set[str], set[str], list[str]]:
    titles: set[str] = set()
    nested: set[str] = set()
    other: list[str] = []
    for issue in issues:
        if issue.startswith("同名嵌套 "):
            nested.add(issue[len("同名嵌套 "):].strip())
        elif issue.startswith("禁用标题 "):
            titles.add(issue[len("禁用标题 "):].strip())
        elif issue.startswith("人员或商务标题 "):
            titles.add(issue[len("人员或商务标题 "):].strip())
        elif issue.startswith("照抄要点 "):
            titles.add(issue[len("照抄要点 "):].strip())
        else:
            other.append(issue)
    return titles, nested, other


def _drop_indexes(numbered: list[dict], titles: set[str], nested: set[str]) -> set[int]:
    by_number = {item.get("number"): item for item in numbered}
    drop: set[int] = set()
    for index, item in enumerate(numbered):
        title = str(item.get("title") or "")
        if title in titles:
            drop.add(index)
            continue
        if title not in nested:
            continue
        parent_number = ".".join(str(item.get("number") or "").split(".")[:-1])
        parent = by_number.get(parent_number)
        if parent and parent.get("title") == title:
            drop.add(index)
    return drop


def _worth_keeping(nodes: list[dict]) -> bool:
    level_one = sum(1 for node in nodes if int(node.get("level") or 0) == 1)
    for index, node in enumerate(nodes):
        if _has_child(nodes, index):
            continue
        if node.get("mount_ids") or node.get("requirement_ids"):
            return True
    return level_one >= 2


def _without_dropped(nodes: list[dict], drop: set[int], reqs: dict[str, dict]) -> list[dict]:
    kept: list[dict] = []
    pending: list[dict] = []
    for index, node in enumerate(nodes):
        if index in drop:
            if node.get("_task"):
                pending.append(node["_task"])
            continue
        kept.append(node)
    if pending and kept:
        host = next((node for node in reversed(kept) if node.get("_task")), kept[-1])
        _merge_tasks_onto_host(host, pending, reqs)
    return kept


def compose_tree_with_model(
    tasks: list[dict], reqs: dict[str, dict], workflow: dict, model: Any,
) -> list[dict] | None:
    workflow.pop("_tree_call_failed", None)
    workflow.pop("_tree_shape_rejected", None)
    if not _usable_tree_model(model):
        return None
    points = summarize_points(tasks, reqs)
    lines, alias_to_id = _prompt_aliases(points)
    if not lines:
        return None
    sidecar = workflow.get("technical_sidecars") or {}
    order = detect_format_lock(sidecar.get("format_lines"))
    user = "归纳后的响应要点（代号、主题、摘要）：\n" + "\n".join(lines)
    if order:
        user += "\n招标编制顺序（仅参考，不必照抄）：" + "、".join(order)
    try:
        raw = model.suggest(TREE_SYSTEM, user)
        items = _parse_tree_payload(str(raw or ""))
    except Exception:
        workflow["_tree_call_failed"] = True
        return None
    if not items:
        workflow["_tree_call_failed"] = True
        return None
    by_id = {item["id"]: item["task"] for item in points if item.get("id")}
    nodes: list[dict] = []
    used: set[str] = set()
    for item in items:
        title = strip_heading_number(str(item.get("title") or ""))
        level = int(item.get("level") or 1)
        raw_mounts = _ids_for_aliases(item.get("mount_ids") or [], alias_to_id)
        title = _heading_for_model_title(title, raw_mounts, points)
        if not title or title in BANNED_TITLES or any(word in title for word in PERSONNEL_WORDS):
            continue
        if SPEC_NUMBER_THEME.match(title) or SPEC_NUMBER_COMPACT.match(title) or PLACEHOLDER_TITLE.match(title):
            continue
        if level < 1 or level > 3:
            continue
        mount_ids = [rid for rid in raw_mounts if rid in by_id and rid not in used]
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
    if not nodes:
        workflow["_tree_call_failed"] = True
        return None
    if _too_flat(nodes):
        reshaped = _reshape_flat_leaves(nodes, points)
        if _hosted_parent_count(reshaped) >= 2:
            nodes = reshaped
        else:
            workflow["_tree_shape_rejected"] = True
            return None
    # 只把还没挂上的编号并进总体方案。整任务并进去会把已挂编号再记一次，触发重复挂载并整树回退。
    buckets: list[list] = []
    index_by_task: dict[int, int] = {}
    for item in points:
        rid = item.get("id")
        task = item.get("task")
        if not rid or rid in used or not task:
            continue
        key = id(task)
        slot = index_by_task.get(key)
        if slot is None:
            index_by_task[key] = len(buckets)
            buckets.append([task, []])
            slot = index_by_task[key]
        if rid not in buckets[slot][1]:
            buckets[slot][1].append(rid)
    leftover = []
    for task, unused in buckets:
        narrowed = dict(task)
        narrowed["requirement_ids"] = list(unused)
        leftover.append(narrowed)
    if leftover:
        host = next((node for node in nodes if node.get("title") == "总体方案"), None)
        if host is None:
            host = _node(1, "总体方案")
            nodes.append(host)
        # 与已有「总体方案」任务合并，禁止覆盖导致原先 mount 从 response_tasks 消失。
        _merge_tasks_onto_host(host, leftover, reqs)
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
    failed = bool(workflow.pop("_tree_call_failed", False))
    shape_rejected = bool(workflow.pop("_tree_shape_rejected", False))
    used_model = bool(nodes) and not shape_rejected
    if not used_model:
        if shape_rejected:
            failed = True
        nodes = stand_in_chapter_tree(tasks, reqs)
    preview = copy.deepcopy(nodes)
    numbered, rewritten = _finish_tree(preview)
    issues = tree_issues(numbered, list(reqs.values()), rewritten)
    # 能删掉的坏标题就删，保留其余模型章。「评分点未索引」仍是软问题。
    hard = [item for item in issues if not item.startswith("评分点未索引")]
    if hard and used_model:
        titles, nested, other = _split_hard_issues(hard)
        drop = set() if other or not (titles or nested) else _drop_indexes(numbered, titles, nested)
        kept = _without_dropped(nodes, drop, reqs) if drop else []
        if drop and _worth_keeping(kept):
            nodes = kept
            numbered, rewritten = _finish_tree(nodes)
        else:
            nodes = stand_in_chapter_tree(tasks, reqs)
            numbered, rewritten = _finish_tree(nodes)
            used_model = False
            failed = True
    if used_model:
        workflow["outline_source"] = "model"
        workflow["tree_model_failed"] = False
    elif failed:
        workflow["outline_source"] = "rule_fallback"
        workflow["tree_model_failed"] = True
    else:
        workflow["outline_source"] = "rule"
        workflow["tree_model_failed"] = False
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
        if PLACEHOLDER_TITLE.match(title) or SPEC_NUMBER_THEME.match(title) or SPEC_NUMBER_COMPACT.match(title):
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
