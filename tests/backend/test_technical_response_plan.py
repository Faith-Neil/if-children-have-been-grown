# 为什么有这个文件：核对两层矩阵、主题目录短标题与计划校验。
from __future__ import annotations

from icg.domain.technical_chapter_tree import (
    BACKBONE_BACK,
    BACKBONE_FRONT,
    build_chapter_tree,
    detect_format_lock,
    tree_issues,
)
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


def test_model_tree_survives_unindexed_score_soft_issue():
    import json
    from icg.domain.technical_chapter_tree import build_chapter_tree

    class Local:
        is_real_model = True
        is_local = True
        base_url = "http://127.0.0.1:11434"

        def suggest(self, system, user):
            return json.dumps([
                {"level": 1, "title": "运维保障与巡检", "mount_ids": ["m1"]},
            ], ensure_ascii=False)

    tasks = [{
        "task_id": "t1", "theme": "巡检", "title": "巡检",
        "requirement_ids": ["r1"],
        "response_points": ["每月巡检"], "constraint_ids": [], "rejection_requirement_ids": [],
    }]
    workflow = {
        "requirements": {
            "r1": {
                "id": "r1", "text": "每月巡检", "section_kind": "scoring",
                "technical_clause": True, "status": "confirmed",
            },
            "r2": {
                "id": "r2", "text": "故障两小时内恢复", "section_kind": "scoring",
                "technical_clause": True, "status": "confirmed",
            },
        }
    }
    headings, _rewritten = build_chapter_tree(tasks, workflow, model=Local())
    titles = [item["title"] for item in headings]
    assert "运维保障与巡检" in titles
    assert not any(str(title).startswith("规范") for title in titles)


def _mount_task():
    tasks = [{
        "task_id": "t1", "theme": "巡检", "title": "巡检",
        "requirement_ids": ["r1"],
        "response_points": ["每月巡检"], "constraint_ids": [], "rejection_requirement_ids": [],
    }]
    workflow = {
        "requirements": {
            "r1": {
                "id": "r1", "text": "每月巡检", "section_kind": "scoring",
                "technical_clause": True, "status": "confirmed",
            },
        }
    }
    return tasks, workflow


def test_tree_model_timeout_labels_rule_fallback():
    from icg.infra.openai_model import RetryableModelError

    class Boom:
        is_real_model = True
        is_local = True
        base_url = "http://127.0.0.1:11434"

        def suggest(self, system, user):
            raise RetryableModelError("timeout")

    tasks, workflow = _mount_task()
    headings, _rewritten = build_chapter_tree(tasks, workflow, model=Boom())
    assert headings
    assert workflow["outline_source"] == "rule_fallback"
    assert workflow["tree_model_failed"] is True


def test_tree_model_success_labels_model_source():
    import json

    class Local:
        is_real_model = True
        is_local = True
        base_url = "http://127.0.0.1:11434"

        def suggest(self, system, user):
            return json.dumps([
                {"level": 1, "title": "运维保障与巡检", "mount_ids": ["m1"]},
            ], ensure_ascii=False)

    tasks, workflow = _mount_task()
    headings, _rewritten = build_chapter_tree(tasks, workflow, model=Local())
    assert any(item["title"] == "运维保障与巡检" for item in headings)
    assert workflow["outline_source"] == "model"
    assert workflow["tree_model_failed"] is False


def test_tree_without_model_is_rule_not_a_failure():
    tasks, workflow = _mount_task()
    headings, _rewritten = build_chapter_tree(tasks, workflow, model=None)
    assert headings
    assert workflow["outline_source"] == "rule"
    assert workflow["tree_model_failed"] is False


