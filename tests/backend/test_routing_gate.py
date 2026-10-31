# 为什么有这个文件：验证“未确认分流的矩阵行不出现在任何分册的写作方案候选中”与“跨分册共用行在两个分册都能选到”
# （PRD v1.8 §5.3.1 规则 8、验收④⑤）。
# 它解决什么问题：分流确认原先只是矩阵上的一个标记，写作方案和生成照样使用未确认的行；跨分册共用行只能出现在一个分册。

from test_reference_flow import ProjectFlow, client, login  # noqa: F401


def _writing_input(flow, chapter_id):
    resp = flow.client.get(f"{flow.path}/chapters/{chapter_id}/writing-input", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _issues(preview):
    return preview.get("issues") or preview.get("input_snapshot", {}).get("issues") or []


def test_unconfirmed_routing_keeps_a_row_out_of_the_writing_plan(client):
    flow = ProjectFlow(client).ready()
    row = next(r for r in flow.state()["requirements"] if r["volume"] == "technical")
    chapter_id = row["chapter_id"]
    before = _writing_input(flow, chapter_id)
    assert any(r["id"] == row["id"] for r in before["input_snapshot"]["requirements"])
    # 退回待确认（模拟分册负责人改分册建议后的状态）
    client.app.state.service.repository.transaction(
        lambda st: st.workflows[flow.id]["requirements"][row["id"]].update(volume_confirmed_at=None, volume_confirmed_by=None))
    after = _writing_input(flow, chapter_id)
    assert not any(r["id"] == row["id"] for r in after["input_snapshot"]["requirements"])
    blocked = [i for i in _issues(after) if i.get("requirement_id") == row["id"]]
    assert blocked and blocked[0]["code"] == "REQUIREMENT_NOT_READY" and "分流" in blocked[0]["message"]
    # 负责人确认分流后恢复
    flow.write("/matrix/routing", {"rows": [{"id": row["id"], "volume": "technical"}]})
    assert any(r["id"] == row["id"] for r in _writing_input(flow, chapter_id)["input_snapshot"]["requirements"])


def test_only_the_project_lead_routes_rows(client):
    flow = ProjectFlow(client).ready()
    row = next(r for r in flow.state()["requirements"] if r["volume"] == "business")
    headers = {**login(client, "alpha-editor"), "If-Match": str(flow.state()["revision"]), "Idempotency-Key": "routing-editor-1"}
    resp = client.patch(f"{flow.path}/requirements/{row['id']}", headers=headers, json={"volume": "technical", "chapter_id": None})
    assert resp.status_code == 403 and resp.json()["code"] == "PROJECT_LEAD_REQUIRED"
    assert next(r for r in flow.state()["requirements"] if r["id"] == row["id"])["volume_confirmed_at"]


def test_cross_volume_row_can_be_planned_in_both_volumes(client):
    flow = ProjectFlow(client).ready()
    state = flow.state()
    row = next(r for r in state["requirements"] if r["volume"] == "technical")
    business = next(c for c in state["chapters"] if c["volume"] == "business")
    flow.write("/matrix/routing", {"rows": [{"id": row["id"], "volume": "technical", "is_cross_volume": True}]})
    flow.write("/requirements/" + row["id"], {"shared_chapter_id": business["id"]}, "PATCH")
    shared = _writing_input(flow, business["id"])["input_snapshot"]["requirements"]
    assert any(r["id"] == row["id"] for r in shared)
    assert any(r["id"] == row["id"] for r in _writing_input(flow, row["chapter_id"])["input_snapshot"]["requirements"])
    chapter = next(c for c in flow.state()["chapters"] if c["id"] == business["id"])
    assert row["id"] in chapter["requirement_ids"]
    # 不是跨分册共用的行不能再对应另一分册
    other = next(r for r in state["requirements"] if r["volume"] == "business")
    technical = next(c for c in state["chapters"] if c["volume"] == "technical")
    error = flow.write("/requirements/" + other["id"], {"shared_chapter_id": technical["id"]}, "PATCH", expected=409)
    assert error["code"] == "CHAPTER_VOLUME_MISMATCH"
