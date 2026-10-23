# 为什么有这个文件：实现 PRD MVP §5.8 / §5.8.1 / §5.8.5 第一批核心合规规则体系（P0 规则编号落地）。
# 它解决什么问题：
# 1. 结构化实现 R15（证明材料齐全性核验）、R23（废标红线与关键标星条款响应率核验）、
#    R34（占位符与“待补/待完善”残留字样核验）、R37（技术/商务偏离表一致性核验）；
# 2. 为合规检查中心、分册定稿前置门禁与整本递交导出门禁提供确定性、可复现的编号规则裁决；
# 3. 输出结构化结果：rule_id, title, severity, passed, finding_summary, suggestion 与具体问题项；
# 4. 严禁巨石逻辑膨胀，新业务全部封装在 icg.domain 上下文子包内。

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

from icg_demo.domain import (
    DemoService,
    DemoState,
    DomainError,
    Principal,
    iso_time,
    new_id,
)
from icg_demo.generation_context import evidence_expired
from icg_demo.project_access import (
    VOLUMES,
    lead,
    writable,
)

SHANGHAI = timezone = None
try:
    from icg.domain.export_service import SHANGHAI
except ImportError:
    from datetime import timedelta, timezone
    SHANGHAI = timezone(timedelta(hours=8))


def is_critical_requirement(row: dict) -> bool:
    """判定是否为废标红线或关键标星条款。"""
    text = str(row.get("text", "") or "")
    is_disqual = bool(
        row.get("is_disqualification") is True
        or row.get("category") == "disqualification"
        or "废标" in text
        or "否决" in text
    )
    is_star = bool(
        row.get("importance") == "star"
        or row.get("category") == "star"
        or "★" in text
        or "标星" in text
        or "星号" in text
    )
    return is_disqual or is_star


def plan_is_current(state: DemoState, project_id: str, chapter_id: str) -> bool:
    chapter = state.chapters.get(chapter_id)
    return bool(chapter and chapter.project_id == project_id and chapter.writing_input.is_current)


