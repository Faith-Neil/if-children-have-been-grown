# ISSUE-046：PRD v1.8 §5.8.1 编号对齐后的 check_rXX 实现（与错位旧逻辑分离，旧逻辑见 compliance_ext_legacy.py）。

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Literal

from icg.domain.chapter_generation import (
    AI_CONVERSATION_RESIDUALS,
    CITATION_PATTERN,
    PLACEHOLDER_REGEXES,
)
from icg.domain.compliance_rules import (
    ComplianceRuleIssue,
    ComplianceRuleResult,
    is_critical_requirement,
    new_id,
)
from icg.domain.generation_context import evidence_expired
from icg.domain.domain import DemoState
from icg.domain.library_orchestrator import LibraryOrchestrator
from icg.domain.sla import sla_issues

try:
    from icg.domain.export_service import SHANGHAI
except ImportError:
    from datetime import timezone

    SHANGHAI = timezone(timedelta(hours=8))


def _chapters(state: DemoState, project_id: str, volume: str):
    chapters = [ch for ch in state.chapters.values() if ch.project_id == project_id]
    if volume != "all":
        chapters = [ch for ch in chapters if ch.volume == volume]
    return chapters


def _citations(text: str) -> list[tuple[str, str]]:
    return [(m.group(1), (m.group(2) or "").strip()) for m in CITATION_PATTERN.finditer(text or "")]


def _evidence_usable(state: DemoState, project: Any, evidence_id: str) -> tuple[bool, str, str]:
    evidence = state.library.get(evidence_id)
    if evidence is None:
        return False, "EVIDENCE_MISSING", "引用的资料不存在"
    if evidence.get("company_id") != project.company_id:
        return False, "EVIDENCE_CROSS_COMPANY", "引用的资料不属于本公司空间"
    if evidence.get("status") != "confirmed":
        return False, "EVIDENCE_NOT_CONFIRMED", f"资料状态为 {evidence.get('status')}，不可引用"
    if evidence.get("type") == "history" or evidence.get("source_tier") == "reference":
        return False, "EVIDENCE_REFERENCE_ONLY", "仅供参考资料或未发布片段禁止引用"
    if evidence.get("deleted") or evidence.get("is_deleted"):
        return False, "EVIDENCE_DELETED", "资料已删除或停用"
    if evidence.get("disabled") or evidence.get("status") == "disabled":
        return False, "EVIDENCE_DISABLED", "资料已停用"
    return True, "", ""


def prd_check_r01(
    state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
) -> ComplianceRuleResult:
    issues: list[ComplianceRuleIssue] = []
    today = (
        datetime.fromtimestamp(now_ts, SHANGHAI).date()
        if now_ts
        else datetime.now(SHANGHAI).date()
    )
    checked = 0
    for ch in _chapters(state, project.id, volume):
        content = ch.content or ""
        if not content.strip():
            continue
        for kind, ref in _citations(content):
            if kind != "证" or not ref:
                continue
            checked += 1
            ok, code, msg = _evidence_usable(state, project, ref)
            if not ok:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R01",
                        code=code,
                        severity="blocker",
                        message=f"章节《{ch.title}》{msg}：[证:{ref}]",
                        chapter_id=ch.id,
                        evidence_id=ref,
                    )
                )
                continue
            evidence = state.library[ref]
            if evidence_expired(evidence, project.deadline, today=today):
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R01",
                        code="EVIDENCE_EXPIRED",
                        severity="blocker",
                        message=f"章节《{ch.title}》引用的资料有效期不能覆盖投标截止日：[证:{ref}]",
                        chapter_id=ch.id,
                        evidence_id=ref,
                    )
                )
    passed = not issues
    return ComplianceRuleResult(
        rule_id="R01",
        title="不可引用的资料禁止引用",
        severity="blocker" if issues else "info",
        passed=passed,
        finding_summary=(
            f"复核 {checked} 处正文证据引用，均可引用且有效。"
            if passed
            else f"发现 {len(issues)} 处不可引用或失效的资料引用。"
        ),
        suggestion="请更换为已确认、在有效期内且来源分级合规的资料，或移除无效引用标记。",
        issues=[i.to_dict() for i in issues],
        details={"citation_count": checked},
    )


