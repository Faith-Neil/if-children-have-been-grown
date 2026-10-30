# 为什么有这个文件：验证 R33 拟派人员条件与 R38 证明材料与评分要点对应（PRD v1.8 §5.8.1、§5.1.4；APP-M2-T241、T253）。
# 它解决什么问题：招标人员条件被拆成角色、人数、学历、专业、年限、证书、AB 角、不得兼任；没排人或人员资料缺项是“资料缺失”警告，
# 资格条款不满足阻断、评分条款不满足只提示；工作年限算到投标截止时间；只有项目负责人能排人，排人时立即返回 R33 结果；
# R38 拆出功能点，附件功能点标签或同义词找不到时逐个功能点警告。全部用合成招标文件与合成人员资料。

from io import BytesIO
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from icg.domain.staff_proof_rules import conditions, features, profile
from test_reference_flow import ProjectFlow, client, login  # noqa: F401

TENDER = ("合成招标文件：拟派人员验收\n招标编号：STAFF-001\n投标截止时间：2026-12-31T17:00:00+08:00\n"
          "第一章 投标人资格要求\n1. 项目经理须具有本科及以上学历，计算机或通信相关专业，8年以上项目管理经验，"
          "持有PMP或信息系统项目管理师证书，不得兼任。\n"
          "第二章 评分办法\n一、技术方案（20分）\n1. 驻场工程师不少于2名，须设AB角，具有3年以上运维经验的得5分。\n"
          "2. 系统支持日志审计、告警推送和自动巡检功能，提供功能截图的得5分。\n"
          "第三章 技术要求\n1. 每月完成巡检并提交报告。\n")


def test_conditions_profiles_and_features_are_parsed():
    need = conditions("项目经理须具有本科及以上学历，计算机或通信相关专业，8年以上项目管理经验，持有PMP或信息系统项目管理师证书，不得兼任。")
    assert need["role"] == "项目经理" and need["degree"] == "本科" and need["majors"] == ["计算机", "通信"]
    assert need["years"] == 8 and need["certificates"] == ["PMP", "信息系统项目管理师"] and need["certificates_any"]
    assert need["exclusive"] and not need["ab_role"]
    crew = conditions("驻场工程师不少于2名，须设AB角，具有3年以上运维经验的得5分。")
    assert (crew["role"], crew["count"], crew["ab_role"], crew["years"]) == ("驻场工程师", 2, True, 3)
    assert conditions("投标人须具有有效的营业执照。") is None
    assert conditions("每月完成巡检并提交报告。") is None
    person = profile({"content": "学历：硕士\n专业：计算机科学与技术\n参加工作：2015-03\n证书：PMP、ITIL"})
    assert person == {"degree": "硕士", "major": "计算机科学与技术", "work_start": "2015-03-01", "years": None,
                      "certificates": ["PMP", "ITIL"]}
    assert profile({"content": "仅有姓名"})["degree"] is None
    assert features("系统支持日志审计、告警推送和自动巡检功能，提供功能截图的得5分。") == ["日志审计", "告警推送", "自动巡检"]


def _flow(client):
    flow = ProjectFlow(client).reviewed(TENDER)
    return flow


def _staff(flow, entries, expected=200, headers=None):
    resp = flow.client.put(f"{flow.path}/proposed-staff", json={"staff": entries},
                           headers=headers or {**flow.headers, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())})
    assert resp.status_code == expected, resp.text
    return resp.json()


def _codes(result):
    return sorted((i["code"], i["severity"]) for i in result["r33"]["issues"])


