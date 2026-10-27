# 为什么有这个文件：为 PRD MVP §5.8 第五批核心合规规则（R13/R16/R18/R24/R32，BE-COMPLIANCE-RULES-P4）提供专属自动化测试套件。
# 它解决什么问题：
# 1. 验证 R13 团队人员配置核验（项目经理执业资格、持证人数门槛、社保证明核验，正例放行，缺失或不足强阻断）；
# 2. 验证 R16 投标保证金与保函有效性核验（金额足额、基本户汇出、保函有效期覆盖，正例放行，不足、第三方代缴或过期强阻断）；
# 3. 验证 R18 联合体投标协议与资质认定核验（非联合体免检通过、联合体协议与牵头人完备放行，协议缺失或牵头人未授权强阻断）；
# 4. 验证 R24 响应格式排版与强制表单签名盖章完整性核验（法定表单签字盖章完备放行，未盖章/未签名/空表单强阻断）；
# 5. 验证 R32 投标有效期与承诺不可撤销性核验（承诺期满足招标要求且不可撤回放行，有效期缩水或保留撤销权强阻断）；
# 6. 验证整本递交导出门禁联动（存在上述任一 P4 blocker 缺陷时，正式递交版 submission 严格触发 400 CHECK_BLOCKER_EXISTS）。

import uuid
import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from test_reference_flow import ProjectFlow, client, login


