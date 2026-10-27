# 为什么有这个文件：为 PRD MVP §5.8 第三批核心合规规则（R07/R11/R14/R25/R31，BE-COMPLIANCE-RULES-P2）提供专属自动化测试套件。
# 它解决什么问题：
# 1. 验证 R07 原厂授权覆盖与多级授权链核验（授权缺失/过期/产品不覆盖/授权链断裂强阻断，正例放行）；
# 2. 验证 R11 本单位人员与社保缴纳核验（借调挂靠/社保证明缺失/缴纳单位不符/断缴未连续/合同过期强阻断，正例放行）；
# 3. 验证 R14 必备附件齐全性核验（开标一览表、法人授权委托书、保函、承诺函等强制必备附件缺失强阻断，齐全放行）；
# 4. 验证 R25 其他公司/旧项目名称与文档残留排查（正文与条款响应中旧项目名称/某某公司/占位残留强阻断，整洁放行）；
# 5. 验证 R31 真实巡检报告与敏感信息残留排查（明文身份证/银行卡号/数据库口令/真实巡检报告特征强阻断，脱敏合规放行）；
# 6. 验证整本递交导出门禁联动（存在上述任一 blocker 缺陷时，正式递交版 submission 严格触发 400 CHECK_BLOCKER_EXISTS）。

import uuid
import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from test_reference_flow import ProjectFlow, client, login


