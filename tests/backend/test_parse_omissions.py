# 为什么有这个文件：验证 APP-M2-T111 星号/废标兜底扫描与疑似遗漏逐条处理（PRD v1.8 §5.2.4 验收 ④⑤⑥）。
# 它解决什么问题：
# 1. 带“★”或“否决投标”等词、但未被星号/废标条目覆盖的原文列为疑似遗漏；
# 2. 只能逐条新增为条目或写理由排除，排除不填理由不能保存，只有项目负责人能处理；
# 3. 疑似遗漏未处理完不能确认解析结果；重新解析不覆盖已处理结果。

from uuid import uuid4

from test_reference_flow import ProjectFlow, client, login  # noqa: F401

TENDER = ("合成招标文件：兜底扫描\n招标编号：SYNTH-002\n投标截止时间：2026-12-31T17:00:00+08:00\n"
          "★技术要求：每月完成巡检并提交报告。\n"
          "逾期送达的投标文件不予受理。\n"
          "商务要求：提供有效企业资质证明。")


def _headers(flow, account="alpha-manager"):
    return {**login(flow.client, account), "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())}


def _reviewed(client):
    flow = ProjectFlow(client).reviewed(TENDER)
    return flow


def test_uncovered_disqualification_line_is_suspected_and_blocks_confirm(client):
    flow = _reviewed(client)
    listing = client.get(flow.path + "/parse/omissions", headers=flow.headers).json()
    states = {h["quote"]: h["state"] for h in listing["hits"]}
    assert states["★技术要求：每月完成巡检并提交报告。"] == "covered"
    assert states["逾期送达的投标文件不予受理。"] == "suspected"
    assert listing["summary"]["suspected"] == 1 and listing["scan_version"].startswith("platform-")
    assert listing["can_handle"] is True

    blocked = client.post(flow.path + "/parse/confirm", json={}, headers=_headers(flow))
    assert blocked.status_code == 409 and blocked.json()["code"] == "OMISSIONS_PENDING"


def test_exclude_requires_reason_and_lead(client):
    flow = _reviewed(client)
    hit = next(h for h in client.get(flow.path + "/parse/omissions", headers=flow.headers).json()["hits"]
               if h["state"] == "suspected")
    by_writer = client.post(f"{flow.path}/parse/omissions/{hit['id']}/exclude", json={"reason": "不适用"},
                            headers=_headers(flow, "alpha-editor"))
    assert by_writer.status_code == 403
    empty = client.post(f"{flow.path}/parse/omissions/{hit['id']}/exclude", json={"reason": ""}, headers=_headers(flow))
    assert empty.status_code == 422
    done = client.post(f"{flow.path}/parse/omissions/{hit['id']}/exclude", json={"reason": "已在商务条款中统一响应"},
                       headers=_headers(flow))
    assert done.status_code == 200 and done.json()["hit"]["state"] == "excluded"
    twice = client.post(f"{flow.path}/parse/omissions/{hit['id']}/exclude", json={"reason": "再次"}, headers=_headers(flow))
    assert twice.status_code == 409
    confirmed = client.post(flow.path + "/parse/confirm", json={}, headers=_headers(flow))
    assert confirmed.status_code == 200, confirmed.text
    audit = client.app.state.service.repository.read().audit
    assert any(e["action"].startswith("parse.omission.exclude") and e["details"]["reason"] for e in audit)


def test_add_as_requirement_upgrades_line_and_needs_reconfirm(client):
    flow = _reviewed(client)
    hit = next(h for h in client.get(flow.path + "/parse/omissions", headers=flow.headers).json()["hits"]
               if h["state"] == "suspected")
    added = client.post(f"{flow.path}/parse/omissions/{hit['id']}/add",
                        json={"category": "disqualification", "volume": "business"}, headers=_headers(flow))
    assert added.status_code == 200, added.text
    requirement = added.json()["requirement"]
    assert requirement["category"] == "disqualification" and requirement["status"] == "pending"
    rows = [r for r in flow.state()["requirements"] if r["text"] == hit["quote"]]
    assert len(rows) == 1  # 同一原文升级，不重复建条目
    blocked = client.post(flow.path + "/parse/confirm", json={}, headers=_headers(flow))
    assert blocked.status_code == 409 and blocked.json()["code"] == "REVIEW_PENDING"
    flow.write("/requirements/" + requirement["id"], {"status": "confirmed"}, "PATCH")
    assert client.post(flow.path + "/parse/confirm", json={}, headers=_headers(flow)).status_code == 200


def test_ignoring_a_star_requirement_reopens_the_hit_and_reparse_keeps_handled(client):
    flow = _reviewed(client)
    star = next(r for r in flow.state()["requirements"] if r["text"].startswith("★"))
    flow.write("/requirements/" + star["id"], {"status": "rejected", "reason": "合成测试忽略"}, "PATCH")
    listing = client.get(flow.path + "/parse/omissions", headers=flow.headers).json()
    assert {h["quote"] for h in listing["hits"] if h["state"] == "suspected"} >= {star["text"]}

    target = next(h for h in listing["hits"] if h["quote"] == star["text"])
    client.post(f"{flow.path}/parse/omissions/{target['id']}/exclude", json={"reason": "与第2条重复"}, headers=_headers(flow))
    flow.write("/parse", {})
    again = {h["quote"]: h for h in client.get(flow.path + "/parse/omissions", headers=flow.headers).json()["hits"]}
    assert again[star["text"]]["state"] == "excluded" and again[star["text"]]["reason"] == "与第2条重复"
    assert len(again) == 2
