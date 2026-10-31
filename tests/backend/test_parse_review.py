# 为什么有这个文件：验证解析结果的分类树、确认前提与批量确认（PRD v1.8 §5.2.2 规则 3、5、7，验收②③⑤⑥；APP-M2-T104）。
# 它解决什么问题：10 类都列出且计数与条款一致；评分项下列出得分要点；星号/废标/资格不能批量确认（后台拒绝，不只是隐藏按钮）；
# 确认前提表格驱动（冲突待处理、遗漏未处理、星号未确认各一例），与后台 confirm_parse 一致；人工改过的条目重新抽取后不变。

import pytest

from icg.domain.parse_review import requirement_category
from test_reference_flow import ProjectFlow, client, login  # noqa: F401

TENDER = ("合成招标文件：分类树验收\n招标编号：TREE-001\n投标截止时间：2026-12-31T17:00:00+08:00\n投标保证金：5万元\n"
          "第一章 投标人资格要求\n1. 具有独立承担民事责任的能力，提供营业执照。\n"
          "第二章 评分办法\n一、技术方案（20分）\n1. 架构设计合理的得10分。\n2. 运维方案完整的得10分。\n"
          "第三章 技术要求\n★1. 提供7×24小时驻场服务。\n2. 每月完成巡检并提交报告。\n3. 一级故障响应时间不超过30分钟。\n"
          "4. 投标文件未按要求盖章的，视为无效投标。\n")