def prd_check_r02(
    state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
) -> ComplianceRuleResult:
    issues: list[ComplianceRuleIssue] = []
    checked = 0
    lo = LibraryOrchestrator
    for ch in _chapters(state, project.id, volume):
        for kind, ref in _citations(ch.content or ""):
            if kind != "证" or not ref:
                continue
            evidence = state.library.get(ref)
            if not evidence or evidence.get("company_id") != project.company_id:
                continue
            checked += 1
            tier = evidence.get("source_tier") or "own"
            if tier == "partner":
                if not lo._agreement_present(state, project.id, evidence):
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R02",
                            code="PARTNER_AGREEMENT_MISSING",
                            severity="blocker",
                            message=f"合作伙伴资料缺少联合体/分包协议：[证:{ref}]",
                            chapter_id=ch.id,
                            evidence_id=ref,
                        )
                    )
                else:
                    issues.append(
                        ComplianceRuleIssue(
                            id=new_id("issue"),
                            rule_id="R02",
                            code="PARTNER_SOURCE_HINT",
                            severity="warning",
                            message=f"正文引用合作伙伴资料，请在响应中注明来源：[证:{ref}]",
                            chapter_id=ch.id,
                            evidence_id=ref,
                        )
                    )
            elif tier not in ("own", "partner"):
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R02",
                        code="SOURCE_TIER_MISMATCH",
                        severity="blocker",
                        message=f"资料来源分级与投标主体不一致：[证:{ref}]",
                        chapter_id=ch.id,
                        evidence_id=ref,
                    )
                )
    passed = not any(i.severity in ("blocker", "blocking") for i in issues)
    sev: Literal["blocker", "blocking", "warning", "info"] = (
        "blocker" if any(i.severity == "blocker" for i in issues) else ("warning" if issues else "info")
    )
    return ComplianceRuleResult(
        rule_id="R02",
        title="资料来源分级与投标主体一致",
        severity=sev,
        passed=passed,
        finding_summary="本节引用资料来源分级合规。" if passed else f"发现 {len(issues)} 处来源分级或合作伙伴协议问题。",
        suggestion="合作伙伴资料须登记合作方并上传协议；引用时在正文注明来源。",
        issues=[i.to_dict() for i in issues],
        details={"checked_citations": checked},
    )


def prd_check_r04(
    state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
) -> ComplianceRuleResult:
    issues: list[ComplianceRuleIssue] = []
    today = (
        datetime.fromtimestamp(now_ts, SHANGHAI).date()
        if now_ts
        else datetime.now(SHANGHAI).date()
    )
    horizon = today + timedelta(days=30)
    for item in state.library.values():
        if item.get("company_id") != project.company_id:
            continue
        expiry_raw = item.get("valid_until") or item.get("valid_to")
        if not expiry_raw:
            continue
        try:
            raw = str(expiry_raw).strip()
            expiry = datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                from datetime import date as date_cls

                expiry = date_cls.fromisoformat(raw[:10])
            except ValueError:
                continue
        if today <= expiry <= horizon:
            issues.append(
                ComplianceRuleIssue(
                    id=new_id("issue"),
                    rule_id="R04",
                    code="EVIDENCE_EXPIRING_SOON",
                    severity="info",
                    message=f"资料【{item.get('name', item.get('id'))}】将于 {expiry} 到期，请安排复审或续期。",
                    evidence_id=item.get("id"),
                )
            )
    passed = True
    return ComplianceRuleResult(
        rule_id="R04",
        title="临期与复审提醒",
        severity="info",
        passed=passed,
        finding_summary=(
            f"未来 30 天内有 {len(issues)} 条资料临期，已生成提醒。"
            if issues
            else "暂无临期资料需复审提醒。"
        ),
        suggestion="临期提醒发给资料负责人，请在截止前完成续期或替换。",
        issues=[i.to_dict() for i in issues],
        details={"reminder_count": len(issues)},
    )


