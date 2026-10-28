# 为什么有这个文件：按 PRD v1.8 §5.7.4 由系统规则编排章节“检查 → 定位修正 → 再检查”循环，并把自动修不了的问题送进人工处理队列。
# 它解决什么问题：
# 1. 处理路径由规则判定：缺证据的【待补】、星号/废标、金额与承诺数值、人员身份、商务偏离、证据引用、系统生成章节等直接转人工，自动修正永远不改动它们（§5.7.4 第 4 条）；
# 2. 定位修正只改被点名的段落，其余段落逐字不变；只做不编造的确定性修正（删除对话残留、补签章槽位、用已确认事实变量替换【待补】、移除失效知识片段标记），
#    模型改写结果必须通过“不新增数字、不新增引用、不新增直接转人工缺陷”的安全复核才会被采用；
# 3. 停止条件按 §5.7.4 第 6 条的顺序判定（修正引入新问题回退 / 全部解决 / 剩余需人工 / 达到最大轮数 / 问题数未减少），同一问题自动修正 2 次仍在则单独升级转人工；
# 4. 问题记录带指纹跨轮跟踪，新一次循环沿用同指纹的历史编号并重新打开，处理与驳回记录不可删除。

from __future__ import annotations

import hashlib
import re
from typing import Any, Callable

from .chapter_generation import (
    AI_CONVERSATION_RESIDUALS,
    CITATION_PATTERN,
    MISSING_SEAL_TRIGGERS,
    NEGATIVE_DEVIATION_TRIGGERS,
    PLACEHOLDER_REGEXES,
    SEAL_SIGNATURE_REPLACEMENTS,
    STATUTORY_FORM_KEYWORDS,
    VALID_SEAL_MARKERS,
)

DEFAULT_MAX_ROUNDS = 3
MAX_FIX_ATTEMPTS = 2  # §5.7.4 第 5 条：修正次数上限固定为 2，MVP 不开放配置

ROUTE_AUTO = "auto_fix"
ROUTE_DIRECT = "direct_human"
ROUTE_ESCALATED = "escalated_human"

# 直接转人工的情形（§5.7.4 第 4 条）；代码给前端分组，文案给人看。
HUMAN_REASONS: dict[str, str] = {
    "MISSING_EVIDENCE": "缺证据的【待补】",
    "STAR_OR_DISQUALIFY": "星号或废标条款",
    "AMOUNT_OR_COMMITMENT": "金额或承诺数值",
    "PERSONNEL_IDENTITY": "人员身份",
    "BUSINESS_DEVIATION": "商务偏离",
    "EVIDENCE_CITATION": "证据引用问题",
    "SYSTEM_CHAPTER": "系统生成章节",
    "FIX_LIMIT_REACHED": "同一问题自动修正 2 次仍在",
    "LOOP_STOPPED": "循环停止时仍未解决",
    "EXTRA_COMMITMENT": "招标未要求的额外数值承诺",
}

STOP_REASONS: dict[str, str] = {
    "FIX_REGRESSION": "修正引入新问题",
    "ALL_RESOLVED": "问题全部解决",
    "NEED_HUMAN": "剩余问题需人工处理",
    "MAX_ROUNDS": "达到最大轮数",
    "NO_DECREASE": "问题数量未减少",
    "MANUAL_TERMINATED": "人工终止",
}

# 问题状态（字典 v1.7 §4.12）
OPEN_STATUSES = ("pending_fix", "pending_human")
CLOSED_STATUSES = ("resolved", "human_handled", "rejected", "void")

RESOLVE_METHODS: dict[str, str] = {
    "edited": "已修改正文",
    "keep_placeholder": "保留【待补】等资料补齐",
    "replaced_variable": "已替换为变量",
}
REJECT_REASONS = {"false_positive": "误报", "not_adopted": "不采纳"}

_AMOUNT_WORDS = ("金额", "报价", "价格", "费用", "万元", "元", "响应时间", "到场", "恢复", "时限", "次数", "人数", "比例", "%", "小时", "分钟")
_PERSON_WORDS = ("项目经理", "人员", "姓名", "工程师", "证书", "身份证", "职务", "负责人", "驻场")
_SYSTEM_CHAPTER_WORDS = ("点对点应答", "评审索引表", "偏离表", "年度服务计划表", "证明材料清单")
_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def split_paragraphs(content: str) -> list[str]:
    """按行切分段落；合并时用 "\n" 原样拼回，未被点名的段落逐字不变。"""
    return (content or "").split("\n")


