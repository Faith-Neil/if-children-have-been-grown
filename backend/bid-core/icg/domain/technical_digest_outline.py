# 为什么有这个文件：用三张清单两阶段调用模型拟 1～4 级目录（ISSUE-060 / TV-M0-T32）。
# 它解决什么问题：
# 1. 真实模型环境下禁止静默规则兜底——阶段一生成章节骨架，阶段二把全部有效 T/S 编号
#    按语义全量均衡挂载到骨架叶子；重试仍失败必须明确上浮失败原因，不得偷塞通用规则目录；
# 2. 彻底移除「每章最多 9 条、剩余倾倒其他服务承诺」的硬编码截断：漏挂编号只进未挂载池
#    （目录确认 409 闸门可查）或明确失败，绝不倒进兜底章；
# 3. 目录失败/超时记录兼容真实适配器 Timeout/timeout 异常类型与 cause 链。

from __future__ import annotations

import json
import re
from typing import Any

from icg.domain.domain import new_id
from icg.domain.technical_digest import build_digest, digest_index

# 阶段一：只规划章节骨架。高分评分项须独立成章/节；禁用兜底章名。
SKELETON_SYSTEM = (
    "你在为技术服务方案设计章节目录骨架。只输出 JSON："
    '{"nodes":[{"level":1,"title":"…"}]}。'
    "level 为 1～3，按阅读顺序排列，不跳级，不输出挂载内容。title 是不超过 16 字的章节名，"
    "不抄条款原文，不带编号，不带「第N章」「第N节」。"
    "依据技术需求清单与评分规则清单的分值权重设计骨架：高分评分项（尤其 15 分以上）应独立成章或设专节；"
    "服务内容按主题分章，叶子节数量与要点规模匹配，不要把所有要点挤进少数几章。"
    "禁止使用「其他服务承诺」「其他服务」「其他」「综合」这类兜底章名。"
    "废标清单 R 只作红线，不单独成章。联合体、转包分包、投标文件份数、报名材料、资格条件、"
    "投标有效期、保证金、报价、格式装订等商务/资格/格式条款不得写成技术目录章节。"
    "若给出编制顺序，一级标题按它排。禁止编造清单外的服务和指标。"
)
# 阶段二：把全部清单编号挂到骨架叶子。全量、均衡、不重复、不遗漏。
MOUNT_SYSTEM = (
    "你在为技术服务方案目录挂载响应要点。只输出 JSON："
    '{"mounts":[{"node":"1.2","refs":["T-01","S-01-1"]}]}。'
    "node 必须是目录骨架里叶子节点的编号；refs 是挂到该叶子的清单编号。"
    "每个清单编号必须且只能挂到一个叶子节点，按语义挂到最匹配的章节，一个都不许遗漏。"
    "高分评分要点必须挂到对应的核心技术章节；各叶子挂载数量按语义容量均衡分布，"
    "严禁把大量编号集中堆进同一节。禁止编造清单外的编号。"
)
FALLBACK_TITLE = "其他服务承诺"
BANNED_CHAPTER_TITLES = frozenset({"其他服务承诺", "其他服务", "其他", "综合", "综合服务"})
MODEL_FAILED = "模型两阶段目录规划失败"
MAX_ATTEMPTS = 3  # 1 次首调 + 最多 2 次自动重试（ISSUE-060 AC-05）
MIN_MOUNT_RATIO = 0.6  # 阶段二全量挂载的最低接受比例；残余漏挂进未挂载池而非兜底章
MAX_LEAF_SHARE = 0.5  # 单叶挂载占比超过一半且叶子数 ≥3 视为倾倒，触发均衡重试
TITLE_LIMIT = 18


# ---------------------------------------------------------------- 错误与超时识别
def error_is_timeout(exc: BaseException | None) -> bool:
    """真实适配器超时识别，共享 technical_model_extract 的 cause 链实现。"""
    from icg.domain.technical_model_extract import error_is_timeout as shared

    return shared(exc)


def _error_detail(exc: BaseException) -> dict[str, Any]:
    chain: list[str] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen and len(chain) < 4:
        seen.add(id(current))
        chain.append(f"{type(current).__name__}: {str(current).strip()[:120]}")
        current = current.__cause__ or (None if current.__suppress_context__ else current.__context__)
    return {
        "type": type(exc).__name__,
        "message": str(exc).strip()[:200] or type(exc).__name__,
        "timeout": error_is_timeout(exc),
        "chain": chain,
    }


