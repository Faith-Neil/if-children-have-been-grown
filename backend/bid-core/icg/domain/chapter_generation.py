# 为什么有这个文件：实现大纲写作计划输入组装（APP-M2-T124）与逐节确认启动章节生成（APP-M2-T126）。
# 它解决什么问题：
# 1. 写作方案输入上下文组装（APP-M2-T124）：将各章节得分要点小标题、已关联的公司证据版本（含 [证] 标记）、RAGFlow 候选切片（含 [片] 溯源）、项目可用事实及 SLA 变量组装为标准模型 Prompt 写作计划，包含字数预期、事实变量不可篡改约束及 [证] 引用标记规范；
# 2. 逐节确认启动生成（APP-M2-T126）：落地 start_chapter_generation(project_id, chapter_id, principal)，按逐节确认结果独立启动已确认章节的生成任务，未确认分册或未确认章节绝对不阻塞已确认章节的独立启动；未确认方案的章节企图启动生成前置抛出 400 PLAN_NOT_CONFIRMED；
# 3. 异步任务与进度流转：在 demo_job 中创建异步任务（job_type="generate_chapter", status="running", progress=0），并与 JobProgress 进度流转对接；
# 4. 敏感项目本地模型强门禁：敏感项目强制使用本地模型配置，企图使用云端模型抛出 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL。

from __future__ import annotations

import re
import time
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from .domain import Chapter, DemoState, DomainError, Principal, Project, iso_time, new_id
from .generation_context import (
    build_generation_context,
    chapter_plan,
    plan_is_current,
    project_facts,
    project_input_fingerprint,
    refuse_source_change,
    require_ready,
    validate_model_output,
    writing_source_fingerprint,
)
from .project_access import (
    READONLY_SYSTEM_ROLES,
    ROLE_NORMALIZATION_MAP,
    writable,
)
from .prompt_budget import (
    DEFAULT_MAX_CONTEXT_TOKENS,
    DynamicPromptContextManager,
    check_sensitive_model_gate,
)

VARIABLE_PATTERN = re.compile(r"\{\{([A-Za-z0-9_.:\u4e00-\u9fa5-]+)\}\}")
CITATION_PATTERN = re.compile(r"\[(证|片|cite)(?::([^\]]+))?\]")


def parse_scoring_points(writing_points: str | list[str] | None) -> list[str]:
    """解析章节写作计划中的评分要点清单。"""
    if not writing_points:
        return []
    items = writing_points if isinstance(writing_points, list) else str(writing_points).split("\n")
    points = []
    for item in items:
        line = str(item).strip()
        if not line:
            continue
        cleaned = re.sub(r"^[0-9]+[、.．\s-]+\s*", "", line).strip()
        if cleaned:
            points.append(cleaned)
    return points