def join_paragraphs(paragraphs: list[str]) -> str:
    return "\n".join(paragraphs)


def paragraph_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def _placeholders(text: str) -> list[str]:
    found: set[str] = set()
    for pattern in PLACEHOLDER_REGEXES:
        for match in pattern.finditer(text):
            found.add(match.group(0))
    # 去掉被更长标记包含的短标记，例如“待补”包含于“【待补：项目经理】”
    return sorted(token for token in found if not any(token != other and token in other for other in found))


def _is_statutory(title: str) -> bool:
    return any(keyword in (title or "") for keyword in STATUTORY_FORM_KEYWORDS)


def _citations(text: str) -> list[tuple[str, str]]:
    return [(m.group(1), (m.group(2) or "").strip()) for m in CITATION_PATTERN.finditer(text or "")]


def _fact_variable(token: str, facts: list[dict]) -> str | None:
    """只用已确认的项目事实替换【待补】；找不到对应事实时不编造。"""
    inner = token.strip("【】[]")
    inner = inner.split("：", 1)[-1].split(":", 1)[-1].strip()
    if not inner or inner in ("待补", "待完善", "待确认", "占位", "占位符"):
        return None
    for fact in facts:
        if fact.get("status") not in (None, "confirmed"):
            continue
        key = str(fact.get("key") or fact.get("label") or "").strip()
        if key and (key == inner or key in inner or inner in key):
            variable = (fact.get("variable") or fact.get("variable_token")
                        or ("{{fact:" + str(fact["id"]) + "}}" if fact.get("id") else ""))
            return variable or None
    return None


class LoopContext:
    """一次循环需要的只读依据。"""

    def __init__(self, *, title: str = "", allowed_evidence_ids: set[str] | None = None,
                 allowed_snippet_ids: set[str] | None = None, facts: list[dict] | None = None,
                 critical: bool = False, system_chapter: bool | None = None, locked_paragraphs: set[int] | None = None,
                 tender_numbers: set[tuple[str, str]] | None = None):
        self.title = title or ""
        self.allowed_evidence_ids = set(allowed_evidence_ids or ())
        self.allowed_snippet_ids = set(allowed_snippet_ids or ())
        self.facts = list(facts or [])
        self.critical = critical
        self.system_chapter = (any(w in self.title for w in _SYSTEM_CHAPTER_WORDS)
                               if system_chapter is None else system_chapter)
        self.locked_paragraphs = set(locked_paragraphs or ())
        # R30 ②：招标依据中出现过的（数值, 单位）；None 表示调用方未提供依据，不做该项检查
        self.tender_numbers = tender_numbers


def _finding(code: str, rule: str, level: str, index: int, text: str, message: str,
             suggestion: str, route: str, reason: str | None = None, tokens: list[str] | None = None) -> dict:
    quote = text.strip()
    if len(quote) > 80:
        quote = quote[:80] + "…"
    return {
        "fingerprint": f"{rule}|{code}|P{index}",
        "code": code, "rule": rule, "source": "rule", "level": level,
        "severity": "high" if level == "blocker" else "medium",
        "paragraph_index": index, "quote": quote, "message": message, "suggestion": suggestion,
        "route": route, "human_reason": reason, "tokens": tokens or [],
    }


