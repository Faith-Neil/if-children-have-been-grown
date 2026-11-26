# 为什么有这个文件：技术分册节生成先查本标切片，再查公司 history 与 materials，并留下可审计记录。
# 它解决什么问题：检索词只用节标题，禁止把招标原文写进 query，禁止把招标页写进公司库，禁止缺库静默假成功。
# 含外项目专名的历史命中在截断前降权。history_hits 仍按检索条数计。Prompt 里的 history 只留最高分 3 条，每条正文最多 400 字。

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import inspect
import re
from typing import Any

from icg.domain.knowledge_base import MATERIAL_SUBKINDS, dataset_full_name, read_index
from icg.domain.technical_tender_index import retrieve_tender
from icg.domain.writing_knowledge_prompt import (
    format_retrieved_knowledge_prompt_lines,
    history_foreign_names,
    retrieved_chunk_dataset_kind,
)


def section_query(title: str, row: dict | None = None, *, task: dict | None = None,
                  requirements: list[dict] | None = None, points: list[str] | None = None) -> str:
    """节标题，再加上标题里至多 3 个不少于 2 字的词，以及至多 2 条挂载要点。招标原文不进入检索词。"""
    del row, task, requirements
    base = _title_query(title)
    extra = [str(point).strip()[:20] for point in (points or []) if str(point or "").strip()][:2]
    return " ".join([base, *extra]).strip() if extra else base


def _title_query(title: str) -> str:
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
    """编辑台提示用：公司历史库与资料库（含三子库任一）是否已配置，以及本标索引是否已建。"""
    index = read_index(state, company_id) if state is not None else {}
    datasets = index.get("datasets") or {}
    history_name = dataset_full_name(company_id, "history")
    material_name = dataset_full_name(company_id, "materials")
    history_ok = bool((datasets.get("history") or {}).get("dataset_id"))
    subkinds_configured = [k for k in MATERIAL_SUBKINDS if (datasets.get(k) or {}).get("dataset_id")]
    material_ok = bool((datasets.get("materials") or {}).get("dataset_id") or subkinds_configured)
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
        "subkinds": {
            k: {"name": dataset_full_name(company_id, k), "configured": k in subkinds_configured}
            for k in MATERIAL_SUBKINDS
        },
        "tender": {
            "name": str(tender.get("dataset_name") or ""),
            "configured": tender_ok,
            "backend": str(tender.get("backend") or ""),
        },
        "missing": missing,
        "ready": not missing,
    }


def _kb_search_supports_meta(kb: Any) -> bool:
    search_fn = getattr(kb, "search", None)
    if not callable(search_fn):
        return False
    try:
        params = inspect.signature(search_fn).parameters
        return "metadata_condition" in params or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
    except (TypeError, ValueError):
        return False


# 本机 RAGFlow v1.0 /datasets/{id}/retrieval 的 metadata_condition 协议算子全集
_ALLOWED_META_OPS = {
    "is", "not is", "contains", "not contains", "in", "not in",
    "start with", "end with", "empty", "not empty",
}
_MODEL_PREFIX_RE = re.compile(r"(?i)^\s*(?:model|机型|型号)[-:_：\s]*")
_MODEL_META_KEYS = ("model", "product_model")
_DOC_TYPE_BY_SUBKIND = {"products": "product_spec", "manuals": "manual", "fault_cases": "fault_case"}


def _sanitize_metadata_condition(cond: Any) -> dict[str, Any] | None:
    """严格收敛为 RAGFlow v1.0 metadata_condition 协议结构：{logic: and|or, conditions:[{name,comparison_operator,value}]}；非法结构返回 None。"""
    if not isinstance(cond, dict):
        return None
    raw_conditions = cond.get("conditions")
    if not isinstance(raw_conditions, list) or not raw_conditions:
        return None
    logic = str(cond.get("logic") or "and").strip().lower()
    if logic not in ("and", "or"):
        logic = "and"
    kept: list[dict[str, str]] = []
    for item in raw_conditions:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        op = str(item.get("comparison_operator") or "contains").strip().lower()
        if op not in _ALLOWED_META_OPS:
            op = "contains"
        if op in ("empty", "not empty"):
            kept.append({"name": name, "comparison_operator": op, "value": ""})
            continue
        value = str(item.get("value") or "").strip()
        if not value:
            continue
        kept.append({"name": name, "comparison_operator": op, "value": value[:64]})
    if not kept:
        return None
    return {"logic": logic, "conditions": kept[:6]}


