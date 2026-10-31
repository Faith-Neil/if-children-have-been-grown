# 为什么有这个文件：实现 PRD v1.8 §5.8.1 / §5.8.3 的 R29 本公司查重与 R30 超范围响应（APP-M2-T235～T237）。
# 它解决什么问题：
# R29：正文与本公司近 N 个月历史标书、同期在编的其他标书、“仅供参考”资料逐字比对，
#      去掉空格标点后连续 dup_min_chars 个字相同记一处重复；招标原文、注明出处的段落、英文/数字术语与命令不算。
#      只在全文检查运行（不进章节循环与分册检查）；与“仅供参考”资料重复给警告，其余给提示。只比文本，不调模型。
# R30：①非增值、非系统章节里找不到对应招标条款的段落给警告；②招标未要求的额外数值承诺（时限、次数、人数、比例、期限
#      在条款原文、招标文件、SLA 招标值与已确认事实中都找不到）给警告，须项目负责人逐条确认；增值章节只豁免①不豁免②。
#      章节循环里的②由 chapter_loop 按同一判定直接转人工（EXTRA_COMMITMENT）。

from __future__ import annotations

import re
import time
from datetime import date, datetime, timezone
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# 文本归一与指纹
# ---------------------------------------------------------------------------

_SPACE_PUNCT = re.compile(r"[\s\u3000，。、；：？！“”‘’（）【】《》〈〉「」『』—…·,.;:?!'\"()\[\]{}<>|\-_*#=~`^]+")
# 平台基础术语白名单：英文/数字串（产品名、命令、参数、错误码、标准号，如 MySQL、ALTER SYSTEM、TLS1.2、GB/T 22239）
_ASCII_TERM = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._/:+\-]*")
_VARIABLE = re.compile(r"\{\{[^}]*\}\}|\[(?:证|片)(?::[^\]]*)?\]")
_CITED = re.compile(r"(出处|引自|摘自|来源)\s*[:：]")
BREAK = "\u0000"


def normalize(text: str, extra_terms: Iterable[str] = ()) -> str:
    """去掉变量、空格与标点；白名单术语替换为断点，使其不参与连续相同字符计数。"""
    value = _VARIABLE.sub(BREAK, text or "")
    for term in sorted({t for t in extra_terms if t}, key=len, reverse=True):
        value = value.replace(term, BREAK)
    value = _ASCII_TERM.sub(BREAK, value)
    return _SPACE_PUNCT.sub("", value)


def grams(value: str, n: int) -> set[str]:
    out: set[str] = set()
    for segment in value.split(BREAK):
        for i in range(len(segment) - n + 1):
            out.add(segment[i:i + n])
    return out


def duplicate_runs(value: str, n: int, index: dict[str, int], excluded: set[str]) -> tuple[int, list[tuple[str, set[int]]]]:
    """返回 (重复字数, [(重复片段, 命中来源下标集合)])。片段由相邻命中的 n 字窗口合并而成。"""
    runs: list[tuple[str, set[int]]] = []
    covered = 0
    for segment in value.split(BREAK):
        i, length = 0, len(segment)
        while i <= length - n:
            gram = segment[i:i + n]
            if gram in index and gram not in excluded:
                start, sources, j = i, {index[gram]}, i + 1
                while j <= length - n and segment[j:j + n] in index and segment[j:j + n] not in excluded:
                    sources.add(index[segment[j:j + n]])
                    j += 1
                end = j - 1 + n
                runs.append((segment[start:end], sources))
                covered += end - start
                i = end
            else:
                i += 1
    return covered, runs


def paragraphs_of(content: str) -> list[str]:
    return [p for p in (content or "").split("\n")]


def _skippable(paragraph: str) -> bool:
    text = paragraph.strip()
    return (not text or text.startswith("#") or text.startswith("|") or bool(_CITED.search(text)))


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _months_between(earlier: date, later: date) -> int:
    return (later.year - earlier.year) * 12 + (later.month - earlier.month) - (1 if later.day < earlier.day else 0)


def dup_settings(state: Any, company_id: str) -> dict[str, Any]:
    stored = ((getattr(state, "service_stores", {}) or {}).get("company_settings") or {}).get(company_id) or {}
    if hasattr(stored, "model_dump"):
        stored = stored.model_dump()
    custom = stored.get("custom_settings") or {}
    scopes = custom.get("dup_scopes") or {}
    return {
        "min_chars": max(4, int(stored.get("dup_min_chars") or 8)),
        "history_months": max(1, int(stored.get("dup_history_months") or 24)),
        "whitelist": [str(t) for t in custom.get("dup_whitelist") or [] if str(t).strip()],
        "history": scopes.get("history", True) is not False,
        "in_progress": scopes.get("in_progress", True) is not False,
        "reference": scopes.get("reference", True) is not False,
    }


