# 为什么有这个文件：核对 ISSUE-060 条款清洗——碎片补全/过滤、非技术条款范围标记与审计。
from __future__ import annotations

from icg.domain.technical_clause_cleaning import clean_technical_requirements


def _row(rid, text, quote="", page=1, kind="spec"):
    return {
        "id": rid, "text": text, "technical_clause": True, "status": "pending",
        "section_kind": kind, "source": {"page": page, "quote": quote or text, "file_id": "f1"},
    }


def _workflow(rows, page_text=""):
    workflow = {"requirements": {row["id"]: row for row in rows}}
    if page_text:
        workflow["files"] = {"f1": {"pages": [page_text]}}
    return workflow


def test_fragment_completed_from_page_text():
    page = "服务内容如下：\n运维服务地点：重庆市渝中区。\n年度服务费按年支付。"
    row = _row("r1", "运维服务地点：", quote="运维服务地点")
    workflow = _workflow([row], page)
    audit = clean_technical_requirements(workflow)
    assert workflow["requirements"]["r1"]["text"] == "运维服务地点：重庆市渝中区。"
    assert len(audit["completed"]) == 1


def test_fragment_completed_preserves_digits():
    page = "年度服务费为¥5000元整，按年支付。"
    row = _row("r1", ") ，年度 服务费为¥ 元", quote="年度服务费")
    workflow = _workflow([row], page)
    audit = clean_technical_requirements(workflow)
    text = workflow["requirements"]["r1"]["text"]
    assert "5000" in text and len(audit["completed"]) == 1


def test_unrecoverable_fragment_filtered_not_deleted():
    row = _row("r1", "运维任务:（见服务方", quote="不存在的原文锚点")
    workflow = _workflow([row], "完全不同的页面内容，没有任何匹配文字。")
    audit = clean_technical_requirements(workflow)
    item = workflow["requirements"]["r1"]
    assert item["id"] == "r1"
    assert item["requirement_scope"] == "fragment_filtered"
    assert len(audit["filtered"]) == 1


def test_short_fragment_without_anchor_not_passed_through_raw():
    row = _row("r1", "三年", quote="")
    workflow = _workflow([row], "合作期限为三年，自合同签订之日起。")
    clean_technical_requirements(workflow)
    item = workflow["requirements"]["r1"]
    # 无锚点极短碎片：要么被补全要么被过滤，绝不原样进入技术清单
    assert item.get("requirement_scope") == "fragment_filtered" or len(item["text"]) > 4


def test_non_tech_business_clauses_marked_and_auditable():
    samples = [
        ("r1", "投标报价不得高于最高限价"),
        ("r2", "需提供基本账户证明"),
        ("r3", "投标人不得进入清算或破产程序"),
        ("r4", "投标文件应按第六章格式编写"),
        ("r5", "投标文件修改需书面通知"),
    ]
    rows = [_row(rid, text) for rid, text in samples]
    rows.append(_row("r6", "每月巡检数据库并出具报告"))
    workflow = _workflow(rows)
    audit = clean_technical_requirements(workflow)
    for rid, _ in samples:
        item = workflow["requirements"][rid]
        assert item["requirement_scope"] == "non_technical", rid
        assert item.get("non_tech_category")
    assert workflow["requirements"]["r6"]["requirement_scope"] == "technical"
    assert len(audit["non_technical"]) == 5


def test_cleaning_is_idempotent():
    page = "运维服务地点：重庆市渝中区。"
    row = _row("r1", "运维服务地点：", quote="运维服务地点")
    workflow = _workflow([row], page)
    first = clean_technical_requirements(workflow)
    text_after = workflow["requirements"]["r1"]["text"]
    second = clean_technical_requirements(workflow)
    assert second["checked"] == 0
    assert workflow["requirements"]["r1"]["text"] == text_after
    assert len(first["completed"]) == 1


def test_filtered_and_non_tech_excluded_from_digest_rows():
    from icg.domain.technical_digest import build_digest

    rows = [
        _row("r1", "投标报价不得高于最高限价"),
        _row("r2", "每月巡检数据库并出具报告"),
    ]
    workflow = _workflow(rows)
    clean_technical_requirements(workflow)
    digest = build_digest(workflow)
    texts = [item["text"] for item in digest["tech"]]
    assert any("巡检" in text for text in texts)
    assert not any("限价" in text for text in texts)