# ---------------------------------------------------------------- 输入组装
def _scoring_weight_lines(digest: dict) -> list[str]:
    lines: list[str] = []
    for group in digest.get("scoring") or []:
        score = f"（{group['score']:g} 分）" if isinstance(group.get("score"), (int, float)) else ""
        lines.append(f"{group['id']} {group['item']}{score}：{str(group.get('criteria') or '')[:120]}")
    return lines


def skeleton_user(workflow: dict, digest: dict) -> str:
    """阶段一输入：项目语境 + 三张清单（带评分权重）。"""
    facts = workflow.get("technical_facts") or {}
    order = ((workflow.get("technical_sidecars") or {}).get("format_lines") or [])[:12]
    lines = [f"项目：{facts.get('客户名') or ''} {facts.get('项目理解') or ''}".strip()]
    if order:
        lines.append("编制顺序：" + "；".join(str(item) for item in order))
    lines.append("技术需求清单：")
    lines += [f"{item['id']} {item['text']}" for item in digest.get("tech") or []] or ["（无）"]
    lines.append("评分规则清单：")
    scoring_lines = _scoring_weight_lines(digest)
    if scoring_lines:
        lines += scoring_lines
        for group in digest.get("scoring") or []:
            lines += [f"  {point['id']} {point['text']}" for point in group["points"]]
    else:
        lines.append("（无）")
    return "\n".join(lines)


def mount_user(workflow: dict, digest: dict, skeleton: list[dict], feedback: str = "") -> str:
    """阶段二输入：带编号的骨架叶子 + 全部有效 T/S 编号清单。"""
    lines = ["目录骨架（只能挂到叶子节点编号）："]
    for node in skeleton:
        leaf = "（叶子）" if node.get("leaf") else ""
        lines.append(f"{node['number']} {node['title']}{leaf}")
    lines.append("技术需求清单（必须全部挂载）：")
    lines += [f"{item['id']} {item['text']}" for item in digest.get("tech") or []] or ["（无）"]
    lines.append("评分要点清单（必须全部挂载）：")
    point_lines: list[str] = []
    for group in digest.get("scoring") or []:
        score = f"（{group['score']:g} 分）" if isinstance(group.get("score"), (int, float)) else ""
        for point in group["points"]:
            point_lines.append(f"{point['id']} {point['text']} 〔{group['item']}{score}〕")
    lines += point_lines or ["（无）"]
    if feedback:
        lines.append(feedback)
    return "\n".join(lines)


# ---------------------------------------------------------------- JSON 修复
def _strip_fence(raw: str) -> str:
    text = (raw or "").strip()
    if "```" not in text:
        return text
    body = text.split("```", 2)[1]
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


def _json_openers(text: str) -> list[str]:
    stack: list[str] = []
    in_string = False
    escaped = False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char in "[{":
            stack.append(char)
        elif char in "]}" and stack:
            stack.pop()
    return stack


def _repair_truncated_json(candidate: str) -> dict:
    """真实模型在 max_tokens/长输出边界常把合法 JSON 数组尾部截断。只在完整对象边界
    截断并补齐未闭合括号；绝不补写任何业务字段或编号。"""
    positions = [match.start() for match in re.finditer(r"}", candidate)]
    for position in reversed(positions):
        prefix = candidate[:position + 1].rstrip().rstrip(",")
        stack = _json_openers(prefix)
        if not stack or len(stack) > 4:
            continue
        closing = "".join("}" if opener == "{" else "]" for opener in reversed(stack))
        for text in (prefix + closing, re.sub(r",\s*([}\]])", r"\1", prefix + closing)):
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                return data
    return {}


def repair_json_payload(raw: str) -> dict:
    """JSON 修复：剥围栏/注释、截取对象体、去尾逗号；再修复被 max_tokens 截断的合法前缀。"""
    body = _strip_js_comments(_strip_fence(str(raw or "")))
    start, end = body.find("{"), body.rfind("}")
    if start < 0:
        return {}
    candidate = body[start:end + 1] if end >= 0 else body[start:]
    for text in (candidate, re.sub(r",\s*([}\]])", r"\1", candidate)):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return _repair_truncated_json(candidate)


