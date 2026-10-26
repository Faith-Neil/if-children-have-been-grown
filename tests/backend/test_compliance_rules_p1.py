# 为什么有这个文件：为 PRD MVP §5.8 第二批核心合规规则（R03/R04/R09/R10，BE-COMPLIANCE-RULES-P1）提供专属自动化测试套件。
# 它解决什么问题：
# 1. 验证 R03 资质有效期与信誉核验（证书过期/缺失/失信名单强阻断）；
# 2. 验证 R04 联合体投标协议核验（联合体协议书缺失/成员资质缺失强阻断，独立投标自动放行）；
# 3. 验证 R09 服务期/工期与 SLA 承诺核验（服务期未承诺/负偏离强阻断，SLA 核心指标未填报/负偏离强阻断）；
# 4. 验证 R10 质保期与服务响应时间核验（质保期低于基线/响应时间超标/跨章节承诺自相矛盾强阻断）；
# 5. 验证整本递交导出门禁联动（存在上述 blocker 缺陷时，严禁导出正式递交版 Word，严格触发 400 CHECK_BLOCKER_EXISTS）。

import uuid
import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from test_reference_flow import ProjectFlow, client, login


def test_r03_qualification_validity_and_credit(client):
    """验证 R03：资质有效期与信誉核验（正例、过期、缺失证书及失信记录拦截）。"""
    flow = ProjectFlow(client).ready()
    state = flow.state()
    reqs = state["requirements"]
    r_biz = next(r for r in reqs if r["volume"] == "business")

    # 1. 正例：有效资质证书挂接，有效期覆盖投标截止时间，且无失信记录
    valid_lib = flow.library(valid_until="2027-12-31", name="国家信息安全资质认证")
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "text": "投标人资质要求：具备有效的国家信息安全资质认证，且无重大失信违法记录。",
            "category": "qualification",
            "evidence_ids": [valid_lib["id"]],
            "status": "confirmed",
            "response": "我方持有有效资质认证，未被列入失信被执行人或重大税收违法黑名单。",
        },
        "PATCH",
    )
    flow.write("", {"deadline": "2026-12-31T17:00:00+08:00"}, "PATCH")

    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    r03 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R03")
    print("DEBUG R03 ISSUES:", r03["issues"])
    assert r03["passed"] is True
    assert r03["severity"] == "info"

    # 2. 反例 A：证书在投标截止时间前过期 -> blocker (QUALIFICATION_CERTIFICATE_EXPIRED)
    # 先将截止时间设为早于证书有效期的日期以便成功关联，随后更新截止时间为推迟后的日期，触发证书过期阻断
    expired_lib = flow.library(valid_until="2025-06-30", name="已过期的行业资质证书")
    flow.write("", {"deadline": "2025-01-01T17:00:00+08:00"}, "PATCH")
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "evidence_ids": [expired_lib["id"]],
            "response": "提供行业资质证书。",
        },
        "PATCH",
    )
    flow.write("", {"deadline": "2026-12-31T17:00:00+08:00"}, "PATCH")
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r03 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R03")
    assert r03["passed"] is False
    assert r03["severity"] == "blocker"
    assert any(i["code"] == "QUALIFICATION_CERTIFICATE_EXPIRED" for i in r03["issues"])

    # 3. 反例 B：资质要求缺少任何证据挂接 -> blocker (QUALIFICATION_CERTIFICATE_MISSING)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "evidence_ids": [],
            "response": "我方具备相关资质认证。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r03 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R03")
    assert r03["passed"] is False
    assert r03["severity"] == "blocker"
    assert any(i["code"] == "QUALIFICATION_CERTIFICATE_MISSING" for i in r03["issues"])

    # 4. 反例 C：存在失信黑名单记录 -> blocker (DISHONEST_RECORD_EXISTS)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "text": "投标人信用核验：查询信用中国，严禁被列入失信被执行人名单。",
            "evidence_ids": [valid_lib["id"]],
            "response": "因诉讼纠纷被执行人，存在失信记录，正在申请信用修复。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r03 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R03")
    assert r03["passed"] is False
    assert r03["severity"] == "blocker"
    assert any(i["code"] == "DISHONEST_RECORD_EXISTS" for i in r03["issues"])