def test_r13_team_staffing_compliance(client):
    """验证 R13：团队人员配置核验（项目经理执业资格、持证人数门槛、社保证明，正例放行，资质缺失或人数不足强阻断）。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r_tech = next(r for r in reqs if r["volume"] == "technical")

    # 1. 正例：项目经理具备一级建造师与PMP资格证书，社保证明连续在缴，团队技术人员15人满足门槛要求
    pm_cert = flow.library(
        name="项目经理一级建造师执业资格证书与近半年社保证明",
        content="拟派项目经理具备一级建造师执业资格证书（注册编号：建110123456789），PMP认证证书，连续缴纳近半年城镇职工社保（社保证明编号：SB-2026-8899）。",
        valid_until="2027-12-31",
        type="qualification",
    )
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "text": "团队人员配置要求：拟派项目经理须具备一级建造师执业资格并提供连续近半年社保证明，团队常驻技术人员不少于10人。",
            "category": "team",
            "evidence_ids": [pm_cert["id"]],
            "status": "confirmed",
            "response": "我方拟派项目经理具备一级建造师执业资格及PMP认证，已提供近半年社保证明，常驻专业技术团队共15人，满足且优于招标人数门槛。",
        },
        "PATCH",
    )

    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    r13 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R13")
    assert r13["passed"] is True
    assert r13["severity"] == "info"

    # 2. 反例 A：项目经理执业资格缺失 -> blocker (TEAM_PROJECT_MANAGER_QUALIFICATION_MISSING)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "response": "我方拟派项目经理执业资格暂未取得注册执业证书，项目经理执业资格缺失，拟以其他技术负责人员代行职责。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r13 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R13")
    assert r13["passed"] is False
    assert r13["severity"] == "blocker"
    assert any(i["code"] == "TEAM_PROJECT_MANAGER_QUALIFICATION_MISSING" for i in r13["issues"])

    # 3. 反例 B：项目经理社保证明缺失或断缴 -> blocker (TEAM_PROJECT_MANAGER_QUALIFICATION_MISSING)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "response": "项目经理具备建造师证书，但由于人事调整，项目经理社保证明缺失，未提供连续社保缴纳记录。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r13 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R13")
    assert r13["passed"] is False
    assert r13["severity"] == "blocker"
    assert any(i["code"] == "TEAM_PROJECT_MANAGER_QUALIFICATION_MISSING" for i in r13["issues"])

    # 4. 反例 C：团队人员数量未达招标文件最低门槛 -> blocker (TEAM_STAFFING_THRESHOLD_UNMET)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "response": "项目经理具备建造师证书并已缴纳社保。但因近期项目密集，拟派常驻团队人数仅配置5人，团队人员配置不足，持证人数不足招标要求。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r13 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R13")
    assert r13["passed"] is False
    assert r13["severity"] == "blocker"
    assert any(i["code"] == "TEAM_STAFFING_THRESHOLD_UNMET" for i in r13["issues"])

    # 5. 反例 D：响应为空 -> blocker (TEAM_PROJECT_MANAGER_QUALIFICATION_MISSING)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "response": "",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r13 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R13")
    assert r13["passed"] is False
    assert r13["severity"] == "blocker"
    assert any(i["code"] == "TEAM_PROJECT_MANAGER_QUALIFICATION_MISSING" for i in r13["issues"])


def test_r16_bid_security_deposit_compliance(client):
    """验证 R16：投标保证金与保函有效性核验（金额足额、基本户汇出、保函有效期覆盖，正例放行，不足、第三方代缴或过期强阻断）。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r_biz = next(r for r in reqs if r["volume"] == "business")

    # 1. 正例：投标保证金足额缴纳（人民币100,000元），由投标人基本账户转出，银行保函有效期完全覆盖投标有效期
    bond_ev = flow.library(
        name="银行投标保函与保证金转账凭证",
        content="我司已由基本存款账户汇出投标保证金人民币100,000.00元整，并开立不可撤销见索即付银行保函，保函有效期至2027年3月31日，覆盖投标有效期要求。",
        valid_until="2027-03-31",
        type="qualification",
    )
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "text": "投标保证金要求：人民币100,000元整，须由投标人基本账户汇出或出具银行保函，保函有效期须覆盖投标有效期。",
            "category": "bond",
            "evidence_ids": [bond_ev["id"]],
            "status": "confirmed",
            "response": "我方已足额由基本账户转出投标保证金100000元整，银行保函有效且覆盖全部投标有效期，附银行保函及银行电汇回单。",
        },
        "PATCH",
    )

    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    r16 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R16")
    assert r16["passed"] is True
    assert r16["severity"] == "info"

    # 2. 反例 A：保证金金额不足 -> blocker (BID_SECURITY_DEPOSIT_NON_COMPLIANT)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "response": "我方因内部审批额度限制，本次实际缴纳投标保证金50000元，保证金金额不足，不足额缴纳。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r16 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R16")
    assert r16["passed"] is False
    assert r16["severity"] == "blocker"
    assert any(i["code"] == "BID_SECURITY_DEPOSIT_NON_COMPLIANT" for i in r16["issues"])

    # 3. 反例 B：第三方账户代缴或汇出主体不一致 -> blocker (BID_SECURITY_DEPOSIT_NON_COMPLIANT)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "response": "投标保证金足额，但由关联公司第三方代缴，转出账户非投标人基本存款账户，汇款主体不一致。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r16 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R16")
    assert r16["passed"] is False
    assert r16["severity"] == "blocker"
    assert any(i["code"] == "BID_SECURITY_DEPOSIT_NON_COMPLIANT" for i in r16["issues"])

    # 4. 反例 C：保函有效期不足或过期 -> blocker (BID_SECURITY_DEPOSIT_NON_COMPLIANT)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "response": "我方开立的银行保函有效期至本月底，保函有效期不足，未覆盖招标要求的投标有效期。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r16 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R16")
    assert r16["passed"] is False
    assert r16["severity"] == "blocker"
    assert any(i["code"] == "BID_SECURITY_DEPOSIT_NON_COMPLIANT" for i in r16["issues"])

    # 5. 反例 D：响应为空 -> blocker (BID_SECURITY_DEPOSIT_NON_COMPLIANT)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "response": "",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r16 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R16")
    assert r16["passed"] is False
    assert r16["severity"] == "blocker"
    assert any(i["code"] == "BID_SECURITY_DEPOSIT_NON_COMPLIANT" for i in r16["issues"])


