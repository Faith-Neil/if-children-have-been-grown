# 为什么有这个文件：技术分册用本地模型按页读标，抽出响应挂载、废标约束、编制顺序和事实。
# 它解决什么问题：正则扫行会丢掉表格、换说法的服务期和「这份标是谁、要干什么」；模型读标做主路径，规则只补漏检。

from __future__ import annotations

import json
from typing import Any

from icg.domain.technical_clause_extract import TechnicalClause, _matter_key, _same

EXTRACT_SYSTEM = (
    "你在读一份招标文件的一页或一块原文。只根据这一块输出 JSON，不要解释。"
    "字段：who（招标人/业主）、what（要采购或运维什么）、period（服务期/维保期原文）、"
    "sla（故障响应或到场时限）、format_order（编制顺序一级标题数组）、"
    "requirements（技术需求清单：数组，每项 text、quote、star）、"
    "scoring（评分规则清单：数组，每项 item、score、criteria、points、quote）、"
    "rejections（废标清单：数组，每项 text、quote、category）。"
    "requirements 是投标人必须在技术方案里回应的服务、指标、工作内容；star 为 true 表示带★或实质性条款。"
    "scoring 只收技术评分（技术方案、服务方案等主观分），不收报价、资质、业绩分；"
    "item 是评分项名称，score 是分值数字（原文没有写 null），criteria 是评分标准原文，"
    "points 是评委据以给分的得分要点数组，每条不超过 30 字。"
    "rejections 是废标、否决、无效投标条件，category 只能是 技术、资格、商务、格式 之一，不要当成要单独成章回答的服务项。"
    "text 是不超过 40 字的要点，quote 是原文短句。"
    "表格单元格、换行拆开的句子也要读。没有的字段用空字符串或空数组。"
    "禁止编造本页没有的业主、系统名、期限和分值。"
)


EXTRA_KEYS = ("score_item", "score", "criteria", "star", "category")
LIST_OF_ROLE = {
    ("response_mount", "spec"): "requirement_count",
    ("response_mount", "scoring"): "scoring_count",
    ("rejection_constraint", "spec"): "rejection_count",
    ("rejection_constraint", "scoring"): "rejection_count",
}


def _score(value: Any) -> float | None:
    try:
        number = float(str(value).strip().rstrip("分"))
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _payload_items(payload: dict) -> list[dict]:
    """三张清单摊平成统一条目；旧格式 items 照收，便于替身与历史缓存。"""
    found: list[dict] = [item for item in payload.get("items") or [] if isinstance(item, dict)]
    for item in payload.get("requirements") or []:
        if isinstance(item, dict):
            found.append({
                "text": item.get("text"), "quote": item.get("quote"), "kind": "spec",
                "role": "response_mount", "star": bool(item.get("star")) or None,
            })
    for rule in payload.get("scoring") or []:
        if not isinstance(rule, dict):
            continue
        name = str(rule.get("item") or "").strip()
        points = [str(point).strip() for point in rule.get("points") or [] if str(point or "").strip()]
        meta = {
            "score_item": name, "score": _score(rule.get("score")),
            "criteria": str(rule.get("criteria") or "").strip()[:400],
        }
        for point in points or [name]:
            found.append({
                "text": point, "quote": rule.get("quote") or rule.get("criteria"),
                "kind": "scoring", "role": "response_mount", **meta,
            })
    for item in payload.get("rejections") or []:
        if isinstance(item, dict):
            category = str(item.get("category") or "").strip()
            found.append({
                "text": item.get("text"), "quote": item.get("quote"), "kind": "spec",
                "role": "rejection_constraint",
                "category": category if category in ("技术", "资格", "商务", "格式") else "",
            })
    return found


def usable_local_model(model: Any) -> bool:
    if not (model and getattr(model, "is_real_model", False) and getattr(model, "is_local", None) is not False):
        return False
    url = getattr(model, "base_url", "") or ""
    if not url:
        return True
    from icg.infra.openai_model import is_public_model_url
    return not is_public_model_url(url)


def _parse_payload(text: str) -> dict:
    raw = (text or "").strip()
    if "```" in raw:
        fenced = raw.split("```", 2)[1]
        raw = fenced[4:] if fenced.startswith("json") else fenced
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < 0:
        return {}
    try:
        data = json.loads(raw[start:end + 1])
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _chunks(pages: list[str], *, limit: int = 2400) -> list[tuple[int, str]]:
    packed: list[tuple[int, str]] = []
    buf, start = "", 0
    for index, page in enumerate(pages, start=1):
        text = str(page or "").strip()
        if not text:
            continue
        if buf and len(buf) + len(text) > limit:
            packed.append((start, buf))
            buf, start = "", 0
        if not buf:
            start = index
        buf = f"{buf}\n{text}".strip() if buf else text
        if len(buf) >= limit:
            packed.append((start, buf))
            buf, start = "", 0
    if buf:
        packed.append((start, buf))
    return packed


def _is_timeout(exc: BaseException) -> bool:
    return "timeout" in f"{type(exc).__name__} {exc}".lower()


