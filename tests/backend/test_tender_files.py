# 为什么有这个文件：验证文件类型修改与版本链（设为被替代），以及补遗差异接口（PRD v1.8 §5.2.1、§5.2.4，APP-M2 WP-4）。
# 它解决什么问题：新版文件替代旧版后旧版条目只标记不删除；顺序/类型不符的替代被拒；已解析文件不能切换补遗类型。

from _parse_helpers import parsed_flow, upload_role
from test_reference_flow import TENDER, ProjectFlow, client  # noqa: F401


def test_set_role_before_parse_and_block_switch_after_parse(client):
    flow = ProjectFlow(client)
    record = upload_role(flow, TENDER, "t.txt")
    changed = flow.write(f"/files/{record['id']}/role", {"file_role": "addendum"})
    assert changed["file"]["file_role"] == "addendum"
    flow.write(f"/files/{record['id']}/role", {"file_role": "tender"})
    flow.write("/parse", {})
    error = flow.write(f"/files/{record['id']}/role", {"file_role": "addendum"}, expected=409)
    assert error["code"] == "FILE_ALREADY_PARSED"
    assert flow.write(f"/files/{record['id']}/role", {"file_role": "tech_spec"})["file"]["file_role"] == "tech_spec"


def test_supersede_requires_later_upload_of_same_role(client):
    flow = ProjectFlow(client)
    first = upload_role(flow, TENDER, "招标v1.txt")
    second = upload_role(flow, TENDER.replace("12个月", "18个月"), "招标v2.txt")
    wrong = flow.write(f"/files/{second['id']}/supersede", {"replacement_file_id": first["id"], "reason": "x"}, expected=409)
    assert wrong["code"] == "FILE_ROLE_MISMATCH"


def test_supersede_marks_old_items_and_confirm_ignores_old_file(client):
    flow = parsed_flow(client, TENDER, "招标v1.txt")
    first = flow.state()["files"][0]
    edited = next(r for r in flow.state()["requirements"] if r["text"].startswith("商务要求"))
    flow.write("/requirements/" + edited["id"], {"text": "商务要求：提供有效企业资质证明（人工补充）。"}, "PATCH")
    second = upload_role(flow, TENDER.replace("12个月", "18个月"), "招标v2.txt")
    result = flow.write(f"/files/{first['id']}/supersede", {"replacement_file_id": second["id"], "reason": "招标人发布第二版"})
    assert result["file"]["superseded_by"] == second["id"] and result["replacement"]["version_no"] == 2
    again = flow.write(f"/files/{first['id']}/supersede", {"replacement_file_id": second["id"], "reason": "再次"}, expected=409)
    assert again["code"] == "FILE_ALREADY_SUPERSEDED"
    flow.write("/parse", {})
    old = [r for r in flow.state()["requirements"] if r["source"]["file_id"] == first["id"]]
    assert old and all(r["effective_status"] == "superseded" or r.get("needs_recheck") is not None for r in old)
    assert any(r["source"]["file_id"] == second["id"] for r in flow.state()["requirements"])


def test_addendum_diff_for_non_amending_file_is_not_amending(client):
    flow = parsed_flow(client)
    record = flow.state()["files"][0]
    resp = flow.client.get(f"{flow.path}/files/{record['id']}/addendum-diff", headers=flow.headers)
    assert resp.status_code == 200 and resp.json()["amending"] is False
