# 为什么有这个文件：用三张清单一次调用模型拟 1～4 级目录，并把响应要点挂到叶子节点。
# 它解决什么问题：替代「规则归主题 + 大段修补」主路径；只做轻量确定性校验，失败回落旧规则目录。
from __future__ import annotations

import re
from typing import Any

from icg.domain.domain import new_id
from icg.domain.technical_digest import build_digest, digest_index

OUTLINE_SYSTEM = (
    "你在为技术服务方案拟目录。只输出 JSON："
    '{"nodes":[{"level":1,"title":"…","points":[{"text":"…","refs":["S-01-1","T-03"]}]}]}。'
    "level 为 1～4，按阅读顺序排列，不跳级。title 是不超过 16 字的章节名，不抄条款原文，不带编号。"
    "points 只挂在最末级节点上，每条是本节要回应的要点（不超过 30 字），refs 写它回应的清单编号。"
    "每个技术需求 T 和每个得分要点 S-x-y 都必须至少挂到一个节点。评分项尽量单独成节，便于评委对照打分。"
    "废标清单 R 只作红线，不单独成章。联合体、转包分包、投标文件份数、报名材料、资格条件、投标有效期、保证金、报价、格式装订等商务/资格/格式条款不得写成技术目录章节。若给出编制顺序，一级标题按它排。禁止编造清单外的服务和指标。"
)
FALLBACK_TITLE = "其他服务承诺"
MODEL_FAILED = "模型拟目录失败，已用规则目录。"
MIN_MOUNT_RATIO = 0.5
TITLE_LIMIT = 18


def outline_user(workflow: dict, digest: dict) -> str:
    facts = workflow.get("technical_facts") or {}
    order = ((workflow.get("technical_sidecars") or {}).get("format_lines") or [])[:12]
    lines = [f"项目：{facts.get('客户名') or ''} {facts.get('项目理解') or ''}".strip()]
    if order:
        lines.append("编制顺序：" + "；".join(str(item) for item in order))
    lines.append("技术需求清单：")
    lines += [f"{item['id']} {item['text']}" for item in digest.get("tech") or []] or ["（无）"]
    lines.append("评分规则清单：")
    for group in digest.get("scoring") or []:
        score = f"（{group['score']:g} 分）" if isinstance(group.get("score"), (int, float)) else ""
        lines.append(f"{group['id']} {group['item']}{score}：{str(group.get('criteria') or '')[:120]}")
        lines += [f"  {point['id']} {point['text']}" for point in group["points"]]
    if not digest.get("scoring"):
        lines.append("（无）")
    lines.append("废标清单（只作红线）：")
    lines += [f"{item['id']} {item['text']}" for item in digest.get("rejection") or []] or ["（无）"]
    return "\n".join(lines)


def _title(raw: Any) -> str:
    from icg.domain.technical_response_plan import short_chapter_title

    text = re.sub(r"^(?:\d+(?:\.\d+)*|[一二三四五六七八九十]+[、.．])\s*", "", str(raw or "").strip())
    return short_chapter_title(text) if len(text) > TITLE_LIMIT else text


def _points(raw: Any, index: dict[str, list[str]]) -> list[dict]:
    found = []
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, str):
            item = {"text": item, "refs": []}
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()[:60]
        raw_refs = item.get("refs")
        raw_refs = raw_refs if isinstance(raw_refs, list) else [raw_refs] if raw_refs else []
        refs = [re.sub(r"\s", "", str(ref).upper()) for ref in raw_refs]
        refs = [ref for ref in refs if ref in index]
        if text and refs:
            found.append({"text": text, "refs": refs})
    return found


def _normalize(nodes: list, index: dict[str, list[str]]) -> list[dict]:
    out: list[dict] = []
    for node in nodes if isinstance(nodes, list) else []:
        if not isinstance(node, dict):
            continue
        title = _title(node.get("title"))
        if not title:
            continue
        try:
            level = int(node.get("level") or 1)
        except (TypeError, ValueError):
            level = 1
        level = 1 if not out else max(1, min(level, out[-1]["level"] + 1, 4))
        out.append({"level": level, "title": title, "points": _points(node.get("points"), index)})
    for position, node in enumerate(out):
        if node["points"] and not _is_leaf(out, position):
            target = next(j for j in range(position + 1, len(out)) if _is_leaf(out, j))
            out[target]["points"] = node["points"] + out[target]["points"]
            node["points"] = []
    changed = True
    while changed:
        changed = False
        for position in range(len(out) - 1, -1, -1):
            if _is_leaf(out, position) and not out[position]["points"]:
                del out[position]
                changed = True
    return out


def _is_leaf(nodes: list[dict], position: int) -> bool:
    return position + 1 >= len(nodes) or nodes[position + 1]["level"] <= nodes[position]["level"]


def _number(nodes: list[dict]) -> None:
    counters = [0, 0, 0, 0]
    for node in nodes:
        level = node["level"]
        counters[level - 1] += 1
        for deeper in range(level, 4):
            counters[deeper] = 0
        node["number"] = ".".join(str(value) for value in counters[:level])


