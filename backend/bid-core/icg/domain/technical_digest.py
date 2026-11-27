# 为什么有这个文件：把招标要求整理成技术需求、评分规则、废标三张清单（tender_digest）。
# 它解决什么问题：目录编排、覆盖视图和正文约束共用同一份带编号、可追溯原文的清单。
from __future__ import annotations

from typing import Any

NON_SERVICE_SECTION_KINDS = frozenset({"business", "qualification"})


def _rows(workflow: dict) -> list[dict]:
    """可进技术卷三张清单的条款。商务/资格/格式包装条款只留在商务卷或风险提示，
    不得作为技术目录必须挂载的 T/S 输入。清洗分流（ISSUE-060）落盘的
    non_technical / fragment_filtered 同样拦截，审计原因可区分。"""
    from icg.domain.technical_constraint_context import row_is_non_tech
    from icg.domain.technical_clause_cleaning import SCOPE_FRAGMENT, SCOPE_NON_TECHNICAL

    rows = []
    intercepted = []
    for row in (workflow.get("requirements") or {}).values():
        if not row.get("technical_clause") or row.get("status") == "rejected" or row.get("section_kind") in NON_SERVICE_SECTION_KINDS:
            continue
        scope = str(row.get("requirement_scope") or "")
        if scope in (SCOPE_NON_TECHNICAL, SCOPE_FRAGMENT):
            intercepted.append({
                "requirement_id": row.get("id"),
                "text": str(row.get("extracted_summary") or row.get("text") or "")[:120],
                "reason": "fragment" if scope == SCOPE_FRAGMENT else "non_technical",
                "category": str(row.get("non_tech_category") or ""),
            })
            continue
        if row_is_non_tech(row):
            intercepted.append({
                "requirement_id": row.get("id"),
                "text": str(row.get("extracted_summary") or row.get("text") or "")[:120],
                "reason": "business_or_packaging",
            })
            continue
        rows.append(row)
    if intercepted:
        workflow["business_intercepted_requirements"] = intercepted
    else:
        workflow.pop("business_intercepted_requirements", None)
    return rows


def _page(row: dict) -> int | None:
    source = row.get("source") or {}
    return source.get("page") or row.get("page")


def _file_id(row: dict) -> str:
    return str((row.get("source") or {}).get("file_id") or "")


def _chunk_id(row: dict) -> str:
    return str((row.get("source") or {}).get("chunk_id") or "")


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
            items.append({"text": text[:80], "quote": text, "page": None, "file_id": "", "chunk_id": "", "category": ""})
    return items


def parse_score_table_row(row: dict) -> tuple[str, float | None, str]:
    """从 Markdown/管道表格原文回补评分项名称、分值与评分细则。

    真实招标评分表常见形态：`2 | 服务方案，合计30分 …… | 30分 | 100分`。
    模型抽取可能把同一行拆成多个碎片且丢失 score_item/criteria，目录与正文必须
    以表格原文为唯一评分依据，不能让模型自行发明权重或计算系数。
    """
    quote = str((row.get("source") or {}).get("quote") or "")
    cells = [part.strip() for part in quote.split("|") if part.strip()]
    if len(cells) < 3 or not cells[0].strip().isdigit():
        return (str(row.get("score_item") or "").strip(), row.get("score"), str(row.get("criteria") or "").strip())
    body = cells[1]
    score: float | None = None
    import re
    if len(cells) >= 3:
        matched = re.fullmatch(r"(\d+(?:\.\d+)?)\s*分?", cells[-2])
        if matched:
            score = float(matched.group(1))
    import re
    name_match = re.match(r"(.+?)[，,]?\s*合计\s*\d+(?:\.\d+)?\s*分", body)
    name = name_match.group(1).strip(" ，,") if name_match else str(row.get("score_item") or "").strip()
    criteria = re.sub(r"^.*?[，,]?\s*合计\s*\d+(?:\.\d+)?\s*分\s*", "", body).strip() if name_match else str(row.get("criteria") or "").strip()
    return name, score if score is not None else row.get("score"), criteria


