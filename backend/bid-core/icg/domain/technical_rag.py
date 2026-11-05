# 为什么有这个文件：技术分册节生成强制查 history + material 双库，并留下可审计记录。
# 它解决什么问题：禁止只搜章节标题、禁止缺库静默假成功；查询与命中统计集中在一处。

from __future__ import annotations

from typing import Any

from icg.domain.knowledge_base import dataset_full_name, read_index
from icg.domain.writing_knowledge_prompt import format_retrieved_knowledge_prompt_lines


def section_query(title: str, row: dict | None = None, *, task: dict | None = None, requirements: list[dict] | None = None) -> str:
    """Query = 章节任务 + 招标要求 + 检索目标；禁止只搜标题。"""
    parts = [title.strip()]
    if task:
        points = task.get("response_points") or []
        parts.extend(str(point)[:100] for point in points[:6] if point)
        parts.append(str(task.get("theme") or ""))
    rows = requirements or ([row] if row else [])
    for item in rows[:8]:
        clause = str(item.get("extracted_summary") or item.get("text") or "").strip()
        if clause:
            parts.append(clause[:120])
        point = str(item.get("response") or "").strip()
        if point and point not in clause:
            parts.append(point[:80])
    parts.append("检索目标：企业历史技术方案 实施措施 流程 交付 巡检 故障响应 容灾")
    return " ".join(part for part in parts if part)


def dataset_presence(state: Any, company_id: str) -> dict[str, Any]:
    """编辑台提示用：两库是否已配置（有 dataset_id）。展示解析后的全名。"""
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
    return {
        "history": {"name": history_name, "configured": history_ok},
        "material": {"name": material_name, "configured": material_ok},
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


def knowledge_prompt_block(chunks: list[dict]) -> str:
    lines = format_retrieved_knowledge_prompt_lines(chunks)
    return "\n".join(lines).strip()