def extract_with_model(pages: list[str], model: Any, on_chunk=None) -> dict[str, Any]:
    """按页/块调用本地模型。失败的块跳过，不把空结果当成已读完整份标。"""
    result: dict[str, Any] = {
        "who": "",
        "what": "",
        "period": "",
        "sla": "",
        "format_order": [],
        "items": [],
        "pages_read": 0,
        "skip_reason": "",
        "timeout_count": 0,
        "chunks_attempted": 0,
        "extract_degraded": False,
        "requirement_count": 0,
        "scoring_count": 0,
        "rejection_count": 0,
    }
    if not usable_local_model(model):
        result["skip_reason"] = "no local model"
        return result
    from icg.infra.openai_model import EXTRACT_CALL, call_with_profile

    seen: set[str] = set()
    chunks = _chunks(pages)
    total = len(chunks)
    timeouts = 0
    result["chunks_attempted"] = total
    for index, (page_no, blob) in enumerate(chunks, start=1):
        if on_chunk is not None:
            on_chunk(index, total)
        try:
            raw = call_with_profile(model.suggest, EXTRACT_SYSTEM, f"页码 {page_no}：\n{blob[:8000]}", profile=EXTRACT_CALL)
            payload = _parse_payload(str(raw or ""))
        except Exception as exc:
            if _is_timeout(exc):
                timeouts += 1
            if not result["skip_reason"]:
                result["skip_reason"] = type(exc).__name__
            continue
        if not payload:
            continue
        result["pages_read"] += 1
        for key in ("who", "what", "period", "sla"):
            value = str(payload.get(key) or "").strip()
            if value and not result[key]:
                result[key] = value
        for title in payload.get("format_order") or []:
            name = str(title or "").strip()
            if name and name not in result["format_order"]:
                result["format_order"].append(name)
        for item in _payload_items(payload):
            text = str(item.get("text") or "").strip()
            quote = str(item.get("quote") or text).strip()
            if not text:
                continue
            key = _matter_key(text)
            if not key or any(_same(key, existing) for existing in seen):
                continue
            seen.add(key)
            role = str(item.get("role") or "response_mount").strip()
            if role not in ("response_mount", "rejection_constraint"):
                role = "response_mount"
            kind = str(item.get("kind") or "scoring").strip()
            if kind not in ("scoring", "spec"):
                kind = "scoring"
            entry = {
                "text": text[:80],
                "quote": quote[:400],
                "page": page_no,
                "kind": kind,
                "role": role,
            }
            entry.update({key: item[key] for key in EXTRA_KEYS if item.get(key) not in (None, "")})
            result["items"].append(entry)
            result[LIST_OF_ROLE[(role, kind)]] += 1
    result["timeout_count"] = timeouts
    result["extract_degraded"] = total > 0 and timeouts * 2 > total
    if not result["items"] and not result["skip_reason"]:
        result["skip_reason"] = "model returned no items"
    return result


def clauses_from_model(payload: dict[str, Any]) -> list[TechnicalClause]:
    found: list[TechnicalClause] = []
    for item in payload.get("items") or []:
        found.append(TechnicalClause(
            text=item["text"],
            page=int(item.get("page") or 1),
            quote=item.get("quote") or item["text"],
            kind=item.get("kind") or "scoring",
            extract_source="model",
            role=item.get("role") or "response_mount",
            extra={key: item[key] for key in EXTRA_KEYS if item.get(key) not in (None, "")},
        ))
    return found


def miss_patch(regex_clauses: list[TechnicalClause], model_clauses: list[TechnicalClause]) -> list[TechnicalClause]:
    """正则只补模型没抽到的要点，不覆盖模型主路径。"""
    keys = [_matter_key(item.text) for item in model_clauses]
    patched: list[TechnicalClause] = []
    for clause in regex_clauses:
        key = _matter_key(clause.text)
        if any(_same(key, existing) for existing in keys):
            continue
        clause.extract_source = "regex_patch"
        patched.append(clause)
    return patched


def absorb_model_facts(workflow: dict, payload: dict[str, Any]) -> None:
    facts = workflow.setdefault("technical_facts", {})
    promises = workflow.setdefault("technical_promises", {})
    if payload.get("who"):
        facts.setdefault("客户名", str(payload["who"]).strip())
    if payload.get("what"):
        facts.setdefault("项目理解", str(payload["what"]).strip())
    if payload.get("period"):
        facts.setdefault("服务期", str(payload["period"]).strip())
    if payload.get("sla"):
        value = str(payload["sla"]).strip()
        promises.setdefault("响应时限", value)
        facts.setdefault("响应时限", value)
    sidecar = workflow.setdefault("technical_sidecars", {"format_lines": [], "rejection_lines": []})
    order = sidecar.setdefault("format_lines", [])
    for title in payload.get("format_order") or []:
        line = str(title).strip()
        if line and line not in order:
            order.append(line)
    previous = workflow.get("technical_extract_model") or {}
    timeout_count = int(previous.get("timeout_count") or 0) + int(payload.get("timeout_count") or 0)
    chunks_attempted = int(previous.get("chunks_attempted") or 0) + int(payload.get("chunks_attempted") or 0)
    pages_read = int(previous.get("pages_read") or 0) + int(payload.get("pages_read") or 0)
    degraded = bool(previous.get("extract_degraded")) or bool(payload.get("extract_degraded"))
    if chunks_attempted and timeout_count * 2 > chunks_attempted:
        degraded = True
    workflow["technical_extract_model"] = {
        "used": bool(payload.get("items")) or bool(previous.get("used")),
        "pages_read": pages_read,
        "skip_reason": payload.get("skip_reason") or previous.get("skip_reason") or "",
        "item_count": int(previous.get("item_count") or 0) + len(payload.get("items") or []),
        **{
            key: int(previous.get(key) or 0) + int(payload.get(key) or 0)
            for key in ("requirement_count", "scoring_count", "rejection_count")
        },
        "timeout_count": timeout_count,
        "chunks_attempted": chunks_attempted,
        "extract_degraded": degraded,
    }
    workflow["extract_degraded"] = degraded
    workflow["extract_timeout_count"] = timeout_count
