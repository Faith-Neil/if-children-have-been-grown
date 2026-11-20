# 为什么有这个文件：核对生成后的废标校验，不让模型自己把废标写成已响应。
# 它解决什么问题：技术废标被写反或放宽才失败；没写到、资格和保证金都不失败。

from __future__ import annotations

import json
from types import SimpleNamespace

from icg.domain.technical_clause_role import classify_constraint
from icg.domain.technical_constraint_check import completion_message, evaluate_volume

_GENERIC = "每月巡检数据库并出具运行记录，过程记录供验收核对，供后续复查。"
_CLAIM = "本节废标已全部响应。已响应全部废标条款。过程记录供验收核对，请人工复核本节范围。"
_VIOLATING_CLAIM = "不承诺备份窗口。" + _CLAIM
_L0 = "备份窗口不满足则作废标处理"
_REMOTE = "须保证7×24小时远程响应，不满足则作废标处理"
_DEPOSIT = "未提交投标保证金的，否决其投标"
_TIP = "被列入失信被执行人名单的，否决其投标"
_L1 = "未覆盖监控点位的否决其投标"


def _workflow(lines: list[str]) -> dict:
    return {"technical_sidecars": {"rejection_lines": lines}, "requirements": {}}


def _section(key: str, title: str, body: str, rows: list[dict] | None = None, task: dict | None = None) -> dict:
    return {"key": key, "title": title, "body": body, "rows": rows or [], "task": task}


def _texts(result: dict) -> list[str]:
    return [item["text"] for item in result["missing"]]


def test_model_claim_does_not_cover_l0():
    silent = evaluate_volume(
        _workflow([_L0]),
        [_section("t1", "备份", _CLAIM)],
    )
    assert silent["status"] == "passed"
    assert silent["missing"] == []
    result = evaluate_volume(
        _workflow([_L0]),
        [_section("t1", "备份", _VIOLATING_CLAIM)],
    )
    assert result["status"] == "failed"
    assert _L0 in _texts(result)
    assert "已响应" not in result["status"]


def test_keyword_overlap_covers_l0():
    result = evaluate_volume(
        _workflow([_L0]),
        [_section("t1", "备份", "承诺备份窗口在2小时内完成，并留下备份记录供验收核对。")],
    )
    assert result["status"] == "passed"
    assert result["missing"] == []
    assert result["conflicts"] == []


def test_explicit_cite_covers_l0():
    result = evaluate_volume(
        _workflow([_L0]),
        [_section("t1", "备份", "依据[标:备份窗口不满足]安排备份，并留下记录供验收核对。")],
    )
    assert result["status"] == "passed"
    assert result["missing"] == []


def test_non_tech_tip_does_not_require_a_body_response():
    result = evaluate_volume(
        _workflow([_TIP, _DEPOSIT]),
        [_section("t1", "巡检", _GENERIC)],
    )
    assert result["status"] == "passed"
    assert result["missing"] == []
    assert all("失信" not in text and "保证金" not in text for text in _texts(result))


def test_qualification_row_is_not_a_section_requirement():
    result = evaluate_volume(
        _workflow([]),
        [_section("t1", "巡检", _GENERIC, rows=[{
            "text": "具备信息系统集成资质",
            "extracted_summary": "具备信息系统集成资质",
            "requirement_type": "qualification",
            "is_rejection_criterion": True,
        }])],
    )
    assert result["status"] == "passed"
    assert all("资质" not in text for text in _texts(result))


def test_l1_silence_passes_and_negation_fails_in_its_section():
    row = {
        "text": _L1,
        "extracted_summary": _L1,
        "clause_role": "rejection_constraint",
    }
    covered = "覆盖监控点位并按点位清单逐项核对，留下记录。"
    silent = evaluate_volume(
        _workflow([]),
        [
            _section("t1", "点位", _GENERIC, rows=[row]),
            _section("t2", "其他", covered),
        ],
    )
    assert silent["status"] == "passed"
    assert silent["missing"] == []
    assert silent["sections"]["t1"]["status"] == "passed"
    result = evaluate_volume(
        _workflow([]),
        [_section("t1", "点位", "不承诺覆盖监控点位。", rows=[row])],
    )
    assert result["status"] == "failed"
    missed = [item for item in result["missing"] if item["level"] == "L1"]
    assert len(missed) == 1
    assert missed[0]["text"] == _L1
    assert missed[0]["section"] == "点位"
    assert result["sections"]["t1"]["status"] == "failed"


