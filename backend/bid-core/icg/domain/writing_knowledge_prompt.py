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
    "外项目专名省略，或概括为“相关机构/同类项目”。来源已脱敏，仅供参考。"
)
MATERIALS_HEADING = "企业权威资料：产品说明书、技术参数、企业实际能力等事实依据。"
FOREIGN_NAME_PLACEHOLDER = "相关机构"
# 后缀先写长的。覆盖银行、医院、农信社及政企委办局、高校与公司实体全称。
_FOREIGN_ENTITY = re.compile(
    r"[\u4e00-\u9fff]{2,12}?(?:农村商业银行|农商行|农村信用社|农信社|农信|信用社|"
    r"人民医院|中医院|妇幼保健院|卫生院|医院|银行|"
    r"大数据局|政务服务局|财政局|卫健委|公安局|税务局|交通局|人社局|"
    r"有限责任公司|股份有限公司|集团有限公司)"
)
_GENERIC_ENTITY_SKIP = ("我公司", "本公司", "贵公司", "招标", "投标", "采购", "供应")
_IDENTITY_KEYS = frozenset({
    "采购人", "招标人", "业主", "采购单位", "客户名称", "customer_name",
    "项目名称", "采购项目名称", "招标项目名称", "project_name",
    "系统名称", "系统名",
})
CAPABILITY_GAP_LINE = "企业历史标书与权威资料：无命中。能力、人员、流程和案例的真实私有缺口标 [待人工补充：具体项]。禁止用本标项目事实冒充我方能力；本标业主、系统名、期限和 SLA 必须按项目事实直接写明，不得用占位符代替。"
SUBKIND_LABELS = {
    "products": "kb_products",
    "manuals": "kb_manuals",
    "fault_cases": "kb_fault_cases",
    "materials": "kb_materials",
}


def retrieved_chunk_dataset_kind(chunk: dict[str, Any]) -> str:
    kind = str(chunk.get("dataset_kind") or "").strip()
    if kind == "tender":
        return "tender"
    if kind == "history":
        return "history"
    if kind in ("materials", "manuals", "fault_cases", "products"):
        return "materials"
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
    ref_notice = "【仅供参考·仅借结构与话术，严禁照抄旧客户名、旧工期、旧金额或旧型号，不得作为正式附着证据】" if chunk.get("reference_only") else ""
    name = chunk.get("name") or ""
    raw_kind = str(chunk.get("dataset_kind") or "")
    meta = chunk.get("meta_fields") if isinstance(chunk.get("meta_fields"), dict) else {}
    meta_badges: list[str] = []
    if raw_kind in SUBKIND_LABELS:
        meta_badges.append(f"来源：{SUBKIND_LABELS[raw_kind]}")
    model_val = str(meta.get("model") or meta.get("product_model") or "").strip()
    if model_val:
        meta_badges.append(f"型号：{model_val}")
    fault_cat = str(meta.get("fault_category") or "").strip()
    if fault_cat:
        meta_badges.append(f"分类：{fault_cat}")
    badge_str = f"[{' | '.join(meta_badges)}] " if meta_badges else ""
    title = f"{name} · " if name else ""
    role = "项目事实" if retrieved_chunk_dataset_kind(chunk) == "tender" else "检索切片"
    return [
        f"{chunk.get('cite_tag') or tag} {badge_str}{title}{role}{prov}{ref_notice}：",
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
        if any(name.startswith(prefix) for prefix in _GENERIC_ENTITY_SKIP):
            continue
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
    wf = workflow or {}
    for sheet_key in ("global_fact_sheet_snapshot", "global_fact_sheet"):
        sheet = wf.get(sheet_key)
        if isinstance(sheet, dict):
            for k in ("client_name", "project_name"):
                val = str(sheet.get(k) or "").strip()
                if len(val) >= 2:
                    names.add(val)
                    names.update(_entity_spans(val))
    tech_facts = wf.get("technical_facts") or {}
    if isinstance(tech_facts, dict):
        for k in ("客户名", "项目理解"):
            val = str(tech_facts.get(k) or "").strip()
            if len(val) >= 2:
                names.add(val)
                names.update(_entity_spans(val))
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
    texts: list[str] = []
    explicit_foreign: list[str] = []
    for chunk in chunks:
        if retrieved_chunk_dataset_kind(chunk) != "history":
            continue
        texts.append(f"{chunk.get('name') or ''}\n{chunk.get('content') or ''}")
        meta = chunk.get("meta_fields") if isinstance(chunk.get("meta_fields"), dict) else {}
        for mkey in ("purchaser", "client_name", "project_name"):
            mval = str(meta.get(mkey) or "").strip()
            if len(mval) >= 2 and not _name_allowed(mval, allowed) and mval not in explicit_foreign:
                explicit_foreign.append(mval)
    detected = foreign_entity_names(texts, allowed)
    for item in explicit_foreign:
        if item not in detected:
            detected.append(item)
    detected.sort(key=len, reverse=True)
    return detected


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
