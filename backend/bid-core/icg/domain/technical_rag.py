# 为什么有这个文件：技术分册节生成先查本标切片，再查公司 history 与 materials，并留下可审计记录。
# 它解决什么问题：检索词只用节标题，禁止把招标原文写进 query，禁止把招标页写进公司库，禁止缺库静默假成功。
# 含外项目专名的历史命中不进入返回列表。history_hits 仍按检索条数计。Prompt 里的 history 只留最高分 3 条，每条正文最多 400 字。

from __future__ import annotations

import re
from typing import Any

from icg.domain.knowledge_base import dataset_full_name, read_index
from icg.domain.technical_tender_index import retrieve_tender
from icg.domain.writing_knowledge_prompt import (
    format_retrieved_knowledge_prompt_lines,
    history_foreign_names,
    retrieved_chunk_dataset_kind,
)


def section_query(title: str, row: dict | None = None, *, task: dict | None = None, requirements: list[dict] | None = None) -> str:
    """节标题，再加上标题里至多 3 个不少于 2 字的词。招标原文不进入检索词。"""
    del row, task, requirements
    heading = str(title or "").strip()
    words: list[str] = []
    for token in re.findall(r"[0-9A-Za-z]{2,}|[\u4e00-\u9fff]{2,}", heading):
        if token == heading or token in words:
            continue
        words.append(token)
        if len(words) == 3:
            break
    if not words:
        return heading
    return f"{heading} {' '.join(words)}"


def dataset_presence(state: Any, company_id: str, workflow: dict | None = None) -> dict[str, Any]:
    """编辑台提示用：公司双库是否已配置，以及本标索引是否已建。"""
    index = read_index(state, company_id) if state is not None else {}
    datasets = index.get("datasets") or {}
    history_name = dataset_full_name(company_id, "history")
    material_name = dataset_full_name(company_id, "materials")
    history_ok = bool((datasets.get("history") or {}).get("dataset_id"))
    material_ok = bool((datasets.get("materials") or {}).get("dataset_id"))
    missing = []
    if not history_ok:
        missing.append(history_name)
    if not material_ok:
        missing.append(material_name)
    tender = (workflow or {}).get("tender_index") if isinstance(workflow, dict) else None
    tender = tender if isinstance(tender, dict) else {}
    chunks = tender.get("chunks") if isinstance(tender.get("chunks"), list) else []
    count = tender.get("chunk_count")
    if not isinstance(count, int) or isinstance(count, bool):
        count = len(chunks)
    tender_ok = bool(tender.get("dataset_id") or count or chunks)
    return {
        "history": {"name": history_name, "configured": history_ok},
        "material": {"name": material_name, "configured": material_ok},
        "tender": {
            "name": str(tender.get("dataset_name") or ""),
            "configured": tender_ok,
            "backend": str(tender.get("backend") or ""),
        },
        "missing": missing,
        "ready": not missing,
    }