@dataclass
class ComplianceRuleIssue:
    id: str
    rule_id: str
    code: str
    severity: Literal["blocker", "blocking", "warning", "info"]
    message: str
    requirement_id: str | None = None
    chapter_id: str | None = None
    evidence_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ComplianceRuleResult:
    rule_id: str
    title: str
    severity: Literal["blocker", "blocking", "warning", "info"]
    passed: bool
    finding_summary: str
    suggestion: str
    issues: list[dict[str, Any]] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ComplianceRulesEngine:
    """PRD P0 级合规规则执行引擎（R15、R23、R34、R37）。"""

    CATALOG = [
        {
            "rule_id": "R15",
            "title": "证明材料齐全性核验",
            "category": "qualification",
            "default_severity": "blocker",
            "can_disable": False,
            "description": "核验资质、证书、业绩、原厂授权等证明类要求是否已挂接已确认且在保质期内的企业材料，严禁证据缺失或过期。",
        },
        {
            "rule_id": "R23",
            "title": "废标红线与关键标星条款响应率核验",
            "category": "matrix",
            "default_severity": "blocker",
            "can_disable": False,
            "description": "废标红线与★关键条款必须100%确认响应并映射有效章节编写正文，未响应直接阻断定稿与递交导出。",
        },
        {
            "rule_id": "R34",
            "title": "占位符与“待补/待完善”残留字样核验",
            "category": "content_integrity",
            "default_severity": "blocking",
            "can_disable": False,
            "description": "排查正文与条款响应中的【待补】、TODO占位符、未替换变量模板及AI遗留对话，禁止带草稿瑕疵导出。",
        },
        {
            "rule_id": "R37",
            "title": "技术/商务偏离表一致性核验",
            "category": "deviation",
            "default_severity": "blocker",
            "can_disable": False,
            "description": "技术与商务条款偏离表与响应矩阵严格一致性校验；关键条款负偏离强阻断，正偏离与无偏离前后一致。",
        },
    ]

    # R34 敏感占位符与残留模式
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
        re.compile(r"\b(?:TODO|TBD|FIXME|XXX)\b", re.IGNORECASE),
        re.compile(r"\{\{(?!(?:fact|sla):)[^}]+\}\}"),  # 未替换的模板 Handlebars 变量（排除合法变量标记 {{fact:...}} 与 {{sla:...}}）
        re.compile(r"\$\{(?!(?:fact|sla):)[^}]+\}"),
    ]

    AI_CONVERSATION_RESIDUALS = [
        "希望对你有帮助",
        "作为AI语言模型",
        "作为人工智能模型",
        "以下是为您生成的",
        "如需进一步修改",
        "希望以上方案能满足",
        "如果还有其他需要补充",
    ]

    @classmethod
    def check_r15(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
    ) -> ComplianceRuleResult:
        """
        R15：证明材料齐全性核验。
        检查证明类要求是否有已生效且在保质期内的资质/业绩证据挂接。
        """
        issues: list[ComplianceRuleIssue] = []
        requirements = workflow.get("requirements", {})
        checked_count = 0
        missing_count = 0
        expired_count = 0

        today = (
            datetime.fromtimestamp(now_ts, SHANGHAI).date()
            if now_ts
            else datetime.now(SHANGHAI).date()
        )

        for req in requirements.values():
            if volume != "all" and req.get("volume") != volume:
                continue

            # 判定是否为证明类要求
            text = str(req.get("text", "") or "")
            need_evidence = bool(
                req.get("need_evidence") is True
                or any(w in text for w in ("资质", "证书", "证明", "业绩", "授权", "合同", "认证", "发票", "财务", "纳税", "社保"))
            )
            if not need_evidence:
                continue

            checked_count += 1
            is_crit = is_critical_requirement(req)
            sev: Literal["blocker", "blocking"] = "blocker" if is_crit else "blocking"
            evidence_ids = req.get("evidence_ids") or []

            # 1. 证据缺失校验
            if not evidence_ids:
                missing_count += 1
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R15",
                        code="EVIDENCE_MISSING",
                        severity=sev,
                        message=f"证明类条款缺少已确认的企业证据挂接：{text[:50]}",
                        requirement_id=req.get("id"),
                        details={"is_critical": is_crit, "volume": req.get("volume")},
                    )
                )
                continue

            # 2. 挂接证据有效性与保质期校验
            for eid in evidence_ids:
                evidence = state.library.get(eid)
                if evidence is None or evidence.get("company_id") != project.company_id:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R15",
                            code="EVIDENCE_NOT_USABLE",
                            severity=sev,
                            message="条款引用的证明材料不存在或属于其他公司空间",
                            requirement_id=req.get("id"),
                            evidence_id=eid,
                            details={"reason": "cross_company_or_missing"},
                        )
                    )
                    continue

                if evidence.get("status") != "confirmed":
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R15",
                            code="EVIDENCE_NOT_USABLE",
                            severity=sev,
                            message=f"条款引用的证明材料尚未确认（状态：{evidence.get('status')}）",
                            requirement_id=req.get("id"),
                            evidence_id=eid,
                            details={"evidence_name": evidence.get("name")},
                        )
                    )
                    continue

                if evidence.get("type") == "history":
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R15",
                            code="EVIDENCE_NOT_USABLE",
                            severity=sev,
                            message="历史参考资料仅供内部查阅，禁止作为正式投标证明材料引用",
                            requirement_id=req.get("id"),
                            evidence_id=eid,
                            details={"type": "history"},
                        )
                    )
                    continue

                # 有效期校验
                if evidence_expired(evidence, project.deadline, today=today):
                    expired_count += 1
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R15",
                            code="EVIDENCE_EXPIRED",
                            severity=sev,
                            message=f"证明材料有效期（{evidence.get('valid_until') or evidence.get('valid_to')}）无法覆盖投标截止日",
                            requirement_id=req.get("id"),
                            evidence_id=eid,
                            details={"evidence_name": evidence.get("name"), "deadline": project.deadline},
                        )
                    )

        passed = len(issues) == 0
        overall_severity: Literal["blocker", "blocking", "warning", "info"] = (
            "blocker"
            if any(i.severity == "blocker" for i in issues)
            else ("blocking" if issues else "info")
        )

        if passed:
            summary = f"共核验 {checked_count} 条证明类要求，全部已挂接有效且在保质期内的证明材料。"
            suggestion = "证明材料完备，符合PRD R15齐全性门禁要求。"
        else:
            summary = f"共核验 {checked_count} 条证明类要求，发现 {len(issues)} 处材料缺失或失效缺陷（缺失 {missing_count} 项，过期 {expired_count} 项）。"
            suggestion = "请在企业资料库中核实并挂接有效资质证书、业绩合同或认证文件，确保有效期覆盖投标截止日。"

        return ComplianceRuleResult(
            rule_id="R15",
            title="证明材料齐全性核验",
            severity=overall_severity,
            passed=passed,
            finding_summary=summary,
            suggestion=suggestion,
            issues=[i.to_dict() for i in issues],
            details={"checked_requirements": checked_count, "missing_count": missing_count, "expired_count": expired_count},
        )

    @classmethod
    def check_r23(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all"
    ) -> ComplianceRuleResult:
        """
        R23：废标红线与关键标星条款响应率核验。
        100% 覆盖与非空确认，未响应则 blocker。
        """
        issues: list[ComplianceRuleIssue] = []
        requirements = workflow.get("requirements", {})
        total_critical = 0

        for req in requirements.values():
            if volume != "all" and req.get("volume") != volume:
                continue

            if not is_critical_requirement(req):
                continue

            total_critical += 1
            text = str(req.get("text", "") or "")
            req_id = req.get("id")

            # 1. 状态必须已确认（不能为 pending 或 rejected）
            if req.get("status") == "pending":
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R23",
                        code="REQUIREMENT_PENDING",
                        severity="blocker",
                        message=f"废标红线/标星条款尚未确认响应：{text[:50]}",
                        requirement_id=req_id,
                        details={"category": req.get("category"), "status": req.get("status")},
                    )
                )
            elif req.get("status") == "rejected":
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R23",
                        code="CRITICAL_REQUIREMENT_REJECTED",
                        severity="blocker",
                        message=f"废标红线与标星条款绝对禁止忽略或标记为不适用：{text[:50]}",
                        requirement_id=req_id,
                        details={"category": req.get("category"), "status": req.get("status")},
                    )
                )

            # 2. 必须映射到本分册有效章节
            chapter_id = req.get("chapter_id")
            chapter = state.chapters.get(chapter_id) if chapter_id else None
            if chapter is None or chapter.project_id != project.id or chapter.volume != req.get("volume"):
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R23",
                        code="MATRIX_MAPPING_MISSING",
                        severity="blocker",
                        message=f"废标/标星条款未映射到本分册有效章节：{text[:50]}",
                        requirement_id=req_id,
                        details={"mapped_chapter_id": chapter_id},
                    )
                )

            # 3. 条款响应必须非空且不得含待补
            resp = str(req.get("response", "") or "").strip()
            if not resp:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R23",
                        code="MATRIX_RESPONSE_MISSING",
                        severity="blocker",
                        message=f"废标/标星条款响应内容为空：{text[:50]}",
                        requirement_id=req_id,
                        details={"response": resp},
                    )
                )
            elif "待补" in resp or "待完善" in resp:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R23",
                        code="CRITICAL_RESPONSE_INVALID",
                        severity="blocker",
                        message=f"废标/标星条款响应内容包含待补瑕疵：{resp[:40]}",
                        requirement_id=req_id,
                        details={"response": resp},
                    )
                )

            # 4. 章节正文校验
            if chapter is not None:
                content = str(chapter.content or "").strip()
                if not content:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R23",
                            code="CHAPTER_CONTENT_EMPTY",
                            severity="blocker",
                            message=f"关键条款映射章节正文为空：{chapter.title}",
                            requirement_id=req_id,
                            chapter_id=chapter.id,
                        )
                    )
                elif "待补" in content:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R23",
                            code="CHAPTER_CONTENT_PENDING",
                            severity="blocker",
                            message=f"关键条款映射章节正文包含待补内容：{chapter.title}",
                            requirement_id=req_id,
                            chapter_id=chapter.id,
                        )
                    )

            # 5. 引用核对状态校验
            if req.get("reference_status") == "unresolved":
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R23",
                        code="REFERENCE_UNRESOLVED",
                        severity="blocker",
                        message=f"关键条款招标文件引用尚未人工核对：{text[:50]}",
                        requirement_id=req_id,
                    )
                )

        passed = len(issues) == 0
        severity: Literal["blocker", "blocking", "warning", "info"] = "blocker" if issues else "info"

        if passed:
            summary = f"共核验 {total_critical} 条废标红线与关键标星条款，100% 确认响应并映射有效章节正文。"
            suggestion = "废标红线与★条款响应率 100%，符合导出合规门禁。"
        else:
            summary = f"共核验 {total_critical} 条废标红线与关键标星条款，发现 {len(issues)} 处阻断缺陷（未响应、未映射或正文待补）。"
            suggestion = "废标红线与★条款必须实现 100% 实质性响应、映射有效章节并完成正文编写，严禁缺漏、忽略或残留待补。"

        return ComplianceRuleResult(
            rule_id="R23",
            title="废标红线与关键标星条款响应率核验",
            severity=severity,
            passed=passed,
            finding_summary=summary,
            suggestion=suggestion,
            issues=[i.to_dict() for i in issues],
            details={"total_critical_requirements": total_critical, "blocker_issues_count": len(issues)},
        )

    @classmethod
    def check_r34(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all"
    ) -> ComplianceRuleResult:
        """
        R34：占位符与“待补/待完善”残留字样核验。
        检测到残留即为 blocking / blocker，禁止带草稿瑕疵导出。
        """
        issues: list[ComplianceRuleIssue] = []

        # 1. 扫描相关章节正文
        chapters = [
            c for c in state.chapters.values()
            if c.project_id == project.id and (volume == "all" or c.volume == volume)
        ]

        for chapter in chapters:
            content = chapter.content or ""
            if not content.strip():
                continue

            # 检查占位符正则
            for pattern in cls.PLACEHOLDER_REGEXES:
                match = pattern.search(content)
                if match:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R34",
                            code="PLACEHOLDER_RESIDUAL",
                            severity="blocking",
                            message=f"章节《{chapter.title}》正文包含占位符或待补字样：'{match.group(0)}'",
                            chapter_id=chapter.id,
                            details={"matched_token": match.group(0), "volume": chapter.volume},
                        )
                    )
                    break

            # 检查 AI 遗留对话残留
            for dialogue in cls.AI_CONVERSATION_RESIDUALS:
                if dialogue in content:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R34",
                            code="AI_CONVERSATION_RESIDUAL",
                            severity="blocking",
                            message=f"章节《{chapter.title}》正文检测到 AI 对话残留语句：'{dialogue}'",
                            chapter_id=chapter.id,
                            details={"dialogue": dialogue, "volume": chapter.volume},
                        )
                    )
                    break

        # 2. 扫描条款响应矩阵
        requirements = workflow.get("requirements", {})
        for req in requirements.values():
            if volume != "all" and req.get("volume") != volume:
                continue

            resp = req.get("response", "") or ""
            is_crit = is_critical_requirement(req)
            sev: Literal["blocker", "blocking"] = "blocker" if is_crit else "blocking"

            for pattern in cls.PLACEHOLDER_REGEXES:
                match = pattern.search(resp)
                if match:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R34",
                            code="PLACEHOLDER_RESIDUAL",
                            severity=sev,
                            message=f"条款响应文本包含占位符或待补标记：'{match.group(0)}'",
                            requirement_id=req.get("id"),
                            details={"matched_token": match.group(0), "is_critical": is_crit},
                        )
                    )
                    break

        passed = len(issues) == 0
        overall_severity: Literal["blocker", "blocking", "warning", "info"] = (
            "blocker"
            if any(i.severity == "blocker" for i in issues)
            else ("blocking" if issues else "info")
        )

        if passed:
            summary = "正文与条款响应中未发现待补、占位符或 AI 对话残留字样。"
            suggestion = "正文内容清洁完整，符合 PRD R34 占位符清零门禁要求。"
        else:
            summary = f"在 {len(issues)} 处正文或条款响应中检测到“待补/占位符/AI残留”字样，导出阻断。"
            suggestion = "请人工清理相关章节正文与条款响应中的【待补】、TODO占位符及AI遗留对话，确保交付文件严谨完整。"

        return ComplianceRuleResult(
            rule_id="R34",
            title="占位符与“待补/待完善”残留字样核验",
            severity=overall_severity,
            passed=passed,
            finding_summary=summary,
            suggestion=suggestion,
            issues=[i.to_dict() for i in issues],
            details={"residual_locations_count": len(issues)},
        )

    @classmethod
    def check_r37(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all"
    ) -> ComplianceRuleResult:
        """
        R37：技术/商务偏离表一致性核验。
        负偏离强阻断，正偏离与无偏离一致性校验。
        """
        issues: list[ComplianceRuleIssue] = []
        requirements = workflow.get("requirements", {})
        total_checked = 0
        negative_deviations = 0
        positive_deviations = 0

        # 获取工作流中显式登记的偏离表字典（如果有）
        deviations_map = workflow.get("deviations", {})

        for req in requirements.values():
            if volume != "all" and req.get("volume") != volume:
                continue

            total_checked += 1
            req_id = req.get("id")
            text = str(req.get("text", "") or "")
            resp = str(req.get("response", "") or "")
            is_crit = is_critical_requirement(req)

            # 偏离类型推断：优先读取字段，次之读取偏离表字典，再次语义推导
            dev_type = req.get("deviation_type")
            if not dev_type and req_id in deviations_map:
                dev_type = deviations_map[req_id].get("type")

            # 归一化为 standard: none, positive, negative
            normalized_type: Literal["none", "positive", "negative"] = "none"
            if dev_type in ("negative", "负偏离"):
                normalized_type = "negative"
            elif dev_type in ("positive", "正偏离"):
                normalized_type = "positive"
            elif dev_type in ("none", "无偏离", "完全满足"):
                normalized_type = "none"
            else:
                # 语义推断
                if any(w in resp for w in ("负偏离", "无法满足", "不满足指标", "存在负偏离")):
                    normalized_type = "negative"
                elif any(w in resp for w in ("正偏离", "优于要求", "高于招标要求", "指标更优")):
                    normalized_type = "positive"
                else:
                    normalized_type = "none"

            # 1. 负偏离强门禁
            if normalized_type == "negative":
                negative_deviations += 1
                if is_crit:
                    # 关键废标/标星条款绝对禁止负偏离！
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R37",
                            code="DEVIATION_NEGATIVE_CRITICAL",
                            severity="blocker",
                            message=f"废标红线与标星关键条款绝对禁止负偏离：{text[:50]}",
                            requirement_id=req_id,
                            details={"is_critical": True, "response": resp},
                        )
                    )
                else:
                    # 一般条款负偏离：缺少书面说明则 blocker，有说明则 blocking
                    explanation = req.get("deviation_reason") or req.get("reason") or ""
                    if not explanation.strip():
                        issues.append(
                            ComplianceRuleIssue(
                                id=new_id("issue"),
                                rule_id="R37",
                                code="DEVIATION_NEGATIVE_UNEXPLAINED",
                                severity="blocker",
                                message=f"条款存在负偏离但缺少审批说明：{text[:50]}",
                                requirement_id=req_id,
                                details={"response": resp},
                            )
                        )
                    else:
                        issues.append(
                            ComplianceRuleIssue(
                                id=new_id("issue"),
                                rule_id="R37",
                                code="DEVIATION_NEGATIVE_EXISTS",
                                severity="blocking",
                                message=f"条款存在负偏离，须由项目负责人专项核准确认方可导出：{text[:50]}",
                                requirement_id=req_id,
                                details={"explanation": explanation, "response": resp},
                            )
                        )

            # 2. 偏离表与响应文本矛盾冲突核验
            if normalized_type == "negative":
                if any(w in resp for w in ("完全满足", "无偏离", "100%满足", "全部满足")):
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R37",
                            code="DEVIATION_CONFLICT",
                            severity="blocker",
                            message="偏离表登记为负偏离，但条款响应文本声称完全满足/无偏离，前后自相矛盾",
                            requirement_id=req_id,
                            details={"deviation_type": "negative", "response": resp},
                        )
                    )
            elif normalized_type == "none":
                if any(w in resp for w in ("负偏离", "无法满足", "不满足")):
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R37",
                            code="DEVIATION_CONFLICT",
                            severity="blocker",
                            message="偏离表登记为无偏离，但条款响应文本表述存在负偏离或无法满足",
                            requirement_id=req_id,
                            details={"deviation_type": "none", "response": resp},
                        )
                    )

            # 3. 正偏离充分性校验
            if normalized_type == "positive":
                positive_deviations += 1
                explanation = req.get("deviation_reason") or req.get("reason") or resp
                if len(explanation.strip()) < 6:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R37",
                            code="DEVIATION_POSITIVE_UNEXPLAINED",
                            severity="warning",
                            message=f"正偏离条款未详细阐述优于招标要求的具体参数或技术指标：{text[:50]}",
                            requirement_id=req_id,
                            details={"explanation": explanation},
                        )
                    )

        passed = len(issues) == 0
        overall_severity: Literal["blocker", "blocking", "warning", "info"] = (
            "blocker"
            if any(i.severity == "blocker" for i in issues)
            else ("blocking" if any(i.severity == "blocking" for i in issues) else ("warning" if issues else "info"))
        )

        if passed:
            summary = f"共核验 {total_checked} 条偏离表与条款矩阵，响应与偏离声明严格一致，无关键负偏离。"
            suggestion = "偏离表一致性核验通过，符合投标偏离管理规范。"
        else:
            summary = f"共核验 {total_checked} 条偏离表与条款矩阵，发现 {len(issues)} 处偏离表矛盾或关键负偏离（负偏离 {negative_deviations} 项，正偏离 {positive_deviations} 项）。"
            suggestion = "关键条款禁止负偏离；请消减负偏离项，修正矛盾偏离表述，并为正偏离项补充实质优越性说明。"

        return ComplianceRuleResult(
            rule_id="R37",
            title="技术/商务偏离表一致性核验",
            severity=overall_severity,
            passed=passed,
            finding_summary=summary,
            suggestion=suggestion,
            issues=[i.to_dict() for i in issues],
            details={
                "total_checked": total_checked,
                "negative_deviations": negative_deviations,
                "positive_deviations": positive_deviations,
            },
        )

    @classmethod
    def evaluate_p0_rules(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
    ) -> list[ComplianceRuleResult]:
        """按顺序完整执行 PRD P0 级合规规则体系。"""
        return [
            cls.check_r15(state, project, workflow, volume=volume, now_ts=now_ts),
            cls.check_r23(state, project, workflow, volume=volume),
            cls.check_r34(state, project, workflow, volume=volume),
            cls.check_r37(state, project, workflow, volume=volume),
        ]