def test_stand_in_never_uses_spec_number_as_chapter_title():
    from icg.domain.technical_chapter_tree import stand_in_chapter_tree

    tasks = [{
        "task_id": "t1", "theme": "规范 10", "title": "规范 10方案",
        "requirement_ids": ["r1"],
        "response_points": ["7x24"], "constraint_ids": [], "rejection_requirement_ids": [],
    }]
    reqs = {
        "r1": {
            "id": "r1", "text": "须承诺提供7*24小时在线及15分钟响应服务",
            "section_kind": "spec", "section_path": ["10"], "technical_clause": True,
        },
    }
    titles = [item["title"] for item in stand_in_chapter_tree(tasks, reqs)]
    assert titles
    assert not any(str(title).startswith("规范") for title in titles)
    assert not any("方案方案" in str(title) for title in titles)


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
        {"level": 1, "number": "3", "title": "规范 2方案", "requirement_ids": [], "score_refs": []},
    ]
    issues = tree_issues(headings, [{"id": "a", "section_kind": "scoring", "status": "confirmed"}], [])
    assert any("同名嵌套" in item for item in issues)
    assert any("人员或商务标题" in item for item in issues)
    assert any("重复挂载" in item for item in issues)
    assert any("占位拼接标题" in item for item in issues)


def test_validate_plan_flags_unmapped():
    reqs = [{"id": "a", "technical_clause": True, "status": "confirmed"}]
    tasks = [{"task_id": "t1", "requirement_ids": [], "rejection_requirement_ids": []}]
    headings = [{"task_id": "t1", "title": "x"}]
    result = validate_plan(reqs, tasks, headings)
    assert result["passed"] is False
    assert result["unmapped_requirement_ids"] == ["a"]


def test_model_title_equal_to_long_clause_is_not_the_outline_title():
    import json
    from icg.domain.technical_chapter_tree import compose_tree_with_model

    clause = "投标人须承诺提供数据库每月巡检并在两小时内到达现场处理故障且出具书面报告"
    assert len(clause) > 16

    class Local:
        is_real_model = True
        is_local = True
        base_url = "http://127.0.0.1:11434"

        def suggest(self, system, user):
            return json.dumps([
                {"level": 1, "title": clause, "mount_ids": ["m1"]},
            ], ensure_ascii=False)

    tasks = [{
        "task_id": "t1", "theme": "运维保障与巡检", "title": "运维保障与巡检",
        "requirement_ids": ["r1"],
        "response_points": ["每月巡检"], "constraint_ids": [], "rejection_requirement_ids": [],
    }]
    reqs = {
        "r1": {
            "id": "r1", "text": clause, "extracted_summary": clause,
            "section_kind": "scoring", "technical_clause": True, "status": "confirmed",
        },
    }
    nodes = compose_tree_with_model(tasks, reqs, {}, Local())
    titles = [node["title"] for node in nodes or []]
    assert "运维保障与巡检" in titles
    assert all(title == "项目理解" or (clause not in title and not clause.startswith(title)) for title in titles)


def test_model_title_that_starts_a_long_clause_is_not_left_as_the_heading():
    import json
    from icg.domain.technical_chapter_tree import compose_tree_with_model

    clause = "数据库每月巡检并在故障发生后两小时内到达现场处理且提交书面记录"
    prefix = clause[:20]

    class Local:
        is_real_model = True
        is_local = True
        base_url = "http://127.0.0.1:11434"

        def suggest(self, system, user):
            return json.dumps([
                {"level": 1, "title": prefix, "mount_ids": ["m1"]},
            ], ensure_ascii=False)

    tasks = [{
        "task_id": "t1", "theme": "规范 10", "title": "规范 10",
        "requirement_ids": ["r1"],
        "response_points": ["每月巡检"], "constraint_ids": [], "rejection_requirement_ids": [],
    }]
    reqs = {
        "r1": {
            "id": "r1", "text": clause, "extracted_summary": clause,
            "section_kind": "spec", "technical_clause": True, "status": "confirmed",
        },
    }
    nodes = compose_tree_with_model(tasks, reqs, {}, Local())
    titles = [node["title"] for node in nodes or []]
    assert titles
    assert prefix not in titles
    assert all(not str(title).startswith("规范") for title in titles)
    assert all(clause not in title and not clause.startswith(title) for title in titles)


