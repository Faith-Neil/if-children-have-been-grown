# 为什么有这个文件：为 PRD MVP §5.8 第六批（终批）核心合规规则（R17/R19/R26/R27/R28，BE-COMPLIANCE-RULES-P5）提供专属自动化测试套件。
# 它解决什么问题：
# 1. 验证 R17 关联交易与利害关系回避核验（单位负责人为同一人/控股参股，正例放行，未回避或存在利害关系强阻断）；
# 2. 验证 R19 环保、节能与绿色采购强制产品认证核验（国家节能品目与能效证书，正例放行，认证缺失或能效未达标强阻断）；
# 3. 验证 R26 知识产权与侵权无争议声明核验（自主知识产权与无条件侵权兜底承诺，正例放行，声明缺失或推卸侵权责任强阻断）；
# 4. 验证 R27 本地化服务网点与常驻技术力量核验（本地售后分公司与常驻技术人员，正例放行，无本地网点或无法驻场强阻断）；
# 5. 验证 R28 关键技术规格实质性负偏离排查（关键指标参数无负偏离，正例放行，标记负偏离或指标不满足强阻断）；
# 6. 验证整本递交导出门禁联动（存在上述任一 P5 blocker 缺陷时，正式递交版 submission 严格触发 400 CHECK_BLOCKER_EXISTS，修复后通畅放行）。

import uuid
import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from test_reference_flow import ProjectFlow, client, login


def test_r17_conflict_of_interest_compliance(client):
    """验证 R17：关联交易与利害关系回避核验（正例放行，未回避或存在实质性利害关系强阻断）。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r_bus = next(r for r in reqs if r["volume"] == "business")

    # 1. 正例：承诺无利害关系与无关联交易，符合回避原则
    flow.write(
        f"/requirements/{r_bus['id']}",
        {
            "text": "关联交易与利害关系回避要求：投标人与招标人、招标代理机构不得存在利害关系、控股参股关系，单位负责人不得为同一人。",
            "category": "qualification",
            "status": "confirmed",
            "response": "我方与招标人及招标代理机构无任何利害关系，无控股参股关联交易，单位负责人非同一人，符合回避规定并已签署承诺书。",
        },
        "PATCH",
    )

    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    r17 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R17")
    assert r17["passed"] is True
    assert r17["severity"] == "info"

    # 2. 反例 A：未填写响应承诺 -> blocker (CONFLICT_OF_INTEREST_UNRESOLVED)
    flow.write(
        f"/requirements/{r_bus['id']}",
        {
            "response": "",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r17 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R17")
    assert r17["passed"] is False
    assert r17["severity"] == "blocker"
    assert any(i["code"] == "CONFLICT_OF_INTEREST_UNRESOLVED" for i in r17["issues"])

    # 3. 反例 B：标记为 rejected -> blocker (CONFLICT_OF_INTEREST_UNRESOLVED)
    flow.write(
        f"/requirements/{r_bus['id']}",
        {
            "status": "rejected",
            "reason": "存在利益冲突，无法签署回避声明",
            "response": "不符合回避要求。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r17 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R17")
    assert r17["passed"] is False
    assert r17["severity"] == "blocker"
    assert any(i["code"] == "CONFLICT_OF_INTEREST_UNRESOLVED" for i in r17["issues"])

    # 4. 反例 C：实质性关联交易或利害关系未回避 -> blocker (CONFLICT_OF_INTEREST_UNRESOLVED)
    flow.write(
        f"/requirements/{r_bus['id']}",
        {
            "status": "confirmed",
            "response": "经核查，我方控股股东为招标人下属控股子公司，存在关联关系，未能签署回避声明，构成关联交易未披露。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r17 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R17")
    assert r17["passed"] is False
    assert r17["severity"] == "blocker"
    assert any(i["code"] == "CONFLICT_OF_INTEREST_UNRESOLVED" for i in r17["issues"])


def test_r19_mandatory_green_cert_compliance(client):
    """验证 R19：环保、节能与绿色采购强制产品认证核验（正例放行，强制品目认证缺失强阻断）。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r_tech = next(r for r in reqs if r["volume"] == "technical")

    # 1. 正例：核心设备具备中国节能产品认证证书及一级能效标识
    green_cert = flow.library(
        name="服务器与交换机中国节能产品认证证书及一级能效证明",
        content="投标产品已列入国家强制采购节能产品品目清单，具备中国质量认证中心颁发的节能产品认证证书（证书编号：CQC-ENERGY-2026-9901），能效等级一级。",
        valid_until="2028-12-31",
        type="qualification",
    )
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "text": "强制节能与绿色采购要求：所投服务器与网络设备属于强制节能产品品目，须取得有效节能认证证书并满足绿色采购标准。",
            "category": "qualification",
            "evidence_ids": [green_cert["id"]],
            "status": "confirmed",
            "response": "我方所投全部设备均具备有效节能认证，属于强制节能品目并附证书，取得中国节能产品认证证书，达到一级能效要求。",
        },
        "PATCH",
    )

    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    r19 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R19")
    assert r19["passed"] is True
    assert r19["severity"] == "info"

    # 2. 反例 A：未填写响应说明 -> blocker (MANDATORY_GREEN_CERT_MISSING)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "response": "",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r19 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R19")
    assert r19["passed"] is False
    assert r19["severity"] == "blocker"
    assert any(i["code"] == "MANDATORY_GREEN_CERT_MISSING" for i in r19["issues"])

    # 3. 反例 B：强制节能条款被拒绝 -> blocker (MANDATORY_GREEN_CERT_MISSING)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "status": "rejected",
            "reason": "部分设备未能取得节能品目认证证书",
            "response": "无法满足节能要求。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r19 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R19")
    assert r19["passed"] is False
    assert r19["severity"] == "blocker"
    assert any(i["code"] == "MANDATORY_GREEN_CERT_MISSING" for i in r19["issues"])

    # 4. 反例 C：未取得节能认证证书 -> blocker (MANDATORY_GREEN_CERT_MISSING)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "status": "confirmed",
            "response": "所投部分型号未取得节能认证，强制节能产品未认证，无环保标志认证，暂未提供节能证书。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r19 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R19")
    assert r19["passed"] is False
    assert r19["severity"] == "blocker"
    assert any(i["code"] == "MANDATORY_GREEN_CERT_MISSING" for i in r19["issues"])


