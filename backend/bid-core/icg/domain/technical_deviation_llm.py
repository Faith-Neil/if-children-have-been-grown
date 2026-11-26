# 为什么有这个文件：把《技术偏离表》少数规则未命中条款做按章批量语义提炼（TV-M0-T30）。
# 它解决什么问题：通用兜底句安全但机械；这里只对兜底池按章调用本地 JSON 模型，
# 高置信度规则命中仍走确定性提取，模型失败或校验不过的单条回退确定性兜底。

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from icg.domain.technical_fact_sheet import prompt_fact_sheet_json
from icg.domain.writing_knowledge_prompt import allowed_identity_names, foreign_entity_names
from icg.infra.model_fallback import call_model
from icg.infra.openai_model import AuditIoLabel, ModelCallProfile

# 偏离表批量提炼只输出 JSON；关闭思考模式，请求体不携带 thinking_budget。
DEVIATION_BATCH_CALL = ModelCallProfile(enable_thinking=False, max_tokens=1536, timeout_seconds=35, json_mode=True)

_SYSTEM = """你是投标技术偏离表响应提炼器。只输出一个 JSON 对象，禁止输出解释、Markdown 或思考过程。
你必须基于给定章节正文和 Global Fact Sheet 提炼，不得编造事实，不得引用其他项目、其他客户或历史标书。
输出格式：{"responses":[{"id":"条款ID","response":"50到110字的第一人称正式投标响应"}]}
响应要求：
1. 每条 50～110 个字符，以“我司”开头，以中文句号结束，语义完整；建议写成“承诺 + 正文证据动作/机制”两个分句，避免过短；
2. 技术/服务类条款：跨句提炼本章正文中的具体动作、频次、角色、时限或量化承诺；必须至少包含一个可核验动作（如巡检、复盘、优化、评估、报告、会议、响应、审计、更换、诊断）或角色/频次/数字，禁止只写“规范、可追溯、全面支撑”等空泛表述；
3. 违约/赔偿/保密/责任类条款：明确承诺“完全接受并遵守”，复述核心责任（如违约金比例、直接经济损失、保密义务），并补充我方预防、审计或闭环保障机制；
4. 禁止出现“制定专项响应措施”“明确执行流程、责任分工、时限要求与交付记录”“详见对应章节正文”等机械套话；
5. 禁止出现“历史做法”“历史标书”“负偏离”“不满足”“无法响应”“不能响应”；
6. 不得改变 Global Fact Sheet 中的人员、期限、SLA、资产数量和评分决策；不得使用“杜绝”“完全避免”“无中断”“确保不发生”等正文未明确支撑的绝对化承诺。
句式参考（只学习结构，不得照抄）：服务类可写“我司承诺……，由……完成……，形成……报告/记录”；责任类可写“我司完全接受并遵守……，通过……机制预防风险，确保责任可追溯”。"""

_MECHANICAL = re.compile(r"制定专项响应措施|明确执行流程、责任分工、时限要求与交付记录|详见对应章节正文")
_FORBIDDEN = re.compile(r"历史做法|历史标书|负偏离|不满足|无法响应|不能响应")
_ABSOLUTE = re.compile(r"杜绝|完全避免|无中断|确保不发生")
_OBLIGATION = re.compile(r"违约|赔偿|保密|损失|责任|泄漏|泄露")
_SERVICE_EVIDENCE = re.compile(r"巡检|复盘|优化|评估|报告|会议|演练|响应|审计|更换|诊断|热线|电话|每月|每季度|\d|项目总监|工程师")
_PROMPT_VERSION = "t30-deviation-v7"




def clause_response_kind(clause: str) -> str:
    return "obligation" if _OBLIGATION.search(clause or "") else "service"