def check_paragraphs(paragraphs: list[str], context: LoopContext) -> list[dict]:
    """规则层检查（可复现）。每个段落每类问题一条记录。"""
    findings: list[dict] = []
    statutory = _is_statutory(context.title)

    def route_for(default_route: str, reason: str | None, index: int) -> tuple[str, str | None]:
        if context.system_chapter:
            return ROUTE_DIRECT, "SYSTEM_CHAPTER"
        if default_route == ROUTE_AUTO and index in context.locked_paragraphs:
            return ROUTE_DIRECT, "LOOP_STOPPED"
        return default_route, reason

    for index, text in enumerate(paragraphs):
        if not text.strip():
            continue
        tokens = _placeholders(text)
        if tokens:
            fixable = [t for t in tokens if _fact_variable(t, context.facts)]
            if len(fixable) == len(tokens):
                route, reason = route_for(ROUTE_AUTO, None, index)
                suggestion = "已有确认的项目事实，替换为事实变量。"
            else:
                joined = "".join(tokens)
                if context.critical:
                    reason = "STAR_OR_DISQUALIFY"
                elif any(w in joined for w in _AMOUNT_WORDS):
                    reason = "AMOUNT_OR_COMMITMENT"
                elif any(w in joined for w in _PERSON_WORDS):
                    reason = "PERSONNEL_IDENTITY"
                else:
                    reason = "MISSING_EVIDENCE"
                route, reason = route_for(ROUTE_DIRECT, reason, index)
                suggestion = "补录资料或确认项目事实后替换；资料暂缺时保留【待补】，导出前须清零。"
            findings.append(_finding("PLACEHOLDER_RESIDUAL", "R15", "blocker", index, text,
                                     "正文残留【待补】等占位标记：" + "、".join(tokens[:5]),
                                     suggestion, route, reason, tokens))
        residuals = [r for r in AI_CONVERSATION_RESIDUALS if r in text]
        if residuals:
            route, reason = route_for(ROUTE_AUTO, None, index)
            findings.append(_finding("AI_CONVERSATION_RESIDUAL", "R34", "blocker", index, text,
                                     "正文残留模型对话语句：" + "、".join(residuals[:3]),
                                     "由系统直接删除对话残留句。", route, reason, residuals))
        deviations = [d for d in NEGATIVE_DEVIATION_TRIGGERS if d in text]
        if deviations:
            route, reason = route_for(ROUTE_DIRECT, "STAR_OR_DISQUALIFY" if context.critical else "BUSINESS_DEVIATION", index)
            findings.append(_finding("NEGATIVE_DEVIATION_DETECTED", "R37", "blocker", index, text,
                                     "正文出现偏离或不满足表述：" + "、".join(deviations[:3]),
                                     "核实是否确属偏离：属实则保留并在偏离表登记理由；能够满足则由负责人改写并补充依据。系统不自动改写承诺。",
                                     route, reason, deviations))
        if statutory:
            missing = [m for m in MISSING_SEAL_TRIGGERS if m in text]
            if missing:
                route, reason = route_for(ROUTE_AUTO, None, index)
                findings.append(_finding("MANDATORY_SEAL_SIGNATURE_MISSING", "R24", "blocker", index, text,
                                         "法定表单存在未签字或未盖章标记：" + "、".join(missing[:3]),
                                         "替换为标准签字、盖章槽位，实际签章在系统外完成。", route, reason, missing))
        fabricated = sorted({ref for kind, ref in _citations(text)
                             if kind == "证" and ref and ref not in context.allowed_evidence_ids})
        if fabricated:
            route, reason = route_for(ROUTE_DIRECT, "EVIDENCE_CITATION", index)
            findings.append(_finding("FABRICATED_OR_INVALID_EVIDENCE_CITATION", "R01", "blocker", index, text,
                                     "正文引用了本章依据中没有的证据编号：" + "、".join(f"[证:{r}]" for r in fabricated),
                                     "到资料库补录或在响应矩阵挂接真实证据；没有依据的事实改为【待补】。",
                                     route, reason, fabricated))
        if context.allowed_snippet_ids:
            unverified = sorted({ref for kind, ref in _citations(text)
                                 if kind == "片" and ref and ref not in context.allowed_snippet_ids})
            if unverified:
                route, reason = route_for(ROUTE_AUTO, None, index)
                findings.append(_finding("UNVERIFIED_SNIPPET_CITATION", "R02", "warning", index, text,
                                         "正文引用了本章候选以外的知识片段：" + "、".join(f"[片:{r}]" for r in unverified),
                                         "移除失效的片段标记。", route, reason, unverified))
    if context.tender_numbers is not None:
        from .scope_rules import commitments_in
        for index, text in enumerate(paragraphs):
            extra = []
            for value, unit, raw in commitments_in(text):
                if (value, unit) not in context.tender_numbers and raw not in extra:
                    extra.append(raw)
            if extra:
                # 额外承诺不由系统改写，也不随系统章节改道：一律由项目负责人确认保留或删除
                findings.append(_finding("EXTRA_NUMERIC_COMMITMENT", "R30", "warning", index, text,
                                         "承诺了招标未要求的数值：" + "、".join(extra[:5]),
                                         "项目负责人确认保留（填写理由，必要时登记为项目事实）或删除。",
                                         ROUTE_DIRECT, "EXTRA_COMMITMENT", extra))
    if statutory and paragraphs and not any(m in join_paragraphs(paragraphs) for m in VALID_SEAL_MARKERS):
        last = max((i for i, t in enumerate(paragraphs) if t.strip()), default=len(paragraphs) - 1)
        if not any(f["code"] == "MANDATORY_SEAL_SIGNATURE_MISSING" for f in findings):
            route, reason = route_for(ROUTE_AUTO, None, last)
            findings.append(_finding("MANDATORY_SEAL_SIGNATURE_MISSING", "R24", "blocker", last, paragraphs[last],
                                     f"法定表单「{context.title}」缺少签字、盖章槽位",
                                     "在落款处补充签字、盖章槽位。", route, reason))
    return findings


