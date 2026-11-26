import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend" / "bid-core"))

from icg.domain.technical_volume import _content_response, complete_clause_text, table_rows
from icg.domain.technical_constraint_context import row_is_non_tech


def test_clause_completion_repairs_broken_edges():
    row = {"text": "acle原厂服务授权函原件", "extracted_summary": "acle原厂服务授权函原件", "source": {"quote": "(2) 我方承诺在收到合作通知书10个工作日内提供Oracle原厂服务授权函原件；"}}
    assert complete_clause_text(row) == "(2) 我方承诺在收到合作通知书10个工作日内提供Oracle原厂服务授权函原件；"
    row = {"text": "服务商为用户提供7*", "source": {"quote": "2、服务商为用户提供7*24小时热线电话，电话响应时间小于15分钟，提供包括服务请求、故障诊断、技术咨询等服务。"}}
    assert "7*24小时" in complete_clause_text(row)


def test_content_response_uses_clause_specific_unit_not_section_first_sentence():
    content = """3 故障响应与应急机制
本项目是章节开篇套话，不能作为所有条款的统一响应。
| 故障场景 | 处置动作 | SLA |
| 数据库实例崩溃 | 启动主备切换预案 | 15分钟内电话响应，40分钟内到场 |
二级故障确认系统仍可运行但性能异常，15分钟内回电话，2小时内到达现场。
"""
    heading = {"number": "3", "title": "故障响应与应急机制"}
    row1 = {"text": "一级故障40分钟到场", "source": {"quote": "一级故障接到服务请求后40分钟内到达现场。"}}
    row2 = {"text": "二级故障2小时到场", "source": {"quote": "二级故障在2小时之内到达现场。"}}
    first = _content_response(content, heading, row1)
    second = _content_response(content, heading, row2)
    assert first != second
    assert "主备切换" in first or "40分钟" in first
    assert "2小时" in second
    assert not first.startswith("我司一、")
    assert "章节开篇套话" not in first + second


def test_process_and_time_responses_are_grammatical():
    content = """3 故障响应与应急机制
故障告警触发 → 告警自动推送 → 值班工程师15分钟内拨通电话 → 修复后提交恢复报告。
15分钟内回电话：确认系统仍可运行但性能异常。
"""
    heading = {"number": "3", "title": "故障响应与应急机制"}
    process = _content_response(content, heading, {"text": "故障告警闭环处理", "source": {}})
    timed = _content_response(content, heading, {"text": "15分钟内回电话", "source": {}})
    assert process.startswith("我司按“故障告警触发")
    assert timed.startswith("我司在15分钟内回电话")


def test_procedure_and_printing_clauses_are_non_technical():
    samples = [
        "投标文件应采用不褪色材料书写或打印",
        "投标文件不得涂改、行间插字或删除",
        "法定代表人或授权代理人须出席开标会议",
        "项目成交结果公示要求",
        "电子文件不一致时按最不利原则处理",
        "未通过评标办法前附表审核的投标无效",
    ]
    assert all(row_is_non_tech({"text": text}) for text in samples)
    assert not row_is_non_tech({"text": "7×24小时应急响应机制"})
    assert not row_is_non_tech({"text": "数据库巡检服务"})


def test_export_sanitizer_t29_residues():
    from icg.domain.export_sanitizer import sanitize_markdown
    sample = """# 服务方案
# 1 总体
本项目第一节保留。
# 2 故障响应与应急机制
本项目针对业主建立体系。
> 注：响应T-01、T-05中标关键条款，满足中“SLA”。
"""
    out = sanitize_markdown(sample)
    assert "> " not in out
    assert "T-01" not in out and "T-05" not in out
    assert "招标文件中标关键条款" not in out
    assert "满足招标文件" in out
    assert "应急体系针对业主建立体系" in out
    assert "\n本项目第一节保留。" in out