_CLOSED_PROJECT_STATUS = {"submitted", "won", "lost", "closed", "archived", "已递交", "中标", "未中标"}


def tender_text(workflow: dict) -> str:
    parts = []
    for record in (workflow.get("files") or {}).values():
        pages = record.get("pages")
        if isinstance(pages, list):
            parts.extend(str(p) for p in pages)
        elif record.get("content"):
            parts.append(str(record["content"]))
    parts.extend(str(r.get("text", "")) for r in (workflow.get("requirements") or {}).values())
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# R29 本公司查重
# ---------------------------------------------------------------------------

def check_r29(state: Any, project: Any, workflow: dict, volume: str = "all", now_ts: float | None = None):
    from .compliance_rules import ComplianceRuleIssue, ComplianceRuleResult
    from .domain import new_id

    title = "本公司查重"
    from .project_access import project_volumes
    full_text = volume == "all" or tuple(project_volumes(state, project.id)) == (volume,)  # 只写技术标：技术分册即全文
    if not full_text:
        return ComplianceRuleResult(rule_id="R29", title=title, severity="info", passed=True,
                                    finding_summary="本公司查重只在全文检查和导出前运行，不在分册检查中运行。",
                                    suggestion="运行全文检查时比对。", issues=[], details={"skipped": "volume_check"})
    settings = dup_settings(state, project.company_id)
    n = settings["min_chars"]
    today = datetime.fromtimestamp(now_ts if now_ts is not None else time.time(), tz=timezone.utc).date()

    sources: list[dict] = []
    if settings["history"] or settings["reference"]:
        for item in state.library.values():
            if item.get("company_id") != project.company_id or not str(item.get("content") or "").strip():
                continue
            if item.get("type") == "history" and settings["history"]:
                submitted = _parse_date(item.get("submitted_on"))
                if submitted is not None and _months_between(submitted, today) > settings["history_months"]:
                    continue
                sources.append({"kind": "history", "id": item["id"], "name": item.get("name", ""),
                                "submitted_on": item.get("submitted_on"), "text": item["content"],
                                "note": "" if submitted else "递交日期未登记，按在比对年限内处理"})
            elif item.get("source_tier") == "reference" and settings["reference"]:
                sources.append({"kind": "reference", "id": item["id"], "name": item.get("name", ""), "text": item["content"]})
    if settings["in_progress"]:
        for other in state.projects.values():
            if (other.id == project.id or other.company_id != project.company_id or getattr(other, "is_archived", False)
                    or str(getattr(other, "status", "")).lower() in _CLOSED_PROJECT_STATUS):
                continue
            text = "\n".join(c.content or "" for c in state.chapters.values() if c.project_id == other.id)
            if text.strip():
                sources.append({"kind": "in_progress", "id": other.id, "name": other.name, "text": text})

    index: dict[str, int] = {}
    for position, source in enumerate(sources):
        for paragraph in paragraphs_of(source["text"]):
            for gram in grams(normalize(paragraph, settings["whitelist"]), n):
                current = index.get(gram)
                # 同一片段既出现在“仅供参考”资料又出现在历史标书时，按更严重的“仅供参考”报
                if current is None or (sources[current]["kind"] != "reference" and source["kind"] == "reference"):
                    index[gram] = position
    excluded = grams(normalize(tender_text(workflow), settings["whitelist"]), n)

    issues = []
    total_chars = dup_chars = 0
    chapters = [c for c in state.chapters.values() if c.project_id == project.id]
    for chapter in chapters:
        for paragraph_index, paragraph in enumerate(paragraphs_of(chapter.content)):
            normalized = normalize(paragraph, settings["whitelist"])
            if _skippable(paragraph):
                continue
            total_chars += len(normalized.replace(BREAK, ""))
            covered, runs = duplicate_runs(normalized, n, index, excluded)
            if not runs:
                continue
            dup_chars += covered
            hit = sorted({i for _, s in runs for i in s})
            kinds = {sources[i]["kind"] for i in hit}
            severity = "warning" if "reference" in kinds else "info"
            targets = [{"kind": sources[i]["kind"], "id": sources[i]["id"], "name": sources[i]["name"],
                        "submitted_on": sources[i].get("submitted_on"), "note": sources[i].get("note", "")} for i in hit]
            label = {"reference": "“仅供参考”资料", "history": "本公司历史标书", "in_progress": "本公司在编标书"}
            names = "、".join(f"{label[t['kind']]}《{t['name']}》" for t in targets[:3])
            length = max(1, len(normalized.replace(BREAK, "")))
            issues.append(ComplianceRuleIssue(
                id=new_id("issue"), rule_id="R29", code="COMPANY_DUPLICATE_TEXT", severity=severity,
                message=f"《{chapter.title}》第 {paragraph_index + 1} 段与{names}重复 {covered} 字（占本段 {round(covered * 100 / length)}%）。",
                chapter_id=chapter.id,
                details={"paragraph_index": paragraph_index, "quote": paragraph.strip()[:120],
                         "fragments": [text for text, _ in runs][:5], "dup_char_count": covered,
                         "targets": targets, "dup_params_snapshot": {k: settings[k] for k in ("min_chars", "history_months")}},
            ).to_dict())
    passed = not issues
    worst = "warning" if any(i["severity"] == "warning" for i in issues) else "info"
    return ComplianceRuleResult(
        rule_id="R29", title=title, severity="info" if passed else worst, passed=passed,
        finding_summary=("未发现与本公司历史标书、在编标书或“仅供参考”资料的连续重复。" if passed else
                         f"{len(issues)} 个段落存在连续 {n} 字以上重复，全文重复 {dup_chars} 字。"),
        suggestion=("" if passed else "局部改写重复段落，或换用方案片段的替代版本；与“仅供参考”资料重复须项目负责人填写理由放行。"),
        issues=[i for i in issues],
        details={"compared_sources": len(sources), "min_chars": n, "history_months": settings["history_months"],
                 "dup_chars": dup_chars, "total_chars": total_chars,
                 "full_text_ratio": round(dup_chars / total_chars, 4) if total_chars else 0.0},
    )


