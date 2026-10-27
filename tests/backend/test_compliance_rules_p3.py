# 为什么有这个文件：为 PRD MVP §5.8 第四批核心合规规则（R05/R06/R08/R12/R20，BE-COMPLIANCE-RULES-P3）提供专属自动化测试套件。
# 它解决什么问题：
# 1. 验证 R05 财务指标核验（资产负债率超标、净利润亏损或资不抵债强阻断，正例放行）；
# 2. 验证 R06 业绩案例核验（合同金额门槛不足、缺少双方签字盖章页、缺少验收证明或超出近三年有效期限强阻断，正例放行）；
# 3. 验证 R08 交付周期与进度计划偏离核验（承诺交付天数超过招标上限或工期负偏离强阻断，正例放行）；
# 4. 验证 R12 服务响应 SLA 与质保期偏离核验（承诺质保年限低于最低基线或现场到达响应时间超时强阻断，正例放行）；
# 5. 验证 R20 报价雷同排查（分项报价比例异常一致、复制其他投标主体报价或串标特征强阻断，正例放行）；
# 6. 验证整本递交导出门禁联动（存在上述任一 blocker 缺陷时，正式递交版 submission 严格触发 400 CHECK_BLOCKER_EXISTS）。

import uuid
import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from test_reference_flow import ProjectFlow, client, login


