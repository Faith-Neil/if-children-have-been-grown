# 为什么有这个文件：实现 AI 合规检查依据交叉核验与差距诊断核心服务（AI-COMPLIANCE-CROSS-CHECK）。
# 它解决什么问题：
# 1. 提取章节内全部 .cite 引用与声明内容（SLA数值承诺、资质认证、人员经验、业绩案例、通用服务承诺）；
# 2. 交叉比对 RAGFlow 已核验资料与当前招标文件切片，若发现声明内容缺乏有效数据支撑（如承诺 99.99% 高可用但证据仅为一般描述，或证据过期/无协议），生成带有依据置信度（confidence_score）与差距分析（gap_description）的诊断建议；
# 3. 配合后端 checks 服务，生成合规风险提示并联动更新章节增量复查状态（incremental_check_status）；
# 4. 严格落实数据隔离与安全门禁：涉密项目强校验本地模型（403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL），跨租户隔离（404 NOT_FOUND）与权限门禁（403 FORBIDDEN）。

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

from .domain import DemoService, DemoState, DomainError, Principal, iso_time, new_id

SHANGHAI = timezone(timedelta(hours=8))
from .workflow_schemas import (
    CheckIssue,
    ComplianceFinding,
    ComplianceCrossCheckResponse,
)

# 声明分类常量
CLAIM_SLA = "sla_metric"
CLAIM_QUALIFICATION = "qualification"
CLAIM_PERSONNEL = "personnel"
CLAIM_CASE = "case_experience"
CLAIM_GENERAL = "general_promise"

# 置信度等级
CONF_HIGH = "high"
CONF_MEDIUM = "medium"
CONF_LOW = "low"
CONF_UNSUPPORTED = "unsupported"

# 风险级别
RISK_BLOCK = "block"
RISK_WARNING = "warning"
RISK_INFO = "info"


def extract_citations_from_text(text: str) -> list[dict[str, str]]:
    """从文本中抽取 .cite 标记（如 [证:ID]、[片:ID]、[证]、[片]）。"""
    citations = []
    # 抽取带 ID 的引用胶囊 [证:ID] 或 [片:ID]
    for m in re.finditer(r"\[(证|片):([a-zA-Z0-9_\-\.\:]+)\]", text):
        tag = m.group(1)
        cid = m.group(2)
        citations.append({
            "type": "evidence" if tag == "证" else "tender_slice",
            "id": cid,
            "raw": m.group(0),
            "start": m.start(),
            "end": m.end(),
        })
    # 抽取不带 ID 的泛指标记 [证] 或 [片]
    for m in re.finditer(r"\[(证|片)\]", text):
        tag = m.group(1)
        citations.append({
            "type": "evidence" if tag == "证" else "tender_slice",
            "id": "",
            "raw": m.group(0),
            "start": m.start(),
            "end": m.end(),
        })
    return citations