def _model_variants(value: str) -> list[str]:
    """型号写法差异（X800 / Model-X800 / X 800 / X-800）生成检索变体，防止 contains 精确匹配空窗。"""
    raw = str(value or "").strip()
    if not raw:
        return []
    variants = [raw]
    stripped = _MODEL_PREFIX_RE.sub("", raw).strip()
    if stripped and stripped != raw:
        variants.append(stripped)
    base = stripped or raw
    for alt in (base.replace("-", ""), base.replace("-", " "), base.replace(" ", "-"), base.replace(" ", "")):
        if alt and alt not in variants:
            variants.append(alt)
    return variants[:4]


def _metadata_fallback_ladder(cond: dict[str, Any] | None, kind_key: str) -> list[dict[str, Any] | None]:
    """零命中逐级放宽：型号写法变体 OR → 仅 doc_type 级过滤 → 不过滤。
    history 的排他条件（排除 not_reusable / buyer_requirement）是安全底线，永不做放宽重试。"""
    clean = _sanitize_metadata_condition(cond)
    if clean is None or kind_key == "history":
        return [clean]
    ladder: list[dict[str, Any] | None] = [clean]
    doc_type = _DOC_TYPE_BY_SUBKIND.get(kind_key)
    model_items = [c for c in clean["conditions"] if c["name"] in _MODEL_META_KEYS]
    if model_items:
        expanded = [
            {"name": c["name"], "comparison_operator": "is", "value": v}
            for c in model_items for v in _model_variants(c["value"])
        ]
        variant_cond: dict[str, Any] | None = (
            {"logic": "or", "conditions": expanded[:6]} if expanded else None
        )
        if variant_cond and variant_cond != clean:
            ladder.append(variant_cond)
    if doc_type:
        ladder.append({
            "logic": "and",
            "conditions": [{"name": "doc_type", "comparison_operator": "is", "value": doc_type}],
        })
    ladder.append(None)
    return ladder


def _configured_material_subkinds(kb: Any, company_id: str) -> list[str]:
    repo = getattr(kb, "repository", None)
    if repo is None or not hasattr(repo, "read"):
        return []
    try:
        index = read_index(repo.read(), company_id)
    except Exception:
        return []
    datasets = index.get("datasets") or {}
    active = [k for k in MATERIAL_SUBKINDS if (datasets.get(k) or {}).get("dataset_id")]
    if active and (datasets.get("materials") or {}).get("dataset_id"):
        active.append("materials")
    return active


def _call_kb_search(
    kb: Any,
    company_id: str,
    query: str,
    *,
    limit: int,
    kinds: set[str],
    metadata_condition: dict[str, Any] | None = None,
    max_chunks_per_doc: int = 2,
) -> tuple[list[Any], str]:
    if not _kb_search_supports_meta(kb):
        return kb.search(company_id, query, limit=limit, kinds=kinds)
    kind_key = next(iter(kinds), "")
    # 逐级放宽阶梯：精确型号 → 型号写法变体 → doc_type 级 → 不过滤，避免型号写法细微差异导致子库空窗
    attempts = _metadata_fallback_ladder(metadata_condition, kind_key)
    hits: list[Any] = []
    reason = ""
    for index, cond in enumerate(attempts):
        hits, reason = kb.search(
            company_id,
            query,
            limit=limit,
            kinds=kinds,
            metadata_condition=cond,
            max_chunks_per_doc=max_chunks_per_doc,
        )
        if hits or index == len(attempts) - 1:
            break
    return hits, reason


def _filter_history_hits(hits: list[Any]) -> tuple[list[Any], int]:
    """历史标书排他（not_reusable / buyer_requirement）在应用侧确定性执行。

    真机实测 RAGFlow 1.0 的 not is 负向过滤行为不可靠（缺字段文档被误排、命中行为不一致），
    而排他是防串标安全底线，必须可测可控——因此在命中回收后按 meta_fields 精确丢弃，
    不再依赖检索端负向算子。返回 (保留命中, 丢弃条数)。
    """
    kept: list[Any] = []
    dropped = 0
    for hit in hits:
        meta = dict(getattr(hit, "meta_fields", None) or {})
        reusability = str(meta.get("reusability") or "").strip().lower()
        content_role = str(meta.get("content_role") or "").strip().lower()
        if reusability == "not_reusable" or content_role == "buyer_requirement":
            dropped += 1
            continue
        kept.append(hit)
    return kept, dropped