# ---------------------------------------------------------------- 骨架校验
def _clean_title(raw: Any) -> str:
    from icg.domain.technical_response_plan import short_chapter_title

    text = re.sub(r"^(?:\d+(?:\.\d+)*|[一二三四五六七八九十]+[、.．])\s*", "", str(raw or "").strip())
    text = re.sub(r"^第[\d一二三四五六七八九十百]+[章节篇][、.．\s]*", "", text).strip()
    return short_chapter_title(text) if len(text) > TITLE_LIMIT else text


def _normalize_skeleton(raw_nodes: Any) -> list[dict]:
    """骨架结构校验与轻量修复：不跳级、标题非空、禁兜底章名。返回带 leaf 标记的编号骨架。"""
    out: list[dict] = []
    for node in raw_nodes if isinstance(raw_nodes, list) else []:
        if not isinstance(node, dict):
            continue
        title = _clean_title(node.get("title"))
        if not title or title in BANNED_CHAPTER_TITLES:
            continue
        try:
            level = int(node.get("level") or 1)
        except (TypeError, ValueError):
            level = 1
        level = 1 if not out else max(1, min(level, out[-1]["level"] + 1, 4))
        out.append({"level": level, "title": title})
    if len(out) < 1:
        return []
    return _number_skeleton(out)


def _number_skeleton(nodes: list[dict]) -> list[dict]:
    """按阅读顺序重排 1～4 级编号并重算 leaf；裁剪空节点后必须复用同一逻辑。"""
    out = [dict(node) for node in nodes]
    counters = [0, 0, 0, 0]
    for position, node in enumerate(out):
        level = int(node["level"])
        counters[level - 1] += 1
        for deeper in range(level, 4):
            counters[deeper] = 0
        node["number"] = ".".join(str(value) for value in counters[:level])
        node["leaf"] = position + 1 >= len(out) or int(out[position + 1]["level"]) <= level
    return out


# ---------------------------------------------------------------- 挂载校验
def _expand_refs(refs: Any, index: dict[str, list[str]]) -> list[str]:
    """模型可用组号或点号作答；去重/覆盖率之前统一把组号展开为点号。"""
    found: list[str] = []

    def add(key: str) -> None:
        if key in index and key not in found:
            found.append(key)

    raw_refs = refs if isinstance(refs, list) else [refs] if refs else []
    for ref in raw_refs:
        key = re.sub(r"\s", "", str(ref).upper())
        if key not in index:
            continue
        point_keys: list[str] = []
        if re.fullmatch(r"S-\d+", key):
            prefix = key + "-"
            point_keys = sorted(
                (candidate for candidate in index if candidate.startswith(prefix) and candidate[len(prefix):].isdigit()),
                key=lambda candidate: int(candidate[len(prefix):]),
            )
        if point_keys:
            for point_key in point_keys:
                add(point_key)
        else:
            add(key)
    return found


def _normalize_mounts(raw_mounts: Any, skeleton: list[dict], index: dict[str, list[str]]) -> tuple[dict[str, list[str]], list[str]]:
    """返回 叶子编号 → 清单编号 映射与无效条目原因。每条编号只保留首次挂载。"""
    leaf_numbers = {node["number"] for node in skeleton if node.get("leaf")}
    leaf_titles = {node["title"]: node["number"] for node in skeleton if node.get("leaf")}
    mounts: dict[str, list[str]] = {}
    used: set[str] = set()
    problems: list[str] = []
    duplicate_refs: set[str] = set()
    for entry in raw_mounts if isinstance(raw_mounts, list) else []:
        if not isinstance(entry, dict):
            continue
        key = re.sub(r"\s", "", str(entry.get("node") or entry.get("number") or ""))
        if key not in leaf_numbers:
            title_key = str(entry.get("node") or entry.get("title") or "").strip()
            key = leaf_titles.get(title_key, "")
        if key not in leaf_numbers:
            if entry.get("refs"):
                problems.append("non_leaf_node")
            continue
        refs: list[str] = []
        for ref in _expand_refs(entry.get("refs"), index):
            if ref in used:
                duplicate_refs.add(ref)
                continue
            refs.append(ref)
        if not refs:
            continue
        used.update(refs)
        bucket = mounts.setdefault(key, [])
        for ref in refs:
            if ref not in bucket:
                bucket.append(ref)
    if duplicate_refs:
        problems.append("duplicate_refs:" + "、".join(sorted(duplicate_refs)[:20]))
    return mounts, sorted(set(problems))