def _json_object(text: str) -> dict[str, Any] | None:
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(raw[start:end + 1])
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def validate_llm_response(response: str, workflow: dict, source_body: str = "") -> tuple[bool, str]:
    """单条安全门禁：长度、第一人称、完整句、机械套话、负偏离/历史做法与外实体。"""
    text = re.sub(r"\s+", "", str(response or ""))
    if not text:
        return False, "empty"
    if len(text) < 50:
        return False, "too_short"
    if len(text) > 110:
        return False, "too_long"
    if not text.startswith(("我司", "我们", "我公司")):
        return False, "not_first_person"
    if not text.endswith(("。", "！", "？")):
        return False, "incomplete_sentence"
    if text.endswith(("，", "、", "；", ":", "：")) or "一。" in text:
        return False, "broken_boundary"
    if text.count("“") != text.count("”") or text.count("（") != text.count("）"):
        return False, "unclosed_quote"
    if _MECHANICAL.search(text):
        return False, "mechanical_fallback"
    if _FORBIDDEN.search(text):
        return False, "forbidden_wording"
    absolute = _ABSOLUTE.search(text)
    if absolute and absolute.group(0) not in str(source_body or ""):
        return False, "unsupported_absolute"
    foreign = foreign_entity_names([text], allowed_identity_names(workflow))
    if foreign:
        return False, "foreign_entity:" + foreign[0]
    return True, ""