def test_r05_financial_metrics_compliance(client):
    """验证 R05：财务指标核验（资产负债率、净利润连续性，正例放行，负债率超标/净利润亏损/资不抵债强阻断）。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r_biz = next(r for r in reqs if r["volume"] == "business")

    # 1. 正例：资产负债率 55%（<= 70%），近三年净利润均为正，提供合规财务审计报告
    audit_ev = flow.library(
        name="2023-2025年度企业财务审计报告",
        content="经会计师事务所审计：企业资产负债率为55.2%，近三年净利润分别为1200万元、1500万元、1800万元，经营财务状况良好。",
        valid_until="2027-12-31",
        type="qualification",
    )
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "text": "财务状况要求：投标人资产负债率不超过70%，近三年净利润为正，须提供经审计的财务审计报告。",
            "category": "financial",
            "evidence_ids": [audit_ev["id"]],
            "status": "confirmed",
            "response": "我方财务状况稳健，资产负债率为55.2%，近三年净利润持续为正且连年增长，已附三年审计报告。",
        },
        "PATCH",
    )

    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    r05 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R05")
    assert r05["passed"] is True
    assert r05["severity"] == "info"

    # 2. 反例 A：资产负债率超出招标文件限额（如 82% > 70%）-> blocker (FINANCIAL_METRICS_NON_COMPLIANT)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "response": "我方由于前期固定资产集中投资，当前资产负债率为82.5%，超出常规控制标准。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r05 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R05")
    assert r05["passed"] is False
    assert r05["severity"] == "blocker"
    assert any(i["code"] == "FINANCIAL_METRICS_NON_COMPLIANT" for i in r05["issues"])

    # 3. 反例 B：近三年出现年度亏损或净利润为负 -> blocker (FINANCIAL_METRICS_NON_COMPLIANT)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "response": "我方资产负债率为60%，但受市场波动影响，2024年度出现亏损，净利润为负。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r05 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R05")
    assert r05["passed"] is False
    assert r05["severity"] == "blocker"
    assert any(i["code"] == "FINANCIAL_METRICS_NON_COMPLIANT" for i in r05["issues"])

    # 4. 反例 C：未作响应承诺 -> blocker (FINANCIAL_METRICS_NON_COMPLIANT)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "response": "",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r05 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R05")
    assert r05["passed"] is False
    assert r05["severity"] == "blocker"
    assert any(i["code"] == "FINANCIAL_METRICS_NON_COMPLIANT" for i in r05["issues"])

    # 5. 反例 D：严重资不抵债或实质性负偏离 -> blocker (FINANCIAL_METRICS_NON_COMPLIANT)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "response": "我方当前企业严重资不抵债，无法满足招标财务指标要求。",
            "deviation_type": "negative",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r05 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R05")
    assert r05["passed"] is False
    assert r05["severity"] == "blocker"
    assert any(i["code"] == "FINANCIAL_METRICS_NON_COMPLIANT" for i in r05["issues"])


def test_r06_performance_case_sufficiency(client):
    """验证 R06：业绩案例核验（金额门槛、类似项目、签字盖章页与验收证明，正例放行，金额不足/缺盖章/缺验收/超期强阻断）。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r_biz = next(r for r in reqs if r["volume"] == "business")

    # 1. 正例：合同金额 680 万元（门槛 500 万），近三年签订，附带双方签字盖章页与验收报告
    case_ev = flow.library(
        name="某省智慧政务中台系统建设项目合同及验收报告",
        content="合同金额：680万元；签订日期：2024年6月；附双方法定代表人签字盖章页及终验验收合格证明报告。",
        valid_until="2028-12-31",
        type="performance",
    )
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "text": "业绩要求：投标人须提供近三年内单项合同金额不低于500万元的类似项目业绩，须提供合同双方签字盖章页及验收证明。",
            "category": "performance",
            "evidence_ids": [case_ev["id"]],
            "status": "confirmed",
            "response": "我方提供某省智慧政务中台系统业绩，合同金额为680万元，2024年合同，已附双方签字盖章页与验收报告。",
        },
        "PATCH",
    )

    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    r06 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R06")
    assert r06["passed"] is True
    assert r06["severity"] == "info"

    # 2. 反例 A：业绩案例金额未达到门槛要求（260万元 < 500万元）-> blocker (PERFORMANCE_CASE_INSUFFICIENT)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "response": "我方提供类似项目业绩，合同金额为260万元，已完成项目验收。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r06 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R06")
    assert r06["passed"] is False
    assert r06["severity"] == "blocker"
    assert any(i["code"] == "PERFORMANCE_CASE_INSUFFICIENT" for i in r06["issues"])

    # 3. 反例 B：缺少双方签字盖章页证明材料 -> blocker (PERFORMANCE_CASE_INSUFFICIENT)
    no_stamp_ev = flow.library(
        name="某市信息系统合同（缺少盖章页）",
        content="合同金额：600万元；注意：因原件遗失，本材料缺少盖章页，仅为内部草稿版本。",
        valid_until="2028-12-31",
        type="performance",
    )
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "evidence_ids": [no_stamp_ev["id"]],
            "response": "合同金额600万元，但原件遗失导致缺少盖章页。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r06 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R06")
    assert r06["passed"] is False
    assert r06["severity"] == "blocker"
    assert any(i["code"] == "PERFORMANCE_CASE_INSUFFICIENT" for i in r06["issues"])

    # 4. 反例 C：缺少验收证明或验收报告 -> blocker (PERFORMANCE_CASE_INSUFFICIENT)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "evidence_ids": [case_ev["id"]],
            "response": "合同金额为680万元，双方盖章齐全，但项目尚在实施阶段，缺少验收证明材料。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r06 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R06")
    assert r06["passed"] is False
    assert r06["severity"] == "blocker"
    assert any(i["code"] == "PERFORMANCE_CASE_INSUFFICIENT" for i in r06["issues"])

    # 5. 反例 D：业绩签订时间超出近三年范围（2019年合同）-> blocker (PERFORMANCE_CASE_INSUFFICIENT)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "evidence_ids": [case_ev["id"]],
            "response": "提供2019年合同业绩，合同金额为800万元，合同超出3年有效期。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r06 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R06")
    assert r06["passed"] is False
    assert r06["severity"] == "blocker"
    assert any(i["code"] == "PERFORMANCE_CASE_INSUFFICIENT" for i in r06["issues"])