def test_bid_packaging_is_constraint_and_not_a_tree_mount():
    from icg.domain.technical_chapter_tree import summarize_points
    from icg.domain.technical_clause_role import assign_clause_role

    packaging = "投标人注册资金不低于1000万元并提交社保缴纳证明"
    row = {"id": "pack", "text": packaging, "technical_clause": True, "status": "confirmed"}
    assert assign_clause_role(row) == "rejection_constraint"
    assert assign_clause_role({"id": "old", "text": "出现废标条件时否决其投标"}) == "rejection_constraint"
    tasks = [{
        "task_id": "t1",
        "theme": "运维保障与巡检",
        "requirement_ids": ["pack", "svc"],
        "response_points": ["每月巡检数据库并出具报告"],
        "constraint_ids": [],
        "rejection_requirement_ids": [],
    }]
    reqs = {
        "pack": row,
        "svc": {
            "id": "svc", "text": "每月巡检数据库并出具报告",
            "technical_clause": True, "status": "confirmed", "section_kind": "scoring",
        },
    }
    points = summarize_points(tasks, reqs)
    assert [item["id"] for item in points] == ["svc"]
    assert all("注册资金" not in item["point"] for item in points)


def test_stand_in_keeps_requirement_ids_when_title_would_be_personnel():
    from icg.domain.technical_chapter_tree import stand_in_chapter_tree

    tasks = [{
        "task_id": "t1", "theme": "人员配置", "title": "人员配置",
        "requirement_ids": ["r1"], "response_points": ["每月巡检数据库并出具报告"],
        "constraint_ids": [], "rejection_requirement_ids": [],
    }]
    reqs = {
        "r1": {
            "id": "r1", "text": "每月巡检数据库并出具报告",
            "section_kind": "scoring", "technical_clause": True,
        },
    }
    nodes = stand_in_chapter_tree(tasks, reqs)
    from icg.domain.technical_chapter_tree import _finish_tree
    _, rewritten = _finish_tree(nodes)
    mapped = {rid for task in rewritten for rid in (task.get("requirement_ids") or [])}
    assert "r1" in mapped
    assert all("人员" not in str(node.get("title") or "") for node in nodes)


def test_stand_in_parks_constraint_only_tasks_so_ids_stay_mapped():
    from icg.domain.technical_chapter_tree import _finish_tree, stand_in_chapter_tree

    tasks = [
        {
            "task_id": "t1", "theme": "运维保障与巡检", "title": "运维保障与巡检",
            "requirement_ids": ["r1"], "response_points": ["每月巡检"],
            "constraint_ids": [], "rejection_requirement_ids": [],
        },
        {
            "task_id": "t2", "theme": "综合技术响应", "title": "注册资金约束",
            "requirement_ids": ["r2"], "response_points": [],
            "constraint_ids": ["r2"], "rejection_requirement_ids": [],
        },
    ]
    reqs = {
        "r1": {"id": "r1", "text": "每月巡检", "section_kind": "scoring", "technical_clause": True},
        "r2": {
            "id": "r2", "text": "注册资金不少于五百万元人民币",
            "section_kind": "scoring", "technical_clause": True, "category": "disqualification",
        },
    }
    nodes = stand_in_chapter_tree(tasks, reqs)
    _, rewritten = _finish_tree(nodes)
    mapped = {
        rid
        for task in rewritten
        for rid in (
            *(task.get("requirement_ids") or []),
            *(task.get("constraint_ids") or []),
        )
    }
    assert mapped >= {"r1", "r2"}


def test_apply_response_plan_keeps_themes_when_validation_misses():
    import json

    class Spy:
        is_real_model = True
        is_local = True
        base_url = "http://127.0.0.1:11434"

        def __init__(self):
            self.calls = 0

        def suggest(self, system, user):
            self.calls += 1
            return json.dumps([
                {"level": 1, "title": "人员配置", "mount_ids": ["m1"]},
            ], ensure_ascii=False)

    workflow = {
        "requirements": {
            "r1": {
                "id": "r1", "text": "每月巡检数据库并出具报告",
                "technical_clause": True, "status": "confirmed", "section_kind": "scoring",
            },
            "r2": {
                "id": "r2", "text": "拟派项目人员不少于三名",
                "technical_clause": True, "status": "confirmed", "section_kind": "scoring",
            },
        }
    }
    spy = Spy()
    plan = apply_response_plan(workflow, model=spy)
    themes = [task.get("theme") for task in plan["tasks"]]
    assert themes
    assert all(themes)
    assert "" not in themes
    assert "运维保障与巡检" in themes
    assert spy.calls == 1


