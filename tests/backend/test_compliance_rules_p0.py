# 为什么有这个文件：为 PRD MVP §5.8 P0 合规规则体系（BE-COMPLIANCE-RULES-P0）提供专属自动化测试套件。
# 它解决什么问题：
# 1. 验证 R15 证明材料齐全性（证据缺失、失效、过期拦截）；
# 2. 验证 R23 废标红线与关键标星条款响应率（100% 覆盖与非空确认，未响应则 blocker）；
# 3. 验证 R34 占位符与“待补/待完善”残留字样（检测到残留即阻断导出）；
# 4. 验证 R37 技术/商务偏离表一致性（负偏离强阻断，正偏离与无偏离一致性校验）；
# 5. 验证 /api/v1 契约端点、多租户强隔离与已挂载规则目录。

import uuid
import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from test_reference_flow import ProjectFlow, client, login


def test_r15_proof_material_completeness(client):
    """验证 R15：证明材料齐全性核验（正例与缺失/过期/未确认反例）。"""
    flow = ProjectFlow(client).ready()
    state = flow.state()
    reqs = state["requirements"]
    r_biz = next(r for r in reqs if r["volume"] == "business")

    # 1. 正例：已有有效证据挂接
    resp = flow.client.get(
        f"{flow.path}/compliance-rules",
        headers=flow.headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    r15_res = next(r for r in data["rules"] if r["rule_id"] == "R15")
    assert r15_res["passed"] is True
    assert r15_res["severity"] == "info"
    assert len(r15_res["issues"]) == 0

    # 2. 反例 A：证明类要求未挂接任何证据 (EVIDENCE_MISSING)
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "text": "商务证明要求：投标人须提供近三年经审计的财务报表及纳税凭证。",
            "category": "qualification",
            "evidence_ids": [],
            "status": "confirmed",
            "response": "已按要求准备财务审计报表及相关证明文件。",
        },
        "PATCH",
    )
    res = flow.client.post(
        f"{flow.path}/compliance-rules/evaluate",
        headers=flow.headers,
        json={"volume": "all"},
    )
    assert res.status_code == 200
    r15 = next(r for r in res.json()["rules"] if r["rule_id"] == "R15")
    assert r15["passed"] is False
    assert any(i["code"] == "EVIDENCE_MISSING" for i in r15["issues"])

    # 3. 反例 B：引用的证据已过期 (EVIDENCE_EXPIRED)
    # 挂接有效证据，但项目截止时间延期超过证书有效期
    valid_lib = flow.library(valid_until="2027-12-31", name="合规质量体系认证")
    flow.write(
        f"/requirements/{r_biz['id']}",
        {
            "evidence_ids": [valid_lib["id"]],
            "status": "confirmed",
            "response": "提供质量认证体系证书。",
        },
        "PATCH",
    )
    # 将项目截止时间延期至 2028-12-31（超出证书有效期 2027-12-31）
    flow.write("", {"deadline": "2028-12-31T17:00:00+08:00"}, "PATCH")
    res = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert res.status_code == 200
    r15 = next(r for r in res.json()["rules"] if r["rule_id"] == "R15")
    assert r15["passed"] is False
    assert any(i["code"] == "EVIDENCE_EXPIRED" for i in r15["issues"])
    # 恢复项目截止时间
    flow.write("", {"deadline": "2026-12-31T17:00:00+08:00"}, "PATCH")

    # 4. 反例 C：证据库条目被修改需重新核对，处于 pending 状态 (EVIDENCE_NOT_USABLE)
    lib_rev = flow.client.get("/api/v1/library", headers=flow.headers).json()["revision"]
    res_patch = flow.client.patch(
        f"/api/v1/library/{valid_lib['id']}",
        json={"name": "资质原件-重新修改待审核"},
        headers={**flow.headers, "If-Match": str(lib_rev), "Idempotency-Key": str(uuid.uuid4())},
    )
    assert res_patch.status_code == 200
    res = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert res.status_code == 200
    r15 = next(r for r in res.json()["rules"] if r["rule_id"] == "R15")
    assert r15["passed"] is False
    assert any(i["code"] == "EVIDENCE_NOT_USABLE" for i in r15["issues"])


