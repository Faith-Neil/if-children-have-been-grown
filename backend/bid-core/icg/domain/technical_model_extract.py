# 为什么有这个文件：技术分册用本地模型按页读标，抽出响应挂载、废标约束、编制顺序和事实。
# 它解决什么问题：正则扫行会丢掉表格、换说法的服务期和「这份标是谁、要干什么」；模型读标做主路径，规则只补漏检。

from __future__ import annotations

import json
import re
from typing import Any

from icg.domain.technical_clause_extract import TechnicalClause, _matter_key, _same

EXTRACT_SYSTEM = (
    "你在读一份招标文件的一页或一块原文（块内带 [第 P 页] 页锚，表格用 Markdown 表呈现）。"
    "只根据这一块输出 JSON，不要解释。"
    "字段：who（招标人/业主）、what（要采购或运维什么）、period（服务期/维保期原文）、"
    "warranty（质保期原文，没有留空）、sla（故障响应或到场时限）、"
    "on_site（驻场人数或驻场要求，没有留空）、team（项目经理或核心团队要求，没有留空）、"
    "models（投标或运维涉及的核心产品/系统型号数组，没有用空数组）、"
    "format_order（编制顺序一级标题数组）、"
    "requirements（技术需求清单：数组，每项 text、quote、star、page）、"
    "scoring（评分规则清单：数组，每项 item、score、criteria、points、quote、page）、"
    "rejections（废标清单：数组，每项 text、quote、category、page）。"
    "requirements 是投标人必须在技术方案里回应的服务、指标、工作内容；star 为 true 表示带★或实质性条款。"
    "scoring 只收技术评分（技术方案、服务方案等主观分），不收报价、资质、业绩分；"
    "item 是评分项名称，score 是分值数字（原文没有写 null），criteria 是评分标准原文，"
    "points 是评委据以给分的得分要点数组，每条不超过 30 字。"
    "rejections 是废标、否决、无效投标条件，category 只能是 技术、资格、商务、格式 之一，不要当成要单独成章回答的服务项。"
    "text 是不超过 40 字的要点，quote 是原文逐字短句，page 是所在页码整数。"
    "表格单元格、跨页续表、换行拆开的句子也要读。没有的字段用空字符串或空数组。"
    "禁止编造本块没有的业主、系统名、型号、期限和分值。"
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
                "page": item.get("page"),
            })
    for rule in payload.get("scoring") or []:
        if not isinstance(rule, dict):
            continue
        name = str(rule.get("item") or "").strip()
        points = [str(point).strip() for point in rule.get("points") or [] if str(point or "").strip()]
        meta = {
            "score_item": name, "score": _score(rule.get("score")),
            "criteria": str(rule.get("criteria") or "").strip()[:400],
            "page": rule.get("page"),
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
                "page": item.get("page"),
            })
    return found


def _merge_duplicate(entry: dict, item: dict, result: dict) -> None:
    """同一事项在需求和评分里各出现一次时，保留一条并补上评分项名、分值与评分标准。"""
    if entry["role"] != "response_mount" or str(item.get("role") or "response_mount") != "response_mount":
        return
    if item.get("kind") == "scoring" and entry["kind"] != "scoring":
        result[LIST_OF_ROLE[("response_mount", entry["kind"])]] -= 1
        result[LIST_OF_ROLE[("response_mount", "scoring")]] += 1
        entry["kind"] = "scoring"
    for key in EXTRA_KEYS:
        if entry.get(key) in (None, "") and item.get(key) not in (None, ""):
            entry[key] = item[key]


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


def _table_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if "|" not in stripped:
        return None
    if stripped.startswith("|") and stripped.endswith("|"):
        cells = [c.strip() for c in stripped[1:-1].split("|")]
    else:
        cells = [c.strip() for c in stripped.split("|")]
    if len(cells) < 2:
        return None
    if all(re.fullmatch(r":?-{2,}:?", c or "") for c in cells if c):
        return None
    return cells


def _md_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _md_sep(col_count: int) -> str:
    return "| " + " | ".join("---" for _ in range(col_count)) + " |"


def _looks_like_header(cells: list[str]) -> bool:
    joined = "".join(cells)
    if any(k in joined for k in ("评分", "分值", "因素", "标准", "细则", "序号", "指标", "参数", "要求", "名称", "类别")):
        return True
    return not any(re.fullmatch(r"\d+(?:\.\d+)?分?", c) for c in cells if c)


