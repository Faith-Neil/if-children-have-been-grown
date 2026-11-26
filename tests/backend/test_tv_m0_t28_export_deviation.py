# TV-M0-T28：导出净化、偏离表/追溯表单向提炼、商务网关、故障配额、蓝图卡、截断续写 单元测试
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend", "bid-core"))

from icg.domain.export_sanitizer import sanitize_body, sanitize_markdown, clean_orphan_pipe_lines
from icg.domain.technical_volume import (
    _cell, _content_response, _merge_continuation, _section_weight, _trim_broken_tail, _trim_unfinished_sentence, _unclosed_tail,
    build_section_blueprint, export_parts, find_samples, table_rows,
)
from icg.domain.technical_rag import wants_fault_cases
from icg.domain.technical_constraint_context import is_business_clause
from icg.infra.openai_model import _finish_reason_from_body


# ---------- 导出净化 ----------

def test_sanitizer_strips_internal_markers():
    dirty = "正文[标:req-1]引用[片:doc][证:abc][medium]风险aa10e0521a7966a4d89a3c4d5e6f7a8b尾"
    out = sanitize_body(dirty)
    for token in ("[标:", "[片:", "[证:", "[medium]", "aa10e0521a7966a4d89a3c4d5e6f7a8b"):
        assert token not in out
    assert "正文" in out


def test_sanitizer_strips_duplicate_title():
    out = sanitize_body("数据库每月巡检\n\n实质内容第一句。", title="数据库每月巡检")
    assert out.splitlines()[0].startswith("实质内容")


def test_orphan_pipe_lines_converted_but_tables_kept():
    md = "| a | b |\n| --- | --- |\n| 1 | 2 |\n\n| 半截"
    out = clean_orphan_pipe_lines(md)
    lines = out.splitlines()
    assert lines[0] == "| a | b |"
    assert "⎮" in lines[-1] and "|" not in lines[-1]


# ---------- 截断闭合 ----------

def test_unclosed_detection():
    assert _unclosed_tail("周期：按需执行（变更前")
    assert _unclosed_tail("| 事项 |\n| 未经")
    assert not _unclosed_tail("全部写完。")
    assert not _unclosed_tail("| a |\n| --- |\n| 巡检 |")


def test_merge_continuation_dedupes_overlap():
    merged = _merge_continuation("前文内容ABC", "内容ABC后续写完。")
    assert "内容ABC内容ABC" not in merged
    assert "后续写完" in merged


def test_section_weight_tiers():
    assert _section_weight([{"score": 10, "section_kind": "scoring"}], None) == "core"
    assert _section_weight([{"text": "x"}], {"response_points": []}) == "brief"
    assert _section_weight([{"text": "x"}, {"text": "y"}, {"text": "z"}], {"response_points": ["a", "b", "c"]}) == "normal"


# ---------- 偏离表单向提炼 ----------

def _workflow_with_content():
    content = "1 数据库巡检\n\n我司按 15 分钟响应执行每月深度巡检并提交报告。\n\n2 应急\n"
    heading = {"number": "1", "title": "数据库巡检", "requirement_id": "r1", "task_id": "t1"}
    row = {
        "id": "r1", "response": "历史做法中 30 分钟响应", "response_type": "deviate",
        "category": "mandatory", "text": "故障响应要求", "source": {"page": 12},
    }
    return content, heading, row


def test_deviation_response_from_content_not_history():
    content, heading, row = _workflow_with_content()
    out = _content_response(content, heading, row)
    assert "历史做法" not in out
    assert "30 分钟" not in out
    assert "15 分钟" in out


def test_no_negative_deviation_for_critical():
    content, heading, row = _workflow_with_content()
    sample = {"scope": "technical", "headers": ["偏离"]}
    cell = _cell("偏离", heading, row, sample, content=content)
    assert cell == "无偏离"  # critical 行 deviate 被强制纠正
    note = _cell("说明", heading, row, sample, content=content)
    assert "人工确认" in note


def test_page_backfill():
    content, heading, row = _workflow_with_content()
    assert _cell("页码", heading, row, {"scope": "technical"}, content=content) == "详见第 1 节（排版后填页码）"


