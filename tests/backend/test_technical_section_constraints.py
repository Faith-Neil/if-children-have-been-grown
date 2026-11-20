# 为什么有这个文件：核对技术节写作提示怎么分级使用废标和包装条款。
# 它解决什么问题：技术废标留在硬约束里；信用中国、失信和装订否决不进每节废标块。
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
    marker = f"{start}\n"
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
    project = _slice(user, "项目级约束", "本章任务")
    section = _slice(user, "本章硬约束：", "招标原文")
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
            "未按装订要求编制的投标文件将被否决",
        ]}},
    )
    cover = _slice(user, "招标原文", "知识库")
    project = _slice(user, "项目级约束", "本章任务")
    section = _slice(user, "本章硬约束：", "招标原文")
    assert "每月巡检数据库并出具报告" in cover
    assert "装订" not in cover
    assert "失信" not in cover
    assert "未按要求装订" not in user
    assert "正本" not in user
    assert "被列入失信被执行人名单的，否决其投标" not in user
    assert "未按装订要求编制的投标文件将被否决" not in user
    assert "被列入失信被执行人名单的，否决其投标" not in project
    assert "未按装订要求编制的投标文件将被否决" not in project
    assert "装订" not in section
    assert "失信" not in section
    assert "装订" not in project
    assert "失信" not in project


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
    cover = _slice(user, "招标原文", "知识库")
    section = _slice(user, "本章硬约束：", "招标原文")
    assert "每月巡检数据库并出具报告" in cover
    assert "具备信息系统集成资质" not in cover
    assert "具备信息系统集成资质" not in user
    assert "（无）" in section
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
    project = _slice(user, "项目级约束", "本章任务")
    assert project.count("条款1不满足则作废标处理") == 1
    assert "条款8不满足则作废标处理" in project
    assert "条款9不满足则作废标处理" not in project


def test_unclear_line_stays_out_of_the_body_prompt():
    model = _Local()
    vague = "按采购人另行通知办理"
    user = _write(
        model,
        row={"text": "每月巡检数据库并出具报告", "response": "按招标执行", "response_type": "comply"},
        requirements=[{
            "text": "每月巡检数据库并出具报告",
            "extracted_summary": "每月巡检数据库并出具报告",
        }],
        workflow={"technical_sidecars": {"rejection_lines": [vague]}},
    )
    assert vague not in user
    project = _slice(user, "项目级约束", "本章任务")
    assert "（无）" in project


def test_is_bid_packaging_uses_existing_markers():
    from icg.domain.technical_clause_role import assign_clause_role, is_bid_packaging

    assert is_bid_packaging("未按规定装订")
    assert is_bid_packaging("被列入失信名单")
    assert not is_bid_packaging("每月巡检数据库并出具报告")
    assert assign_clause_role({"text": "未按规定装订"}) == "rejection_constraint"
    assert assign_clause_role({"text": "每月巡检数据库并出具报告"}) == "response_mount"


# 各批次信用中国长段互不为子串，去重不会把它们收成一条。
_CREDIT_HEAD = (
    "投标人提供信用中国网站www.creditchina.gov.cn查询结果网页打印件并加盖投标人公章，"
    "查询范围覆盖失信被执行人、企业经营异常名录、重大税收违法案件当事人名单和行政处罚，"
    "列入上述名单或被责令停产停业、吊销许可证或者执照的，否决其投标。"
)
_CREDIT_BODY = "查询页须能看清投标人名称、查询时间和名单状态，缺页或模糊的打印件无效。" * 3
_CREDIT_TAIL = "专属尾注只存在于长截图后半段，不应进入技术节提示。"


def _credit_line(batch: int) -> str:
    return f"{_CREDIT_HEAD}本段批次{batch:02d}单独编号，不得替换。{_CREDIT_BODY}{_CREDIT_TAIL}"


def _rejection_block(user: str) -> str:
    project = _slice(user, "项目级约束", "本章任务")
    section = _slice(user, "本章硬约束：", "招标原文")
    return f"{project}\n{section}"


def test_chongqing_credit_duplicates_stay_out_of_rejection_block():
    """重庆类侧车：信用中国重复段不进废标块，块长不超过 1500，且比全文粘贴至少短 60%。"""
    credits = [_credit_line(batch) for batch in range(1, 13)]
    sidecar = [
        "未按装订要求编制的投标文件将被否决",
        "被列入失信被执行人名单的，否决其投标",
        *credits,
        "一般故障未在2小时内恢复的，作废标处理",
        "技术方案缺项的投标无效",
    ]
    naive = "\n".join(f"- 废标约束：{line}" for line in sidecar)
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
                "text": "具备信息系统集成资质否则否决",
                "extracted_summary": "具备信息系统集成资质否则否决",
                "requirement_type": "qualification",
                "is_rejection_criterion": True,
            },
        ],
        workflow={"technical_sidecars": {"rejection_lines": sidecar}},
    )
    project = _slice(user, "项目级约束", "本章任务")
    section = _slice(user, "本章硬约束：", "招标原文")
    cover = _slice(user, "招标原文", "知识库")
    block = _rejection_block(user)
    assert len(block) <= 1500, f"废标块 {len(block)} 字符，朴素全文 {len(naive)}，user {len(user)}"
    assert len(block) * 5 <= len(naive) * 2, f"废标块 {len(block)} 未比朴素全文 {len(naive)} 短 60%"
    assert "信用中国" not in project
    assert "信用中国" not in section
    assert "专属尾注" not in project
    assert "专属尾注" not in section
    assert "信用中国" not in user
    assert "专属尾注" not in user
    assert "未按装订要求编制的投标文件将被否决" not in user
    assert "被列入失信被执行人名单的，否决其投标" not in user
    assert "一般故障未在2小时内恢复的，作废标处理" in project
    assert "技术方案缺项的投标无效" in project
    assert "关键设备故障超过4小时未恢复作废标处理" in section
    assert "每月巡检数据库并出具报告" in cover
    assert "具备信息系统集成资质否则否决" not in cover
    assert "资质" not in project
    assert model.system.count("废标硬约束必须遵守") == 1


def test_task_linkage_prefers_relevant_project_rejection():
    """任务挂了废标要求时，项目硬约束只留对得上的那条，不把其余技术废标铺进本节。"""
    unrelated = [f"机房指标{i}不满足则作废标处理" for i in range(1, 11)]
    linked = "未提交巡检记录则否决其投标"
    model = _Local()
    user = _write(
        model,
        row={"text": "每月巡检数据库并出具报告", "response": "按招标执行", "response_type": "comply"},
        requirements=[{
            "text": "每月巡检数据库并出具报告",
            "extracted_summary": "每月巡检数据库并出具报告",
        }],
        task={"rejection_requirement_ids": ["rej-inspect"]},
        workflow={
            "requirements": {
                "rej-inspect": {
                    "id": "rej-inspect",
                    "text": linked,
                    "extracted_summary": linked,
                    "is_rejection_criterion": True,
                    "requirement_type": "rejection_item",
                },
            },
            "technical_sidecars": {"rejection_lines": [*unrelated, linked]},
        },
    )
    project = _slice(user, "项目级约束", "本章任务")
    assert linked in project
    assert "机房指标1不满足则作废标处理" not in project
    assert "机房指标8不满足则作废标处理" not in project
    assert "机房指标10不满足则作废标处理" not in project