def test_r07_original_manufacturer_authorization(client):
    """验证 R07：原厂授权覆盖与多级授权链核验（正例放行、授权缺失、响应无法提供、过期、产品不覆盖、多级链断裂阻断）。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r_tech = next(r for r in reqs if r["volume"] == "technical")

    # 1. 正例：挂接有效且在保质期内的原厂授权书，覆盖指定产品
    auth_lib = flow.library(
        name="Oracle原厂技术服务授权书（Oracle数据库）",
        content="原厂商授权内容：授权我方为本项目指定产品Oracle数据库提供原厂服务支持及质保承诺。",
        valid_until="2027-12-31",
        type="qualification",
    )
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "text": "投标人须具备原厂商授权：提供针对Oracle数据库的原厂服务承诺函及授权书。",
            "category": "qualification",
            "evidence_ids": [auth_lib["id"]],
            "status": "confirmed",
            "response": "我方已取得原厂商正式授权书及技术支持承诺，在投标截止期内真实有效。",
        },
        "PATCH",
    )
    flow.write("", {"deadline": "2026-12-31T17:00:00+08:00"}, "PATCH")

    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    r07 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R07")
    assert r07["passed"] is True
    assert r07["severity"] == "info"

    # 2. 反例 A：要求原厂授权，未挂接任何原厂授权材料 -> blocker (ORIGINAL_MANUFACTURER_AUTHORIZATION_MISSING)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "evidence_ids": [],
            "response": "我方具备相关原厂合作关系。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r07 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R07")
    assert r07["passed"] is False
    assert r07["severity"] == "blocker"
    assert any(i["code"] == "ORIGINAL_MANUFACTURER_AUTHORIZATION_MISSING" for i in r07["issues"])

    # 3. 反例 B：条款响应明确声称“无法提供原厂授权” -> blocker (ORIGINAL_MANUFACTURER_AUTHORIZATION_MISSING)
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "evidence_ids": [auth_lib["id"]],
            "response": "经与厂商沟通，由于商务条款分歧，本次无法提供原厂授权，由我方自研团队提供等同支持。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r07 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R07")
    assert r07["passed"] is False
    assert r07["severity"] == "blocker"
    assert any(i["code"] == "ORIGINAL_MANUFACTURER_AUTHORIZATION_MISSING" for i in r07["issues"])

    # 4. 反例 C：原厂授权书在投标截止日已过期失效 -> blocker (ORIGINAL_MANUFACTURER_AUTHORIZATION_MISSING)
    # 先将截止时间设为早于授权书有效期的日期以便成功关联，随后更新截止时间为推迟后的日期，触发原厂授权过期阻断
    expired_auth = flow.library(
        name="已过期的原厂技术支持承诺函（Oracle数据库）",
        content="原厂技术服务授权书。",
        valid_until="2025-12-31",
    )
    flow.write("", {"deadline": "2025-01-01T17:00:00+08:00"}, "PATCH")
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "evidence_ids": [expired_auth["id"]],
            "response": "提供原厂技术服务授权书。",
        },
        "PATCH",
    )
    flow.write("", {"deadline": "2026-12-31T17:00:00+08:00"}, "PATCH")
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r07 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R07")
    assert r07["passed"] is False
    assert r07["severity"] == "blocker"
    assert any(i["code"] == "ORIGINAL_MANUFACTURER_AUTHORIZATION_MISSING" for i in r07["issues"])

    # 5. 反例 D：原厂授权未覆盖招标文件指定产品 -> blocker (ORIGINAL_MANUFACTURER_AUTHORIZATION_MISSING)
    unmatched_auth = flow.library(
        name="MySQL技术支持授权书",
        content="原厂授权产品：仅限MySQL数据库，未覆盖Oracle数据库产品。",
        valid_until="2028-12-31",
    )
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "text": "投标人须具备原厂商授权：提供针对Oracle数据库的原厂服务承诺函及授权书。",
            "evidence_ids": [unmatched_auth["id"]],
            "response": "提供厂商技术授权材料。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r07 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R07")
    assert r07["passed"] is False
    assert r07["severity"] == "blocker"
    assert any(i["code"] == "ORIGINAL_MANUFACTURER_AUTHORIZATION_MISSING" for i in r07["issues"])

    # 6. 反例 E：多级代理转授权链条断裂 -> blocker (ORIGINAL_MANUFACTURER_AUTHORIZATION_MISSING)
    broken_chain_auth = flow.library(
        name="二级代理商转授权函（多级授权链断裂）",
        content="转授权声明：多级授权链条断裂，缺失上游原厂一级授权文件。",
        valid_until="2027-12-31",
    )
    flow.write(
        f"/requirements/{r_tech['id']}",
        {
            "evidence_ids": [broken_chain_auth["id"]],
            "response": "提供二级代理转授权函。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r07 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R07")
    assert r07["passed"] is False
    assert r07["severity"] == "blocker"
    assert any(i["code"] == "ORIGINAL_MANUFACTURER_AUTHORIZATION_MISSING" for i in r07["issues"])


def test_r11_personnel_and_social_security(client):
    """验证 R11：本单位人员与社保缴纳核验（正例放行、借调外部人员、社保证明缺失、缴纳单位不一致、未连续缴纳阻断）。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r_biz = next(r for r in reqs if r["volume"] == "business")

    # 1. 正例：挂接有效社保证明与劳动合同，社保由投标主体连续缴纳
    social_sec_lib = flow.library(
        name="拟派项目经理社保证明与劳动合同",
        content="社保证明：由投标主体按月连续缴纳近6个月社保，劳动合同真实有效覆盖截止日。",
        valid_until="2027-12-31",
        type="qualification",
    )
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "text": "拟派团队资格：拟派项目经理须为本单位人员，提供近6个月连续缴纳社保证明及劳动合同。",
            "category": "personnel",
            "evidence_ids": [social_sec_lib["id"]],
            "status": "confirmed",
            "response": "拟派项目经理为我方正式在职员工，由我单位按月连续缴纳社会保险，附社保证明及劳动合同。",
        },
        "PATCH",
    )

    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r11 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R11")
    assert r11["passed"] is True
    assert r11["severity"] == "info"

    # 2. 反例 A：响应声明拟派人员为外部借调/第三方代缴 -> blocker (PERSONNEL_SOCIAL_SECURITY_MISMATCH)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "response": "项目经理为外部高校专家借调人员，社保不在本单位缴纳，提供专家特聘协议。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r11 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R11")
    assert r11["passed"] is False
    assert r11["severity"] == "blocker"
    assert any(i["code"] == "PERSONNEL_SOCIAL_SECURITY_MISMATCH" for i in r11["issues"])

    # 3. 反例 B：要求社保证明但未挂接证明材料 -> blocker (PERSONNEL_SOCIAL_SECURITY_MISMATCH)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "evidence_ids": [],
            "response": "项目经理为本单位正式员工，承诺按期到岗。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r11 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R11")
    assert r11["passed"] is False
    assert r11["severity"] == "blocker"
    assert any(i["code"] == "PERSONNEL_SOCIAL_SECURITY_MISMATCH" for i in r11["issues"])

    # 4. 反例 C：挂接证明材料显示社保缴纳单位与投标主体不一致 -> blocker (PERSONNEL_SOCIAL_SECURITY_MISMATCH)
    mismatch_lib = flow.library(
        name="第三方劳务派遣社保证明",
        content="社保证明：拟派人员社保缴纳单位为第三方劳务派遣有限公司，社保不在本单位缴纳，社保不一致。",
        valid_until="2027-12-31",
    )
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "evidence_ids": [mismatch_lib["id"]],
            "response": "提供拟派人员社保证明。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r11 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R11")
    assert r11["passed"] is False
    assert r11["severity"] == "blocker"
    assert any(i["code"] == "PERSONNEL_SOCIAL_SECURITY_MISMATCH" for i in r11["issues"])

    # 5. 反例 D：社保存在断缴未连续缴纳 -> blocker (PERSONNEL_SOCIAL_SECURITY_MISMATCH)
    interrupted_lib = flow.library(
        name="存在断缴的社保证明",
        content="社保证明：近6个月内存在断缴记录，社保未连续缴纳。",
        valid_until="2027-12-31",
    )
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "evidence_ids": [interrupted_lib["id"]],
            "response": "提供拟派人员社保证明。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r11 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R11")
    assert r11["passed"] is False
    assert r11["severity"] == "blocker"
    assert any(i["code"] == "PERSONNEL_SOCIAL_SECURITY_MISMATCH" for i in r11["issues"])


