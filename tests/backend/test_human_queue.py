# 为什么有这个文件：验证 PRD v1.8 §5.7.4～5.7.7 章节循环规则与人工处理队列（APP-M2-T133 / BE-HUMAN-QUEUE）。
# 它解决什么问题：
# 1. 直接转人工的七类问题从不出现在自动修正里，未点名段落逐字不变；
# 2. 停止条件按顺序判定，回退时保留修正前版本；
# 3. 队列只对本项目成员可见，处理/驳回权限按 PRD，阻断级不能驳回，处理完自动“人工已处理”；
# 4. 重新检查开始新一次循环，同指纹问题沿用编号并重新打开，修正生成新章节版本并留痕。

from uuid import uuid4

import pytest

from icg.domain import chapter_loop
from icg.domain.chapter_loop import LoopContext, run_chapter_loop
from test_reference_flow import ProjectFlow, client, login  # noqa: F401


# ---------------------------------------------------------------- 纯规则层

def test_direct_human_categories_are_never_auto_fixed():
    content = "\n".join([
        "本节总体说明，语句完整。",
        "我司无法提供7x24小时驻场服务。",
        "拟派项目经理为【待补：项目经理姓名】。",
        "本项目报价为【待补：报价金额】。",
        "企业资质见[证:not-in-plan]。",
        "希望能帮到您！",
    ])
    outcome = run_chapter_loop(content, LoopContext(title="服务方案"))
    before, after = content.split("\n"), outcome["content"].split("\n")
    assert after[:5] == before[:5]                 # 直接转人工与未点名段落逐字不变
    assert "希望能帮到您" not in after[5]            # 对话残留由系统直接删除
    reasons = {i["code"]: i["human_reason"] for i in outcome["issues"]}
    assert reasons["NEGATIVE_DEVIATION_DETECTED"] == "BUSINESS_DEVIATION"
    assert reasons["FABRICATED_OR_INVALID_EVIDENCE_CITATION"] == "EVIDENCE_CITATION"
    placeholder = {i["paragraph_index"]: i["human_reason"] for i in outcome["issues"] if i["code"] == "PLACEHOLDER_RESIDUAL"}
    assert placeholder == {2: "PERSONNEL_IDENTITY", 3: "AMOUNT_OR_COMMITMENT"}
    assert outcome["stop_reason"] == "NEED_HUMAN"
    assert all(i["fix_count"] == 0 for i in outcome["issues"])


def test_star_requirement_routes_placeholder_to_human_and_fact_variable_is_auto():
    facts = [{"id": "f1", "key": "服务期", "status": "confirmed", "variable_token": "{{fact:f1}}"}]
    star = run_chapter_loop("服务期为【待补：服务期】。", LoopContext(facts=facts, critical=True))
    assert star["issues"] == [] and "{{fact:f1}}" in star["content"]
    star_missing = run_chapter_loop("驻场人数【待补：人数】。", LoopContext(facts=facts, critical=True))
    assert star_missing["issues"][0]["human_reason"] == "STAR_OR_DISQUALIFY"


def test_system_generated_chapter_problems_go_to_human():
    outcome = run_chapter_loop("偏离说明。希望能帮到您！", LoopContext(title="商务偏离表"))
    assert outcome["content"] == "偏离说明。希望能帮到您！"
    assert outcome["issues"][0]["human_reason"] == "SYSTEM_CHAPTER"


def test_max_rounds_one_checks_only_and_hands_over():
    outcome = run_chapter_loop("内容。希望能帮到您！", LoopContext(), max_rounds=1)
    assert outcome["stop_reason"] == "MAX_ROUNDS"
    assert outcome["content"] == "内容。希望能帮到您！"
    assert outcome["issues"][0]["route"] == "escalated_human"


def test_unsafe_model_rewrite_is_refused():
    def fabricate(original, issues):
        return "我司承诺 15 分钟到场，满足全部要求[证:ev-x]。"

    outcome = run_chapter_loop("内容。希望能帮到您！", LoopContext(), model_fix=fabricate)
    assert "15" not in outcome["content"] and "ev-x" not in outcome["content"]
    assert outcome["stop_reason"] == "ALL_RESOLVED"