def test_r26_ip_infringement_indemnity_compliance(client):
    """验证 R26：知识产权与侵权无争议声明核验（正例放行，侵权兜底承诺缺失或推卸责任强阻断）。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r_tech = next(r for r in reqs if r["volume"] == "technical")

    # 1. 正例：承诺自主知识产权及侵权法律与经济责任全额兜底
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "text": "知识产权合规要求：投标人须声明方案及软件具备完全自主知识产权，承诺若发生知识产权侵权争议由投标人承担全部法律责任与经济赔偿。",
            "category": "legal",
            "status": "confirmed",
            "response": "我方投标软件具备完全自主知识产权，承诺不侵犯任何第三方知识产权，如发生侵权纠纷由我方承担全部责任及无条件兜底，知识产权无争议。",
        },
        "PATCH",
    )

    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    r26 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R26")
    assert r26["passed"] is True
    assert r26["severity"] == "info"

    # 2. 反例 A：未填写响应声明 -> blocker (IP_INFRINGEMENT_INDEMNITY_MISSING)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "response": "",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r26 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R26")
    assert r26["passed"] is False
    assert r26["severity"] == "blocker"
    assert any(i["code"] == "IP_INFRINGEMENT_INDEMNITY_MISSING" for i in r26["issues"])

    # 3. 反例 B：条款被拒绝 -> blocker (IP_INFRINGEMENT_INDEMNITY_MISSING)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "status": "rejected",
            "reason": "第三方开源组件存在许可争议风险",
            "response": "拒绝承诺知识产权免责。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r26 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R26")
    assert r26["passed"] is False
    assert r26["severity"] == "blocker"
    assert any(i["code"] == "IP_INFRINGEMENT_INDEMNITY_MISSING" for i in r26["issues"])

    # 4. 反例 C：推卸侵权责任或拒绝兜底 -> blocker (IP_INFRINGEMENT_INDEMNITY_MISSING)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "status": "confirmed",
            "response": "我方不承担侵权责任，第三方侵权免责排除，若产生侵权纠纷由招标人承担，拒绝承担侵权赔偿。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r26 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R26")
    assert r26["passed"] is False
    assert r26["severity"] == "blocker"
    assert any(i["code"] == "IP_INFRINGEMENT_INDEMNITY_MISSING" for i in r26["issues"])


def test_r27_local_service_branch_compliance(client):
    """验证 R27：本地化服务网点与常驻技术力量核验（正例放行，缺少本地网点强阻断）。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r_tech = next(r for r in reqs if r["volume"] == "technical")

    # 1. 正例：本地分公司执照与常驻技术工程师团队满足本地化服务要求
    branch_cert = flow.library(
        name="项目所在地分公司营业执照及常驻售后技术人员清单",
        content="我司在项目所在地设有直属分公司（统一社会信用代码：91110108MA01234567），常驻专业技术支持工程师8人，提供7x24小时本地化驻场服务。",
        valid_until="2027-06-30",
        type="qualification",
    )
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "text": "本地化服务网点要求：投标人须在项目所在地具备合法的本地化售后服务机构或办事处，配备不少于5名常驻技术支持人员。",
            "category": "service",
            "evidence_ids": [branch_cert["id"]],
            "status": "confirmed",
            "response": "我方已设立本地分公司，具备本地售后服务网点，常驻技术人员已配备8人，本地办事处营业执照齐全，提供本地化驻场支持。",
        },
        "PATCH",
    )

    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    r27 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R27")
    assert r27["passed"] is True
    assert r27["severity"] == "info"

    # 2. 反例 A：未填写响应内容 -> blocker (LOCAL_SERVICE_BRANCH_MISSING)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "response": "",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r27 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R27")
    assert r27["passed"] is False
    assert r27["severity"] == "blocker"
    assert any(i["code"] == "LOCAL_SERVICE_BRANCH_MISSING" for i in r27["issues"])

    # 3. 反例 B：条款被拒绝 -> blocker (LOCAL_SERVICE_BRANCH_MISSING)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "status": "rejected",
            "reason": "项目所在地暂未设立分支机构",
            "response": "不满足本地化网点要求。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r27 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R27")
    assert r27["passed"] is False
    assert r27["severity"] == "blocker"
    assert any(i["code"] == "LOCAL_SERVICE_BRANCH_MISSING" for i in r27["issues"])

    # 4. 反例 C：无本地售后服务机构与常驻人员 -> blocker (LOCAL_SERVICE_BRANCH_MISSING)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "status": "confirmed",
            "response": "我方目前在项目所在地无本地服务机构，无本地网点，未设立办事处，无法驻场，无法提供本地化响应。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r27 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R27")
    assert r27["passed"] is False
    assert r27["severity"] == "blocker"
    assert any(i["code"] == "LOCAL_SERVICE_BRANCH_MISSING" for i in r27["issues"])