def test_r18_consortium_agreement_compliance(client):
    """验证 R18：联合体投标协议与资质认定核验（非联合体免检通过、联合体协议与牵头人完备放行，协议缺失或牵头人未授权强阻断）。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r_biz = next(r for r in reqs if r["volume"] == "business")

    # 1. 正例 A：非联合体独立投标，明确声明非联合体投标，直接通过
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "text": "联合体投标要求：本项目接受联合体投标，联合体各方须签订联合体协议书并明确牵头人及分工。",
            "category": "consortium",
            "status": "confirmed",
            "response": "我方声明本次为独立投标，非联合体投标，不采用联合体形式参与本项目竞标。",
        },
        "PATCH",
    )

    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    r18 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R18")
    assert r18["passed"] is True
    assert r18["severity"] == "info"

    # 2. 正例 B：联合体投标，具备合法联合体协议书、明确授权牵头人、各自分工与资质划分明确
    consortium_ev = flow.library(
        name="联合体投标协议书盖章扫描件",
        content="联合体协议书：甲方为主办人（牵头人），乙方为成员单位。甲方负责项目总体集成与系统开发，乙方负责配套工程施工与运维，双方共同承担连带责任。",
        valid_until="2027-12-31",
        type="qualification",
    )
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "evidence_ids": [consortium_ev["id"]],
            "response": "我方以联合体形式投标，已附具有法律效力的联合体协议书，明确我方为联合体牵头人（主办人），各成员单位资质与职责分工明确。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r18 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R18")
    assert r18["passed"] is True
    assert r18["severity"] == "info"

    # 3. 反例 A：联合体协议书缺失 -> blocker (CONSORTIUM_AGREEMENT_INVALID)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "evidence_ids": [],
            "response": "我方由多家单位组成联合体，但目前联合体协议书尚未正式签署完毕，缺少联合体协议书。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r18 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R18")
    assert r18["passed"] is False
    assert r18["severity"] == "blocker"
    assert any(i["code"] == "CONSORTIUM_AGREEMENT_INVALID" for i in r18["issues"])

    # 4. 反例 B：联合体牵头人未授权或主办人缺失 -> blocker (CONSORTIUM_AGREEMENT_INVALID)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "response": "以联合体形式参与投标，已签署协议，但尚未确定牵头人，牵头人未授权，成员各自独立承担义务。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r18 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R18")
    assert r18["passed"] is False
    assert r18["severity"] == "blocker"
    assert any(i["code"] == "CONSORTIUM_AGREEMENT_INVALID" for i in r18["issues"])

    # 5. 反例 C：联合体成员资质不全或未经批准擅自分包变更 -> blocker (CONSORTIUM_AGREEMENT_INVALID)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "response": "联合体已签署协议，但其中成员单位专业资质不足，且中途更换联合体成员，存在违规分包变更。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r18 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R18")
    assert r18["passed"] is False
    assert r18["severity"] == "blocker"
    assert any(i["code"] == "CONSORTIUM_AGREEMENT_INVALID" for i in r18["issues"])


def test_r24_mandatory_seal_signature_compliance(client):
    """验证 R24：响应格式排版与强制表单签名盖章完整性核验（法定表单签字盖章完备放行，未盖章/未签名/空表单强阻断）。"""
    flow = ProjectFlow(client).ready()
    chapters = flow.state()["chapters"]
    biz_chapter = next(c for c in chapters if c["volume"] == "business")
    tech_chapter = next(c for c in chapters if c["volume"] == "technical")

    # 将商务分册某章节标记为法定表单（投标函与法定代表人身份证明）
    flow.confirm_plan({
        "chapters": [
            {"id": biz_chapter["id"], "title": "一、投标函及法定代表人身份证明与授权委托书", "volume": "business"},
            {"id": tech_chapter["id"], "title": tech_chapter["title"], "volume": "technical"},
        ]
    })

    # 1. 正例：包含完整的 (签字) 与 (盖章) 占位标记，表单排版正规完整
    flow.commit(
        biz_chapter["id"],
        "投标函：我方全面响应招标文件要求。法定代表人（签字）：张三。投标人：（公章/盖章）。日期：2026年10月27日。",
    )

    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    r24 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R24")
    assert r24["passed"] is True
    assert r24["severity"] == "info"

    # 2. 反例 A：法定表单中显式标明未盖章或未签名 -> blocker (MANDATORY_SEAL_SIGNATURE_MISSING)
    flow.commit(
        biz_chapter["id"],
        "投标函及授权书：法定代表人（签字）：张三。投标人：（未盖章）。待中标后补齐公章。",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r24 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R24")
    assert r24["passed"] is False
    assert r24["severity"] == "blocker"
    assert any(i["code"] == "MANDATORY_SEAL_SIGNATURE_MISSING" for i in r24["issues"])

    # 3. 反例 B：法定表单正文缺失盖章或签字标记 -> blocker (MANDATORY_SEAL_SIGNATURE_MISSING)
    flow.commit(
        biz_chapter["id"],
        "投标函正文：我方愿以投标报价承接本项目全部工程。落款仅有打印名称，无任何签字或印章栏位。",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r24 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R24")
    assert r24["passed"] is False
    assert r24["severity"] == "blocker"
    assert any(i["code"] == "MANDATORY_SEAL_SIGNATURE_MISSING" for i in r24["issues"])

    # 4. 反例 C：法定表单章节正文为空白 -> blocker (MANDATORY_SEAL_SIGNATURE_MISSING)
    flow.commit(
        biz_chapter["id"],
        "",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r24 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R24")
    assert r24["passed"] is False
    assert r24["severity"] == "blocker"
    assert any(i["code"] == "MANDATORY_SEAL_SIGNATURE_MISSING" for i in r24["issues"])


def test_r32_bid_validity_period_compliance(client):
    """验证 R32：投标有效期与承诺不可撤销性核验（承诺期满足招标要求且不可撤回放行，有效期缩水或保留撤销权强阻断）。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r_biz = next(r for r in reqs if r["volume"] == "business")

    # 1. 正例：承诺投标有效期为90日历天，完全满足招标文件90天要求，承诺在投标有效期内不可撤回
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "text": "投标有效期要求：自投标截止之日起不少于90日历天，投标在有效期内不可撤回。",
            "category": "validity",
            "status": "confirmed",
            "response": "我方庄重承诺：本次投标有效期为自投标截止之日起90日历天，在投标有效期内，本投标文件对我方始终具有约束力，承诺不可撤回、不可变更。",
        },
        "PATCH",
    )

    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    r32 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R32")
    assert r32["passed"] is True
    assert r32["severity"] == "info"

    # 2. 反例 A：承诺投标有效期缩水（如 60 天 < 90 天）-> blocker (BID_VALIDITY_PERIOD_DEFICIENT)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "response": "我方承诺本次投标有效期为自递交之日起60日历天，超出60天后需重新核实商务报价与实施周期。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r32 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R32")
    assert r32["passed"] is False
    assert r32["severity"] == "blocker"
    assert any(i["code"] == "BID_VALIDITY_PERIOD_DEFICIENT" for i in r32["issues"])

    # 3. 反例 B：承诺附带可撤回、单方撤销等实质性负偏离条件 -> blocker (BID_VALIDITY_PERIOD_DEFICIENT)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "response": "投标有效期为90天，但我方保留在评标完成前单方撤回投标文件的权利，投标并非不可撤销承诺。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r32 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R32")
    assert r32["passed"] is False
    assert r32["severity"] == "blocker"
    assert any(i["code"] == "BID_VALIDITY_PERIOD_DEFICIENT" for i in r32["issues"])

    # 4. 反例 C：响应为空 -> blocker (BID_VALIDITY_PERIOD_DEFICIENT)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "response": "",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r32 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R32")
    assert r32["passed"] is False
    assert r32["severity"] == "blocker"
    assert any(i["code"] == "BID_VALIDITY_PERIOD_DEFICIENT" for i in r32["issues"])