def _hit_to_chunk(hit: Any, default_kind: str) -> dict[str, Any]:
    ds_kind = getattr(hit, "dataset_kind", "") or default_kind
    return {
        "id": hit.source_id,
        "name": hit.name,
        "content": hit.content,
        "score": hit.score,
        "dataset_kind": ds_kind,
        "reference_only": bool(getattr(hit, "reference_only", False) or default_kind == "history"),
        "document_id": hit.document_id,
        "chunk_id": (hit.chunk_ids or [""])[0],
        "cite_tag": hit.cite_tag,
        "meta_fields": dict(getattr(hit, "meta_fields", None) or {}),
    }


# 故障案例全局配额：仅应急处置/故障预案类章节检索 fault_cases，其余章节物理上不查，
# 从根上消灭同一案例全书复读（真机「心跳链路 MTU 不一致」重复 40 次）。
_FAULT_CASE_HINT = ("故障", "应急", "预案", "处置", "抢修", "容灾", "演练", "恢复", "切换", "重大故障")


def wants_fault_cases(title: str, points: list[str] | None = None, blueprint: dict | None = None) -> bool:
    if blueprint and blueprint.get("assigned_cases"):
        return True
    haystack = str(title or "") + " " + " ".join(str(p) for p in (points or []))
    return any(hint in haystack for hint in _FAULT_CASE_HINT)