def test_r23_critical_clauses_100_percent_response(client):
    """验证 R23：废标红线与关键标星条款响应率核验（100% 覆盖与非空确认，未响应则 blocker）。"""
    flow = ProjectFlow(client).ready()
    state = flow.state()
    reqs = state["requirements"]
    r0 = reqs[0]

    # 1. 废标红线条款未填写响应内容 -> blocker (MATRIX_RESPONSE_MISSING)
    flow.write(
        f"/requirements/{r0['id']}",
        {
            "text": "废标红线：供应商未取得数据库原厂服务资质将作否决投标处理。",
            "category": "disqualification",
            "status": "confirmed",
            "response": "",
            "reason": "废标红线条款",
        },
        "PATCH",
    )
    res = flow.client.post(
        f"{flow.path}/compliance-rules/evaluate",
        headers=flow.headers,
        json={"volume": "all"},
    )
    assert res.status_code == 200
    r23 = next(r for r in res.json()["rules"] if r["rule_id"] == "R23")
    assert r23["passed"] is False
    assert r23["severity"] == "blocker"
    assert any(i["code"] == "MATRIX_RESPONSE_MISSING" and i["severity"] == "blocker" for i in r23["issues"])

    # 2. 废标红线条款响应包含待补 -> blocker (CRITICAL_RESPONSE_INVALID)
    flow.write(
        f"/requirements/{r0['id']}",
        {
            "response": "待补充原厂授权原件说明。",
        },
        "PATCH",
    )
    res = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert res.status_code == 200
    r23 = next(r for r in res.json()["rules"] if r["rule_id"] == "R23")
    assert r23["passed"] is False
    assert any(i["code"] == "CRITICAL_RESPONSE_INVALID" and i["severity"] == "blocker" for i in r23["issues"])

    # 3. 关键标星条款被错误标记为 rejected -> blocker (CRITICAL_REQUIREMENT_REJECTED)
    flow.write(
        f"/requirements/{r0['id']}",
        {
            "text": "★技术关键要求：核心巡检必须每周执行一次。",
            "category": "star",
            "response": "完全响应。",
        },
        "PATCH",
    )
    flow.write(
        f"/requirements/{r0['id']}",
        {
            "status": "rejected",
            "reason": "不适用忽略",
        },
        "PATCH",
    )
    res = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert res.status_code == 200
    r23 = next(r for r in res.json()["rules"] if r["rule_id"] == "R23")
    assert r23["passed"] is False
    assert any(i["code"] == "CRITICAL_REQUIREMENT_REJECTED" and i["severity"] == "blocker" for i in r23["issues"])

    # 4. 关键标星条款未映射有效章节 -> blocker (MATRIX_MAPPING_MISSING)
    flow.write(
        f"/requirements/{r0['id']}",
        {
            "status": "confirmed",
            "chapter_id": None,
            "response": "完全满足。",
        },
        "PATCH",
    )
    res = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert res.status_code == 200
    r23 = next(r for r in res.json()["rules"] if r["rule_id"] == "R23")
    assert r23["passed"] is False
    assert any(i["code"] == "MATRIX_MAPPING_MISSING" and i["severity"] == "blocker" for i in r23["issues"])


def test_r34_placeholder_and_residual_verification(client):
    """验证 R34：占位符与“待补/待完善”残留字样核验（检测到残留即为 blocking/blocker）。"""
    flow = ProjectFlow(client).ready()
    chapters = flow.state()["chapters"]
    target_chapter = chapters[0]

    # 1. 正例：clean state 应该通过 R34
    res = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert res.status_code == 200
    r34 = next(r for r in res.json()["rules"] if r["rule_id"] == "R34")
    assert r34["passed"] is True
    assert r34["severity"] == "info"

    # 2. 反例 A：章节正文中包含【待补】
    flow.commit(target_chapter["id"], "本章节正文正在编写中，数据库巡检方案【待补：补充巡检表】。")
    res = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert res.status_code == 200
    r34 = next(r for r in res.json()["rules"] if r["rule_id"] == "R34")
    assert r34["passed"] is False
    assert r34["severity"] in ("blocking", "blocker")
    assert any(i["code"] == "PLACEHOLDER_RESIDUAL" for i in r34["issues"])

    # 3. 反例 B：章节正文中包含 TODO 或未替换模板变量 {{var}}
    flow.commit(target_chapter["id"], "数据库故障切换指标如下：TODO 补充切换时延 {{sla_metric}} 秒。")
    res = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert res.status_code == 200
    r34 = next(r for r in res.json()["rules"] if r["rule_id"] == "R34")
    assert r34["passed"] is False
    assert any(i["code"] == "PLACEHOLDER_RESIDUAL" for i in r34["issues"])

    # 4. 反例 C：章节正文中遗留 AI 对话残留句
    flow.commit(target_chapter["id"], "本项目维保体系完整。希望对你有帮助，如果还有其他需要补充请随时告诉我。")
    res = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert res.status_code == 200
    r34 = next(r for r in res.json()["rules"] if r["rule_id"] == "R34")
    assert r34["passed"] is False
    assert any(i["code"] == "AI_CONVERSATION_RESIDUAL" for i in r34["issues"])


