# 为什么有这个文件：验证 TV-M0-T26 五段隔离 Prompt、废标分级注入、一级章间串行摘要调度与后置核验器。
from __future__ import annotations

from types import SimpleNamespace

from icg.domain.technical_response_plan import confirm_reasons
from icg.domain.technical_verifier import verify_sections
from icg.domain.technical_volume import write_volume


class _Kb:
    def search(self, company_id, query, *, limit=4, kinds=None):
        return [], ""


class _Model:
    is_real_model = True
    is_local = True
    base_url = "http://127.0.0.1:9"

    def __init__(self):
        self.users: list[str] = []

    def suggest(self, system, user):
        self.users.append(user)
        return "本项目承诺每日自动巡检核心数据库并留存巡检记录，重大故障30分钟内响应到场处置完毕。"


def _state():
    return SimpleNamespace(
        chapters={"c1": SimpleNamespace(id="c1", content="", revision=1)},
        projects={"p": SimpleNamespace(id="p", name="合成项目", company_id="alpha")},
    )


def _workflow() -> dict:
    return {
        "plan_confirmed": True,
        "global_fact_sheet_snapshot": {
            "project_name": "政务云核心库维保项目", "client_name": "星河大数据局",
            "service_period": "3年", "sla_response": "30分钟", "frozen_at": "2026-01-01T00:00:00",
        },
        "technical_sidecars": {"rejection_lines": [
            "信用中国失信被执行人否决投标",
            "投标文件装订不符合要求否决投标",
        ]},
        "technical_outline": {
            "chapter_id": "c1",
            "headings": [
                {"level": 1, "number": "1", "title": "总体方案"},
                {"level": 2, "number": "1.1", "title": "日常巡检",
                 "task_id": "t1", "requirement_id": "r1", "requirement_ids": ["r1"]},
                {"level": 1, "number": "2", "title": "售后保障"},
                {"level": 2, "number": "2.1", "title": "应急响应",
                 "task_id": "t2", "requirement_id": "r2", "requirement_ids": ["r2"]},
            ],
        },
        "requirements": {
            "r1": {"id": "r1", "technical_clause": True, "text": "每日巡检数据库",
                   "status": "confirmed", "section_kind": "scoring"},
            "r2": {"id": "r2", "technical_clause": True, "text": "重大故障30分钟响应",
                   "status": "confirmed", "section_kind": "scoring"},
        },
        "response_tasks": {
            "t1": {"task_id": "t1", "requirement_ids": ["r1"], "response_points": ["每日巡检数据库"]},
            "t2": {"task_id": "t2", "requirement_ids": ["r2"], "response_points": ["重大故障30分钟响应"]},
        },
        "files": {"f1": {"pages": ["本标要求每日巡检数据库，重大故障30分钟内响应，服务期限3年。"]}},
    }


def test_five_part_prompt_chapter_serial_summary_and_no_full_rejection_dump():
    model = _Model()
    workflow = _workflow()
    result = write_volume(_state(), "p", workflow, None, model, knowledge_base=_Kb())
    assert result["failed"] == []
    assert len(model.users) == 2

    first, second = model.users
    # 五段结构：写作定位 → 全局项目事实 → 项目级约束 → 本章任务 → 招标原文 → 知识库 → 生成规则
    for label in ("写作定位", "全局项目事实", "项目级约束", "本章任务", "招标原文", "知识库", "生成规则"):
        assert label in first
    positions = [first.index(label) for label in ("写作定位", "全局项目事实", "项目级约束", "本章任务", "招标原文", "知识库", "生成规则")]
    assert positions == sorted(positions)
    # 面包屑路径与相邻章节边界
    assert "当前章节路径：1 总体方案 / 1.1 日常巡检" in first
    assert "下节「应急响应」" in first
    # 全局事实表 JSON 注入
    assert '"client_name": "星河大数据局"' in first
    assert '"sla_response": "30分钟"' in first
    # 资格/包装类废标不再全量灌入每节
    assert "信用中国" not in first
    assert "装订不符合" not in first
    assert "废标清单（全文不得违反）" not in first
    # [待人工补充] 缺口占位规则
    assert "待人工补充" in first

    # 一级章间串行：第二章 prompt 携带第一章 running_summary
    assert "已生成前文关键承诺摘要" in second
    assert "每日自动巡检" in second
    assert workflow["chapter_summaries"].get("1")

    # 后置核验器已跑过全书
    assert workflow["technical_verify"]["checked"] == 2


def test_verifier_flags_foreign_entity_fact_conflict_scoring_gap_and_cross_conflict():
    workflow = {
        "global_fact_sheet_snapshot": {
            "project_name": "测试项目", "client_name": "测试业主",
            "service_period": "3年", "frozen_at": "2026-01-01T00:00:00",
        },
    }
    sections = [
        {
            "key": "s1", "title": "巡检",
            "body": "本项目为安康市人民医院提供维保服务，服务期限5年，每月定期巡检并出具巡检报告记录。",
            "task": {}, "rows": [],
        },
        {
            "key": "s2", "title": "应急",
            "body": "本项目服务期限3年，重大故障30分钟响应。",
            "task": {},
            "rows": [{"section_kind": "scoring", "extracted_summary": "建立三级备品备件库保障机制"}],
        },
    ]
    out = verify_sections(workflow, sections)
    w1, w2 = out["sections"]["s1"], out["sections"]["s2"]
    assert any("安康市人民医院" in w for w in w1)
    assert any("服务期限" in w and "5年" in w for w in w1)
    assert any("跨节口径冲突" in w for w in w1)
    assert any("跨节口径冲突" in w for w in w2)
    assert any("评分点疑似未实质响应" in w for w in w2)
    assert out["summary"]["warned"] == 2