def test_r33_flags_missing_staff_then_checks_each_condition_to_the_deadline(client):
    flow = _flow(client)
    empty = client.get(f"{flow.path}/proposed-staff", headers=flow.headers).json()
    assert empty["staff"] == [] and {c for c, _ in _codes(empty)} == {"STAFF_DATA_MISSING"}
    assert "项目经理" in empty["roles"]

    zhang = flow.library(name="张合成", type="personnel", content="学历：本科\n专业：计算机科学与技术\n参加工作：2020-03\n证书：ITIL")
    li = flow.library(name="李合成", type="personnel", content="学历：大专\n专业：通信工程\n参加工作：2010-01\n证书：PMP")
    wang = flow.library(name="王合成", type="personnel", content="仅姓名，无其他资料")
    viewer = login(client, "alpha-viewer")
    _staff(flow, [{"person_id": zhang["id"], "role": "项目经理"}], expected=403,
           headers={**viewer, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())})

    result = _staff(flow, [
        {"person_id": zhang["id"], "role": "项目负责人", "is_key_person": True},  # 别名归为项目经理
        {"person_id": zhang["id"], "role": "驻场工程师", "position": "A"},
        {"person_id": wang["id"], "role": "驻场工程师"},
    ])
    assert [s["role"] for s in result["staff"]] == ["项目经理", "驻场工程师", "驻场工程师"]
    assert result["staff"][0]["profile"]["work_start"] == "2020-03-01"
    issues = {(i["code"], i["severity"]) for i in result["r33"]["issues"]}
    # 资格条款（项目经理）不满足 → 阻断：不足 8 年（2020-03 到截止约 6.8 年）、缺 PMP/信息系统项目管理师、兼任驻场
    assert {("STAFF_YEARS_UNMET", "blocker"), ("STAFF_CERT_MISSING", "blocker"), ("STAFF_DUAL_ROLE", "blocker")} <= issues
    # 评分条款（驻场 AB 角）不满足 → 只提示；王合成资料缺年限 → 资料缺失警告
    assert ("STAFF_AB_ROLE_MISSING", "info") in issues and ("STAFF_DATA_MISSING", "warning") in issues
    years = next(i for i in result["r33"]["issues"] if i["code"] == "STAFF_YEARS_UNMET")
    assert years["details"]["years"] == pytest.approx(6.8, abs=0.1)
    assert result["r33"]["severity"] == "blocker" and not result["r33"]["passed"]

    fixed = _staff(flow, [
        {"person_id": li["id"], "role": "项目经理"},
        {"person_id": zhang["id"], "role": "驻场工程师", "position": "A"},
        {"person_id": wang["id"], "role": "驻场工程师", "position": "B"},
    ])
    left = {(i["code"], i["severity"]) for i in fixed["r33"]["issues"]}
    assert ("STAFF_DEGREE_UNMET", "blocker") in left  # 李合成大专，低于本科
    assert not any(code in ("STAFF_CERT_MISSING", "STAFF_DUAL_ROLE", "STAFF_AB_ROLE_MISSING") for code, _ in left)
    bad = _staff(flow, [{"person_id": "evidence-nope", "role": "项目经理"}], expected=422)
    assert "人员" in bad["message"]


def test_r33_and_r38_run_in_project_checks(client, monkeypatch):
    monkeypatch.setenv("ICG_SECRET_KEY", Fernet.generate_key().decode())
    flow = _flow(client)
    shot = flow.library(name="合成运维平台功能截图", type="performance", content="平台功能截图合集")
    row = next(r for r in flow.state()["requirements"] if "日志审计" in r["text"])
    flow.write("/requirements/" + row["id"], {"evidence_ids": [shot["id"]]}, "PATCH")
    from PIL import Image
    buffer = BytesIO()
    Image.new("RGB", (200, 100), "white").save(buffer, "PNG")
    uploaded = client.post(f"/api/v1/library/{shot['id']}/attachments/raw", params={"filename": "截图.png"}, content=buffer.getvalue(),
                           headers={**flow.headers, "Content-Type": "application/octet-stream"}).json()["attachment"]
    client.patch(f"/api/v1/library/attachments/{uploaded['id']}", json={"feature_tags": ["日志审计", "告警"]}, headers=flow.headers)
    admin = login(client, "alpha-company-admin")
    saved = client.patch("/api/v1/companies/alpha/settings", headers=admin,
                         json={"custom_settings": {"r38_synonyms": {"告警推送": ["告警", "报警"]}}})
    assert saved.status_code == 200, saved.text

    state = client.app.state.service.repository.read()
    from icg.domain.compliance_rules import ComplianceRulesEngine
    results = {r.rule_id: r for r in ComplianceRulesEngine.evaluate_p6_rules(state, state.projects[flow.id], state.workflows[flow.id])}
    r38 = results["R38"]
    assert [i["details"]["feature"] for i in r38.issues] == ["自动巡检"] and r38.severity == "warning"
    assert results["R33"].issues and all(i["code"] == "STAFF_DATA_MISSING" for i in results["R33"].issues)
    catalog = {item["rule_id"] for item in ComplianceRulesEngine.CATALOG}
    assert {"R33", "R38"} <= catalog
    from icg.domain.workflow_orchestrator import WorkflowService
    assert {"R33", "R38"} <= set(WorkflowService.IMPLEMENTED_RULES)

    before = flow.state()["input_fingerprint"]
    client.patch(f"/api/v1/library/attachments/{uploaded['id']}", json={"feature_tags": ["日志审计", "告警", "自动巡检"]}, headers=flow.headers)
    assert flow.state()["input_fingerprint"] != before  # 改附件标签后旧检查过期