def _expected_refs(digest: dict) -> list[str]:
    expected = [item["id"] for item in digest.get("tech") or []]
    for group in digest.get("scoring") or []:
        expected += [point["id"] for point in group["points"]]
    return expected


def _ref_weights(digest: dict) -> dict[str, float]:
    """挂载候选择优权重。技术条款为 1；评分点按分值加权，避免模型为了凑 T 编号
    而牺牲 60/30/15 分核心评分项。权重只用于在多次模型输出之间仲裁，不改变清单事实。"""
    weights = {item["id"]: 1.0 for item in digest.get("tech") or []}
    for group in digest.get("scoring") or []:
        score = group.get("score") if isinstance(group.get("score"), (int, float)) else 0
        weight = 1.0 + float(score) / 5.0
        weights[group["id"]] = weight
        for point in group.get("points") or []:
            weights[point["id"]] = weight
    return weights


def _mount_score(mounts: dict[str, list[str]], weights: dict[str, float]) -> tuple[float, int]:
    refs = {ref for refs in mounts.values() for ref in refs}
    return sum(weights.get(ref, 1.0) for ref in refs), len(refs)


def _mount_quality(mounts: dict[str, list[str]], weights: dict[str, float]) -> tuple[float, int]:
    """候选质量：覆盖评分权重优先，但重罚把高分评分点和技术条款集中倒进同一叶子的输出。
    否则模型只要把大多数编号堆进一个宽泛章节就能获得高覆盖分，违背全量均衡挂载目标。"""
    total, count = _mount_score(mounts, weights)
    leaf_weights = [sum(weights.get(ref, 1.0) for ref in refs) for refs in mounts.values()]
    concentration = max(leaf_weights, default=0.0)
    empty_penalty = 0.0
    return total - concentration * 1.5 - empty_penalty, count


def _merge_missing_mounts(
    best: dict[str, list[str]], candidates: list[dict[str, list[str]]], expected: list[str],
) -> dict[str, list[str]]:
    """多次模型输出都是候选证据；重试耗尽后，把最佳候选漏挂、但其他候选已挂上的编号
    按模型给出的叶子位置补入。只补缺失编号，不覆盖最佳候选已有位置，不用规则猜章节。"""
    merged = {node: list(refs) for node, refs in best.items()}
    mounted = {ref for refs in merged.values() for ref in refs}
    for candidate in candidates:
        for node, refs in candidate.items():
            for ref in refs:
                if ref in expected and ref not in mounted:
                    merged.setdefault(node, []).append(ref)
                    mounted.add(ref)
    return merged


def prune_empty_skeleton(
    skeleton: list[dict], mounts: dict[str, list[str]],
) -> tuple[list[dict], dict[str, list[str]]]:
    """裁掉无挂载空叶子及因此变空的父节点，并同步重编号与 mounts 键。
    空叶子不进入可生成目录，避免整卷生成写入「待补」占位正文。"""
    keep: set[int] = set()
    for index, node in enumerate(skeleton):
        if not node.get("leaf") or not mounts.get(node.get("number")):
            continue
        keep.add(index)
        floor = int(node.get("level") or 1)
        for parent in range(index - 1, -1, -1):
            level = int(skeleton[parent].get("level") or 1)
            if level < floor:
                keep.add(parent)
                floor = level
                if floor == 1:
                    break
    ordered = sorted(keep)
    if not ordered:
        return [], {}
    renumbered = _number_skeleton([
        {"level": skeleton[index]["level"], "title": skeleton[index]["title"]}
        for index in ordered
    ])
    number_map: dict[str, str] = {}
    for position, index in enumerate(ordered):
        number_map[str(skeleton[index].get("number") or "")] = renumbered[position]["number"]
    remapped: dict[str, list[str]] = {}
    for node, refs in mounts.items():
        new_node = number_map.get(node)
        if new_node and refs:
            remapped[new_node] = list(refs)
    return renumbered, remapped


def _max_leaf_share(mounts: dict[str, list[str]], expected_count: int) -> float:
    return max((len(refs) for refs in mounts.values()), default=0) / max(1, expected_count)