def test_tree_alias_parse_keeps_real_ids_from_messy_json():
    """昆明目录回复的围栏、注释、null 和截断不得把整树打回规则替身。"""
    from icg.domain.technical_chapter_tree import compose_tree_with_model

    real_id = "req-" + ("a" * 32)
    other_id = "req-" + ("b" * 32)
    fixture = """```json
[
  {
    "level": 1,
    "title": "第一章 现场与远程支持",
    "mount_ids": null
  },
  {
    "level": 2,
    "title": "第一节 巡检服务方案",
    "mount_ids": [
      "m1" // truncated req note
    ]
  },
  {
    "level": 3,
    "title": "1.1.1 核心保障方案",
    "mount_ids": []
  },
  {
    "level": 2,
    "title": "第二节 截断未闭合",
    "mount_ids": ["m2"
"""

    class Local:
        is_real_model = True
        is_local = True
        base_url = "http://127.0.0.1:11434"

        def suggest(self, system, user):
            self.system = system
            self.user = user
            return fixture

    tasks = [{
        "task_id": "t1",
        "theme": "运维保障与巡检",
        "title": "运维保障与巡检",
        "requirement_ids": [real_id, other_id],
        "response_points": ["每月巡检"],
        "constraint_ids": [],
        "rejection_requirement_ids": [],
    }]
    reqs = {
        real_id: {
            "id": real_id,
            "text": "每月巡检数据库并出具报告",
            "section_kind": "scoring",
            "technical_clause": True,
            "status": "confirmed",
        },
        other_id: {
            "id": other_id,
            "text": "提供现场到达支持",
            "section_kind": "spec",
            "technical_clause": True,
            "status": "confirmed",
        },
    }
    model = Local()
    nodes = compose_tree_with_model(tasks, reqs, {}, model)
    assert nodes
    titles = [node["title"] for node in nodes]
    assert "现场与远程支持" in titles
    assert "巡检服务方案" in titles
    assert "核心保障方案" in titles
    assert "1 核心保障方案" not in titles
    assert "截断未闭合" not in titles
    assert all(not str(title).startswith("第") for title in titles)
    leaf = next(node for node in nodes if node["title"] == "巡检服务方案")
    assert real_id in (leaf.get("requirement_ids") or [])
    assert other_id not in (leaf.get("requirement_ids") or [])
    parked = next(node for node in nodes if other_id in (node.get("requirement_ids") or []))
    assert parked["title"] == "总体方案"
    assert real_id not in model.user
    assert other_id not in model.user
    assert "m1\t" in model.user
    assert "m2\t" in model.user


KUNMING5_TREE_ASSISTANT = r"""
[
{"level": 1, "title": "服务方案概述与目标", "mount_ids": []},
{"level": 2, "title": "服务背景与建设目标规划", "mount_ids": ["m87","m84","m85"]},
{"level": 2, "title": "实施计划与交付承诺要求", "mount_ids": ["m71","m69","m65"]},
{"level": 2, "title": "技术配置与评分对照说明", "mount_ids": ["m76","m83","m4"], []},
{"level": 2, "title": "实施交付承诺要求", "mount_ids": ["m1", "m2", "m3", ["m2,""m50], ["m9, [m10] "43", "44", "w96", w88, m89"], m92"]},
{"level": 1, "title": "原厂维保与硬件保障体系", "mount_ids": []},
{"level": 2, "title": "原厂授权与资质要求", "mount_ids": ["m11","m12","m16","m29","m80"]},
{"level": 2, "title": "软硬件维保周期标准", "mount_ids": ["m13","w14",""15","m21","m22","m27]},
{"level": 2, "title": "Exadata一体机维保服务规范", "mount_ids": ["m17","m18","m19","m20","m23","m24","m26"]},
{"level": 2, "title": "备件更换与硬件维护机制", "mount_ids": ["m30","m40","w52]}, {level": "DBA运维与巡检管理，"mount_ids": []},
{"level": 1, "title": "DBA运维与巡检保障", "mount_ids": []},
{"level": 2, "title": "驻场人员资质与管理体系", "mount_ids": ["m54","m55","m57,""58","w94"}, {"W0], [63"],
{"level": 1, "title": "系统架构优化与容量规划保障", "mount_ids": []},
{"level": 2, "title": "业务护航与系统方案实施", "mount_ids": ["m68","m70"]},
{"level": 2, "title": "性能调优与关键业务护航", "mount_ids": ['"m72","m73","w86]}, {level: "安全合规与验收培训，"mount_ids": },
{"level": 2, "title": "保密协议与安全规范落实", "mount_ids": ["m109","m110","m11", w112"],
{"level": 2, "title": "验收标准与知识转移流程", "mount_ids": ["m60","m61","m62","w113"]}
]
"""