class ComplianceRulesMixin:
    """混入工作流服务，提供合规规则评估与查询能力。"""

    def evaluate_compliance_rules(
        self, principal: Principal, project_id: str, volume: str = "all"
    ) -> dict[str, Any]:
        state = self.repository.read()
        project = self.demo._project(state, principal, project_id)
        workflow = self._workflow(state, project_id)

        # 跨租户强隔离校验
        if project.company_id != principal.user.company_id:
            raise DomainError(404, "NOT_FOUND", "项目不存在或不属于当前企业空间。")

        rule_results = ComplianceRulesEngine.evaluate_p0_rules(
            state, project, workflow, volume=volume, now_ts=self.demo._now()
        )

        all_issues = []
        for r in rule_results:
            all_issues.extend(r.issues)

        has_blockers = any(i.get("severity") == "blocker" for i in all_issues)
        all_passed = all(r.passed for r in rule_results)

        return {
            "project_id": project_id,
            "volume": volume,
            "passed": all_passed,
            "has_blockers": has_blockers,
            "total_rules": len(rule_results),
            "passed_rules": sum(1 for r in rule_results if r.passed),
            "failed_rules": sum(1 for r in rule_results if not r.passed),
            "rules": [r.to_dict() for r in rule_results],
            "issues": all_issues,
            "evaluated_at": iso_time(self.demo._now()),
        }

    def get_compliance_rules_catalog(self) -> list[dict[str, Any]]:
        return ComplianceRulesEngine.CATALOG