def deterministic_fix(text: str, issues: list[dict], context: LoopContext) -> str:
    """只做不编造的修正：删对话残留、补签章槽位、用已确认事实变量换【待补】、移除失效片段标记。"""
    fixed = text
    codes = {issue["code"] for issue in issues}
    if "AI_CONVERSATION_RESIDUAL" in codes:
        for residual in AI_CONVERSATION_RESIDUALS:
            fixed = fixed.replace(residual, "")
    if "MANDATORY_SEAL_SIGNATURE_MISSING" in codes:
        replaced = False
        for missing, slot in SEAL_SIGNATURE_REPLACEMENTS.items():
            if missing in fixed:
                fixed = fixed.replace(missing, slot)
                replaced = True
        if not replaced and not any(m in fixed for m in VALID_SEAL_MARKERS):
            fixed = fixed.rstrip() + " 法定代表人或授权代表签字：【法定代表人签字】 投标人（盖章）：【公章】"
    if "PLACEHOLDER_RESIDUAL" in codes:
        for token in _placeholders(fixed):
            variable = _fact_variable(token, context.facts)
            if variable:
                fixed = fixed.replace(token, variable)
    if "UNVERIFIED_SNIPPET_CITATION" in codes:
        for kind, ref in _citations(fixed):
            if kind == "片" and ref and ref not in context.allowed_snippet_ids:
                fixed = fixed.replace(f"[片:{ref}]", "")
    fixed = re.sub(r"[ \t]{2,}", " ", fixed)
    return fixed.strip() if fixed.strip() else fixed


def model_fix_is_safe(original: str, rewritten: str, context: LoopContext) -> bool:
    """模型改写只有在没带入新数字、新引用和新的直接转人工缺陷时才可采用（§5.7.4 第 5 条第 3 项）。"""
    if not rewritten or not rewritten.strip() or "\n" in rewritten.strip():
        return False
    if any(r in rewritten for r in AI_CONVERSATION_RESIDUALS):
        return False
    if set(_NUMBER.findall(rewritten)) - set(_NUMBER.findall(original)):
        return False
    if set(_citations(rewritten)) - set(_citations(original)):
        return False
    before = {f["code"] for f in check_paragraphs([original], context) if f["route"] != ROUTE_AUTO}
    after = {f["code"] for f in check_paragraphs([rewritten], context) if f["route"] != ROUTE_AUTO}
    return after <= before