def prd_check_r05(
    state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
) -> ComplianceRuleResult:
    return ComplianceRuleResult(
        rule_id="R05",
        title="年审/监督审核有效",
        severity="info",
        passed=True,
        finding_summary="二期规则：MVP 简化版不在导出前强制年审/监督审核字段比对。",
        suggestion="正式递交前由商务人工核对审计报告年度与监督审核状态。",
        issues=[],
        details={"mvp": "deferred"},
    )


def prd_check_r06(
    state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
) -> ComplianceRuleResult:
    issues: list[ComplianceRuleIssue] = []
    company_name = str(getattr(project, "company_name", "") or getattr(project, "name", "") or "").strip()
    for req in workflow.get("requirements", {}).values():
        if volume != "all" and req.get("volume") != volume:
            continue
        for eid in req.get("evidence_ids") or []:
            ev = state.library.get(eid)
            if not ev or ev.get("company_id") != project.company_id:
                continue
            holder = str(ev.get("holder_name") or ev.get("certificate_holder") or ev.get("name") or "")
            if holder and company_name and company_name not in holder and holder not in company_name:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R06",
                        code="CERT_HOLDER_NAME_MISMATCH",
                        severity="warning",
                        message=f"持证单位【{holder}】与投标主体名称可能不一致",
                        requirement_id=req.get("id"),
                        evidence_id=eid,
                    )
                )
    passed = not issues
    return ComplianceRuleResult(
        rule_id="R06",
        title="持证单位与主体名称一致",
        severity="warning" if issues else "info",
        passed=passed,
        finding_summary="持证单位与主体名称未发现明显不一致。" if passed else f"发现 {len(issues)} 处持证单位名称提示。",
        suggestion="核对证书录入字段与营业执照名称；OCR 比对为二期能力。",
        issues=[i.to_dict() for i in issues],
        details={},
    )


def prd_check_r08(
    state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
) -> ComplianceRuleResult:
    issues: list[ComplianceRuleIssue] = []
    staff = workflow.get("staff") or workflow.get("personnel") or []
    if isinstance(staff, dict):
        staff = list(staff.values())
    for row in staff:
        if not isinstance(row, dict):
            continue
        certs = str(row.get("certifications") or row.get("cert_names") or "")
        if row.get("role") and "原厂" in str(row.get("required_cert_hint") or "") and not certs:
            issues.append(
                ComplianceRuleIssue(
                    id=new_id("issue"),
                    rule_id="R08",
                    code="OEM_CERT_MISSING",
                    severity="warning",
                    message=f"拟派人员【{row.get('name', '未知')}】缺少招标产品的原厂认证记录",
                    details={"staff_id": row.get("id")},
                )
            )
    passed = not issues
    return ComplianceRuleResult(
        rule_id="R08",
        title="拟派人员持有原厂认证",
        severity="warning" if issues else "info",
        passed=passed,
        finding_summary="拟派人员原厂认证项已登记。" if passed else f"发现 {len(issues)} 处人员原厂认证缺失提示。",
        suggestion="在排人界面补充原厂认证证书或调整拟派人员。",
        issues=[i.to_dict() for i in issues],
        details={},
    )


def prd_check_r10(
    state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
) -> ComplianceRuleResult:
    issues: list[ComplianceRuleIssue] = []
    for raw in sla_issues(state, project.id):
        code = raw.get("code", "")
        if code not in ("SLA_TEXT_MISMATCH", "SLA_VALUE_INVALID", "SLA_VARIABLE_UNCONFIRMED"):
            continue
        issues.append(
            ComplianceRuleIssue(
                id=new_id("issue"),
                rule_id="R10",
                code=code,
                severity="blocker",
                message=raw.get("message", "SLA 承诺与正文不一致"),
                chapter_id=raw.get("chapter_id"),
                requirement_id=raw.get("requirement_id"),
            )
        )
    passed = not issues
    return ComplianceRuleResult(
        rule_id="R10",
        title="SLA 承诺全文一致",
        severity="blocker" if issues else "info",
        passed=passed,
        finding_summary="正文 SLA 数值与矩阵/变量一致。" if passed else f"发现 {len(issues)} 处 SLA 全文不一致。",
        suggestion="统一章节正文与 SLA 矩阵承诺，使用变量插入或修正手写数值。",
        issues=[i.to_dict() for i in issues],
        details={"mismatch_count": len(issues)},
    )


