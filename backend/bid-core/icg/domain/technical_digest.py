# 为什么有这个文件：把招标要求整理成技术需求、评分规则、废标三张清单（tender_digest）。
# 它解决什么问题：目录编排、覆盖视图和正文约束共用同一份带编号、可追溯原文的清单。
from __future__ import annotations

from typing import Any

NON_SERVICE_SECTION_KINDS = frozenset({"business", "qualification"})


def _rows(workflow: dict) -> list[dict]:
    return [
        row for row in (workflow.get("requirements") or {}).values()
        if row.get("technical_clause")
        and row.get("status") != "rejected"
        and row.get("section_kind") not in NON_SERVICE_SECTION_KINDS
    ]


def _page(row: dict) -> int | None:
    source = row.get("source") or {}
    return source.get("page") or row.get("page")


def _quote(row: dict) -> str:
    return str((row.get("source") or {}).get("quote") or row.get("text") or "")[:400]


def _rejections(workflow: dict) -> list[dict]:
    sidecar = workflow.get("technical_sidecars") or {}
    items = [item for item in sidecar.get("rejection_items") or [] if isinstance(item, dict)]
    seen = {str(item.get("quote") or "").strip() for item in items}
    for line in sidecar.get("rejection_lines") or []:
        text = str(line or "").strip()
        if text and text not in seen:
            seen.add(text)
            items.append({"text": text[:80], "quote": text, "page": None, "category": ""})
    return items


def build_digest(workflow: dict) -> dict[str, Any]:
    """三张清单。编号按出现顺序：T-01、S-01（得分要点 S-01-1）、R-01；要求行回写 digest_id。"""
    tech: list[dict] = []
    groups: dict[str, dict] = {}
    for row in _rows(workflow):
        if row.get("section_kind") == "scoring":
            name = str(row.get("score_item") or row.get("text") or "").strip()
            group = groups.get(name)
            if group is None:
                group = {
                    "id": f"S-{len(groups) + 1:02d}", "item": name, "score": row.get("score"),
                    "criteria": str(row.get("criteria") or ""), "quote": _quote(row),
                    "page": _page(row), "points": [],
                }
                groups[name] = group
            point_id = f"{group['id']}-{len(group['points']) + 1}"
            group["points"].append({"id": point_id, "text": str(row.get("text") or ""), "requirement_id": row["id"]})
            row["digest_id"] = point_id
            continue
        digest_id = f"T-{len(tech) + 1:02d}"
        tech.append({
            "id": digest_id, "text": str(row.get("extracted_summary") or row.get("text") or ""),
            "quote": _quote(row), "page": _page(row), "requirement_id": row["id"],
            "star": bool(row.get("star") or row.get("is_rejection_criterion")),
        })
        row["digest_id"] = digest_id
    rejection = [
        {
            "id": f"R-{index:02d}", "text": str(item.get("text") or item.get("quote") or "")[:80],
            "quote": str(item.get("quote") or "")[:400], "page": item.get("page"),
            "category": item.get("category") or "",
        }
        for index, item in enumerate(_rejections(workflow), start=1)
    ]
    used_model = bool((workflow.get("technical_extract_model") or {}).get("used"))
    digest = {
        "source": "model" if used_model else "rule",
        "tech": tech,
        "scoring": list(groups.values()),
        "rejection": rejection,
    }
    workflow["tender_digest"] = digest
    return digest


def digest_index(digest: dict) -> dict[str, list[str]]:
    """清单编号 → 要求行 id。S-01 指整项全部得分要点。"""
    index: dict[str, list[str]] = {}
    for item in digest.get("tech") or []:
        index[item["id"]] = [item["requirement_id"]]
    for group in digest.get("scoring") or []:
        index[group["id"]] = [point["requirement_id"] for point in group["points"]]
        for point in group["points"]:
            index[point["id"]] = [point["requirement_id"]]
    return index


def rejection_lines(workflow: dict | None, *, limit: int | None = None) -> list[str]:
    digest = (workflow or {}).get("tender_digest") or {}
    return [
        f"{item['id']} {item['text']}" for item in (digest.get("rejection") or [])[:limit] if item.get("text")
    ]


def scoring_criteria(rows: list[dict]) -> list[str]:
    found: list[str] = []
    for row in rows:
        name = str(row.get("score_item") or "").strip()
        if not name or row.get("section_kind") != "scoring":
            continue
        score = row.get("score")
        criteria = str(row.get("criteria") or "").strip()
        line = name + (f"（{score:g} 分）" if isinstance(score, (int, float)) else "") + (f"：{criteria[:160]}" if criteria else "")
        if line not in found:
            found.append(line)
    return found