def extract_claims_from_text(paragraph_text: str, paragraph_id: str) -> list[dict[str, Any]]:
    """
    智能分析段落文本，抽取 SLA 数值指标、资质认证、人员能力、业绩案例及重大服务承诺声明。
    """
    claims: list[dict[str, Any]] = []

    # 1. SLA 与关键数值承诺抽取
    # 1.1 可用性指标 (如 99.99% 可用性, 业务可用性 99.99%, 99.9% 在线率, 99.99% 的高可用)
    for m in re.finditer(
        r"(?:(?:可用性|系统可用性|SLA|在线率|高可用|可靠性)\s*(?:达到|为|不低于|优于)?\s*)?(?P<val>99\.\d{1,4}%|99%)(?:\s*(?:的|以上|及以上)?\s*(?:可用性|系统可用性|SLA|在线率|高可用|可靠性|服务水平))?",
        paragraph_text,
    ):
        matched_str = m.group(0)
        if any(kw in matched_str for kw in ("可用性", "SLA", "在线率", "高可用", "可靠性")) or "99" in matched_str:
            claims.append({
                "claim_type": CLAIM_SLA,
                "claim_text": matched_str.strip(),
                "metric_type": "availability",
                "target_value": m.group("val"),
                "paragraph_id": paragraph_id,
                "start": m.start(),
                "end": m.end(),
            })

    # 1.2 响应与恢复时限 (如 15分钟响应, 30分钟内到达现场, 2小时内排除故障)
    for m in re.finditer(r"(?P<val>\d+\s*(?:分钟|小时|min|h|s|秒))(?:以内|内)?(?:到达现场|到达|响应|恢复|排除故障)", paragraph_text):
        claims.append({
            "claim_type": CLAIM_SLA,
            "claim_text": m.group(0),
            "metric_type": "response_time",
            "target_value": m.group("val"),
            "paragraph_id": paragraph_id,
            "start": m.start(),
            "end": m.end(),
        })

    # 1.3 服务时间覆盖 (如 7×24小时, 7*24小时, 5×8小时)
    for m in re.finditer(r"(?P<val>(?:7|5)\s*[×*xX]\s*(?:24|8)\s*(?:小时)?)", paragraph_text):
        claims.append({
            "claim_type": CLAIM_SLA,
            "claim_text": m.group(0),
            "metric_type": "service_hours",
            "target_value": m.group("val"),
            "paragraph_id": paragraph_id,
            "start": m.start(),
            "end": m.end(),
        })

    # 1.4 巡检频次 (如 每周2次巡检, 每月1次健康检查)
    for m in re.finditer(r"(?P<val>(?:每周|每月|每季度)\s*\d+\s*次)(?:巡检|例行巡检|巡查|健康检查)", paragraph_text):
        claims.append({
            "claim_type": CLAIM_SLA,
            "claim_text": m.group(0),
            "metric_type": "inspection_frequency",
            "target_value": m.group("val"),
            "paragraph_id": paragraph_id,
            "start": m.start(),
            "end": m.end(),
        })

    # 1.5 RTO / RPO
    for m in re.finditer(r"(?P<type>RTO|RPO)\s*[<≤=]?\s*(?P<val>\d+\s*(?:分钟|小时|秒|min|h|s))", paragraph_text, re.IGNORECASE):
        claims.append({
            "claim_type": CLAIM_SLA,
            "claim_text": m.group(0),
            "metric_type": m.group("type").upper(),
            "target_value": m.group("val"),
            "paragraph_id": paragraph_id,
            "start": m.start(),
            "end": m.end(),
        })

    # 2. 资质认证声明抽取 (如 CMMI5级, ISO27001, 高新技术企业)
    for m in re.finditer(r"(?P<val>CMMI\s*(?:[1-5]|一|二|三|四|五)级?|ISO\s*(?:9001|27001|20000|14001|45001)|ITSS\s*(?:[1-4]|一|二|三|四)级?|CCRC\s*(?:[1-3]|一|二|三)级?|高新技术企业|系统集成(?:特|一|二|三)?级?资质)", paragraph_text, re.IGNORECASE):
        claims.append({
            "claim_type": CLAIM_QUALIFICATION,
            "claim_text": m.group(0),
            "metric_type": "qualification_name",
            "target_value": m.group("val"),
            "paragraph_id": paragraph_id,
            "start": m.start(),
            "end": m.end(),
        })

    # 3. 人员与团队能力声明抽取 (如 10年以上经验, 持有PMP认证, 20人专职团队)
    for m in re.finditer(r"(?P<val>具备\s*\d+\s*年(?:及以上)?(?:相关|运维|开发|项目管理)?经验|持有\s*(?:PMP|ITIL|CCIE|HCIE|CISP|软考高项|高级工程师)(?:认证|证书)?|配置\s*\d+\s*人(?:及以上)?的?(?:专职|专属|驻场)?(?:运维|技术服务)?团队)", paragraph_text):
        claims.append({
            "claim_type": CLAIM_PERSONNEL,
            "claim_text": m.group(0),
            "metric_type": "personnel_capability",
            "target_value": m.group("val"),
            "paragraph_id": paragraph_id,
            "start": m.start(),
            "end": m.end(),
        })

    # 4. 业绩与案例声明抽取 (如 5个以上同类项目, 合同金额不低于1000万元)
    for m in re.finditer(r"(?P<val>具备\s*\d+\s*个(?:及以上)?(?:类似|同类|省级|金融级)?(?:业绩|案例)|合同金额(?:不低于|大于|超过)\s*\d+\s*万元)", paragraph_text):
        claims.append({
            "claim_type": CLAIM_CASE,
            "claim_text": m.group(0),
            "metric_type": "case_experience",
            "target_value": m.group("val"),
            "paragraph_id": paragraph_id,
            "start": m.start(),
            "end": m.end(),
        })

    # 5. 重大通用服务承诺抽取 (驻场保障、备品备件、零数据丢失)
    general_patterns = [
        r"(?:承诺)?(?:提供)?驻场(?:保障|服务|保障承诺|保障服务)",
        r"(?:承诺)?(?:提供)?(?:免费)?备品备件(?:库|保障)?",
        r"(?:承诺)?(?:系统架构)?支持零数据丢失",
        r"(?:承诺)?提供原厂备件保障",
    ]
    for pattern in general_patterns:
        for m in re.finditer(pattern, paragraph_text):
            if m.group(0).strip():
                claims.append({
                    "claim_type": CLAIM_GENERAL,
                    "claim_text": m.group(0).strip(),
                    "metric_type": "general_commitment",
                    "target_value": m.group(0).strip(),
                    "paragraph_id": paragraph_id,
                    "start": m.start(),
                    "end": m.end(),
                })

    return claims