def run_chapter_loop(content: str, context: LoopContext, *, max_rounds: int = DEFAULT_MAX_ROUNDS,
                     model_fix: Callable[[str, list[dict]], str | None] | None = None) -> dict:
    """执行一次章节循环。返回最终内容、轮次记录、停止原因和未解决问题。"""
    max_rounds = max(1, min(int(max_rounds or DEFAULT_MAX_ROUNDS), 5))
    paragraphs = split_paragraphs(content)
    tracker: dict[str, dict] = {}  # 指纹 → 跨轮信息
    rounds: list[dict] = []
    previous_findings: list[dict] | None = None
    previous_paragraphs: list[str] | None = None
    last_modified: set[int] = set()
    stop_reason = "ALL_RESOLVED"
    rolled_back = False
    findings: list[dict] = []

    for round_no in range(1, max_rounds + 1):
        findings = check_paragraphs(paragraphs, context)
        current = {f["fingerprint"] for f in findings}
        record = {"round": round_no, "checked_hash": paragraph_hash(join_paragraphs(paragraphs)),
                  "found": len(findings), "new": 0, "resolved": 0, "modified_paragraphs": [], "conclusion": "",
                  "codes": sorted({f["code"] for f in findings}), "fixes": []}
        if previous_findings is not None:
            previous_fps = {f["fingerprint"] for f in previous_findings}
            introduced = [f for f in findings if f["fingerprint"] not in previous_fps and f["paragraph_index"] in last_modified]
            record["new"] = len([f for f in findings if f["fingerprint"] not in previous_fps])
            record["resolved"] = len(previous_fps - current)
            if introduced:
                paragraphs = previous_paragraphs or paragraphs
                findings = previous_findings
                stop_reason, rolled_back = "FIX_REGRESSION", True
                record["conclusion"] = f"已回退到第 {round_no - 1} 轮的版本"
                rounds.append(record)
                break
        for f in findings:
            info = tracker.setdefault(f["fingerprint"], {"first_round": round_no, "fix_count": 0})
            info["last_round"] = round_no
            f["first_round"], f["last_round"], f["fix_count"] = info["first_round"], round_no, info["fix_count"]
            if f["route"] == ROUTE_AUTO and info["fix_count"] >= MAX_FIX_ATTEMPTS:
                f["route"], f["human_reason"] = ROUTE_ESCALATED, "FIX_LIMIT_REACHED"
        auto = [f for f in findings if f["route"] == ROUTE_AUTO]
        if not findings:
            stop_reason = "ALL_RESOLVED"
        elif not auto:
            stop_reason = "NEED_HUMAN"
        elif round_no == max_rounds:
            stop_reason = "MAX_ROUNDS"
        elif previous_findings is not None and len(findings) >= len(previous_findings):
            stop_reason = "NO_DECREASE"
        else:
            stop_reason = ""
        if stop_reason:
            record["conclusion"] = STOP_REASONS[stop_reason]
            rounds.append(record)
            break
        previous_findings, previous_paragraphs = findings, list(paragraphs)
        by_paragraph: dict[int, list[dict]] = {}
        for f in auto:
            by_paragraph.setdefault(f["paragraph_index"], []).append(f)
        modified: set[int] = set()
        fixes: list[dict] = []
        for index, issues in by_paragraph.items():
            original = paragraphs[index]
            replacement = None
            fixed_by = "rule"
            if model_fix is not None:
                try:
                    candidate = model_fix(original, issues)
                except Exception:
                    candidate = None
                if candidate and model_fix_is_safe(original, candidate, context):
                    replacement = candidate.strip()
                    fixed_by = "model"
            if replacement is None:
                replacement = deterministic_fix(original, issues, context)
            for issue in issues:
                tracker[issue["fingerprint"]]["fix_count"] += 1
            if replacement != original:
                paragraphs[index] = replacement
                modified.add(index)
                fixes.append({"paragraph_index": index, "by": fixed_by, "codes": sorted({i["code"] for i in issues})})
        last_modified = modified
        record["modified_paragraphs"] = sorted(modified)
        record["fixes"] = sorted(fixes, key=lambda item: item["paragraph_index"])
        record["conclusion"] = "继续修正"
        rounds.append(record)

    remaining = []
    for f in findings:
        item = dict(f)
        if item["route"] == ROUTE_AUTO:
            item["route"], item["human_reason"] = ROUTE_ESCALATED, "LOOP_STOPPED"
        item["fix_count"] = tracker.get(item["fingerprint"], {}).get("fix_count", 0)
        remaining.append(item)
    return {
        "content": join_paragraphs(paragraphs),
        "rounds": rounds,
        "max_rounds": max_rounds,
        "stop_reason": stop_reason,
        "stop_reason_label": STOP_REASONS[stop_reason],
        "rolled_back": rolled_back,
        "issues": remaining,
        "passed": not remaining,
    }


# ---------------------------------------------------------------------------
# 人工处理队列的持久化记录（workflow["human_queue"]）
# ---------------------------------------------------------------------------