def test_kunming5_shredded_tree_keeps_titled_levels_and_m_codes():
    from icg.domain.technical_chapter_tree import _parse_tree_payload

    items = _parse_tree_payload(KUNMING5_TREE_ASSISTANT)
    titles = [item["title"] for item in items]
    assert len(items) >= 12
    assert "软硬件维保周期标准" in titles
    assert "保密协议与安全规范落实" in titles
    assert "验收标准与知识转移流程" in titles
    assert "DBA运维与巡检保障" in titles
    assert "DBA运维与巡检管理，" not in titles
    assert "安全合规与验收培训，" not in titles

    def mounts(title):
        return next(item["mount_ids"] for item in items if item["title"] == title)

    soft = mounts("软硬件维保周期标准")
    assert "m13" in soft and "m21" in soft and "m27" in soft
    assert "w14" not in soft
    assert all(code.startswith("m") and code[1:].isdigit() for code in soft)
    delivered = mounts("实施交付承诺要求")
    assert "m1" in delivered and "m50" in delivered and "m92" in delivered
    assert "w96" not in delivered
    assert "m109" in mounts("保密协议与安全规范落实")
    assert "m60" in mounts("验收标准与知识转移流程")
    assert "w113" not in mounts("验收标准与知识转移流程")


def test_personnel_heading_does_not_discard_the_model_tree():
    import json
    from icg.domain.technical_chapter_tree import build_chapter_tree

    class Local:
        is_real_model = True
        is_local = True
        base_url = "http://127.0.0.1:11434"

        def suggest(self, system, user):
            return json.dumps([
                {"level": 1, "title": "运维保障与巡检", "mount_ids": []},
                {"level": 2, "title": "运维保障与巡检", "mount_ids": ["m1"]},
                {"level": 1, "title": "人员配置", "mount_ids": []},
                {"level": 1, "title": "备份恢复与容灾", "mount_ids": []},
                {"level": 2, "title": "备份切换步骤", "mount_ids": ["m2"]},
            ], ensure_ascii=False)

    tasks = [
        {
            "task_id": "t1", "theme": "运维保障与巡检", "title": "运维保障与巡检",
            "requirement_ids": ["r1"], "response_points": ["每月巡检"],
            "constraint_ids": [], "rejection_requirement_ids": [],
        },
        {
            "task_id": "t2", "theme": "备份恢复与容灾", "title": "备份恢复与容灾",
            "requirement_ids": ["r2"], "response_points": ["备份切换"],
            "constraint_ids": [], "rejection_requirement_ids": [],
        },
    ]
    workflow = {
        "requirements": {
            "r1": {
                "id": "r1", "text": "每月巡检数据库并出具报告",
                "section_kind": "scoring", "technical_clause": True, "status": "confirmed",
            },
            "r2": {
                "id": "r2", "text": "提供备份恢复与容灾切换",
                "section_kind": "scoring", "technical_clause": True, "status": "confirmed",
            },
        }
    }
    headings, _rewritten = build_chapter_tree(tasks, workflow, model=Local())
    titles = [item["title"] for item in headings]
    assert workflow["outline_source"] == "model"
    assert "运维保障与巡检" in titles
    assert "备份切换步骤" in titles
    assert all("人员" not in title for title in titles)


def test_stand_in_multi_mount_theme_splits_level_two():
    from icg.domain.technical_chapter_tree import stand_in_chapter_tree

    tasks = [{
        "task_id": "t1", "theme": "运维保障与巡检", "title": "运维保障与巡检",
        "requirement_ids": ["r1", "r2"],
        "response_points": ["每月巡检", "故障到场"],
        "constraint_ids": [], "rejection_requirement_ids": [],
    }]
    reqs = {
        "r1": {"id": "r1", "text": "每月巡检", "section_kind": "scoring", "technical_clause": True},
        "r2": {"id": "r2", "text": "故障到场", "section_kind": "scoring", "technical_clause": True},
    }
    nodes = stand_in_chapter_tree(tasks, reqs)
    levels = {node["level"] for node in nodes}
    assert 1 in levels and 2 in levels
    host = next(node for node in nodes if node["level"] == 1 and node["title"] == "运维保障与巡检")
    assert not host.get("requirement_ids")
    child_titles = {node["title"] for node in nodes if node["level"] == 2}
    assert "每月巡检" in child_titles
    assert "故障到场" in child_titles
    mapped = {rid for node in nodes for rid in (node.get("requirement_ids") or [])}
    assert mapped == {"r1", "r2"}