def test_r08_delivery_timeline_deviation(client):
    """验证 R08：交付周期与进度计划偏离核验（正例放行，承诺周期超出上限/工期负偏离/未承诺强阻断）。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r_tech = next(r for r in reqs if r["volume"] == "technical")

    # 1. 正例：招标要求 60 日历天，投标承诺 45 日历天完成交付
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "text": "交付周期要求：自合同签订之日起不超过60日历天内完成交付并上线验收。",
            "category": "schedule",
            "status": "confirmed",
            "response": "我方完全响应交付进度要求，承诺交付周期为45日历天，配置专项敏捷交付团队。",
        },
        "PATCH",
    )

    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    r08 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R08")
    assert r08["passed"] is True
    assert r08["severity"] == "info"

    # 2. 反例 A：承诺交付周期超过招标上限（90日历天 > 60日历天）-> blocker (DELIVERY_TIMELINE_NEGATIVE_DEVIATION)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "response": "经工程评估，本项目整体承诺90日历天内完成交付，以确保交付质量。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r08 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R08")
    assert r08["passed"] is False
    assert r08["severity"] == "blocker"
    assert any(i["code"] == "DELIVERY_TIMELINE_NEGATIVE_DEVIATION" for i in r08["issues"])

    # 3. 反例 B：响应明确声称超出交付周期或延长工期 -> blocker (DELIVERY_TIMELINE_NEGATIVE_DEVIATION)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "response": "受供应链供货周期影响，交期超出招标上限要求，需要延长工期。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r08 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R08")
    assert r08["passed"] is False
    assert r08["severity"] == "blocker"
    assert any(i["code"] == "DELIVERY_TIMELINE_NEGATIVE_DEVIATION" for i in r08["issues"])

    # 4. 反例 C：未填写响应承诺 -> blocker (DELIVERY_TIMELINE_NEGATIVE_DEVIATION)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "response": "",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r08 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R08")
    assert r08["passed"] is False
    assert r08["severity"] == "blocker"
    assert any(i["code"] == "DELIVERY_TIMELINE_NEGATIVE_DEVIATION" for i in r08["issues"])


def test_r12_sla_warranty_deviation(client):
    """验证 R12：服务响应 SLA 与质保期偏离核验（正例放行，质保期不足/现场到达超时/负偏离强阻断）。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r_tech = next(r for r in reqs if r["volume"] == "technical")

    # 1. 正例：招标要求不少于3年质保与2小时内到达现场，投标承诺3年质保与1小时到达
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "text": "SLA 与质保要求：提供不少于3年免费质保，突发严重故障2小时内到达现场。",
            "category": "service",
            "status": "confirmed",
            "response": "我方提供3年免费质保服务，本地运维常驻团队承诺1小时内到达现场排查处置。",
        },
        "PATCH",
    )

    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    r12 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R12")
    assert r12["passed"] is True
    assert r12["severity"] == "info"

    # 2. 反例 A：承诺质保期低于招标文件最低要求（1年 < 3年）-> blocker (SLA_WARRANTY_NEGATIVE_DEVIATION)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "response": "我方标准提供1年免费质保，后续维保需另行签署有偿服务合同。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r12 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R12")
    assert r12["passed"] is False
    assert r12["severity"] == "blocker"
    assert any(i["code"] == "SLA_WARRANTY_NEGATIVE_DEVIATION" for i in r12["issues"])

    # 3. 反例 B：现场到达响应时间超时（承诺4小时 > 招标2小时上限）-> blocker (SLA_WARRANTY_NEGATIVE_DEVIATION)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "response": "我方提供3年免费质保，因服务半径限制，承诺4小时内到达现场处置。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r12 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R12")
    assert r12["passed"] is False
    assert r12["severity"] == "blocker"
    assert any(i["code"] == "SLA_WARRANTY_NEGATIVE_DEVIATION" for i in r12["issues"])

    # 4. 反例 C：明确声明缩短质保期或实质性负偏离 -> blocker (SLA_WARRANTY_NEGATIVE_DEVIATION)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "response": "由于硬件采购成本限制，低于质保期要求，无法在2小时内到达现场。",
            "deviation_type": "negative",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r12 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R12")
    assert r12["passed"] is False
    assert r12["severity"] == "blocker"
    assert any(i["code"] == "SLA_WARRANTY_NEGATIVE_DEVIATION" for i in r12["issues"])


