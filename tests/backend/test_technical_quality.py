# 为什么有这个文件：核对质量八条规则抽检与「需核对」标记。
# 它解决什么问题：未达标必须可见警告，且不得恢复矩阵确认闸门语义。

from __future__ import annotations

from icg.domain.technical_quality import apply_quality_markers, evaluate_quality


def _workflow(*, headings=None, requirements=None):
    return {
        "technical_outline": {
            "title": "技术方案",
            "chapter_id": "ch1",
            "headings": headings or [
                {"level": 1, "number": "1", "title": "总体", "requirement_id": None},
                {"level": 2, "number": "1.1", "title": "巡检方案", "requirement_id": "r1"},
                {"level": 2, "number": "1.2", "title": "主机可用性", "requirement_id": "r2"},
            ],
        },
        "requirements": requirements or {
            "r1": {
                "id": "r1", "text": "每月巡检数据库并出具报告", "status": "confirmed",
                "technical_clause": True, "section_kind": "scoring",
                "response_type": "comply", "response": "按招标执行",
            },
            "r2": {
                "id": "r2", "text": "技术规格书第 3.2 条主机可用性", "status": "confirmed",
                "technical_clause": True, "section_kind": "spec",
                "response_type": "comply", "response": "按招标执行",
            },
        },
    }


def test_quality_flags_thin_scoring_and_commercial_noise():
    content = """1 总体

1.1 巡检方案
待补
1.2 主机可用性
本节约营业执照与投标保证金材料说明，不替代主机可用性技术响应。以下文字仅作商务材料罗列。
"""
    result = evaluate_quality(_workflow(), content)
    assert result["passed"] is False
    assert result["failed_count"] >= 2
    assert "巡检方案" in result["review_titles"]
    assert "主机可用性" in result["review_titles"]
    assert "质量八条未全部通过" in result["warning"]
    ids = {rule["id"] for rule in result["rules"] if not rule["passed"]}
    assert 2 in ids and 8 in ids


def test_quality_passes_when_sections_touch_project():
    content = """1 总体

1.1 巡检方案
服务目标：本项目按招标要求每月巡检数据库并出具报告。
开篇说明结合客户机房场景落地巡检节奏。
| 项 | 内容 |
| --- | --- |
| 频次 | 每月 |
收束：以上措施可在本招标场景执行。
1.2 主机可用性
服务目标：技术规格书第 3.2 条主机可用性在本项目落地。
结合招标机房约束安排冗余与切换演练。
| 项 | 内容 |
| --- | --- |
| 可用性 | 按规格书 |
小结：扣住本项目核心技术要求。
"""
    result = evaluate_quality(_workflow(), content)
    assert result["passed"] is True
    assert result["failed_count"] == 0
    assert result["warning"] == ""
    assert result["review_titles"] == []


def test_apply_quality_markers_appends_once():
    outline = _workflow()["technical_outline"]
    content = """1 总体

1.1 巡检方案
一段正文。
1.2 报价说明
另一段。
"""
    once = apply_quality_markers(content, ["巡检方案"], outline)
    assert once.count("需要核对") == 1
    twice = apply_quality_markers(once, ["巡检方案"], outline)
    assert twice.count("需要核对") == 1


def test_quality_outline_shell_counts_listed_ids_and_defers_body_rules():
    headings = [
        {"level": 1, "number": "1", "title": "运维保障", "requirement_id": None, "requirement_ids": []},
        {
            "level": 2,
            "number": "1.1",
            "title": "巡检与主机",
            "requirement_id": "r1",
            "requirement_ids": ["r2"],
            "mount_ids": ["r3"],
            "constraint_ids": ["r4"],
        },
    ]
    requirements = {
        "r1": {
            "id": "r1", "text": "每月巡检数据库并出具报告", "status": "confirmed",
            "technical_clause": True, "section_kind": "scoring",
        },
        "r2": {
            "id": "r2", "text": "技术规格书主机可用性指标", "status": "confirmed",
            "technical_clause": True, "section_kind": "spec",
        },
        "r3": {
            "id": "r3", "text": "故障两小时内到达现场", "status": "confirmed",
            "technical_clause": True, "section_kind": "scoring",
        },
        "r4": {
            "id": "r4", "text": "不得转包关键运维", "status": "confirmed",
            "technical_clause": True, "section_kind": "spec",
        },
    }
    content = "1 运维保障\n1.1 巡检与主机\n"
    result = evaluate_quality(_workflow(headings=headings, requirements=requirements), content)
    by_id = {rule["id"]: rule for rule in result["rules"]}
    assert by_id[1]["passed"] is True
    assert by_id[1]["detail"] == "挂接完整"
    for rule_id in (2, 3, 5, 6, 8):
        assert by_id[rule_id]["passed"] is True
        assert by_id[rule_id]["detail"] == "待生成正文后再检"
    assert by_id[4]["passed"] is True
    assert by_id[7]["passed"] is True
    assert by_id[7]["detail"] != "待生成正文后再检"
    assert result["review_titles"] == []