def prd_check_r12(
    state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
) -> ComplianceRuleResult:
    issues: list[ComplianceRuleIssue] = []
    staff = workflow.get("staff") or []
    if isinstance(staff, dict):
        staff = list(staff.values())
    seen: dict[str, list[str]] = {}
    for row in staff:
        if not isinstance(row, dict):
            continue
        if row.get("status") in ("disabled", "resigned", "离职", "停用"):
            issues.append(
                ComplianceRuleIssue(
                    id=new_id("issue"),
                    rule_id="R12",
                    code="STAFF_INACTIVE",
                    severity="blocker",
                    message=f"停用或离职人员不得拟派：{row.get('name', row.get('id'))}",
                )
            )
        pid = row.get("person_id") or row.get("id")
        if pid:
            seen.setdefault(str(pid), []).append(str(row.get("project_role") or row.get("role") or ""))
    for pid, roles in seen.items():
        if len(roles) > 1:
            issues.append(
                ComplianceRuleIssue(
                    id=new_id("issue"),
                    rule_id="R12",
                    code="STAFF_SCHEDULE_CONFLICT",
                    severity="warning",
                    message=f"人员 {pid} 在同一项目多角色占用：{', '.join(roles)}",
                )
            )
    passed = not any(i.severity == "blocker" for i in issues)
    sev: Literal["blocker", "blocking", "warning", "info"] = (
        "blocker" if any(i.severity == "blocker" for i in issues) else ("warning" if issues else "info")
    )
    return ComplianceRuleResult(
        rule_id="R12",
        title="人员占用冲突、停用离职不得拟派",
        severity=sev,
        passed=passed,
        finding_summary="排人状态正常。" if passed else f"发现 {len(issues)} 处人员冲突或停用问题。",
        suggestion="移除停用/离职人员；冲突项由负责人确认是否调整排班。",
        issues=[i.to_dict() for i in issues],
        details={},
    )


def prd_check_r13(
    state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
) -> ComplianceRuleResult:
    issues: list[ComplianceRuleIssue] = []
    for req in workflow.get("requirements", {}).values():
        if volume != "all" and req.get("volume") != volume:
            continue
        text = str(req.get("text") or "")
        if "业绩" not in text and req.get("category") != "performance":
            continue
        if not req.get("evidence_ids"):
            issues.append(
                ComplianceRuleIssue(
                    id=new_id("issue"),
                    rule_id="R13",
                    code="PERFORMANCE_EVIDENCE_MISSING",
                    severity="warning",
                    message=f"业绩条款缺少证明材料：{text[:50]}",
                    requirement_id=req.get("id"),
                )
            )
    passed = not issues
    return ComplianceRuleResult(
        rule_id="R13",
        title="业绩满足资格与评分条件",
        severity="warning" if issues else "info",
        passed=passed,
        finding_summary="业绩条款证明材料基本齐全。" if passed else f"发现 {len(issues)} 处业绩材料提示。",
        suggestion="补充业绩合同、验收证明并核对年限与签约主体。",
        issues=[i.to_dict() for i in issues],
        details={},
    )


def _scan_placeholders(content: str) -> list[str]:
    found: list[str] = []
    for pattern in PLACEHOLDER_REGEXES:
        for m in pattern.finditer(content):
            found.append(m.group(0))
    return found


