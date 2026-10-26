# 为什么有这个文件：验证 PRD P0 级合规规则体系（R01, R02, R15, R23, R34, R35, R37）的正确性。
# 它解决什么问题：
# 1. 验证规则目录（CATALOG）完整性，包含全部 7 项核心规则；
# 2. 验证 R01（招标编号与项目名称一致性）、R02（资质有效性与原件备查承诺）、R35（主体自称与称谓统一性）逻辑；
# 3. 验证端到端评估引擎返回结构化结果、严重级别与阻断判定。

import pytest
from icg.domain.domain import Chapter, DemoState, Project
from icg.domain.compliance_rules import ComplianceRulesEngine


def test_compliance_rules_catalog():
    catalog = ComplianceRulesEngine.CATALOG
    rule_ids = [r["rule_id"] for r in catalog]
    assert rule_ids == ["R01", "R02", "R15", "R23", "R34", "R35", "R37"]
    for item in catalog:
        assert item["rule_id"] in ("R01", "R02", "R15", "R23", "R34", "R35", "R37")
        assert "title" in item
        assert "default_severity" in item
        assert "description" in item


def test_r01_tender_number_consistency():
    state = DemoState()
    project = Project("p1", "智慧政务平台", "alpha", 1, tender_number="GOV-2026-CLOUD-088")
    
    # 正常情况：编号一致
    state.chapters["c1"] = Chapter("c1", "p1", "技术方案", "technical", "按照 GOV-2026-CLOUD-088 招标文件要求建设...")
    res = ComplianceRulesEngine.check_r01(state, project, {})
    assert res.passed is True
    assert len(res.issues) == 0

    # 异常情况：出现冲突的招标编号（串标或复制粘贴遗留）
    state.chapters["c2"] = Chapter("c2", "p1", "商务方案", "business", "根据 ABC-2024-OLD-001 要求...")
    res_err = ComplianceRulesEngine.check_r01(state, project, {})
    assert res_err.passed is False
    assert res_err.severity == "blocker"
    assert any(i["code"] == "TENDER_NUMBER_CONFLICT" for i in res_err.issues)


def test_r02_qualification_original_commitment():
    state = DemoState()
    project = Project("p1", "智慧城市项目", "alpha", 1)
    
    # 未承诺原件备查 -> blocker
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
    res_err = ComplianceRulesEngine.check_r02(state, project, workflow_err)
    assert res_err.passed is False
    assert res_err.severity == "blocker"
    assert res_err.issues[0]["code"] == "QUALIFICATION_ORIGINAL_COMMITMENT_MISSING"

    # 正确承诺 -> passed
    workflow_ok = {
        "requirements": {
            "req-1": {
                "id": "req-1",
                "text": "投标人须提供安全生产许可证原件备查",
                "is_disqualification": True,
                "response": "我方承诺按招标要求提供真实有效的安全生产许可证原件备查。",
            }
        }
    }
    res_ok = ComplianceRulesEngine.check_r02(state, project, workflow_ok)
    assert res_ok.passed is True
    assert len(res_ok.issues) == 0


def test_r35_self_designation_and_counterparty():
    state = DemoState()
    project = Project("p1", "系统项目", "alpha", 1)
    
    # 正常情况：自称统一为“我方”，对招标人称“贵方”
    state.chapters["c1"] = Chapter("c1", "p1", "方案1", "technical", "我方根据贵方要求制定了高可用方案。")
    state.chapters["c2"] = Chapter("c2", "p1", "方案2", "technical", "我方承诺在约定期限内完成。")
    res_ok = ComplianceRulesEngine.check_r35(state, project, {})
    assert res_ok.passed is True
    assert len(res_ok.issues) == 0

    # 出现不规范的“甲方”称谓与混乱自称
    state.chapters["c3"] = Chapter("c3", "p1", "方案3", "business", "本单位向甲方承诺，我们公司与我司将共同协作。")
    res_warn = ComplianceRulesEngine.check_r35(state, project, {})
    assert res_warn.passed is False
    assert res_warn.severity == "warning"
    codes = [i["code"] for i in res_warn.issues]
    assert "COUNTERPARTY_DESIGNATION_IRREGULAR" in codes
    assert "SELF_DESIGNATION_INCONSISTENT" in codes


def test_evaluate_p0_rules_returns_seven_rules():
    state = DemoState()
    project = Project("p1", "完整合规评估项目", "alpha", 1, tender_number="SEC-2026-999")
    workflow = {"requirements": {}}
    results = ComplianceRulesEngine.evaluate_p0_rules(state, project, workflow)
    assert len(results) == 7
    ids = [r.rule_id for r in results]
    assert ids == ["R01", "R02", "R15", "R23", "R34", "R35", "R37"]
