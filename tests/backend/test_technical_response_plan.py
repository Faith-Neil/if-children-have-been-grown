# 为什么有这个文件：核对两层矩阵、主题目录短标题与计划校验。
from __future__ import annotations

from icg.domain.technical_chapter_tree import BACKBONE_BACK, BACKBONE_FRONT, detect_format_lock, tree_issues
from icg.domain.technical_response_plan import (
    apply_response_plan,
    short_chapter_title,
    validate_plan,
)


def test_short_title_does_not_keep_full_clause():
    long = "服务商为用户提供现场技术支持服务：一级故障立即电话支持并在两小时内到达现场处理"
    title = short_chapter_title(long)
    assert len(title) <= 18
    assert "两小时内到达现场处理" not in title


def test_apply_response_plan_builds_theme_outline_not_raw_clause_titles():
    workflow = {
        "requirements": {
            "r1": {
                "id": "r1", "text": "提供数据库系统方案设计和实施（不低于2次）",
                "technical_clause": True, "status": "confirmed", "section_kind": "scoring",
            },
            "r2": {
                "id": "r2", "text": "一级故障：(系统宕机)立即电话支持",
                "technical_clause": True, "status": "confirmed", "section_kind": "scoring",
            },
            "r3": {
                "id": "r3", "text": "每月巡检数据库并出具报告",
                "technical_clause": True, "status": "confirmed", "section_kind": "scoring",
            },
        }
    }
    plan = apply_response_plan(workflow)
    assert plan["validation"]["passed"] is True
    assert workflow["response_tasks"]
    h1 = [item["title"] for item in plan["headings"] if item.get("level") == 1]
    assert "项目理解" not in h1
    assert "评分响应" not in h1
    assert h1 != list(BACKBONE_FRONT) + list(BACKBONE_BACK)
    titles = [item["title"] for item in plan["headings"] if item.get("task_id")]
    assert titles
    assert all("不低于2次" not in title for title in titles)
    assert all("每月巡检数据库并出具报告" not in title for title in titles)


def test_rejection_is_constraint_and_scoring_stays_mount():
    workflow = {
        "requirements": {
            "r1": {
                "id": "r1", "text": "每月巡检数据库并出具报告",
                "technical_clause": True, "status": "confirmed", "section_kind": "scoring",
            },
            "r2": {
                "id": "r2", "text": "出现废标条件时否决其投标",
                "technical_clause": True, "status": "confirmed", "section_kind": "scoring",
                "category": "disqualification",
            },
        }
    }
    plan = apply_response_plan(workflow)
    tasks = list(workflow["response_tasks"].values())
    points = [point for task in tasks for point in task["response_points"]]
    constraints = [item for task in tasks for item in task["constraint_ids"]]
    assert "r2" in constraints
    assert all("废标" not in point for point in points)
    assert workflow["requirements"]["r1"]["clause_role"] == "response_mount"
    assert workflow["requirements"]["r2"]["clause_role"] == "rejection_constraint"
    assert plan["validation"]["passed"] is True


def test_pre_drop_lines_keep_format_and_rejection_out_of_clauses():
    from icg.domain.technical_clause_extract import capture_pre_drop_lines, extract_technical_clauses

    pages = [
        "投标文件格式\n一、项目理解\n1. 总体方案\n废标条件：未按顺序编制的否决其投标\n提供数据库巡检服务",
    ]
    sidecar = capture_pre_drop_lines(pages)
    clauses = extract_technical_clauses(pages)
    assert any("投标文件格式" in line for line in sidecar["format_lines"])
    assert any("一、项目理解" in line for line in sidecar["format_lines"])
    assert any("1. 总体方案" in line for line in sidecar["format_lines"])
    assert any("废标" in line for line in sidecar["rejection_lines"])
    assert all("废标" not in item.text for item in clauses)


def test_format_lock_three_consecutive_numbers():
    locked = detect_format_lock(["1. 项目理解", "2. 总体方案", "3. 实施计划"])
    assert locked == ["项目理解", "总体方案", "实施计划"]