def test_fix_that_introduces_new_problem_is_rolled_back(monkeypatch):
    monkeypatch.setattr(chapter_loop, "model_fix_is_safe", lambda *args: True)

    def introduce(original, issues):
        return "内容【待补：某资料】。"

    content = "内容。希望能帮到您！"
    outcome = run_chapter_loop(content, LoopContext(), model_fix=introduce)
    assert outcome["stop_reason"] == "FIX_REGRESSION"
    assert outcome["rolled_back"] is True
    assert outcome["content"] == content


# ---------------------------------------------------------------- HTTP 队列

DEFECTIVE = "技术正文：每月巡检。我司无法提供全天候驻场。项目业绩见【待补：同类业绩】。希望能帮到您！"


def _headers(flow, account="alpha-manager"):
    return {**login(flow.client, account), "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())}


def _technical(flow):
    return next(c for c in flow.state()["chapters"] if c["volume"] == "technical")


def _prepared(client):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    flow.commit(chapter["id"], DEFECTIVE)
    return flow, chapter["id"]


def test_recheck_fixes_safe_items_and_queues_the_rest(client):
    flow, cid = _prepared(client)
    before = client.get(f"/api/chapters/{cid}", headers=flow.headers).json()["revision"]
    result = client.post(f"{flow.path}/chapters/{cid}/loop/recheck", json={}, headers=_headers(flow))
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["content_fixed"] is True
    assert body["stop_reason"] == "NEED_HUMAN"
    assert body["chapter_revision"] == before + 1
    chapter = client.get(f"/api/chapters/{cid}", headers=flow.headers).json()
    assert "希望能帮到您" not in chapter["content"] and "无法提供" in chapter["content"]

    queue = client.get(f"{flow.path}/human-queue", headers=flow.headers).json()
    assert queue["summary"]["pending"] == 2 and queue["summary"]["chapters"] == 1
    group = queue["chapters"][0]
    assert group["loop"]["status"] == "pending_human" and group["loop"]["stop_reason_label"] == "剩余问题需人工处理"
    # 技术章节回应的是★条款，所在段落的问题一律按“星号或废标条款”转人工
    labels = {i["human_reason_label"] for i in group["issues"]}
    assert labels == {"星号或废标条款"}
    assert {i["code"] for i in group["issues"]} == {"NEGATIVE_DEVIATION_DETECTED", "PLACEHOLDER_RESIDUAL"}
    assert all(i["number"].startswith("1-") for i in group["issues"])
    assert all(i["permissions"] == {"resolve": True, "reject": False} for i in group["issues"])

    loop = client.get(f"{flow.path}/chapters/{cid}/loop", headers=flow.headers).json()
    assert loop["counts"]["pending_human"] == 2 and loop["counts"]["resolved"] == 0
    assert loop["loop"]["rounds"][0]["modified_paragraphs"] == [0]


def test_queue_visibility_and_tenant_isolation(client):
    flow, cid = _prepared(client)
    client.post(f"{flow.path}/chapters/{cid}/loop/recheck", json={}, headers=_headers(flow))
    viewer = client.get(f"{flow.path}/human-queue", headers=login(client, "alpha-viewer")).json()
    assert viewer["summary"]["pending"] == 2
    assert all(i["permissions"] == {"resolve": False, "reject": False} for i in viewer["chapters"][0]["issues"])
    issue = viewer["chapters"][0]["issues"][0]
    denied = client.post(f"{flow.path}/human-queue/issues/{issue['id']}/resolve", json={"method": "edited"},
                         headers=_headers(flow, "alpha-viewer"))
    assert denied.status_code == 403
    beta = client.get(f"{flow.path}/human-queue", headers=login(client, "beta-manager"))
    assert beta.status_code == 404
    readonly_recheck = client.post(f"{flow.path}/chapters/{cid}/loop/recheck", json={}, headers=_headers(flow, "alpha-viewer"))
    assert readonly_recheck.status_code == 403


def test_blocker_cannot_be_rejected_and_resolving_all_marks_human_handled(client):
    flow, cid = _prepared(client)
    client.post(f"{flow.path}/chapters/{cid}/loop/recheck", json={}, headers=_headers(flow))
    issues = client.get(f"{flow.path}/human-queue", headers=flow.headers).json()["chapters"][0]["issues"]
    first, second = issues

    rejected = client.post(f"{flow.path}/human-queue/issues/{first['id']}/reject",
                           json={"reason_type": "false_positive", "reason": "误报"}, headers=_headers(flow))
    assert rejected.status_code == 409 and rejected.json()["code"] == "BLOCKER_NOT_REJECTABLE"

    no_method = client.post(f"{flow.path}/human-queue/issues/{first['id']}/resolve", json={"method": "skip"},
                            headers=_headers(flow))
    assert no_method.status_code == 422

    done = client.post(f"{flow.path}/human-queue/issues/{first['id']}/resolve",
                       json={"method": "keep_placeholder", "note": "业绩证明待商务补齐", "also_issue_ids": [second["id"]]},
                       headers=_headers(flow))
    assert done.status_code == 200, done.text
    assert done.json()["chapter_status"] == "human_handled"
    assert set(done.json()["issue_ids"]) == {first["id"], second["id"]}

    again = client.post(f"{flow.path}/human-queue/issues/{first['id']}/resolve", json={"method": "edited"},
                        headers=_headers(flow))
    assert again.status_code == 409 and again.json()["code"] == "HUMAN_ISSUE_NOT_PENDING"
    assert client.get(f"{flow.path}/human-queue", headers=flow.headers).json()["summary"]["pending"] == 0

    # 重新检查开始新一次循环：正文未改，同指纹问题沿用原编号重新打开
    client.post(f"{flow.path}/chapters/{cid}/loop/recheck", json={}, headers=_headers(flow))
    reopened = client.get(f"{flow.path}/human-queue", headers=flow.headers).json()["chapters"][0]
    assert {i["number"] for i in reopened["issues"]} == {first["number"], second["number"]}
    assert reopened["loop"]["loop_no"] == 2 and reopened["loop"]["loop_count"] == 2
    audit = client.app.state.service.repository.read().audit
    assert any(event["action"].startswith("human.resolve") for event in audit)


def test_warning_rejection_requires_project_lead(client):
    flow, cid = _prepared(client)
    client.post(f"{flow.path}/chapters/{cid}/loop/recheck", json={}, headers=_headers(flow))
    repository = client.app.state.service.repository

    def add_warning(state):
        store = state.workflows[flow.id]["human_queue"]
        store["issues"]["hq-warn"] = {
            "id": "hq-warn", "number": "1-099", "chapter_id": cid, "volume": "technical", "fingerprint": "R43|x|P0",
            "code": "AI_TONE", "rule": "R43", "source": "rule", "level": "warning", "severity": "medium",
            "status": "pending_human", "route": "escalated_human", "human_reason": "LOOP_STOPPED",
            "paragraph_index": 0, "quote": "", "message": "套话", "suggestion": "", "fix_count": 2, "loop_no": 1,
            "history": [],
        }

    repository.transaction(add_warning)
    by_writer = client.post(f"{flow.path}/human-queue/issues/hq-warn/reject",
                            json={"reason_type": "not_adopted", "reason": "保留"}, headers=_headers(flow, "alpha-editor"))
    assert by_writer.status_code == 403
    missing_reason = client.post(f"{flow.path}/human-queue/issues/hq-warn/reject",
                                 json={"reason_type": "not_adopted", "reason": ""}, headers=_headers(flow))
    assert missing_reason.status_code == 422
    by_lead = client.post(f"{flow.path}/human-queue/issues/hq-warn/reject",
                          json={"reason_type": "not_adopted", "reason": "公司惯用表达"}, headers=_headers(flow))
    assert by_lead.status_code == 200, by_lead.text


def test_recheck_refuses_locked_chapter_and_needs_version(client):
    flow, cid = _prepared(client)
    lock = client.post(f"/api/chapters/{cid}/lock", headers=flow.headers, json={})
    assert lock.status_code == 200
    busy = client.post(f"{flow.path}/chapters/{cid}/loop/recheck", json={}, headers=_headers(flow))
    assert busy.status_code == 409 and busy.json()["code"] == "CHAPTER_IN_USE"
    no_version = client.post(f"{flow.path}/chapters/{cid}/loop/recheck", json={},
                             headers={**login(client), "Idempotency-Key": str(uuid4())})
    assert no_version.status_code == 428


# ---------------------------------------------------------------- 循环进度与轮次时间线（APP-M2-T130 / T131）

def test_round_records_which_paragraph_was_fixed_and_how():
    outcome = run_chapter_loop("内容。希望能帮到您！\n第二段正常。", LoopContext())
    first = outcome["rounds"][0]
    assert first["codes"] and first["fixes"] == [{"paragraph_index": 0, "by": "rule", "codes": first["fixes"][0]["codes"]}]
    assert outcome["rounds"][-1]["fixes"] == []


def test_chapter_loops_lists_every_chapter_and_progress(client):
    flow, cid = _prepared(client)
    before = client.get(f"{flow.path}/chapter-loops", headers=flow.headers)
    assert before.status_code == 200, before.text
    rows = before.json()["chapters"]
    assert len(rows) == len(flow.state()["chapters"]) and all(r["loop"] is None for r in rows)
    assert before.json()["totals"]["not_started"] == len(rows)

    client.post(f"{flow.path}/chapters/{cid}/loop/recheck", json={}, headers=_headers(flow))
    body = client.get(f"{flow.path}/chapter-loops?volume=technical", headers=flow.headers).json()
    row = next(r for r in body["chapters"] if r["chapter_id"] == cid)
    assert row["loop"]["status"] == "pending_human" and row["pending"] == 2 and row["can_recheck"] is True
    assert body["totals"]["pending_human"] == 1
    assert all(r["volume"] == "technical" for r in body["chapters"])
    viewer = client.get(f"{flow.path}/chapter-loops", headers=login(client, "alpha-viewer")).json()
    assert all(r["can_recheck"] is False for r in viewer["chapters"])
    assert client.get(f"{flow.path}/chapter-loops", headers=login(client, "beta-manager")).status_code == 404


def test_loop_timeline_records_task_inputs_versions_and_summary_relay(client):
    flow, cid = _prepared(client)
    client.post(f"{flow.path}/chapters/{cid}/loop/recheck", json={}, headers=_headers(flow))
    client.post(f"{flow.path}/chapters/{cid}/loop/recheck", json={}, headers=_headers(flow))
    body = client.get(f"{flow.path}/chapters/{cid}/loop", headers=flow.headers).json()
    loop = body["loop"]
    meta = loop["meta"]
    assert meta["task"] == "recheck" and meta["model"] is None and "规则" in meta["fixer"]
    assert set(meta["inputs"]) >= {"requirements", "evidence", "snippets", "facts"}
    assert meta["summary_relay"]["status"] in {"not_applicable", "missing", "used"}
    assert loop["result_revision"] == body["chapter_revision"] and loop["started_by"]
    # 上一次循环进入历史，带版本与依据
    assert loop["loop_count"] == 2 and len(body["history"]) == 1
    previous = body["history"][0]
    assert previous["meta"]["base_revision"] < previous["result_revision"]
    assert previous["rounds"][0]["fixes"][0]["by"] == "rule"


def test_summary_relay_marks_missing_previous_chapter():
    from types import SimpleNamespace
    from icg.domain.generation_context import previous_chapter_relay

    one = SimpleNamespace(id="c1", project_id="p", volume="technical", title="总体方案", content="", revision=1)
    two = SimpleNamespace(id="c2", project_id="p", volume="technical", title="服务方案", content="", revision=1)
    other = SimpleNamespace(id="c3", project_id="p", volume="business", title="商务", content="正文", revision=1)
    state = SimpleNamespace(workflows={"p": {"chapter_order": ["c1", "c3", "c2"]}}, chapters={"c1": one, "c2": two, "c3": other})
    assert previous_chapter_relay(state, "p", one)["status"] == "not_applicable"
    missing = previous_chapter_relay(state, "p", two)
    assert missing["status"] == "missing" and "总体方案" in missing["message"]
    one.content = "# 总体方案\n我司按 {{fact:f1}} 提供驻场服务[证:ev1]，覆盖全部系统。"
    used = previous_chapter_relay(state, "p", two)
    assert used["status"] == "used" and used["summary"].startswith("我司按") and "{{" not in used["summary"]
    assert previous_chapter_relay(state, "p", other)["status"] == "not_applicable"