def build_extract_windows(
    pages: list[str], *, limit: int = 2800, overlap: int = 240,
) -> list[tuple[int, str]]:
    """构造表格感知、带跨页续表表头与段间重叠的模型扫描窗口。"""
    units: list[tuple[int, str, tuple[str, str] | None]] = []
    active_header: tuple[int, list[str], str, str] | None = None

    for page_no, raw_page in enumerate(pages, start=1):
        text = str(raw_page or "").strip()
        if not text:
            continue
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            continue
        units.append((page_no, f"[第 {page_no} 页]", None))
        in_table_on_page = False
        for idx, line in enumerate(lines):
            cells = _table_cells(line)
            if cells is None:
                in_table_on_page = False
                # 非表格正文出现超过一行时，结束跨页续表承接状态
                if idx > 0:
                    active_header = None
                units.append((page_no, line, None))
                continue
            col_count = len(cells)
            if not in_table_on_page:
                in_table_on_page = True
                if (
                    idx == 0
                    and active_header is not None
                    and active_header[0] == col_count
                    and cells != active_header[1]
                    and not _looks_like_header(cells)
                ):
                    _, h_cells, h_md, sep_md = active_header
                    units.append((page_no, h_md, (h_md, sep_md)))
                    units.append((page_no, sep_md, (h_md, sep_md)))
                    units.append((page_no, _md_row(cells), (h_md, sep_md)))
                else:
                    h_md = _md_row(cells)
                    sep_md = _md_sep(col_count)
                    active_header = (col_count, cells, h_md, sep_md)
                    units.append((page_no, h_md, (h_md, sep_md)))
                    units.append((page_no, sep_md, (h_md, sep_md)))
            else:
                if active_header is not None and active_header[0] == col_count:
                    _, _, h_md, sep_md = active_header
                    units.append((page_no, _md_row(cells), (h_md, sep_md)))
                else:
                    h_md = _md_row(cells)
                    sep_md = _md_sep(col_count)
                    active_header = (col_count, cells, h_md, sep_md)
                    units.append((page_no, h_md, (h_md, sep_md)))
                    units.append((page_no, sep_md, (h_md, sep_md)))

    packed: list[tuple[int, str]] = []
    buf_lines: list[str] = []
    buf_len = 0
    start_page = 0
    last_page = 0
    prose_tail: list[str] = []

    for page_no, text_line, table_ctx in units:
        add_len = len(text_line) + (1 if buf_lines else 0)
        if buf_lines and buf_len + add_len > limit:
            packed.append((start_page, "\n".join(buf_lines).strip()))
            buf_lines = []
            buf_len = 0
            start_page = page_no
            if table_ctx is not None:
                h_md, sep_md = table_ctx
                prefix = [f"[第 {page_no} 页]", h_md, sep_md]
                buf_lines.extend(prefix)
                buf_len = sum(len(x) for x in prefix) + len(prefix) - 1
            elif overlap > 0 and prose_tail:
                carried: list[str] = []
                carried_chars = 0
                for prev in reversed(prose_tail):
                    if carried_chars + len(prev) > overlap and carried:
                        break
                    carried.insert(0, prev)
                    carried_chars += len(prev) + 1
                if carried:
                    if not text_line.startswith("[第 "):
                        carried.append(f"[第 {page_no} 页]")
                    buf_lines.extend(carried)
                    buf_len = sum(len(x) for x in carried) + len(carried) - 1
        if not buf_lines:
            start_page = page_no
        if text_line in buf_lines[-2:] and (text_line.startswith("| ") and "---" in text_line or text_line.startswith("[第 ")):
            continue
        buf_lines.append(text_line)
        buf_len += len(text_line) + (1 if len(buf_lines) > 1 else 0)
        last_page = page_no
        if table_ctx is None and not text_line.startswith("[第 "):
            prose_tail.append(text_line)
            if len(prose_tail) > 12:
                prose_tail.pop(0)
        else:
            prose_tail.clear()

    if buf_lines:
        packed.append((start_page or last_page or 1, "\n".join(buf_lines).strip()))
    return packed


def _chunks(pages: list[str], *, limit: int = 2400) -> list[tuple[int, str]]:
    return build_extract_windows(pages, limit=limit)


def _compact(text: str) -> str:
    return re.sub(r"[\s|★]+", "", str(text or ""))


def resolve_quote_page(pages: list[str], quote: str, fallback_page: int, model_page: Any = None) -> int:
    """按 quote 在各页原文中精确定位 1-based 页码；优先校验模型给的页码，再全书查找。"""
    total = len(pages)
    if total == 0:
        return max(1, int(fallback_page or 1))
    needle = _compact(quote)
    candidates: list[int] = []
    try:
        mp = int(model_page)
        if 1 <= mp <= total:
            candidates.append(mp)
    except (TypeError, ValueError):
        mp = 0
    if 1 <= fallback_page <= total and fallback_page not in candidates:
        candidates.append(fallback_page)
    for p in range(1, total + 1):
        if p not in candidates:
            candidates.append(p)
    if needle and len(needle) >= 3:
        short = needle[:16]
        for p in candidates:
            hay = _compact(pages[p - 1])
            if needle in hay or (len(short) >= 4 and short in hay):
                return p
    if candidates:
        return candidates[0]
    return max(1, min(fallback_page, total))