def prd_check_r15(
    state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
) -> ComplianceRuleResult:
    issues: list[ComplianceRuleIssue] = []
    for ch in _chapters(state, project.id, volume):
        for token in _scan_placeholders(ch.content or ""):
            issues.append(
                ComplianceRuleIssue(
                    id=new_id("issue"),
                    rule_id="R15",
                    code="PLACEHOLDER_RESIDUAL",
                    severity="blocker",
                    message=f"章节《{ch.title}》残留占位符：{token}",
                    chapter_id=ch.id,
                )
            )
    for req in workflow.get("requirements", {}).values():
        if volume != "all" and req.get("volume") != volume:
            continue
        resp = req.get("response") or ""
        for token in _scan_placeholders(resp):
            sev: Literal["blocker", "blocking"] = "blocker" if is_critical_requirement(req) else "blocking"
            issues.append(
                ComplianceRuleIssue(
                    id=new_id("issue"),
                    rule_id="R15",
                    code="PLACEHOLDER_RESIDUAL",
                    severity=sev,
                    message=f"条款响应残留占位符：{token}",
                    requirement_id=req.get("id"),
                )
            )
    passed = not issues
    overall: Literal["blocker", "blocking", "warning", "info"] = (
        "blocker" if any(i.severity == "blocker" for i in issues) else ("blocking" if issues else "info")
    )
    return ComplianceRuleResult(
        rule_id="R15",
        title="占位符与【待补】清零",
        severity=overall,
        passed=passed,
        finding_summary="未发现【待补】或占位符残留。" if passed else f"发现 {len(issues)} 处占位符/待补残留。",
        suggestion="补录资料或确认事实后替换占位符，导出前须清零。",
        issues=[i.to_dict() for i in issues],
        details={"residual_count": len(issues)},
    )


def prd_check_r16(
    state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
) -> ComplianceRuleResult:
    issues: list[ComplianceRuleIssue] = []
    if getattr(project, "entity_status", None) in ("注销", "吊销", "异常"):
        issues.append(
            ComplianceRuleIssue(
                id=new_id("issue"),
                rule_id="R16",
                code="ENTITY_STATUS_INVALID",
                severity="warning",
                message=f"投标主体状态异常：{project.entity_status}",
            )
        )
    passed = not issues
    return ComplianceRuleResult(
        rule_id="R16",
        title="主体基本资格与证明材料时效",
        severity="warning" if issues else "info",
        passed=passed,
        finding_summary="主体存续状态正常。" if passed else "主体状态或证明材料时效需人工核对。",
        suggestion="立项时核对营业执照存续与财务/纳税证明有效期。",
        issues=[i.to_dict() for i in issues],
        details={},
    )


def prd_check_r17(
    state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
) -> ComplianceRuleResult:
    issues: list[ComplianceRuleIssue] = []
    if getattr(project, "is_confidential", False) or workflow.get("confidential"):
        issues.append(
            ComplianceRuleIssue(
                id=new_id("issue"),
                rule_id="R17",
                code="CONFIDENTIAL_PROJECT_REMINDER",
                severity="info",
                message="涉密项目：引用与导出须遵守保密要求，仅限授权人员查阅完整内容。",
            )
        )
    return ComplianceRuleResult(
        rule_id="R17",
        title="使用提示与保密项目提醒",
        severity="info",
        passed=True,
        finding_summary="已提示引用与保密注意事项。" if issues else "无额外保密提醒。",
        suggestion="涉密项目请在内网环境操作并避免外发完整招标文件。",
        issues=[i.to_dict() for i in issues],
        details={},
    )


def prd_check_r18(
    state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
) -> ComplianceRuleResult:
    hits = workflow.get("similarity_hits") or workflow.get("cross_company_similarity") or []
    issues: list[ComplianceRuleIssue] = []
    threshold = float(workflow.get("similarity_threshold") or 0.85)
    for hit in hits if isinstance(hits, list) else []:
        score = float(hit.get("score") or hit.get("similarity") or 0)
        if score >= threshold:
            issues.append(
                ComplianceRuleIssue(
                    id=new_id("issue"),
                    rule_id="R18",
                    code="CROSS_COMPANY_SIMILARITY",
                    severity="warning",
                    message=f"与集团内其他公司标书段落相似度 {score:.0%} 超过阈值",
                    details=hit,
                )
            )
    passed = not issues
    return ComplianceRuleResult(
        rule_id="R18",
        title="相似度检查（集团内其他公司）",
        severity="warning" if issues else "info",
        passed=passed,
        finding_summary=(
            "未检测到超阈值的跨公司段落相似度。" if passed else f"发现 {len(issues)} 处段落相似度警告。"
        ),
        suggestion="一期仅文本层段落相似度；请人工核对是否存在异常一致。",
        issues=[i.to_dict() for i in issues],
        details={"hit_count": len(issues)},
    )


