# 为什么有这个文件：核对服务承诺“需复核”传播提示与判定汇总（APP-M2-T122 / APP-M2-T119）。
# 它解决什么问题：模板、取值或来源变化后，页面读到的原因、受影响章节和过期承诺函必须与后台判定同源，
# 且只读派生、不放行任何门禁；跨公司不能读取。

from test_sla import SlaFlow, client, login  # noqa: F401


def _propagation(flow):
    result = flow.client.get(flow.path + "/sla/propagation", headers=flow.headers)
    assert result.status_code == 200, result.text
    return result.json()


def _put_content(flow, content):
    chapter_id = flow.state()["chapters"][0]["id"]

    def write(state):
        state.chapters[chapter_id].content = content

    flow.client.app.state.service.repository.transaction(write)
    return chapter_id


def test_propagation_without_template_is_empty_not_error(client):
    body = _propagation(SlaFlow(client))
    assert body["selected"] is False and body["rows"] == [] and body["chapters"] == []
    assert body["summary"]["total"] == 0 and body["summary"]["by_judgment"] == {}


def test_unconfirmed_then_changed_then_confirmed_reasons_follow_the_fact_status(client):
    flow = SlaFlow(client)
    flow.template()
    body = _propagation(flow)
    assert body["selected"] is True and body["summary"]["total"] == 1 and body["summary"]["unconfirmed"] == 1
    assert "UNCONFIRMED" in [r["code"] for r in body["rows"][0]["reasons"]]
    flow.bind()  # 登记招标要求与取值会使事实回到“需重新核对”
    body = _propagation(flow)
    row = body["rows"][0]
    assert body["summary"]["by_judgment"]["satisfied"] == 1 and body["summary"]["needs_review"] == 1
    assert [r["code"] for r in row["reasons"]] == ["NEEDS_REVIEW"] and row["needs_review"] is True
    flow.confirm()
    row = _propagation(flow)["rows"][0]
    assert row["reasons"] == [] and row["fact_status"] == "confirmed" and row["needs_review"] is False


def test_changed_value_marks_needs_review_and_lists_chapters_using_the_variable(client):
    flow = SlaFlow(client)
    flow.template()
    flow.bind()
    flow.confirm()
    chapter_id = _put_content(flow, "服务承诺：一级故障响应时限为{{sla:P1.response}}分钟。")
    flow.write("/sla/values/P1.response", {"project_value": "20", "reason": "负责人改承诺值。"}, "PATCH")
    body = _propagation(flow)
    row = body["rows"][0]
    assert row["needs_review"] is True and [r["code"] for r in row["reasons"]] == ["NEEDS_REVIEW"]
    assert [c["chapter_id"] for c in row["chapters"]] == [chapter_id]
    assert body["summary"]["needs_review"] == 1 and body["summary"]["affected_chapters"] == 1
    affected = body["chapters"][0]
    assert affected["chapter_id"] == chapter_id and affected["var_keys"] == ["P1.response"]
    assert any(i["code"] == "SLA_VARIABLE_UNCONFIRMED" for i in affected["issues"])


def test_template_change_marks_template_stale(client):
    flow = SlaFlow(client)
    item = flow.template()
    flow.bind()
    flow.confirm()
    flow.patch_template(item["id"], {"body_text": "一级故障响应时限不超过{{P1.response}}分钟。", "status": "confirmed",
                                     "reason": "合成测试：修改正文后重新核对。"})
    body = _propagation(flow)
    assert body["template_stale"] is True
    row = body["rows"][0]
    assert row["needs_review"] is True and "TEMPLATE_STALE" in [r["code"] for r in row["reasons"]]


def test_stale_commitment_is_counted_after_the_value_changes(client):
    flow = SlaFlow(client)
    flow.template()
    flow.bind()
    flow.confirm()
    flow.commitment()
    assert _propagation(flow)["summary"]["stale_commitments"] == 0
    flow.write("/sla/values/P1.response", {"project_value": "25", "reason": "负责人改承诺值。"}, "PATCH")
    assert _propagation(flow)["summary"]["stale_commitments"] == 1


def test_hand_written_number_that_disagrees_is_reported_per_chapter(client):
    flow = SlaFlow(client)
    flow.template()
    flow.bind()
    flow.confirm()
    chapter_id = _put_content(flow, "一级故障响应时限为45分钟。")
    body = _propagation(flow)
    affected = next(c for c in body["chapters"] if c["chapter_id"] == chapter_id)
    assert any(i["code"] == "SLA_TEXT_MISMATCH" for i in affected["issues"])


def test_other_company_cannot_read_propagation(client):
    flow = SlaFlow(client)
    flow.template()
    denied = client.get(flow.path + "/sla/propagation", headers=login(client, "beta-manager"))
    assert denied.status_code == 404