def resolve_chunk_id(workflow: dict | None, file_id: str, pages: list[str], page: int, quote: str) -> str:
    """关联本标切片 chunk_id（形如 file_id:page:idx），供溯源与正文检索锚定。"""
    from icg.domain.technical_tender_index import chunk_pages

    chunks = ((workflow or {}).get("tender_index") or {}).get("chunks")
    if not isinstance(chunks, list) or not chunks:
        chunks = chunk_pages(pages, file_id=file_id)
    same_file = [c for c in chunks if not file_id or str(c.get("file_id") or "") == str(file_id)]
    pool = same_file or chunks
    same_page = [c for c in pool if int(c.get("page") or 0) == int(page)]
    needle = _compact(quote)[:16]
    if needle:
        for candidate in [*same_page, *pool]:
            if needle in _compact(candidate.get("text") or ""):
                return str(candidate.get("id") or "")
    if same_page:
        return str(same_page[0].get("id") or "")
    return f"{file_id}:{page}:0" if file_id else f":{page}:0"


def error_is_timeout(exc: BaseException | None) -> bool:
    """真实适配器超时识别：httpx.TimeoutException/TimeoutError/asyncio.TimeoutError
    以及被 ModelCallError 包装的 RetryableModelError('timeout') cause 链（ISSUE-060）。"""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        name = type(current).__name__.lower()
        if "timeout" in name or "timedout" in name:
            return True
        message = str(current).lower()
        if "timeout" in message or "timed out" in message:
            return True
        current = current.__cause__ or (None if current.__suppress_context__ else current.__context__)
    return False


def _is_timeout(exc: BaseException) -> bool:
    return error_is_timeout(exc)


def extract_with_model(pages: list[str], model: Any, on_chunk=None) -> dict[str, Any]:
    """按页/块调用本地模型。失败的块跳过，不把空结果当成已读完整份标。"""
    result: dict[str, Any] = {
        "who": "",
        "what": "",
        "period": "",
        "warranty": "",
        "sla": "",
        "on_site": "",
        "team": "",
        "models": [],
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

    seen: dict[str, dict] = {}
    chunks = build_extract_windows(pages)
    total = len(chunks)
    timeouts = 0
    result["chunks_attempted"] = total
    for index, (page_no, blob) in enumerate(chunks, start=1):
        if on_chunk is not None:
            on_chunk(index, total)
        try:
            raw = call_with_profile(model.suggest, EXTRACT_SYSTEM, f"起始页码 {page_no}：\n{blob[:8000]}", profile=EXTRACT_CALL)
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
        for key in ("who", "what", "period", "warranty", "sla", "on_site", "team"):
            value = str(payload.get(key) or "").strip()
            if value and not result[key]:
                result[key] = value
        for model_name in payload.get("models") or []:
            clean_model = str(model_name or "").strip()
            if clean_model and clean_model not in result["models"]:
                result["models"].append(clean_model)
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
            if not key:
                continue
            existing = next((entry for old, entry in seen.items() if _same(key, old)), None)
            if existing is not None:
                _merge_duplicate(existing, item, result)
                continue
            role = str(item.get("role") or "response_mount").strip()
            if role not in ("response_mount", "rejection_constraint"):
                role = "response_mount"
            kind = str(item.get("kind") or "scoring").strip()
            if kind not in ("scoring", "spec"):
                kind = "scoring"
            exact_page = resolve_quote_page(pages, quote, page_no, item.get("page"))
            entry = {
                "text": text[:80],
                "quote": quote[:400],
                "page": exact_page,
                "kind": kind,
                "role": role,
            }
            entry.update({key: item[key] for key in EXTRA_KEYS if item.get(key) not in (None, "")})
            result["items"].append(entry)
            seen[key] = entry
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
    if payload.get("warranty"):
        facts.setdefault("质保期", str(payload["warranty"]).strip())
    if payload.get("sla"):
        value = str(payload["sla"]).strip()
        promises.setdefault("响应时限", value)
        facts.setdefault("响应时限", value)
    if payload.get("on_site"):
        facts.setdefault("驻场要求", str(payload["on_site"]).strip())
    if payload.get("team"):
        facts.setdefault("团队要求", str(payload["team"]).strip())
    if payload.get("models"):
        models = list(facts.get("目标型号") or [])
        for name in payload.get("models") or []:
            clean = str(name or "").strip()
            if clean and clean not in models:
                models.append(clean)
        if models:
            facts["目标型号"] = models
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