def prd_check_r20(
    state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
) -> ComplianceRuleResult:
    return ComplianceRuleResult(
        rule_id="R20",
        title="同一编写人跨公司参与（二期）",
        severity="info",
        passed=True,
        finding_summary="二期规则：MVP 不实现跨公司同一自然人编写人识别。",
        suggestion="导出前由集团管理员人工核对编写人归属。",
        issues=[],
        details={"mvp": "phase2"},
    )


def prd_check_r26(
    state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
) -> ComplianceRuleResult:
    issues: list[ComplianceRuleIssue] = []
    plan = workflow.get("writing_plan") or {}
    chapters_plan = plan.get("chapters") or {}
    matrix = workflow.get("requirements") or {}
    for ch_id, ch_plan in chapters_plan.items():
        if volume != "all":
            ch = state.chapters.get(ch_id)
            if ch and ch.volume != volume:
                continue
        assigned = set(ch_plan.get("requirement_ids") or ch_plan.get("matrix_row_ids") or [])
        if not assigned and ch_plan.get("confirmed_at"):
            issues.append(
                ComplianceRuleIssue(
                    id=new_id("issue"),
                    rule_id="R26",
                    code="SCORING_ITEM_UNASSIGNED",
                    severity="warning",
                    message=f"写作方案章节 {ch_id} 未分配评分项/矩阵行",
                    chapter_id=ch_id,
                )
            )
    for ch in _chapters(state, project.id, volume):
        wp = chapters_plan.get(ch.id) or {}
        req_ids = wp.get("requirement_ids") or []
        if not req_ids or not (ch.content or "").strip():
            continue
        for rid in req_ids:
            if rid not in matrix:
                continue
            if rid not in (ch.content or ""):
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R26",
                        code="MATRIX_ROW_NOT_COVERED_IN_BODY",
                        severity="warning",
                        message=f"章节《{ch.title}》正文可能未回应矩阵行 {rid}",
                        chapter_id=ch.id,
                        requirement_id=rid,
                    )
                )
    passed = not issues
    return ComplianceRuleResult(
        rule_id="R26",
        title="评分项覆盖度",
        severity="warning" if issues else "info",
        passed=passed,
        finding_summary="写作方案与正文覆盖度正常。" if passed else f"发现 {len(issues)} 处覆盖度警告。",
        suggestion="确认写作方案已分配全部评分项，正文须有段落回应。",
        issues=[i.to_dict() for i in issues],
        details={},
    )


def prd_check_r27(
    state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
) -> ComplianceRuleResult:
    issues: list[ComplianceRuleIssue] = []
    facts = workflow.get("facts") or workflow.get("project_facts") or []
    if isinstance(facts, dict):
        facts = list(facts.values())
    fact_map = {str(f.get("key") or f.get("label") or ""): f for f in facts if isinstance(f, dict)}
    keywords = ("服务期", "服务地点", "项目名称", "招标人", "项目经理")
    for ch in _chapters(state, project.id, volume):
        text = ch.content or ""
        for key in keywords:
            fact = fact_map.get(key)
            if not fact or fact.get("status") not in (None, "confirmed"):
                continue
            val = str(fact.get("value") or "")
            if val and val not in text and key in text:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R27",
                        code="PROJECT_FACT_MISMATCH",
                        severity="blocker",
                        message=f"章节《{ch.title}》提及【{key}】但与项目事实表取值不一致",
                        chapter_id=ch.id,
                        details={"expected": val},
                    )
                )
    passed = not issues
    return ComplianceRuleResult(
        rule_id="R27",
        title="项目事实一致",
        severity="blocker" if issues else "info",
        passed=passed,
        finding_summary="正文与项目事实表一致。" if passed else f"发现 {len(issues)} 处项目事实不一致。",
        suggestion="修正正文手写值或更新项目事实表后重新确认。",
        issues=[i.to_dict() for i in issues],
        details={},
    )