def test_volume_l0_is_covered_by_any_section():
    result = evaluate_volume(
        _workflow([_L0, _TIP]),
        [
            _section("t1", "总则", _GENERIC),
            _section("t2", "备份", "承诺备份窗口在2小时内完成，并留下备份记录供验收核对。"),
        ],
    )
    assert result["status"] == "passed"
    assert result["missing"] == []
    assert result["sections"]["t1"]["status"] == "passed"


def test_volume_scans_l0_past_the_prompt_cap():
    stems = ["备份窗口", "巡检周期", "监控点位", "故障恢复", "日志留存", "权限分离", "演练频次", "补丁时限", "切换演练"]
    lines = [f"{stem}不满足则作废标处理" for stem in stems]
    covered = "、".join(stems[:-1])
    result = evaluate_volume(
        _workflow(lines),
        [_section("t1", "总则", f"不承诺{stems[-1]}。正文写明{covered}，并留下记录供验收核对。")],
    )
    assert result["status"] == "failed"
    assert any("切换演练" in text for text in _texts(result))
    assert not any("备份窗口" in text for text in _texts(result))


def test_contradicting_promises_need_confirm():
    line = "故障恢复时限超过4小时未恢复作废标处理"
    result = evaluate_volume(
        _workflow([line]),
        [
            _section("t1", "甲节", "承诺故障恢复在4小时内完成，并留下记录供验收核对。"),
            _section("t2", "乙节", "承诺故障恢复在2小时内完成，并留下记录供验收核对。"),
        ],
    )
    assert result["status"] == "needs_confirm"
    assert result["missing"] == []
    blob = json.dumps(result["conflicts"], ensure_ascii=False)
    assert "甲节" in blob and "乙节" in blob
    assert "4小时" in blob and "2小时" in blob


def test_same_promise_is_not_a_conflict():
    line = "故障恢复时限超过4小时未恢复作废标处理"
    body = "承诺故障恢复在4小时内完成，并留下记录供验收核对。"
    result = evaluate_volume(
        _workflow([line]),
        [_section("t1", "甲节", body), _section("t2", "乙节", body)],
    )
    assert result["status"] == "passed"
    assert result["conflicts"] == []


def test_seeded_responded_status_does_not_flip_the_check():
    task = {"response_status": "已响应", "constraint_check": {"status": "passed", "notice": "废标已全部响应"}}
    result = evaluate_volume(
        _workflow([_L0]),
        [_section("t1", "备份", _VIOLATING_CLAIM, task=task)],
    )
    assert result["status"] == "failed"
    assert result["notice"]
    assert "废标已全部响应" not in result["notice"]
    assert "不能视为已全部响应" in result["notice"]


def test_completion_message_rejects_a_false_all_clear():
    text = completion_message("技术分册已写入当前正文。", {
        "status": "failed",
        "notice": "废标已全部响应",
    })
    assert text.startswith("技术分册已写入当前正文。")
    assert "不能视为已全部响应" in text
    assert "废标已全部响应" not in text
    confirm = completion_message("技术分册内部稿已生成。", {"status": "needs_confirm"})
    assert "不能视为已全部响应" in confirm
    assert completion_message("技术分册内部稿已生成。", {"status": "passed", "notice": "废标已全部响应"}) == "技术分册内部稿已生成。"
    assert completion_message("技术分册内部稿已生成。", None) == "技术分册内部稿已生成。"