def test_export_gate_blocked_by_p4_compliance_rules(client):
    """验证整本递交导出门禁联动：当存在 P4 核心合规阻断缺陷时，正式递交版导出严格返回 400 CHECK_BLOCKER_EXISTS。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r_biz = next(r for r in reqs if r["volume"] == "business")

    # 在商务分册中植入 R32 投标有效期缩水重大负偏离 blocker 缺陷（承诺 45 日历天远低于 90 天要求）
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "text": "投标有效期要求：自投标截止之日起不少于90日历天，投标在有效期内不可撤销。",
            "category": "validity",
            "status": "confirmed",
            "response": "我方仅能承诺投标有效期为45日历天，有效期不足且附带调价条件。",
        },
        "PATCH",
    )

    # 执行项目检查
    check_res = flow.write("/checks", {"volume": "all"})
    check = check_res["check"]
    assert check["passed"] is False

    # 确认检查结果中存在 R32 blocker 缺陷
    blocker_issues = [i for i in check["issues"] if i.get("severity") == "blocker"]
    assert len(blocker_issues) > 0
    assert any(i.get("code") == "BID_VALIDITY_PERIOD_DEFICIENT" for i in blocker_issues)
    assert any(i.get("rule_id") == "R32" for i in blocker_issues)

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

    # 尝试导出内部评审版 internal_review -> 允许通过（has_blockers=True 提示）
    res_review = flow.client.post(
        f"{flow.path}/exports",
        headers={
            **flow.headers,
            "If-Match": str(flow.state()["revision"]),
            "Idempotency-Key": str(uuid.uuid4()),
        },
        json={"check_id": check["id"], "kind": "internal_review", "volume": "all"},
    )
    assert res_review.status_code in (200, 201), res_review.text
    export_obj = res_review.json()["export"]
    assert export_obj["kind"] == "internal_review"
    assert export_obj["has_blockers"] is True