def prd_check_r28(
    state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
) -> ComplianceRuleResult:
    return ComplianceRuleResult(
        rule_id="R28",
        title="章节模型评审（辅助）",
        severity="info",
        passed=True,
        finding_summary="模型评审在章节循环内单独运行，合规规则引擎仅登记占位提示。",
        suggestion="启用模型评审开关后，在章节循环结果中查看 R28 提示项。",
        issues=[],
        details={"engine": "chapter_loop"},
    )


def prd_check_r32(
    state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
) -> ComplianceRuleResult:
    issues: list[ComplianceRuleIssue] = []
    products = workflow.get("product_list") or workflow.get("tender_products") or []
    if isinstance(products, dict):
        products = list(products.keys())
    known = {str(p).lower() for p in products}
    brand_pattern = re.compile(r"(Oracle|MySQL|DB2|SQL Server|MongoDB|Redis|Kafka|Tomcat|WebLogic)", re.I)
    for ch in _chapters(state, project.id, volume):
        for m in brand_pattern.finditer(ch.content or ""):
            brand = m.group(0)
            if known and brand.lower() not in known and not any(brand.lower() in k for k in known):
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R32",
                        code="PRODUCT_OUT_OF_SCOPE",
                        severity="warning",
                        message=f"章节《{ch.title}》出现清单外产品品牌：{brand}",
                        chapter_id=ch.id,
                    )
                )
    passed = not issues
    return ComplianceRuleResult(
        rule_id="R32",
        title="产品范围一致",
        severity="warning" if issues else "info",
        passed=passed,
        finding_summary="正文产品品牌在招标清单范围内。" if passed else f"发现 {len(issues)} 处清单外品牌提示。",
        suggestion="核对招标产品清单，删除或说明额外品牌。",
        issues=[i.to_dict() for i in issues],
        details={},
    )


_MARKDOWN_PATTERNS = [
    re.compile(r"^#+\s", re.M),
    re.compile(r"\*\*[^*]+\*\*"),
    re.compile(r"```"),
    re.compile(r"^\s*-\s", re.M),
    re.compile(r"\|[^|]+\|"),
]


def prd_check_r34(
    state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
) -> ComplianceRuleResult:
    issues: list[ComplianceRuleIssue] = []
    for ch in _chapters(state, project.id, volume):
        content = ch.content or ""
        for dialogue in AI_CONVERSATION_RESIDUALS:
            if dialogue in content:
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R34",
                        code="AI_CONVERSATION_RESIDUAL",
                        severity="blocker",
                        message=f"章节《{ch.title}》残留对话语句：{dialogue}",
                        chapter_id=ch.id,
                    )
                )
        for pat in _MARKDOWN_PATTERNS:
            if pat.search(content):
                issues.append(
                    ComplianceRuleIssue(
                        id=new_id("issue"),
                        rule_id="R34",
                        code="MARKDOWN_SYMBOL_RESIDUAL",
                        severity="warning",
                        message=f"章节《{ch.title}》残留 Markdown 格式符号",
                        chapter_id=ch.id,
                    )
                )
                break
    passed = not any(i.severity == "blocker" for i in issues)
    sev: Literal["blocker", "blocking", "warning", "info"] = (
        "blocker" if any(i.severity == "blocker" for i in issues) else ("warning" if issues else "info")
    )
    return ComplianceRuleResult(
        rule_id="R34",
        title="AI 痕迹与格式符号残留",
        severity=sev,
        passed=passed,
        finding_summary="未发现 AI 对话或 Markdown 残留。" if passed else f"发现 {len(issues)} 处 AI/格式残留。",
        suggestion="删除对话残留句；Markdown 符号在导出时自动转换或手工清理。",
        issues=[i.to_dict() for i in issues],
        details={},
    )


def remap_ext_result(result: ComplianceRuleResult, ext_id: str, title: str) -> ComplianceRuleResult:
    issues = []
    for item in result.issues:
        row = dict(item)
        row["rule_id"] = ext_id
        issues.append(row)
    return ComplianceRuleResult(
        rule_id=ext_id,
        title=title,
        severity=result.severity,
        passed=result.passed,
        finding_summary=result.finding_summary,
        suggestion=result.suggestion,
        issues=issues,
        details={**result.details, "ext_from_prd_rule": True},
    )
