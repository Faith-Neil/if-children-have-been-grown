# 为什么有这个文件：验证抽取后处理汇总、去重合并/拆分与合并建议（PRD v1.8 §5.2.4，APP-M2 WP-4）。
# 它解决什么问题：重复条款只列一条并保留全部来源；数字不同的不能合并；拆开后不再自动合并；建议必须写理由处理。

from _parse_helpers import parsed_flow
from test_reference_flow import client  # noqa: F401

DUPLICATE = "★技术要求：每月完成巡检并提交报告。\n其他说明：无。\f★技术要求：每月完成巡检并提交报告。"


def _summary(flow):
    resp = flow.client.get(f"{flow.path}/parse/post-process", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _star(flow):
    return [r for r in flow.state()["requirements"] if r["text"].startswith("★") and not r.get("merged_into")]


def test_summary_counts_merged_duplicates(client):
    flow = parsed_flow(client, DUPLICATE)
    data = _summary(flow)
    assert data["merged_groups"] == 1 and data["merged_items"] == 1
    assert data["conflicts_pending"] == 0 and data["omissions_pending"] >= 0
    primary = _star(flow)
    assert len(primary) == 1 and sorted(s["page"] for s in primary[0]["sources"]) == [1, 2]


def test_split_then_merge_back(client):
    flow = parsed_flow(client, DUPLICATE)
    primary = _star(flow)[0]
    flow.write(f"/requirements/{primary['id']}/split", {"reason": "两页分属不同章节"})
    stars = [r for r in flow.state()["requirements"] if r["text"].startswith("★")]
    assert len(stars) == 2 and not any(r.get("merged_into") for r in stars)
    flow.write("/parse", {})  # 拆开的不再自动合并
    assert len([r for r in flow.state()["requirements"] if r["text"].startswith("★") and not r.get("merged_into")]) == 2
    first, second = stars
    merged = flow.write(f"/requirements/{first['id']}/merge", {"requirement_ids": [second["id"]], "reason": "确认重复"})
    assert merged["merged_ids"] == [second["id"]]
    again = flow.write(f"/requirements/{second['id']}/merge", {"requirement_ids": [first['id']], "reason": "x"}, expected=409)
    assert again["code"] == "REQUIREMENT_NOT_READY"


def test_split_unmerged_item_is_rejected(client):
    flow = parsed_flow(client, DUPLICATE)
    other = next(r for r in flow.state()["requirements"] if not r["text"].startswith("★"))
    assert flow.write(f"/requirements/{other['id']}/split", {}, expected=409)["code"] == "NOT_MERGED"


def test_merge_with_different_numbers_is_rejected(client):
    flow = parsed_flow(client, "技术要求：响应时间不超过30分钟。\f技术要求：响应时间不超过60分钟。")
    first, second = [r for r in flow.state()["requirements"] if r["text"].startswith("技术要求")][:2]
    error = flow.write(f"/requirements/{first['id']}/merge", {"requirement_ids": [second["id"]], "reason": "x"}, expected=409)
    assert error["code"] == "REQUIREMENT_VALUES_DIFFER"


def test_merged_member_cannot_be_edited_until_split(client):
    flow = parsed_flow(client, DUPLICATE)
    primary = _star(flow)[0]
    member_id = next(r["id"] for r in flow.state()["requirements"] if r.get("merged_into") == primary["id"])
    error = flow.write("/requirements/" + member_id, {"status": "confirmed"}, "PATCH", 409)
    assert error["code"] == "REQUIREMENT_MERGED"