def _fingerprint(content: str, entries: list[dict], fact_sheet: dict) -> str:
    payload = {
        "prompt_version": _PROMPT_VERSION,
        "content_sha": hashlib.sha256((content or "").encode("utf-8")).hexdigest(),
        "fact": fact_sheet,
        "entries": [
            {
                "id": str(item.get("id") or ""),
                "clause": str(item.get("clause") or ""),
                "section": str(item.get("section_key") or ""),
            }
            for item in entries
        ],
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _compact_text(text: str) -> str:
    """压缩提示词中的空白与 Markdown 包装，不删正文句子、表格单元或事实字段。"""
    from icg.domain.export_sanitizer import normalize_markdown_noise, strip_internal_markers
    lines: list[str] = []
    for raw in strip_internal_markers(normalize_markdown_noise(str(text or ""))).splitlines():
        line = raw.strip()
        if not line or re.match(r"^\|?\s*:?-{2,}", line) or line == "---":
            continue
        line = re.sub(r"\s+", " ", line)
        if line:
            lines.append(line)
    return "\n".join(lines)


def _compact_fact(value):
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    if isinstance(value, list):
        return [_compact_fact(item) for item in value]
    if isinstance(value, dict):
        return {key: _compact_fact(item) for key, item in value.items()}
    return value


def _prompt_for_group(group: list[dict], workflow: dict, fact_sheet: dict) -> str:
    first = group[0]
    clauses = [
        {
            "id": str(item.get("id") or ""),
            "clause": str(item.get("clause") or ""),
            "type": clause_response_kind(str(item.get("clause") or "")),
        }
        for item in group
    ]
    payload = {
        "section": {
            "number": str(first.get("section_number") or ""),
            "title": str(first.get("section_title") or ""),
        },
        "global_fact_sheet": _compact_fact(fact_sheet),
        "section_body": _compact_text(str(first.get("body") or ""))[:10000],
        "fallback_clauses": clauses,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _parse_responses(raw: str) -> dict[str, str]:
    obj = _json_object(raw)
    if not obj:
        return {}
    rows = obj.get("responses")
    if not isinstance(rows, list):
        return {}
    out: dict[str, str] = {}
    for item in rows:
        if not isinstance(item, dict):
            continue
        rid = str(item.get("id") or "").strip()
        response = str(item.get("response") or "").strip()
        if rid and response:
            out[rid] = response
    return out


def refine_deviation_fallbacks(model: Any, workflow: dict, content: str, entries: list[dict], *,
                               max_workers: int = 2) -> tuple[dict[str, str], dict[str, Any]]:
    """兜底池按章批量提炼。entries 必须已按章节带上 body；返回 {条款ID: 通过门禁的响应} 与审计。"""
    if not entries:
        return {}, {"fallback_clauses": 0, "calls": 0, "accepted": 0, "rejected": 0, "cache_hit": False}
    fact_sheet = prompt_fact_sheet_json(workflow)
    cache_key = _fingerprint(content or "", entries, fact_sheet)
    cache = workflow.setdefault("technical_deviation_llm_cache", {})
    cached = cache.get(cache_key) if isinstance(cache, dict) else None
    if isinstance(cached, dict) and isinstance(cached.get("responses"), dict):
        cache_started = time.time()
        audit = dict(cached.get("audit") or {})
        audit.update({
            "cache_hit": True,
            "fallback_clauses": len(entries),
            "cached_calls": audit.get("calls", 0),
            "calls": 0,
            "cached_chapter_calls": audit.get("chapter_calls") or [],
            "chapter_calls": [],
            "elapsed_ms": int((time.time() - cache_started) * 1000),
        })
        return dict(cached["responses"]), audit
    if model is None:
        return {}, {"fallback_clauses": len(entries), "calls": 0, "accepted": 0,
                    "rejected": len(entries), "cache_hit": False, "skipped": "no_model"}

    groups: dict[str, list[dict]] = {}
    for item in entries:
        key = str(item.get("section_key") or item.get("section_number") or "")
        groups.setdefault(key, []).append(item)
    started = time.time()
    accepted: dict[str, str] = {}
    rejected: dict[str, str] = {}
    call_audit: list[dict[str, Any]] = []

    def one_group(section_key: str, group: list[dict]) -> tuple[str, dict[str, str], dict[str, str], dict[str, Any]]:
        user = _prompt_for_group(group, workflow, fact_sheet)
        meta: dict[str, Any] = {
            "section_key": section_key,
            "section": (str(group[0].get("section_number") or "") + " " + str(group[0].get("section_title") or "")).strip(),
            "clauses": len(group),
        }
        try:
            with AuditIoLabel("DEVIATION"):
                result = call_model(model, _SYSTEM, user, profile=DEVIATION_BATCH_CALL)
            raw = result.text
            meta.update({"status": "ok", "model": result.model, "is_fallback_model": result.is_fallback})
        except Exception as exc:  # 模型超时/连接/上游错误：整组安全回落确定性兜底
            meta.update({"status": "error", "error": type(exc).__name__})
            return section_key, {}, {str(item.get("id") or ""): "model_error" for item in group}, meta
        parsed = _parse_responses(raw)
        local_accepted: dict[str, str] = {}
        local_rejected: dict[str, str] = {}
        for item in group:
            rid = str(item.get("id") or "")
            candidate = parsed.get(rid) or ""
            ok, reason = validate_llm_response(candidate, workflow, str(item.get("body") or ""))
            kind = clause_response_kind(str(item.get("clause") or ""))
            if ok and kind == "obligation" and "完全接受并遵守" not in candidate:
                ok, reason = False, "missing_accept_obligation"
            if ok and kind == "service" and not _SERVICE_EVIDENCE.search(candidate):
                ok, reason = False, "service_too_generic"
            if ok:
                local_accepted[rid] = re.sub(r"\s+", " ", candidate).strip()
            else:
                local_rejected[rid] = reason or "missing"
        meta.update({"returned": len(parsed), "accepted": len(local_accepted), "rejected": len(local_rejected)})
        return section_key, local_accepted, local_rejected, meta

    workers = max(1, min(int(max_workers or 1), len(groups), 4))
    if workers == 1 or len(groups) == 1:
        results = [one_group(key, groups[key]) for key in sorted(groups)]
    else:
        results = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(one_group, key, groups[key]): key for key in sorted(groups)}
            for future in as_completed(futures):
                results.append(future.result())
    for _key, good, bad, meta in results:
        accepted.update(good)
        rejected.update(bad)
        call_audit.append(meta)

    audit = {
        "fallback_clauses": len(entries),
        "calls": len(groups),
        "accepted": len(accepted),
        "rejected": len(rejected),
        "rejected_reasons": rejected,
        "chapter_calls": call_audit,
        "elapsed_ms": int((time.time() - started) * 1000),
        "cache_hit": False,
        "concurrency": workers,
    }
    if isinstance(cache, dict):
        if not rejected:
            cache[cache_key] = {"responses": dict(accepted), "audit": dict(audit)}
    workflow["technical_deviation_llm_audit"] = audit
    return accepted, audit