def _select_merged_mounts(
    candidates: list[dict[str, list[str]]], expected: list[str], weights: dict[str, float], leaf_count: int,
) -> dict[str, list[str]] | None:
    """重试耗尽后在多次模型输出间仲裁。合并只在集中度门槛内接受；
    合并会把某叶推回倾倒状态时，宁可换平衡候选或显式失败，也不产出失真目录。"""
    ordered = sorted(candidates, key=lambda item: _mount_quality(item, weights), reverse=True)
    best: dict[str, list[str]] | None = None
    best_key: tuple[float, int] = (-1.0, -1)
    enforce_share = leaf_count >= 3
    for base in ordered:
        merged = _merge_missing_mounts(base, ordered, expected)
        if enforce_share and _max_leaf_share(merged, len(expected)) > MAX_LEAF_SHARE:
            continue
        quality, count = _mount_quality(merged, weights)
        if (quality, count) > best_key:
            best, best_key = merged, (quality, count)
    return best


def _digest_text(digest: dict, ref: str) -> str:
    for item in digest.get("tech") or []:
        if item["id"] == ref:
            return str(item.get("text") or "")
    for group in digest.get("scoring") or []:
        if group["id"] == ref:
            return str(group.get("item") or "")
        for point in group["points"]:
            if point["id"] == ref:
                return str(point.get("text") or "")
    return ""


# ---------------------------------------------------------------- 树构建与出参
def _points_for_refs(refs: list[str], digest: dict, index: dict[str, list[str]]) -> tuple[list[dict], list[str]]:
    """挂载编号 → 确定性响应要点（逐条 1:1，文本取清单原文，不编造）；组级编号展开到得分要点。"""
    points: list[dict] = []
    requirement_ids: list[str] = []
    for ref in refs:
        rids = list(index.get(ref) or [])
        if not rids:
            continue
        expanded = [ref]
        # 组级 S-xx 展开到点级，保证每个得分要点单独成条可追溯。
        for group in digest.get("scoring") or []:
            if group["id"] == ref and group["points"]:
                expanded = [point["id"] for point in group["points"]]
                break
        for leaf_ref in expanded:
            text = _digest_text(digest, leaf_ref)[:60]
            if text:
                points.append({"text": text, "refs": [leaf_ref]})
            for rid in index.get(leaf_ref) or []:
                if rid not in requirement_ids:
                    requirement_ids.append(rid)
    return points, requirement_ids


def build_from_mounts(workflow: dict, digest: dict, skeleton: list[dict], mounts: dict[str, list[str]]) -> dict[str, Any]:
    """骨架 + 全量挂载 → 目录任务/标题。漏挂编号只进校验与未挂载池，绝不倾倒兜底章。"""
    from icg.domain.technical_response_plan import validate_plan

    index = digest_index(digest)
    expected = _expected_refs(digest)
    mounted_refs = sorted({ref for refs in mounts.values() for ref in refs})
    missing_refs = [ref for ref in expected if ref not in mounted_refs]
    reqs = workflow.get("requirements") or {}
    rejection_ids = [
        row["id"] for row in reqs.values()
        if row.get("is_rejection_criterion") and row.get("technical_clause")
        and row.get("requirement_type") != "qualification" and row.get("status") != "rejected"
    ]
    headings: list[dict] = []
    tasks: list[dict] = []
    for node in skeleton:
        heading = {"level": node["level"], "number": node["number"], "title": node["title"]}
        if node.get("leaf"):
            refs = mounts.get(node["number"]) or []
            points, rids = _points_for_refs(refs, digest, index)
            task_id = new_id("task")
            heading.update({
                "requirement_id": rids[0] if rids else None, "task_id": task_id,
                "requirement_ids": rids, "mount_ids": list(rids),
                "score_refs": [rid for rid in rids if (reqs.get(rid) or {}).get("section_kind") == "scoring"],
                "constraint_ids": [], "points": points,
            })
            tasks.append({
                "task_id": task_id, "title": node["title"], "theme": node["title"],
                "requirement_ids": rids, "response_strategy": "point_by_point",
                "response_points": [point["text"] for point in points],
                "digest_refs": sorted({ref for point in points for ref in point["refs"] if ref}),
                "rejection_requirement_ids": list(rejection_ids), "constraint_ids": [],
                "generation_status": "pending", "response_status": "not_started",
                "verification_status": "unchecked", "outline_number": node["number"], "chapter_id": None,
            })
        headings.append(heading)
    missing_rids = sorted({rid for ref in missing_refs for rid in (index.get(ref) or [])})
    rows = [
        row for row in reqs.values()
        if row.get("technical_clause") and row.get("status") != "rejected"
    ]
    check = validate_plan(rows, tasks, headings)
    check["unmounted_digest_refs"] = missing_refs
    check["patched_requirement_ids"] = []
    if missing_refs:
        check["issues"] = list(check.get("issues") or []) + [
            f"{len(missing_refs)} 条清单编号未挂载，保留在未挂载池"
        ]
    return {"tasks": tasks, "headings": headings, "validation": check}