class ComplianceCrossCheckService:
    """
    落地 AI-COMPLIANCE-CROSS-CHECK 依据交叉核验与差距诊断核心服务：
    1. 抽取章节内 .cite 标记与强声明（SLA数值、资质认证、人员、案例等）；
    2. 交叉比对 RAGFlow 已核验资料与招标文件切片要求；
    3. 诊断依据充分性，计算置信度（高/中/低/未支撑），生成差距与改进建议；
    4. 联动后端 checks 记录与增量复查状态流转；
    5. 严格落实敏感项目本地模型门禁与多租户权限隔离。
    """

    def __init__(self, demo: DemoService) -> None:
        self.demo = demo

    def cross_check_chapter(
        self,
        principal: Principal,
        project_id: str,
        chapter_id: str,
        model_config_id: str | None = None,
        strict_mode: bool = True,
    ) -> dict[str, Any]:
        """
        执行单章节合规依据交叉核验与差距诊断：
        - 校验调用权限与租户隔离；
        - 校验敏感项目本地模型门禁；
        - 执行全量段落声明抽取与证据比对；
        - 生成结构化差距诊断与置信度评分；
        - 联动写入 checks 记录并更新章节增量复查状态。
        """
        def operation(state: DemoState):
            # 门禁 1：租户与项目隔离
            project = state.projects.get(project_id)
            if project is None or project.company_id != principal.user.company_id:
                raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")

            team = state.project_teams.get(project_id, {})
            members = team.get("members", {})
            norm_role = principal.user.role
            if principal.user.id not in members and norm_role not in ("company_admin", "admin"):
                raise DomainError(403, "FORBIDDEN", "您不是本项目成员，无权发起合规交叉核验。")

            chapter = state.chapters.get(chapter_id)
            if chapter is None or chapter.project_id != project_id:
                raise DomainError(404, "NOT_FOUND", "未找到有权访问的章节。")

            # 门禁 2：敏感项目本地模型强门禁
            is_sensitive = getattr(project, "sensitive", False) or getattr(project, "is_sensitive", False)
            if is_sensitive:
                cfg_id = model_config_id or state.project_model_configs.get(project_id)
                cfg = None
                if cfg_id and cfg_id in state.model_configs:
                    cfg = state.model_configs[cfg_id]
                else:
                    default_id = f"default-{project.company_id}"
                    if default_id in state.model_configs:
                        cfg = state.model_configs[default_id]

                if cfg is not None:
                    if not getattr(cfg, "is_local", False) or not getattr(cfg, "allow_sensitive", False):
                        raise DomainError(403, "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL", "敏感项目只能使用本地模型配置。")
                else:
                    provider = getattr(self.demo, "model_provider", None)
                    if getattr(provider, "is_local", False) is False and getattr(provider, "is_real_model", None) is not False:
                        raise DomainError(403, "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL", "敏感项目只能使用本地模型。")

            # 准备数据源
            workflow = state.workflows.setdefault(project_id, {})
            candidates: dict[str, Any] = workflow.get("candidates", {})
            tender_requirements: list[dict[str, Any]] = workflow.get("requirements", [])
            injected_tender_clauses: list[dict[str, Any]] = workflow.get("injected_tender_clauses", {}).get(chapter_id, [])

            # 切分段落
            content = chapter.content or ""
            normalized = content.replace("\r\n", "\n").replace("\r", "\n")
            blocks = [b for b in normalized.split("\n") if b.strip()]

            # 收集已有章节引用元数据
            chapter_citations: list[dict[str, Any]] = getattr(chapter, "citations", []) or []
            citations_map: dict[str, dict[str, Any]] = {}
            for c in chapter_citations:
                cid = c.get("id") or c.get("source_id") or ""
                if cid:
                    citations_map[cid] = c

            findings: list[ComplianceFinding] = []
            finding_counter = 0

            # 逐段抽取与核验
            for idx, block in enumerate(blocks):
                p_order = idx + 1
                p_id = f"{chapter.id}-p{p_order}"

                # 提取本段内的引用标记
                inline_cites = extract_citations_from_text(block)
                # 提取本段声明
                claims = extract_claims_from_text(block, p_id)

                for claim in claims:
                    finding_counter += 1
                    fid = f"gap-{p_id}-{finding_counter:02d}"
                    c_type = claim["claim_type"]
                    c_text = claim["claim_text"]
                    target_val = claim.get("target_value", "")
                    metric_type = claim.get("metric_type", "")

                    # 1. 定位关联证据
                    matched_eid = None
                    if inline_cites:
                        claim_end = claim.get("end", 0)
                        # 查找紧随当前声明后面的带 ID 引用胶囊
                        after_cites = [c for c in inline_cites if c["start"] >= claim_end and c.get("id")]
                        if after_cites:
                            closest = min(after_cites, key=lambda c: c["start"] - claim_end)
                            matched_eid = closest["id"]
                        elif len(inline_cites) == 1 and inline_cites[0].get("id"):
                            matched_eid = inline_cites[0]["id"]
                        else:
                            # 查找本段内距离当前声明最近的带 ID 引用
                            id_cites = [c for c in inline_cites if c.get("id")]
                            if id_cites:
                                closest = min(id_cites, key=lambda c: abs(c["start"] - claim.get("start", 0)))
                                matched_eid = closest["id"]
                            elif chapter_citations:
                                matched_eid = chapter_citations[0].get("id")

                    # 若段落未显式标注引用，检查章节引用列表是否有与声明语义相关的依据
                    if not matched_eid and chapter_citations:
                        for cc in chapter_citations:
                            c_name = cc.get("name", "") + " " + cc.get("content", "")
                            if target_val and (target_val in c_name or metric_type in c_name):
                                matched_eid = cc.get("id")
                                break

                    evidence = None
                    if matched_eid:
                        evidence = candidates.get(matched_eid) or citations_map.get(matched_eid)

                    # 2. 交叉比对与置信度推导
                    confidence_score = 1.0
                    confidence_level = CONF_HIGH
                    risk_level = RISK_INFO
                    evidence_status = "valid"
                    gap_desc = "依据充分，与正文声明严格相符。"
                    sugg = "依据充分，可保持。"
                    matched_req_id = None

                    # 2.1 检查招标文件硬性要求交叉核验（核查负偏离）
                    # 遍历招标文件条款
                    reqs_to_check = tender_requirements + injected_tender_clauses
                    for req in reqs_to_check:
                        r_text = (req.get("requirement") or req.get("content") or req.get("name") or "")
                        # 响应时间条款比对
                        if metric_type == "response_time" and ("响应时间" in r_text or "到达现场" in r_text):
                            matched_req_id = req.get("id") or req.get("clause_number")
                            # 提取招标文件要求的数值
                            req_val_m = re.search(r"(\d+)\s*(?:分钟|min)", r_text)
                            claim_val_m = re.search(r"(\d+)\s*(?:分钟|min)", target_val)
                            if req_val_m and claim_val_m:
                                req_minutes = int(req_val_m.group(1))
                                claim_minutes = int(claim_val_m.group(1))
                                if claim_minutes > req_minutes:
                                    # 负偏离！
                                    confidence_score = 0.0
                                    confidence_level = CONF_UNSUPPORTED
                                    risk_level = RISK_BLOCK
                                    gap_desc = (
                                        f"正文承诺的响应时间【{target_val}】劣于招标文件条款要求（不超过 {req_minutes} 分钟），"
                                        "构成负偏离废标风险。"
                                    )
                                    sugg = f"必须将响应时间调整至不超过 {req_minutes} 分钟，以满足招标文件强制条款要求。"
                                    break

                    # 若已触发负偏离阻断，直接构建 finding
                    if risk_level == RISK_BLOCK and confidence_score == 0.0:
                        findings.append(ComplianceFinding(
                            finding_id=fid,
                            paragraph_id=p_id,
                            claim_type=c_type,
                            claim_text=c_text,
                            cited_evidence_id=matched_eid,
                            evidence_status=evidence_status,
                            tender_clause_id=matched_req_id,
                            confidence_score=confidence_score,
                            confidence_level=confidence_level,
                            risk_level=risk_level,
                            gap_description=gap_desc,
                            suggestion=sugg,
                        ))
                        continue

                    # 2.2 证据状态核验
                    if matched_eid and evidence is not None:
                        # 检查过期
                        if evidence.get("is_expired") or evidence.get("status") == "expired":
                            evidence_status = "expired"
                            confidence_score = 0.0
                            confidence_level = CONF_UNSUPPORTED
                            risk_level = RISK_BLOCK
                            gap_desc = f"引用的证据 (ID: {matched_eid}) 已超过有效截止时间，属于失效依据。"
                            sugg = "请在资料库更新该证据的有效资质证明或重新上传有效版本。"
                        elif evidence.get("status") in ("unconfirmed", "draft"):
                            evidence_status = "pending_verification"
                            confidence_score = 0.40
                            confidence_level = CONF_MEDIUM
                            risk_level = RISK_WARNING
                            gap_desc = f"引用的证据 (ID: {matched_eid}) 尚未经录入人或资料管理员审核确认。"
                            sugg = "请先在资料库完成证据真实性与有效性复核确认后再引用。"
                        elif evidence.get("source_tier") == "partner" and not evidence.get("agreement_present", True):
                            evidence_status = "missing_agreement"
                            confidence_score = 0.0
                            confidence_level = CONF_UNSUPPORTED
                            risk_level = RISK_BLOCK
                            gap_desc = f"引用的合作伙伴证据 (ID: {matched_eid}) 缺少联合体协议或分包合作协议。"
                            sugg = "请在项目挂证据抽屉中补传合作协议，否则不可作为合规依据引用。"
                        else:
                            # 证据状态有效，核对证据具体内容是否能充分支撑声明
                            evidence_text = (
                                evidence.get("content")
                                or evidence.get("text")
                                or evidence.get("name")
                                or ""
                            )
                            if c_type == CLAIM_SLA:
                                # SLA 数值核验：如果正文承诺 99.99%，证据中是否具备确切数据支撑？
                                clean_target = target_val.replace(" ", "")
                                if clean_target in evidence_text.replace(" ", ""):
                                    confidence_score = 0.95
                                    confidence_level = CONF_HIGH
                                    risk_level = RISK_INFO
                                    gap_desc = f"声明的【{c_text}】在已核验证据 (ID: {matched_eid}) 中有确切公章/测评指标支撑。"
                                    sugg = "依据充分，可保持。"
                                else:
                                    # 关键发现：正文做高额数值承诺，但证据中仅包含一般描述
                                    confidence_score = 0.55
                                    confidence_level = CONF_MEDIUM
                                    risk_level = RISK_WARNING
                                    gap_desc = (
                                        f"正文承诺【{c_text}】，但引用的证据 (ID: {matched_eid}) 仅包含一般性架构或运维文字描述，"
                                        f"缺少明确的【{target_val}】量化指标测评报告或加盖公章的 SLA 承诺支撑。"
                                    )
                                    sugg = (
                                        "建议在资料库补充上传带有 99.99% SLA 承诺指标的权威第三方测评报告或盖章承诺函，"
                                        "或适度调整正文过高承诺表述以防履约违约风险。"
                                    )
                            elif c_type == CLAIM_QUALIFICATION:
                                # 资质等级核验
                                clean_q = target_val.upper().replace(" ", "")
                                if clean_q in evidence_text.upper().replace(" ", ""):
                                    confidence_score = 0.95
                                    confidence_level = CONF_HIGH
                                    risk_level = RISK_INFO
                                    gap_desc = f"正文声明的资质【{c_text}】与已核验证据严格一致。"
                                    sugg = "依据充分，可保持。"
                                else:
                                    confidence_score = 0.50
                                    confidence_level = CONF_MEDIUM
                                    risk_level = RISK_WARNING
                                    gap_desc = f"正文声明持有【{c_text}】，但引用证据未明确记载该特定等级认证。"
                                    sugg = "请上传对应等级的证书原件或核准资质名称。"
                            else:
                                confidence_score = 0.88
                                confidence_level = CONF_HIGH
                                risk_level = RISK_INFO
                                gap_desc = "正文陈述与引用的佐证资料基本一致。"
                                sugg = "依据有效，可保持。"
                    elif matched_eid and evidence is None:
                        # 标记了证据 ID 但未找到实体
                        evidence_status = "missing"
                        confidence_score = 0.20
                        confidence_level = CONF_UNSUPPORTED
                        risk_level = RISK_WARNING
                        gap_desc = f"段落中标记了引用依据 [{matched_eid}]，但在本项目资料库中未检索到该记录。"
                        sugg = "请核对引用 ID 是否正确，或在资料库重新录入并挂接该证据。"
                    else:
                        # 正文有强声明但完全没有引用标记
                        evidence_status = "missing"
                        # 检查在项目候选资料库中是否有潜在支撑
                        potential_match = None
                        for cid, cand in candidates.items():
                            cand_str = (cand.get("name") or "") + " " + (cand.get("content") or "")
                            if target_val and target_val in cand_str:
                                potential_match = cid
                                break

                        if potential_match:
                            confidence_score = 0.40
                            confidence_level = CONF_LOW
                            risk_level = RISK_WARNING
                            gap_desc = f"段落作出了关键声明【{c_text}】，资料库中有潜在相关证据 (ID: {potential_match}) 但未在正文中显式引用。"
                            sugg = f"建议在声明语句后追加引用标记 [证:{potential_match}] 以充实投标依据链条。"
                        else:
                            confidence_score = 0.15
                            confidence_level = CONF_UNSUPPORTED
                            risk_level = RISK_WARNING
                            gap_desc = f"段落陈述了强承诺【{c_text}】，但在正文与资料库中均未检索到有效依据支撑。"
                            sugg = "请补充相关证明文件并添加依据引用，避免评标专家判定虚假响应。"

                    findings.append(ComplianceFinding(
                        finding_id=fid,
                        paragraph_id=p_id,
                        claim_type=c_type,
                        claim_text=c_text,
                        cited_evidence_id=matched_eid,
                        evidence_status=evidence_status,
                        tender_clause_id=matched_req_id,
                        confidence_score=confidence_score,
                        confidence_level=confidence_level,
                        risk_level=risk_level,
                        gap_description=gap_desc,
                        suggestion=sugg,
                    ))

            # 3. 统计汇总指标
            total_claims = len(findings)
            verified_claims = sum(1 for f in findings if f.confidence_level == CONF_HIGH)
            warning_claims = sum(1 for f in findings if f.confidence_level == CONF_MEDIUM)
            unsupported_claims = sum(1 for f in findings if f.confidence_level in (CONF_LOW, CONF_UNSUPPORTED))

            if total_claims > 0:
                overall_confidence = round(sum(f.confidence_score for f in findings) / total_claims, 3)
            else:
                overall_confidence = 1.0

            has_block = any(f.risk_level == RISK_BLOCK for f in findings)
            has_warning = any(f.risk_level == RISK_WARNING for f in findings)

            if has_block:
                comp_status = "non_compliant"
                check_status_val = "failed"
            elif has_warning:
                comp_status = "warning"
                check_status_val = "warning"
            else:
                comp_status = "compliant"
                check_status_val = "passed"

            now_ts = self.demo._now()
            now_iso = iso_time(now_ts)

            # 4. 联动更新章节与工作流检查结果
            chapter.incremental_check_status = check_status_val

            # 记录到增量复查历史列表
            inc_checks = workflow.setdefault("incremental_checks", [])
            check_record = {
                "id": new_id("chk-cross"),
                "chapter_id": chapter_id,
                "project_id": project_id,
                "type": "compliance_cross_check",
                "status": comp_status,
                "overall_confidence": overall_confidence,
                "total_claims": total_claims,
                "verified_claims": verified_claims,
                "warning_claims": warning_claims,
                "unsupported_claims": unsupported_claims,
                "findings": [f.model_dump() for f in findings],
                "created_at": now_iso,
                "checked_by": principal.user.id,
            }
            inc_checks.append(check_record)

            # 如果存在阻断项，同步写入 project.check 队列以通知检查中心
            issues: list[dict[str, Any]] = []
            for f in findings:
                if f.risk_level in (RISK_BLOCK, RISK_WARNING):
                    issues.append({
                        "id": f.finding_id,
                        "code": "CHECK_FAILED" if f.risk_level == RISK_BLOCK else "CHECK_WARNING",
                        "severity": "blocking" if f.risk_level == RISK_BLOCK else "warning",
                        "message": f"{f.claim_text}：{f.gap_description}",
                        "chapter_id": chapter_id,
                        "evidence_id": f.cited_evidence_id,
                    })

            checks_summary = {
                "check_id": check_record["id"],
                "compliance_status": comp_status,
                "issues_count": len(issues),
                "issues": issues,
            }

            return {
                "chapter_id": chapter_id,
                "project_id": project_id,
                "overall_confidence": overall_confidence,
                "compliance_status": comp_status,
                "total_claims": total_claims,
                "verified_claims": verified_claims,
                "warning_claims": warning_claims,
                "unsupported_claims": unsupported_claims,
                "findings": findings,
                "checks_summary": checks_summary,
                "checked_at": now_iso,
                "message": (
                    f"章节交叉核验完成：共核验 {total_claims} 项声明，"
                    f"充分支撑 {verified_claims} 项，"
                    f"待补差距 {warning_claims + unsupported_claims} 项，"
                    f"综合置信度 {overall_confidence:.1%}。"
                ),
            }

        return self.demo.repository.transaction(operation)