def retrieve_dual(kb: Any, company_id: str, query: str, *, limit: int = 8) -> tuple[list[dict], dict]:
    """两库各检索再合并；返回 prompt 用 hits 与审计行。"""
    audit = {
        "query": query,
        "history_searched": False,
        "material_searched": False,
        "history_hits": 0,
        "material_hits": 0,
        "skip_reason": "",
        "top": [],
    }
    if kb is None:
        audit["skip_reason"] = "knowledge base unavailable"
        return [], audit
    chunks: list[dict] = []
    for kind, label in (("history", "history"), ("materials", "material")):
        try:
            hits, reason = kb.search(company_id, query, limit=max(limit // 2, 4), kinds={kind})
        except Exception as exc:
            audit["skip_reason"] = f"{label}:{type(exc).__name__}"
            hits, reason = [], str(exc)
        audit[f"{label}_searched"] = True
        audit[f"{label}_hits"] = len(hits)
        if reason and not hits and not audit["skip_reason"]:
            audit["skip_reason"] = reason
        for hit in hits:
            chunks.append({
                "id": hit.source_id,
                "name": hit.name,
                "content": hit.content,
                "score": hit.score,
                "dataset_kind": hit.dataset_kind or kind,
                "reference_only": hit.reference_only or kind == "history",
                "document_id": hit.document_id,
                "chunk_id": (hit.chunk_ids or [""])[0],
                "cite_tag": hit.cite_tag,
            })
            if len(audit["top"]) < 8:
                audit["top"].append({"name": hit.name, "dataset_kind": hit.dataset_kind or kind, "score": hit.score})
    chunks.sort(key=lambda item: (-float(item.get("score") or 0), item.get("name") or ""))
    return chunks[:limit], audit


_HISTORY_PROMPT_KEEP = 3
_HISTORY_PROMPT_CHARS = 400


def _chunks_for_prompt(chunks: list[dict]) -> list[dict]:
    """Prompt 只带最高分的 3 条 history，每条正文截到 400 字。招标切片和资料原样保留。"""
    history = [item for item in chunks if retrieved_chunk_dataset_kind(item) == "history"]
    others = [item for item in chunks if retrieved_chunk_dataset_kind(item) != "history"]
    ranked = sorted(history, key=lambda item: float(item.get("score") or 0), reverse=True)
    kept: list[dict] = []
    for item in ranked[:_HISTORY_PROMPT_KEEP]:
        content = str(item.get("content") or "")
        if len(content) <= _HISTORY_PROMPT_CHARS:
            kept.append(item)
            continue
        kept.append({**item, "content": content[:_HISTORY_PROMPT_CHARS]})
    return [*others, *kept]


def knowledge_prompt_block(chunks: list[dict], workflow: dict | None = None) -> str:
    lines = format_retrieved_knowledge_prompt_lines(_chunks_for_prompt(chunks), workflow)
    return "\n".join(lines).strip()


def _demote_foreign_history(
    company_hits: list[dict], tender_hits: list[dict], workflow: dict | None,
) -> tuple[list[dict], list[str]]:
    """含外项目专名的历史切片不返回。招标切片和资料原样保留。专名留给正文遮蔽。"""
    foreign = history_foreign_names([*tender_hits, *company_hits], workflow)
    if not foreign:
        return company_hits, []
    kept: list[dict] = []
    for chunk in company_hits:
        if retrieved_chunk_dataset_kind(chunk) != "history":
            kept.append(chunk)
            continue
        blob = f"{chunk.get('name') or ''} {chunk.get('content') or ''}"
        if any(name in blob for name in foreign):
            continue
        kept.append(chunk)
    return kept, foreign


def retrieve_for_section(
    kb: Any, company_id: str, query: str, workflow: dict | None = None, *, limit: int = 8,
) -> tuple[list[dict], dict]:
    """先检索本标切片，再检索公司双库。两路都有命中时给企业证据留窗口，本标切片不能占满 limit。"""
    tender_hits, tender_audit = retrieve_tender(
        workflow or {}, query, kb=kb, company_id=company_id, limit=limit,
    )
    company_hits, company_audit = retrieve_dual(kb, company_id, query, limit=limit)
    company_hits, foreign_names = _demote_foreign_history(company_hits, tender_hits, workflow)
    if tender_hits and company_hits and limit >= 2:
        company_slots = min(len(company_hits), max(limit // 2, 1))
    else:
        company_slots = min(len(company_hits), limit)
    tender_slots = min(len(tender_hits), max(limit - company_slots, 0))
    merged: list[dict] = []
    seen: set[str] = set()
    for chunk in [*tender_hits[:tender_slots], *company_hits[:company_slots]]:
        cid = str(chunk.get("chunk_id") or chunk.get("id") or "")
        if cid and cid in seen:
            continue
        if cid:
            seen.add(cid)
        merged.append(chunk)
    audit = {
        "query": query,
        "tender_searched": bool(tender_audit.get("tender_searched")),
        "tender_hits": int(tender_audit.get("tender_hits") or 0),
        "tender_dataset": tender_audit.get("tender_dataset") or "",
        "tender_backend": tender_audit.get("tender_backend") or "",
        "history_searched": bool(company_audit.get("history_searched")),
        "material_searched": bool(company_audit.get("material_searched")),
        "history_hits": int(company_audit.get("history_hits") or 0),
        "material_hits": int(company_audit.get("material_hits") or 0),
        "skip_reason": tender_audit.get("skip_reason") or company_audit.get("skip_reason") or "",
        "foreign_names": foreign_names,
        "top": [
            {
                "name": item.get("name"),
                "dataset_kind": retrieved_chunk_dataset_kind(item),
                "score": item.get("score"),
            }
            for item in merged[:8]
        ],
    }
    return merged[:limit], audit