def test_r04_consortium_agreement_verification(client):
    """验证 R04：联合体投标协议核验（独立投标放行、联合体协议缺失/成员资质缺失拦截）。"""
    flow = ProjectFlow(client).ready()

    # 1. 正例 A：非联合体独立投标 -> 自动放行
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r04 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R04")
    assert r04["passed"] is True
    assert r04["severity"] == "info"
    assert "单一主体独立投标" in r04["finding_summary"]

    # 2. 反例 A：标记为联合体投标但未上传联合体协议书 -> blocker (CONSORTIUM_AGREEMENT_MISSING)
    flow.write("", {"project_partners": [{"partner_entity_id": "贝塔科技"}]}, "PATCH")
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r04 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R04")
    assert r04["passed"] is False
    assert r04["severity"] == "blocker"
    assert any(i["code"] == "CONSORTIUM_AGREEMENT_MISSING" for i in r04["issues"])

    # 3. 正例 B：联合体上传协议书及成员资质材料 -> 通过
    flow.upload(content="这是牵头人与成员单位共同盖章签署的联合体投标协议书。".encode("utf-8"), filename="联合体投标协议书-盖章签署件.pdf")
    # 在证据库中录入成员资质
    flow.library(name="联合体成员-贝塔科技营业执照", valid_until="2028-12-31")

    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r04 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R04")
    assert r04["passed"] is True
    assert r04["severity"] == "info"

    # 4. 反例 B：联合体新增成员单位缺少资质证明 -> blocker (CONSORTIUM_MEMBER_QUALIFICATION_MISSING)
    flow.write("", {"project_partners": [{"partner_entity_id": "贝塔科技"}, {"partner_entity_id": "伽马科技"}]}, "PATCH")
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r04 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R04")
    assert r04["passed"] is False
    assert r04["severity"] == "blocker"
    assert any(i["code"] == "CONSORTIUM_MEMBER_QUALIFICATION_MISSING" for i in r04["issues"])