def test_r28_critical_tech_spec_negative_deviation_compliance(client):
    """验证 R28：关键技术规格实质性负偏离排查（正例放行，参数负偏离强阻断）。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r_tech = next(r for r in reqs if r["volume"] == "technical")

    # 1. 正例：关键技术指标完全满足或优于招标文件，无负偏离
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "text": "关键技术指标与参数要求（★不得负偏离）：系统服务可用性需达到 99.99%，故障切换时间小于 30 秒，任何负偏离视为无效投标。",
            "category": "technical",
            "status": "confirmed",
            "deviation_type": "none",
            "response": "我方系统可用性实测达 99.999%，故障切换时间小于 10 秒，所有关键技术指标完全满足，无负偏离，正偏离优于招标要求。",
        },
        "PATCH",
    )

    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    r28 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R28")
    assert r28["passed"] is True
    assert r28["severity"] == "info"

    # 2. 反例 A：明确标记 deviation_type 为 negative -> blocker (CRITICAL_TECH_SPEC_NEGATIVE_DEVIATION)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "deviation_type": "negative",
            "response": "参数存在负偏离说明。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r28 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R28")
    assert r28["passed"] is False
    assert r28["severity"] == "blocker"
    assert any(i["code"] == "CRITICAL_TECH_SPEC_NEGATIVE_DEVIATION" for i in r28["issues"])

    # 3. 反例 B：未填写关键技术指标参数 -> blocker (CRITICAL_TECH_SPEC_NEGATIVE_DEVIATION)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "deviation_type": "none",
            "response": "",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r28 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R28")
    assert r28["passed"] is False
    assert r28["severity"] == "blocker"
    assert any(i["code"] == "CRITICAL_TECH_SPEC_NEGATIVE_DEVIATION" for i in r28["issues"])

    # 4. 反例 C：关键技术参数存在实质性负偏离 -> blocker (CRITICAL_TECH_SPEC_NEGATIVE_DEVIATION)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "status": "confirmed",
            "response": "我方系统当前实测指标不满足 99.99%，故障切换时间为 60 秒，参数低于要求，存在实质性负偏离。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r28 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R28")
    assert r28["passed"] is False
    assert r28["severity"] == "blocker"
    assert any(i["code"] == "CRITICAL_TECH_SPEC_NEGATIVE_DEVIATION" for i in r28["issues"])


def test_export_gate_blocked_by_p5_compliance_rules(client):
    """验证整本递交导出门禁联动：存在任一 P5 规则 blocker 缺陷时，正式递交版导出严格触发 400 CHECK_BLOCKER_EXISTS。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r_bus = next(r for r in reqs if r["volume"] == "business")

    # 1. 制造 R17 规则 blocker 缺陷（未回避关联交易）
    flow.write(
        f"/requirements/{r_bus['id']}",
        {
            "text": "关联交易回避条款：投标人不得与招标人存在利害关系。",
            "category": "qualification",
            "status": "confirmed",
            "response": "存在关联关系，控股股东为招标人，未回避利害关系。",
        },
        "PATCH",
    )

    # 2. 触发全量合规检查，生成检查批次
    check_res = flow.write("/checks", {"volume": "all"})
    check = check_res["check"]
    assert check["passed"] is False
    issues = check.get("issues", [])
    assert any(i.get("code") == "CONFLICT_OF_INTEREST_UNRESOLVED" for i in issues)

    # 3. 尝试导出正式递交版（kind="submission"）-> 严格拦截 400 CHECK_BLOCKER_EXISTS
    sub_export_resp = flow.client.post(
        f"{flow.path}/exports",
        headers={
            **flow.headers,
            "If-Match": str(flow.state()["revision"]),
            "Idempotency-Key": str(uuid.uuid4()),
        },
        json={"check_id": check["id"], "kind": "submission", "volume": "all"},
    )
    assert sub_export_resp.status_code == 400, sub_export_resp.text
    err = sub_export_resp.json()
    assert err["code"] == "CHECK_BLOCKER_EXISTS"
    assert "阻断项" in err["message"]

    # 4. 内部评审版导出（kind="internal_review"）-> 放行但显式标记 has_blockers=True
    internal_export_resp = flow.client.post(
        f"{flow.path}/exports",
        headers={
            **flow.headers,
            "If-Match": str(flow.state()["revision"]),
            "Idempotency-Key": str(uuid.uuid4()),
        },
        json={"check_id": check["id"], "kind": "internal_review", "volume": "all"},
    )
    assert internal_export_resp.status_code in (200, 201), internal_export_resp.text
    internal_export_data = internal_export_resp.json()["export"]
    assert internal_export_data["has_blockers"] is True

    # 5. 修复 R17 缺陷，重新检查
    flow.write(
        f"/requirements/{r_bus['id']}",
        {
            "response": "我方与招标人无任何利害关系，不存在控股参股关系，已签署回避声明，符合回避要求。",
        },
        "PATCH",
    )
    check_res2 = flow.write("/checks", {"volume": "all"})
    check2 = check_res2["check"]
    assert not any(i.get("code") == "CONFLICT_OF_INTEREST_UNRESOLVED" for i in check2.get("issues", []))

    # 6. 重新导出内部评审版 -> 成功放行且 has_blockers 为 False
    internal_export_resp2 = flow.client.post(
        f"{flow.path}/exports",
        headers={
            **flow.headers,
            "If-Match": str(flow.state()["revision"]),
            "Idempotency-Key": str(uuid.uuid4()),
        },
        json={"check_id": check2["id"], "kind": "internal_review", "volume": "all"},
    )
    assert internal_export_resp2.status_code in (200, 201), internal_export_resp2.text
    export_obj2 = internal_export_resp2.json()["export"]
    assert export_obj2["kind"] == "internal_review"
    assert export_obj2["has_blockers"] is False

    # 7. 正式递交版门禁守护：分册定稿未完成时严格诚实守卫 409 RULES_INCOMPLETE，严禁虚假声称可递交
    sub_export_resp2 = flow.client.post(
        f"{flow.path}/exports",
        headers={
            **flow.headers,
            "If-Match": str(flow.state()["revision"]),
            "Idempotency-Key": str(uuid.uuid4()),
        },
        json={"check_id": check2["id"], "kind": "submission", "volume": "all"},
    )
    assert sub_export_resp2.status_code == 409
    assert sub_export_resp2.json()["code"] == "RULES_INCOMPLETE"