def test_r20_quotation_collusion_risk_detection(client):
    """验证 R20：报价雷同排查（正例放行，正文/响应串标特征/比例雷同/结构化串标标志强阻断）。"""
    flow = ProjectFlow(client).ready()
    chapters = flow.state()["chapters"]
    biz_chapter = next(c for c in chapters if c["volume"] == "business")

    # 1. 正例：独立自主报价测算，正文与条款响应整洁合规
    flow.commit(biz_chapter["id"], "商务分册报价表：各项服务及软件分项报价依据实际工时测算，独立编制，总价合规。")
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    r20 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R20")
    assert r20["passed"] is True
    assert r20["severity"] == "info"

    # 2. 反例 A：章节正文中排查到“分项报价比例异常一致”违规串标特征 -> blocker (BID_PRICE_COLLUSION_RISK_DETECTED)
    flow.commit(biz_chapter["id"], "报价分析备注：经对比，我方分项报价比例异常一致，各子项均呈固定比例分布。")
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r20 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R20")
    assert r20["passed"] is False
    assert r20["severity"] == "blocker"
    assert any(i["code"] == "BID_PRICE_COLLUSION_RISK_DETECTED" for i in r20["issues"])

    # 3. 反例 B：正文中排查到“复制其他投标主体报价”或“报价雷同”特征 -> blocker (BID_PRICE_COLLUSION_RISK_DETECTED)
    flow.commit(biz_chapter["id"], "本标段直接复制其他投标主体报价清单结构，调整系数为0.98。")
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r20 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R20")
    assert r20["passed"] is False
    assert r20["severity"] == "blocker"
    assert any(i["code"] == "BID_PRICE_COLLUSION_RISK_DETECTED" for i in r20["issues"])

    # 4. 反例 C：条款响应中出现“串通投标风险”特征 -> blocker (BID_PRICE_COLLUSION_RISK_DETECTED)
    flow.commit(biz_chapter["id"], "商务报价表正文正常。")
    reqs = flow.state()["requirements"]
    r_biz = next(r for r in reqs if r["volume"] == "business")
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "response": "投标报价存在串通投标风险，与其他投标人报价规律异常一致。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r20 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R20")
    assert r20["passed"] is False
    assert r20["severity"] == "blocker"
    assert any(i["code"] == "BID_PRICE_COLLUSION_RISK_DETECTED" for i in r20["issues"])


def test_export_gate_blocked_by_p3_compliance_rules(client):
    """验证整本递交导出门禁联动：当存在 P3 核心合规阻断缺陷时，正式递交版导出严格返回 400 CHECK_BLOCKER_EXISTS。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r_tech = next(r for r in reqs if r["volume"] == "technical")

    # 在技术分册中植入 R08 交付周期重大负偏离超期 blocker 缺陷（承诺 120 日历天超出招标 60 天上限）
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "text": "交付周期要求：自合同签订之日起不超过60日历天内完成交付。",
            "category": "schedule",
            "status": "confirmed",
            "response": "我方承诺120日历天内完成交付，交期超出招标文件规定上限。",
        },
        "PATCH",
    )

    # 执行项目检查
    check_res = flow.write("/checks", {"volume": "all"})
    check = check_res["check"]
    assert check["passed"] is False

    # 确认检查结果中存在 R08 blocker 缺陷
    blocker_issues = [i for i in check["issues"] if i.get("severity") == "blocker"]
    assert len(blocker_issues) > 0
    assert any(i.get("code") == "DELIVERY_TIMELINE_NEGATIVE_DEVIATION" for i in blocker_issues)
    assert any(i.get("rule_id") == "R08" for i in blocker_issues)

    # 尝试在存在 blocker 缺陷时导出 submission 正式递交版 -> 必须被 400 CHECK_BLOCKER_EXISTS 门禁拦截！
    res = flow.client.post(
        f"{flow.path}/exports",
        headers={
            **flow.headers,
            "If-Match": str(flow.state()["revision"]),
            "Idempotency-Key": str(uuid.uuid4()),
        },
        json={"check_id": check["id"], "kind": "submission", "volume": "all"},
    )
    assert res.status_code == 400, res.text
    err = res.json()
    assert err["code"] == "CHECK_BLOCKER_EXISTS"
    assert "阻断项" in err["message"]
