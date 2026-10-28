# 为什么有这个文件：验证导出递交版时同时生成合标核对清单（APP-M2-T200，PRD v1.8 §5.9.2 验收①～④）。
# 它解决什么问题：清单 9 类核对项齐全，一致性结论引用本批次全文检查，未实现的 R36/R41 写明“未运行”，
# Excel 可直接打开核对；只有负责人与公司管理员能下载；分册解锁后清单标“已过期”仍可下载。

from uuid import uuid4

from icg.infra.xlsx import build_xlsx, read_xlsx_rows
from test_reference_flow import ProjectFlow, client, login  # noqa: F401


def _headers(flow, account="alpha-manager"):
    return {**login(flow.client, account), "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())}


def _submission(client):
    flow = ProjectFlow(client).ready()
    check = flow.write("/checks", {"volume": "all"})["check"]
    assert check["passed"], check["issues"]
    for volume in ("technical", "business"):
        flow.cross_reviewed(volume)
        resp = client.post(f"{flow.path}/volumes/{volume}/finalize", json={"check_id": check["id"]}, headers=_headers(flow))
        assert resp.status_code == 200, resp.text
    resp = client.post(f"{flow.path}/exports", json={"check_id": check["id"], "kind": "submission", "volume": "all"},
                       headers=_headers(flow))
    assert resp.status_code == 200, resp.text
    return flow, check, resp.json()["export"]


def test_xlsx_writer_round_trips_text_and_numbers():
    data = build_xlsx([{"name": "表", "rows": [["序号", "内容"], [1, "含<特殊>&字符\n第二行"]], "header_rows": 1}])
    assert data[:2] == b"PK"
    assert read_xlsx_rows(data) == [["序号", "内容"], ["1", "含<特殊>&字符\n第二行"]]


def test_submission_export_always_generates_checklist_with_nine_items(client):
    flow, check, export = _submission(client)
    assert export["merge_checklist_url"].endswith(f"/exports/{export['id']}/merge-checklist.xlsx")
    body = client.get(f"{flow.path}/exports/{export['id']}/merge-checklist", headers=flow.headers)
    assert body.status_code == 200, body.text
    checklist, stale = body.json()["checklist"], body.json()["stale"]
    assert stale is False and checklist["check_id"] == check["id"]
    assert [s["item"] for s in checklist["sections"]] == [
        "分册与文件", "页码与目录", "评审索引表", "两本之间的一致性结论", "偏离表与点对点应答",
        "密封、份数、装订", "签章", "暗标", "文件命名"]
    files = " ".join(r["text"] for r in checklist["sections"][0]["rows"])
    assert all(v["filename"] in files for v in export["volumes"]) and "估算" in files
    consistency = [r["text"] for r in checklist["sections"][3]["rows"]]
    assert any(t.startswith("R36") and "未运行" in t for t in consistency)  # 系统尚未实现 R36，不冒充已检查
    r10 = next(r for r in check["rules"] if r["rule_id"] == "R10")
    assert any(t.startswith("R10") and ("通过" if r10["passed"] else "未通过") in t for t in consistency)
    assert any(check["id"] in t for t in consistency)
    assert any("R41" in r["text"] and "未运行" in r["text"] for r in checklist["sections"][6]["rows"])


def test_checklist_excel_opens_with_header_and_rows(client):
    flow, _, export = _submission(client)
    resp = client.get(export["merge_checklist_url"], headers=flow.headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    rows = read_xlsx_rows(resp.content)
    assert rows[0][0].startswith("合标核对清单")
    assert rows[4] == ["序号", "核对项", "清单内容（系统生成）", "原文位置", "合标时由人做什么", "核对结果（人工填写）"]
    assert {r[1] for r in rows[5:] if len(r) > 1 and r[1]} >= {"分册与文件", "两本之间的一致性结论", "文件命名"}
    assert "已过期" not in rows[1][0]


def test_checklist_permissions_and_internal_exports_have_none(client):
    flow, check, export = _submission(client)
    viewer = client.get(f"{flow.path}/exports/{export['id']}/merge-checklist", headers=login(client, "alpha-viewer"))
    assert viewer.status_code in (403, 404)
    writer = client.get(f"{flow.path}/exports/{export['id']}/merge-checklist", headers=login(client, "alpha-editor"))
    assert writer.status_code == 403  # 编写人不是分册负责人，不能下载
    beta = client.get(f"{flow.path}/exports/{export['id']}/merge-checklist", headers=login(client, "beta-manager"))
    assert beta.status_code == 404


def test_internal_export_has_no_checklist(client):
    flow = ProjectFlow(client).ready()
    check = flow.write("/checks", {"volume": "all"})["check"]
    export = flow.write("/exports", {"check_id": check["id"], "kind": "internal"})["export"]
    assert "merge_checklist_url" not in export
    assert client.get(f"{flow.path}/exports/{export['id']}/merge-checklist", headers=flow.headers).status_code == 404


def test_checklist_marked_stale_after_volume_unlock_but_still_downloadable(client):
    flow, _, export = _submission(client)
    resp = client.post(f"{flow.path}/volumes/technical/unlock", json={"reason": "补充人员证书"}, headers=_headers(flow))
    assert resp.status_code == 200, resp.text
    body = client.get(f"{flow.path}/exports/{export['id']}/merge-checklist", headers=flow.headers).json()
    assert body["stale"] is True
    rows = read_xlsx_rows(client.get(export["merge_checklist_url"], headers=flow.headers).content)
    assert "已过期" in rows[1][0]


def test_tender_requirements_are_listed_with_page_references():
    from types import SimpleNamespace
    from icg.domain.merge_checklist import build_merge_checklist

    workflow = {"files": {"f1": {"filename": "招标文件.pdf", "pages": [
        "第二章 投标人须知\n投标文件正本1份、副本4份，正副本分开密封。\n投标文件须胶装成册。",
        "投标函须法定代表人签字并加盖公章。\n电子文件命名为“项目编号+投标人名称”。\n本项目技术部分采用暗标评审。",
        "报价文件单独密封递交。",
    ]}}, "requirements": {}, "chapter_order": []}
    project = SimpleNamespace(id="p", name="合成项目")
    state = SimpleNamespace(chapters={})
    record = {"id": "e1", "volumes": [{"volume": "technical", "filename": "t.docx"}], "documents": {"technical": {"content": "正文"}}}
    checklist = build_merge_checklist(state, project, workflow, record, {"id": "c1", "rules": [], "issues": []}, now_iso="now")
    by_item = {s["item"]: s["rows"] for s in checklist["sections"]}
    assert any("副本4份" in r["text"] and r["source"] == "招标文件.pdf 第 1 页" for r in by_item["密封、份数、装订"])
    assert any("加盖公章" in r["text"] and r["source"].endswith("第 2 页") for r in by_item["签章"])
    assert any("暗标" in r["text"] for r in by_item["暗标"]) and any("R42" in r["text"] for r in by_item["暗标"])
    assert any("需人工插入或另行递交" in r["text"] for r in by_item["分册与文件"])
    # 只有一个分册在系统内编制：R36 未运行
    assert by_item["两本之间的一致性结论"][0]["text"].startswith("只有一个分册在系统内编制")