def test_scoring_digest_recovers_exact_four_score_items():
    from icg.domain.technical_digest import build_digest
    quote = "2 | 服务方案，合计30分 服务方案全面、合理、可行，加20-30分。 | 30分 | 100分"
    workflow = {
        "requirements": {"r-score": {"id": "r-score", "text": "服务方案", "section_kind": "scoring", "technical_clause": True, "source": {"quote": quote}}},
        "files": {"f1": {"pages": [{"text": "2方案服务评分表\n1 | 昆航DBA服务需求，合计30分 数据库每月巡检，加10分；服务增加2个月及以上，加20分。 | 30分 | 100分\n3.商务资质评分表"}]}},
    }
    digest = build_digest(workflow)
    assert {("服务方案", 30.0), ("昆航DBA服务需求", 30.0)} <= {(x["item"], x["score"]) for x in digest["scoring"]}


def test_fact_sheet_structured_rows_roundtrip():
    from icg.domain.technical_fact_sheet import prompt_fact_sheet_json, update_global_fact_sheet
    state = type("S", (), {"fact_sheets": {}})()
    workflow = {}
    update_global_fact_sheet(state, "p1", workflow, {
        "service_modules": [{"module": "原厂维保", "period": "12个月"}],
        "asset_inventory": [{"database": "Oracle", "count": "66套"}],
        "scoring_rules": [{"item": "昆航DBA服务需求", "score": "30分"}],
    })
    out = prompt_fact_sheet_json({"global_fact_sheet_snapshot": workflow["global_fact_sheet"]})
    assert out["service_modules"][0]["period"] == "12个月"
    assert out["asset_inventory"][0]["count"] == "66套"
    assert out["scoring_rules"][0]["score"] == "30分"
    assert out["current_year"].isdigit()


def test_response_extractor_skips_table_header_and_anchor_mismatch():
    content = """4 应急响应机制
| 故障场景 | 响应动作 | 恢复目标 |
| --- | --- | --- |
| 数据库实例崩溃 | 启动主备切换预案 | 15分钟内电话响应，40分钟内到场 |
二级故障在2小时之内到达现场，检查系统部件，修复系统。
一级故障接到服务请求后40分钟内到达现场。
"""
    heading = {"number": "4", "title": "应急响应机制"}
    row = {"text": "二级故障违约处置", "technical_clause": True, "source": {}}
    response = _content_response(content, heading, row)
    assert "故障场景场景" not in response
    assert "一级" not in response
    assert "2小时" in response


def test_deviation_ineligible_and_clause_key():
    from icg.domain.technical_volume import _deviation_clause_key, _is_deviation_ineligible
    assert _deviation_clause_key("1. 服务商为用户提供7*24小时热线。") == _deviation_clause_key("服务商为用户提供7*24小时热线")
    assert _is_deviation_ineligible({}, "招标人不得泄漏评标活动中应当保密的情况和资料")
    assert _is_deviation_ineligible({}, "目前公司使用数据库整体情况如下表：")
    assert _is_deviation_ineligible({}, "服务方案有描述但无实际落地相关内容，加0-10分。")
    assert _is_deviation_ineligible({}, "重保（时长由重保时限决定）驻场服务3（含）-5次，加10分；")
    assert _is_deviation_ineligible({}, "4）方案服务得分 （满分100分）最终得分为F2×A2")
    assert not _is_deviation_ineligible({}, "数据库每月巡检并提交巡检报告")


