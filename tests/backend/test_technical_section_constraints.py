# 为什么有这个文件：核对技术节写作提示怎么使用废标和包装条款。
# 它解决什么问题：侧车里的废标必须成为硬约束，包装条款不能留在必须覆盖里。
from __future__ import annotations


_BODY = (
    "针对「运维保障与巡检」按招标要求写巡检步骤，每月一次并留下运行记录。"
    "过程记录供验收核对。"
)


class _Local:
    is_real_model = True
    is_local = True
    base_url = "http://127.0.0.1:9"

    def __init__(self):
        self.system = ""
        self.user = ""

    def suggest(self, system, user):
        self.system = system
        self.user = user
        return _BODY


def _slice(prompt: str, start: str, end: str) -> str:
    marker = f"\n{start}\n"
    assert marker in prompt
    body = prompt.split(marker, 1)[1]
    return body.split(f"\n{end}", 1)[0]


def _write(model, **kwargs):
    from icg.domain.technical_volume import produce_section

    produce_section("运维保障与巡检", kwargs.pop("row"), model, **kwargs)
    return model.user


def test_sidecar_rejection_lines_are_prompt_hard_constraints():
    model = _Local()
    user = _write(
        model,
        row={"text": "每月巡检数据库并出具报告", "response": "按招标执行", "response_type": "comply"},
        requirements=[
            {
                "text": "每月巡检数据库并出具报告",
                "extracted_summary": "每月巡检数据库并出具报告",
                "risk_level": "high",
            },
            {
                "text": "关键设备故障超过4小时未恢复作废标处理",
                "extracted_summary": "关键设备故障超过4小时未恢复作废标处理",
                "is_rejection_criterion": True,
                "requirement_type": "rejection_item",
            },
            {
                "text": "未覆盖监控点位的否决其投标",
                "extracted_summary": "未覆盖监控点位的否决其投标",
                "clause_role": "rejection_constraint",
                "is_rejection_criterion": False,
                "requirement_type": "other_constraint",
            },
        ],
        workflow={"technical_sidecars": {"rejection_lines": [
            "一般故障未在2小时内恢复的，作废标处理",
            "技术方案缺项的投标无效",
            "未提交巡检记录则否决其投标",
            "废标条件：未提交巡检记录则否决其投标",
        ]}},
    )
    project = _slice(user, "项目废标硬约束：", "本章废标硬约束：")
    section = _slice(user, "本章废标硬约束：", "包装风险提示：")
    assert "一般故障未在2小时内恢复的，作废标处理" in project
    assert "技术方案缺项的投标无效" in project
    assert user.count("未提交巡检记录则否决其投标") == 1
    assert "关键设备故障超过4小时未恢复作废标处理" in section
    assert "未覆盖监控点位的否决其投标" in section
    assert "废标硬约束必须遵守" in model.system
    assert "不得改写成能力表述" in model.system


def test_packaging_rows_are_risk_tips_not_must_cover():
    model = _Local()
    user = _write(
        model,
        row={"text": "每月巡检数据库并出具报告", "response": "按招标执行", "response_type": "comply"},
        requirements=[
            {
                "text": "每月巡检数据库并出具报告",
                "extracted_summary": "每月巡检数据库并出具报告",
                "risk_level": "high",
            },
            {
                "text": "投标文件未按要求装订",
                "extracted_summary": "未按要求装订",
                "clause_role": "rejection_constraint",
                "is_rejection_criterion": False,
                "requirement_type": "other_constraint",
            },
        ],
        workflow={"technical_sidecars": {"rejection_lines": [
            "被列入失信被执行人名单的，否决其投标",
            "正本一份、副本四份",
        ]}},
    )
    cover = _slice(user, "必须覆盖的招标要求：", "响应要点：")
    project = _slice(user, "项目废标硬约束：", "本章废标硬约束：")
    section = _slice(user, "本章废标硬约束：", "包装风险提示：")
    tips = _slice(user, "包装风险提示：", "偏离口径：")
    assert "每月巡检数据库并出具报告" in cover
    assert "装订" not in cover
    assert "未按要求装订" in tips
    assert "失信" in tips
    assert "正本" in tips
    assert "失信" not in project
    assert "装订" not in section
    assert "失信" not in section


def test_empty_sidecar_states_no_section_rejection():
    model = _Local()
    user = _write(
        model,
        row={"text": "每月巡检数据库并出具报告", "response": "按招标执行", "response_type": "comply"},
        requirements=[
            {
                "text": "每月巡检数据库并出具报告",
                "extracted_summary": "每月巡检数据库并出具报告",
            },
            {
                "text": "具备信息系统集成资质",
                "extracted_summary": "具备信息系统集成资质",
                "requirement_type": "qualification",
                "is_rejection_criterion": True,
                "clause_role": "response_mount",
            },
        ],
        workflow={"technical_sidecars": {"format_lines": [], "rejection_lines": []}},
    )
    cover = _slice(user, "必须覆盖的招标要求：", "响应要点：")
    section = _slice(user, "本章废标硬约束：", "包装风险提示：")
    assert "每月巡检数据库并出具报告" in cover
    assert "具备信息系统集成资质" in cover
    assert "（无技术类废标）" in section
    assert "废标约束：" not in section


def test_project_rejection_lines_are_deduped_then_capped():
    lines = [f"条款{i}不满足则作废标处理" for i in range(1, 9)]
    lines.append("条款1不满足则作废标处理")
    lines.append("条款9不满足则作废标处理")
    model = _Local()
    user = _write(
        model,
        row={"text": "每月巡检数据库并出具报告", "response": "按招标执行", "response_type": "comply"},
        requirements=[{
            "text": "每月巡检数据库并出具报告",
            "extracted_summary": "每月巡检数据库并出具报告",
        }],
        workflow={"technical_sidecars": {"rejection_lines": lines}},
    )
    project = _slice(user, "项目废标硬约束：", "本章废标硬约束：")
    assert project.count("条款1不满足则作废标处理") == 1
    assert "条款8不满足则作废标处理" in project
    assert "条款9不满足则作废标处理" not in project


def test_is_bid_packaging_uses_existing_markers():
    from icg.domain.technical_clause_role import assign_clause_role, is_bid_packaging

    assert is_bid_packaging("未按规定装订")
    assert is_bid_packaging("被列入失信名单")
    assert not is_bid_packaging("每月巡检数据库并出具报告")
    assert assign_clause_role({"text": "未按规定装订"}) == "rejection_constraint"
    assert assign_clause_role({"text": "每月巡检数据库并出具报告"}) == "response_mount"