def extract_paragraph_citations(
    text: str,
    allowed_evidence_ids: set[str] | None = None,
    allowed_snippet_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """提取段落内的 [证:xxx] 与 [片:xxx] 引用标记，并校验是否在有效依据范围内。"""
    citations = []
    for match in CITATION_PATTERN.finditer(text):
        tag_type = match.group(1)
        ref_id = (match.group(2) or "").strip()
        full_tag = match.group(0)
        cit_type = "evidence" if tag_type == "证" else ("snippet" if tag_type == "片" else "cite")

        is_valid = True
        if ref_id:
            if cit_type == "evidence" and allowed_evidence_ids is not None:
                is_valid = ref_id in allowed_evidence_ids
            elif cit_type == "snippet" and allowed_snippet_ids is not None:
                is_valid = ref_id in allowed_snippet_ids

        citations.append({
            "tag": full_tag,
            "type": cit_type,
            "id": ref_id,
            "valid": is_valid,
        })
    return citations


def parse_structured_paragraphs(
    raw_content: str,
    scoring_points: str | list[str] | None = None,
    allowed_evidence_ids: set[str] | None = None,
    allowed_snippet_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """将大模型生成的正文解析为带有 [P1]~[Pn] 编号、小标题与引用绑定的结构化段落列表。"""
    if not raw_content or not raw_content.strip():
        return []

    parsed_points = parse_scoring_points(scoring_points)
    lines = raw_content.strip().split("\n")

    paragraphs: list[dict[str, Any]] = []
    current_subheading: str | None = None
    current_title: str | None = None
    current_scoring_point: str | None = None
    accumulated_lines: list[str] = []

    def flush_paragraph():
        nonlocal accumulated_lines, current_subheading, current_title, current_scoring_point
        if not accumulated_lines:
            return
        p_text = " ".join(l.strip() for l in accumulated_lines if l.strip()).strip()
        accumulated_lines = []
        if not p_text:
            return

        order = len(paragraphs) + 1
        label = f"[P{order}]"

        m_label = re.match(r"^\[P(\d+)\]\s*(.*)", p_text, re.DOTALL)
        if m_label:
            clean_text = m_label.group(2).strip()
            label = f"[P{order}]"
        else:
            clean_text = p_text

        subhead = current_subheading
        title = current_title
        sc_point = current_scoring_point
        if not subhead and parsed_points:
            sp_idx = min(order - 1, len(parsed_points) - 1)
            sc_point = parsed_points[sp_idx]
            subhead = f"### 1.{sp_idx + 1} {sc_point}"
            title = sc_point

        citations = extract_paragraph_citations(clean_text, allowed_evidence_ids, allowed_snippet_ids)
        variables = [m.group(1) for m in VARIABLE_PATTERN.finditer(clean_text)]

        paragraphs.append({
            "id": f"p-{order}",
            "paragraph_id": f"p-{order}",
            "order": order,
            "label": label,
            "subheading": subhead,
            "title": title,
            "text": clean_text,
            "content": f"{label} {clean_text}",
            "citations": citations,
            "scoring_point": sc_point,
            "variables": variables,
            "char_length": len(clean_text),
        })

    heading_pattern = re.compile(r"^(#{1,6})\s*(.+)$")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            continue

        h_match = heading_pattern.match(stripped)
        if h_match:
            flush_paragraph()
            current_subheading = stripped
            raw_title = h_match.group(2).strip()
            current_title = re.sub(r"^[0-9]+[、.．\s-]+\s*", "", raw_title).strip()
            current_scoring_point = None
            if parsed_points:
                for sp in parsed_points:
                    if sp in current_title or current_title in sp:
                        current_scoring_point = sp
                        break
                if not current_scoring_point and parsed_points:
                    sp_idx = min(len(paragraphs), len(parsed_points) - 1)
                    current_scoring_point = parsed_points[sp_idx]
            continue

        if re.match(r"^\[P\d+\]", stripped):
            flush_paragraph()

        accumulated_lines.append(stripped)

    flush_paragraph()
    return paragraphs


def format_structured_chapter_content(paragraphs: list[dict[str, Any]]) -> str:
    """将结构化段落列表格式化为标准 Markdown 章节正文。"""
    if not paragraphs:
        return ""

    blocks = []
    emitted_subheadings = set()

    for p in paragraphs:
        subheading = p.get("subheading")
        if subheading and subheading not in emitted_subheadings:
            blocks.append(subheading)
            emitted_subheadings.add(subheading)

        blocks.append(p.get("content") or f"{p.get('label', '')} {p.get('text', '')}".strip())

    return "\n\n".join(blocks).strip()


# ---------------------------------------------------------------------------
# 章节生成产物合规性自动即时质检门禁（PRD MVP v1.8 §5.7.8 & §5.10 / AI-CHAPTER-AUTO-VALIDATION-GATE）
# ---------------------------------------------------------------------------

PLACEHOLDER_REGEXES = [
    re.compile(r"【待补(?:：[^】]*)?】"),
    re.compile(r"\[待补(?:：[^\]]*)?\]"),
    re.compile(r"待补"),
    re.compile(r"【待完善(?:：[^】]*)?】"),
    re.compile(r"\[待完善(?:：[^\]]*)?\]"),
    re.compile(r"待完善"),
    re.compile(r"【待确认(?:：[^】]*)?】"),
    re.compile(r"\[待确认(?:：[^\]]*)?\]"),
    re.compile(r"待确认"),
    re.compile(r"【占位(?:：[^】]*)?】"),
    re.compile(r"\[占位(?:：[^\]]*)?\]"),
    re.compile(r"占位符"),
    re.compile(r"【待定(?:：[^】]*)?】"),
    re.compile(r"\[待定(?:：[^\]]*)?\]"),
    re.compile(r"(?<![a-zA-Z0-9_])(?:TODO|TBD|FIXME|XXXX|XXX)(?![a-zA-Z0-9_])", re.IGNORECASE),
    re.compile(r"\{\{(?!(?:fact|sla):)[^}]+\}\}"),
    re.compile(r"\$\{(?!(?:fact|sla):)[^}]+\}"),
]

AI_CONVERSATION_RESIDUALS = [
    "希望对你有帮助",
    "希望能帮到您",
    "希望能帮助到您",
    "作为AI语言模型",
    "作为AI大模型",
    "作为人工智能模型",
    "作为大语言模型",
    "以下是为您生成的",
    "如需进一步修改",
    "希望以上方案能满足",
    "如果还有其他需要补充",
    "如有其他需求",
    "祝您投标顺利",
]

NEGATIVE_DEVIATION_TRIGGERS = [
    "不满足",
    "负偏离",
    "无法提供",
    "存在差距",
    "无法满足",
    "不符合要求",
    "未能达到",
    "偏离招标要求",
    "指标不满足",
    "存在负偏离",
    "重大负偏离",
    "实质性负偏离",
    "技术参数低于要求",
    "未能完全满足",
    "无法按期交付",
    "无法承诺",
]

STATUTORY_FORM_KEYWORDS = (
    "投标函",
    "法定代表人身份证明",
    "授权委托书",
    "签署页",
    "签字盖章页",
    "承诺书",
    "投标声明",
    "服务承诺书",
    "廉政承诺书",
    "安全承诺书",
    "保密承诺书",
)

VALID_SEAL_MARKERS = (
    "(盖章)", "（盖章）", "[公章]", "【公章】", "[盖章]", "(公章)", "（公章）",
    "(签字)", "（签字）", "[签名]", "[法定代表人签字]", "（法定代表人签字）", "(法定代表人签字)",
    "电子签名", "电子印章", "CA签章", "已盖章", "已签名", "法定代表人签字或盖章", "【法定代表人签字】", "【公章/签字】"
)

MISSING_SEAL_TRIGGERS = (
    "未盖公章", "未签字", "(未盖章)", "（未盖章）", "[未签名]", "(未签名)", "（未签名）",
    "待盖章", "待签字", "印章缺失", "签名缺失", "印章未齐", "无签字"
)


def validate_chapter_candidate(
    content: str,
    paragraphs: list[dict[str, Any]] | None = None,
    chapter: Any = None,
    allowed_evidence_ids: set[str] | None = None,
    allowed_snippet_ids: set[str] | None = None,
    workflow: dict[str, Any] | None = None,
    project: Any = None,
    strict_mode: bool = False,
) -> dict[str, Any]:
    """对大模型章节生成产物执行即时合规性与质量门禁核验（PRD MVP v1.8 §5.7.8 & §5.10）。

    核心核验项：
    1. R34 占位符与 AI 对话残留排查（【待定】、【待补】、TODO、XXXX 及客套语）；
    2. R37 / R28 负偏离与不满足排查（负偏离、无法提供、存在差距等实质性违规表述）；
    3. R24 签字盖章槽位合规排查（法定承诺与授权章节缺失签字盖章槽位或包含未盖公章标记）；
    4. CITATION_AUTH 证据引用真实性核验（排查虚构证据编号与未匹配知识库切片）。

    输出质量健康度评分（quality_health_score: 0~100）与评级（excellent / good / warning / critical）。
    """
    detected_blockers: list[dict[str, Any]] = []
    detected_warnings: list[dict[str, Any]] = []
    remediation_suggestions: list[str] = []

    text_to_check = content or ""
    ch_title = getattr(chapter, "title", "") if chapter else ""
    if isinstance(chapter, dict):
        ch_title = chapter.get("title", "")

    # 1. R34 占位符与“待补/待完善”残留排查
    matched_placeholders = set()
    for pattern in PLACEHOLDER_REGEXES:
        for m in pattern.finditer(text_to_check):
            matched_placeholders.add(m.group(0))

    if matched_placeholders:
        tokens_preview = "、".join(sorted(list(matched_placeholders))[:5])
        detected_blockers.append({
            "rule_id": "R34",
            "code": "PLACEHOLDER_RESIDUAL",
            "severity": "blocker",
            "message": f"正文包含未替换的占位符或待补标记：{tokens_preview}",
            "matched_tokens": sorted(list(matched_placeholders)),
        })

    # AI 对话客套残留语句排查
    matched_residuals = [dialogue for dialogue in AI_CONVERSATION_RESIDUALS if dialogue in text_to_check]
    if matched_residuals:
        res_preview = "、".join(matched_residuals[:3])
        detected_blockers.append({
            "rule_id": "R34",
            "code": "AI_CONVERSATION_RESIDUAL",
            "severity": "blocker",
            "message": f"正文检测到 AI 对话残留语句：{res_preview}",
            "matched_residuals": matched_residuals,
        })

    # 2. R37 / R28 负偏离与不满足排查
    matched_neg_devs = [trig for trig in NEGATIVE_DEVIATION_TRIGGERS if trig in text_to_check]
    if matched_neg_devs:
        dev_preview = "、".join(matched_neg_devs[:3])
        detected_blockers.append({
            "rule_id": "R37",
            "code": "NEGATIVE_DEVIATION_DETECTED",
            "severity": "blocker",
            "message": f"正文包含负偏离或无法满足声明：'{dev_preview}'，违反实质性响应要求",
            "matched_triggers": matched_neg_devs,
        })

    # 3. R24 签字盖章占位合规排查
    is_statutory_form = any(k in ch_title for k in STATUTORY_FORM_KEYWORDS)
    if is_statutory_form:
        # 排查显式“未盖公章”、“未签字”等瑕疵
        matched_missing_seals = [trig for trig in MISSING_SEAL_TRIGGERS if trig in text_to_check]
        if matched_missing_seals:
            detected_blockers.append({
                "rule_id": "R24",
                "code": "MANDATORY_SEAL_SIGNATURE_MISSING",
                "severity": "blocker",
                "message": f"法定承诺章节「{ch_title}」存在未盖章或未签字标记：{matched_missing_seals[0]}",
                "trigger": matched_missing_seals[0],
            })
        elif any(k in ch_title for k in ("投标函", "授权委托书", "签署页", "签字盖章页", "身份证明")):
            has_valid_seal = any(m in text_to_check for m in VALID_SEAL_MARKERS)
            if not has_valid_seal:
                detected_blockers.append({
                    "rule_id": "R24",
                    "code": "MANDATORY_SEAL_SIGNATURE_MISSING",
                    "severity": "blocker",
                    "message": f"法定关键表单章节「{ch_title}」缺少法定代表人签字或单位公章槽位标记",
                })

    # 4. CITATION_AUTH 证据引用真实性核验
    extracted_citations = extract_paragraph_citations(
        text_to_check,
        allowed_evidence_ids=allowed_evidence_ids,
        allowed_snippet_ids=allowed_snippet_ids,
    )
    fabricated_ev_ids = set()
    unverified_snip_ids = set()
    for cit in extracted_citations:
        if cit.get("type") == "evidence" and cit.get("id"):
            if not cit.get("valid", True):
                fabricated_ev_ids.add(cit["id"])
        elif cit.get("type") == "snippet" and cit.get("id"):
            if allowed_snippet_ids is not None and len(allowed_snippet_ids) > 0:
                if not cit.get("valid", True):
                    unverified_snip_ids.add(cit["id"])

    for eid in sorted(list(fabricated_ev_ids)):
        detected_blockers.append({
            "rule_id": "CITATION_AUTH",
            "code": "FABRICATED_OR_INVALID_EVIDENCE_CITATION",
            "severity": "blocker",
            "message": f"正文引用了未在项目依据白名单中登记的虚构或无效证据编号：[证:{eid}]",
            "evidence_id": eid,
        })

    for sid in sorted(list(unverified_snip_ids)):
        detected_warnings.append({
            "rule_id": "CITATION_AUTH",
            "code": "UNVERIFIED_SNIPPET_CITATION",
            "severity": "warning",
            "message": f"正文引用了未在当前候选切片库中的知识库切片：[片:{sid}]",
            "snippet_id": sid,
        })

    # 5. 质量健康度评分与评级计算
    blocker_count = len(detected_blockers)
    warning_count = len(detected_warnings)

    if blocker_count == 0:
        validation_passed = True
        validation_failed = False
        if warning_count == 0:
            quality_health_score = 100
            quality_health_rating = "excellent"
        elif warning_count == 1:
            quality_health_score = 90
            quality_health_rating = "excellent"
        elif warning_count == 2:
            quality_health_score = 80
            quality_health_rating = "good"
        elif warning_count == 3:
            quality_health_score = 70
            quality_health_rating = "warning"
        else:
            quality_health_score = max(50, 100 - warning_count * 10)
            quality_health_rating = "warning"
    else:
        validation_passed = False
        validation_failed = True
        if blocker_count == 1:
            quality_health_score = max(40, 55 - warning_count * 5)
            quality_health_rating = "warning" if quality_health_score >= 50 else "critical"
        else:
            quality_health_score = max(0, 35 - (blocker_count - 2) * 15 - warning_count * 5)
            quality_health_rating = "critical"

    # 6. 生成修复建议清单
    all_codes = {b.get("code") for b in detected_blockers} | {w.get("code") for w in detected_warnings}
    if "PLACEHOLDER_RESIDUAL" in all_codes or "AI_CONVERSATION_RESIDUAL" in all_codes:
        remediation_suggestions.append("请清除章节正文中的未替换占位符（如【待定】/TODO）与AI对话客套语，补充真实业务描述。")
    if "NEGATIVE_DEVIATION_DETECTED" in all_codes:
        remediation_suggestions.append("正文包含负偏离表述，请核实招标文件实质性指标要求并改写为完全满足。")
    if "MANDATORY_SEAL_SIGNATURE_MISSING" in all_codes:
        remediation_suggestions.append("法定表单章节必须包含公章与法定代表人签字槽位（如【盖章】、【法定代表人签字】），且不得包含未盖章标记。")
    if "FABRICATED_OR_INVALID_EVIDENCE_CITATION" in all_codes:
        remediation_suggestions.append("检测到虚构证据编号，请仅引用项目响应矩阵已关联并核对有效的真实资质/业绩编号。")
    if "UNVERIFIED_SNIPPET_CITATION" in all_codes:
        remediation_suggestions.append("建议核对知识库切片引用编号有效性，或重新匹配当前知识库候选切片。")

    if not remediation_suggestions:
        remediation_suggestions.append("章节生成产物合规性核验全部通过，质量良好。")

    validation_report = {
        "validation_passed": validation_passed,
        "validation_failed": validation_failed,
        "quality_health_score": quality_health_score,
        "quality_health_rating": quality_health_rating,
        "total_rules_evaluated": 4,
        "total_blockers": blocker_count,
        "total_warnings": warning_count,
        "detected_blockers": detected_blockers,
        "detected_warnings": detected_warnings,
        "remediation_suggestions": remediation_suggestions,
    }

    return {
        "validation_passed": validation_passed,
        "validation_failed": validation_failed,
        "quality_health_score": quality_health_score,
        "quality_health_rating": quality_health_rating,
        "detected_blockers": detected_blockers,
        "detected_warnings": detected_warnings,
        "remediation_suggestions": remediation_suggestions,
        "validation_report": validation_report,
    }


# ---------------------------------------------------------------------------
# 章节合规质检缺陷自动整改建议与局部智能重写引擎（PRD MVP v1.8 §5.7.8 & §5.10 / AI-OUTLINE-AUTO-REMEDIATION）
# ---------------------------------------------------------------------------

# 原“负偏离 → 完全满足”的确定性翻转表已删除（ISSUE-039）：偏离与承诺属于直接转人工的问题，
# 系统和模型都不能把“不满足”改写成“满足”（PRD v1.8 §5.7.4 第 4 条、§1.4 原则 3）。

SEAL_SIGNATURE_REPLACEMENTS = {
    "未盖公章": "【单位公章】",
    "未签字": "【法定代表人签字】",
    "(未盖章)": "【公章】",
    "（未盖章）": "【公章】",
    "[未签名]": "【法定代表人签字】",
    "(未签名)": "【法定代表人签字】",
    "（未签名）": "【法定代表人签字】",
    "待盖章": "【公章】",
    "待签字": "【法定代表人签字】",
    "印章缺失": "【公章】",
    "签名缺失": "【法定代表人签字】",
    "印章未齐": "【公章】",
    "无签字": "【法定代表人签字】",
}

STANDARD_STATUTORY_SEAL_BLOCK = """

法定代表人或授权代表签字：【法定代表人签字】
投标人名称（盖章）：【公章】
签署日期：2026年10月28日"""


def diagnose_paragraph_defects(
    p_text: str,
    chapter_title: str = "",
    allowed_evidence_ids: set[str] | None = None,
    allowed_snippet_ids: set[str] | None = None,
    is_statutory_form: bool = False,
) -> dict[str, Any]:
    """诊断单个段落文本中存在的合规缺陷与违规标记。"""
    matched_placeholders = set()
    for pattern in PLACEHOLDER_REGEXES:
        for m in pattern.finditer(p_text):
            matched_placeholders.add(m.group(0))

    matched_residuals = [dialogue for dialogue in AI_CONVERSATION_RESIDUALS if dialogue in p_text]
    matched_neg_devs = [trig for trig in NEGATIVE_DEVIATION_TRIGGERS if trig in p_text]

    matched_missing_seals = []
    if is_statutory_form:
        matched_missing_seals = [trig for trig in MISSING_SEAL_TRIGGERS if trig in p_text]

    extracted_citations = extract_paragraph_citations(
        p_text,
        allowed_evidence_ids=allowed_evidence_ids,
        allowed_snippet_ids=allowed_snippet_ids,
    )
    fabricated_ev_ids = []
    unverified_snip_ids = []
    for cit in extracted_citations:
        if cit.get("type") == "evidence" and cit.get("id"):
            if not cit.get("valid", True):
                fabricated_ev_ids.append(cit["id"])
        elif cit.get("type") == "snippet" and cit.get("id"):
            if allowed_snippet_ids is not None and len(allowed_snippet_ids) > 0:
                if not cit.get("valid", True):
                    unverified_snip_ids.append(cit["id"])

    has_blockers = bool(
        matched_placeholders
        or matched_residuals
        or matched_neg_devs
        or matched_missing_seals
        or fabricated_ev_ids
    )
    has_warnings = bool(unverified_snip_ids)

    return {
        "placeholders": sorted(list(matched_placeholders)),
        "ai_residuals": matched_residuals,
        "negative_deviations": matched_neg_devs,
        "missing_seals": matched_missing_seals,
        "fabricated_ev_ids": sorted(list(set(fabricated_ev_ids))),
        "unverified_snip_ids": sorted(list(set(unverified_snip_ids))),
        "has_blockers": has_blockers,
        "has_warnings": has_warnings,
    }


def sanitize_and_remediate_paragraph_text(
    p_text: str,
    defects: dict[str, Any],
    chapter_title: str = "",
    allowed_evidence_ids: set[str] | None = None,
    allowed_snippet_ids: set[str] | None = None,
    facts: list[dict[str, Any]] | None = None,
) -> str:
    """对单个违规段落执行不编造的确定性清洗（PRD v1.8 §1.4 原则 3、§5.7.4 第 4/5 条）。

    只做：删除对话残留、签章瑕疵换成签章槽位、用已确认事实变量替换【待补】、移除失效知识片段标记、
    把本章依据外的证据编号换成【待补：依据】。负偏离、无依据的【待补】和承诺数值属于直接转人工的问题，
    这里保持原文不动，由人工处理队列处理。
    """
    cleaned = p_text

    # 1. 清理 AI 对话残留客套语
    for res in defects.get("ai_residuals", []):
        cleaned = cleaned.replace(res, "")
    for res in AI_CONVERSATION_RESIDUALS:
        if res in cleaned:
            cleaned = cleaned.replace(res, "")

    # 2. 负偏离属于商务偏离/承诺类问题，直接转人工，系统不改写为正向承诺。

    # 3. 签字盖章瑕疵标记替换
    for miss, valid in SEAL_SIGNATURE_REPLACEMENTS.items():
        if miss in cleaned:
            cleaned = cleaned.replace(miss, valid)

    # 4. 依据外的证据编号不能换成别的证据（那等于给事实挂上不相干的依据），只能改为【待补：依据】；
    #    失效的知识片段标记只是参考来源，直接移除。
    all_cits = extract_paragraph_citations(
        cleaned,
        allowed_evidence_ids=allowed_evidence_ids,
        allowed_snippet_ids=allowed_snippet_ids,
    )
    for cit in all_cits:
        if cit.get("type") == "evidence" and cit.get("id"):
            if not cit.get("valid", True):
                cleaned = cleaned.replace(f"[证:{cit['id']}]", "【待补：依据】")
        elif cit.get("type") == "snippet" and cit.get("id"):
            if allowed_snippet_ids is not None and len(allowed_snippet_ids) > 0:
                if not cit.get("valid", True):
                    cleaned = cleaned.replace(f"[片:{cit['id']}]", "")

    # 5. 【待补】只在有已确认项目事实时替换为事实变量；没有依据时保留原标记，不写空泛承诺。
    fact_map = {}
    if facts:
        for f in facts:
            if f.get("status") not in (None, "confirmed"):
                continue
            key = f.get("key", "")
            var = f.get("variable", "")
            val = f.get("value", "")
            if key:
                fact_map[key] = var or val

    for token in defects.get("placeholders", []):
        inner = token.strip("【】[]").split("：", 1)[-1].split(":", 1)[-1].strip()
        if not inner or inner in ("待补", "待完善", "待确认", "待定", "占位", "占位符"):
            continue
        for k, v in fact_map.items():
            if v and (k == inner or k in inner or inner in k):
                cleaned = cleaned.replace(token, str(v))
                break

    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n\s*\n\s*\n+", "\n\n", cleaned)
    return cleaned.strip()


def synthesize_remediation_plan(
    content: str,
    paragraphs: list[dict[str, Any]] | None = None,
    chapter: Any = None,
    allowed_evidence_ids: set[str] | None = None,
    allowed_snippet_ids: set[str] | None = None,
    facts: list[dict[str, Any]] | None = None,
    detected_blockers: list[dict[str, Any]] | None = None,
    detected_warnings: list[dict[str, Any]] | None = None,
    project: Any = None,
) -> dict[str, Any]:
    """自动诊断违规段落并针对性合成合规整改计划与重写 Prompt（PRD MVP v1.8 §5.7.8 & §5.10）。"""
    ch_title = getattr(chapter, "title", "") if chapter else ""
    if isinstance(chapter, dict):
        ch_title = chapter.get("title", "")

    is_statutory = any(k in ch_title for k in STATUTORY_FORM_KEYWORDS)

    if not paragraphs:
        paragraphs = parse_structured_paragraphs(
            content,
            allowed_evidence_ids=allowed_evidence_ids,
            allowed_snippet_ids=allowed_snippet_ids,
        )
    if not paragraphs and content:
        paragraphs = [{"index": 0, "label": "[P1]", "content": content, "text": content}]

    target_paragraphs = []
    total_defect_count = 0
    valid_ev_list = sorted(list(allowed_evidence_ids)) if allowed_evidence_ids else []
    ev_whitelist_str = "、".join([f"[证:{eid}]" for eid in valid_ev_list[:5]]) or "项目当前无额外已确认资质，严禁虚构"

    for idx, p in enumerate(paragraphs):
        p_text = p.get("content") or p.get("text") or ""
        diag = diagnose_paragraph_defects(
            p_text=p_text,
            chapter_title=ch_title,
            allowed_evidence_ids=allowed_evidence_ids,
            allowed_snippet_ids=allowed_snippet_ids,
            is_statutory_form=is_statutory,
        )

        if not diag["has_blockers"] and not diag["has_warnings"]:
            continue

        instructions = []
        defect_items = []

        if diag["placeholders"]:
            p_list_str = "、".join(diag["placeholders"])
            instructions.append(f"占位符（{p_list_str}）有已确认项目事实时替换为事实变量；没有依据时保留【待补】并转人工补资料，不得改写为空泛承诺。")
            defect_items.append({
                "rule_id": "R34",
                "code": "PLACEHOLDER_RESIDUAL",
                "severity": "blocker",
                "matched_tokens": diag["placeholders"],
                "instruction": "消除待定/待补占位符并补充完整业务承诺",
            })
            total_defect_count += len(diag["placeholders"])

        if diag["ai_residuals"]:
            r_list_str = "、".join(diag["ai_residuals"])
            instructions.append(f"删除 AI 对话客套残留语句（{r_list_str}），保持严谨规范的公文投标语态。")
            defect_items.append({
                "rule_id": "R34",
                "code": "AI_CONVERSATION_RESIDUAL",
                "severity": "blocker",
                "matched_residuals": diag["ai_residuals"],
                "instruction": "删除对话式客套语",
            })
            total_defect_count += len(diag["ai_residuals"])

        if diag["negative_deviations"]:
            n_list_str = "、".join(diag["negative_deviations"])
            instructions.append(f"偏离表述（{n_list_str}）属于商务偏离/承诺类问题，转人工核实：属实则在偏离表登记理由，能满足则由负责人补充依据后改写，模型不得自行改为满足。")
            defect_items.append({
                "rule_id": "R37",
                "code": "NEGATIVE_DEVIATION_DETECTED",
                "severity": "blocker",
                "matched_triggers": diag["negative_deviations"],
                "instruction": "转人工核实偏离，不自动改写承诺",
                "route": "direct_human",
            })
            total_defect_count += len(diag["negative_deviations"])

        if diag["missing_seals"]:
            m_list_str = "、".join(diag["missing_seals"])
            instructions.append(f"修复印章与签名缺失标记（{m_list_str}），替换为标准的【法定代表人签字】与【单位公章】槽位。")
            defect_items.append({
                "rule_id": "R24",
                "code": "MANDATORY_SEAL_SIGNATURE_MISSING",
                "severity": "blocker",
                "matched_triggers": diag["missing_seals"],
                "instruction": "修复签字盖章槽位",
            })
            total_defect_count += len(diag["missing_seals"])

        if diag["fabricated_ev_ids"]:
            f_list_str = "、".join([f"[证:{eid}]" for eid in diag["fabricated_ev_ids"]])
            instructions.append(f"证据编号 {f_list_str} 不在本章依据中，改为【待补：依据】并转人工补挂真实证据，不得换成其他证据编号。")
            defect_items.append({
                "rule_id": "CITATION_AUTH",
                "code": "FABRICATED_OR_INVALID_EVIDENCE_CITATION",
                "severity": "blocker",
                "evidence_ids": diag["fabricated_ev_ids"],
                "instruction": "改为【待补：依据】并转人工补挂证据",
                "route": "direct_human",
            })
            total_defect_count += len(diag["fabricated_ev_ids"])

        if diag["unverified_snip_ids"]:
            s_list_str = "、".join([f"[片:{sid}]" for sid in diag["unverified_snip_ids"]])
            instructions.append(f"核对知识库切片编号 {s_list_str}，建议仅引用有效匹配的候选知识切片。")
            defect_items.append({
                "rule_id": "CITATION_AUTH",
                "code": "UNVERIFIED_SNIPPET_CITATION",
                "severity": "warning",
                "snippet_ids": diag["unverified_snip_ids"],
                "instruction": "核准知识库切片编号",
            })
            total_defect_count += len(diag["unverified_snip_ids"])

        label = p.get("label") or f"[P{idx + 1}]"
        rem_prompt = (
            f"你是一位严谨的投标编写合规专家。请针对投标章节「{ch_title}」中段落 {label} 的合规缺陷执行局部精准重写：\n"
            f"【原段落内容】\n{p_text}\n\n"
            f"【合规整改要求】\n" + "\n".join(f"- {inst}" for inst in instructions) + "\n\n"
            f"【合法依据白名单】\n{ev_whitelist_str}\n\n"
            f"【重写指令】\n"
            f"1. 仅输出重写后的段落正文，严禁包含任何前缀、解释、客套语或分析说明；\n"
            f"2. 不得新增或改动任何数字、金额、时限、人员和证据编号；\n"
            f"3. 没有依据的事实保留或写成【待补：缺少什么】，不得改写为“已满足”“已具备”等空泛承诺；\n"
            f"4. 偏离与不满足表述原样保留，由人工核实。"
        )

        replacement = sanitize_and_remediate_paragraph_text(
            p_text=p_text,
            defects=diag,
            chapter_title=ch_title,
            allowed_evidence_ids=allowed_evidence_ids,
            allowed_snippet_ids=allowed_snippet_ids,
            facts=facts,
        )

        target_paragraphs.append({
            "paragraph_index": idx,
            "label": label,
            "original_text": p_text,
            "defects": defect_items,
            "diagnostics": diag,
            "remediation_instructions": instructions,
            "remediation_prompt": rem_prompt,
            "suggested_replacement_text": replacement,
        })

    has_seal_defect = detected_blockers and any(b.get("code") == "MANDATORY_SEAL_SIGNATURE_MISSING" for b in detected_blockers)
    if is_statutory and has_seal_defect:
        seal_handled = any(
            any(d.get("code") == "MANDATORY_SEAL_SIGNATURE_MISSING" for d in tp["defects"])
            for tp in target_paragraphs
        )
        if not seal_handled and paragraphs:
            last_idx = len(paragraphs) - 1
            last_p = paragraphs[last_idx]
            last_text = last_p.get("content") or last_p.get("text") or ""
            existing_tp = next((tp for tp in target_paragraphs if tp["paragraph_index"] == last_idx), None)
            seal_instr = "在法定表单结尾补充法定代表人签字与单位公章落款槽位。"
            if existing_tp:
                existing_tp["remediation_instructions"].append(seal_instr)
                existing_tp["suggested_replacement_text"] += STANDARD_STATUTORY_SEAL_BLOCK
            else:
                target_paragraphs.append({
                    "paragraph_index": last_idx,
                    "label": last_p.get("label") or f"[P{last_idx + 1}]",
                    "original_text": last_text,
                    "defects": [{
                        "rule_id": "R24",
                        "code": "MANDATORY_SEAL_SIGNATURE_MISSING",
                        "severity": "blocker",
                        "instruction": seal_instr,
                    }],
                    "diagnostics": {"has_blockers": True, "has_warnings": False},
                    "remediation_instructions": [seal_instr],
                    "remediation_prompt": f"请为法定章节「{ch_title}」段落结尾补充法定代表人签字及公章落款：\n{last_text}\n" + STANDARD_STATUTORY_SEAL_BLOCK,
                    "suggested_replacement_text": last_text + STANDARD_STATUTORY_SEAL_BLOCK,
                })
            total_defect_count += 1

    overall_prompt = (
        f"【投标章节合规整改指导计划 · {ch_title}】\n"
        f"总计检测到违规段落 {len(target_paragraphs)} 处，违规项 {total_defect_count} 个。\n"
        f"请严格按各段落局部整改要求执行重写，确保 100% 消除废标阻断项。"
    )

    return {
        "has_defects": len(target_paragraphs) > 0,
        "defect_count": total_defect_count,
        "total_paragraphs": len(paragraphs),
        "remediable_paragraphs_count": len(target_paragraphs),
        "target_paragraphs": target_paragraphs,
        "overall_remediation_prompt": overall_prompt,
    }


def format_writing_plan_prompt(snapshot: dict) -> str:
    """将写作方案快照渲染为大模型 Prompt 写作计划文本（APP-M2-T124）。"""
    chapter = snapshot["chapter"]
    plan = snapshot["plan"]
    project = snapshot["project"]

    lines = [
        "【章节与分册目标】",
        f"章节：{chapter['title']}（分册：{chapter['volume']}）",
        f"项目：{project['name']}",
        "提示：本生成内容为待人工核对的草稿候选，不会自动成为正式承诺。",
        "",
        "【得分要点小标题与写作计划】",
        f"{plan.get('writing_points') or '未指定小标题与写作要点'}",
        "",
        "【字数预期】",
        f"目标字数：{plan.get('target_length') or '未限制'} 字（供人工审核参考）",
        "",
        "【事实约束规范】",
        "1. 正文引用事实必须保留变量标记（如 {{fact:xxx}} 或 {{sla:xxx}}），严禁修改取值或将变量替换为手写文字；",
        "2. 严禁私自修改事实来源取值，若有差异需在响应矩阵中修正；",
        "",
        "【证据引用规范】",
        "1. 必须使用 [证] 或 [证:编号] 标记引用已核对的公司资质、证书或业绩，严禁捏造未核对的公司证明；",
        "2. [片] 检索切片仅供写作方案参考，不得作为正式附着证据；",
        "",
    ]

    # 招标文件条款
    reqs = snapshot.get("requirements", [])
    if reqs:
        lines.append("【招标文件条款与响应要求】")
        for req in reqs:
            lines.append(f"• 条款：{req['text']}")
            lines.append(f"  响应：{req['response'].strip() or '【待补】请填写经核对的响应'}")
            if any(w in req["text"] for w in ("资质", "证书", "证明", "业绩", "授权")) and not req.get("evidence_ids"):
                lines.append("  注意：本条款缺少已核对证据，不得编造证明材料。")
        lines.append("")

    # 公司资质与已关联证据
    evs = snapshot.get("evidence", [])
    if evs:
        lines.append("【已关联公司证据清单】")
        for ev in evs:
            tag = ev.get("tag", "[证]")
            lines.append(
                f"{tag} 已确认可引用证据：{ev['name']}（标识 {ev['id']}，记录版本 {ev.get('revision', 1)}，有效期至 {ev.get('valid_until') or '未登记'}）"
            )
            if ev.get("content"):
                lines.append(f"  证据内容摘要：{ev['content']}")
        lines.append("")

    # RAGFlow 检索证据切片
    retrieved = snapshot.get("retrieved_evidence", [])
    if retrieved:
        lines.append("【RAGFlow 检索证据候选切片】")
        for chunk in retrieved:
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
            lines.append(f"{chunk.get('cite_tag') or tag} 检索切片{prov}{ref_notice}：")
            lines.append(f"  {chunk.get('content', '')}")
        lines.append("")

    # 项目事实与 SLA 变量
    facts = snapshot.get("facts", [])
    if facts:
        lines.append("【已确认项目事实与变量清单】")
        for fact in facts:
            val = fact["value"] + (" " + fact["unit"] if fact.get("unit") else "")
            src = fact.get("source")
            src_str = (
                f"来源：{src.get('filename', src.get('file_id'))} 第{src.get('page')}页"
                if src
                else "来源：已确认项目事实"
            )
            lines.append(f"• {fact['key']}：变量 {fact['variable']}；核对取值：{val}；{src_str}")
        lines.append("")

    if snapshot.get("official_content", "").strip():
        lines.append("【当前已提交正文（所有事实变量必须保留）】")
        lines.append(snapshot["official_content"])
        lines.append("")

    return "\n".join(lines)


def assemble_writing_prompt_plan(
    state: DemoState,
    project_id: str,
    chapter_id: str,
    evidence_service: Any | None = None,
    now: float | None = None,
    max_context_tokens: int | None = None,
    snippet_matches: list[dict] | None = None,
) -> dict:
    """组装各章节得分要点小标题、已关联公司证据版本、RAGFlow候选切片及项目事实要点为模型Prompt写作计划（APP-M2-T124 / AI-DYNAMIC-PROMPT-CONTEXT）。"""
    project = state.projects.get(project_id)
    if project is None:
        raise DomainError(404, "NOT_FOUND", "未找到项目。")
    chapter = state.chapters.get(chapter_id)
    if chapter is None or chapter.project_id != project_id:
        raise DomainError(404, "NOT_FOUND", "未找到章节。")

    # 涉密项目本地模型强门禁拦截
    check_sensitive_model_gate(state, project_id)

    # 动态上下文 Token 预算与最大窗口解析
    effective_max_tokens = max_context_tokens
    if effective_max_tokens is None:
        bound_id = state.project_model_configs.get(project_id)
        cfg = state.model_configs.get(bound_id) if bound_id else state.model_configs.get(f"default-{project.company_id}")
        if cfg:
            effective_max_tokens = getattr(cfg, "context_window", None) or getattr(cfg, "max_context_tokens", None)
        if effective_max_tokens is None:
            effective_max_tokens = DEFAULT_MAX_CONTEXT_TOKENS

    current_time = now if now is not None else time.time()
    service = evidence_service if evidence_service is not None else getattr(state, "evidence_service", None)
    assembled = build_generation_context(state, project_id, chapter, current_time, evidence_service=service)
    snapshot = assembled["input_snapshot"]
    plan = snapshot.get("plan", {})

    # 自适应 Prompt 动态上下文裁剪与 Token 预算控制
    manager = DynamicPromptContextManager(max_context_tokens=effective_max_tokens)
    budget_result = manager.assemble_budgeted_prompt(snapshot, snippet_matches=snippet_matches)

    return {
        "project_id": project_id,
        "chapter_id": chapter_id,
        "title": chapter.title,
        "volume": chapter.volume,
        "prompt": budget_result["prompt"],
        "token_budget_usage": budget_result["token_budget_usage"],
        "context_fingerprint": budget_result["context_fingerprint"],
        "missing_variables": budget_result["missing_variables"],
        "has_missing_variables": budget_result["has_missing_variables"],
        "truncated_items_count": budget_result["truncated_items_count"],
        "truncated_items": budget_result["truncated_items"],
        "retained_counts": budget_result["retained_counts"],
        "writing_points": plan.get("writing_points", ""),
        "target_length": plan.get("target_length"),
        "fact_constraints": "正文引用事实必须保留变量标记（如 {{fact:xxx}} 或 {{sla:xxx}}），严禁修改事实取值或手写替换。",
        "citation_rules": "[证] 证据引用必须注明来源编号，严禁编造未核对的公司资质或业绩证明；[片] 检索切片仅供参考，不得作为正式附着证据。",
        "evidence": snapshot.get("evidence", []),
        "retrieved_evidence": snapshot.get("retrieved_evidence", []),
        "facts": snapshot.get("facts", []),
        "requirements": snapshot.get("requirements", []),
        "input_snapshot": snapshot,
    }


def _config_value(config: Any, key: str) -> Any:
    if config is None:
        return None
    return config.get(key) if isinstance(config, dict) else getattr(config, key, None)


def generation_loop_meta(state: Any, project_id: str, candidate: dict) -> dict:
    """生成后循环的轮次依据：模型、配置、任务、实际输入规模与前章摘要接力。"""
    snapshot = candidate.get("input_snapshot") or {}
    bound = state.project_model_configs.get(project_id) if hasattr(state, "project_model_configs") else None
    project = state.projects.get(project_id)
    config_id = bound or (f"default-{project.company_id}" if project is not None else None)
    config = state.model_configs.get(config_id) if config_id and hasattr(state, "model_configs") else None
    usage = candidate.get("token_budget_usage") or {}
    if hasattr(usage, "__dict__") and not isinstance(usage, dict):
        usage = vars(usage)
    return {
        "task": "generate_chapter", "task_label": "章节生成",
        "model": candidate.get("provider"), "is_real_model": bool(candidate.get("is_real_model")),
        "model_config_id": config_id if config is not None else None,
        "model_name": _config_value(config, "model_name") or _config_value(config, "model"),
        "fixer": "模型修正（未通过安全核对时退回规则修正）",
        "base_revision": candidate.get("base_revision"),
        "context_fingerprint": candidate.get("context_fingerprint"),
        "inputs": {"requirements": len(snapshot.get("requirements") or []),
                   "evidence": len(snapshot.get("evidence") or []),
                   "snippets": len(snapshot.get("retrieved_evidence") or []),
                   "facts": len(snapshot.get("facts") or []),
                   "omitted": len(snapshot.get("omitted_inputs") or []),
                   "truncated": int(usage.get("truncated_items_count") or 0) if isinstance(usage, dict) else 0},
        "summary_relay": snapshot.get("previous_chapter") or {"status": "not_recorded", "message": "生成时未记录前章摘要。"},
    }


class ChapterGenerationService:
    """章节写作计划组装与按逐节确认结果启动生成服务（APP-M2-T124 / T126 / AI-DYNAMIC-PROMPT-CONTEXT）。"""

    def __init__(self, demo: Any, repository: Any | None = None, evidence_service: Any | None = None):
        self.demo = demo
        self.repository = repository or getattr(demo, "repository", None)
        self.evidence_service = evidence_service or getattr(demo, "evidence_service", None)

    def assemble_writing_prompt_plan(
        self,
        project_id: str,
        chapter_id: str,
        principal: Principal | None = None,
        state: DemoState | None = None,
        max_context_tokens: int | None = None,
        snippet_matches: list[dict] | None = None,
    ) -> dict:
        """组装章节写作方案 Prompt 输入（APP-M2-T124 / AI-DYNAMIC-PROMPT-CONTEXT）。"""
        st = state if state is not None else self.repository.read()
        if principal is not None:
            self._check_access(st, project_id, chapter_id, principal)
        return assemble_writing_prompt_plan(
            st,
            project_id,
            chapter_id,
            evidence_service=self.evidence_service,
            now=self.demo._now() if hasattr(self.demo, "_now") else time.time(),
            max_context_tokens=max_context_tokens,
            snippet_matches=snippet_matches,
        )

    def start_chapter_generation(
        self,
        project_id: str,
        chapter_id: str,
        principal: Principal,
        sync_execute: bool = False,
        max_context_tokens: int | None = None,
        snippet_matches: list[dict] | None = None,
        auto_remediate: bool = False,
    ) -> dict:
        """按逐节确认结果独立启动已确认章节的生成任务（APP-M2-T126 / AI-OUTLINE-GENERATE-EXPAND）。"""
        state = self.repository.read()

        # 门禁 1：角色与操作权限核验（只读角色拦截）
        self._check_access(state, project_id, chapter_id, principal)

        project = state.projects[project_id]
        chapter = state.chapters[chapter_id]

        # 门禁 2：逐节确认门禁
        # 核心约束：按逐节确认结果独立启动已确认章节，未确认分册或未确认章节绝对不阻塞已确认章节的独立启动
        workflow = state.workflows.get(project_id, {})
        saved_plan = workflow.get("writing_plan", {}).get("chapters", {}).get(chapter_id, {})
        if not saved_plan.get("confirmed_at") or not plan_is_current(state, project_id, chapter_id):
            raise DomainError(409, "PLAN_NOT_CONFIRMED", "本章写作方案尚未确认或方案已过期，不能启动生成。")

        # 门禁 3：敏感项目本地模型隔离门禁
        self._check_model_gate(state, project)

        # 组装 Prompt 写作计划（APP-M2-T124 / AI-DYNAMIC-PROMPT-CONTEXT）
        prompt_plan = self.assemble_writing_prompt_plan(
            project_id,
            chapter_id,
            principal,
            state=state,
            max_context_tokens=max_context_tokens,
            snippet_matches=snippet_matches,
        )
        input_snapshot = prompt_plan["input_snapshot"]
        prompt = prompt_plan["prompt"]
        token_budget_usage = prompt_plan.get("token_budget_usage")
        context_fingerprint = prompt_plan.get("context_fingerprint")

        # 在 demo_job 中创建异步任务（job_type="generate_chapter", status="running", progress=0）
        now_time = self.demo._now() if hasattr(self.demo, "_now") else time.time()
        now_iso = iso_time(now_time)
        job_id = new_id("job")

        job_data = {
            "id": job_id,
            "job_type": "generate_chapter",
            "type": "generate_chapter",
            "project_id": project_id,
            "chapter_id": chapter_id,
            "status": "running",
            "progress": 0,
            "step_name": "准备生成提示词",
            "created_by": principal.user.id,
            "created_at": now_iso,
            "updated_at": now_iso,
            "error_json": None,
            "result_json": None,
            "token_budget_usage": token_budget_usage,
            "context_fingerprint": context_fingerprint,
        }

        # 持久化或存入仓储与状态机
        self.repository.save_job(job_data)

        def sync_job_to_state(st: DemoState):
            st.jobs[job_id] = deepcopy(job_data)
            st.recoverable_jobs[job_id] = {
                "id": job_id,
                "project_id": project_id,
                "type": "generate_chapter",
                "status": "running",
                "progress": 0,
                "message": "已启动章节生成任务。",
                "created_at": now_iso,
                "completed_at": None,
                "error": None,
                "events": [],
                "recoverable": True,
                "chapter_ids": [chapter_id],
            }

        self.repository.transaction(sync_job_to_state)

        # 推进中间步骤进度流转，与 JobProgress 对接
        self.repository.update_job_progress(
            job_id,
            progress=25,
            status="running",
            step_name="组装上下文提示词完成",
        )

        candidate = None
        # 如果需要同步执行或存在模型推理
        if sync_execute:
            self.repository.update_job_progress(
                job_id,
                progress=60,
                status="running",
                step_name="调用模型推理中",
            )
            provider = self.demo.resolve_model_provider(state, project_id)
            instruction = "按本章已确认条款、响应、证据和事实组织候选；不能编造证据与承诺。引用事实保留变量，不能改取值。"
            refuse_source_change(prompt_plan["writing_points"], input_snapshot)
            try:
                content = provider.suggest(instruction, prompt)
            except DomainError:
                self.repository.update_job_progress(
                    job_id,
                    progress=60,
                    status="failed",
                    step_name="模型调用失败",
                    error_json={"code": "MODEL_FAILED"},
                )
                raise
            except Exception as error:
                self.repository.update_job_progress(
                    job_id,
                    progress=60,
                    status="failed",
                    step_name="模型调用异常",
                    error_json={"code": "MODEL_UNAVAILABLE", "message": str(error)},
                )
                raise DomainError(502, "MODEL_UNAVAILABLE", "候选生成失败，正式正文没有修改。") from error

            validate_model_output(state, project_id, content, input_snapshot)

            # 解析结构化多段落与评分小标题
            scoring_points = prompt_plan.get("writing_points", "")
            allowed_evidence_ids = {e.get("id") for e in prompt_plan.get("evidence", []) if e.get("id")}
            reqs = [r for r in workflow.get("requirements", {}).values() if r.get("chapter_id") == chapter_id]
            for r in reqs:
                for eid in r.get("evidence_ids", []):
                    if eid:
                        allowed_evidence_ids.add(eid)
            allowed_snippet_ids = {s.get("snippet_id") or s.get("id") for s in (snippet_matches or []) if s.get("snippet_id") or s.get("id")}

            paragraphs = parse_structured_paragraphs(
                content,
                scoring_points=scoring_points,
                allowed_evidence_ids=allowed_evidence_ids,
                allowed_snippet_ids=allowed_snippet_ids,
            )
            structured_content = format_structured_chapter_content(paragraphs)
            seen_subheads = set()
            scoring_subheadings = []
            for p in paragraphs:
                sh = p.get("title") or p.get("subheading")
                if sh and sh not in seen_subheads:
                    seen_subheads.add(sh)
                    scoring_subheadings.append(sh)

            validation_res = validate_chapter_candidate(
                content=content,
                paragraphs=paragraphs,
                chapter=chapter,
                allowed_evidence_ids=allowed_evidence_ids,
                allowed_snippet_ids=allowed_snippet_ids,
                workflow=workflow,
                project=project,
            )

            cand_id = new_id("candidate")
            candidate = {
                "id": cand_id,
                "content": content,
                "structured_content": structured_content,
                "paragraphs": paragraphs,
                "scoring_subheadings": scoring_subheadings,
                "base_revision": chapter.revision,
                "input_fingerprint": project_input_fingerprint(state, project_id),
                "context_fingerprint": context_fingerprint,
                "token_budget_usage": token_budget_usage,
                "provider": getattr(provider, "name", "model"),
                "is_real_model": bool(getattr(provider, "is_real_model", False)),
                "created_at": now_iso,
                "source_scope": "whole_chapter",
                "input_snapshot": input_snapshot,
                "validation_passed": validation_res["validation_passed"],
                "validation_failed": validation_res["validation_failed"],
                "quality_health_score": validation_res["quality_health_score"],
                "quality_health_rating": validation_res["quality_health_rating"],
                "detected_blockers": validation_res["detected_blockers"],
                "detected_warnings": validation_res["detected_warnings"],
                "remediation_suggestions": validation_res["remediation_suggestions"],
                "validation_report": validation_res["validation_report"],
            }

            rem_res: dict[str, Any] | None = None
            if auto_remediate and validation_res.get("validation_failed"):
                rem_res = self.remediate_chapter_candidate(
                    project_id=project_id,
                    chapter_id=chapter_id,
                    principal=principal,
                    candidate=candidate,
                    auto_save=False,
                    provider=provider,
                )
                candidate = rem_res["candidate"]
                validation_res = candidate.get("validation_report", validation_res)
                paragraphs = candidate.get("paragraphs", paragraphs)
                structured_content = candidate.get("structured_content", structured_content)
                content = candidate.get("content", content)

            def save_candidate_op(st: DemoState):
                wf = st.workflows.setdefault(project_id, {})
                wf.setdefault("candidates", {})[chapter_id] = candidate
                if rem_res is not None and rem_res.get("loop_outcome"):
                    from .chapter_loop import record_loop

                    order = wf.get("chapter_order") or [c.id for c in st.chapters.values() if c.project_id == project_id]
                    live_chapter = st.chapters.get(chapter_id)
                    if live_chapter is not None:
                        record_loop(
                            wf, live_chapter, order.index(chapter_id) + 1 if chapter_id in order else 1,
                            rem_res["loop_outcome"], actor_id=principal.user.id,
                            now_iso=iso_time(self.demo._now()) if hasattr(self.demo, "_now") else iso_time(time.time()),
                            checked_revision=int(live_chapter.revision or 0), kind="generation_candidate",
                            meta=generation_loop_meta(st, project_id, candidate),
                        )

            self.repository.transaction(save_candidate_op)

            self.repository.update_job_progress(
                job_id,
                progress=100,
                status="completed",
                step_name="章节生成完成",
                result_json={
                    "candidate_id": cand_id,
                    "chapter_id": chapter_id,
                    "token_budget_usage": token_budget_usage,
                    "context_fingerprint": context_fingerprint,
                    "paragraph_count": len(paragraphs),
                    "validation_passed": validation_res["validation_passed"],
                    "quality_health_score": validation_res["quality_health_score"],
                    "quality_health_rating": validation_res["quality_health_rating"],
                    "blocker_count": len(validation_res["detected_blockers"]),
                    "remediation_applied": candidate.get("remediation_applied", False),
                    "remediated_paragraphs_count": candidate.get("remediated_paragraphs_count", 0),
                },
            )

        final_job = self.repository.read_job(job_id) or job_data
        if token_budget_usage and "token_budget_usage" not in final_job:
            final_job["token_budget_usage"] = token_budget_usage
        if context_fingerprint and "context_fingerprint" not in final_job:
            final_job["context_fingerprint"] = context_fingerprint

        return {
            "job_id": job_id,
            "job": final_job,
            "project_id": project_id,
            "chapter_id": chapter_id,
            "status": final_job.get("status", "running"),
            "progress": final_job.get("progress", 0),
            "step_name": final_job.get("step_name"),
            "prompt_plan": prompt_plan,
            "candidate": candidate,
            "token_budget_usage": token_budget_usage,
            "context_fingerprint": context_fingerprint,
            "paragraphs": candidate.get("paragraphs") if candidate else [],
            "structured_content": candidate.get("structured_content") if candidate else None,
            "scoring_subheadings": candidate.get("scoring_subheadings") if candidate else [],
            "validation_passed": candidate.get("validation_passed", True) if candidate else True,
            "validation_failed": candidate.get("validation_failed", False) if candidate else False,
            "quality_health_score": candidate.get("quality_health_score", 100) if candidate else 100,
            "quality_health_rating": candidate.get("quality_health_rating", "excellent") if candidate else "excellent",
            "detected_blockers": candidate.get("detected_blockers", []) if candidate else [],
            "detected_warnings": candidate.get("detected_warnings", []) if candidate else [],
            "remediation_suggestions": candidate.get("remediation_suggestions", []) if candidate else [],
            "validation_report": candidate.get("validation_report", {}) if candidate else {},
            "remediation_applied": candidate.get("remediation_applied", False) if candidate else False,
            "remediated_paragraphs_count": candidate.get("remediated_paragraphs_count", 0) if candidate else 0,
            "pre_remediation_score": candidate.get("pre_remediation_score") if candidate else None,
            "post_remediation_score": candidate.get("post_remediation_score") if candidate else None,
        }

    def batch_generate_chapters(
        self,
        project_id: str,
        chapter_ids: list[str],
        principal: Principal,
        sync_execute: bool = False,
        max_context_tokens: int | None = None,
        snippet_matches_by_chapter: dict[str, list[dict]] | None = None,
    ) -> dict[str, Any]:
        """批量启动多章节结构化写作方案生成（PRD MVP v1.8 §5.7.2 / AI-OUTLINE-GENERATE-EXPAND）。"""
        state = self.repository.read()

        # 门禁 1：角色与操作权限核验（只读角色拦截）
        role = getattr(principal.user, "role", "")
        norm_role = ROLE_NORMALIZATION_MAP.get(role, role)
        if norm_role in READONLY_SYSTEM_ROLES:
            raise DomainError(403, "FORBIDDEN", "只读角色不可启动章节生成。")

        project = state.projects.get(project_id)
        if project is None or project.company_id != principal.user.company_id:
            raise DomainError(404, "NOT_FOUND", "项目不存在或不属于当前公司。")

        if not writable(state, project_id, principal.user.id):
            raise DomainError(403, "PROJECT_WRITER_REQUIRED", "当前角色无权编辑或启动章节生成。")

        # 门禁 2：敏感项目本地模型隔离门禁（前置阻断）
        self._check_model_gate(state, project)

        successful_results: dict[str, Any] = {}
        failed_chapters: dict[str, Any] = {}
        all_jobs: list[dict[str, Any]] = []
        fingerprints: dict[str, str] = {}
        total_prompt_tokens = 0
        total_estimated_tokens = 0

        for cid in chapter_ids:
            chapter = state.chapters.get(cid)
            if chapter is None or chapter.project_id != project_id:
                failed_chapters[cid] = {
                    "code": "NOT_FOUND",
                    "message": f"章节 {cid} 不存在或不属于当前项目。",
                }
                continue

            workflow = state.workflows.get(project_id, {})
            saved_plan = workflow.get("writing_plan", {}).get("chapters", {}).get(cid, {})
            if not saved_plan.get("confirmed_at") or not plan_is_current(state, project_id, cid):
                # 核心约束：未确认分册或未确认章节绝对不阻塞已确认章节的独立启动
                failed_chapters[cid] = {
                    "code": "PLAN_NOT_CONFIRMED",
                    "message": f"章节 {cid} 写作方案尚未确认或方案已过期，不能启动生成。",
                }
                continue

            try:
                snips = (snippet_matches_by_chapter or {}).get(cid)
                res = self.start_chapter_generation(
                    project_id=project_id,
                    chapter_id=cid,
                    principal=principal,
                    sync_execute=sync_execute,
                    max_context_tokens=max_context_tokens,
                    snippet_matches=snips,
                )
                successful_results[cid] = res
                if res.get("job"):
                    all_jobs.append(res["job"])
                if res.get("context_fingerprint"):
                    fingerprints[cid] = res["context_fingerprint"]
                usage = res.get("token_budget_usage", {})
                total_prompt_tokens += usage.get("prompt_tokens", 0)
                total_estimated_tokens += usage.get("total_estimated_tokens", 0)
            except DomainError as err:
                failed_chapters[cid] = {
                    "code": err.code,
                    "message": err.message,
                }
            except Exception as exc:
                failed_chapters[cid] = {
                    "code": "GENERATION_FAILED",
                    "message": str(exc),
                }

        return {
            "project_id": project_id,
            "total_chapters": len(chapter_ids),
            "total_requested": len(chapter_ids),
            "successful_count": len(successful_results),
            "failed_count": len(failed_chapters),
            "results": successful_results,
            "failed_chapters": failed_chapters,
            "jobs": all_jobs,
            "fingerprints": fingerprints,
            "aggregate_summary": {
                "total_prompt_tokens": total_prompt_tokens,
                "total_estimated_tokens": total_estimated_tokens,
                "context_fingerprints": fingerprints,
            },
            "token_budget_usage_summary": {
                "total_prompt_tokens": total_prompt_tokens,
                "total_estimated_tokens": total_estimated_tokens,
            },
        }

    def schedule_batch_pipeline(
        self,
        project_id: str,
        principal: Principal,
        chapter_ids: list[str] | None = None,
        concurrency_limit: int = 2,
        sync_execute: bool = False,
        max_context_tokens: int | None = None,
        snippet_matches_by_chapter: dict[str, list[dict]] | None = None,
        priority_threshold: str | None = None,
        auto_remediate: bool = False,
    ) -> dict[str, Any]:
        """基于优先级推荐队列的大纲多章节批量生成流水线调度引擎（PRD MVP v1.8 §5.7.8）。

        核心能力：
        1. 优先级自适应排序：依据大纲评分项权重与推荐编写序列（recommended_writing_order），
           优先执行 critical 废标红线与★关键必保章节，次之 high 高分核心章节，再次 medium/low；
        2. 批次切片并发受控：按 concurrency_limit（1~5，默认 2）切分 Stage 批次，防止瞬时并发耗尽显存与 Token 预算；
        3. PRD §5.7.8 关键红线：未确认章节或个别生成失败，绝对不阻塞后续其他已确认/有效章节的批量生成调度与执行；
        4. 全局看板与耗时统计：自动汇聚各批次任务状态、耗时（duration_ms）、Token 预算消耗与优先级执行分布看板；
        5. 安全物理隔离与防编造：涉密项目本地模型强制门禁（403）、白名单防幻觉、多租户强隔离（404）。
        """
        pipeline_start_time = time.time()
        state = self.repository.read()

        # 门禁 1：角色与操作权限核验（只读角色拦截 403）
        role = getattr(principal.user, "role", "")
        norm_role = ROLE_NORMALIZATION_MAP.get(role, role)
        if norm_role in READONLY_SYSTEM_ROLES:
            raise DomainError(403, "FORBIDDEN", "只读角色不可启动章节生成流水线。")

        project = state.projects.get(project_id)
        if project is None or project.company_id != principal.user.company_id:
            raise DomainError(404, "NOT_FOUND", "项目不存在或不属于当前公司。")

        if not writable(state, project_id, principal.user.id):
            raise DomainError(403, "PROJECT_WRITER_REQUIRED", "当前角色无权编辑或启动章节生成流水线。")

        # 门禁 2：涉密项目本地模型隔离门禁（前置阻断）
        self._check_model_gate(state, project)

        workflow = state.workflows.get(project_id, {})
        outline_plans = workflow.get("outline_plans", {})
        recommended_order = workflow.get("recommended_writing_order", [])

        # 1. 建立章节优先级与元数据映射
        ch_meta_map: dict[str, dict[str, Any]] = {}
        if recommended_order:
            for item in recommended_order:
                cid = item.get("chapter_id")
                if cid:
                    ch_meta_map[cid] = item

        # 如果工作流中尚未保存 recommended_order，则尝试从 outline_plans 补齐
        for cid, plan in outline_plans.items():
            if cid not in ch_meta_map:
                ch_meta_map[cid] = {
                    "chapter_id": cid,
                    "title": plan.get("title", ""),
                    "priority": plan.get("priority", "low"),
                    "priority_score": plan.get("priority_score", 0.0),
                    "total_score": plan.get("total_score", 0.0),
                    "section_number": plan.get("section_number", ""),
                    "volume": plan.get("volume", ""),
                }

        # 如果仍为空，调用 calculate_score_weights_and_priorities 动态计算
        if not ch_meta_map:
            reqs = list(workflow.get("requirements", {}).values())
            project_chapters = [c for c in state.chapters.values() if c.project_id == project_id]
            leaves = []
            for c in project_chapters:
                op = outline_plans.get(c.id, {})
                bound_rids = op.get("bound_requirement_ids")
                if not bound_rids:
                    bound_rids = [r["id"] for r in reqs if r.get("chapter_id") == c.id]
                has_ast = op.get("has_asterisk", False) or any(
                    (r.get("mandatory") or r.get("asterisk") or "★" in r.get("clause", "") or "★" in r.get("text", ""))
                    for r in reqs if r.get("chapter_id") == c.id
                )
                has_disq = op.get("has_disqualified", False) or any(
                    (r.get("disqualified") or "废标" in r.get("clause", "") or "废标" in r.get("text", ""))
                    for r in reqs if r.get("chapter_id") == c.id
                )
                leaves.append({
                    "id": c.id,
                    "chapter_id": c.id,
                    "title": c.title,
                    "volume": c.volume,
                    "section_number": op.get("section_number", ""),
                    "bound_requirement_ids": bound_rids,
                    "has_asterisk": has_ast,
                    "has_disqualified": has_disq,
                })
            from icg.domain.outline_auto_tree import calculate_score_weights_and_priorities
            _, dynamic_order = calculate_score_weights_and_priorities(leaves, reqs)
            for item in dynamic_order:
                cid = item.get("chapter_id")
                if cid:
                    ch_meta_map[cid] = item

        # 2. 确定候选执行章节集合
        if chapter_ids is not None:
            candidate_cids = list(chapter_ids)
        else:
            if recommended_order:
                candidate_cids = [item["chapter_id"] for item in recommended_order if item.get("chapter_id")]
            else:
                candidate_cids = [c.id for c in state.chapters.values() if c.project_id == project_id]

        # 3. 按综合优先级（-priority_score, -total_score, section_number）严格排序
        def get_sort_key(cid: str):
            meta = ch_meta_map.get(cid, {})
            p_score = float(meta.get("priority_score") or 0.0)
            t_score = float(meta.get("total_score") or 0.0)
            sec_no = str(meta.get("section_number") or "")
            return (-p_score, -t_score, sec_no, cid)

        ordered_chapter_ids = sorted(candidate_cids, key=get_sort_key)

        # 4. 可选：按优先级阈值过滤（priority_threshold）
        PRIORITY_LEVELS = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        if priority_threshold and priority_threshold.lower() in PRIORITY_LEVELS:
            min_lvl = PRIORITY_LEVELS[priority_threshold.lower()]
            ordered_chapter_ids = [
                cid for cid in ordered_chapter_ids
                if PRIORITY_LEVELS.get(ch_meta_map.get(cid, {}).get("priority", "low"), 1) >= min_lvl
            ]

        # 5. 切片批次规划（Batch Pipeline Slicing）
        limit_val = 2 if concurrency_limit is None else concurrency_limit
        limit = max(1, min(int(limit_val), 5))
        batched_cids = [ordered_chapter_ids[i:i + limit] for i in range(0, len(ordered_chapter_ids), limit)]

        pipeline_id = f"pipeline-{project_id}-{int(pipeline_start_time * 1000)}"
        pipeline_batches: list[dict[str, Any]] = []
        successful_results: dict[str, Any] = {}
        failed_chapters: dict[str, Any] = {}
        skipped_unconfirmed: list[dict[str, Any]] = []
        all_jobs: list[dict[str, Any]] = []
        fingerprints: dict[str, str] = {}
        by_chapter_tokens: dict[str, dict[str, int]] = {}
        total_prompt_tokens = 0
        total_estimated_tokens = 0

        # 6. 按批次切片推进执行（落实未确认章节不阻塞已确认章节核心红线）
        for batch_idx, batch_cids in enumerate(batched_cids, start=1):
            batch_start = time.time()
            batch_successful: dict[str, Any] = {}
            batch_failed: dict[str, Any] = {}
            batch_jobs: list[dict[str, Any]] = []
            batch_prompt_tokens = 0
            batch_estimated_tokens = 0

            for cid in batch_cids:
                chapter = state.chapters.get(cid)
                if chapter is None or chapter.project_id != project_id:
                    err_info = {
                        "code": "NOT_FOUND",
                        "message": f"章节 {cid} 不存在或不属于当前项目。",
                        "priority": ch_meta_map.get(cid, {}).get("priority", "low"),
                    }
                    failed_chapters[cid] = err_info
                    batch_failed[cid] = err_info
                    continue

                saved_plan = workflow.get("writing_plan", {}).get("chapters", {}).get(cid, {})
                if not saved_plan.get("confirmed_at") or not plan_is_current(state, project_id, cid):
                    # 核心红线：未确认方案章节绝对不阻塞其他章节调度生成
                    skip_info = {
                        "chapter_id": cid,
                        "reason": "PLAN_NOT_CONFIRMED",
                        "status": "skipped",
                        "message": f"章节 {cid} 写作方案尚未确认或方案已过期，流水线跳过生成并继续后续章节。",
                    }
                    skipped_unconfirmed.append(skip_info)
                    err_info = {
                        "code": "PLAN_NOT_CONFIRMED",
                        "message": skip_info["message"],
                        "priority": ch_meta_map.get(cid, {}).get("priority", "low"),
                    }
                    failed_chapters[cid] = err_info
                    batch_failed[cid] = err_info
                    continue

                try:
                    ch_start = time.time()
                    snips = (snippet_matches_by_chapter or {}).get(cid)
                    res = self.start_chapter_generation(
                        project_id=project_id,
                        chapter_id=cid,
                        principal=principal,
                        sync_execute=sync_execute,
                        max_context_tokens=max_context_tokens,
                        snippet_matches=snips,
                        auto_remediate=auto_remediate,
                    )
                    ch_elapsed = round((time.time() - ch_start) * 1000, 2)
                    res["elapsed_ms"] = ch_elapsed
                    res["priority"] = ch_meta_map.get(cid, {}).get("priority", "low")
                    res["priority_score"] = ch_meta_map.get(cid, {}).get("priority_score", 0.0)

                    successful_results[cid] = res
                    batch_successful[cid] = res

                    if res.get("job"):
                        all_jobs.append(res["job"])
                        batch_jobs.append(res["job"])
                    if res.get("context_fingerprint"):
                        fingerprints[cid] = res["context_fingerprint"]

                    usage = res.get("token_budget_usage", {})
                    p_tok = usage.get("prompt_tokens", 0)
                    e_tok = usage.get("total_estimated_tokens", 0)
                    c_tok = usage.get("reserved_generation_tokens", max(0, e_tok - p_tok))
                    total_prompt_tokens += p_tok
                    total_estimated_tokens += e_tok
                    batch_prompt_tokens += p_tok
                    batch_estimated_tokens += e_tok
                    by_chapter_tokens[cid] = {
                        "prompt_tokens": p_tok,
                        "completion_tokens": c_tok,
                        "total_tokens": p_tok + c_tok,
                    }
                except DomainError as err:
                    err_info = {
                        "code": err.code,
                        "message": err.message,
                        "priority": ch_meta_map.get(cid, {}).get("priority", "low"),
                    }
                    failed_chapters[cid] = err_info
                    batch_failed[cid] = err_info
                except Exception as exc:
                    err_info = {
                        "code": "GENERATION_FAILED",
                        "message": str(exc),
                        "priority": ch_meta_map.get(cid, {}).get("priority", "low"),
                    }
                    failed_chapters[cid] = err_info
                    batch_failed[cid] = err_info

            batch_duration_ms = round((time.time() - batch_start) * 1000, 2)
            if len(batch_successful) == len(batch_cids):
                batch_status = "completed"
            elif len(batch_successful) > 0:
                batch_status = "partial_completed"
            else:
                batch_status = "failed"

            batch_record = {
                "batch_index": batch_idx,
                "batch_name": f"Stage {batch_idx} (Batch {batch_idx})",
                "chapter_ids": batch_cids,
                "chapter_count": len(batch_cids),
                "chapters_metadata": [
                    {
                        "chapter_id": cid,
                        "title": ch_meta_map.get(cid, {}).get("title", ""),
                        "priority": ch_meta_map.get(cid, {}).get("priority", "low"),
                        "priority_score": ch_meta_map.get(cid, {}).get("priority_score", 0.0),
                        "section_number": ch_meta_map.get(cid, {}).get("section_number", ""),
                        "total_score": ch_meta_map.get(cid, {}).get("total_score", 0.0),
                        "status": "success" if cid in batch_successful else "failed",
                        "validation_passed": batch_successful.get(cid, {}).get("validation_passed", True) if cid in batch_successful else False,
                        "quality_health_score": batch_successful.get(cid, {}).get("quality_health_score", 100) if cid in batch_successful else 0,
                        "quality_health_rating": batch_successful.get(cid, {}).get("quality_health_rating", "excellent") if cid in batch_successful else "critical",
                        "blocker_count": len(batch_successful.get(cid, {}).get("detected_blockers", [])) if cid in batch_successful else 0,
                        "remediation_applied": batch_successful.get(cid, {}).get("remediation_applied", False) if cid in batch_successful else False,
                        "remediated_paragraphs_count": batch_successful.get(cid, {}).get("remediated_paragraphs_count", 0) if cid in batch_successful else 0,
                    }
                    for cid in batch_cids
                ],
                "status": batch_status,
                "duration_ms": batch_duration_ms,
                "succeeded_count": len(batch_successful),
                "failed_count": len(batch_failed),
                "succeeded_chapter_ids": list(batch_successful.keys()),
                "failed_chapter_ids": list(batch_failed.keys()),
                "token_budget_usage": {
                    "prompt_tokens": batch_prompt_tokens,
                    "estimated_tokens": batch_estimated_tokens,
                },
            }
            pipeline_batches.append(batch_record)

        total_pipeline_duration_ms = round((time.time() - pipeline_start_time) * 1000, 2)

        if len(successful_results) == len(ordered_chapter_ids) and len(ordered_chapter_ids) > 0:
            pipeline_status = "completed"
        elif len(successful_results) > 0:
            pipeline_status = "partial_completed"
        else:
            pipeline_status = "failed"

        # 7. 优先级分布统计
        priority_summary = {}
        for p in ["critical", "high", "medium", "low"]:
            p_cids = [cid for cid in ordered_chapter_ids if ch_meta_map.get(cid, {}).get("priority") == p]
            p_succ = sum(1 for cid in p_cids if cid in successful_results)
            p_fail = sum(1 for cid in p_cids if cid in failed_chapters)
            priority_summary[p] = {
                "total": len(p_cids),
                "succeeded": p_succ,
                "failed": p_fail,
            }

        # 8. 全局 Token 预算与看板统计
        limit_tokens = max_context_tokens or DEFAULT_MAX_CONTEXT_TOKENS
        token_dashboard = {
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": max(0, total_estimated_tokens - total_prompt_tokens),
            "total_tokens": total_estimated_tokens if total_estimated_tokens > 0 else total_prompt_tokens,
            "total_estimated_tokens": total_estimated_tokens,
            "max_context_tokens_limit": limit_tokens,
            "average_prompt_tokens_per_chapter": round(total_prompt_tokens / max(1, len(successful_results)), 1),
            "context_fingerprints": fingerprints,
            "by_chapter": by_chapter_tokens,
        }

        total_validation_passed = sum(1 for r in successful_results.values() if r.get("validation_passed", True))
        total_validation_failed = sum(1 for r in successful_results.values() if not r.get("validation_passed", True))
        total_detected_blockers = sum(len(r.get("detected_blockers", [])) for r in successful_results.values())
        average_quality_score = round(
            sum(r.get("quality_health_score", 100) for r in successful_results.values()) / max(1, len(successful_results)),
            1,
        ) if successful_results else 100.0

        total_remediated_chapters = sum(1 for r in successful_results.values() if r.get("remediation_applied", False))
        validation_summary = {
            "total_validation_passed": total_validation_passed,
            "total_validation_failed": total_validation_failed,
            "total_detected_blockers": total_detected_blockers,
            "average_quality_score": average_quality_score,
            "total_remediated_chapters": total_remediated_chapters,
        }

        dashboard_record = {
            "pipeline_id": pipeline_id,
            "project_id": project_id,
            "concurrency_limit": limit,
            "total_batches": len(pipeline_batches),
            "total_chapters_planned": len(ordered_chapter_ids),
            "total_chapters_scheduled": len(ordered_chapter_ids),
            "succeeded_count": len(successful_results),
            "failed_count": len(failed_chapters),
            "skipped_unconfirmed_count": len(skipped_unconfirmed),
            "pipeline_status": pipeline_status,
            "duration_ms": total_pipeline_duration_ms,
            "token_budget_usage": token_dashboard,
            "priority_execution_summary": priority_summary,
            "validation_summary": validation_summary,
            "created_at": iso_time(datetime.now(timezone.utc).timestamp()),
        }

        # 9. 持久化记录到工作流
        def save_pipeline_op(st: DemoState):
            wf = st.workflows.setdefault(project_id, {})
            runs = wf.setdefault("batch_pipeline_runs", [])
            runs.append(dashboard_record)
            wf["latest_batch_pipeline_run"] = deepcopy(dashboard_record)

        self.repository.transaction(save_pipeline_op)

        return {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "pipeline_status": pipeline_status,
            "concurrency_limit": limit,
            "total_batches": len(pipeline_batches),
            "total_chapters_planned": len(ordered_chapter_ids),
            "total_chapters_scheduled": len(ordered_chapter_ids),
            "succeeded_count": len(successful_results),
            "failed_count": len(failed_chapters),
            "skipped_unconfirmed_count": len(skipped_unconfirmed),
            "duration_ms": total_pipeline_duration_ms,
            "total_duration_ms": total_pipeline_duration_ms,
            "batches": pipeline_batches,
            "results": successful_results,
            "failed_chapters": failed_chapters,
            "skipped_unconfirmed_chapters": skipped_unconfirmed,
            "jobs": all_jobs,
            "fingerprints": fingerprints,
            "dashboard": dashboard_record,
            "token_budget_dashboard": token_dashboard,
            "priority_execution_summary": priority_summary,
            "validation_summary": validation_summary,
        }

    def _check_access(self, state: DemoState, project_id: str, chapter_id: str, principal: Principal) -> None:
        role = getattr(principal.user, "role", "")
        norm_role = ROLE_NORMALIZATION_MAP.get(role, role)
        if norm_role in READONLY_SYSTEM_ROLES:
            raise DomainError(403, "FORBIDDEN", "只读角色不可启动章节生成。")

        project = state.projects.get(project_id)
        if project is None or project.company_id != principal.user.company_id:
            raise DomainError(404, "NOT_FOUND", "项目不存在或不属于当前公司。")

        chapter = state.chapters.get(chapter_id)
        if chapter is None or chapter.project_id != project_id:
            raise DomainError(404, "NOT_FOUND", "章节不存在或不属于当前项目。")

        if not writable(state, project_id, principal.user.id):
            raise DomainError(403, "PROJECT_WRITER_REQUIRED", "当前角色无权编辑或启动章节生成。")

    def _check_model_gate(self, state: DemoState, project: Project, provider: Any | None = None) -> None:
        is_sensitive = getattr(project, "sensitive", False) or getattr(project, "is_sensitive", False)
        if not is_sensitive:
            return

        if provider is not None:
            if getattr(provider, "is_local", False) is False and getattr(provider, "is_real_model", None) is not False:
                raise DomainError(403, "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL", "敏感项目只能使用本地模型配置。")

        bound_id = state.project_model_configs.get(project.id)
        cfg = state.model_configs.get(bound_id) if bound_id else state.model_configs.get(f"default-{project.company_id}")

        if cfg is not None:
            if not getattr(cfg, "is_local", False) or not getattr(cfg, "allow_sensitive", False):
                raise DomainError(403, "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL", "敏感项目只能使用本地模型配置。")
        else:
            resolved_p = None
            if hasattr(self.demo, "resolve_model_provider"):
                try:
                    resolved_p = self.demo.resolve_model_provider(state, project.id)
                except Exception:
                    resolved_p = None
            active_p = resolved_p or getattr(self.demo, "model_provider", None)
            if active_p and getattr(active_p, "is_local", False) is False and getattr(active_p, "is_real_model", None) is not False:
                raise DomainError(403, "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL", "敏感项目只能使用本地模型配置。")

    def validate_chapter_content(
        self,
        project_id: str,
        chapter_id: str,
        principal: Principal,
        content: str | None = None,
    ) -> dict[str, Any]:
        """即时质检章节正文或候选草稿合规性（PRD MVP v1.8 §5.7.8 / §5.10 / AI-CHAPTER-AUTO-VALIDATION-GATE）。"""
        state = self.repository.read()

        # 门禁 1：角色与操作权限核验（只读角色拦截 403）
        role = getattr(principal.user, "role", "")
        norm_role = ROLE_NORMALIZATION_MAP.get(role, role)
        if norm_role in READONLY_SYSTEM_ROLES:
            raise DomainError(403, "FORBIDDEN", "只读角色不可执行章节合规质检。")

        # 租户与项目隔离（404）
        project = state.projects.get(project_id)
        if project is None or project.company_id != principal.user.company_id:
            raise DomainError(404, "NOT_FOUND", "项目不存在或不属于当前公司。")

        chapter = state.chapters.get(chapter_id)
        if chapter is None or chapter.project_id != project_id:
            raise DomainError(404, "NOT_FOUND", "章节不存在或不属于当前项目。")

        workflow = state.workflows.get(project_id, {})
        prompt_plan = workflow.get("writing_plan", {}).get("chapters", {}).get(chapter_id, {})

        allowed_evidence_ids = {e.get("id") for e in prompt_plan.get("evidence", []) if e.get("id")}
        reqs = [r for r in workflow.get("requirements", {}).values() if r.get("chapter_id") == chapter_id]
        for r in reqs:
            for eid in r.get("evidence_ids", []):
                if eid:
                    allowed_evidence_ids.add(eid)

        allowed_snippet_ids: set[str] = set()
        retrieved = prompt_plan.get("retrieved_evidence", [])
        for chunk in retrieved:
            cid = chunk.get("chunk_id") or chunk.get("id")
            if cid:
                allowed_snippet_ids.add(cid)

        # 目标正文：优先使用入参 content，若无则读取候选草稿或正式正文
        target_content = content
        candidate = workflow.get("candidates", {}).get(chapter_id)
        if target_content is None:
            if candidate and candidate.get("content"):
                target_content = candidate["content"]
            else:
                target_content = chapter.content or ""

        paragraphs = parse_structured_paragraphs(
            target_content,
            scoring_points=prompt_plan.get("writing_points"),
            allowed_evidence_ids=allowed_evidence_ids,
            allowed_snippet_ids=allowed_snippet_ids,
        )

        return validate_chapter_candidate(
            content=target_content,
            paragraphs=paragraphs,
            chapter=chapter,
            allowed_evidence_ids=allowed_evidence_ids,
            allowed_snippet_ids=allowed_snippet_ids,
            workflow=workflow,
            project=project,
        )

    def remediate_chapter_candidate(
        self,
        project_id: str,
        chapter_id: str,
        principal: Principal,
        content: str | None = None,
        candidate: dict[str, Any] | None = None,
        max_rounds: int = 3,
        auto_save: bool = True,
        provider: Any | None = None,
    ) -> dict[str, Any]:
        """对存在合规缺陷的章节执行自动整改建议合成与局部针对性智能重写（PRD MVP v1.8 §5.7.8 & §5.10 / AI-OUTLINE-AUTO-REMEDIATION）。

        核心能力：
        1. 针对性局部智能重写：定位含有 blocker 缺陷的特定段落，保持未违规段落不受影响；
        2. 自动诊断与整改指引合成：自动提取检出缺陷、生成针对性修复 Prompt 与确定性保底清洗方案；
        3. 即时复检与门禁清零：重写后自动重新执行 validate_chapter_candidate，直至 blocker 清零、质量健康分跃升；
        4. 涉密与权限硬隔离：涉密项目本地模型硬门禁（403）、多租户强隔离（404）、只读角色拦截（403）。
        """
        state = self.repository.read()

        # 门禁 1：角色与操作权限核验（只读角色拦截 403）
        role = getattr(principal.user, "role", "")
        norm_role = ROLE_NORMALIZATION_MAP.get(role, role)
        if norm_role in READONLY_SYSTEM_ROLES:
            raise DomainError(403, "FORBIDDEN", "只读角色不可执行章节合规整改与智能重写。")

        # 门禁 2：租户与项目隔离（404）
        project = state.projects.get(project_id)
        if project is None or project.company_id != principal.user.company_id:
            raise DomainError(404, "NOT_FOUND", "项目不存在或不属于当前公司。")

        chapter = state.chapters.get(chapter_id)
        if chapter is None or chapter.project_id != project_id:
            raise DomainError(404, "NOT_FOUND", "章节不存在或不属于当前项目。")

        if not writable(state, project_id, principal.user.id):
            raise DomainError(403, "PROJECT_WRITER_REQUIRED", "当前角色无权编辑或执行章节整改。")

        # 门禁 3：涉密项目本地模型硬门禁（403）
        model_provider = provider
        if model_provider is None:
            model_provider = self.demo.resolve_model_provider(state, project_id)
        self._check_model_gate(state, project, provider=model_provider)

        workflow = state.workflows.get(project_id, {})
        prompt_plan = workflow.get("writing_plan", {}).get("chapters", {}).get(chapter_id, {})

        allowed_evidence_ids = {e.get("id") for e in prompt_plan.get("evidence", []) if e.get("id")}
        reqs = [r for r in workflow.get("requirements", {}).values() if r.get("chapter_id") == chapter_id]
        for r in reqs:
            for eid in r.get("evidence_ids", []):
                if eid:
                    allowed_evidence_ids.add(eid)

        allowed_snippet_ids: set[str] = set()
        retrieved = prompt_plan.get("retrieved_evidence", [])
        for chunk in retrieved:
            cid = chunk.get("chunk_id") or chunk.get("id")
            if cid:
                allowed_snippet_ids.add(cid)

        facts = prompt_plan.get("facts", []) or workflow.get("facts", [])

        # 确定待整改初始内容与 candidate
        current_candidate = candidate
        if current_candidate is None:
            current_candidate = workflow.get("candidates", {}).get(chapter_id)

        current_content = content
        if current_content is None:
            if current_candidate and current_candidate.get("content"):
                current_content = current_candidate["content"]
            else:
                current_content = chapter.content or ""

        active_paragraphs = parse_structured_paragraphs(
            current_content,
            scoring_points=prompt_plan.get("writing_points"),
            allowed_evidence_ids=allowed_evidence_ids,
            allowed_snippet_ids=allowed_snippet_ids,
        )
        if not active_paragraphs and current_content:
            active_paragraphs = [{"index": 0, "label": "[P1]", "content": current_content, "text": current_content}]

        initial_val = validate_chapter_candidate(
            content=current_content,
            paragraphs=active_paragraphs,
            chapter=chapter,
            allowed_evidence_ids=allowed_evidence_ids,
            allowed_snippet_ids=allowed_snippet_ids,
            workflow=workflow,
            project=project,
        )

        initial_health_score = initial_val["quality_health_score"]
        initial_rating = initial_val["quality_health_rating"]

        # PRD v1.8 §5.7.4：由系统规则编排“检查 → 定位修正 → 再检查”，直接转人工的问题永远不进入自动修正。
        from .chapter_loop import LoopContext, run_chapter_loop

        critical = any(
            str(r.get("importance", "")).lower() in ("star", "critical", "disqualification")
            or str(r.get("category", "")).lower() in ("star", "disqualification")
            or "★" in str(r.get("text", ""))
            for r in reqs
        )
        loop_context = LoopContext(
            title=getattr(chapter, "title", ""),
            allowed_evidence_ids=allowed_evidence_ids,
            allowed_snippet_ids=allowed_snippet_ids,
            facts=facts if isinstance(facts, list) else list(facts.values()) if isinstance(facts, dict) else [],
            critical=critical,
        )

        def model_fix(original: str, issues: list[dict[str, Any]]) -> str | None:
            if not (model_provider and hasattr(model_provider, "suggest")):
                return None
            prompt = (
                f"你是投标文件编写人。请只修正章节「{getattr(chapter, 'title', '')}」中的下面这一段：\n"
                f"【原段落】\n{original}\n【需要修正的问题】\n"
                + "\n".join(f"- {i['message']}；{i['suggestion']}" for i in issues)
                + "\n【要求】只输出替换后的这一段；不得新增或改动数字、人员、证据编号；没有依据的内容写【待补：缺少什么】。"
            )
            return model_provider.suggest(prompt, original)

        loop_outcome = run_chapter_loop(current_content, loop_context, max_rounds=max_rounds, model_fix=model_fix)
        # 段落编号沿用结构化段落（[P1]…[Pn]）口径，便于与写作方案和编辑台对照。
        before_structured = [p.get("content") for p in active_paragraphs]
        after_structured = [p.get("content") for p in parse_structured_paragraphs(
            loop_outcome["content"],
            scoring_points=prompt_plan.get("writing_points"),
            allowed_evidence_ids=allowed_evidence_ids,
            allowed_snippet_ids=allowed_snippet_ids,
        )]
        remediated_indices: set[int] = {
            i for i, text in enumerate(after_structured) if i < len(before_structured) and text != before_structured[i]
        }
        current_content = loop_outcome["content"]
        rounds_executed = len(loop_outcome["rounds"])
        remediation_history: list[dict[str, Any]] = [
            {
                "round": r["round"],
                "remediated_paragraph_indices": r["modified_paragraphs"],
                "found": r["found"],
                "resolved": r["resolved"],
                "conclusion": r["conclusion"],
            }
            for r in loop_outcome["rounds"]
        ]
        active_paragraphs = parse_structured_paragraphs(
            current_content,
            scoring_points=prompt_plan.get("writing_points"),
            allowed_evidence_ids=allowed_evidence_ids,
            allowed_snippet_ids=allowed_snippet_ids,
        )
        current_val = validate_chapter_candidate(
            content=current_content,
            paragraphs=active_paragraphs,
            chapter=chapter,
            allowed_evidence_ids=allowed_evidence_ids,
            allowed_snippet_ids=allowed_snippet_ids,
            workflow=workflow,
            project=project,
        )
        latest_plan = synthesize_remediation_plan(
            content=current_content,
            paragraphs=active_paragraphs,
            chapter=chapter,
            allowed_evidence_ids=allowed_evidence_ids,
            allowed_snippet_ids=allowed_snippet_ids,
            facts=loop_context.facts,
            detected_blockers=current_val["detected_blockers"],
            detected_warnings=current_val["detected_warnings"],
            project=project,
        ) if not loop_outcome["passed"] else {"has_defects": False, "target_paragraphs": []}

        now_time = self.demo._now() if hasattr(self.demo, "_now") else time.time()
        now_iso = iso_time(now_time)
        cand_id = (current_candidate.get("id") if current_candidate else None) or new_id("candidate")

        remediated_candidate = dict(current_candidate or {})
        remediated_candidate.update({
            "id": cand_id,
            "content": current_content,
            "structured_content": current_content,
            "paragraphs": active_paragraphs,
            "validation_passed": current_val["validation_passed"],
            "validation_failed": current_val["validation_failed"],
            "quality_health_score": current_val["quality_health_score"],
            "quality_health_rating": current_val["quality_health_rating"],
            "detected_blockers": current_val["detected_blockers"],
            "detected_warnings": current_val["detected_warnings"],
            "remediation_suggestions": current_val["remediation_suggestions"],
            "validation_report": current_val["validation_report"],
            "remediation_applied": len(remediated_indices) > 0,
            "remediation_rounds": rounds_executed,
            "remediated_paragraphs_count": len(remediated_indices),
            "remediated_paragraph_indices": sorted(list(remediated_indices)),
            "pre_remediation_score": initial_health_score,
            "post_remediation_score": current_val["quality_health_score"],
            "pre_remediation_rating": initial_rating,
            "post_remediation_rating": current_val["quality_health_rating"],
            "remediation_plan": latest_plan,
            "remediation_history": remediation_history,
            "loop_stop_reason": loop_outcome["stop_reason"],
            "loop_stop_reason_label": loop_outcome["stop_reason_label"],
            "loop_rolled_back": loop_outcome["rolled_back"],
            "human_issue_count": len(loop_outcome["issues"]),
            "updated_at": now_iso,
        })

        loop_record: dict[str, Any] | None = None
        if auto_save:
            def save_remediated_cand(st: DemoState):
                nonlocal loop_record
                from .chapter_loop import record_loop

                wf = st.workflows.setdefault(project_id, {})
                wf.setdefault("candidates", {})[chapter_id] = remediated_candidate
                order = wf.get("chapter_order") or [c.id for c in st.chapters.values() if c.project_id == project_id]
                number = order.index(chapter_id) + 1 if chapter_id in order else 1
                live_chapter = st.chapters.get(chapter_id, chapter)
                loop_record = record_loop(
                    wf, live_chapter, number, loop_outcome, actor_id=principal.user.id, now_iso=now_iso,
                    checked_revision=int(getattr(live_chapter, "revision", 0) or 0), kind="generation_candidate",
                    meta=generation_loop_meta(st, project_id, remediated_candidate),
                )

            self.repository.transaction(save_remediated_cand)

        return {
            "remediation_passed": current_val["validation_passed"],
            "remediation_applied": len(remediated_indices) > 0,
            "remediation_rounds": rounds_executed,
            "pre_remediation_score": initial_health_score,
            "post_remediation_score": current_val["quality_health_score"],
            "pre_remediation_rating": initial_rating,
            "post_remediation_rating": current_val["quality_health_rating"],
            "remediated_paragraphs_count": len(remediated_indices),
            "remediated_paragraph_indices": sorted(list(remediated_indices)),
            "candidate": remediated_candidate,
            "validation_report": current_val["validation_report"],
            "remediation_plan": latest_plan,
            "remediation_history": remediation_history,
            "loop": loop_record,
            "loop_stop_reason": loop_outcome["stop_reason"],
            "human_issues": loop_outcome["issues"],
            "loop_outcome": loop_outcome if not auto_save else None,
        }


def start_chapter_generation(
    project_id_or_service: Any,
    chapter_id_or_proj: str | None = None,
    principal_or_chap: Any = None,
    principal: Principal | None = None,
    *,
    demo: Any | None = None,
    repository: Any | None = None,
    evidence_service: Any | None = None,
    sync_execute: bool = False,
    max_context_tokens: int | None = None,
    snippet_matches: list[dict] | None = None,
    auto_remediate: bool = False,
) -> dict:
    """按逐节确认结果独立启动已确认章节的生成任务（模块顶层快捷入口，兼容多种传参形式）。"""
    if hasattr(project_id_or_service, "start_chapter_generation") and not isinstance(project_id_or_service, str):
        # 形式 1: start_chapter_generation(service, project_id, chapter_id, principal)
        service = project_id_or_service
        return service.start_chapter_generation(
            chapter_id_or_proj,
            principal_or_chap,
            principal,
            sync_execute=sync_execute,
            max_context_tokens=max_context_tokens,
            snippet_matches=snippet_matches,
            auto_remediate=auto_remediate,
        )

    # 形式 2: start_chapter_generation(project_id, chapter_id, principal, demo=...)
    project_id = str(project_id_or_service)
    chapter_id = str(chapter_id_or_proj)
    prin = principal_or_chap if principal is None else principal

    if demo is None:
        raise ValueError("demo or service must be provided to start_chapter_generation")

    service = ChapterGenerationService(demo, repository=repository, evidence_service=evidence_service)
    return service.start_chapter_generation(
        project_id,
        chapter_id,
        prin,
        sync_execute=sync_execute,
        max_context_tokens=max_context_tokens,
        snippet_matches=snippet_matches,
        auto_remediate=auto_remediate,
    )


def batch_generate_chapters(
    project_id_or_service: Any,
    chapter_ids_or_proj: list[str] | None = None,
    principal_or_chap: Any = None,
    principal: Principal | None = None,
    *,
    demo: Any | None = None,
    repository: Any | None = None,
    evidence_service: Any | None = None,
    sync_execute: bool = False,
    max_context_tokens: int | None = None,
    snippet_matches_by_chapter: dict[str, list[dict]] | None = None,
) -> dict[str, Any]:
    """批量启动多章节结构化写作方案生成（模块顶层快捷入口）。"""
    if hasattr(project_id_or_service, "batch_generate_chapters") and not isinstance(project_id_or_service, str):
        service = project_id_or_service
        return service.batch_generate_chapters(
            chapter_ids_or_proj,
            principal_or_chap,
            principal=principal,
            sync_execute=sync_execute,
            max_context_tokens=max_context_tokens,
            snippet_matches_by_chapter=snippet_matches_by_chapter,
        )

    project_id = str(project_id_or_service)
    chapter_ids = list(chapter_ids_or_proj or [])
    prin = principal_or_chap if principal is None else principal

    if demo is None:
        raise ValueError("demo or service must be provided to batch_generate_chapters")

    service = ChapterGenerationService(demo, repository=repository, evidence_service=evidence_service)
    return service.batch_generate_chapters(
        project_id,
        chapter_ids,
        prin,
        sync_execute=sync_execute,
        max_context_tokens=max_context_tokens,
        snippet_matches_by_chapter=snippet_matches_by_chapter,
    )


def schedule_batch_pipeline(
    project_id_or_service: Any,
    principal_or_proj: Any = None,
    chapter_ids: list[str] | None = None,
    principal: Principal | None = None,
    concurrency_limit: int = 2,
    sync_execute: bool = False,
    max_context_tokens: int | None = None,
    snippet_matches_by_chapter: dict[str, list[dict]] | None = None,
    priority_threshold: str | None = None,
    auto_remediate: bool = False,
    *,
    demo: Any | None = None,
    repository: Any | None = None,
    evidence_service: Any | None = None,
) -> dict[str, Any]:
    """基于优先级推荐队列的大纲多章节批量生成流水线调度（模块顶层快捷入口）。"""
    if hasattr(project_id_or_service, "schedule_batch_pipeline") and not isinstance(project_id_or_service, str):
        service = project_id_or_service
        return service.schedule_batch_pipeline(
            principal_or_proj,
            chapter_ids=chapter_ids,
            principal=principal,
            concurrency_limit=concurrency_limit,
            sync_execute=sync_execute,
            max_context_tokens=max_context_tokens,
            snippet_matches_by_chapter=snippet_matches_by_chapter,
            priority_threshold=priority_threshold,
            auto_remediate=auto_remediate,
        )

    project_id = str(project_id_or_service)
    prin = principal_or_proj if principal is None else principal

    if demo is None:
        raise ValueError("demo or service must be provided to schedule_batch_pipeline")

    service = ChapterGenerationService(demo, repository=repository, evidence_service=evidence_service)
    return service.schedule_batch_pipeline(
        project_id=project_id,
        principal=prin,
        chapter_ids=chapter_ids,
        concurrency_limit=concurrency_limit,
        sync_execute=sync_execute,
        max_context_tokens=max_context_tokens,
        snippet_matches_by_chapter=snippet_matches_by_chapter,
        priority_threshold=priority_threshold,
        auto_remediate=auto_remediate,
    )


def validate_chapter_content(
    project_id_or_service: Any,
    chapter_id_or_proj: Any = None,
    principal: Principal | None = None,
    content: str | None = None,
    *,
    demo: Any | None = None,
    repository: Any | None = None,
) -> dict[str, Any]:
    """即时质检章节正文或候选草稿合规性（模块顶层快捷入口）。"""
    if hasattr(project_id_or_service, "validate_chapter_content") and not isinstance(project_id_or_service, str):
        service = project_id_or_service
        return service.validate_chapter_content(
            chapter_id_or_proj,
            principal=principal,
            content=content,
        )

    project_id = str(project_id_or_service)
    chapter_id = str(chapter_id_or_proj)
    if demo is None:
        raise ValueError("demo or service must be provided to validate_chapter_content")

    service = ChapterGenerationService(demo, repository=repository)
    return service.validate_chapter_content(
        project_id=project_id,
        chapter_id=chapter_id,
        principal=principal,
        content=content,
    )


def remediate_chapter_candidate(
    project_id_or_service: Any,
    chapter_id_or_proj: Any = None,
    principal: Principal | None = None,
    content: str | None = None,
    candidate: dict[str, Any] | None = None,
    max_rounds: int = 3,
    auto_save: bool = True,
    *,
    demo: Any | None = None,
    repository: Any | None = None,
    provider: Any | None = None,
) -> dict[str, Any]:
    """对存在合规缺陷的章节执行自动整改建议合成与局部针对性智能重写（模块顶层快捷入口）。"""
    if hasattr(project_id_or_service, "remediate_chapter_candidate") and not isinstance(project_id_or_service, str):
        service = project_id_or_service
        return service.remediate_chapter_candidate(
            chapter_id_or_proj,
            principal=principal,
            content=content,
            candidate=candidate,
            max_rounds=max_rounds,
            auto_save=auto_save,
            provider=provider,
        )

    project_id = str(project_id_or_service)
    chapter_id = str(chapter_id_or_proj)
    if demo is None:
        raise ValueError("demo or service must be provided to remediate_chapter_candidate")

    service = ChapterGenerationService(demo, repository=repository)
    return service.remediate_chapter_candidate(
        project_id=project_id,
        chapter_id=chapter_id,
        principal=principal,
        content=content,
        candidate=candidate,
        max_rounds=max_rounds,
        auto_save=auto_save,
        provider=provider,
    )