def build_from_nodes(workflow: dict, digest: dict, nodes: list) -> dict[str, Any] | None:
    from icg.domain.technical_response_plan import validate_plan

    index = digest_index(digest)
    tree = _normalize(nodes, index)
    expected = [rid for item in digest.get("tech") or [] for rid in [item["requirement_id"]]]
    expected += [point["requirement_id"] for group in digest.get("scoring") or [] for point in group["points"]]
    mounted = {rid for node in tree for point in node["points"] for ref in point["refs"] for rid in index[ref]}
    if not tree or (expected and len(mounted & set(expected)) < len(expected) * MIN_MOUNT_RATIO):
        return None
    reqs = workflow.get("requirements") or {}
    missing = [rid for rid in expected if rid not in mounted]
    if missing:
        tree.append({"level": 1, "title": FALLBACK_TITLE, "points": [
            {"text": str((reqs.get(rid) or {}).get("text") or "")[:60], "refs": [str((reqs.get(rid) or {}).get("digest_id") or "")],
             "patched": True}
            for rid in missing
        ]})
    _number(tree)
    rejection_ids = [
        row["id"] for row in reqs.values()
        if row.get("is_rejection_criterion") and row.get("technical_clause")
        and row.get("requirement_type") != "qualification" and row.get("status") != "rejected"
    ]
    headings: list[dict] = []
    tasks: list[dict] = []
    for position, node in enumerate(tree):
        heading = {"level": node["level"], "number": node["number"], "title": node["title"]}
        if _is_leaf(tree, position):
            rids: list[str] = []
            for point in node["points"]:
                for ref in point["refs"]:
                    for rid in index.get(ref) or []:
                        if rid not in rids:
                            rids.append(rid)
            if not rids:
                rids = [rid for rid in missing if rid in reqs] if node["title"] == FALLBACK_TITLE else []
            task_id = new_id("task")
            heading.update({
                "requirement_id": rids[0] if rids else None, "task_id": task_id,
                "requirement_ids": rids, "mount_ids": list(rids),
                "score_refs": [rid for rid in rids if (reqs.get(rid) or {}).get("section_kind") == "scoring"],
                "constraint_ids": [], "points": node["points"],
            })
            tasks.append({
                "task_id": task_id, "title": node["title"], "theme": node["title"],
                "requirement_ids": rids, "response_strategy": "point_by_point",
                "response_points": [point["text"] for point in node["points"]],
                "digest_refs": sorted({ref for point in node["points"] for ref in point["refs"] if ref}),
                "rejection_requirement_ids": list(rejection_ids), "constraint_ids": [],
                "generation_status": "pending", "response_status": "not_started",
                "verification_status": "unchecked", "outline_number": node["number"], "chapter_id": None,
            })
        headings.append(heading)
    rows = [row for row in reqs.values() if row.get("technical_clause") and row.get("status") != "rejected"]
    check = validate_plan(rows, tasks, headings)
    check["patched_requirement_ids"] = missing
    return {"tasks": tasks, "headings": headings, "validation": check}


def outline_from_digest(workflow: dict, digest: dict, model: Any) -> dict[str, Any] | None:
    from icg.domain.technical_model_extract import _parse_payload
    from icg.infra.openai_model import TREE_CALL, call_with_profile

    user = outline_user(workflow, digest)
    for _ in range(2):
        try:
            raw = call_with_profile(model.suggest, OUTLINE_SYSTEM, user, profile=TREE_CALL)
        except Exception:
            continue
        payload = _parse_payload(str(raw or ""))
        try:
            plan = build_from_nodes(workflow, digest, payload.get("nodes") or payload.get("outline") or [])
        except (TypeError, ValueError, KeyError, AttributeError):
            plan = None
        if plan is not None:
            return plan
    return None


def plan_technical_outline(workflow: dict, model: Any = None) -> dict[str, Any]:
    """主路径：三张清单 → 模型一次拟目录；没有本地模型或模型失败时回落旧规则目录。"""
    from icg.domain.technical_model_extract import usable_local_model
    from icg.domain.technical_response_plan import apply_response_plan

    digest = build_digest(workflow)
    model = model or workflow.get("tree_model")
    if not usable_local_model(model):
        return apply_response_plan(workflow, model=model)
    plan = outline_from_digest(workflow, digest, model)
    if plan is None:
        held = workflow.pop("tree_model", None)
        try:
            plan = apply_response_plan(workflow, model=None)
        finally:
            if held is not None:
                workflow["tree_model"] = held
        workflow["outline_source"] = "rule_fallback"
        workflow["tree_model_failed"] = True
        workflow["outline_reason"] = MODEL_FAILED
        return plan
    workflow["response_tasks"] = {task["task_id"]: task for task in plan["tasks"]}
    workflow["plan_validation"] = plan["validation"]
    workflow["outline_source"] = "model"
    workflow["tree_model_failed"] = False
    workflow["outline_reason"] = ""
    return plan
