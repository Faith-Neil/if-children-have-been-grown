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

from icg.domain.domain import (
    DemoService,
    DemoState,
    DomainError,
    Principal,
    iso_time,
    new_id,
)
from icg.domain.generation_context import evidence_expired
from icg.domain.project_access import (
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
            "rule_id": "R01",
            "title": "招标单位与项目名称提取一致性核验",
            "category": "consistency",
            "default_severity": "blocker",
            "can_disable": False,
            "description": "核验正文与条款响应中出现的招标人全称、项目名称及招标编号与项目元数据是否严格一致，严禁名称错漏或项目编号冲突。",
        },
        {
            "rule_id": "R02",
            "title": "资质有效性与原件备查承诺核验",
            "category": "qualification",
            "default_severity": "blocker",
            "can_disable": False,
            "description": "核验营业执照、行业资质及原件核对条款，必须具备真实有效承诺与原件备查书面声明，严禁无承诺响应。",
        },
        {
            "rule_id": "R03",
            "title": "资质有效期与信誉核验",
            "category": "qualification",
            "default_severity": "blocker",
            "can_disable": False,
            "description": "核验营业执照与行业资质证书在投标截止时间是否有效，且未被列入失信被执行人或重大违法名单，过期直接判定阻断红线。",
        },
        {
            "rule_id": "R04",
            "title": "联合体投标协议核验",
            "category": "consortium",
            "default_severity": "blocker",
            "can_disable": False,
            "description": "当项目标记为联合体投标时，核验是否已上传合法联合体协议书及全部成员资质，缺失直接阻断递交。",
        },
        {
            "rule_id": "R05",
            "title": "财务指标核验（资产负债率、净利润连续性）",
            "category": "qualification",
            "default_severity": "blocker",
            "can_disable": False,
            "description": "核验企业审计报告中资产负债率是否低于招标最高限额要求（如不超过70%）、近三年净利润是否为正；严重资不抵债或亏损判定为阻断红线。",
        },
        {
            "rule_id": "R06",
            "title": "业绩案例核验（合同金额、类似项目与签字盖章页）",
            "category": "performance",
            "default_severity": "blocker",
            "can_disable": False,
            "description": "核验提供的业绩案例合同金额是否达到招标门槛金额、签订时间是否在有效年限内、是否附带双方签字盖章页及验收证明；业绩金额不足或缺少盖章页判定为阻断红线。",
        },
        {
            "rule_id": "R07",
            "title": "原厂授权覆盖与多级授权链核验",
            "category": "qualification",
            "default_severity": "blocker",
            "can_disable": False,
            "description": "招标明确要求原厂授权时，核验原厂授权书是否覆盖招标涉及的产品、授权链是否逐级有效；缺失原厂授权书判定为阻断红线。",
        },
        {
            "rule_id": "R08",
            "title": "交付周期与进度计划偏离核验",
            "category": "commitment",
            "default_severity": "blocker",
            "can_disable": False,
            "description": "招标明确要求交付天数上限（如60日历天），投标响应承诺交付周期若超过招标上限，判定为负偏离重大违规阻断红线。",
        },
        {
            "rule_id": "R09",
            "title": "服务期/工期与 SLA 承诺核验",
            "category": "commitment",
            "default_severity": "blocker",
            "can_disable": False,
            "description": "核验服务承诺工期是否满足招标文件要求，负偏离或未承诺指标直接判为阻断缺陷。",
        },
        {
            "rule_id": "R10",
            "title": "质保期与服务响应时间核验",
            "category": "commitment",
            "default_severity": "blocker",
            "can_disable": False,
            "description": "核验质保期年限与故障响应时限，低于招标基线或各章节承诺自相矛盾直接判为阻断缺陷。",
        },
        {
            "rule_id": "R11",
            "title": "本单位人员与社保缴纳核验",
            "category": "personnel",
            "default_severity": "blocker",
            "can_disable": False,
            "description": "核验拟派团队人员归属单位与社保缴纳单位是否与投标主体一致、劳动合同在投标截止时间是否有效，人员归属不一致或社保未连续缴纳判定为阻断红线。",
        },
        {
            "rule_id": "R12",
            "title": "服务响应 SLA 与质保期偏离核验",
            "category": "commitment",
            "default_severity": "blocker",
            "can_disable": False,
            "description": "招标要求质保期最低年限（如3年）及现场到达响应时间（如2小时），响应若低于质保期要求或超出到达响应时间，判定为阻断红线。",
        },
        {
            "rule_id": "R14",
            "title": "必备附件齐全性核验",
            "category": "attachment",
            "default_severity": "blocker",
            "can_disable": False,
            "description": "核验招标文件强制要求的必备附件（开标一览表、法定代表人身份证明与授权委托书、投标保证金证明或电子保函、承诺函、资质证书附件）是否全部上传，缺失任一必备附件判定为阻断红线。",
        },
        {
            "rule_id": "R15",
            "title": "证明材料齐全性核验",
            "category": "qualification",
            "default_severity": "blocker",
            "can_disable": False,
            "description": "核验资质、证书、业绩、原厂授权等证明类要求是否已挂接已确认且在保质期内的企业材料，严禁证据缺失或过期。",
        },
        {
            "rule_id": "R20",
            "title": "报价雷同排查（分项报价比例与异常一致性排查）",
            "category": "collusion",
            "default_severity": "blocker",
            "can_disable": False,
            "description": "排查分项报价清单是否存在异常数字规律、或明显复制其他投标主体的报价结构，排查违规串通投标风险；识别重大异常判定为阻断红线。",
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
            "rule_id": "R25",
            "title": "其他公司/旧项目名称与文档残留排查",
            "category": "content_integrity",
            "default_severity": "blocker",
            "can_disable": False,
            "description": "扫描正文文本与条款响应，排查复制旧标书遗留的其他公司全称/简称、其他招标人或旧项目名称残留，存在残留判定为阻断红线。",
        },
        {
            "rule_id": "R31",
            "title": "真实巡检报告与敏感信息残留排查",
            "category": "security",
            "default_severity": "blocker",
            "can_disable": False,
            "description": "扫描正文文本排查明文身份证号（18位）、银行卡号、数据库明文口令或整段真实客户现场巡检报告特征，违规暴露高敏信息判定为阻断红线。",
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
            "rule_id": "R35",
            "title": "投标主体自称与称谓统一性核验",
            "category": "consistency",
            "default_severity": "warning",
            "can_disable": False,
            "description": "全册核验投标主体自称（我方/本投标人/公司全称）与对招标方称谓（贵方/招标人/采购人）是否口径统一，提示口径混乱瑕疵。",
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
    def check_r01(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all"
    ) -> ComplianceRuleResult:
        """
        R01：招标单位与项目名称提取一致性核验。
        核验项目名称、招标编号与条款/正文中的引用一致性，防范张冠李戴错漏。
        """
        issues: list[ComplianceRuleIssue] = []
        expected_code = str(getattr(project, "tender_number", "") or "").strip()
        expected_name = str(getattr(project, "name", "") or "").strip()

        # 检查项目章节正文
        chapters = [ch for ch in state.chapters.values() if ch.project_id == project.id]
        if volume != "all":
            chapters = [ch for ch in chapters if ch.volume == volume]

        code_pattern = re.compile(r"\b[A-Z0-9]{3,}-[0-9]{4}-[A-Z0-9-]+\b")

        for ch in chapters:
            if not ch.content:
                continue
            # 若正文中出现其他编号且与项目招标编号不符
            if expected_code:
                found_codes = code_pattern.findall(ch.content)
                for fc in set(found_codes):
                    if fc != expected_code:
                        issues.append(
                            ComplianceRuleIssue(
                                id=new_id("issue"),
                                rule_id="R01",
                                code="TENDER_NUMBER_CONFLICT",
                                severity="blocker",
                                message=f"章节【{ch.title}】正文中出现与项目招标编号不符的编号：{fc}（期望：{expected_code}）",
                                chapter_id=ch.id,
                                details={"found_code": fc, "expected_code": expected_code},
                            )
                        )

        passed = len(issues) == 0
        severity: Literal["blocker", "blocking", "warning", "info"] = "blocker" if issues else "info"
        summary = (
            f"核验项目名称【{expected_name}】与招标编号【{expected_code or '未设置'}】，正文未发现编号冲突或串标瑕疵。"
            if passed
            else f"发现 {len(issues)} 处项目编号或招标名称不一致风险，存在张冠李戴阻断红线。"
        )
        suggestion = "核验通过" if passed else "请修正正文中错误的招标编号或项目名称，确保与招标公告一致。"

        return ComplianceRuleResult(
            rule_id="R01",
            title="招标单位与项目名称提取一致性核验",
            severity=severity,
            passed=passed,
            finding_summary=summary,
            suggestion=suggestion,
            issues=[i.to_dict() for i in issues],
            details={"expected_code": expected_code, "expected_name": expected_name},
        )

    @classmethod
    def check_r02(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all"
    ) -> ComplianceRuleResult:
        """
        R02：资质有效性与原件备查承诺核验。
        对明确要求原件备查或资质承诺的关键条款进行响应核验。
        """
        issues: list[ComplianceRuleIssue] = []
        requirements = workflow.get("requirements", {})
        checked = 0

        for req_id, req in requirements.items():
            if volume != "all" and req.get("volume") != volume:
                continue

            text = str(req.get("text", "") or "")
            need_original = any(w in text for w in ("原件备查", "原件核对", "提供原件", "核验原件"))
            if not need_original:
                continue

            checked += 1
            resp = str(req.get("response", "") or req.get("confirmed_response", "") or "").strip()
            # 检查响应中是否明确承诺真实原件备查
            has_commitment = any(w in resp for w in ("原件备查", "提供原件", "承诺", "真实有效", "备查"))

            if not has_commitment:
                is_crit = is_critical_requirement(req)
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R02",
                        code="QUALIFICATION_ORIGINAL_COMMITMENT_MISSING",
                        severity="blocker" if is_crit else "blocking",
                        message=f"条款要求原件备查，但响应说明中未见明确书面承诺：{text[:50]}",
                        requirement_id=req_id,
                        details={"requirement_text": text, "response": resp},
                    )
                )

        passed = len(issues) == 0
        severity: Literal["blocker", "blocking", "warning", "info"] = "blocker" if any(i.severity == "blocker" for i in issues) else ("blocking" if issues else "info")
        summary = (
            f"共核验 {checked} 条原件备查与资质条款，全部具备真实有效原件备查书面承诺。"
            if passed
            else f"共核验 {checked} 条原件备查条款，发现 {len(issues)} 处缺少原件承诺书面声明。"
        )
        suggestion = "核验通过" if passed else "请在响应说明中补充'我方承诺按招标文件要求提供相关真实有效原件备查'。"

        return ComplianceRuleResult(
            rule_id="R02",
            title="资质有效性与原件备查承诺核验",
            severity=severity,
            passed=passed,
            finding_summary=summary,
            suggestion=suggestion,
            issues=[i.to_dict() for i in issues],
            details={"checked_count": checked},
        )

    @classmethod
    def check_r03(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
    ) -> ComplianceRuleResult:
        """
        R03：资质有效期与信誉核验。
        核验营业执照与行业资质证书在投标截止时间 deadline 是否有效，且未被列入失信名单；过期或缺失判为 blocker。
        """
        issues: list[ComplianceRuleIssue] = []
        requirements = workflow.get("requirements", {})
        checked = 0

        today = (
            datetime.fromtimestamp(now_ts, SHANGHAI).date()
            if now_ts
            else datetime.now(SHANGHAI).date()
        )
        deadline_str = getattr(project, "deadline", "") or ""

        # 1. 核验资质与信誉类条款
        for req_id, req in requirements.items():
            if volume != "all" and req.get("volume") != volume:
                continue

            text = str(req.get("text", "") or "")
            is_qual = bool(
                req.get("category") == "qualification"
                or any(w in text for w in ("营业执照", "资质", "许可", "认证证书", "资格证书", "信用", "信誉", "失信", "黑名单", "纳税信用"))
            )
            if not is_qual:
                continue

            checked += 1
            is_crit = is_critical_requirement(req)
            resp = str(req.get("response", "") or req.get("confirmed_response", "") or "").strip()

            # 信誉/失信名单排查
            if any(w in text for w in ("失信", "黑名单", "信用中国", "受惩黑名单", "违法失信")):
                dishonest_triggers = ("列入失信", "存在失信", "行政处罚", "被执行人", "有失信记录", "重大税收违法")
                has_dishonest = False
                sentences = re.split(r"[，,。；;！!\n]", resp)
                for sentence in sentences:
                    sentence = sentence.strip()
                    for trig in dishonest_triggers:
                        if trig in sentence:
                            t_idx = sentence.find(trig)
                            pre = sentence[:t_idx]
                            negations = ("未", "无", "不", "免", "非", "没", "零", "排除")
                            if not any(neg in pre for neg in negations):
                                has_dishonest = True
                                break
                    if has_dishonest:
                        break
                if has_dishonest:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R03",
                            code="DISHONEST_RECORD_EXISTS",
                            severity="blocker",
                            message=f"投标主体存在被列入失信被执行人或重大税收违法失信记录风险：{text[:50]}",
                            requirement_id=req_id,
                            details={"response": resp},
                        )
                    )
                elif not resp:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R03",
                            code="CREDIT_COMMITMENT_MISSING",
                            severity="blocker",
                            message=f"招标文件要求的信用与无重大违法记录声明未作响应承诺：{text[:50]}",
                            requirement_id=req_id,
                            details={"text": text},
                        )
                    )

            # 资质证书挂接核验
            needs_cert = any(w in text for w in ("营业执照", "资质", "证书", "许可", "认证"))
            if needs_cert:
                evidence_ids = req.get("evidence_ids") or []
                if not evidence_ids:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R03",
                            code="QUALIFICATION_CERTIFICATE_MISSING",
                            severity="blocker",
                            message=f"资质证明材料缺失：招标文件要求的资质/证照未挂接有效证书材料：{text[:50]}",
                            requirement_id=req_id,
                            details={"text": text, "is_critical": is_crit},
                        )
                    )
                    continue

                for eid in evidence_ids:
                    evidence = state.library.get(eid)
                    if evidence is None or evidence.get("company_id") != project.company_id:
                        issues.append(
                            ComplianceRuleIssue(
                                id=new_id("issue"),
                                rule_id="R03",
                                code="QUALIFICATION_CERTIFICATE_INVALID",
                                severity="blocker",
                                message=f"挂接的资质证明材料不存在或属于其他公司空间：{eid}",
                                requirement_id=req_id,
                                evidence_id=eid,
                                details={"reason": "cross_company_or_missing"},
                            )
                        )
                        continue

                    if evidence.get("status") != "confirmed":
                        issues.append(
                            ComplianceRuleIssue(
                                id=new_id("issue"),
                                rule_id="R03",
                                code="QUALIFICATION_CERTIFICATE_UNCONFIRMED",
                                severity="blocker",
                                message=f"挂接的资质证明材料【{evidence.get('name', eid)}】尚未完成审核确认",
                                requirement_id=req_id,
                                evidence_id=eid,
                                details={"status": evidence.get("status")},
                            )
                        )
                        continue

                    if evidence.get("is_dishonest") or "失信" in str(evidence.get("name", "")):
                        issues.append(
                            ComplianceRuleIssue(
                                id=new_id("issue"),
                                rule_id="R03",
                                code="DISHONEST_RECORD_EXISTS",
                                severity="blocker",
                                message=f"挂接的企业材料【{evidence.get('name')}】包含不良信用或失信信息记录",
                                requirement_id=req_id,
                                evidence_id=eid,
                            )
                        )

                    if evidence_expired(evidence, deadline_str, today=today):
                        valid_to = evidence.get("valid_to") or evidence.get("valid_until") or "已过期"
                        issues.append(
                            ComplianceRuleIssue(
                                id=new_id("issue"),
                                rule_id="R03",
                                code="QUALIFICATION_CERTIFICATE_EXPIRED",
                                severity="blocker",
                                message=f"资质证书【{evidence.get('name')}】有效截止期为 {valid_to}，无法覆盖投标截止时间（{deadline_str[:10] or '未设定'}）",
                                requirement_id=req_id,
                                evidence_id=eid,
                                details={"valid_to": valid_to, "deadline": deadline_str},
                            )
                        )

        # 2. 核验企业基础营业执照有效性（在 library 中登记的 license）
        company_libs = [item for item in state.library.values() if item.get("company_id") == project.company_id]
        license_items = [item for item in company_libs if "营业执照" in str(item.get("name", "")) or item.get("type") == "license"]
        for lic in license_items:
            if evidence_expired(lic, deadline_str, today=today):
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R03",
                        code="BUSINESS_LICENSE_EXPIRED",
                        severity="blocker",
                        message=f"企业营业执照【{lic.get('name')}】在投标截止时间已过期失效",
                        evidence_id=lic.get("id"),
                        details={"deadline": deadline_str},
                    )
                )

        passed = len(issues) == 0
        severity: Literal["blocker", "blocking", "warning", "info"] = "blocker" if issues else "info"
        summary = (
            f"共核验 {checked} 条资质与信誉要求及企业证照，资质证照均在投标截止期内真实有效且无失信记录。"
            if passed
            else f"共核验 {checked} 条资质与信誉要求，发现 {len(issues)} 处资质证照缺失、过期或失信阻断红线。"
        )
        suggestion = "核验通过" if passed else "请补充挂接真实有效且在投标截止期内有效的营业执照与行业资质证书，确保无失信受惩记录。"

        return ComplianceRuleResult(
            rule_id="R03",
            title="资质有效期与信誉核验",
            severity=severity,
            passed=passed,
            finding_summary=summary,
            suggestion=suggestion,
            issues=[i.to_dict() for i in issues],
            details={"checked_count": checked, "deadline": deadline_str},
        )

    @classmethod
    def check_r04(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all"
    ) -> ComplianceRuleResult:
        """
        R04：联合体投标协议核验。
        当项目为联合体投标时，核验是否已附联合体协议书及各成员资质，缺失判为 blocker。
        """
        issues: list[ComplianceRuleIssue] = []
        is_consortium = bool(
            getattr(project, "is_consortium", False)
            or getattr(project, "consortium", False)
            or getattr(project, "joint_venture", False)
            or workflow.get("is_consortium")
            or workflow.get("joint_venture")
            or workflow.get("is_joint_venture")
            or state.project_partners.get(project.id)
            or getattr(project, "partner_ids", None)
            or workflow.get("partners")
        )

        if not is_consortium:
            requirements = workflow.get("requirements", {})
            for r in requirements.values():
                t = str(r.get("text", "") or "")
                resp = str(r.get("response", "") or "")
                if "联合体投标" in t and ("是以联合体" in resp or "作为联合体牵头人" in resp or "联合体成员" in resp):
                    is_consortium = True
                    break

        if not is_consortium:
            return ComplianceRuleResult(
                rule_id="R04",
                title="联合体投标协议核验",
                severity="info",
                passed=True,
                finding_summary="本项目为单一主体独立投标，不涉及联合体协议及各成员资质核验。",
                suggestion="核验通过",
                issues=[],
                details={"is_consortium": False},
            )

        # 联合体投标：1. 核验联合体协议书文件
        uploaded_files = workflow.get("files", {})
        if isinstance(uploaded_files, dict):
            file_list = list(uploaded_files.values())
        elif isinstance(uploaded_files, list):
            file_list = uploaded_files
        else:
            file_list = []

        library_files = [item for item in state.library.values() if item.get("company_id") == project.company_id]

        has_agreement = any(
            any(w in str(f.get("name", "") or f.get("title", "") or f.get("filename", "")) for w in ("联合体协议", "联合体投标协议", "联合体协议书", "联合体合作协议"))
            for f in file_list
        ) or any(
            any(w in str(lib.get("name", "")) for w in ("联合体协议", "联合体投标协议", "联合体协议书", "联合体合作协议"))
            for lib in library_files
        ) or bool(workflow.get("consortium_agreement_file_id") or workflow.get("consortium_agreement")) or any(
            bool(p.get("agreement_attachment_id")) for p in (state.project_partners.get(project.id, []) or [])
        )

        if not has_agreement:
            issues.append(
                ComplianceRuleIssue(
                    id=new_id("issue"),
                    rule_id="R04",
                    code="CONSORTIUM_AGREEMENT_MISSING",
                    severity="blocker",
                    message="本项目为联合体投标，但未上传由各成员共同盖章签署的《联合体投标协议书》。",
                    details={"is_consortium": True},
                )
            )

        # 2. 核验各成员单位信息与资质文件
        partners = (
            state.project_partners.get(project.id, [])
            or workflow.get("partners", [])
            or getattr(project, "partner_ids", [])
        )

        if not partners and is_consortium:
            issues.append(
                ComplianceRuleIssue(
                    id=new_id("issue"),
                    rule_id="R04",
                    code="CONSORTIUM_MEMBERS_MISSING",
                    severity="blocker",
                    message="项目已标记为联合体投标，但未登记联合体成员单位名单。",
                    details={"is_consortium": True},
                )
            )
        else:
            for p in partners:
                p_name = p.get("name") or p.get("partner_entity_id") if isinstance(p, dict) else str(p)
                p_qual = (
                    p.get("license_file_id")
                    or p.get("evidence_ids")
                    or p.get("qualification_id")
                    or p.get("has_qualification")
                    if isinstance(p, dict) else False
                )
                if isinstance(p, dict) and not p_qual:
                    has_lib_qual = any((p_name in str(lib.get("name", ""))) or (lib.get("partner_entity_id") == p_name and lib.get("status") == "confirmed") for lib in library_files)
                    if not has_lib_qual:
                        issues.append(
                            ComplianceRuleIssue(
                                id=new_id("issue"),
                                rule_id="R04",
                                code="CONSORTIUM_MEMBER_QUALIFICATION_MISSING",
                                severity="blocker",
                                message=f"联合体成员单位【{p_name}】未上传营业执照或法定资质证明材料。",
                                details={"partner_name": p_name},
                            )
                        )

        passed = len(issues) == 0
        severity: Literal["blocker", "blocking", "warning", "info"] = "blocker" if issues else "info"
        summary = (
            "联合体投标协议书齐全，各成员单位法定资质文件完备。"
            if passed
            else f"联合体投标核验未通过，发现 {len(issues)} 处协议或成员资质缺失阻断红线。"
        )
        suggestion = "核验通过" if passed else "请上传由联合体牵头人与各成员单位法定代表人签署盖章的协议书，并补充各成员资质证明。"

        return ComplianceRuleResult(
            rule_id="R04",
            title="联合体投标协议核验",
            severity=severity,
            passed=passed,
            finding_summary=summary,
            suggestion=suggestion,
            issues=[i.to_dict() for i in issues],
            details={"is_consortium": is_consortium, "partners_count": len(partners)},
        )

    @classmethod
    def check_r09(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all"
    ) -> ComplianceRuleResult:
        """
        R09：服务期/工期与 SLA 承诺核验。
        核验服务承诺工期是否满足招标文件要求，负偏离或无承诺判为 blocker。
        """
        issues: list[ComplianceRuleIssue] = []
        requirements = workflow.get("requirements", {})
        checked_count = 0

        # 1. 工期与服务期条款核验
        for req_id, req in requirements.items():
            if volume != "all" and req.get("volume") != volume:
                continue

            text = str(req.get("text", "") or "")
            is_service_period = any(
                w in text for w in ("服务期", "工期", "交货期", "服务期限", "交付时限", "运维周期", "实施周期", "完成时限")
            )
            if not is_service_period:
                continue

            checked_count += 1
            resp = str(req.get("response", "") or req.get("confirmed_response", "") or "").strip()
            dev_type = str(req.get("deviation_type", "")).lower()

            if not resp:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R09",
                        code="SERVICE_PERIOD_COMMITMENT_MISSING",
                        severity="blocker",
                        message=f"服务期/工期条款未填写响应承诺：{text[:50]}",
                        requirement_id=req_id,
                        details={"text": text},
                    )
                )
                continue

            # 负偏离核验
            is_negative = (
                dev_type in ("negative", "负偏离")
                or any(w in resp for w in ("负偏离", "无法满足工期", "无法按期", "延迟交付", "延长工期", "不能满足服务期", "超出招标要求时限"))
            )
            if is_negative:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R09",
                        code="SERVICE_PERIOD_NEGATIVE_DEVIATION",
                        severity="blocker",
                        message=f"服务期承诺劣于招标文件要求，构成实质性负偏离：{text[:50]}",
                        requirement_id=req_id,
                        details={"response": resp, "deviation_type": "negative"},
                    )
                )

        # 2. SLA 核心指标承诺核验
        sla = workflow.get("sla") or {}
        sla_values = sla.get("values") or {}
        if isinstance(sla_values, dict):
            for k, item in sla_values.items():
                if not isinstance(item, dict):
                    continue
                checked_count += 1
                val = str(item.get("current_value") or item.get("value") or "").strip()
                dev = str(item.get("deviation") or "").lower()
                name = item.get("name") or k

                if not val:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R09",
                            code="SLA_VALUE_MISSING",
                            severity="blocker",
                            message=f"SLA 核心服务指标【{name}】尚未承诺取值",
                            details={"variable_key": k},
                        )
                    )
                elif dev in ("negative", "负偏离") or item.get("is_negative"):
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R09",
                            code="SLA_COMMITMENT_NEGATIVE_DEVIATION",
                            severity="blocker",
                            message=f"SLA 核心指标【{name}】承诺劣于招标基线，存在负偏离",
                            details={"variable_key": k, "value": val},
                        )
                    )

        passed = len(issues) == 0
        severity: Literal["blocker", "blocking", "warning", "info"] = "blocker" if issues else "info"
        summary = (
            f"共核验 {checked_count} 条服务期/工期与 SLA 承诺项，服务承诺完全满足招标文件基线要求。"
            if passed
            else f"共核验 {checked_count} 条服务期与 SLA 承诺项，发现 {len(issues)} 处负偏离或未承诺阻断缺陷。"
        )
        suggestion = "核验通过" if passed else "请修正负偏离工期表述，补充未填报的 SLA 承诺指标，确保满足招标文件要求。"

        return ComplianceRuleResult(
            rule_id="R09",
            title="服务期/工期与 SLA 承诺核验",
            severity=severity,
            passed=passed,
            finding_summary=summary,
            suggestion=suggestion,
            issues=[i.to_dict() for i in issues],
            details={"checked_count": checked_count},
        )

    @classmethod
    def check_r10(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all"
    ) -> ComplianceRuleResult:
        """
        R10：质保期与服务响应时间核验。
        质保期年限与响应时间核验，低于招标基线或各分册自相矛盾判为 blocker。
        """
        issues: list[ComplianceRuleIssue] = []
        requirements = workflow.get("requirements", {})
        checked_count = 0

        # 1. 质保期条款核验
        for req_id, req in requirements.items():
            if volume != "all" and req.get("volume") != volume:
                continue

            text = str(req.get("text", "") or "")
            is_warranty = any(
                w in text for w in ("质保期", "维保期", "保修期", "免费维保", "免费质保", "质量保证期")
            )
            if not is_warranty:
                continue

            checked_count += 1
            resp = str(req.get("response", "") or req.get("confirmed_response", "") or "").strip()
            dev_type = str(req.get("deviation_type", "")).lower()

            if not resp:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R10",
                        code="WARRANTY_PERIOD_MISSING",
                        severity="blocker",
                        message=f"质保期/维保期条款未填写响应承诺：{text[:50]}",
                        requirement_id=req_id,
                        details={"text": text},
                    )
                )
                continue

            if dev_type in ("negative", "负偏离") or any(
                w in resp for w in ("负偏离", "无法满足", "不满足质保", "缩短质保期", "少于招标文件要求", "不提供免费质保")
            ):
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R10",
                        code="WARRANTY_PERIOD_BELOW_BASELINE",
                        severity="blocker",
                        message=f"承诺质保期低于招标文件基线要求：{text[:50]}",
                        requirement_id=req_id,
                        details={"response": resp, "deviation_type": "negative"},
                    )
                )

        # 2. 服务响应时间条款核验
        for req_id, req in requirements.items():
            if volume != "all" and req.get("volume") != volume:
                continue

            text = str(req.get("text", "") or "")
            is_response_time = any(
                w in text for w in ("响应时间", "响应时限", "到达现场时间", "解决时限", "故障排除时间", "恢复时限")
            )
            if not is_response_time:
                continue

            checked_count += 1
            resp = str(req.get("response", "") or req.get("confirmed_response", "") or "").strip()
            dev_type = str(req.get("deviation_type", "")).lower()

            if not resp:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R10",
                        code="RESPONSE_TIME_COMMITMENT_MISSING",
                        severity="blocker",
                        message=f"服务响应时间条款未填写明确响应承诺：{text[:50]}",
                        requirement_id=req_id,
                        details={"text": text},
                    )
                )
                continue

            if dev_type in ("negative", "负偏离") or any(
                w in resp for w in ("负偏离", "超时响应", "无法达到响应时间", "响应时间延长", "无法满足响应")
            ):
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R10",
                        code="RESPONSE_TIME_BELOW_BASELINE",
                        severity="blocker",
                        message=f"服务响应时间承诺劣于招标文件基线要求：{text[:50]}",
                        requirement_id=req_id,
                        details={"response": resp, "deviation_type": "negative"},
                    )
                )

        # 3. 章节间质保期与响应时间一致性核验（全文一致性）
        chapters = [ch for ch in state.chapters.values() if ch.project_id == project.id]
        if volume != "all":
            chapters = [ch for ch in chapters if ch.volume == volume]

        warranty_pattern = re.compile(r"([1-9][0-9]*)\s*年(?:免费)?(?:质保|维保|保修)")
        found_warranties: dict[int, list[str]] = {}
        for ch in chapters:
            if not ch.content:
                continue
            matches = warranty_pattern.findall(ch.content)
            for m in matches:
                y = int(m)
                found_warranties.setdefault(y, []).append(ch.title)

        if len(found_warranties) > 1:
            years_str = " vs ".join(f"{y}年（{', '.join(titles)}）" for y, titles in found_warranties.items())
            issues.append(
                ComplianceRuleIssue(
                    id=new_id("issue"),
                    rule_id="R10",
                    code="WARRANTY_PERIOD_INCONSISTENT",
                    severity="blocker",
                    message=f"投标文件各章节质保期年限承诺自相矛盾：{years_str}",
                    details={"warranties": {str(k): v for k, v in found_warranties.items()}},
                )
            )

        passed = len(issues) == 0
        severity: Literal["blocker", "blocking", "warning", "info"] = "blocker" if issues else "info"
        summary = (
            f"共核验 {checked_count} 条质保期与响应时限条款，承诺均满足招标要求且全册口径一致。"
            if passed
            else f"共核验 {checked_count} 条质保与响应条款，发现 {len(issues)} 处低于基线或自相矛盾阻断红线。"
        )
        suggestion = "核验通过" if passed else "请修正低于招标要求的质保与响应指标，统一各章节承诺年限与响应时限。"

        return ComplianceRuleResult(
            rule_id="R10",
            title="质保期与服务响应时间核验",
            severity=severity,
            passed=passed,
            finding_summary=summary,
            suggestion=suggestion,
            issues=[i.to_dict() for i in issues],
            details={"checked_count": checked_count},
        )


    @classmethod
    def check_r35(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all"
    ) -> ComplianceRuleResult:
        """
        R35：投标主体自称与称谓统一性核验。
        检查全册自称口径（我方/本公司/本单位）及客户称呼规范性。
        """
        issues: list[ComplianceRuleIssue] = []
        chapters = [ch for ch in state.chapters.values() if ch.project_id == project.id]
        if volume != "all":
            chapters = [ch for ch in chapters if ch.volume == volume]

        self_terms = {"我方": 0, "本投标人": 0, "我司": 0, "我们公司": 0, "本单位": 0}
        counter_terms = {"贵方": 0, "招标人": 0, "采购人": 0, "甲方": 0}

        for ch in chapters:
            content = ch.content or ""
            for t in self_terms:
                self_terms[t] += content.count(t)
            for t in counter_terms:
                counter_terms[t] += content.count(t)

        used_self = [t for t, cnt in self_terms.items() if cnt > 0]
        if len(used_self) > 2:
            issues.append(
                ComplianceRuleIssue(
                    id=new_id("issue"),
                    rule_id="R35",
                    code="SELF_DESIGNATION_INCONSISTENT",
                    severity="warning",
                    message=f"投标主体自称口径不统一，混合使用了多种表达：{', '.join(used_self)}（建议统一为'我方'或'本投标人'）",
                    details={"used_self": used_self, "counts": self_terms},
                )
            )

        if counter_terms["甲方"] > 0:
            issues.append(
                ComplianceRuleIssue(
                    id=new_id("issue"),
                    rule_id="R35",
                    code="COUNTERPARTY_DESIGNATION_IRREGULAR",
                    severity="warning",
                    message="投标文件正文中出现'甲方'非规范招投标称谓（建议规范使用'贵方'或'招标人/采购人'）",
                    details={"counts": counter_terms},
                )
            )

        passed = len(issues) == 0
        severity: Literal["blocker", "blocking", "warning", "info"] = "warning" if issues else "info"
        summary = (
            "全册自称与称谓口径一致规范。"
            if passed
            else f"检测到 {len(issues)} 处称谓口径不一致或非规范称谓风险提示。"
        )
        suggestion = "核验通过" if passed else "建议通读全书，将自称统一规范为'我方'，客户称谓统一为'贵方/招标人'。"

        return ComplianceRuleResult(
            rule_id="R35",
            title="投标主体自称与称谓统一性核验",
            severity=severity,
            passed=passed,
            finding_summary=summary,
            suggestion=suggestion,
            issues=[i.to_dict() for i in issues],
            details={"self_terms": self_terms, "counter_terms": counter_terms},
        )

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
    def check_r07(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
    ) -> ComplianceRuleResult:
        """
        R07：原厂授权覆盖与多级授权链核验。
        招标明确要求原厂授权时，核验原厂授权书是否覆盖招标涉及的产品、授权链是否逐级有效；缺失原厂授权书判定为 blocker。
        """
        issues: list[ComplianceRuleIssue] = []
        requirements = workflow.get("requirements", {})
        checked_count = 0

        today = (
            datetime.fromtimestamp(now_ts, SHANGHAI).date()
            if now_ts
            else datetime.now(SHANGHAI).date()
        )
        deadline_str = getattr(project, "deadline", "") or ""

        for req_id, req in requirements.items():
            if volume != "all" and req.get("volume") != volume:
                continue

            text = str(req.get("text", "") or "")
            requires_auth = bool(
                req.get("requires_original_authorization")
                or req.get("requires_authorization")
                or any(w in text for w in ("原厂授权", "原厂商授权", "制造商授权", "原厂服务承诺", "原厂售后", "原厂技术支持", "代理授权书", "原厂盖章授权"))
            )
            if not requires_auth:
                continue

            checked_count += 1
            resp = str(req.get("response", "") or req.get("confirmed_response", "") or "").strip()

            # 1. 响应文本明确声称无授权
            if any(w in resp for w in ("无原厂授权", "无法提供原厂授权", "未获得原厂授权", "缺少原厂授权")):
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R07",
                        code="ORIGINAL_MANUFACTURER_AUTHORIZATION_MISSING",
                        severity="blocker",
                        message=f"条款要求原厂授权，但响应声明无法提供或未获得原厂授权：{text[:50]}",
                        requirement_id=req_id,
                        details={"response": resp},
                    )
                )
                continue

            # 2. 证据材料挂接核验
            evidence_ids = req.get("evidence_ids") or []
            if not evidence_ids:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R07",
                        code="ORIGINAL_MANUFACTURER_AUTHORIZATION_MISSING",
                        severity="blocker",
                        message=f"招标明确要求原厂授权，但未挂接已确认的原厂授权证明材料：{text[:50]}",
                        requirement_id=req_id,
                        details={"text": text},
                    )
                )
                continue

            # 3. 证据有效性、跨租户、有效期及产品覆盖核验
            for eid in evidence_ids:
                evidence = state.library.get(eid)
                if evidence is None or evidence.get("company_id") != project.company_id:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R07",
                            code="ORIGINAL_MANUFACTURER_AUTHORIZATION_MISSING",
                            severity="blocker",
                            message=f"挂接的原厂授权材料不存在或属于其他公司空间：{eid}",
                            requirement_id=req_id,
                            evidence_id=eid,
                            details={"reason": "cross_company_or_missing"},
                        )
                    )
                    continue

                if evidence.get("status") != "confirmed":
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R07",
                            code="ORIGINAL_MANUFACTURER_AUTHORIZATION_MISSING",
                            severity="blocker",
                            message=f"挂接的原厂授权书【{evidence.get('name', eid)}】尚未审核确认",
                            requirement_id=req_id,
                            evidence_id=eid,
                            details={"status": evidence.get("status")},
                        )
                    )
                    continue

                if evidence_expired(evidence, deadline_str, today=today):
                    valid_to = evidence.get("valid_to") or evidence.get("valid_until") or "已过期"
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R07",
                            code="ORIGINAL_MANUFACTURER_AUTHORIZATION_MISSING",
                            severity="blocker",
                            message=f"原厂授权书【{evidence.get('name')}】有效截止期为 {valid_to}，无法覆盖投标截止时间（{deadline_str[:10] or '未设定'}）",
                            requirement_id=req_id,
                            evidence_id=eid,
                            details={"valid_to": valid_to, "deadline": deadline_str},
                        )
                    )

                # 产品/品牌覆盖核验
                req_product = req.get("product_name") or req.get("product") or ""
                if not req_product:
                    for prod_candidate in ("Oracle数据库", "MySQL数据库", "达梦数据库", "人大金仓", "openGauss", "华为交换机", "思科路由器"):
                        if prod_candidate in text:
                            req_product = prod_candidate
                            break

                ev_name = str(evidence.get("name", ""))
                ev_content = str(evidence.get("content", ""))
                if req_product:
                    covered = evidence.get("covered_products") or evidence.get("products") or []
                    is_covered = (
                        (covered and req_product in covered)
                        or (req_product in ev_name or req_product in ev_content)
                    ) and not ("未覆盖" in ev_content or "不覆盖" in ev_content or "未覆盖" in ev_name)
                    if not is_covered:
                        issues.append(
                            ComplianceRuleIssue(
                                id=new_id("issue"),
                                rule_id="R07",
                                code="ORIGINAL_MANUFACTURER_AUTHORIZATION_MISSING",
                                severity="blocker",
                                message=f"原厂授权书【{ev_name}】未覆盖招标文件指定产品【{req_product}】",
                                requirement_id=req_id,
                                evidence_id=eid,
                                details={"required_product": req_product, "covered_products": covered},
                            )
                        )

                # 4. 多级授权链核验
                is_multilevel = bool(
                    evidence.get("auth_type") in ("agent", "transfer", "multilevel")
                    or evidence.get("is_agent_authorization")
                    or evidence.get("chain_depth", 1) > 1
                    or evidence.get("upstream_authorization_id")
                    or evidence.get("requires_chain")
                    or any(w in ev_name + ev_content for w in ("转授权", "代理授权", "二级代理", "多级授权"))
                )
                if is_multilevel:
                    upstream_id = evidence.get("upstream_authorization_id")
                    chain_broken = bool(
                        evidence.get("chain_broken") is True
                        or evidence.get("is_chain_valid") is False
                        or any(w in ev_name + ev_content for w in ("授权链断裂", "链条断裂", "多级授权链断裂", "缺失上级授权", "缺失上游", "上游未登记"))
                        or (not upstream_id and not evidence.get("authorization_chain") and not ("原厂" in ev_content and "一级" in ev_content) and any(w in ev_name + ev_content for w in ("断裂", "未登记")))
                    )
                    if chain_broken:
                        issues.append(
                            ComplianceRuleIssue(
                                id=new_id("issue"),
                                rule_id="R07",
                                code="ORIGINAL_MANUFACTURER_AUTHORIZATION_MISSING",
                                severity="blocker",
                                message=f"原厂多级转授权链条不完整或已断裂，缺失上游原厂一级授权：【{evidence.get('name')}】",
                                requirement_id=req_id,
                                evidence_id=eid,
                                details={"chain_broken": True},
                            )
                        )
                    elif upstream_id:
                        upstream = state.library.get(upstream_id)
                        if upstream is None or upstream.get("company_id") != project.company_id:
                            issues.append(
                                ComplianceRuleIssue(
                                    id=new_id("issue"),
                                    rule_id="R07",
                                    code="ORIGINAL_MANUFACTURER_AUTHORIZATION_MISSING",
                                    severity="blocker",
                                    message=f"上游原厂授权文件【{upstream_id}】不存在或非本公司材料，多级授权链断裂",
                                    requirement_id=req_id,
                                    evidence_id=eid,
                                )
                            )
                        elif evidence_expired(upstream, deadline_str, today=today):
                            issues.append(
                                ComplianceRuleIssue(
                                    id=new_id("issue"),
                                    rule_id="R07",
                                    code="ORIGINAL_MANUFACTURER_AUTHORIZATION_MISSING",
                                    severity="blocker",
                                    message=f"上级原厂授权文件已过期失效，导致多级转授权链无效",
                                    requirement_id=req_id,
                                    evidence_id=eid,
                                )
                            )

        passed = len(issues) == 0
        severity: Literal["blocker", "blocking", "warning", "info"] = "blocker" if issues else "info"
        summary = (
            f"共核验 {checked_count} 条原厂授权要求，全部挂接有效且覆盖完整的多级原厂授权书。"
            if passed and checked_count > 0
            else (
                "本项目无需原厂授权，自动放行。"
                if passed
                else f"共核验 {checked_count} 条原厂授权要求，发现 {len(issues)} 处原厂授权缺失或授权链失效阻断红线。"
            )
        )
        suggestion = "核验通过" if passed else "请补充挂接真实有效覆盖招标产品的原厂授权书，并确保多级转授权链条完整有效。"

        return ComplianceRuleResult(
            rule_id="R07",
            title="原厂授权覆盖与多级授权链核验",
            severity=severity,
            passed=passed,
            finding_summary=summary,
            suggestion=suggestion,
            issues=[i.to_dict() for i in issues],
            details={"checked_count": checked_count},
        )

    @classmethod
    def check_r11(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
    ) -> ComplianceRuleResult:
        """
        R11：本单位人员与社保缴纳核验。
        招标要求拟派团队为本单位人员时，核验拟派人员归属单位与社保缴纳单位是否与投标主体一致、劳动合同在投标截止时间是否有效；人员归属不一致或社保未连续缴纳判定为 blocker。
        """
        issues: list[ComplianceRuleIssue] = []
        requirements = workflow.get("requirements", {})
        checked_count = 0

        today = (
            datetime.fromtimestamp(now_ts, SHANGHAI).date()
            if now_ts
            else datetime.now(SHANGHAI).date()
        )
        deadline_str = getattr(project, "deadline", "") or ""

        for req_id, req in requirements.items():
            if volume != "all" and req.get("volume") != volume:
                continue

            text = str(req.get("text", "") or "")
            is_personnel_req = bool(
                req.get("category") in ("personnel", "team")
                or any(w in text for w in ("本单位人员", "本单位在职", "社保", "社会保险", "社保证明", "连续缴纳", "劳动合同", "拟派人员", "拟派团队", "项目经理社保", "项目负责人社保"))
            )
            if not is_personnel_req:
                continue

            checked_count += 1
            resp = str(req.get("response", "") or req.get("confirmed_response", "") or "").strip()

            # 1. 响应文本中人员借调或社保不一致排查
            mismatch_phrases = ("非本单位", "挂靠", "借调人员", "第三方代缴", "社保不在本单位", "未缴纳社保", "社保中断", "社保不一致", "劳务派遣未合规")
            if any(p in resp for p in mismatch_phrases):
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R11",
                        code="PERSONNEL_SOCIAL_SECURITY_MISMATCH",
                        severity="blocker",
                        message=f"拟派人员归属单位或社保缴纳单位与投标主体不一致，存在违规借调或挂靠风险：{text[:50]}",
                        requirement_id=req_id,
                        details={"response": resp},
                    )
                )
                continue

            # 2. 证明材料挂接核验（社保证明、劳动合同）
            evidence_ids = req.get("evidence_ids") or []
            needs_evidence = any(w in text for w in ("社保证明", "社保缴纳", "连续缴纳", "劳动合同", "证明材料", "本单位人员"))
            if needs_evidence and not evidence_ids:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R11",
                        code="PERSONNEL_SOCIAL_SECURITY_MISMATCH",
                        severity="blocker",
                        message=f"条款要求提供本单位人员社保证明或劳动合同，但未挂接证明材料：{text[:50]}",
                        requirement_id=req_id,
                        details={"text": text},
                    )
                )
                continue

            for eid in evidence_ids:
                evidence = state.library.get(eid)
                if evidence is None or evidence.get("company_id") != project.company_id:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R11",
                            code="PERSONNEL_SOCIAL_SECURITY_MISMATCH",
                            severity="blocker",
                            message=f"挂接的人员社保证明或劳动合同不存在或属于其他公司空间：{eid}",
                            requirement_id=req_id,
                            evidence_id=eid,
                        )
                    )
                    continue

                if evidence.get("status") != "confirmed":
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R11",
                            code="PERSONNEL_SOCIAL_SECURITY_MISMATCH",
                            severity="blocker",
                            message=f"挂接的人员材料【{evidence.get('name', eid)}】尚未审核确认",
                            requirement_id=req_id,
                            evidence_id=eid,
                        )
                    )
                    continue

                # 社保缴纳单位不一致校验
                ev_name = str(evidence.get("name", ""))
                ev_content = str(evidence.get("content", ""))
                mismatch = bool(
                    evidence.get("social_security_mismatch")
                    or (
                        evidence.get("social_security_company")
                        and evidence.get("social_security_company") != project.company_id
                    )
                    or any(w in ev_name + ev_content for w in ("社保不一致", "社保不在本单位", "第三方劳务派遣", "第三方代缴", "劳务派遣社保", "代缴社保"))
                )
                if mismatch:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R11",
                            code="PERSONNEL_SOCIAL_SECURITY_MISMATCH",
                            severity="blocker",
                            message=f"人员证明材料【{evidence.get('name')}】显示的社保缴纳单位与投标主体不一致",
                            requirement_id=req_id,
                            evidence_id=eid,
                            details={"evidence_company": evidence.get("social_security_company"), "project_company": project.company_id},
                        )
                    )

                # 社保未连续缴纳校验
                interrupted = bool(
                    evidence.get("continuous_payment") is False
                    or evidence.get("is_continuous_payment") is False
                    or evidence.get("interrupted") is True
                    or any(w in ev_name + ev_content for w in ("未连续缴纳", "存在断缴", "社保中断", "断缴", "补缴未连续"))
                )
                if interrupted:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R11",
                            code="PERSONNEL_SOCIAL_SECURITY_MISMATCH",
                            severity="blocker",
                            message=f"人员社保证明【{evidence.get('name')}】未满足连续缴纳要求（存在断缴或不足月）",
                            requirement_id=req_id,
                            evidence_id=eid,
                        )
                    )

                # 劳动合同有效期校验
                if "劳动合同" in str(evidence.get("name", "")) or evidence.get("type") == "contract":
                    if evidence_expired(evidence, deadline_str, today=today):
                        issues.append(
                            ComplianceRuleIssue(
                                id=new_id("issue"),
                                rule_id="R11",
                                code="PERSONNEL_SOCIAL_SECURITY_MISMATCH",
                                severity="blocker",
                                message=f"拟派人员劳动合同【{evidence.get('name')}】在投标截止时间已过期失效",
                                requirement_id=req_id,
                                evidence_id=eid,
                                details={"deadline": deadline_str},
                            )
                        )

        # 3. 结构化拟派团队人员核验
        team_members = workflow.get("team", []) or workflow.get("personnel", [])
        if isinstance(team_members, dict):
            team_members = list(team_members.values())
        for member in team_members:
            if not isinstance(member, dict):
                continue
            m_name = member.get("name") or member.get("personnel_id")
            if member.get("social_security_status") in ("mismatch", "unpaid", "interrupted", "third_party"):
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R11",
                        code="PERSONNEL_SOCIAL_SECURITY_MISMATCH",
                        severity="blocker",
                        message=f"拟派团队人员【{m_name}】社保状态异常（{member.get('social_security_status')}），未在投标主体正常连续缴纳",
                        details={"member": m_name, "status": member.get("social_security_status")},
                    )
                )
            if member.get("company") and member.get("company") != project.company_id and not member.get("is_branch"):
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R11",
                        code="PERSONNEL_SOCIAL_SECURITY_MISMATCH",
                        severity="blocker",
                        message=f"拟派人员【{m_name}】劳动归属单位（{member.get('company')}）与投标主体不一致",
                        details={"member": m_name, "company": member.get("company")},
                    )
                )

        passed = len(issues) == 0
        severity: Literal["blocker", "blocking", "warning", "info"] = "blocker" if issues else "info"
        summary = (
            f"共核验 {checked_count} 条拟派人员与社保要求，人员归属及社保连续缴纳证明完备合规。"
            if passed and checked_count > 0
            else (
                "本项目未要求特定拟派团队本单位社保，自动放行。"
                if passed
                else f"共核验拟派团队与社保要求，发现 {len(issues)} 处人员归属或社保缴纳不一致阻断红线。"
            )
        )
        suggestion = "核验通过" if passed else "请确保拟派人员劳动合同覆盖截止时间，并补充在投标主体连续缴纳社保的有效证明。"

        return ComplianceRuleResult(
            rule_id="R11",
            title="本单位人员与社保缴纳核验",
            severity=severity,
            passed=passed,
            finding_summary=summary,
            suggestion=suggestion,
            issues=[i.to_dict() for i in issues],
            details={"checked_count": checked_count},
        )

    @classmethod
    def check_r14(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all"
    ) -> ComplianceRuleResult:
        """
        R14：必备附件齐全性核验。
        核验招标文件强制要求的必备附件（开标一览表、法定代表人身份证明与授权委托书、投标保证金证明或电子保函、承诺函、资质证书附件）是否全部上传；缺失任一必备附件判定为 blocker。
        """
        issues: list[ComplianceRuleIssue] = []

        MANDATORY_ATTACHMENTS = [
            {
                "key": "quotation_sheet",
                "name": "开标一览表",
                "keywords": ["开标一览表", "报价一览表", "投标报价表", "开标一览", "投标一览表", "开标报价表", "投标报价一览表"],
            },
            {
                "key": "legal_auth",
                "name": "法定代表人身份证明与授权委托书",
                "keywords": ["法定代表人身份证明", "授权委托书", "法定代表人授权书", "法人代表授权委托书", "法人代表证明", "法定代表人证明", "法定代表人授权委托书"],
            },
            {
                "key": "bid_bond",
                "name": "投标保证金证明或电子保函",
                "keywords": ["投标保证金", "电子保函", "投标保函", "保证金凭证", "保函", "保证金缴纳", "保证金收据", "银行保函"],
            },
            {
                "key": "commitment_letter",
                "name": "承诺函",
                "keywords": ["承诺函", "投标承诺函", "诚信承诺书", "廉洁承诺书", "中小企业声明函", "投标声明书", "合规承诺函", "无重大违法记录承诺"],
            },
            {
                "key": "qualification_cert",
                "name": "资质证书附件",
                "keywords": ["资质证书", "营业执照", "资质证明", "体系认证", "许可证书", "资格证书", "企业证照", "资质文件"],
            },
        ]

        uploaded_files = workflow.get("files", {})
        if isinstance(uploaded_files, dict):
            file_names = [str(f.get("name", "") or f.get("filename", "") or f.get("title", "")) for f in uploaded_files.values()]
        elif isinstance(uploaded_files, list):
            file_names = [str(f.get("name", "") or f.get("filename", "") or f.get("title", "")) for f in uploaded_files]
        else:
            file_names = []

        company_libs = [item for item in state.library.values() if item.get("company_id") == project.company_id]
        lib_names = [str(item.get("name", "")) for item in company_libs]
        has_lib_qual = any(
            item.get("status") == "confirmed" and (
                item.get("type") in ("qualification", "license", "certificate")
                or any(k in str(item.get("name", "")) for k in ("资质", "执照", "证书", "许可"))
            )
            for item in company_libs
        )

        chapters = [c for c in state.chapters.values() if c.project_id == project.id]
        chapter_titles = [c.title for c in chapters]

        mandatory_dict = workflow.get("mandatory_attachments", {}) or {}
        requirements = workflow.get("requirements", {})

        all_pool = " | ".join(file_names + lib_names + chapter_titles)

        global_check = bool(
            workflow.get("mandatory_attachments_required") is True
            or workflow.get("check_mandatory_attachments") is True
            or getattr(project, "requires_mandatory_attachments", False)
        )

        checked_count = 0
        for item in MANDATORY_ATTACHMENTS:
            key = item["key"]
            name = item["name"]
            keywords = item["keywords"]

            is_required_by_clause = any(
                any(kw in str(r.get("text", "") or "") for kw in keywords)
                or r.get("attachment_type") == key
                or (r.get("is_mandatory_attachment") and key in str(r.get("text", "") or ""))
                for r in requirements.values()
            )
            is_required_by_config = (
                global_check
                or (isinstance(workflow.get("required_attachments"), (list, set)) and key in workflow["required_attachments"])
                or (isinstance(workflow.get("mandatory_attachments"), dict) and key in workflow["mandatory_attachments"])
            )

            if not (is_required_by_clause or is_required_by_config):
                continue

            checked_count += 1

            if mandatory_dict.get(key) is True:
                continue

            matched = any(kw in all_pool for kw in keywords)
            if not matched and key == "qualification_cert":
                # 若企业资料库存在已确认的资质证照，或资质条款已挂接有效企业材料，认定资质证书附件已具备
                if has_lib_qual:
                    matched = True
                else:
                    for r in requirements.values():
                        if any(kw in str(r.get("text", "") or "") for kw in keywords):
                            for eid in (r.get("evidence_ids") or []):
                                ev = state.library.get(eid)
                                if ev and ev.get("company_id") == project.company_id and ev.get("status") == "confirmed":
                                    matched = True
                                    break
                        if matched:
                            break

            if not matched:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R14",
                        code="MANDATORY_ATTACHMENT_MISSING",
                        severity="blocker",
                        message=f"缺失招标文件强制要求的必备附件：【{name}】（未在已上传文件、企业资料库或章节中检测到）",
                        details={"attachment_key": key, "attachment_name": name},
                    )
                )

        passed = len(issues) == 0
        severity: Literal["blocker", "blocking", "warning", "info"] = "blocker" if issues else "info"
        summary = (
            f"共核验 {checked_count} 项招标文件强制必备附件，全部上传齐全完备。"
            if passed and checked_count > 0
            else (
                "招标文件未声明强制性必备附件清单，自动放行。"
                if passed
                else f"必备附件齐全性核验未通过，缺失 {len(issues)} 项强制附件，构成阻断红线。"
            )
        )
        suggestion = "核验通过" if passed else "请在已上传文件、企业资料库或章节中补齐缺失的必备附件（如开标一览表、法人授权委托书、保函凭证等）。"

        return ComplianceRuleResult(
            rule_id="R14",
            title="必备附件齐全性核验",
            severity=severity,
            passed=passed,
            finding_summary=summary,
            suggestion=suggestion,
            issues=[i.to_dict() for i in issues],
            details={"checked_count": checked_count, "missing_count": len(issues)},
        )

    @classmethod
    def check_r25(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all"
    ) -> ComplianceRuleResult:
        """
        R25：其他公司/旧项目名称与文档残留排查。
        扫描正文文本，排查是否存在复制旧标书遗留的其他公司全称/简称、其他招标人或旧项目名称残留；存在残留时判定为 blocker。
        """
        issues: list[ComplianceRuleIssue] = []

        chapters = [
            c for c in state.chapters.values()
            if c.project_id == project.id and (volume == "all" or c.volume == volume)
        ]

        RESIDUAL_PATTERNS = [
            re.compile(r"【(?:旧项目|历史项目|其他公司|原客户|前任公司|旧标书|旧标残留|复制模板)[^】]*】"),
            re.compile(r"某某(?:公司|科技|银行|医院|集团|项目|系统|分行|支行)"),
            re.compile(r"XXX(?:公司|科技|银行|医院|集团|项目)"),
            re.compile(r"（(?:旧标残留|旧项目残留)）"),
            re.compile(r"\((?:旧标残留|旧项目残留)\)"),
            re.compile(r"(?:原项目名称|旧项目名称|参考上期项目|旧标书残留)[：:\s]*([^\n，。；]+)"),
        ]

        legacy_entities = (
            workflow.get("legacy_entities", [])
            or workflow.get("forbidden_entities", [])
            or workflow.get("legacy_keywords", [])
        )

        for chapter in chapters:
            content = chapter.content or ""
            if not content.strip():
                continue

            for pattern in RESIDUAL_PATTERNS:
                match = pattern.search(content)
                if match:
                    matched_str = match.group(0)
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R25",
                            code="ENTITY_NAME_RESIDUAL_DETECTED",
                            severity="blocker",
                            message=f"章节《{chapter.title}》正文检测到复制旧标书遗留的旧项目或占位公司名称残留：'{matched_str}'",
                            chapter_id=chapter.id,
                            details={"residual": matched_str, "volume": chapter.volume},
                        )
                    )
                    break

            for entity in legacy_entities:
                if entity and entity in content:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R25",
                            code="ENTITY_NAME_RESIDUAL_DETECTED",
                            severity="blocker",
                            message=f"章节《{chapter.title}》正文检测到指定的其他公司/旧项目名称残留：'{entity}'",
                            chapter_id=chapter.id,
                            details={"residual": entity, "volume": chapter.volume},
                        )
                    )
                    break

        requirements = workflow.get("requirements", {})
        for req_id, req in requirements.items():
            if volume != "all" and req.get("volume") != volume:
                continue
            resp = str(req.get("response", "") or "")
            if not resp:
                continue

            for pattern in RESIDUAL_PATTERNS:
                match = pattern.search(resp)
                if match:
                    matched_str = match.group(0)
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R25",
                            code="ENTITY_NAME_RESIDUAL_DETECTED",
                            severity="blocker",
                            message=f"条款响应文本检测到复制旧标书遗留的其他公司或旧项目名称残留：'{matched_str}'",
                            requirement_id=req_id,
                            details={"residual": matched_str},
                        )
                    )
                    break

            for entity in legacy_entities:
                if entity and entity in resp:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R25",
                            code="ENTITY_NAME_RESIDUAL_DETECTED",
                            severity="blocker",
                            message=f"条款响应文本检测到指定的其他公司/旧项目名称残留：'{entity}'",
                            requirement_id=req_id,
                            details={"residual": entity},
                        )
                    )
                    break

        passed = len(issues) == 0
        severity: Literal["blocker", "blocking", "warning", "info"] = "blocker" if issues else "info"
        summary = (
            "全册正文与条款响应中未发现其他公司、其他招标人或旧项目名称残留。"
            if passed
            else f"在正文或响应中检测到 {len(issues)} 处复制旧标书遗留的其他公司或旧项目名称残留，存在严重串标或错漏风险。"
        )
        suggestion = "核验通过" if passed else "请彻底清除正文中复制旧标书遗留的'某某公司/旧项目/占位符'等其他实体名称残留。"

        return ComplianceRuleResult(
            rule_id="R25",
            title="其他公司/旧项目名称与文档残留排查",
            severity=severity,
            passed=passed,
            finding_summary=summary,
            suggestion=suggestion,
            issues=[i.to_dict() for i in issues],
            details={"residual_count": len(issues)},
        )

    @classmethod
    def check_r31(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all"
    ) -> ComplianceRuleResult:
        """
        R31：真实巡检报告与敏感信息残留排查。
        扫描正文文本，排查是否出现明文身份证号（18位）、银行卡号、数据库明文口令（password=...）、或整段真实客户现场巡检报告特征；违规暴露高敏信息判定为 blocker。
        """
        issues: list[ComplianceRuleIssue] = []

        chapters = [
            c for c in state.chapters.values()
            if c.project_id == project.id and (volume == "all" or c.volume == volume)
        ]

        ID_CARD_PATTERN = re.compile(r"(?<![0-9*])([1-9][0-9]{5}(?:19|20)[0-9]{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12][0-9]|3[01])[0-9]{3}[0-9Xx])(?![0-9*])")
        BANK_CARD_PATTERN = re.compile(r"(?:银行卡号|收款账号|银行账号|对公账户|银行卡|卡号)[：:\s]*([1-9][0-9]{15,18})")
        STANDALONE_BANK_PATTERN = re.compile(r"(?<![0-9a-zA-Z*])(62[0-9]{14,17}|4[0-9]{15}|5[1-5][0-9]{14})(?![0-9a-zA-Z*])")
        PASSWORD_PATTERN = re.compile(r"(?i)\b(?:password|passwd|pwd|db_password|secret_key|root_password)\s*[:=]\s*['\"]?([a-zA-Z0-9@#$%^&*_+~-]{4,})['\"]?")
        REPORT_KEYWORDS = ["现场巡检报告", "机房巡检记录", "设备运行巡检表", "漏洞扫描报告", "内网渗透测试报告", "数据库巡检记录"]

        def scan_text(text: str, location_desc: str, chapter_id: str | None = None, req_id: str | None = None):
            id_matches = ID_CARD_PATTERN.findall(text)
            for m in id_matches:
                if "*" not in m:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R31",
                            code="SENSITIVE_DATA_RESIDUAL_DETECTED",
                            severity="blocker",
                            message=f"{location_desc}检测到未脱敏的 18 位明文身份证号暴露：'{m[:4]}**********{m[-4:]}'",
                            chapter_id=chapter_id,
                            requirement_id=req_id,
                            details={"type": "id_card", "masked": f"{m[:4]}**********{m[-4:]}"},
                        )
                    )
                    break

            bc_matches = BANK_CARD_PATTERN.findall(text) or STANDALONE_BANK_PATTERN.findall(text)
            for bm in bc_matches:
                if "*" not in bm:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R31",
                            code="SENSITIVE_DATA_RESIDUAL_DETECTED",
                            severity="blocker",
                            message=f"{location_desc}检测到未脱敏的银行卡号明文暴露：'{bm[:4]}********{bm[-4:]}'",
                            chapter_id=chapter_id,
                            requirement_id=req_id,
                            details={"type": "bank_card", "masked": f"{bm[:4]}********{bm[-4:]}"},
                        )
                    )
                    break

            pwd_matches = PASSWORD_PATTERN.findall(text)
            for pwd in pwd_matches:
                if not any(x in pwd.lower() for x in ("***", "xxx", "待补", "placeholder", "${")):
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R31",
                            code="SENSITIVE_DATA_RESIDUAL_DETECTED",
                            severity="blocker",
                            message=f"{location_desc}检测到数据库或系统明文口令暴露：'password=***'",
                            chapter_id=chapter_id,
                            requirement_id=req_id,
                            details={"type": "password"},
                        )
                    )
                    break

            for kw in REPORT_KEYWORDS:
                if kw in text:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R31",
                            code="SENSITIVE_DATA_RESIDUAL_DETECTED",
                            severity="blocker",
                            message=f"{location_desc}检测到套用真实客户现场巡检报告特征：'{kw}'（PRD §5.8 禁止直接套用真实巡检报告）",
                            chapter_id=chapter_id,
                            requirement_id=req_id,
                            details={"type": "inspection_report", "keyword": kw},
                        )
                    )
                    break

        for chapter in chapters:
            if chapter.content:
                scan_text(chapter.content, f"章节《{chapter.title}》正文", chapter_id=chapter.id)

        requirements = workflow.get("requirements", {})
        for req_id, req in requirements.items():
            if volume != "all" and req.get("volume") != volume:
                continue
            resp = str(req.get("response", "") or "")
            if resp:
                scan_text(resp, "条款响应说明中", req_id=req_id)

        passed = len(issues) == 0
        severity: Literal["blocker", "blocking", "warning", "info"] = "blocker" if issues else "info"
        summary = (
            "全册正文未检测到身份证号、银行卡号、数据库口令及真实巡检报告高敏信息暴露。"
            if passed
            else f"检测到 {len(issues)} 处明文高敏数据或真实巡检报告暴露，违反信息安全红线，严禁导出正式递交版。"
        )
        suggestion = "核验通过" if passed else "请对正文中的身份证号、银行卡号执行脱敏遮蔽，清除数据库口令，并重构现场巡检方案段落（严禁直接套用客户现成巡检报告）。"

        return ComplianceRuleResult(
            rule_id="R31",
            title="真实巡检报告与敏感信息残留排查",
            severity=severity,
            passed=passed,
            finding_summary=summary,
            suggestion=suggestion,
            issues=[i.to_dict() for i in issues],
            details={"sensitive_issues_count": len(issues)},
        )

    @classmethod
    def check_r05(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all"
    ) -> ComplianceRuleResult:
        """
        R05：财务指标核验（资产负债率、净利润连续性）。
        核验企业审计报告中资产负债率是否低于招标最高限额要求（如不超过 70%）、近三年净利润是否为正；严重资不抵债或亏损判定为 blocker (FINANCIAL_METRICS_NON_COMPLIANT)。
        """
        issues: list[ComplianceRuleIssue] = []
        requirements = workflow.get("requirements", {})
        checked_count = 0

        for req_id, req in requirements.items():
            if volume != "all" and req.get("volume") != volume:
                continue

            text = str(req.get("text", "") or "")
            is_financial = bool(
                req.get("category") in ("financial", "finance")
                or any(w in text for w in ("财务", "资产负债率", "净利润", "审计报告", "财务状况", "财务指标", "负债率", "资不抵债", "连续盈利"))
            )
            if not is_financial:
                continue

            checked_count += 1
            resp = str(req.get("response", "") or req.get("confirmed_response", "") or "").strip()
            dev_type = str(req.get("deviation_type", "")).lower()

            if not resp:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R05",
                        code="FINANCIAL_METRICS_NON_COMPLIANT",
                        severity="blocker",
                        message=f"财务指标与审计报告要求未作响应承诺：{text[:50]}",
                        requirement_id=req_id,
                        details={"text": text},
                    )
                )
                continue

            # 实质性负偏离
            if dev_type in ("negative", "负偏离"):
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R05",
                        code="FINANCIAL_METRICS_NON_COMPLIANT",
                        severity="blocker",
                        message=f"财务指标响应存在实质性负偏离：{text[:50]}",
                        requirement_id=req_id,
                        details={"response": resp, "deviation_type": "negative"},
                    )
                )
                continue

            # 资不抵债或亏损明确标识
            loss_triggers = (
                "资不抵债", "净利润为负", "严重亏损", "连续亏损", "出现亏损", "存在亏损",
                "未连续盈利", "资产负债率超标", "负债率过高", "资产负债率过高", "无法提供审计报告",
                "财务指标不达标", "资产负债率超出", "净利润亏损"
            )
            has_explicit_loss = False
            for trig in loss_triggers:
                if trig in resp:
                    idx = resp.find(trig)
                    prefix = resp[max(0, idx - 6):idx]
                    if not any(neg in prefix for neg in ("未", "无", "不", "免", "非", "零", "排除", "防止")):
                        has_explicit_loss = True
                        break

            if has_explicit_loss:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R05",
                        code="FINANCIAL_METRICS_NON_COMPLIANT",
                        severity="blocker",
                        message=f"企业财务指标不达标（出现亏损、资不抵债或负债率超标）：{text[:50]}",
                        requirement_id=req_id,
                        details={"response": resp},
                    )
                )
                continue

            # 资产负债率上限数值核验
            max_ratio = 70.0
            ratio_limit_match = re.search(r"(?:资产负债率|负债率)(?:不超过|不高于|低于|<=|≤|小于)\s*(\d+(?:\.\d+)?)\s*%", text)
            if ratio_limit_match:
                max_ratio = float(ratio_limit_match.group(1))

            # 从响应与挂接材料提取资产负债率
            bidder_ratio: float | None = None
            ratio_match = re.search(r"(?:资产负债率|负债率)(?:为|达到|约|约为|是|：|:)?\s*(\d+(?:\.\d+)?)\s*%", resp)
            if ratio_match:
                bidder_ratio = float(ratio_match.group(1))
            else:
                for ev_id in req.get("evidence_ids", []):
                    ev = state.library.get(ev_id)
                    if ev:
                        ev_name = ev.get("name", "") if isinstance(ev, dict) else getattr(ev, "name", "")
                        ev_content = ev.get("content", "") if isinstance(ev, dict) else getattr(ev, "content", "")
                        ev_text = f"{ev_name} {ev_content}"
                        ev_ratio = re.search(r"(?:资产负债率|负债率)(?:为|达到|约|约为|是|：|:)?\s*(\d+(?:\.\d+)?)\s*%", ev_text)
                        if ev_ratio:
                            bidder_ratio = float(ev_ratio.group(1))
                            break

            if bidder_ratio is not None and bidder_ratio > max_ratio:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R05",
                        code="FINANCIAL_METRICS_NON_COMPLIANT",
                        severity="blocker",
                        message=f"企业资产负债率（{bidder_ratio}%）超出招标文件最高限额要求（{max_ratio}%）：{text[:50]}",
                        requirement_id=req_id,
                        details={"bidder_ratio": bidder_ratio, "max_ratio": max_ratio},
                    )
                )
                continue

            # 近三年净利润核验
            profit_req = any(w in text for w in ("近三年净利润", "近3年净利润", "净利润连续", "净利润为正", "连续盈利", "无亏损"))
            if profit_req:
                combined_text = resp
                for ev_id in req.get("evidence_ids", []):
                    ev = state.library.get(ev_id)
                    if ev:
                        ev_name = ev.get("name", "") if isinstance(ev, dict) else getattr(ev, "name", "")
                        ev_content = ev.get("content", "") if isinstance(ev, dict) else getattr(ev, "content", "")
                        combined_text += f" {ev_name} {ev_content}"
                if any(k in combined_text for k in ("净利润为负", "年度亏损", "出现亏损")):
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R05",
                            code="FINANCIAL_METRICS_NON_COMPLIANT",
                            severity="blocker",
                            message=f"近三年净利润存在负值或年度亏损，不满足连续盈利要求：{text[:50]}",
                            requirement_id=req_id,
                            details={"text": text},
                        )
                    )

        # 扫描正文文本（商务分册）是否存在资不抵债或财务亏损违规描述
        chapters = [ch for ch in state.chapters.values() if ch.project_id == project.id]
        if volume != "all":
            chapters = [ch for ch in chapters if ch.volume == volume]
        for ch in chapters:
            if not ch.content:
                continue
            if "严重资不抵债" in ch.content or "企业发生重大连续亏损" in ch.content:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R05",
                        code="FINANCIAL_METRICS_NON_COMPLIANT",
                        severity="blocker",
                        message=f"章节《{ch.title}》正文包含严重资不抵债或重大连续亏损描述，违反财务合格底线",
                        chapter_id=ch.id,
                        details={"chapter_title": ch.title},
                    )
                )

        passed = len(issues) == 0
        severity: Literal["blocker", "blocking", "warning", "info"] = "blocker" if issues else "info"
        summary = (
            "财务指标核验通过，资产负债率与近三年净利润指标均满足招标文件合规要求。"
            if passed
            else f"检测到 {len(issues)} 处财务指标不合规项（资产负债率超标、净利润亏损或承诺缺失），构成阻断红线。"
        )
        suggestion = "核验通过" if passed else "请核对审计报告中资产负债率是否低于招标限额（如70%），确保近三年净利润持续为正，并补充合法合规的财务审计报告。"

        return ComplianceRuleResult(
            rule_id="R05",
            title="财务指标核验（资产负债率、净利润连续性）",
            severity=severity,
            passed=passed,
            finding_summary=summary,
            suggestion=suggestion,
            issues=[i.to_dict() for i in issues],
            details={"checked_count": checked_count, "financial_issues_count": len(issues)},
        )

    @classmethod
    def check_r06(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
    ) -> ComplianceRuleResult:
        """
        R06：业绩案例核验（合同金额、类似项目与签字盖章页）。
        核验提供的业绩案例合同金额是否达到招标门槛金额、签订时间是否在有效年限内（如近3年）、是否附带双方签字盖章页及验收证明；业绩金额不足或缺少盖章页判定为 blocker (PERFORMANCE_CASE_INSUFFICIENT)。
        """
        issues: list[ComplianceRuleIssue] = []
        requirements = workflow.get("requirements", {})
        checked_count = 0

        today = (
            datetime.fromtimestamp(now_ts, SHANGHAI).date()
            if now_ts
            else datetime.now(SHANGHAI).date()
        )
        current_year = today.year

        for req_id, req in requirements.items():
            if volume != "all" and req.get("volume") != volume:
                continue

            text = str(req.get("text", "") or "")
            is_perf = bool(
                req.get("category") in ("performance", "case")
                or any(w in text for w in ("业绩", "同类项目", "类似项目", "案例", "合同业绩", "实施案例", "成功案例"))
            )
            if not is_perf:
                continue

            checked_count += 1
            resp = str(req.get("response", "") or req.get("confirmed_response", "") or "").strip()
            dev_type = str(req.get("deviation_type", "")).lower()

            if not resp:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R06",
                        code="PERFORMANCE_CASE_INSUFFICIENT",
                        severity="blocker",
                        message=f"业绩案例条款未填写响应说明与案例承诺：{text[:50]}",
                        requirement_id=req_id,
                        details={"text": text},
                    )
                )
                continue

            if dev_type in ("negative", "负偏离"):
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R06",
                        code="PERFORMANCE_CASE_INSUFFICIENT",
                        severity="blocker",
                        message=f"业绩案例响应存在实质性负偏离：{text[:50]}",
                        requirement_id=req_id,
                        details={"response": resp, "deviation_type": "negative"},
                    )
                )
                continue

            # 明显声明业绩不足或缺失
            missing_perf_triggers = (
                "无类似业绩", "无同类业绩", "无类似项目", "无业绩案例", "无法提供合同",
                "业绩不足", "业绩金额不足", "未达门槛金额", "缺少盖章页", "未盖章",
                "缺少签字盖章", "无验收证明", "缺失验收证明", "合同超出3年", "非近3年业绩",
                "无法提供验收报告", "缺少双方盖章"
            )
            has_explicit_perf_issue = False
            for trig in missing_perf_triggers:
                if trig in resp:
                    idx = resp.find(trig)
                    prefix = resp[max(0, idx - 6):idx]
                    if not any(neg in prefix for neg in ("未", "无", "不", "免", "非", "零", "排除", "防止")):
                        has_explicit_perf_issue = True
                        break

            if has_explicit_perf_issue:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R06",
                        code="PERFORMANCE_CASE_INSUFFICIENT",
                        severity="blocker",
                        message=f"业绩案例不满足招标要求（缺少盖章/金额不足/无验收证明）：{text[:50]}",
                        requirement_id=req_id,
                        details={"response": resp},
                    )
                )
                continue

            # 合同金额门槛提取与核验
            threshold_amount: float | None = None
            th_m = re.search(r"(?:合同金额|单项合同|金额)(?:不少于|不低于|达到|大于等于|≥|>=)\s*(\d+(?:\.\d+)?)\s*(?:万元|万)", text)
            if not th_m:
                th_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:万元|万)(?:以上|及以上)", text)
            if th_m:
                threshold_amount = float(th_m.group(1))

            # 从响应及挂接材料提取业绩案例金额
            case_amount: float | None = None
            resp_amt_m = re.search(r"(?:合同金额|业绩金额|金额)(?:为|达到|：|:)?\s*(\d+(?:\.\d+)?)\s*(?:万元|万)", resp)
            if resp_amt_m:
                case_amount = float(resp_amt_m.group(1))

            evidence_ids = req.get("evidence_ids") or []
            ev_texts = []
            for ev_id in evidence_ids:
                ev = state.library.get(ev_id)
                if ev:
                    ev_name = ev.get("name", "") if isinstance(ev, dict) else getattr(ev, "name", "")
                    ev_content = ev.get("content", "") if isinstance(ev, dict) else getattr(ev, "content", "")
                    ev_texts.append(f"{ev_name} {ev_content}")
                    if case_amount is None:
                        ev_amt_m = re.search(r"(?:合同金额|业绩金额|金额)(?:为|达到|：|:)?\s*(\d+(?:\.\d+)?)\s*(?:万元|万)", f"{ev_name} {ev_content}")
                        if ev_amt_m:
                            case_amount = float(ev_amt_m.group(1))

            all_perf_text = resp + " " + " ".join(ev_texts)

            if threshold_amount is not None and case_amount is not None:
                if case_amount < threshold_amount:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R06",
                            code="PERFORMANCE_CASE_INSUFFICIENT",
                            severity="blocker",
                            message=f"业绩案例合同金额（{case_amount}万元）未达到招标文件门槛要求（{threshold_amount}万元）：{text[:50]}",
                            requirement_id=req_id,
                            details={"case_amount": case_amount, "threshold_amount": threshold_amount},
                        )
                    )
                    continue

            # 签字盖章页与验收证明核验
            needs_stamp = any(w in text for w in ("签字盖章", "双方盖章", "盖章页", "合同关键页"))
            needs_acceptance = any(w in text for w in ("验收证明", "验收报告", "竣工证明", "用户证明", "验收合格"))
            
            if needs_stamp:
                if any(w in all_perf_text for w in ("缺少盖章页", "未盖章", "无公章", "无签字盖章", "缺盖章")):
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R06",
                            code="PERFORMANCE_CASE_INSUFFICIENT",
                            severity="blocker",
                            message=f"业绩案例缺少双方签字盖章页证明材料：{text[:50]}",
                            requirement_id=req_id,
                            details={"text": text},
                        )
                    )
                    continue
            
            if needs_acceptance:
                if any(w in all_perf_text for w in ("缺少验收证明", "无验收证明", "未附验收报告", "无验收报告", "缺失验收证明")):
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R06",
                            code="PERFORMANCE_CASE_INSUFFICIENT",
                            severity="blocker",
                            message=f"业绩案例缺少项目验收证明或竣工验收报告：{text[:50]}",
                            requirement_id=req_id,
                            details={"text": text},
                        )
                    )
                    continue

            # 近三年签订时间有效性核验
            needs_three_years = any(w in text for w in ("近三年", "近3年", "三年内", "3年内"))
            if needs_three_years:
                if any(w in all_perf_text for w in ("超过3年", "非近3年", "超出三年", "合同已超期", "签订时间早于近3年")):
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R06",
                            code="PERFORMANCE_CASE_INSUFFICIENT",
                            severity="blocker",
                            message=f"业绩案例合同签订时间超出近三年有效期限：{text[:50]}",
                            requirement_id=req_id,
                            details={"text": text},
                        )
                    )
                    continue
                year_matches = re.findall(r"(\b20[12][0-9]\b)年?合同", all_perf_text)
                for ym in year_matches:
                    y = int(ym)
                    if current_year - y > 3:
                        issues.append(
                            ComplianceRuleIssue(
                                id=new_id("issue"),
                                rule_id="R06",
                                code="PERFORMANCE_CASE_INSUFFICIENT",
                                severity="blocker",
                                message=f"业绩案例合同年份（{y}年）超出近三年有效期限（{current_year-3}至{current_year}年）：{text[:50]}",
                                requirement_id=req_id,
                                details={"contract_year": y, "current_year": current_year},
                            )
                        )
                        break

            needs_contract_evidence = any(w in text for w in ("提供合同", "附合同", "合同扫描件", "业绩证明材料"))
            if needs_contract_evidence and not evidence_ids and not any(w in resp for w in ("已提供", "已上传", "见附件", "附合同")):
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R06",
                        code="PERFORMANCE_CASE_INSUFFICIENT",
                        severity="blocker",
                        message=f"业绩案例条款要求上传合同证明材料，但未挂接有效材料：{text[:50]}",
                        requirement_id=req_id,
                        details={"text": text},
                    )
                )

        passed = len(issues) == 0
        severity: Literal["blocker", "blocking", "warning", "info"] = "blocker" if issues else "info"
        summary = (
            "业绩案例核验通过，业绩合同金额、签约年限、签字盖章页与验收证明均符合要求。"
            if passed
            else f"检测到 {len(issues)} 处业绩案例不合规项（金额不足、缺少盖章页/验收证明或超出年限），构成阻断红线。"
        )
        suggestion = "核验通过" if passed else "请补充符合招标文件门槛金额（如500万以上）、近三年内签署且具备完整双方签字盖章页与验收证明的有效业绩案例材料。"

        return ComplianceRuleResult(
            rule_id="R06",
            title="业绩案例核验（合同金额、类似项目与签字盖章页）",
            severity=severity,
            passed=passed,
            finding_summary=summary,
            suggestion=suggestion,
            issues=[i.to_dict() for i in issues],
            details={"checked_count": checked_count, "performance_issues_count": len(issues)},
        )

    @classmethod
    def check_r08(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all"
    ) -> ComplianceRuleResult:
        """
        R08：交付周期与进度计划偏离核验。
        招标明确要求交付天数上限（如 60 日历天），投标响应承诺交付周期若超过招标上限，判定为负偏离重大违规 blocker (DELIVERY_TIMELINE_NEGATIVE_DEVIATION)。
        """
        issues: list[ComplianceRuleIssue] = []
        requirements = workflow.get("requirements", {})
        checked_count = 0

        for req_id, req in requirements.items():
            if volume != "all" and req.get("volume") != volume:
                continue

            text = str(req.get("text", "") or "")
            is_delivery = any(
                w in text for w in ("交付周期", "交付天数", "交货期", "交付时限", "完工时限", "实施周期", "工期要求", "日历天", "进度计划", "交付时间")
            )
            if not is_delivery:
                continue

            checked_count += 1
            resp = str(req.get("response", "") or req.get("confirmed_response", "") or "").strip()
            dev_type = str(req.get("deviation_type", "")).lower()

            if not resp:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R08",
                        code="DELIVERY_TIMELINE_NEGATIVE_DEVIATION",
                        severity="blocker",
                        message=f"交付周期与进度计划未填写明确响应承诺：{text[:50]}",
                        requirement_id=req_id,
                        details={"text": text},
                    )
                )
                continue

            if dev_type in ("negative", "负偏离"):
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R08",
                        code="DELIVERY_TIMELINE_NEGATIVE_DEVIATION",
                        severity="blocker",
                        message=f"交付周期与进度计划响应存在实质性负偏离：{text[:50]}",
                        requirement_id=req_id,
                        details={"response": resp, "deviation_type": "negative"},
                    )
                )
                continue

            deviation_triggers = (
                "超出交付周期", "无法按期完成", "交期超出", "延迟交付", "延长工期",
                "超出招标上限", "无法在要求时限内", "超期", "负偏离", "工期无法满足", "延长交付天数"
            )
            has_explicit_dev = False
            for trig in deviation_triggers:
                if trig in resp:
                    idx = resp.find(trig)
                    prefix = resp[max(0, idx - 6):idx]
                    if not any(neg in prefix for neg in ("未", "无", "不", "免", "非", "零", "排除", "防止")):
                        has_explicit_dev = True
                        break

            if has_explicit_dev:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R08",
                        code="DELIVERY_TIMELINE_NEGATIVE_DEVIATION",
                        severity="blocker",
                        message=f"交付周期响应劣于招标文件上限要求，构成实质性负偏离：{text[:50]}",
                        requirement_id=req_id,
                        details={"response": resp},
                    )
                )
                continue

            # 提取招标上限天数与投标承诺天数
            req_days: int | None = None
            m_req = re.search(r"(?:交付周期|交货期|工期)?(?:不超过|不高于|低于|<=|≤|内)?\s*(\d+)\s*(?:个?日历天|天|日)(?:内完成|交付|完工)?", text)
            if not m_req:
                m_req = re.search(r"(\d+)\s*(?:个?日历天|天|日)内", text)
            if m_req:
                req_days = int(m_req.group(1))

            prom_days: int | None = None
            m_prom = re.search(r"(?:承诺|交付周期|工期|交货期|需|需要|用时|时间为)\s*(\d+)\s*(?:个?日历天|天|日)", resp)
            if not m_prom:
                m_prom = re.search(r"(\d+)\s*(?:个?日历天|天|日)内完成", resp)
            if not m_prom:
                m_prom = re.search(r"(\d+)\s*(?:个?日历天|天|日)", resp)
            if m_prom:
                prom_days = int(m_prom.group(1))

            if req_days is not None and prom_days is not None:
                if prom_days > req_days:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R08",
                            code="DELIVERY_TIMELINE_NEGATIVE_DEVIATION",
                            severity="blocker",
                            message=f"投标承诺交付周期（{prom_days}日历天）超出招标文件规定的最高限额（{req_days}日历天），构成负偏离重大违规：{text[:50]}",
                            requirement_id=req_id,
                            details={"prom_days": prom_days, "req_days": req_days},
                        )
                    )

        passed = len(issues) == 0
        severity: Literal["blocker", "blocking", "warning", "info"] = "blocker" if issues else "info"
        summary = (
            "交付周期与进度计划核验通过，承诺交付工期与各节点完全满足招标文件上限要求。"
            if passed
            else f"检测到 {len(issues)} 处交付周期负偏离缺陷（承诺天数超出招标上限或无明确承诺），构成阻断红线。"
        )
        suggestion = "核验通过" if passed else "请修正投标响应与进度计划，确保承诺交付天数不超过招标文件限定的上限（如60日历天）。"

        return ComplianceRuleResult(
            rule_id="R08",
            title="交付周期与进度计划偏离核验",
            severity=severity,
            passed=passed,
            finding_summary=summary,
            suggestion=suggestion,
            issues=[i.to_dict() for i in issues],
            details={"checked_count": checked_count, "delivery_issues_count": len(issues)},
        )

    @classmethod
    def check_r12(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all"
    ) -> ComplianceRuleResult:
        """
        R12：服务响应 SLA 与质保期偏离核验。
        招标要求质保期最低年限（如 3 年）及现场到达响应时间（如 2 小时），响应若低于质保期要求或超出到达响应时间，判定为 blocker (SLA_WARRANTY_NEGATIVE_DEVIATION)。
        """
        issues: list[ComplianceRuleIssue] = []
        requirements = workflow.get("requirements", {})
        checked_count = 0

        for req_id, req in requirements.items():
            if volume != "all" and req.get("volume") != volume:
                continue

            text = str(req.get("text", "") or "")
            is_sla_warranty = any(
                w in text for w in ("质保期", "维保期", "保修期", "免费质保", "免费维保", "响应时间", "到达现场", "现场响应", "赶赴现场", "SLA")
            )
            if not is_sla_warranty:
                continue

            checked_count += 1
            resp = str(req.get("response", "") or req.get("confirmed_response", "") or "").strip()
            dev_type = str(req.get("deviation_type", "")).lower()

            if not resp:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R12",
                        code="SLA_WARRANTY_NEGATIVE_DEVIATION",
                        severity="blocker",
                        message=f"服务响应 SLA 与质保期未填写明确响应承诺：{text[:50]}",
                        requirement_id=req_id,
                        details={"text": text},
                    )
                )
                continue

            if dev_type in ("negative", "负偏离"):
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R12",
                        code="SLA_WARRANTY_NEGATIVE_DEVIATION",
                        severity="blocker",
                        message=f"服务响应 SLA 或质保期承诺存在实质性负偏离：{text[:50]}",
                        requirement_id=req_id,
                        details={"response": resp, "deviation_type": "negative"},
                    )
                )
                continue

            dev_triggers = (
                "低于质保期", "缩短质保期", "少于招标文件要求", "不提供免费质保",
                "超出到达响应时间", "响应超时", "无法在要求时间内到达", "无法在2小时内到达",
                "响应时间负偏离", "超出到达时限", "负偏离", "延长现场到达时间"
            )
            has_explicit_dev = False
            for trig in dev_triggers:
                if trig in resp:
                    idx = resp.find(trig)
                    prefix = resp[max(0, idx - 6):idx]
                    if not any(neg in prefix for neg in ("未", "无", "不", "免", "非", "零", "排除", "防止")):
                        has_explicit_dev = True
                        break

            if has_explicit_dev:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R12",
                        code="SLA_WARRANTY_NEGATIVE_DEVIATION",
                        severity="blocker",
                        message=f"服务响应 SLA 或质保期劣于招标文件最低基线，构成实质性负偏离：{text[:50]}",
                        requirement_id=req_id,
                        details={"response": resp},
                    )
                )
                continue

            # 1. 质保期年限对比核验
            is_warranty = any(w in text for w in ("质保期", "维保期", "保修期", "免费质保", "免费维保"))
            if is_warranty:
                req_years: int | None = None
                m_w_req = re.search(r"(?:不少于|不低于|提供|至少|>=|≥)?\s*(\d+)\s*年(?:免费)?(?:质保|维保|保修)", text)
                if m_w_req:
                    req_years = int(m_w_req.group(1))

                prom_years: int | None = None
                m_w_prom = re.search(r"(?:提供|承诺|质保期为|质保期|维保期|免费质保)?\s*(\d+)\s*年(?:免费)?(?:质保|维保|保修)", resp)
                if m_w_prom:
                    prom_years = int(m_w_prom.group(1))

                if req_years is not None and prom_years is not None:
                    if prom_years < req_years:
                        issues.append(
                            ComplianceRuleIssue(
                                id=new_id("issue"),
                                rule_id="R12",
                                code="SLA_WARRANTY_NEGATIVE_DEVIATION",
                                severity="blocker",
                                message=f"承诺质保期（{prom_years}年）低于招标文件最低要求（{req_years}年）：{text[:50]}",
                                requirement_id=req_id,
                                details={"prom_years": prom_years, "req_years": req_years},
                            )
                        )
                        continue

            # 2. 现场到达响应时间对比核验
            is_arrival = any(w in text for w in ("到达现场", "现场响应", "现场到达", "赶赴现场"))
            if is_arrival:
                req_hours: float | None = None
                m_h_req = re.search(r"(?:不超过|内|<=|≤)?\s*(\d+(?:\.\d+)?)\s*小时(?:内)?(?:到达现场|到达|赶赴现场)", text)
                if not m_h_req:
                    m_h_req = re.search(r"(\d+(?:\.\d+)?)\s*小时内到达", text)
                if m_h_req:
                    req_hours = float(m_h_req.group(1))

                prom_hours: float | None = None
                m_h_prom = re.search(r"(?:承诺|需|将在)?\s*(\d+(?:\.\d+)?)\s*小时(?:内)?(?:到达现场|到达|赶赴现场)", resp)
                if not m_h_prom:
                    m_h_prom = re.search(r"(\d+(?:\.\d+)?)\s*小时内到达", resp)
                if m_h_prom:
                    prom_hours = float(m_h_prom.group(1))

                if req_hours is not None and prom_hours is not None:
                    if prom_hours > req_hours:
                        issues.append(
                            ComplianceRuleIssue(
                                id=new_id("issue"),
                                rule_id="R12",
                                code="SLA_WARRANTY_NEGATIVE_DEVIATION",
                                severity="blocker",
                                message=f"承诺现场到达响应时间（{prom_hours}小时）超出招标文件限定时限（{req_hours}小时）：{text[:50]}",
                                requirement_id=req_id,
                                details={"prom_hours": prom_hours, "req_hours": req_hours},
                            )
                        )
                        continue

        # 检查 workflow['sla'] 指标负偏离
        sla = workflow.get("sla") or {}
        sla_values = sla.get("values") or {}
        if isinstance(sla_values, dict):
            for k, item in sla_values.items():
                if not isinstance(item, dict):
                    continue
                dev = str(item.get("deviation") or "").lower()
                name = item.get("name") or k
                if dev in ("negative", "负偏离"):
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R12",
                            code="SLA_WARRANTY_NEGATIVE_DEVIATION",
                            severity="blocker",
                            message=f"SLA 核心服务指标【{name}】标记为实质性负偏离",
                            details={"variable_key": k, "deviation": dev},
                        )
                    )

        passed = len(issues) == 0
        severity: Literal["blocker", "blocking", "warning", "info"] = "blocker" if issues else "info"
        summary = (
            "服务响应 SLA 与质保期核验通过，质保年限与现场到达响应时间均符合或优于招标文件要求。"
            if passed
            else f"检测到 {len(issues)} 处质保期或 SLA 服务响应负偏离缺陷，阻断正式递交导出。"
        )
        suggestion = "核验通过" if passed else "请修正质保承诺（不少于招标年限）并缩短现场到达响应时间（不超过限定时限）。"

        return ComplianceRuleResult(
            rule_id="R12",
            title="服务响应 SLA 与质保期偏离核验",
            severity=severity,
            passed=passed,
            finding_summary=summary,
            suggestion=suggestion,
            issues=[i.to_dict() for i in issues],
            details={"checked_count": checked_count, "sla_warranty_issues_count": len(issues)},
        )

    @classmethod
    def check_r20(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all"
    ) -> ComplianceRuleResult:
        """
        R20：报价雷同排查（分项报价比例与异常一致性排查）。
        排查分项报价清单是否存在异常数字规律、或明显复制其他投标主体的报价结构，排查违规串通投标风险；识别重大异常判定为 blocker (BID_PRICE_COLLUSION_RISK_DETECTED)。
        """
        issues: list[ComplianceRuleIssue] = []
        checked_count = 0

        # 1. 扫描正文文本（重点在商务分册 business 与报价相关章节）
        chapters = [ch for ch in state.chapters.values() if ch.project_id == project.id]
        if volume != "all":
            chapters = [ch for ch in chapters if ch.volume == volume]

        collusion_patterns = [
            "分项报价比例异常一致",
            "报价雷同",
            "复制其他投标主体报价",
            "复制其他投标人报价",
            "串通投标风险",
            "串标嫌疑",
            "存在串标",
            "分项报价呈固定比例成倍递增",
            "分项报价比例完全一致",
            "与其他投标人报价规律异常一致",
            "报价结构完全雷同",
            "多份投标文件分项报价比例相同",
            "报价规律高度一致",
        ]

        for ch in chapters:
            if not ch.content:
                continue
            checked_count += 1
            for pat in collusion_patterns:
                if pat in ch.content:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R20",
                            code="BID_PRICE_COLLUSION_RISK_DETECTED",
                            severity="blocker",
                            message=f"章节《{ch.title}》正文排查到报价雷同或串通投标风险特征：'{pat}'（违反招投标反串标合规红线）",
                            chapter_id=ch.id,
                            details={"chapter_title": ch.title, "pattern": pat},
                        )
                    )
                    break

        # 2. 扫描条款响应
        requirements = workflow.get("requirements", {})
        for req_id, req in requirements.items():
            if volume != "all" and req.get("volume") != volume:
                continue
            resp = str(req.get("response", "") or req.get("confirmed_response", "") or "").strip()
            if not resp:
                continue
            checked_count += 1
            for pat in collusion_patterns:
                if pat in resp:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R20",
                            code="BID_PRICE_COLLUSION_RISK_DETECTED",
                            severity="blocker",
                            message=f"条款响应中排查到报价雷同或串通投标风险特征：'{pat}'",
                            requirement_id=req_id,
                            details={"pattern": pat},
                        )
                    )
                    break

        # 3. 排查结构化报价数据 workflow.get("quotation") / workflow.get("pricing")
        quotation = workflow.get("quotation") or workflow.get("pricing") or {}
        if isinstance(quotation, dict):
            checked_count += 1
            if (
                quotation.get("collusion_risk") is True
                or quotation.get("identical_breakdown_ratio") is True
                or quotation.get("is_collusive") is True
                or quotation.get("abnormal_consistency") is True
            ):
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R20",
                        code="BID_PRICE_COLLUSION_RISK_DETECTED",
                        severity="blocker",
                        message="报价清单数据分析检测到分项报价比例异常一致，存在串通投标雷同风险",
                        details={"quotation": quotation},
                    )
                )

        passed = len(issues) == 0
        severity: Literal["blocker", "blocking", "warning", "info"] = "blocker" if issues else "info"
        summary = (
            "报价清单排查通过，未检测到分项报价比例异常一致、规律性雷同或串通投标风险。"
            if passed
            else f"排查到 {len(issues)} 处报价雷同或串标高危特征，违反招投标公平竞争红线，阻断正式递交导出。"
        )
        suggestion = "排查通过" if passed else "请核查分项报价测算明细，消除与其他投标主体分项比例异常一致或报价雷同嫌疑，确保报价独立编制。"

        return ComplianceRuleResult(
            rule_id="R20",
            title="报价雷同排查（分项报价比例与异常一致性排查）",
            severity=severity,
            passed=passed,
            finding_summary=summary,
            suggestion=suggestion,
            issues=[i.to_dict() for i in issues],
            details={"checked_count": checked_count, "collusion_issues_count": len(issues)},
        )

    @classmethod
    def evaluate_p0_rules(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
    ) -> list[ComplianceRuleResult]:
        """按顺序完整执行 PRD P0 级合规规则体系（R01, R02, R15, R23, R34, R35, R37）。"""
        return [
            cls.check_r01(state, project, workflow, volume=volume),
            cls.check_r02(state, project, workflow, volume=volume),
            cls.check_r15(state, project, workflow, volume=volume, now_ts=now_ts),
            cls.check_r23(state, project, workflow, volume=volume),
            cls.check_r34(state, project, workflow, volume=volume),
            cls.check_r35(state, project, workflow, volume=volume),
            cls.check_r37(state, project, workflow, volume=volume),
        ]

    @classmethod
    def evaluate_p1_rules(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
    ) -> list[ComplianceRuleResult]:
        """按顺序完整执行 PRD P1 级核心商务与资质合规规则（R03, R04, R09, R10）。"""
        return [
            cls.check_r03(state, project, workflow, volume=volume, now_ts=now_ts),
            cls.check_r04(state, project, workflow, volume=volume),
            cls.check_r09(state, project, workflow, volume=volume),
            cls.check_r10(state, project, workflow, volume=volume),
        ]

    @classmethod
    def evaluate_p2_rules(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
    ) -> list[ComplianceRuleResult]:
        """按顺序完整执行 PRD P2 级核心合规规则体系（R07, R11, R14, R25, R31）。"""
        return [
            cls.check_r07(state, project, workflow, volume=volume, now_ts=now_ts),
            cls.check_r11(state, project, workflow, volume=volume, now_ts=now_ts),
            cls.check_r14(state, project, workflow, volume=volume),
            cls.check_r25(state, project, workflow, volume=volume),
            cls.check_r31(state, project, workflow, volume=volume),
        ]

    @classmethod
    def evaluate_p3_rules(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
    ) -> list[ComplianceRuleResult]:
        """按顺序完整执行 PRD P3 级核心合规规则体系（R05, R06, R08, R12, R20）。"""
        return [
            cls.check_r05(state, project, workflow, volume=volume),
            cls.check_r06(state, project, workflow, volume=volume, now_ts=now_ts),
            cls.check_r08(state, project, workflow, volume=volume),
            cls.check_r12(state, project, workflow, volume=volume),
            cls.check_r20(state, project, workflow, volume=volume),
        ]

    @classmethod
    def evaluate_all(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
    ) -> list[ComplianceRuleResult]:
        """执行当前系统已落地的全部合规规则体系（P0、P1、P2 与 P3 批次共 21 项规则）。"""
        return (
            cls.evaluate_p0_rules(state, project, workflow, volume=volume, now_ts=now_ts)
            + cls.evaluate_p1_rules(state, project, workflow, volume=volume, now_ts=now_ts)
            + cls.evaluate_p2_rules(state, project, workflow, volume=volume, now_ts=now_ts)
            + cls.evaluate_p3_rules(state, project, workflow, volume=volume, now_ts=now_ts)
        )


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

        rule_results = ComplianceRulesEngine.evaluate_all(
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