# ---------------------------------------------------------------- 模型调用与重试
def _call_json(model: Any, system: str, user: str) -> str:
    from icg.infra.openai_model import TREE_CALL, call_with_profile

    return str(call_with_profile(model.suggest, system, user, profile=TREE_CALL) or "")


def _failure_record(stage: str, attempts: int, detail: dict[str, Any] | None, invalid: bool) -> dict[str, Any]:
    record = {
        "stage": stage,
        "attempts": attempts,
        "invalid_output": invalid,
        "timeout": bool((detail or {}).get("timeout")),
        "type": (detail or {}).get("type") or "",
        "message": (detail or {}).get("message") or "",
        "chain": (detail or {}).get("chain") or [],
    }
    return record


def _stage_skeleton(workflow: dict, digest: dict, model: Any) -> tuple[list[dict], dict[str, Any] | None]:
    user = skeleton_user(workflow, digest)
    last_error: dict[str, Any] | None = None
    invalid = False
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            raw = _call_json(model, SKELETON_SYSTEM, user)
        except Exception as exc:
            last_error = _error_detail(exc)
            continue
        payload = repair_json_payload(raw)
        skeleton = _normalize_skeleton(payload.get("nodes") or payload.get("outline") or [])
        if skeleton:
            return skeleton, None
        invalid = True
        last_error = None
    return [], _failure_record("skeleton", MAX_ATTEMPTS, last_error, invalid)


def _stage_mount(
    workflow: dict, digest: dict, model: Any, skeleton: list[dict], index: dict[str, list[str]],
) -> tuple[dict[str, list[str]], dict[str, Any] | None]:
    expected = _expected_refs(digest)
    feedback = ""
    last_error: dict[str, Any] | None = None
    invalid = False
    best: dict[str, list[str]] = {}
    best_mounted = -1
    best_weighted = -1.0
    candidates: list[dict[str, list[str]]] = []
    weights = _ref_weights(digest)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        user = mount_user(workflow, digest, skeleton, feedback=feedback)
        try:
            raw = _call_json(model, MOUNT_SYSTEM, user)
        except Exception as exc:
            last_error = _error_detail(exc)
            continue
        payload = repair_json_payload(raw)
        mounts, problems = _normalize_mounts(payload.get("mounts") or payload.get("nodes"), skeleton, index)
        if not mounts and expected:
            invalid = True
            last_error = None
            feedback = "上一次输出无法解析或没有有效挂载，必须按指定 JSON 格式输出。"
            continue
        mounted = {ref for refs in mounts.values() for ref in refs}
        missing = [ref for ref in expected if ref not in mounted]
        leaf_count = sum(1 for node in skeleton if node.get("leaf"))
        max_share = max((len(refs) for refs in mounts.values()), default=0) / max(1, len(expected))
        weighted, mounted_count = _mount_quality(mounts, weights)
        candidates.append(mounts)
        if (weighted, mounted_count) > (best_weighted, best_mounted):
            best, best_mounted, best_weighted = mounts, mounted_count, weighted
        problems_text = "；".join(
            item for item in [
                f"未挂载编号 {len(missing)} 个：{'、'.join(missing[:30])}，必须全部挂到叶子节点" if missing else "",
                "node 必须是叶子节点编号" if "non_leaf_node" in problems else "",
                "同一编号重复挂载：" + next((item.split(":", 1)[1] for item in problems if item.startswith("duplicate_refs:")), "") if any(item.startswith("duplicate_refs:") for item in problems) else "",
                f"挂载过度集中在同一节（占 {max_share:.0%}），请按语义均衡分散到各章节" if leaf_count >= 3 and max_share > MAX_LEAF_SHARE else "",
            ] if item
        )
        if not problems_text:
            return mounts, None
        invalid = True
        last_error = None
        feedback = "上一次挂载有问题：" + problems_text + "。请重新输出完整 mounts。"
    if best and best_mounted >= len(expected) * MIN_MOUNT_RATIO:
        # 重试耗尽仍少量漏挂：在同一骨架的多次模型输出之间补缺失编号；
        # 合并后的集中度必须重新过门槛，残余漏挂进未挂载池而非兜底章。
        leaf_count = sum(1 for node in skeleton if node.get("leaf"))
        merged = _select_merged_mounts(candidates, expected, weights, leaf_count)
        if merged is not None:
            return merged, None
        invalid = True
    return {}, _failure_record("mount", MAX_ATTEMPTS, last_error, invalid)