def retrieve_dual(
    kb: Any,
    company_id: str,
    query: str,
    *,
    limit: int = 8,
    query_plan: Any = None,
    allow_fault_cases: bool = True,
) -> tuple[list[dict], dict]:
    """支持四物理库（history + manuals/fault_cases/products）并发检索与两库兼容检索。"""
    audit: dict[str, Any] = {
        "query": query,
        "history_searched": False,
        "material_searched": False,
        "history_hits": 0,
        "material_hits": 0,
        "product_hits": 0,
        "manual_hits": 0,
        "fault_case_hits": 0,
        "skip_reason": "",
        "top": [],
    }
    if kb is None:
        audit["skip_reason"] = "knowledge base unavailable"
        return [], audit

    subkinds = _configured_material_subkinds(kb, company_id)
    routes: list[tuple[str, str, str, dict[str, Any] | None, int, int]] = []
    h_query = (query_plan.history_queries[0] if query_plan and query_plan.history_queries else query)
    h_cond = query_plan.history_metadata_condition if query_plan else None
    # history 超额召回：应用侧排他（not_reusable/buyer_requirement）在回收后执行，
    # top_k 放大到 18 防止过滤后归零；过滤后保留前 6 条，Prompt 侧另有预算截断。
    routes.append(("history", "history", h_query, h_cond, 18, 2))

    if subkinds:
        for sk in subkinds:
            if sk == "products":
                q = query_plan.product_queries[0] if query_plan and query_plan.product_queries else query
                cond = query_plan.product_metadata_condition if query_plan else None
                routes.append(("products", "products", q, cond, 3, 3))
            elif sk == "manuals":
                q = query_plan.manual_queries[0] if query_plan and query_plan.manual_queries else query
                cond = query_plan.manual_metadata_condition if query_plan else None
                routes.append(("manuals", "manuals", q, cond, 3, 3))
            elif sk == "fault_cases":
                if not allow_fault_cases:
                    continue
                q = query_plan.fault_case_queries[0] if query_plan and query_plan.fault_case_queries else query
                cond = query_plan.fault_metadata_condition if query_plan else None
                routes.append(("fault_cases", "fault_cases", q, cond, 3, 3))
            else:
                routes.append(("materials", "materials", query, None, 3, 2))
    else:
        m_query = (query_plan.manual_queries[0] if query_plan and query_plan.manual_queries else query)
        routes.append(("materials", "material", m_query, None, max(limit // 2, 4), 3))

    def run_route(spec: tuple[str, str, str, dict[str, Any] | None, int, int]):
        kind_key, label, q, cond, k_limit, chunk_cap = spec
        detail: dict[str, Any] = {"route": kind_key, "query": q, "status": "ok", "raw_hits": 0,
                                  "post_filter_hits": 0, "dropped": 0, "top_score": 0.0, "error_detail": ""}
        try:
            hits, reason = _call_kb_search(
                kb, company_id, q, limit=k_limit, kinds={kind_key},
                metadata_condition=cond, max_chunks_per_doc=chunk_cap,
            )
            # 意图拆解的子 Query 过窄零命中时，回落本节节标题基础 Query 再召回一次
            if not hits and q != query:
                hits, reason = _call_kb_search(
                    kb, company_id, query, limit=k_limit, kinds={kind_key},
                    metadata_condition=cond, max_chunks_per_doc=chunk_cap,
                )
                detail["fallback_query"] = True
                detail["query"] = query
            detail["raw_hits"] = len(hits)
            detail["top_score"] = round(max((float(getattr(h, "score", 0) or 0) for h in hits), default=0.0), 4)
            dropped = 0
            if kind_key == "history" and hits:
                hits, dropped = _filter_history_hits(hits)
                if len(hits) > 6:
                    hits = hits[:6]
            detail["dropped"] = dropped
            detail["post_filter_hits"] = len(hits)
            if not hits:
                detail["status"] = "filtered_empty" if detail["raw_hits"] else "empty"
                detail["error_detail"] = str(reason or "")
            return kind_key, label, hits, reason, "", dropped, detail
        except Exception as exc:
            # 并发检索异常必须显式进审计，杜绝静默吞错
            detail["status"] = "error"
            detail["error_detail"] = f"{type(exc).__name__}: {str(exc)[:160]}"
            return kind_key, label, [], str(exc), f"{label}:{type(exc).__name__}", 0, detail

    if len(routes) > 2:
        with ThreadPoolExecutor(max_workers=min(len(routes), 4)) as pool:
            outcomes = list(pool.map(run_route, routes))
    else:
        outcomes = [run_route(r) for r in routes]

    chunks: list[dict] = []
    seen_doc_chunks: set[str] = set()
    audit.setdefault("routes", [])
    for outcome in outcomes:
        kind_key, _label, hits, reason, err = outcome[:5]
        dropped = outcome[5] if len(outcome) > 5 else 0
        if len(outcome) > 6 and isinstance(outcome[6], dict):
            audit["routes"].append(outcome[6])
        if dropped:
            audit["history_excluded"] = int(audit.get("history_excluded") or 0) + dropped
        if kind_key == "history":
            audit["history_searched"] = True
            audit["history_hits"] += len(hits)
        else:
            audit["material_searched"] = True
            audit["material_hits"] += len(hits)
            if kind_key == "products":
                audit["product_hits"] += len(hits)
            elif kind_key == "manuals":
                audit["manual_hits"] += len(hits)
            elif kind_key == "fault_cases":
                audit["fault_case_hits"] += len(hits)
        # 子库「尚未同步文档」只是该分路状态，already 记录在 routes[].error_detail；
        # 不得提升为顶层 skip_reason/rag.error 干扰 history 等其他分路的正常命中判断。
        route_local_empty = str(reason or "") == "knowledge base has no synced documents"
        if err and not audit["skip_reason"]:
            audit["skip_reason"] = err
        elif reason and not hits and not route_local_empty and not audit["skip_reason"]:
            audit["skip_reason"] = reason
        for hit in hits:
            ch = _hit_to_chunk(hit, kind_key)
            dedup_key = f"{kind_key}:{ch.get('document_id')}:{ch.get('chunk_id') or ch.get('id')}"
            if dedup_key in seen_doc_chunks:
                continue
            seen_doc_chunks.add(dedup_key)
            chunks.append(ch)
            if len(audit["top"]) < 8:
                audit["top"].append({"name": hit.name, "dataset_kind": ch["dataset_kind"], "score": hit.score})
    chunks.sort(key=lambda item: (-float(item.get("score") or 0), item.get("name") or ""))
    return chunks[: max(limit, 10)], audit


_TENDER_BUDGET_CHARS = 1200     # ~20% 参考上下文预算
_MATERIALS_BUDGET_CHARS = 3300  # ~55% 核心事实底座配额
_HISTORY_BUDGET_CHARS = 1500    # ~25% 写法骨架参考配额
_HISTORY_PROMPT_KEEP = 3
_HISTORY_PROMPT_CHARS = 400


def _clip_to_budget(items: list[dict], total_budget: int, per_item_cap: int) -> list[dict]:
    kept: list[dict] = []
    used = 0
    for item in items:
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        clipped = content[:per_item_cap]
        if used + len(clipped) > total_budget and kept:
            remaining = total_budget - used
            if remaining < 120:
                break
            clipped = clipped[:remaining]
        kept.append(item if clipped == content else {**item, "content": clipped})
        used += len(clipped)
        if used >= total_budget:
            break
    return kept


def _chunks_for_prompt(chunks: list[dict]) -> list[dict]:
    """按配额制截断三源上下文（本标 ~20% / 资料库 ~55% / 历史标书 ~25%），防止长历史标书挤出真实技术参数。"""
    tender = [item for item in chunks if retrieved_chunk_dataset_kind(item) == "tender"]
    materials = [item for item in chunks if retrieved_chunk_dataset_kind(item) == "materials"]
    history = [item for item in chunks if retrieved_chunk_dataset_kind(item) == "history"]

    ranked_history = sorted(history, key=lambda item: float(item.get("score") or 0), reverse=True)[:_HISTORY_PROMPT_KEEP]
    ranked_materials = sorted(materials, key=lambda item: float(item.get("score") or 0), reverse=True)

    kept_tender = _clip_to_budget(tender[:3], _TENDER_BUDGET_CHARS, 550)
    kept_materials = _clip_to_budget(ranked_materials[:9], _MATERIALS_BUDGET_CHARS, 900)
    kept_history = _clip_to_budget(ranked_history, _HISTORY_BUDGET_CHARS, _HISTORY_PROMPT_CHARS)
    return [*kept_tender, *kept_materials, *kept_history]


def knowledge_prompt_block(chunks: list[dict], workflow: dict | None = None) -> str:
    lines = format_retrieved_knowledge_prompt_lines(_chunks_for_prompt(chunks), workflow)
    return "\n".join(lines).strip()


def _demote_foreign_history(
    company_hits: list[dict], tender_hits: list[dict], workflow: dict | None,
) -> list[dict]:
    """外项目专名只降权，不从命中里删掉。"""
    foreign = history_foreign_names([*tender_hits, *company_hits], workflow)
    if not foreign:
        return company_hits
    ranked: list[dict] = []
    for chunk in company_hits:
        if retrieved_chunk_dataset_kind(chunk) != "history":
            ranked.append(chunk)
            continue
        blob = f"{chunk.get('name') or ''} {chunk.get('content') or ''}"
        if any(name in blob for name in foreign):
            ranked.append({**chunk, "score": float(chunk.get("score") or 0) - 1.0})
        else:
            ranked.append(chunk)
    ranked.sort(key=lambda item: (-float(item.get("score") or 0), str(item.get("name") or "")))
    return ranked


def rag_summary(audit: dict | None, *, searched_at: str = "") -> dict[str, Any]:
    """覆盖视图用的单节检索摘要：历史库与资料三子库命中数、前 3 条来源、状态与原因。"""
    audit = audit or {}
    history = int(audit.get("history_hits") or 0)
    material = int(audit.get("material_hits") or 0)
    searched = bool(audit.get("history_searched") or audit.get("material_searched"))
    error = str(audit.get("skip_reason") or "")
    if history + material and error == "knowledge base has no synced documents":
        error = ""
    if history + material:
        status = "hit"
    elif searched:
        status = "empty"
    else:
        status = "skipped" if not error else "failed"
    summary: dict[str, Any] = {
        "status": status, "query": str(audit.get("query") or ""), "history_hits": history,
        "material_hits": material, "tender_hits": int(audit.get("tender_hits") or 0), "error": error,
        "top": [
            {"name": item.get("name"), "dataset_kind": item.get("dataset_kind"), "score": item.get("score")}
            for item in (audit.get("top") or [])[:3] if isinstance(item, dict)
        ],
        "searched_at": searched_at,
    }
    for sub_key in ("product_hits", "manual_hits", "fault_case_hits"):
        if int(audit.get(sub_key) or 0) > 0:
            summary[sub_key] = int(audit[sub_key])
    return summary


def retrieve_for_section(
    kb: Any,
    company_id: str,
    query: str,
    workflow: dict | None = None,
    *,
    limit: int = 10,
    breadcrumb: str = "",
    points: list[str] | None = None,
    model: Any = None,
    section_key: str = "",
) -> tuple[list[dict], dict]:
    """意图拆解 → 并发检索本标补充切片与企业四库 → 按配额合并（资料库优先于历史标书，本标不占满窗口）。"""
    from icg.domain.technical_fact_sheet import prompt_fact_sheet_json
    from icg.domain.technical_query_plan import plan_section_queries

    sheet = prompt_fact_sheet_json(workflow)
    target_models = list(sheet.get("target_models") or [])
    q_plan = None
    if breadcrumb or points or target_models or model is not None:
        q_plan = plan_section_queries(
            query, breadcrumb=breadcrumb, points=points, target_models=target_models, model=model,
        )

    tender_q = q_plan.tender_query if q_plan else query
    tender_hits, tender_audit = retrieve_tender(
        workflow or {}, tender_q, kb=kb, company_id=company_id, limit=min(limit, 3),
    )
    if not tender_hits and tender_q != query:
        tender_hits, tender_audit = retrieve_tender(
            workflow or {}, query, kb=kb, company_id=company_id, limit=min(limit, 3),
        )
    blueprints = (workflow or {}).get("writing_blueprints") or {}
    blueprint = blueprints.get(str(section_key or "")) if section_key else None
    allow_fault = wants_fault_cases(query, points, blueprint)
    company_hits, company_audit = retrieve_dual(
        kb, company_id, query, limit=limit, query_plan=q_plan, allow_fault_cases=allow_fault,
    )
    if not allow_fault:
        company_audit["fault_case_quota"] = "skipped_non_emergency_section"
    # 故障案例全书一次性配额：已在前序章节用过的案例 chunk 不再注入，消灭跨章复读
    if allow_fault and isinstance(workflow, dict):
        used = workflow.setdefault("fault_cases_used", [])
        used_set = set(used)
        kept: list[dict] = []
        for chunk in company_hits:
            kind = str(chunk.get("dataset_kind") or chunk.get("kind") or "")
            cid = str(chunk.get("chunk_id") or chunk.get("id") or "")
            if kind == "fault_cases" and cid:
                if cid in used_set:
                    company_audit["fault_case_deduped"] = int(company_audit.get("fault_case_deduped") or 0) + 1
                    continue
                used.append(cid)
                used_set.add(cid)
            kept.append(chunk)
        company_hits = kept
    company_hits = _demote_foreign_history(company_hits, tender_hits, workflow)

    # 优先保住资料库（事实底座）与至多 3 条高分历史参考，本标补充检索最多占 3 槽
    mat_hits = [c for c in company_hits if retrieved_chunk_dataset_kind(c) == "materials"]
    hist_hits = [c for c in company_hits if retrieved_chunk_dataset_kind(c) == "history"][:3]
    ordered_company = [*mat_hits, *hist_hits]

    if tender_hits and ordered_company:
        tender_slots = min(len(tender_hits), max(1, min(3, limit // 4 or 1)))
        company_slots = max(limit - tender_slots, 1)
    else:
        company_slots = min(len(ordered_company), limit)
        tender_slots = min(len(tender_hits), max(limit - company_slots, 0))

    merged: list[dict] = []
    seen: set[str] = set()
    for chunk in [*tender_hits[:tender_slots], *ordered_company[:company_slots]]:
        cid = str(chunk.get("chunk_id") or chunk.get("id") or "")
        if cid and cid in seen:
            continue
        if cid:
            seen.add(cid)
        merged.append(chunk)
    audit = {
        "query": query,
        "query_plan_source": q_plan.source if q_plan else "direct",
        "section_type": q_plan.section_type if q_plan else "",
        "tender_searched": bool(tender_audit.get("tender_searched")),
        "tender_hits": int(tender_audit.get("tender_hits") or 0),
        "tender_dataset": tender_audit.get("tender_dataset") or "",
        "tender_backend": tender_audit.get("tender_backend") or "",
        "history_searched": bool(company_audit.get("history_searched")),
        "material_searched": bool(company_audit.get("material_searched")),
        "history_hits": int(company_audit.get("history_hits") or 0),
        "material_hits": int(company_audit.get("material_hits") or 0),
        "product_hits": int(company_audit.get("product_hits") or 0),
        "manual_hits": int(company_audit.get("manual_hits") or 0),
        "fault_case_hits": int(company_audit.get("fault_case_hits") or 0),
        "history_excluded": int(company_audit.get("history_excluded") or 0),
        "routes": list(company_audit.get("routes") or []),
        "skip_reason": tender_audit.get("skip_reason") or company_audit.get("skip_reason") or "",
        "top": [
            {
                "name": item.get("name"),
                "dataset_kind": item.get("dataset_kind") or retrieved_chunk_dataset_kind(item),
                "score": item.get("score"),
            }
            for item in merged[:8]
        ],
    }
    return merged[:limit], audit