def test_matrix_fill_never_writes_negative_deviation_on_non_tech():
    from icg.domain.technical_matrix import fill_technical_responses

    rows = [_row("r1", "投标报价不得高于最高限价"), _row("r2", "每月巡检数据库并出具报告")]
    workflow = _workflow(rows)
    clean_technical_requirements(workflow)
    fill_technical_responses(None, workflow, model=None, search=lambda clause: [])
    item = workflow["requirements"]["r1"]
    assert item.get("deviation_type") != "负偏离"
    assert "负偏离" not in str(item.get("response") or "")
    assert item.get("response_type") is None  # 不检索不拟写，直接跳过


def test_deviation_entries_skip_cleaned_rows():
    from icg.domain.technical_volume import _deviation_entries

    rows = [_row("r1", "投标报价不得高于最高限价"), _row("r2", "每月巡检数据库并出具报告")]
    workflow = _workflow(rows)
    clean_technical_requirements(workflow)
    workflow["requirements"]["r2"]["response"] = "完全响应"
    workflow["requirements"]["r2"]["deviation_type"] = "无偏离"
    entries = _deviation_entries({}, workflow)
    texts = [str(entry) for entry in entries]
    assert not any("限价" in text for text in texts)


def test_cq_qualification_and_format_noise_samples_are_non_technical():
    samples = [
        ("r1", "投标人应具备独立法人资格"),
        ("r2", "须具备独立承担民事责任能力"),
        ("r3", "投标人及法定代表人未被列入烟草行业不良行为名单"),
        ("r4", "不得提交备选技术方案"),
        ("r5", "不得为招标代理或相关咨询方"),
        ("r6", "不得存在利害关系或控股关系"),
    ]
    workflow = _workflow([_row(rid, text) for rid, text in samples])
    clean_technical_requirements(workflow)
    for rid, _ in samples:
        assert workflow["requirements"][rid]["requirement_scope"] == "non_technical", rid


def test_mid_sentence_truncation_is_completed_from_source_page():
    page = "5.5 乙方须保证遵守甲方的相关保密规定，未经许可不得复制、带走和传播本项目的技术方案和资料，以及涉及的其他信息。"
    row = _row("r1", "守甲方的相关保密规定，未经许可不", quote="守甲方的相关保密规定")
    workflow = _workflow([row], page)
    clean_technical_requirements(workflow)
    item = workflow["requirements"]["r1"]
    assert item["requirement_scope"] == "technical"
    assert item["fragment_completed"] is True
    assert "不得复制、带走和传播" in item["text"]


def test_mid_word_truncation_is_completed_without_heading_leakage():
    page = "4、运维服务范围\n投标人应在运维项目情况介绍中所叙述的系统应用范围内提供全面运维服务，保障系统高效稳定运行。"
    row = _row("r1", "投标人应在运维项目情况介绍中所", quote="投标人应在运维项目情况介绍中所")
    workflow = _workflow([row], page)
    clean_technical_requirements(workflow)
    item = workflow["requirements"]["r1"]
    assert item["requirement_scope"] == "technical"
    assert item["text"].startswith("投标人应在运维项目情况介绍中")
    assert "运维服务范围投标人" not in item["text"]


def test_generic_section_heading_is_filtered_not_expanded():
    page = "4、运维服务范围\n投标人应在运维项目情况介绍中所叙述的系统应用范围内提供全面运维服务。"
    row = _row("r1", "运维服务范围", quote="运维服务范围")
    workflow = _workflow([row], page)
    clean_technical_requirements(workflow)
    assert workflow["requirements"]["r1"]["requirement_scope"] == "fragment_filtered"


def test_completed_text_is_reclassified_when_full_context_is_qualification():
    page = "（4）不得挂靠其他单位，或从其他单位挂靠受让或租用营运车辆，或提供咨询服务；（5）被依法暂停或者取消投标资格。"
    row = _row("r1", "或提供咨询服务", quote="或提供咨询服务")
    workflow = _workflow([row], page)
    clean_technical_requirements(workflow)
    item = workflow["requirements"]["r1"]
    assert item["requirement_scope"] == "non_technical"
    assert item["non_tech_category"] in {"qualification", "business_or_packaging"}


def test_cross_reference_placeholder_completion_is_not_accepted():
    page = "1.1运维任务:（见服务方案，此方案在签订洽谈合同时拟定）\n1.2运维内容：（见服务方案，此方案在签订洽谈合同时拟定）"
    row = _row("r1", "运维任务:（见服务方", quote="运维任务:（见服务方")
    workflow = _workflow([row], page)
    clean_technical_requirements(workflow)
    assert workflow["requirements"]["r1"]["requirement_scope"] == "fragment_filtered"


