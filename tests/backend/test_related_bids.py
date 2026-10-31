# 为什么有这个文件：验证 R19 关联投标冲突（APP-M2-T096 / PRD v1.8 §5.1.2 业务规则 2、§8.3、验收②③）。
# 它解决什么问题：同一标段已有平台内其他公司立项时，填写招标编号必定被拦下且不能跳过说明；提示只给对方公司名称；
# 说明留痕并通知集团管理员；导出前检查再核一次；原先误标为 R19 的绿色采购规则不再占用 R19。

from uuid import uuid4

from icg.domain.company_settings import company_display_name
from icg.domain.compliance_rules import ComplianceRulesEngine
from icg.domain.related_bids import match, normalize, project_keys
from test_reference_flow import ProjectFlow, client, login  # noqa: F401


def _names(client):
    state = client.app.state.service.repository.read()
    return company_display_name(state, "alpha"), company_display_name(state, "beta")


def _beta(client, name="乙公司同标段投标"):
    flow = ProjectFlow(client, account="beta-manager")
    flow.write("", {"name": name}, "PATCH")
    return flow


def test_same_lot_in_another_company_needs_a_reason(client):
    alpha_name, beta_name = _names(client)
    alpha = ProjectFlow(client)
    alpha.write("", {"name": "甲公司数据库维保项目（内部名称）", "tender_number": "ZB-R19-001"}, "PATCH")

    beta = _beta(client)
    blocked = beta.write("", {"tender_number": "zb r19 001"}, "PATCH", expected=409)  # 写法不同也算同一编号
    assert blocked["code"] == "RELATED_BID_CONFLICT"
    assert blocked["details"]["match"] == "exact" and blocked["details"]["companies"] == [alpha_name]
    assert "第三十四条" in blocked["message"]
    assert "甲公司数据库维保项目" not in str(blocked)  # 不透露对方项目内容
    assert beta.state()["project"]["tender_number"] == ""  # 整次修改未保存

    short = beta.write("", {"tender_number": "ZB-R19-001", "related_bid_reason": "无"}, "PATCH", expected=409)
    assert short["code"] == "RELATED_BID_CONFLICT"
    saved = beta.write("", {"tender_number": "ZB-R19-001", "related_bid_reason": "我司与对方公司无控股、管理关系"}, "PATCH")
    assert saved["project"]["tender_number"] == "ZB-R19-001"

    status = client.get(f"{beta.path}/related-bids", headers=beta.headers).json()
    assert status["needs_ack"] is False and status["companies"] == [alpha_name]
    assert status["acknowledged"]["reason"] == "我司与对方公司无控股、管理关系"
    state = client.app.state.service.repository.read()
    notes = [n for n in state.service_stores.get("notifications", {}).get("items", {}).values()
             if n["type"] == "related_bid_conflict"]
    assert notes and {n["user_id"] for n in notes} == {"alpha-group-admin"}
    assert alpha_name in notes[0]["body"] and "甲公司数据库维保项目" not in notes[0]["body"]

    # 对方项目同样看到冲突，也只显示公司名称
    assert client.get(f"{alpha.path}/related-bids", headers=alpha.headers).json()["companies"] == [beta_name]


def test_ack_endpoint_needs_the_lead_and_a_conflict(client):
    alpha = ProjectFlow(client)
    no_conflict = client.post(f"{alpha.path}/related-bids/ack", json={"reason": "无关联关系说明"},
                              headers={**alpha.headers, "If-Match": str(alpha.state()["revision"]), "Idempotency-Key": str(uuid4())})
    assert no_conflict.status_code == 409
    beta = _beta(client)
    beta.write("", {"tender_number": "ZB-R19-002", "related_bid_reason": "合成测试：无关联关系"}, "PATCH")
    alpha.write("", {"tender_number": "ZB-R19-002", "related_bid_reason": "合成测试：无关联关系"}, "PATCH")

    alpha.write("", {"name": "甲公司改名"}, "PATCH")  # 已确认覆盖的冲突，改名不再拦
    editor = client.post(f"{alpha.path}/related-bids/ack", json={"reason": "编写人不能确认"},
                         headers={**login(client, "alpha-editor"), "If-Match": str(alpha.state()["revision"]),
                                  "Idempotency-Key": str(uuid4())})
    assert editor.status_code == 403
    assert client.get(f"{alpha.path}/related-bids", headers=login(client, "beta-manager")).status_code == 404


def test_check_reports_r19_until_the_lead_acknowledges(client):
    _, beta_name = _names(client)
    alpha = ProjectFlow(client).ready()  # 招标编号 SYNTH-001
    beta = _beta(client)
    beta.write("", {"tender_number": "SYNTH-001", "related_bid_reason": "乙公司确认与甲公司无关联关系"}, "PATCH")

    check = alpha.write("/checks", {"volume": "all"})["check"]
    r19 = [i for i in check["issues"] if i.get("rule_id") == "R19"]
    assert len(r19) == 1 and r19[0]["code"] == "RELATED_BID_CONFLICT" and r19[0]["severity"] == "warning"
    assert beta_name in r19[0]["message"] and "乙公司同标段投标" not in r19[0]["message"]
    assert check["passed"] is False

    acked = client.post(f"{alpha.path}/related-bids/ack", json={"reason": "甲公司确认与乙公司无控股、管理关系"},
                        headers={**alpha.headers, "If-Match": str(alpha.state()["revision"]), "Idempotency-Key": str(uuid4())})
    assert acked.status_code == 200, acked.text
    assert acked.json()["needs_ack"] is False
    stale = next(c for c in alpha.state()["checks"] if c["id"] == check["id"])
    assert stale["status"] == "stale"  # 确认后旧检查过期
    again = alpha.write("/checks", {"volume": "all"})["check"]
    assert not [i for i in again["issues"] if i.get("rule_id") == "R19"]
    assert next(r for r in again["rules"] if r["rule_id"] == "R19")["passed"] is True


def test_normalize_and_match_rules():
    assert normalize("ＺＢ－２０２６ / 001") == "zb2026001"
    exact = {"number": "zb1", "lot": "1", "tenderer": "", "name": ""}
    assert match(exact, {**exact}) == "exact"
    assert match(exact, {**exact, "lot": ""}) == "approximate"
    assert match(exact, {**exact, "lot": "2"}) is None
    assert match(exact, {**exact, "number": "zb2"}) is None
    by_name = {"number": "", "lot": "", "tenderer": "星河银行", "name": "数据库维保"}
    assert match(by_name, {**by_name}) == "approximate"
    assert match(by_name, {**by_name, "name": "运维"}) is None
    assert match({**by_name, "tenderer": ""}, by_name) is None  # 只有项目名称不算
    ids = {item["rule_id"] for item in ComplianceRulesEngine.CATALOG}
    assert "EXT-GREEN" in ids
    assert next(item for item in ComplianceRulesEngine.CATALOG if item["rule_id"] == "R19")["title"] == "关联投标冲突"
