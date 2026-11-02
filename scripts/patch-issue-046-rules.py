from pathlib import Path
import re

path = Path("backend/bid-core/icg/domain/compliance_rules.py")
text = path.read_text(encoding="utf-8")

misaligned = [
    ("01", "check_ext_consistency_tender_name", "EXT-CONSISTENCY-TENDER-NAME", "招标单位与项目名称提取一致性核验"),
    ("02", "check_ext_qualification_original", "EXT-QUALIFICATION-ORIGINAL", "资质有效性与原件备查承诺核验"),
    ("04", "check_ext_consortium_agreement", "EXT-CONSORTIUM-AGREEMENT", "联合体投标协议核验"),
    ("05", "check_ext_financial_metrics", "EXT-FINANCIAL-METRICS", "财务指标核验（资产负债率、净利润连续性）"),
    ("06", "check_ext_performance_case", "EXT-PERFORMANCE-CASE", "业绩案例核验"),
    ("08", "check_ext_delivery_timeline", "EXT-DELIVERY-TIMELINE", "交付周期与进度计划偏离核验"),
    ("10", "check_ext_warranty_response_legacy", "EXT-WARRANTY-RESPONSE-LEGACY", "质保期与服务响应时间核验（旧）"),
    ("12", "check_ext_sla_warranty_deviation", "EXT-SLA-WARRANTY-DEVIATION", "服务响应 SLA 与质保期偏离核验"),
    ("13", "check_ext_team_staffing", "EXT-TEAM-STAFFING", "团队人员配置核验"),
    ("15", "check_ext_proof_material", "EXT-PROOF-MATERIAL", "证明材料齐全性核验"),
    ("16", "check_ext_bid_security", "EXT-BID-SECURITY", "投标保证金与保函有效性核验"),
    ("17", "check_ext_conflict_interest", "EXT-CONFLICT-INTEREST", "关联交易与利害关系回避核验"),
    ("18", "check_ext_consortium_qualification", "EXT-CONSORTIUM-QUALIFICATION", "联合体投标协议与资质认定核验"),
    ("20", "check_ext_quotation_collusion", "EXT-QUOTATION-COLLUSION", "报价雷同排查"),
    ("26", "check_ext_ip_indemnity", "EXT-IP-INDEMNITY", "知识产权与侵权无争议声明核验"),
    ("27", "check_ext_local_service", "EXT-LOCAL-SERVICE", "本地化服务网点与常驻技术力量核验"),
    ("28", "check_ext_critical_tech_deviation", "EXT-CRITICAL-TECH-DEVIATION", "关键技术规格实质性负偏离排查"),
    ("32", "check_ext_bid_validity", "EXT-BID-VALIDITY", "投标有效期与承诺不可撤销性核验"),
    ("34", "check_ext_placeholder_legacy", "EXT-PLACEHOLDER-LEGACY", "占位符与待补残留核验（旧合订）"),
]

prd_fn = {num: f"prd_check_r{num}" for num, *_ in misaligned}

for num, *_ in misaligned:
    pat = rf"(    @classmethod\n    def check_r{num}\()"
    repl = rf"    @classmethod\n    def _legacy_misaligned_r{num}("
    new_text, n = re.subn(pat, repl, text, count=1)
    if n != 1:
        raise SystemExit(f"rename failed for R{num}: {n}")
    text = new_text

anchor = "    @classmethod\n    def evaluate_p5_rules("
insert_blocks = []
for num, ext_method, ext_id, ext_title in misaligned:
    insert_blocks.append(
        f"""
    @classmethod
    def check_r{num}(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
    ) -> ComplianceRuleResult:
        from icg.domain.compliance_prd_checks import {prd_fn[num]}
        return {prd_fn[num]}(state, project, workflow, volume=volume, now_ts=now_ts)

    @classmethod
    def {ext_method}(
        cls, state: DemoState, project: Any, workflow: dict[str, Any], volume: str = "all", now_ts: float | None = None
    ) -> ComplianceRuleResult:
        from icg.domain.compliance_prd_checks import remap_ext_result
        legacy_kwargs = {{"volume": volume}}
        if "{num}" in ("06", "15"):
            legacy_kwargs["now_ts"] = now_ts
        legacy = cls._legacy_misaligned_r{num}(state, project, workflow, **legacy_kwargs)
        return remap_ext_result(legacy, "{ext_id}", "{ext_title}")
"""
    )

if anchor not in text:
    raise SystemExit("anchor not found")
text = text.replace(anchor, "".join(insert_blocks) + anchor, 1)
path.write_text(text, encoding="utf-8")
print("patched", path)
