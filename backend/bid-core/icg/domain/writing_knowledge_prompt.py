# 为什么有这个文件：写作 Prompt 中本标项目事实、历史标书与权威资料的分组标题与渲染。
# 它解决什么问题：招标切片只提供项目事实。chapter_generation 与 prompt_budget 共用分组规则，避免循环依赖。
# 历史切片在入 Prompt 前去掉外项目专名。本标业主和系统名保留，history_hits 不在这里扣减。

from __future__ import annotations

import re
from typing import Any

TENDER_HEADING = "本标项目事实：业主、系统、期限、SLA 与约束。只用于认清本项目，禁止复述或改写成投标正文。写入约束时保留对应 [标:]。"
HISTORY_HEADING = (
    "历史技术方案参考：只借鉴写法、步骤和结构。"
    "业主、系统、SLA 与期限以本标招标和项目事实为准。"
    "外项目专名直接省略，不要写进投标正文，也不要写成【待补】。来源已脱敏，仅供参考。"
)
MATERIALS_HEADING = "企业权威资料：产品说明书、技术参数、企业实际能力等事实依据。"
# 空串表示省略专名。写成【待补】会把占位符抄进正文。
FOREIGN_NAME_PLACEHOLDER = ""
# 后缀先写长的。前缀非贪婪，避免把步骤句和专名吞成一块。
_FOREIGN_ENTITY = re.compile(
    r"[\u4e00-\u9fff]{2,8}?(?:农村信用社|农信社|农信|信用社|人民医院|中医院|卫生院|医院|银行)"
)
_IDENTITY_KEYS = frozenset({
    "采购人", "招标人", "业主", "采购单位", "客户名称", "customer_name",
    "项目名称", "采购项目名称", "招标项目名称", "project_name",
    "系统名称", "系统名",
})
CAPABILITY_GAP_LINE = "企业历史标书与权威资料：无命中。能力、人员、流程和案例标【待确认】。禁止用本标项目事实冒充我方能力。本标业主、系统名、期限和 SLA 不要写成【待补】。"


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
    role = "项目事实" if retrieved_chunk_dataset_kind(chunk) == "tender" else "检索切片"
    return [
        f"{chunk.get('cite_tag') or tag} {title}{role}{prov}{ref_notice}：",
        f"  {chunk.get('content', '')}",
    ]


def _fact_items(workflow: dict | None) -> list[dict]:
    facts = (workflow or {}).get("facts") or {}
    items = facts.values() if isinstance(facts, dict) else facts
    if not isinstance(items, list):
        items = list(items)
    return [item for item in items if isinstance(item, dict)]


def _entity_spans(text: str) -> list[str]:
    found: list[str] = []
    for match in _FOREIGN_ENTITY.finditer(text or ""):
        name = match.group(0)
        if name not in found:
            found.append(name)
    return found


def _name_allowed(name: str, allowed: set[str]) -> bool:
    for item in allowed:
        if name == item or name in item:
            return True
        if len(item) >= 4 and item in name:
            return True
    return False


def allowed_identity_names(workflow: dict | None, chunks: list[dict[str, Any]] | None = None) -> set[str]:
    names: set[str] = set()
    for fact in _fact_items(workflow):
        if str(fact.get("status") or "") == "rejected":
            continue
        value = str(fact.get("value") or "").strip()
        if len(value) < 2:
            continue
        if str(fact.get("key") or "").strip() in _IDENTITY_KEYS:
            names.add(value)
        names.update(_entity_spans(value))
    for chunk in chunks or []:
        if retrieved_chunk_dataset_kind(chunk) != "tender":
            continue
        names.update(_entity_spans(f"{chunk.get('name') or ''}\n{chunk.get('content') or ''}"))
    for record in ((workflow or {}).get("files") or {}).values():
        if not isinstance(record, dict):
            continue
        for page in record.get("pages") or []:
            text = page if isinstance(page, str) else str((page or {}).get("text") or "")
            names.update(_entity_spans(text))
    return {name for name in names if len(name) >= 2}


def foreign_entity_names(texts: list[str], allowed: set[str]) -> list[str]:
    found: list[str] = []
    for text in texts:
        for name in _entity_spans(text):
            if _name_allowed(name, allowed) or name in found:
                continue
            found.append(name)
    found.sort(key=len, reverse=True)
    return found


def history_foreign_names(chunks: list[dict[str, Any]], workflow: dict | None = None) -> list[str]:
    allowed = allowed_identity_names(workflow, chunks)
    texts = [
        f"{chunk.get('name') or ''}\n{chunk.get('content') or ''}"
        for chunk in chunks
        if retrieved_chunk_dataset_kind(chunk) == "history"
    ]
    return foreign_entity_names(texts, allowed)


def mask_foreign_names(text: str, names: list[str]) -> str:
    masked = text or ""
    for name in names:
        if name:
            masked = masked.replace(name, FOREIGN_NAME_PLACEHOLDER)
    return masked


def format_retrieved_knowledge_prompt_lines(
    retrieved: list[dict[str, Any]],
    workflow: dict | None = None,
) -> list[str]:
    if not retrieved:
        return []
    tender = [chunk for chunk in retrieved if retrieved_chunk_dataset_kind(chunk) == "tender"]
    history = [chunk for chunk in retrieved if retrieved_chunk_dataset_kind(chunk) == "history"]
    materials = [chunk for chunk in retrieved if retrieved_chunk_dataset_kind(chunk) == "materials"]
    foreign = history_foreign_names(retrieved, workflow) if history else []
    lines: list[str] = []
    if tender:
        lines.append(TENDER_HEADING)
        for chunk in tender:
            lines.extend(_retrieved_chunk_prompt_lines(chunk))
        lines.append("")
    if history:
        lines.append(HISTORY_HEADING)
        for chunk in history:
            rendered = _retrieved_chunk_prompt_lines({**chunk, "reference_only": True})
            if foreign:
                rendered = [mask_foreign_names(line, foreign) for line in rendered]
            lines.extend(rendered)
        lines.append("")
    if materials:
        lines.append(MATERIALS_HEADING)
        for chunk in materials:
            lines.extend(_retrieved_chunk_prompt_lines(chunk))
        lines.append("")
    if not history and not materials:
        lines.append(CAPABILITY_GAP_LINE)
    return lines