def recover_scoring_table_rows(workflow: dict) -> list[dict]:
    """从已解析招标文件全文中回补漏抽的“方案服务评分表”整行。

    条款抽取器可能漏掉评分表第一行，但正文导出必须完整看到 30/30/20/20 四项技术评分。
    回补行只作为评分清单事实，不伪造 requirement_id。
    """
    recovered: list[dict] = []
    import re
    for file in (workflow.get("files") or {}).values():
        pages = file.get("pages") or []
        text = "\n".join((page.get("text") or "") if isinstance(page, dict) else str(page) for page in pages)
        if "方案服务评分表" not in text:
            continue
        start = text.find("方案服务评分表")
        end = text.find("商务资质评分表", start)
        segment = text[start:end if end > start else start + 8000]
        for line in segment.splitlines():
            if not re.match(r"^\s*\d+\s*\|", line):
                continue
            fake = {"id": "", "text": line.strip(), "section_kind": "scoring", "source": {"quote": line.strip()}}
            name, score, criteria = parse_score_table_row(fake)
            if name and score is not None:
                fake.update({"score_item": name, "score": score, "criteria": criteria})
                recovered.append(fake)
    return recovered


def is_score_table_row(row: dict) -> bool:
    """只把真正来自评分表的行归入 S 清单。

    真实数据中 `section_kind` 会在评分章节后持续漂移，导致大量技术服务条款被误标 scoring。
    评分表行的硬特征是管道表 `序号 | 评审因素 | 分值 | 满分`，或已经抽到明确 score_item+score。
    """
    quote = str((row.get("source") or {}).get("quote") or "")
    import re
    if re.match(r"^\s*\d+\s*\|.+\|.+\|", quote) and "分" in quote:
        return True
    return bool(str(row.get("score_item") or "").strip() and row.get("score") is not None)


def build_digest(workflow: dict) -> dict[str, Any]:
    """三张清单。编号按出现顺序：T-01、S-01（得分要点 S-01-1）、R-01；要求行回写 digest_id。"""
    from icg.domain.technical_clause_cleaning import clean_technical_requirements

    # 清洗分流幂等重跑：残句补全/过滤与非技术标记在进清单前落定（ISSUE-060）。
    clean_technical_requirements(workflow)
    tech: list[dict] = []
    groups: dict[str, dict] = {}
    for row in _rows(workflow):
        if row.get("section_kind") == "scoring" and is_score_table_row(row):
            parsed_name, parsed_score, parsed_criteria = parse_score_table_row(row)
            if parsed_name and not row.get("score_item"):
                row["score_item"] = parsed_name
            if parsed_score is not None and row.get("score") is None:
                row["score"] = parsed_score
            if parsed_criteria and not row.get("criteria"):
                row["criteria"] = parsed_criteria
            name = str(row.get("score_item") or row.get("text") or "").strip()
            group = groups.get(name)
            if group is None:
                group = {
                    "id": f"S-{len(groups) + 1:02d}", "item": name, "score": row.get("score"),
                    "criteria": str(row.get("criteria") or ""), "quote": _quote(row),
                    "page": _page(row), "file_id": _file_id(row), "chunk_id": _chunk_id(row), "points": [],
                }
                groups[name] = group
            point_id = f"{group['id']}-{len(group['points']) + 1}"
            group["points"].append({
                "id": point_id, "text": str(row.get("text") or ""), "requirement_id": row["id"],
                "quote": _quote(row), "page": _page(row), "chunk_id": _chunk_id(row),
            })
            row["digest_id"] = point_id
            continue
        digest_id = f"T-{len(tech) + 1:02d}"
        tech.append({
            "id": digest_id, "text": str(row.get("extracted_summary") or row.get("text") or ""),
            "quote": _quote(row), "page": _page(row), "file_id": _file_id(row), "chunk_id": _chunk_id(row),
            "requirement_id": row["id"],
            "star": bool(row.get("star") or row.get("is_rejection_criterion")),
        })
        row["digest_id"] = digest_id
    # 评分表整行回补：抽条器漏掉的评分项仍进入 scoring 清单，保证 30/30/20/20 不缺项。
    for recovered in recover_scoring_table_rows(workflow):
        name = str(recovered.get("score_item") or "")
        if not name or name in groups:
            continue
        group = {
            "id": f"S-{len(groups) + 1:02d}", "item": name, "score": recovered.get("score"),
            "criteria": str(recovered.get("criteria") or ""), "quote": _quote(recovered),
            "page": _page(recovered), "file_id": _file_id(recovered), "chunk_id": _chunk_id(recovered), "points": [],
        }
        groups[name] = group
    rejection = [
        {
            "id": f"R-{index:02d}", "text": str(item.get("text") or item.get("quote") or "")[:80],
            "quote": str(item.get("quote") or "")[:400], "page": item.get("page"),
            "file_id": str(item.get("file_id") or ""), "chunk_id": str(item.get("chunk_id") or ""),
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