def test_r14_mandatory_attachments_verification(client):
    """验证 R14：必备附件齐全性核验（正例放行、开标一览表缺失、法人授权委托书缺失、保证金保函缺失阻断）。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r_biz = next(r for r in reqs if r["volume"] == "business")

    # 1. 设置条款要求 5 大必备附件
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "text": "投标必备附件：必须提供开标一览表、法定代表人身份证明与授权委托书、投标保证金证明或电子保函、承诺函、资质证书附件。",
            "category": "mandatory_attachment",
            "status": "confirmed",
            "response": "所有法定及必备附件已按招标文件要求全部编入商务分册。",
        },
        "PATCH",
    )

    # 此时仅具备企业资质，缺少开标一览表、授权委托书、保函、承诺函 -> blocker (MANDATORY_ATTACHMENT_MISSING)
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r14 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R14")
    assert r14["passed"] is False
    assert r14["severity"] == "blocker"
    missing_codes = [i["code"] for i in r14["issues"]]
    assert all(c == "MANDATORY_ATTACHMENT_MISSING" for c in missing_codes)
    missing_keys = [i["details"]["attachment_key"] for i in r14["issues"]]
    assert "quotation_sheet" in missing_keys
    assert "legal_auth" in missing_keys
    assert "bid_bond" in missing_keys
    assert "commitment_letter" in missing_keys

    # 2. 逐步上传/补齐必备附件文件
    flow.upload(content="开标一览表内容明细".encode("utf-8"), filename="开标一览表-盖章扫描件.pdf")
    flow.upload(content="法定代表人授权委托书盖章件".encode("utf-8"), filename="法定代表人身份证明与授权委托书.pdf")
    flow.upload(content="银行投标保函凭据".encode("utf-8"), filename="投标保证金银行电子保函.pdf")
    flow.upload(content="投标人廉洁与合规承诺函".encode("utf-8"), filename="投标承诺函-签署件.pdf")

    # 再次核验 -> 全部补齐，通过！
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r14 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R14")
    assert r14["passed"] is True
    assert r14["severity"] == "info"


def test_r25_entity_name_and_legacy_residuals(client):
    """验证 R25：其他公司/旧项目名称与文档残留排查（正例放行、正文旧标书占位公司残留、响应旧项目残留阻断）。"""
    flow = ProjectFlow(client).ready()
    chapters = flow.state()["chapters"]
    tech_chapter = next(c for c in chapters if c["volume"] == "technical")

    # 1. 正例：正文内容清洁，无旧项目和其他公司残留
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r25 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R25")
    assert r25["passed"] is True
    assert r25["severity"] == "info"

    # 2. 反例 A：章节正文中出现复制旧标书遗留的占位公司残留 -> blocker (ENTITY_NAME_RESIDUAL_DETECTED)
    flow.commit(tech_chapter["id"], "日常运维巡检方案：由某某科技负责数据库日常巡检，严格按期提交巡检报告。")
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r25 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R25")
    assert r25["passed"] is False
    assert r25["severity"] == "blocker"
    assert any(i["code"] == "ENTITY_NAME_RESIDUAL_DETECTED" for i in r25["issues"])

    # 3. 反例 B：正文中出现【旧标残留】或显式旧项目名称特征 -> blocker (ENTITY_NAME_RESIDUAL_DETECTED)
    flow.commit(tech_chapter["id"], "本章节编写参考原项目名称：中国建设银行2024期核心维保项目（旧标残留）。")
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r25 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R25")
    assert r25["passed"] is False
    assert r25["severity"] == "blocker"
    assert any(i["code"] == "ENTITY_NAME_RESIDUAL_DETECTED" for i in r25["issues"])

    # 4. 反例 C：条款响应文本中出现其他公司残留 -> blocker (ENTITY_NAME_RESIDUAL_DETECTED)
    reqs = flow.state()["requirements"]
    r0 = reqs[0]
    flow.commit(tech_chapter["id"], "日常运维巡检方案：由我方专业工程师负责日常巡检。")
    flow.write(
        f"/requirements/{r0['id']}",
        {
            "response": "本项目由XXX公司承诺提供7x24小时现场响应服务支持。",
        },
        "PATCH",
    )
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r25 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R25")
    assert r25["passed"] is False
    assert r25["severity"] == "blocker"
    assert any(i["code"] == "ENTITY_NAME_RESIDUAL_DETECTED" for i in r25["issues"])


def test_r31_sensitive_data_and_real_inspection_residuals(client):
    """验证 R31：真实巡检报告与敏感信息残留排查（正例放行、18位明文身份证、银行卡号、数据库密码、真实巡检报告特征阻断）。"""
    flow = ProjectFlow(client).ready()
    chapters = flow.state()["chapters"]
    tech_chapter = next(c for c in chapters if c["volume"] == "technical")

    # 1. 正例：正文内容规范脱敏，无明文高敏数据及现成巡检报告套用
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r31 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R31")
    assert r31["passed"] is True
    assert r31["severity"] == "info"

    # 2. 反例 A：章节正文出现未脱敏的 18 位明文身份证号 -> blocker (SENSITIVE_DATA_RESIDUAL_DETECTED)
    flow.commit(tech_chapter["id"], "项目负责人张工（身份证号：110101199003072345）常驻现场统筹运维。")
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r31 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R31")
    assert r31["passed"] is False
    assert r31["severity"] == "blocker"
    assert any(i["code"] == "SENSITIVE_DATA_RESIDUAL_DETECTED" for i in r31["issues"])

    # 3. 反例 B：正文出现未脱敏的银行卡号明文暴露 -> blocker (SENSITIVE_DATA_RESIDUAL_DETECTED)
    flow.commit(tech_chapter["id"], "收款账户明细：公司对公银行账号：6222021234567890123，开户行北京分行。")
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r31 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R31")
    assert r31["passed"] is False
    assert r31["severity"] == "blocker"
    assert any(i["code"] == "SENSITIVE_DATA_RESIDUAL_DETECTED" for i in r31["issues"])

    # 4. 反例 C：正文出现数据库明文口令暴露 -> blocker (SENSITIVE_DATA_RESIDUAL_DETECTED)
    flow.commit(tech_chapter["id"], "数据库测试联通配置参数：db_host=10.0.0.1; port=3306; password=AdminSecurePass!123")
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r31 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R31")
    assert r31["passed"] is False
    assert r31["severity"] == "blocker"
    assert any(i["code"] == "SENSITIVE_DATA_RESIDUAL_DETECTED" for i in r31["issues"])

    # 5. 反例 D：正文直接套用真实客户现场巡检报告特征 -> blocker (SENSITIVE_DATA_RESIDUAL_DETECTED)
    flow.commit(tech_chapter["id"], "现场巡检报告：记录2026年9月机房设备运行巡检表，巡检人员李工，温度22度正常。")
    resp = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert resp.status_code == 200
    r31 = next(r for r in resp.json()["rules"] if r["rule_id"] == "R31")
    assert r31["passed"] is False
    assert r31["severity"] == "blocker"
    assert any(i["code"] == "SENSITIVE_DATA_RESIDUAL_DETECTED" for i in r31["issues"])


def test_export_gate_blocked_by_p2_compliance_rules(client):
    """验证整本递交导出门禁联动：当存在 P2 核心合规阻断缺陷时，正式递交版导出严格返回 400 CHECK_BLOCKER_EXISTS。"""
    flow = ProjectFlow(client).ready()
    chapters = flow.state()["chapters"]
    tech_chapter = next(c for c in chapters if c["volume"] == "technical")

    # 在正文中植入 R31 明文身份证敏感信息 blocker 缺陷
    flow.commit(tech_chapter["id"], "现场常驻专家：王工（身份证号：110101198505051234），负责数据库容灾切换。")

    # 执行项目检查
    check_res = flow.write("/checks", {"volume": "all"})
    check = check_res["check"]
    assert check["passed"] is False

    # 确认检查结果中存在 R31 blocker 缺陷
    blocker_issues = [i for i in check["issues"] if i.get("severity") == "blocker"]
    assert len(blocker_issues) > 0
    assert any(i.get("code") == "SENSITIVE_DATA_RESIDUAL_DETECTED" for i in blocker_issues)
    assert any(i.get("rule_id") == "R31" for i in blocker_issues)

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
