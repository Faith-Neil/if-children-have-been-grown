# 为什么有这个文件：验证冲突四种状态、补遗覆盖、重新解析保留决定、新取值另记冲突（PRD v1.8 §5.2.4，APP-M2 WP-4）。
# 它解决什么问题：冲突必须逐条写理由处理；重新解析不能让已做的决定失效；已按补遗处理的不阻断确认。

from _parse_helpers import fact_values, parsed_flow, settle_pending, upload_role
from test_reference_flow import TENDER, ProjectFlow, client  # noqa: F401

DUAL = TENDER + "\n服务期限：24个月\n服务期限：1年"


def _conflicts(flow):
    resp = flow.client.get(f"{flow.path}/parse/conflicts", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _decide(flow, conflict_id, body, expected=200):
    return flow.write(f"/parse/conflicts/{conflict_id}/decision", body, expected=expected)


def test_field_conflict_lists_values_and_same_value_is_merged(client):
    flow = parsed_flow(client, DUAL)
    data = _conflicts(flow)
    assert data["summary"]["pending"] == 1 and data["can_handle"] is True
    conflict = data["conflicts"][0]
    assert conflict["key"] == "服务期限" and conflict["blocking"] and conflict["status"] == "pending"
    assert len(conflict["fact_ids"]) == 2  # 12个月与1年同值，合并后只剩两种取值
    merged = [f for f in flow.state()["facts"] if f.get("merged_into")]
    assert len(merged) == 1 and merged[0]["value"] == "1年"


def test_choose_requires_reason_and_confirms_selected_value(client):
    flow = parsed_flow(client, DUAL)
    conflict = _conflicts(flow)["conflicts"][0]
    chosen = next(f["id"] for f in flow.state()["facts"] if f["value"] == "24个月")
    assert _decide(flow, conflict["id"], {"action": "choose", "selected_fact_id": chosen}, 422)["code"] == "REASON_REQUIRED"
    _decide(flow, conflict["id"], {"action": "choose", "selected_fact_id": chosen, "reason": "以合成合同条款为准"})
    assert dict(fact_values(flow, "服务期限")) == {"12个月": "rejected", "24个月": "confirmed", "1年": "rejected"}
    assert _conflicts(flow)["summary"]["resolved"] == 1


def test_confirm_blocked_until_conflict_decided_and_rerun_keeps_decision(client):
    flow = parsed_flow(client, DUAL)
    settle_pending(flow)
    assert flow.write("/parse/confirm", {}, expected=409)["code"] == "CONFLICTS_PENDING"
    conflict = _conflicts(flow)["conflicts"][0]
    chosen = next(f["id"] for f in flow.state()["facts"] if f["value"] == "24个月")
    _decide(flow, conflict["id"], {"action": "choose", "selected_fact_id": chosen, "reason": "以合成合同条款为准"})
    flow.write("/parse", {})
    after = _conflicts(flow)
    assert after["summary"]["pending"] == 0 and after["summary"]["resolved"] == 1
    assert after["conflicts"][0]["id"] == conflict["id"]


def test_new_value_after_decision_creates_new_conflict(client):
    flow = parsed_flow(client, DUAL)
    conflict = _conflicts(flow)["conflicts"][0]
    chosen = next(f["id"] for f in flow.state()["facts"] if f["value"] == "24个月")
    _decide(flow, conflict["id"], {"action": "choose", "selected_fact_id": chosen, "reason": "以合成合同条款为准"})
    upload_role(flow, "服务期限：36个月\n", "附件.txt", "attachment")
    flow.write("/parse", {})
    data = _conflicts(flow)
    assert data["summary"]["pending"] == 1 and data["summary"]["history"] == 1
    stale = next(c for c in data["conflicts"] if not c["current"])
    assert stale["id"] == conflict["id"]
    assert _decide(flow, stale["id"], {"action": "not_conflict", "reason": "x"}, 409)["code"] == "VERSION_CONFLICT"


def test_manual_fact_edit_survives_rerun_without_new_conflict(client):
    flow = parsed_flow(client)
    fact = next(f for f in flow.state()["facts"] if f["key"] == "服务期限")
    flow.write("/facts/" + fact["id"], {"value": "十二个月（人工核对）"}, "PATCH")
    flow.write("/parse", {})
    values = [f for f in flow.state()["facts"] if f["key"] == "服务期限"]
    assert [f["value"] for f in values] == ["十二个月（人工核对）"] and values[0]["manually_edited"] is True
    assert _conflicts(flow)["conflicts"] == []


def test_not_conflict_needs_reason_and_unblocks(client):
    flow = parsed_flow(client, DUAL)
    conflict = _conflicts(flow)["conflicts"][0]
    assert _decide(flow, conflict["id"], {"action": "not_conflict"}, 422)["code"] == "REASON_REQUIRED"
    _decide(flow, conflict["id"], {"action": "not_conflict", "reason": "两处分属不同合同阶段"})
    summary = _conflicts(flow)["summary"]
    assert summary["pending"] == 0 and summary["not_conflict"] == 1


def test_unlocated_addendum_assign_target_supersedes_original(client):
    flow = parsed_flow(client)
    addendum = upload_role(flow, "删除第9.9条。\n", "补遗.txt", "addendum")
    flow.write("/parse", {})
    data = _conflicts(flow)
    unlocated = next(c for c in data["conflicts"] if c["conflict_type"] == "addendum_unlocated")
    assert unlocated["blocking"] and unlocated["candidates"]
    target = next(r for r in flow.state()["requirements"] if r["text"].startswith("商务要求"))
    _decide(flow, unlocated["id"], {"action": "assign_target", "requirement_id": target["id"], "reason": "补遗删除的是资质条款"})
    row = next(r for r in flow.state()["requirements"] if r["id"] == target["id"])
    assert row["status"] == "rejected" and row["effective_status"] == "superseded"
    blocked = flow.write("/requirements/" + target["id"], {"status": "confirmed"}, "PATCH", 409)
    assert blocked["code"] == "REQUIREMENT_SUPERSEDED"
    diff = flow.client.get(f"{flow.path}/files/{addendum['id']}/addendum-diff", headers=flow.headers)
    assert diff.status_code == 200 and diff.json()["amending"] is True