def test_flat_model_chapters_become_theme_hosts_with_children():
    import json
    from icg.domain.technical_chapter_tree import TREE_SYSTEM, build_chapter_tree

    class Local:
        is_real_model = True
        is_local = True
        base_url = "http://127.0.0.1:11434"

        def suggest(self, system, user):
            return json.dumps([
                {"level": 1, "title": "月度巡检安排", "mount_ids": ["m1"]},
                {"level": 1, "title": "故障到场处理", "mount_ids": ["m2"]},
                {"level": 1, "title": "备份切换步骤", "mount_ids": ["m3"]},
                {"level": 1, "title": "容灾演练安排", "mount_ids": ["m4"]},
            ], ensure_ascii=False)

    tasks = [
        {
            "task_id": "t1", "theme": "运维保障与巡检", "title": "运维保障与巡检",
            "requirement_ids": ["r1", "r2"], "response_points": ["每月巡检", "故障到场"],
            "constraint_ids": [], "rejection_requirement_ids": [],
        },
        {
            "task_id": "t2", "theme": "备份恢复与容灾", "title": "备份恢复与容灾",
            "requirement_ids": ["r3", "r4"], "response_points": ["备份切换", "容灾演练"],
            "constraint_ids": [], "rejection_requirement_ids": [],
        },
    ]
    workflow = {
        "requirements": {
            "r1": {"id": "r1", "text": "每月巡检", "section_kind": "scoring", "technical_clause": True, "status": "confirmed"},
            "r2": {"id": "r2", "text": "故障到场", "section_kind": "scoring", "technical_clause": True, "status": "confirmed"},
            "r3": {"id": "r3", "text": "备份切换", "section_kind": "scoring", "technical_clause": True, "status": "confirmed"},
            "r4": {"id": "r4", "text": "容灾演练", "section_kind": "scoring", "technical_clause": True, "status": "confirmed"},
        }
    }
    headings, _rewritten = build_chapter_tree(tasks, workflow, model=Local())
    titles = [item["title"] for item in headings]
    levels = {item["level"] for item in headings}
    assert 1 in levels and 2 in levels
    assert workflow["outline_source"] == "model"
    assert "运维保障与巡检" in titles
    assert "备份恢复与容灾" in titles
    assert "月度巡检安排" in titles
    assert "容灾演练安排" in titles
    hosts = [item for item in headings if item["title"] in ("运维保障与巡检", "备份恢复与容灾")]
    assert hosts and all(item["level"] == 1 and not item.get("requirement_ids") for item in hosts)
    assert "m12" in TREE_SYSTEM
    assert "一级" in TREE_SYSTEM


