# 为什么有这个文件：写作 Prompt 中历史标书与权威资料检索块的分组标题与渲染。
# 它解决什么问题：chapter_generation 与 prompt_budget 共用同一套分组规则，避免循环依赖。

from __future__ import annotations

from typing import Any

TENDER_HEADING = "本标招标原文：只陈述这份招标里出现的业主、系统、期限和条款。"
HISTORY_HEADING = "历史技术方案参考：过去项目中的优秀技术表述和实施方法。"
MATERIALS_HEADING = "企业权威资料：产品说明书、技术参数、企业实际能力等事实依据。"


def retrieved_chunk_dataset_kind(chunk: dict[str, Any]) -> str:
    kind = str(chunk.get("dataset_kind") or "").strip()
    if kind in ("tender", "history", "materials"):
        return kind
    if str(chunk.get("cite_tag") or "").startswith("[标:"):
        return "tender"
    return "history" if chunk.get("reference_only") else "materials"


def _retrieved_chunk_prompt_lines(chunk: dict[str, Any]) -> list[str]:
    tag = chunk.get("tag", "[片]")
    chunk_id = chunk.get("chunk_id", chunk.get("id", ""))
    doc_id = chunk.get("document_id", "")
    prov_parts = []
    if chunk_id:
        prov_parts.append(f"chunk_id: {chunk_id}")
    if doc_id:
        prov_parts.append(f"document_id: {doc_id}")
    prov = f"（{', '.join(prov_parts)}）" if prov_parts else ""
    ref_notice = "【仅供参考，不得作为正式附着证据】" if chunk.get("reference_only") else ""
    name = chunk.get("name") or ""
    title = f"{name} · " if name else ""
    return [
        f"{chunk.get('cite_tag') or tag} {title}检索切片{prov}{ref_notice}：",
        f"  {chunk.get('content', '')}",
    ]


def format_retrieved_knowledge_prompt_lines(retrieved: list[dict[str, Any]]) -> list[str]:
    if not retrieved:
        return []
    tender = [chunk for chunk in retrieved if retrieved_chunk_dataset_kind(chunk) == "tender"]
    history = [chunk for chunk in retrieved if retrieved_chunk_dataset_kind(chunk) == "history"]
    materials = [chunk for chunk in retrieved if retrieved_chunk_dataset_kind(chunk) == "materials"]
    lines: list[str] = []
    if tender:
        lines.append(TENDER_HEADING)
        for chunk in tender:
            lines.extend(_retrieved_chunk_prompt_lines(chunk))
        lines.append("")
    if history:
        lines.append(HISTORY_HEADING)
        for chunk in history:
            lines.extend(_retrieved_chunk_prompt_lines(chunk))
        lines.append("")
    if materials:
        lines.append(MATERIALS_HEADING)
        for chunk in materials:
            lines.extend(_retrieved_chunk_prompt_lines(chunk))
        lines.append("")
    return lines