def test_column_no_crossfill():
    content, heading, row = _workflow_with_content()
    sample = {"scope": "technical"}
    seq = _cell("序号", heading, row, sample, content=content)
    resp = _cell("响应", heading, row, sample, content=content)
    clause = _cell("条款", heading, row, sample, content=content)
    assert seq == "1"
    assert seq != resp != clause
    assert clause == "故障响应要求"


def test_table_rows_masks_foreign_names():
    workflow = {
        "requirements": {"r1": {
            "id": "r1", "response": "x", "response_type": "comply", "category": "technical", "technical_clause": True,
            "text": "巡检要求", "source": {"page": 3}, "response_origin": "matrix",
        }},
        "technical_outline": {"headings": [{"number": "1", "title": "巡检", "requirement_id": "r1", "task_id": "t1"}]},
        "foreign_entity_names": ["华为"],
    }
    # 正文含串标词应被遮罩
    rows = table_rows({"scope": "technical", "headers": ["序号", "响应"], "mode": "full"}, workflow,
                      content="1 巡检\n\n我司联合华为技术有限公司提供支持服务响应保障。\n\n")
    assert rows, "table_rows empty"
    assert all("华为" not in cell for row in rows for cell in row)


# ---------- 商务网关 ----------

def test_business_clause_detection():
    assert is_business_clause({"text": "投标报价一览表格式要求"})
    assert is_business_clause({"text": "币种必须为人民币"})
    assert is_business_clause({"score_item": "投标报价得分"})
    assert not is_business_clause({"text": "数据库巡检服务 SLA 响应时限 15 分钟"})
    assert not is_business_clause({"text": "质保期 12 个月运维服务"})


# ---------- 故障案例配额 ----------

def test_fault_case_quota():
    assert not wants_fault_cases("数据库每月巡检", ["提交巡检报告"])
    assert wants_fault_cases("典型故障应急预案", [])
    assert wants_fault_cases("沟通机制", [], {"assigned_cases": ["fault_cases"]})


# ---------- 蓝图卡 ----------

def test_blueprint_fields():
    bp = build_section_blueprint(
        {"task_id": "t1", "title": "数据库巡检", "number": "4.1"},
        [{"score": 10, "section_kind": "scoring", "score_item": "巡检方案"}],
        {"task_id": "t1", "response_points": ["每月巡检"]}, "core")
    assert bp["target_words"] == 2600
    assert bp["scoring_hooks"] == ["巡检方案"]
    assert bp["assigned_cases"] == []


def test_comma_and_pause_tail_are_unclosed():
    assert _unclosed_tail("所有承诺，")
    assert _unclosed_tail("服务范围包括巡检、")
    assert _unclosed_tail("响应时限, ")
    assert not _unclosed_tail("所有承诺。")


def test_business_gateway_user_named_terms():
    for text in [
        "不接受联合体投标", "禁止转包与分包", "投标文件份数要求", "报名材料清单",
        "资格条件审查", "投标有效期120日历天", "投标保证金免缴",
    ]:
        assert is_business_clause({"text": text}), text
    assert not is_business_clause({"text": "数据库性能调优与故障应急响应"})


def test_embedded_sample_header_is_detected():
    workflow = {"files": {"f": {"file_role": "tender", "pages": ["\n".join([
        "十、项目详细需求偏离说明表",
        "投 标 人：",
        "序号 | 招标文件项目详细需求偏离说明表条款的序号及内容 | 投标响应内容对应简述 | 偏离说明 | 投标文件对应的页码",
        "…",
    ])]}}}
    samples = find_samples(workflow)
    assert len(samples) == 1
    assert samples[0]["headers"][-1] == "投标文件对应的页码"


def test_fallback_deviation_export_has_standard_five_columns():
    workflow = {
        "files": {"f": {"file_role": "tender", "pages": ["没有偏离样表"]}},
        "requirements": {"r1": {
            "id": "r1", "technical_clause": True, "status": "confirmed", "response_origin": "matrix",
            "text": "每月巡检", "response": "每月巡检一次", "response_type": "comply",
        }},
        "technical_outline": {"headings": [{"level": 1, "number": "1", "title": "巡检", "requirement_id": "r1", "task_id": "t1", "requirement_ids": ["r1"]}]},
    }
    parts = export_parts(workflow, "服务方案", "1 巡检\n\n我司承诺每月巡检一次并提交报告。\n")
    assert "序号" in parts["attachment"] and "招标条款" in parts["attachment"]
    assert "投标响应简述" in parts["attachment"] and "偏离说明" in parts["attachment"]
    assert "投标文件对应章节号" in parts["attachment"]
    assert "每月巡检" in parts["attachment"]