def outline_two_stage(workflow: dict, digest: dict, model: Any) -> dict[str, Any] | None:
    """两阶段模型目录规划。任何阶段重试耗尽仍失败返回 None，失败细节写入 workflow['_outline_model_error']。"""
    workflow.pop("_outline_model_error", None)
    skeleton, failure = _stage_skeleton(workflow, digest, model)
    if not skeleton:
        workflow["_outline_model_error"] = failure
        return None
    index = digest_index(digest)
    mounts, failure = _stage_mount(workflow, digest, model, skeleton, index)
    if failure is not None:
        workflow["_outline_model_error"] = failure
        return None
    skeleton, mounts = prune_empty_skeleton(skeleton, mounts)
    if not skeleton:
        workflow["_outline_model_error"] = _failure_record("mount", MAX_ATTEMPTS, None, True)
        return None
    return build_from_mounts(workflow, digest, skeleton, mounts)


def _failure_reason(record: dict[str, Any] | None) -> str:
    if not record:
        return f"{MODEL_FAILED}。"
    stage = "章节骨架" if record.get("stage") == "skeleton" else "要点挂载"
    if record.get("timeout"):
        cause = "模型调用超时"
    elif record.get("invalid_output") and not record.get("type"):
        cause = "模型输出无法解析或不合法"
    elif record.get("type"):
        cause = f"{record['type']}: {record['message']}"[:120]
    else:
        cause = "模型输出不完整"
    retries = max(0, int(record.get("attempts") or 1) - 1)
    return (
        f"{MODEL_FAILED}（{stage}阶段：{cause}，已自动重试 {retries} 次）。"
        "未生成可用目录，请检查模型服务后点击「重新生成目录」。"
    )


def plan_technical_outline(workflow: dict, model: Any = None) -> dict[str, Any]:
    """主路径：三张清单 → 模型两阶段拟目录。

    没有可用本地模型时（仅解析期草稿）回落规则目录；模型可用但规划失败时绝不静默
    塞入通用规则目录——返回空 plan，失败原因写 workflow，由编排层仅记录错误供前端重试。
    """
    from icg.domain.technical_model_extract import usable_local_model
    from icg.domain.technical_response_plan import apply_response_plan

    digest = build_digest(workflow)
    model = model or workflow.get("tree_model")
    if not usable_local_model(model):
        return apply_response_plan(workflow, model=None)
    plan = outline_two_stage(workflow, digest, model)
    if plan is None or not plan.get("headings"):
        failure = workflow.pop("_outline_model_error", None)
        # 失败语义：outline_source 反映「当前可见目录是什么」。已有模型目录重跑失败时保留 model
        # （旧目录未被覆盖）；首次解析期可见的是规则草稿，标 rule_fallback。绝不新写规则树冒充结果。
        workflow["outline_source"] = workflow.get("outline_source") or "rule_fallback"
        workflow["tree_model_failed"] = True
        workflow["outline_reason"] = _failure_reason(failure)
        workflow["outline_model_error"] = failure or {}
        return {"tasks": [], "headings": [], "validation": {"passed": False, "issues": [workflow["outline_reason"]]}}
    workflow.pop("_outline_model_error", None)
    workflow.pop("outline_model_error", None)
    workflow["response_tasks"] = {task["task_id"]: task for task in plan["tasks"]}
    workflow["plan_validation"] = plan["validation"]
    workflow["outline_source"] = "model"
    workflow["tree_model_failed"] = False
    workflow["outline_reason"] = ""
    return plan