def test_verify_warnings_flow_into_task_and_confirm_reasons():
    model = _Model()
    workflow = _workflow()
    # 让模型输出外项目实体，触发核验器串标警示
    model.suggest = lambda system, user: (
        model.users.append(user) or
        "本项目参照安康市人民医院做法每日巡检数据库并留存巡检记录，重大故障30分钟内响应到场。"
    )
    write_volume(_state(), "p", workflow, None, model, knowledge_base=_Kb())
    task = workflow["response_tasks"]["t1"]
    warnings = task.get("verify_warnings") or []
    assert any("安康市人民医院" in w for w in warnings)
    reasons = confirm_reasons(task, False)
    assert "后置核验待复核" in reasons


def test_verifier_whitelists_ministry_citations_and_negated_contexts():
    from icg.domain.technical_verifier import verify_sections

    workflow = {"global_fact_sheet_snapshot": {}}
    sections = [
        {
            "key": "s1", "title": "标准依据",
            "body": "本方案严格遵循国家税务总局电子档案规范与中国人民银行支付清算标准，符合要求。",
            "task": {}, "rows": [],
        },
        {
            "key": "s2", "title": "防串标自查",
            "body": "经核查本方案未出现安康市人民医院等外项目名称，与既有方案无冲突。",
            "task": {}, "rows": [],
        },
        {
            "key": "s3", "title": "真实串标",
            "body": "参照安康市人民医院运维体系建立每日巡检制度并留存记录。",
            "task": {}, "rows": [],
        },
    ]
    out = verify_sections(workflow, sections)
    assert not any("国家税务总局" in w or "中国人民银行" in w for w in out["sections"]["s1"])
    assert not any("安康市人民医院" in w for w in out["sections"]["s2"])
    assert any("安康市人民医院" in w for w in out["sections"]["s3"])


def test_verifier_unit_aware_extraction_kills_real_machine_false_positives():
    """真机验收样本：驻场句旁的分钟/小时、服务期句旁的7×24小时不得再误报事实冲突。"""
    from icg.domain.technical_verifier import verify_sections

    workflow = {
        "global_fact_sheet_snapshot": {
            "project_name": "星河项目", "client_name": "星河市大数据局",
            "service_period": "12个月",
            "sla_response": "7×24小时值守，重大故障30分钟响应，4小时恢复",
            "on_site_staff": "驻场2人",
            "frozen_at": "2026-01-01T00:00:00",
        },
    }
    sections = [
        {
            "key": "s1", "title": "故障响应",
            # 真机 R2 样本句式：驻场2人 + 10分钟/2小时同句 —— 不得把分钟/小时当驻场人数
            "body": "驻场2人全天候值守，一般故障10分钟响应、2小时到场处理。服务期限12个月，"
                    "服务期内提供7×24小时值守，重大故障30分钟响应，4小时恢复。",
            "task": {}, "rows": [],
        },
        {
            "key": "s2", "title": "巡检服务",
            "body": "服务期限12个月内每月执行巡检。驻场2人按SLA执行30分钟响应机制。",
            "task": {}, "rows": [],
        },
    ]
    out = verify_sections(workflow, sections)
    all_warnings = [w for ws in out["sections"].values() for w in ws]
    # 单位过滤后：分钟/小时不再冒充驻场人数，24小时不再冒充服务期限 → 不应出现事实冲突类误报
    assert not any("驻场人数" in w and "分钟" in w for w in all_warnings), all_warnings
    assert not any("服务期限" in w and "24小时" in w for w in all_warnings), all_warnings
    assert not any("驻场人数" in w and "小时" in w for w in all_warnings), all_warnings


def test_verifier_still_flags_real_unit_consistent_conflicts():
    """单位对齐后的真冲突必须仍然报警：服务期限正文写24个月、事实表12个月。"""
    from icg.domain.technical_verifier import verify_sections

    workflow = {
        "global_fact_sheet_snapshot": {
            "service_period": "12个月", "on_site_staff": "驻场2人",
            "frozen_at": "2026-01-01T00:00:00",
        },
    }
    sections = [
        {
            "key": "s1", "title": "服务承诺",
            "body": "本项目服务期限24个月，驻场5人全程保障。",
            "task": {}, "rows": [],
        },
    ]
    out = verify_sections(workflow, sections)
    warnings = out["sections"]["s1"]
    assert any("服务期限" in w and "24个月" in w for w in warnings)
    assert any("驻场人数" in w and "5人" in w for w in warnings)