def test_finish_reason_length_is_parsed_and_unfinished_sentence_trimmed():
    assert _finish_reason_from_body({"choices": [{"finish_reason": "length"}]}) == "length"
    trimmed = _trim_unfinished_sentence("第一段已经完整。\n所有承诺，")
    assert trimmed.endswith("。")
    assert not trimmed.endswith(("，", ",", "、"))


def test_long_sample_clause_header_does_not_crossfill_deviation():
    content, heading, row = _workflow_with_content()
    cell = _cell("招标文件项目详细需求偏离说明表条款的序号及内容", heading, row, {"scope": "technical"}, content=content)
    assert cell == "故障响应要求"
    assert cell not in ("无偏离", "正偏离", "负偏离")


def test_digest_rows_intercept_business_before_outline_input():
    from icg.domain.technical_digest import _rows
    workflow = {"requirements": {
        "r1": {"id": "r1", "technical_clause": True, "status": "confirmed", "text": "数据库巡检服务", "section_kind": "service"},
        "r2": {"id": "r2", "technical_clause": True, "status": "confirmed", "text": "不接受联合体投标", "section_kind": "service"},
        "r3": {"id": "r3", "technical_clause": True, "status": "confirmed", "text": "投标有效期120日历天", "section_kind": "service"},
    }}
    rows = _rows(workflow)
    assert [row["id"] for row in rows] == ["r1"]
    assert len(workflow["business_intercepted_requirements"]) == 2


def test_foreign_entity_mask_keeps_sentence_complete():
    from icg.domain.writing_knowledge_prompt import mask_foreign_names
    text = "我司联合华为技术有限公司提供支持，并服务过安康市人民医院。"
    masked = mask_foreign_names(text, ["华为技术有限公司", "安康市人民医院"])
    assert "华为" not in masked and "安康市人民医院" not in masked
    assert "联合相关机构提供支持" in masked
    assert "服务过相关机构" in masked
    assert "签订。" not in masked and "签署的。" not in masked


def test_export_sanitizer_removes_markdown_strong_source():
    from icg.domain.export_sanitizer import sanitize_markdown
    assert "**" not in sanitize_markdown("本项目承诺：**服务期内团队稳定**。")
    assert "服务期内团队稳定" in sanitize_markdown("本项目承诺：**服务期内团队稳定**。")


def test_response_trace_excludes_business_and_masks_history_names():
    from icg.domain.response_trace import build_trace_rows
    class Obj:
        def __init__(self, **kw): self.__dict__.update(kw)
    state = Obj(chapters={}, accounts={}, project_teams={}, library={})
    project = Obj(id="p1", name="本项目")
    workflow = {
        "files": {},
        "technical_rag_audit": [{"task_id": "task-1", "requirement_ids": ["r1"], "history_hits": 1, "material_hits": 1, "top": [{"name": "甘肃农信历史标书.docx", "dataset_kind": "history"}, {"name": "融科产品.docx", "dataset_kind": "materials"}]}],
        "technical_outline": {"headings": [{"number": "1", "title": "巡检", "task_id": "task-1", "requirement_id": "r1", "requirement_ids": ["r1"]}]},
        "requirements": {
            "r1": {"id": "r1", "volume": "technical", "status": "confirmed", "text": "数据库巡检", "category": "technical", "source": {}},
            "r2": {"id": "r2", "volume": "technical", "status": "confirmed", "text": "不接受联合体投标", "category": "technical", "source": {}},
            "r3": {"id": "r3", "volume": "technical", "status": "rejected", "text": "投标有效期120天", "category": "technical", "source": {}},
        },
    }
    rows = build_trace_rows(state, project, workflow, {"technical"})
    assert len(rows) == 1
    assert "联合体" not in str(rows)
    assert "甘肃农信" not in str(rows)
    assert "历史标书参考（已脱敏）" in str(rows)