def test_export_sanitizer_is_project_fact_neutral_and_scopes_basis_logic():
    from icg.domain.export_sanitizer import sanitize_markdown
    sample = """# 7 保密与合规管理
CVE-2025-XXXX；v$parameter；48小时内完成修复；四级响应；二级故障40分钟到场；三级60分钟响应；15人；近三年真实处理案例。
本项目严格对标《某项目数据中心供应商安全协议书》。
| 合规条款 | 执行措施 | 责任人 | 交付物 |  |
| --- | --- | --- | --- | --- |
| 符合数据中心安全协议 | 每月审计 | 安全管理员 | 审计报告 | [标:abcdef0123456789abcdef0123456789] |

| 序号 | 招标条款 | 投标响应简述 | 偏离说明 | 投标文件对应的页码 |
| --- | --- | --- | --- | --- |
| 31 | 保密 | 我司响应 | 无偏离 | 7 |
"""
    out = sanitize_markdown(sample)
    # 通用净化保留：过期 CVE 模板、v$parameter、表头列义。
    assert "CVE-2025" not in out
    assert "v$parameter" in out
    assert "依据来源" in out
    assert "某项目数据中心供应商安全协议书" in out
    # 业务事实不得在导出层被静默改写。
    assert "48小时内完成修复" in out
    assert "四级响应" in out
    assert "二级故障40分钟到场" in out
    assert "三级60分钟响应" in out
    assert "15人" in out
    assert "近三年真实处理案例" in out
    # 合规表依据逻辑不得触碰偏离表页码列。
    assert "| 31 | 保密 | 我司响应 | 无偏离 | 7 |" in out


def test_response_truncation_uses_complete_sentence_boundary():
    from icg.domain.technical_volume import _shape_response_sentence
    long_text = "我司建立完整响应机制" + "，覆盖执行细节" * 18 + "。后续内容。"
    out = _shape_response_sentence(long_text, "响应机制")
    assert out.endswith(("。", "；"))
    assert "一。" not in out
    assert not out.endswith(("，", "、", "“"))


def test_verifier_dynamic_fact_sheet_conflicts():
    from icg.domain.technical_verifier import verify_sections
    workflow = {"global_fact_sheet_snapshot": {
        "sla_response": "15分钟电话响应，一级故障40分钟到场、24小时修复，二级故障2小时到场，三级故障15分钟内电话响应",
        "asset_inventory": [{"category": "合计", "subtotal": "87套"}],
        "scoring_rules": [{"item": "人员经验", "rule": "近两年数据库问题处理过程证明材料每个0.5分"}],
    }}
    sections = [
        {"key": "1", "body": "DBA工程师（专项） | 15 | 每人负责3套。近三年真实处理案例。"},
        {"key": "9", "body": "项目总监+6人。二级故障40分钟内到场，三级故障60分钟内响应。"},
    ]
    result = verify_sections(workflow, sections)
    warnings = "\n".join(w for values in result["sections"].values() for w in values)
    assert "二级故障到场" in warnings
    assert "三级故障响应" in warnings
    assert "团队人数" in warnings or "团队配置容量冲突" in warnings
    assert "案例年限" in warnings

    clean = verify_sections(workflow, [
        {"key": "1", "body": "项目总监+6人。每名专职工程师负责不超过13套。近两年真实处理案例。"},
        {"key": "9", "body": "二级故障2小时到场，三级故障15分钟内电话响应。"},
    ])
    clean_warnings = "\n".join(w for values in clean["sections"].values() for w in values)
    assert "二级故障到场" not in clean_warnings
    assert "三级故障响应" not in clean_warnings


def test_anchor_rejects_opposite_compensation_and_wrong_patrol_frequency():
    from icg.domain.technical_volume import _anchor_mismatch
    assert _anchor_mismatch("因乙方人为因素导致的故障需承担赔偿责任", "我司对于非人为损坏的硬件故障提供免费更换服务")
    assert _anchor_mismatch("提供数据库巡检服务（每季度）", "我司数据库巡检服务按月执行")
    assert not _anchor_mismatch("提供数据库巡检服务（每季度）", "我司承诺每季度完成一次系统巡检并出具报告")
    assert _anchor_mismatch("原厂提供每周7天，每天24小时电话（8008100366）技术支持服务", "15分钟内电话响应，同时启动应急流程")
    assert _anchor_mismatch("运维管理咨询服务", "我司所有操作均通过平台进行自动化调度与日志归档")
    assert not _anchor_mismatch("二级故障15分钟内回电话，2小时之内到达现场", "二级故障15分钟回电，2小时内到场")
