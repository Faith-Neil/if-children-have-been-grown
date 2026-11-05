# 为什么有这个文件：核对两层矩阵、主题目录短标题与计划校验。
from __future__ import annotations

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
    titles = [item["title"] for item in plan["headings"] if item.get("task_id")]
    assert titles
    assert all(len(title) <= 24 for title in titles)
    assert all("不低于2次" not in title for title in titles)


def test_validate_plan_flags_unmapped():
    reqs = [{"id": "a", "technical_clause": True, "status": "confirmed"}]
    tasks = [{"task_id": "t1", "requirement_ids": [], "rejection_requirement_ids": []}]
    headings = [{"task_id": "t1", "title": "x"}]
    result = validate_plan(reqs, tasks, headings)
    assert result["passed"] is False
    assert result["unmapped_requirement_ids"] == ["a"]
