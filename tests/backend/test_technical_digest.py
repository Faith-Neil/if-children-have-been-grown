# 为什么有这个文件：核对三张清单抽取、清单拟目录挂要点与正文提示里的废标约束。
from __future__ import annotations

import json

from icg.domain.technical_digest import build_digest, rejection_lines
from icg.domain.technical_digest_outline import FALLBACK_TITLE, plan_technical_outline
from icg.domain.technical_model_extract import extract_with_model


class FakeModel:
    is_real_model = True
    is_local = True
    base_url = ""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def suggest(self, system, user, profile=None):
        self.calls.append((system, user))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def _workflow():
    return {
        "requirements": {
            "r1": {"id": "r1", "text": "每月巡检数据库并出具报告", "technical_clause": True,
                   "status": "pending", "section_kind": "spec", "source": {"page": 3, "quote": "每月巡检"}},
            "r2": {"id": "r2", "text": "应急预案完整", "technical_clause": True, "status": "pending",
                   "section_kind": "scoring", "score_item": "运维方案", "score": 10.0,
                   "criteria": "方案完整得10分"},
            "r3": {"id": "r3", "text": "备份恢复演练", "technical_clause": True, "status": "pending",
                   "section_kind": "scoring", "score_item": "运维方案", "score": 10.0},
        },
        "technical_sidecars": {"rejection_lines": ["未按要求提供服务方案的投标无效"], "format_lines": []},
    }


def test_extract_reads_three_lists_and_keeps_scoring_meta():
    reply = json.dumps({
        "who": "某银行", "requirements": [{"text": "7×24小时值守", "quote": "提供7×24小时值守", "star": True}],
        "scoring": [{"item": "服务方案", "score": "15分", "criteria": "方案完整", "points": ["巡检计划", "应急预案"],
                     "quote": "服务方案15分"}],
        "rejections": [{"text": "未盖章无效", "quote": "投标文件未盖章的作无效投标", "category": "格式"}],
    }, ensure_ascii=False)
    payload = extract_with_model(["第一页"], FakeModel([reply]))
    by_text = {item["text"]: item for item in payload["items"]}
    assert by_text["巡检计划"]["score_item"] == "服务方案" and by_text["巡检计划"]["score"] == 15.0
    assert by_text["7×24小时值守"]["kind"] == "spec" and by_text["7×24小时值守"]["star"] is True
    assert by_text["未盖章无效"]["role"] == "rejection_constraint" and by_text["未盖章无效"]["category"] == "格式"
    assert (payload["requirement_count"], payload["scoring_count"], payload["rejection_count"]) == (1, 2, 1)


def test_digest_numbers_three_lists():
    workflow = _workflow()
    digest = build_digest(workflow)
    assert [item["id"] for item in digest["tech"]] == ["T-01"]
    assert digest["scoring"][0]["id"] == "S-01" and [p["id"] for p in digest["scoring"][0]["points"]] == ["S-01-1", "S-01-2"]
    assert digest["rejection"][0]["id"] == "R-01"
    assert workflow["requirements"]["r3"]["digest_id"] == "S-01-2"
    assert rejection_lines(workflow) == ["R-01 未按要求提供服务方案的投标无效"]


def test_model_outline_mounts_points_and_patches_missing():
    reply = json.dumps({"nodes": [
        {"level": 1, "title": "运维服务方案"},
        {"level": 2, "title": "日常巡检", "points": [{"text": "月度巡检出报告", "refs": ["T-01"]}]},
        {"level": 2, "title": "应急保障", "points": [{"text": "应急预案", "refs": ["S-01-1"]}]},
        {"level": 2, "title": "空节"},
    ]}, ensure_ascii=False)
    workflow = _workflow()
    model = FakeModel([reply])
    plan = plan_technical_outline(workflow, model)
    assert workflow["outline_source"] == "model"
    assert "R-01" in model.calls[0][1] and "S-01-2" in model.calls[0][1]
    titles = [(item["number"], item["title"]) for item in plan["headings"]]
    assert titles == [("1", "运维服务方案"), ("1.1", "日常巡检"), ("1.2", "应急保障"), ("2", FALLBACK_TITLE)]
    leaf = plan["headings"][1]
    assert leaf["requirement_ids"] == ["r1"] and leaf["points"][0]["text"] == "月度巡检出报告"
    assert plan["headings"][3]["requirement_ids"] == ["r3"]
    assert plan["validation"]["patched_requirement_ids"] == ["r3"]
    task = workflow["response_tasks"][leaf["task_id"]]
    assert task["response_points"] == ["月度巡检出报告"] and task["outline_number"] == "1.1"


def test_model_outline_failure_falls_back_to_rule():
    workflow = _workflow()
    plan = plan_technical_outline(workflow, FakeModel([TimeoutError(), "not json"]))
    assert workflow["outline_source"] == "rule_fallback" and workflow["tree_model_failed"] is True
    assert plan["headings"]


def test_section_prompt_carries_scoring_and_rejection_list():
    from icg.domain.technical_volume import _section_user

    workflow = _workflow()
    build_digest(workflow)
    rows = [workflow["requirements"]["r2"]]
    user = _section_user("应急保障", rows, {"response_points": ["应急预案"]}, workflow, "")
    assert "运维方案（10 分）：方案完整得10分" in user
    assert "R-01 未按要求提供服务方案的投标无效" in user


def test_extract_merges_scoring_meta_into_duplicate_requirement():
    reply = json.dumps({
        "requirements": [{"text": "季度健康检查并出具报告", "quote": "季度健康检查"}],
        "scoring": [{"item": "健康检查", "score": 8, "criteria": "季度检查得8分", "points": ["季度健康检查并出具报告"]}],
    }, ensure_ascii=False)
    payload = extract_with_model(["第一页"], FakeModel([reply]))
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert (item["kind"], item["score_item"], item["score"], item["criteria"]) == ("scoring", "健康检查", 8.0, "季度检查得8分")
    assert (payload["requirement_count"], payload["scoring_count"]) == (0, 1)


def test_malformed_outline_reply_falls_back_without_raising():
    workflow = _workflow()
    model = FakeModel(['{"nodes": 1}', json.dumps({"nodes": [{"level": 1, "title": "巡检", "points": [{"text": "巡检", "refs": 5}]}]})])
    plan = plan_technical_outline(workflow, model)
    assert workflow["outline_source"] == "rule_fallback" and plan["headings"]


def test_rule_fallback_does_not_call_tree_model_again():
    workflow = _workflow()
    model = FakeModel([RuntimeError("boom"), RuntimeError("boom")])
    workflow["tree_model"] = model
    plan_technical_outline(workflow)
    assert len(model.calls) == 2 and workflow["tree_model"] is model
    assert workflow["outline_source"] == "rule_fallback"


def test_rejection_lines_keep_every_condition():
    workflow = _workflow()
    workflow["technical_sidecars"]["rejection_lines"] = [f"第{index}条废标条件" for index in range(1, 61)]
    build_digest(workflow)
    lines = rejection_lines(workflow)
    assert len(lines) == 60 and lines[-1] == "R-60 第60条废标条件"