def test_r37_deviation_table_consistency(client):
    """验证 R37：技术/商务偏离表一致性核验（负偏离强阻断，正偏离与无偏离一致性校验）。"""
    flow = ProjectFlow(client).ready()
    reqs = flow.state()["requirements"]
    r0 = reqs[0]
    r1 = reqs[1]

    # 1. 废标/标星关键条款出现负偏离 -> 强阻断 blocker (DEVIATION_NEGATIVE_CRITICAL)
    flow.write(
        f"/requirements/{r0['id']}",
        {
            "text": "★技术关键要求：提供 7x24 小时现场技术支持响应。",
            "category": "star",
            "deviation_type": "negative",
            "status": "confirmed",
            "response": "我方仅能提供 5x8 小时支持，存在负偏离。",
        },
        "PATCH",
    )
    res = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert res.status_code == 200
    r37 = next(r for r in res.json()["rules"] if r["rule_id"] == "R37")
    assert r37["passed"] is False
    assert r37["severity"] == "blocker"
    assert any(i["code"] == "DEVIATION_NEGATIVE_CRITICAL" and i["severity"] == "blocker" for i in r37["issues"])

    # 2. 偏离表登记与响应文本矛盾冲突 (DEVIATION_CONFLICT)
    # 登记为负偏离，但响应文本声称完全满足无偏离
    flow.write(
        f"/requirements/{r0['id']}",
        {
            "text": "技术要求：系统备份数据保留 180 天。",
            "category": "technical",
            "deviation_type": "negative",
            "status": "confirmed",
            "response": "我司完全满足要求，全部响应无偏离。",
        },
        "PATCH",
    )
    res = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert res.status_code == 200
    r37 = next(r for r in res.json()["rules"] if r["rule_id"] == "R37")
    assert r37["passed"] is False
    assert any(i["code"] == "DEVIATION_CONFLICT" for i in r37["issues"])

    # 登记为无偏离，但响应文本表述存在负偏离
    flow.write(
        f"/requirements/{r0['id']}",
        {
            "deviation_type": "none",
            "response": "因存储资源限制，该指标存在负偏离，无法满足180天要求。",
        },
        "PATCH",
    )
    res = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert res.status_code == 200
    r37 = next(r for r in res.json()["rules"] if r["rule_id"] == "R37")
    assert r37["passed"] is False
    assert any(i["code"] == "DEVIATION_CONFLICT" for i in r37["issues"])

    # 3. 正偏离缺少实质说明 (DEVIATION_POSITIVE_UNEXPLAINED)
    flow.write(
        f"/requirements/{r1['id']}",
        {
            "text": "技术要求：数据库巡检每月一次。",
            "category": "technical",
            "deviation_type": "positive",
            "status": "confirmed",
            "response": "正偏离",
            "reason": "",
        },
        "PATCH",
    )
    res = flow.client.get(f"{flow.path}/compliance-rules", headers=flow.headers)
    assert res.status_code == 200
    r37 = next(r for r in res.json()["rules"] if r["rule_id"] == "R37")
    assert any(i["code"] == "DEVIATION_POSITIVE_UNEXPLAINED" for i in r37["issues"])


def test_compliance_rules_catalog_api(client):
    """验证 GET /api/v1/compliance-rules/catalog 元数据目录端点。"""
    headers = login(client, "alpha-manager")
    resp = client.get("/api/v1/compliance-rules/catalog", headers=headers)
    assert resp.status_code == 200, resp.text
    catalog = resp.json()["catalog"]
    assert len(catalog) == 4
    rule_ids = {item["rule_id"] for item in catalog}
    assert rule_ids == {"R15", "R23", "R34", "R37"}
    for item in catalog:
        assert item["can_disable"] is False
        assert item["title"]
        assert item["default_severity"] in ("blocker", "blocking")


def test_compliance_rules_tenant_and_auth_isolation(client):
    """验证合规规则评估端点的租户强隔离与未认证拦截。"""
    flow = ProjectFlow(client).ready()

    # 1. 未认证访问返回 401
    unauth = client.get(f"{flow.path}/compliance-rules")
    assert unauth.status_code == 401

    # 2. 跨租户访问返回 404
    beta_headers = login(client, "beta-manager")
    cross = client.get(f"{flow.path}/compliance-rules", headers=beta_headers)
    assert cross.status_code == 404
    assert cross.json()["code"] == "NOT_FOUND"


def test_run_check_integrates_p0_compliance_rules(client):
    """验证既有项目检查 /checks 端点自动集成 P0 规则与编号。"""
    flow = ProjectFlow(client).ready()
    state = flow.state()
    r0 = state["requirements"][0]

    # 设置废标条款未响应
    flow.write(
        f"/requirements/{r0['id']}",
        {
            "text": "废标红线：原厂授权证书缺失将直接否决投标。",
            "category": "disqualification",
            "status": "confirmed",
            "response": "",
            "reason": "废标测试",
        },
        "PATCH",
    )

    check_res = flow.write("/checks", {"volume": "all"})
    check = check_res["check"]
    assert check["passed"] is False

    # 检验 rules 列表中包含 P0 四大规则
    assert "rules" in check
    rule_ids = [r["rule_id"] for r in check["rules"]]
    assert set(rule_ids) == {"R15", "R23", "R34", "R37"}

    # 检验 coverage["implemented_rules"] 包含 R15, R23, R34, R37
    impl_rules = check["coverage"]["implemented_rules"]
    for expected in ("R15", "R23", "R34", "R37"):
        assert expected in impl_rules

    # 检验废标条款生成的 issue 携带了 rule_id="R23"
    disqual_issues = [i for i in check["issues"] if i.get("requirement_id") == r0["id"]]
    assert len(disqual_issues) > 0
    assert any(i.get("rule_id") == "R23" for i in disqual_issues)
    assert any(i.get("severity") == "blocker" for i in disqual_issues)