def queue_store(workflow: dict) -> dict:
    store = workflow.setdefault("human_queue", {})
    store.setdefault("loops", {})
    store.setdefault("issues", {})
    store.setdefault("sequence", {})
    return store


def chapter_loop_status(store: dict, chapter_id: str) -> str | None:
    loop = store.get("loops", {}).get(chapter_id)
    return loop.get("status") if loop else None


def record_loop(workflow: dict, chapter: Any, chapter_number: int, outcome: dict, *, actor_id: str,
                now_iso: str, checked_revision: int, kind: str = "generation", meta: dict | None = None) -> dict:
    """把一次循环的结果写进队列：同指纹沿用编号并重新打开，未再出现的关闭为已解决。"""
    store = queue_store(workflow)
    previous = store["loops"].get(chapter.id)
    loop_no = (previous or {}).get("loop_no", 0) + 1
    existing = {i["fingerprint"]: i for i in store["issues"].values() if i["chapter_id"] == chapter.id}
    seen: set[str] = set()
    for finding in outcome["issues"]:
        fp = finding["fingerprint"]
        seen.add(fp)
        issue = existing.get(fp)
        if issue and issue["status"] == "rejected" and issue["level"] != "blocker":
            continue  # 已驳回的警告不再重复打开
        if issue is None:
            sequence = store["sequence"].get(chapter.id, 0) + 1
            store["sequence"][chapter.id] = sequence
            issue = {"id": f"hq-{chapter.id}-{sequence}", "number": f"{chapter_number}-{sequence:03d}",
                     "chapter_id": chapter.id, "volume": chapter.volume, "fingerprint": fp,
                     "history": [], "created_at": now_iso}
            store["issues"][issue["id"]] = issue
        issue.update({key: finding[key] for key in (
            "code", "rule", "source", "level", "severity", "paragraph_index", "quote", "message",
            "suggestion", "route", "human_reason", "tokens", "first_round", "last_round", "fix_count")})
        issue.update({"status": "pending_human", "loop_no": loop_no, "updated_at": now_iso,
                      "human_reason_label": HUMAN_REASONS.get(finding.get("human_reason") or "", "")})
        issue["history"].append({"at": now_iso, "action": "opened", "loop_no": loop_no, "actor_id": actor_id})
    for fp, issue in existing.items():
        if fp not in seen and issue["status"] in OPEN_STATUSES:
            issue["status"] = "resolved"
            issue["updated_at"] = now_iso
            issue["history"].append({"at": now_iso, "action": "resolved_by_check", "loop_no": loop_no, "actor_id": actor_id})
    pending = [i for i in store["issues"].values() if i["chapter_id"] == chapter.id and i["status"] in OPEN_STATUSES]
    status = "completed" if outcome["stop_reason"] == "ALL_RESOLVED" and not pending else ("pending_human" if pending else "human_handled")
    history = list((previous or {}).get("history", []))
    if previous:
        history.append({key: previous.get(key) for key in (
            "loop_no", "stop_reason", "stop_reason_label", "rounds", "rolled_back", "started_at", "started_by",
            "checked_revision", "result_revision", "kind", "meta")})
    loop = {"chapter_id": chapter.id, "loop_no": loop_no, "kind": kind, "status": status,
            "stop_reason": outcome["stop_reason"], "stop_reason_label": outcome["stop_reason_label"],
            "rounds": outcome["rounds"], "max_rounds": outcome["max_rounds"], "rolled_back": outcome["rolled_back"],
            "started_at": now_iso, "started_by": actor_id, "checked_revision": checked_revision,
            "result_revision": int(getattr(chapter, "revision", checked_revision) or checked_revision),
            "meta": dict(meta or {}), "history": history[-10:]}
    store["loops"][chapter.id] = loop
    return loop


def refresh_chapter_status(workflow: dict, chapter_id: str) -> str | None:
    store = queue_store(workflow)
    loop = store["loops"].get(chapter_id)
    if not loop:
        return None
    pending = [i for i in store["issues"].values() if i["chapter_id"] == chapter_id and i["status"] in OPEN_STATUSES]
    if pending:
        loop["status"] = "pending_human"
    elif loop["status"] == "pending_human":
        loop["status"] = "human_handled"
    return loop["status"]