def _review(flow):
    resp = flow.client.get(f"{flow.path}/parse/review", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _parsed(client):
    flow = ProjectFlow(client)
    flow.upload(TENDER.encode())
    flow.write("/parse", {})
    return flow


@pytest.mark.parametrize("text,kind,category,expected", [
    ("★提供7×24小时驻场服务。", "technical", "mandatory", "star"),
    ("未按要求盖章的，视为无效投标。", "technical", "mandatory", "disqualification"),
    ("具有独立承担民事责任的能力。", "qualification", "business", "qualification"),
    ("架构设计合理的得10分。", "scoring", "scoring", "scoring"),
    ("一级故障响应时间不超过30分钟。", "technical", "technical", "sla"),
    ("投标文件正本一份、副本四份，分开密封。", "notice", "business", "format"),
    ("中标后十日内退还投标保证金。", "notice", "business", "deposit"),
    ("每月完成巡检并提交报告。", "technical", "technical", "technical"),
])
def test_requirement_categories(text, kind, category, expected):
    assert requirement_category({"text": text, "section_kind": kind, "category": category}) == expected


def test_tree_lists_ten_categories_with_counts_and_scoring_points(client):
    flow = _parsed(client)
    data = _review(flow)
    cats = {c["key"]: c for c in data["categories"]}
    assert [c["no"] for c in data["categories"]] == list(range(1, 11))
    rows = [r for r in flow.state()["requirements"] if not r.get("out_of_scope")]
    assert sum(c["requirements"] for c in data["categories"]) == len(rows)
    assert set(data["requirement_categories"]) == {r["id"] for r in rows}
    assert cats["star"]["requirements"] >= 1 and cats["star"]["batch_allowed"] is False
    assert cats["disqualification"]["batch_allowed"] is False and cats["qualification"]["batch_allowed"] is False
    assert cats["timeline"]["facts"] >= 1 and cats["deposit"]["facts"] >= 1 and cats["basic"]["facts"] >= 1
    assert all(c["pending"] == c["total"] for c in data["categories"])  # 刚解析，全部待确认
    groups = cats["scoring"]["groups"]
    assert groups and sum(len(g["ids"]) for g in groups) == cats["scoring"]["requirements"]


def test_star_disqualification_and_qualification_cannot_be_batch_confirmed(client):
    flow = _parsed(client)
    data = _review(flow)
    by = data["requirement_categories"]
    star = next(i for i, k in by.items() if k == "star")
    others = [i for i, k in by.items() if k in ("technical", "sla", "scoring")]
    error = flow.write("/requirements/batch-confirm", {"requirement_ids": [star, *others]}, expected=409)
    assert error["code"] == "REQUIREMENT_NOT_READY" and star in error["details"]["requirement_ids"]
    assert all(r["status"] == "pending" for r in flow.state()["requirements"] if r["id"] in others)  # 整批不生效
    ok = flow.write("/requirements/batch-confirm", {"requirement_ids": others})
    assert sorted(ok["confirmed_ids"]) == sorted(others)
    assert all(r["status"] == "confirmed" and r["confirmed_by"] == "alpha-manager"
               for r in flow.state()["requirements"] if r["id"] in others)
    headers = {**login(client, "alpha-editor"), "If-Match": str(flow.state()["revision"]), "Idempotency-Key": "batch-editor"}
    denied = client.post(f"{flow.path}/requirements/batch-confirm", headers=headers, json={"requirement_ids": others})
    assert denied.status_code == 403


@pytest.mark.parametrize("gate", ["CONFLICTS_PENDING", "OMISSIONS_PENDING", "STAR_PENDING", "PARSE_INCOMPLETE"])
def test_confirm_gates_are_listed_and_enforced(client, gate):
    flow = _parsed(client)
    repo = client.app.state.service.repository
    # 先把所有条目和事实处理掉，再只留下被测的这一个前提
    for row in flow.state()["requirements"]:
        flow.write("/requirements/" + row["id"], {"status": "confirmed", "reason": "已人工核对引用"}, "PATCH")
    for fact in flow.state()["facts"]:
        flow.write("/facts/" + fact["id"], {"status": "confirmed"}, "PATCH")
    repo.transaction(lambda st: st.workflows[flow.id].get("post_process", {}).get("hits", {}).clear())
    data = _review(flow)
    assert data["can_confirm"] is True, [g for g in data["gates"] if not g["ok"]]
    if gate == "CONFLICTS_PENDING":
        fact_id = flow.state()["facts"][0]["id"]
        repo.transaction(lambda st: st.workflows[flow.id]["conflicts"].__setitem__("c-1", {
            "id": "c-1", "key": "招标编号", "fact_ids": [fact_id], "selected_fact_id": None, "status": "pending", "reason": ""}))
        code = "CONFLICTS_PENDING"
    elif gate == "OMISSIONS_PENDING":
        repo.transaction(lambda st: st.workflows[flow.id].setdefault("post_process", {}).setdefault("hits", {}).__setitem__("h-1", {
            "id": "h-1", "file_id": "x", "page": 1, "quote": "未抽取的否决条款", "terms": ["否决"], "status": "open", "reason": ""}))
        code = "OMISSIONS_PENDING"
    elif gate == "PARSE_INCOMPLETE":
        file_id = next(iter(repo.read().workflows[flow.id]["files"]))
        repo.transaction(lambda st: st.workflows[flow.id]["files"][file_id].update(status="failed"))
        code = "PARSE_INCOMPLETE"
    else:
        star = next(i for i, k in data["requirement_categories"].items() if k == "star")
        repo.transaction(lambda st: st.workflows[flow.id]["requirements"][star].update(status="pending"))
        code = "REVIEW_PENDING"
    after = _review(flow)
    failing = [g["code"] for g in after["gates"] if not g["ok"] and g["blocking"]]
    assert failing == [gate] and after["can_confirm"] is False
    assert next(g for g in after["gates"] if g["code"] == gate)["count"] == 1
    error = flow.write("/parse/confirm", {}, expected=409)
    assert error["code"] == code


def test_manually_edited_requirement_survives_reparse(client):
    flow = _parsed(client)
    row = next(r for r in flow.state()["requirements"] if "巡检" in r["text"])
    edited = flow.write("/requirements/" + row["id"], {"text": "每月完成一次全面巡检并提交书面报告（人工修订）。"}, "PATCH")["requirement"]
    assert edited["manually_edited"] is True
    flow.write("/parse", {})
    rows = [r for r in flow.state()["requirements"] if r["source"]["quote"] == row["source"]["quote"]]
    assert len(rows) == 1 and rows[0]["text"].endswith("（人工修订）。") and rows[0]["manually_edited"] is True
