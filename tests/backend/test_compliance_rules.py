# ISSUE-046：PRD 编号对齐后 R01/R02 单元测试；错位旧逻辑改 EXT-* 见 test_compliance_rules_p0.py。

import pytest
from icg.domain.domain import Chapter, DemoState, Project
from icg.domain.compliance_rules import ComplianceRulesEngine


def test_compliance_rules_catalog():
    catalog = ComplianceRulesEngine.CATALOG
    rule_ids = [r["rule_id"] for r in catalog]
    for core_rule in ["R01", "R02", "R15", "R23", "R34", "R35", "R37"]:
        assert core_rule in rule_ids
    assert len(rule_ids) >= 26
    for item in catalog:
        assert item["rule_id"].startswith("R") or item["rule_id"].startswith("EXT-")
        assert "title" in item
        assert "default_severity" in item
        assert "description" in item


def test_r01_invalid_evidence_citation_blocked():
    state = DemoState()
    project = Project("p1", "智慧政务平台", "alpha", 1, tender_number="GOV-2026-CLOUD-088")
    state.library["ev-bad"] = {
        "id": "ev-bad",
        "company_id": "alpha",
        "name": "未确认资质",
        "status": "pending",
        "type": "certificate",
    }
    state.chapters["c1"] = Chapter(
        "c1", "p1", "技术方案", "technical", "依据 [证:ev-bad] 提供资质证明。"
    )
    res = ComplianceRulesEngine.check_r01(state, project, {})
    assert res.passed is False
    assert res.severity == "blocker"
    assert any(i["code"] == "EVIDENCE_NOT_CONFIRMED" for i in res.issues)


def test_r01_valid_citation_passes():
    state = DemoState()
    project = Project("p1", "智慧政务平台", "alpha", 1)
    state.library["ev-ok"] = {
        "id": "ev-ok",
        "company_id": "alpha",
        "name": "已确认资质",
        "status": "confirmed",
        "type": "certificate",
        "valid_until": "2028-12-31",
    }
    state.chapters["c1"] = Chapter("c1", "p1", "技术方案", "technical", "依据 [证:ev-ok] 说明。")
    res = ComplianceRulesEngine.check_r01(state, project, {})
    assert res.passed is True


def test_ext_tender_name_consistency_legacy():
    state = DemoState()
    project = Project("p1", "智慧政务平台", "alpha", 1, tender_number="GOV-2026-CLOUD-088")
    state.chapters["c1"] = Chapter("c1", "p1", "技术方案", "technical", "按照 GOV-2026-CLOUD-088 招标文件要求建设...")
    state.chapters["c2"] = Chapter("c2", "p1", "商务方案", "business", "根据 ABC-2024-OLD-001 要求...")
    res_err = ComplianceRulesEngine.check_ext_consistency_tender_name(state, project, {})
    assert res_err.rule_id == "EXT-CONSISTENCY-TENDER-NAME"
    assert res_err.passed is False
    assert any(i["code"] == "TENDER_NUMBER_CONFLICT" for i in res_err.issues)


def test_ext_qualification_original_commitment():
    state = DemoState()
    project = Project("p1", "智慧城市项目", "alpha", 1)
    workflow_err = {
        "requirements": {
            "req-1": {
                "id": "req-1",
                "text": "投标人须提供安全生产许可证原件备查",
                "is_disqualification": True,
                "response": "我司已上传安全生产许可证扫描件。",
            }
        }
    }
    res_err = ComplianceRulesEngine.check_ext_qualification_original(state, project, workflow_err)
    assert res_err.rule_id == "EXT-QUALIFICATION-ORIGINAL"
    assert res_err.passed is False
    assert res_err.issues[0]["code"] == "QUALIFICATION_ORIGINAL_COMMITMENT_MISSING"


def test_r35_self_designation_and_counterparty():
    state = DemoState()
    project = Project("p1", "系统项目", "alpha", 1)
    state.chapters["c1"] = Chapter("c1", "p1", "方案1", "technical", "我方根据贵方要求制定了高可用方案。")
    state.chapters["c2"] = Chapter("c2", "p1", "方案2", "technical", "我方承诺在约定期限内完成。")
    res_ok = ComplianceRulesEngine.check_r35(state, project, {})
    assert res_ok.passed is True

    state.chapters["c3"] = Chapter("c3", "p1", "方案3", "business", "本单位向甲方承诺，我们公司与我司将共同协作。")
    res_warn = ComplianceRulesEngine.check_r35(state, project, {})
    assert res_warn.passed is False
    assert res_warn.severity == "warning"


def test_evaluate_p0_rules_includes_prd_and_ext():
    state = DemoState()
    project = Project("p1", "完整合规评估项目", "alpha", 1, tender_number="SEC-2026-999")
    workflow = {"requirements": {}}
    results = ComplianceRulesEngine.evaluate_p0_rules(state, project, workflow)
    ids = [r.rule_id for r in results]
    assert ids == [
        "R01",
        "EXT-CONSISTENCY-TENDER-NAME",
        "R02",
        "EXT-QUALIFICATION-ORIGINAL",
        "R15",
        "EXT-PROOF-MATERIAL",
        "R23",
        "R34",
        "EXT-PLACEHOLDER-LEGACY",
        "R35",
        "R37",
    ]