def test_blank_contract_scope_completion_is_not_accepted():
    page = "1.3运维范围：甲方委托乙方承担运维范围为系统应用范围，包括：\n，共计     个单位的运行维护工作。"
    row = _row("r1", "运维范围：甲方委托乙", quote="运维范围：甲方委托乙")
    workflow = _workflow([row], page)
    clean_technical_requirements(workflow)
    assert workflow["requirements"]["r1"]["requirement_scope"] == "fragment_filtered"


def test_service_fee_amount_is_pricing_not_technical():
    page = "3.1 合同总金额：为中标金额 ¥    元 (大写：人民币      元整) ，年度 服务费为¥    元 (大写：人民币      元整)。"
    row = _row("r1", ") ，年度 服务费为¥ 元", quote="年度 服务费为¥ 元")
    workflow = _workflow([row], page)
    clean_technical_requirements(workflow)
    item = workflow["requirements"]["r1"]
    assert item["requirement_scope"] == "non_technical"
    assert item["non_tech_category"] == "pricing"


def test_fragment_completion_stops_at_missing_closing_parenthesis():
    from icg.domain.technical_clause_cleaning import complete_fragment_text

    source = (
        "6.2 乙方提供5*8小时的现场值守服务。在各法定节假日，均按照甲方需求安排驻点值班人员提供现场值守服务。"
        "（未要求驻场的标段不含本条）6.3 乙方应及时对故障进行解决。"
    )
    fragment = "均按照 甲方需求安排驻点值班人员提供现场值守服务。（未要求驻场的标段不含本条"
    completed = complete_fragment_text(fragment, "", source)
    assert "驻点值班人员提供现场值守服务" in completed
    assert "未要求驻场的标段不含本条）" in completed
    assert "乙方应及时对故障进行解决" not in completed


def test_decimal_time_limit_is_not_stripped_as_clause_number():
    from icg.domain.technical_clause_cleaning import complete_fragment_text

    source = "6.2 乙方须在故障发生后0.5小时内到场，2小时内恢复服务。"
    fragment = "乙方须在故障发生后0.5小时内到场"
    completed = complete_fragment_text(fragment, "", source)
    assert "0.5小时内到场" in completed
    assert "2小时内恢复服务" in completed
    assert completed.startswith("乙方须在故障发生后")


def test_non_tech_rules_do_not_hit_payment_clearing_interface_or_sla_contract_clause():
    from icg.domain.technical_clause_cleaning import non_tech_category

    assert non_tech_category("跨行支付清算接口应支持秒级交易确认与异常告警") == ""
    assert non_tech_category("合同履行过程中，乙方须在故障发生后0.5小时内到场并恢复服务") == ""
    assert non_tech_category("投标人进入清算或破产程序") == "qualification"
    assert non_tech_category("合同履行过程中，双方按季度结算付款") == "business_or_packaging"


def test_short_scoring_point_with_valid_metadata_is_not_filtered():
    row = _row("s1", "项目组织", kind="scoring", quote="3 | 项目组织 | 15 | 100")
    row.update(score_item="运维响应能力", score=15)
    workflow = _workflow([row])
    clean_technical_requirements(workflow)
    assert row["requirement_scope"] == "technical"
    from icg.domain.technical_digest import build_digest
    digest = build_digest(workflow)
    points = [point for group in digest["scoring"] for point in group["points"]]
    assert any(point["text"] == "项目组织" for point in points)


def test_r09_skips_non_technical_payment_but_keeps_real_service_period_check():
    from icg.domain.compliance_rules import ComplianceRulesEngine

    payment = _row("pay", "服务期内每季度支付一次进度款")
    payment.update(requirement_scope="non_technical", non_tech_category="payment")
    service = _row("svc", "服务期限：三年")
    service.update(response="", volume="technical")
    result = ComplianceRulesEngine.check_r09(None, None, {"requirements": {"pay": payment, "svc": service}})
    codes = [issue["code"] for issue in result.issues]
    assert codes == ["SERVICE_PERIOD_COMMITMENT_MISSING"]
    assert result.issues[0]["requirement_id"] == "svc"


def test_deviation_clause_prefers_completed_clean_text_over_short_quote():
    from icg.domain.technical_volume import complete_clause_text

    row = {
        "text": "乙方须在故障发生后0.5小时内到场，2小时内恢复服务。",
        "extracted_summary": "0.5小时内到场",
        "fragment_completed": True,
        "source": {"quote": "6.2 乙方须在故障发生后0.5小时内到场"},
    }
    assert complete_clause_text(row) == "乙方须在故障发生后0.5小时内到场，2小时内恢复服务。"