def test_partial_theme_mount_keeps_model_tree():
    import json
    from icg.domain.technical_chapter_tree import build_chapter_tree

    class Local:
        is_real_model = True
        is_local = True
        base_url = "http://127.0.0.1:11434"

        def suggest(self, system, user):
            return json.dumps([
                {"level": 1, "title": "运维保障与巡检", "mount_ids": []},
                {"level": 2, "title": "月度巡检安排", "mount_ids": ["m1"]},
                {"level": 1, "title": "备份恢复与容灾", "mount_ids": []},
                {"level": 2, "title": "备份切换步骤", "mount_ids": ["m3"]},
            ], ensure_ascii=False)

    tasks = [
        {
            "task_id": "t1", "theme": "运维保障与巡检", "title": "运维保障与巡检",
            "requirement_ids": ["r1", "r2"], "response_points": ["每月巡检", "故障到场"],
            "constraint_ids": [], "rejection_requirement_ids": [],
        },
        {
            "task_id": "t2", "theme": "备份恢复与容灾", "title": "备份恢复与容灾",
            "requirement_ids": ["r3", "r4"], "response_points": ["备份切换", "容灾演练"],
            "constraint_ids": [], "rejection_requirement_ids": [],
        },
    ]
    workflow = {
        "requirements": {
            "r1": {"id": "r1", "text": "每月巡检", "section_kind": "scoring", "technical_clause": True, "status": "confirmed"},
            "r2": {"id": "r2", "text": "故障到场", "section_kind": "scoring", "technical_clause": True, "status": "confirmed"},
            "r3": {"id": "r3", "text": "备份切换", "section_kind": "scoring", "technical_clause": True, "status": "confirmed"},
            "r4": {"id": "r4", "text": "容灾演练", "section_kind": "scoring", "technical_clause": True, "status": "confirmed"},
        }
    }
    headings, _rewritten = build_chapter_tree(tasks, workflow, model=Local())
    titles = [item["title"] for item in headings]
    assert workflow["outline_source"] == "model"
    assert "月度巡检安排" in titles
    assert "备份切换步骤" in titles
    r1_owners = [item["title"] for item in headings if "r1" in (item.get("requirement_ids") or [])]
    assert r1_owners == ["月度巡检安排"]
    assert any("r2" in (item.get("requirement_ids") or []) for item in headings)


def _long_clauses():
    return {
        "r1": "系统日常巡检应用维护及优化完善并按月提交运行报告",
        "r2": "数据备份恢复检测差错修正及故障后的数据回退步骤",
        "r3": "每年开展一至两次健康巡检并提交优化建议与整改清单",
        "r4": "提供全天远程支持与故障到场并在时限内恢复业务",
    }


def _clause_workflow(texts: dict[str, str]):
    return {
        "requirements": {
            rid: {
                "id": rid,
                "text": text,
                "section_kind": "scoring",
                "technical_clause": True,
                "status": "confirmed",
            }
            for rid, text in texts.items()
        }
    }


def test_single_quoted_tree_payload_stays_model_outline():
    class Local:
        is_real_model = True
        is_local = True
        base_url = "http://127.0.0.1:11434"

        def suggest(self, system, user):
            return (
                "[\n"
                "{'level': 1, 'title': '运维保障方案', 'mount_ids': []},\n"
                "{'level': 2, 'title': '日常巡检服务', 'mount_ids': ['m1', 'm2']},\n"
                "{'level': 1, 'title': '备份恢复方案', 'mount_ids': []},\n"
                "{'level': 2, 'title': '备份演练安排', 'mount_ids': ['m3', 'm4']}\n"
                "]"
            )

    texts = _long_clauses()
    tasks = [{
        "task_id": "t1",
        "theme": "运维保障与巡检",
        "title": "运维保障与巡检",
        "requirement_ids": list(texts),
        "response_points": list(texts.values()),
        "constraint_ids": [],
        "rejection_requirement_ids": [],
    }]
    workflow = _clause_workflow(texts)
    headings, _rewritten = build_chapter_tree(tasks, workflow, model=Local())
    titles = [item["title"] for item in headings]
    assert workflow["outline_source"] == "model"
    assert workflow["tree_model_failed"] is False
    assert "日常巡检服务" in titles
    assert "备份演练安排" in titles
    assert all("…" not in title for title in titles)
    mounted = {rid for item in headings for rid in (item.get("requirement_ids") or [])}
    assert mounted == set(texts)


def test_unusable_tree_payload_does_not_clip_each_clause():
    class Local:
        is_real_model = True
        is_local = True
        base_url = "http://127.0.0.1:11434"

        def suggest(self, system, user):
            return "我先说明目录思路，稍后再给 JSON。"

    texts = _long_clauses()
    tasks = [{
        "task_id": "t1",
        "theme": "运维保障与巡检",
        "title": "运维保障与巡检",
        "requirement_ids": list(texts),
        "response_points": list(texts.values()),
        "constraint_ids": [],
        "rejection_requirement_ids": [],
    }]
    workflow = _clause_workflow(texts)
    headings, _rewritten = build_chapter_tree(tasks, workflow, model=Local())
    titles = [item["title"] for item in headings]
    assert workflow["outline_source"] == "rule_fallback"
    assert all("…" not in title for title in titles)
    assert len(headings) < len(texts)