# ---------------------------------------------------------------------------
# R30 超范围响应
# ---------------------------------------------------------------------------

_NUMBER_UNIT = re.compile(
    r"(?<![0-9.])(\d+(?:\.\d+)?)\s*(分钟|小时|个工作日|工作日|自然日|天|日|周|个月|月|年|次|人|名|%|％|课时)")
_UNIT_NORMAL = {"个工作日": "工作日", "自然日": "日", "天": "日", "个月": "月", "名": "人", "％": "%"}
# 数字后面跟这些字说明不是承诺（日期、章节号、产品型号）
_NON_COMMITMENT_AFTER = re.compile(r"^(?:月\d|年\d|年度|年版|月份|日\d)")
_YEAR = re.compile(r"^(19|20)\d\d$")


def commitments_in(text: str) -> list[tuple[str, str, str]]:
    """抽取正文中的“数值＋单位”承诺：[(数值, 归一单位, 原样片段)]。"""
    found = []
    clean = _VARIABLE.sub(" ", text or "")
    for match in _NUMBER_UNIT.finditer(clean):
        value, unit = match.group(1), match.group(2)
        if unit == "年" and _YEAR.match(value):
            continue  # 2025年 是日期
        if _NON_COMMITMENT_AFTER.match(clean[match.end(1):match.end(1) + 3].lstrip()):
            continue
        found.append((value.rstrip("0").rstrip(".") if "." in value else value, _UNIT_NORMAL.get(unit, unit), match.group(0)))
    return found


def tender_number_basis(state: Any, project: Any, workflow: dict) -> set[tuple[str, str]]:
    """招标依据中出现过的（数值, 单位）：条款原文与响应依据、招标文件全文、SLA 招标值、已确认项目事实。"""
    basis = {(v, u) for v, u, _ in commitments_in(tender_text(workflow))}
    for fact in (workflow.get("facts") or {}).values():
        if fact.get("status") == "confirmed":
            basis |= {(v, u) for v, u, _ in commitments_in(str(fact.get("value", "")))}
    try:
        from .sla import public_sla
        for row in public_sla(state, project.id).get("rows", []):
            if row.get("requirement_id") or row.get("tender_required_value") not in (None, ""):
                for key, unit_key in (("tender_required_value", "tender_unit"), ("project_value", "project_unit")):
                    value = row.get(key)
                    if value not in (None, ""):
                        basis |= {(v, u) for v, u, _ in commitments_in(f"{value}{row.get(unit_key) or ''}")}
    except Exception:  # SLA 未建立时只按条款与事实判定
        pass
    return basis