def test_r09_service_period_and_sla_commitment(client):
    """验证 R09：服务期/工期与 SLA 承诺核验（服务期未承诺/负偏离阻断，SLA 核心指标负偏离阻断）。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r_tech = next(r for r in reqs if r["volume"] == "technical")

    # 1. 正例：服务期明确承诺且无偏离
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "text": "实施服务期要求：自合同签订之日起 180 个日历天内完成系统整体上线交付。",
            "status": "confirmed",
            "response": "我方承诺自合同签订之日起 180 个日历天内完成全部系统交付，完全响应服务期要求。",
            "deviation_type": "none",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r09 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R09")
    assert r09["passed"] is True
    assert r09["severity"] == "info"

    # 2. 反例 A：服务期条款未填写响应承诺 -> blocker (SERVICE_PERIOD_COMMITMENT_MISSING)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "response": "",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r09 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R09")
    assert r09["passed"] is False
    assert r09["severity"] == "blocker"
    assert any(i["code"] == "SERVICE_PERIOD_COMMITMENT_MISSING" for i in r09["issues"])

    # 3. 反例 B：服务期负偏离（工期延长、超出招标要求）-> blocker (SERVICE_PERIOD_NEGATIVE_DEVIATION)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "response": "受供应链周期影响，预计需 240 个日历天交付，存在工期负偏离延长交付。",
            "deviation_type": "negative",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r09 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R09")
    assert r09["passed"] is False
    assert r09["severity"] == "blocker"
    assert any(i["code"] == "SERVICE_PERIOD_NEGATIVE_DEVIATION" for i in r09["issues"])


def test_r10_warranty_period_and_response_time(client):
    """验证 R10：质保期与服务响应时间核验（质保期低于基线/响应时间负偏离/各章节承诺矛盾拦截）。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r0 = reqs[0]
    r1 = reqs[1]
    chapters = flow.state()["chapters"]

    # 1. 正例：质保期与响应时限完全达标，且章节间口径一致
    flow.write(
        f"/requirements/{r0['id']}",
        {
            "text": "免费质保期要求：系统终验合格后提供不少于 3 年的免费质保与维保技术支持服务。",
            "status": "confirmed",
            "response": "我方承诺提供自终验合格之日起 3 年免费质保服务，全面满足招标文件要求。",
            "deviation_type": "none",
        },
        "PATCH",
    )
    flow.write(
        f"/requirements/{r1['id']}",
        {
            "text": "故障响应时间要求：提供 7x24 小时服务支持，重大故障 15 分钟内响应，2 小时内到达现场。",
            "status": "confirmed",
            "response": "我方承诺 15 分钟内响应，2 小时内到达现场排除故障，完全响应指标。",
            "deviation_type": "none",
        },
        "PATCH",
    )
    flow.commit(chapters[0]["id"], "技术服务方案说明：我司提供 3 年免费质保服务，15分钟内快速响应。")
    flow.commit(chapters[1]["id"], "商务保障方案说明：承诺提供 3 年免费质保支持，技术团队 15分钟响应。")

    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r10 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R10")
    assert r10["passed"] is True
    assert r10["severity"] == "info"

    # 2. 反例 A：质保期承诺低于招标基线 -> blocker (WARRANTY_PERIOD_BELOW_BASELINE)
    flow.write(
        f"/requirements/{r0['id']}",
        {
            "response": "我方标准质保期为 1 年免费维保，存在负偏离。",
            "deviation_type": "negative",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r10 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R10")
    assert r10["passed"] is False
    assert r10["severity"] == "blocker"
    assert any(i["code"] == "WARRANTY_PERIOD_BELOW_BASELINE" for i in r10["issues"])

    # 恢复要求
    flow.write(
        f"/requirements/{r0['id']}",
        {
            "response": "我方承诺提供 3 年免费质保支持。",
            "deviation_type": "none",
        },
        "PATCH",
    )

    # 3. 反例 B：故障响应时间超时负偏离 -> blocker (RESPONSE_TIME_BELOW_BASELINE)
    flow.write(
        f"/requirements/{r1['id']}",
        {
            "response": "重大故障无法达到 15 分钟响应，我方提供 4 小时到达现场排除故障，负偏离响应。",
            "deviation_type": "negative",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r10 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R10")
    assert r10["passed"] is False
    assert r10["severity"] == "blocker"
    assert any(i["code"] == "RESPONSE_TIME_BELOW_BASELINE" for i in r10["issues"])

    # 4. 反例 C：各章节质保期承诺自相矛盾 -> blocker (WARRANTY_PERIOD_INCONSISTENT)
    flow.write(
        f"/requirements/{r1['id']}",
        {
            "response": "我方承诺 15 分钟内响应，2 小时到达现场。",
            "deviation_type": "none",
        },
        "PATCH",
    )
    # 技术分册写 3 年质保，商务分册写 1 年质保 -> 矛盾
    flow.commit(chapters[0]["id"], "系统技术方案承诺：提供 3 年免费质保支持与原厂技术服务。")
    flow.commit(chapters[1]["id"], "商务应答分册条款：本项目仅提供 1 年免费维保服务。")

    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r10 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R10")
    assert r10["passed"] is False
    assert r10["severity"] == "blocker"
    assert any(i["code"] == "WARRANTY_PERIOD_INCONSISTENT" for i in r10["issues"])


def test_export_gate_blocked_by_p1_compliance_rules(client):
    """验证整本递交导出门禁：当存在 P1 阻断缺陷时，严格触发 400 CHECK_BLOCKER_EXISTS。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r0 = reqs[0]

    # 设置 R09 服务期负偏离 blocker 缺陷
    flow.write(
        f"/requirements/{r0['id']}",
        {
            "text": "实施服务期要求：要求合同签订后 90 天内交付上线全部功能。",
            "status": "confirmed",
            "response": "无法满足 90 天工期要求，需延长至 180 天交付，存在严重负偏离。",
            "deviation_type": "negative",
        },
        "PATCH",
    )

    # 执行项目检查
    check_res = flow.write("/checks", {"volume": "all"})
    check = check_res["check"]
    assert check["passed"] is False
    
    # 确认检查结果中存在 R09 blocker 缺陷
    blocker_issues = [i for i in check["issues"] if i.get("severity") == "blocker"]
    assert len(blocker_issues) > 0
    assert any(i.get("rule_id") == "R09" for i in blocker_issues)

    # 尝试在有 blocker 的情况下导出 submission 递交版 -> 必须被 400 CHECK_BLOCKER_EXISTS 拦截！
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