def test_format_lock_two_mixed_children_under_format_heading():
    locked = detect_format_lock(["投标文件格式", "一、项目理解", "1. 总体方案"])
    assert locked == ["项目理解", "总体方案"]


def test_stand_in_tree_is_honest_mount_list_not_theme_buckets():
    from icg.domain.technical_chapter_tree import stand_in_chapter_tree

    tasks = [
        {
            "task_id": "t1", "theme": "运维保障与巡检", "title": "运维保障与巡检",
            "requirement_ids": ["r1"],
            "response_points": ["每月巡检"], "constraint_ids": [], "rejection_requirement_ids": [],
        },
        {
            "task_id": "t2", "theme": "备份恢复与容灾", "title": "备份恢复与容灾",
            "requirement_ids": ["r2"],
            "response_points": ["备份恢复"], "constraint_ids": [], "rejection_requirement_ids": [],
        },
    ]
    reqs = {
        "r1": {"id": "r1", "text": "每月巡检数据库并出具报告", "section_kind": "scoring", "technical_clause": True},
        "r2": {"id": "r2", "text": "提供备份恢复与容灾切换", "section_kind": "scoring", "technical_clause": True},
    }
    nodes = stand_in_chapter_tree(tasks, reqs)
    titles = [item["title"] for item in nodes]
    assert "项目理解" not in titles
    assert titles != list(BACKBONE_FRONT) + list(BACKBONE_BACK)
    assert "运维保障与巡检" in titles
    assert "备份恢复与容灾" in titles
    assert any(node.get("task_id") or node.get("requirement_ids") for node in nodes)


def test_format_order_is_soft_reference_in_tree_prompt():
    from icg.domain import technical_chapter_tree as tree

    class Capture:
        is_real_model = True
        is_local = True
        base_url = "http://127.0.0.1:11434/v1"

        def suggest(self, system, user):
            self.system = system
            self.user = user
            return "[]"

    model = Capture()
    tasks = [{
        "task_id": "t1", "theme": "巡检", "requirement_ids": ["r1"],
        "response_points": ["每月巡检"], "constraint_ids": [], "rejection_requirement_ids": [],
    }]
    reqs = {"r1": {"id": "r1", "text": "每月巡检", "section_kind": "scoring", "technical_clause": True}}
    workflow = {"technical_sidecars": {"format_lines": ["1. 项目理解", "2. 总体方案", "3. 实施计划"]}}
    tree.compose_tree_with_model(tasks, reqs, workflow, model)
    assert "仅参考" in model.user
    assert "须包含" not in model.system
    assert "保持相对顺序" not in model.system


def test_format_lock_order_phrase():
    locked = detect_format_lock(["应按以下顺序编制", "一、项目理解", "二、总体方案"])
    assert locked == ["项目理解", "总体方案"]


def test_tree_rejects_same_title_personnel_and_duplicate_mount():
    headings = [
        {"level": 1, "number": "1", "title": "备份恢复与容灾方案", "requirement_ids": ["a", "a"], "score_refs": []},
        {"level": 2, "number": "1.1", "title": "备份恢复与容灾方案", "requirement_ids": [], "score_refs": []},
        {"level": 1, "number": "2", "title": "人员配置", "requirement_ids": [], "score_refs": []},
    ]
    issues = tree_issues(headings, [{"id": "a", "section_kind": "scoring", "status": "confirmed"}], [])
    assert any("同名嵌套" in item for item in issues)
    assert any("人员或商务标题" in item for item in issues)
    assert any("重复挂载" in item for item in issues)


def test_validate_plan_flags_unmapped():
    reqs = [{"id": "a", "technical_clause": True, "status": "confirmed"}]
    tasks = [{"task_id": "t1", "requirement_ids": [], "rejection_requirement_ids": []}]
    headings = [{"task_id": "t1", "title": "x"}]
    result = validate_plan(reqs, tasks, headings)
    assert result["passed"] is False
    assert result["unmapped_requirement_ids"] == ["a"]