def _value_added(workflow: dict, chapter_id: str) -> bool:
    meta = (workflow.get("outline_plans") or {}).get(chapter_id) or {}
    plan = ((workflow.get("writing_plan") or {}).get("chapters") or {}).get(chapter_id) or {}
    return bool(meta.get("value_added") or plan.get("value_added") or meta.get("chapter_type") == "value_added")


def _system_chapter(workflow: dict, chapter: Any) -> bool:
    from .outline_plan import infer_chapter_type
    meta = (workflow.get("outline_plans") or {}).get(chapter.id) or {}
    return infer_chapter_type(chapter.title, meta.get("chapter_type")) == "system"


def _bigrams(text: str) -> set[str]:
    value = normalize(text).replace(BREAK, "")
    return {value[i:i + 2] for i in range(len(value) - 1)}


def check_r30(state: Any, project: Any, workflow: dict, volume: str = "all"):
    from .compliance_rules import ComplianceRuleIssue, ComplianceRuleResult
    from .domain import new_id

    basis = tender_number_basis(state, project, workflow)
    requirements = list((workflow.get("requirements") or {}).values())
    issues = []
    checked = 0
    for chapter in state.chapters.values():
        if chapter.project_id != project.id or (volume != "all" and chapter.volume != volume):
            continue
        content = chapter.content or ""
        if not content.strip() or _system_chapter(workflow, chapter):
            continue
        checked += 1
        paragraphs = paragraphs_of(content)
        value_added = _value_added(workflow, chapter.id)
        rows = [r for r in requirements if r.get("chapter_id") == chapter.id and r.get("status") != "rejected"]
        row_grams: set[str] = set()
        for row in rows:
            row_grams |= _bigrams(f"{row.get('text', '')}{row.get('response', '')}{row.get('confirmed_response', '')}")
        body = [i for i, p in enumerate(paragraphs) if p.strip() and not p.strip().startswith(("#", "|"))]
        # ① 无对应条款的段落（增值章节豁免）。章节开头概述、结尾总结、过渡短句对应本节整体。
        if not value_added:
            if not rows and body:
                issues.append(ComplianceRuleIssue(
                    id=new_id("issue"), rule_id="R30", code="SCOPE_CHAPTER_WITHOUT_CLAUSE", severity="warning",
                    message=f"《{chapter.title}》没有对应的招标条款；若为增值内容，请在写作方案中标为增值章节。",
                    chapter_id=chapter.id, details={"paragraph_count": len(body)}).to_dict())
            elif rows:
                for i in body[1:-1] if len(body) > 2 else []:
                    text = paragraphs[i].strip()
                    own = _bigrams(text)
                    if len(own) < 15:
                        continue  # 过渡短句
                    overlap = len(own & row_grams) / len(own)
                    if overlap < 0.12:
                        issues.append(ComplianceRuleIssue(
                            id=new_id("issue"), rule_id="R30", code="SCOPE_PARAGRAPH_WITHOUT_CLAUSE", severity="warning",
                            message=f"《{chapter.title}》第 {i + 1} 段找不到对应的招标条款，可能是超范围内容。",
                            chapter_id=chapter.id,
                            details={"paragraph_index": i, "quote": text[:120], "overlap": round(overlap, 3)}).to_dict())
        # ② 额外数值承诺（增值章节同样检查）
        for i, paragraph in enumerate(paragraphs):
            extra = [(v, u, raw) for v, u, raw in commitments_in(paragraph) if (v, u) not in basis]
            if not extra:
                continue
            seen = []
            for v, u, raw in extra:
                if raw not in seen:
                    seen.append(raw)
            issues.append(ComplianceRuleIssue(
                id=new_id("issue"), rule_id="R30", code="EXTRA_NUMERIC_COMMITMENT", severity="warning",
                message=f"《{chapter.title}》第 {i + 1} 段承诺了招标未要求的数值：{'、'.join(seen[:5])}；须项目负责人逐条确认保留或删除。",
                chapter_id=chapter.id,
                details={"paragraph_index": i, "quote": paragraph.strip()[:120], "values": seen,
                         "value_added_chapter": value_added}).to_dict())
    passed = not issues
    return ComplianceRuleResult(
        rule_id="R30", title="超范围响应", severity="info" if passed else "warning", passed=passed,
        finding_summary=("未发现无条款段落或招标未要求的数值承诺。" if passed else f"发现 {len(issues)} 处超范围响应。"),
        suggestion=("" if passed else "删除与招标无关的内容；额外数值承诺由项目负责人逐条确认保留（填写理由）或删除。"),
        issues=issues, details={"checked_chapters": checked, "tender_number_basis": len(basis)},
    )