def test_write_volume_stores_failed_check_when_model_claims_responded():
    from icg.domain.technical_volume import write_volume

    class Model:
        is_real_model = True
        is_local = True
        base_url = "http://127.0.0.1:9"

        def suggest(self, system, user):
            return _VIOLATING_CLAIM

    chapter = SimpleNamespace(id="c1", content="", revision=1)
    state = SimpleNamespace(
        chapters={"c1": chapter},
        projects={"p": SimpleNamespace(id="p", name="合成项目", company_id="alpha")},
    )
    task = {"task_id": "t1", "requirement_ids": ["r1"], "response_points": ["备份窗口"]}
    workflow = {
        "plan_confirmed": True,
        "technical_outline": {
            "chapter_id": "c1",
            "headings": [{
                "level": 1, "number": "1", "title": "备份",
                "task_id": "t1", "requirement_id": "r1", "requirement_ids": ["r1"],
            }],
        },
        "requirements": {
            "r1": {
                "id": "r1",
                "technical_clause": True,
                "text": _L0,
                "extracted_summary": _L0,
                "is_rejection_criterion": True,
                "requirement_type": "rejection_item",
                "status": "confirmed",
            },
        },
        "response_tasks": {"t1": task},
        "technical_sidecars": {"rejection_lines": [_L0, _TIP]},
        "files": {},
    }
    result = write_volume(state, "p", workflow, None, Model())
    assert "已响应" in chapter.content
    assert result["constraint_check"]["status"] == "failed"
    assert workflow["constraint_check"]["status"] == "failed"
    assert "不能视为已全部响应" in workflow["constraint_check"]["notice"]
    assert task["constraint_check"]["status"] == "failed"
    assert task["response_status"] != "已响应"
    assert "失信" not in json.dumps(workflow["constraint_check"]["missing"], ensure_ascii=False)


def test_fixture_non_tech_absence_passes():
    deposit = classify_constraint(_DEPOSIT)
    credit = classify_constraint(_TIP)
    assert deposit["kind"] == "non_tech_risk"
    assert credit["kind"] == "non_tech_risk"
    assert deposit["level"] == "L0"
    result = evaluate_volume(
        _workflow([_DEPOSIT, _TIP]),
        [_section("t1", "巡检", _GENERIC)],
    )
    assert result["status"] == "passed"
    assert result["missing"] == []


def test_fixture_tech_l0_absence_passes():
    classified = classify_constraint(_REMOTE)
    assert classified == {"kind": "tech_hard", "level": "L0"}
    result = evaluate_volume(
        _workflow([_REMOTE]),
        [_section("t1", "巡检", _GENERIC)],
    )
    assert result["status"] == "passed"
    assert result["missing"] == []


def test_fixture_work_hours_and_weaker_sla_fail():
    weakened = evaluate_volume(
        _workflow([_REMOTE]),
        [_section("t1", "响应", "仅工作时间远程响应。")],
    )
    assert weakened["status"] == "failed"
    assert _REMOTE in _texts(weakened)
    slower = evaluate_volume(
        _workflow(["故障恢复时限超过4小时未恢复作废标处理"]),
        [_section("t1", "恢复", "承诺故障恢复在8小时内完成，并留下记录供验收核对。")],
    )
    assert slower["status"] == "failed"
    assert slower["missing"]


def test_fixture_explicit_negation_fails():
    result = evaluate_volume(
        _workflow([_REMOTE]),
        [_section("t1", "响应", "不承诺7×24小时远程响应。")],
    )
    assert result["status"] == "failed"
    assert _REMOTE in _texts(result)
    refused = evaluate_volume(
        _workflow([_REMOTE]),
        [_section("t1", "响应", "不保证7×24小时远程响应。")],
    )
    assert refused["status"] == "failed"


def test_fixture_claim_does_not_flip_status():
    claimed = evaluate_volume(
        _workflow([_REMOTE]),
        [_section("t1", "响应", "已响应。已满足废标。")],
    )
    assert claimed["status"] == "passed"
    still = evaluate_volume(
        _workflow([_REMOTE]),
        [_section("t1", "响应", "不承诺7×24小时远程响应。已响应。已满足废标。")],
    )
    assert still["status"] == "failed"


def test_unclear_absence_does_not_fail_or_ask():
    line = "按采购人另行通知办理"
    assert classify_constraint(line) == {"kind": "unclear", "level": "L2"}
    result = evaluate_volume(
        _workflow([line]),
        [_section("t1", "巡检", _GENERIC)],
    )
    assert result["status"] == "passed"
    assert result["missing"] == []
    assert result["notice"] == ""
