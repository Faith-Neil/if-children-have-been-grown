import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend" / "bid-core"))

from icg.domain.technical_deviation_llm import refine_deviation_fallbacks, validate_llm_response
from icg.domain.technical_volume import FALLBACK_DEVIATION_SAMPLE, table_rows


class FakeJsonModel:
    name = "fake-local-qwen"
    is_real_model = True
    is_local = True

    def __init__(self, responses):
        self.responses = responses
        self.calls = []
        self.profiles = []

    def suggest(self, instruction, content, *, profile=None):
        self.calls.append({"instruction": instruction, "content": content})
        self.profiles.append(profile)
        return json.dumps({"responses": self.responses}, ensure_ascii=False)


def _workflow():
    return {
        "global_fact_sheet_snapshot": {
            "client_name": "昆明航空有限公司",
            "project_name": "Oracle数据库一体机软硬件维保和DBA服务",
            "sla_response": "15分钟电话响应；一级故障40分钟到场、24小时修复",
        }
    }


def test_batch_llm_extracts_service_and_obligation_responses_in_one_chapter_call():
    service = "我司完全响应原厂故障硬件免费更换要求，由原厂工程师完成故障诊断、备件调配和更换验证，服务过程纳入月度巡检记录并形成可追溯报告。"
    obligation = "我司完全接受并遵守因人为因素导致故障时承担全部直接经济损失的责任要求，通过操作审批、双人复核和全程审计日志预防风险并闭环追责。"
    model = FakeJsonModel([
        {"id": "r-service", "response": service},
        {"id": "r-obligation", "response": obligation},
    ])
    entries = [
        {"id": "r-service", "clause": "原厂提供故障硬件免费更换服务", "section_key": "s2", "section_number": "2", "section_title": "维保服务方案", "body": "我司提供原厂维保，故障硬件由原厂工程师诊断、更换并验证。"},
        {"id": "r-obligation", "clause": "因乙方人为因素导致的故障，乙方需承担全部直接经济损失", "section_key": "s2", "section_number": "2", "section_title": "维保服务方案", "body": "我司执行操作审批、双人复核和全程审计。"},
    ]
    responses, audit = refine_deviation_fallbacks(model, _workflow(), "2 维保服务方案\n正文", entries, max_workers=2)
    assert responses == {"r-service": service, "r-obligation": obligation}
    assert len(model.calls) == 1  # 同一章多个兜底条款只发起 1 次批量 JSON 调用
    assert audit["calls"] == 1 and audit["accepted"] == 2 and audit["rejected"] == 0
    profile = model.profiles[0]
    assert profile is not None and profile.enable_thinking is False and profile.json_mode is True
    assert not hasattr(profile, "thinking_budget")
    assert "制定专项响应措施" not in responses["r-service"] + responses["r-obligation"]


def test_invalid_or_foreign_llm_response_is_rejected_and_table_falls_back():
    workflow = _workflow()
    foreign = "我司完全接受并遵守相关责任要求，并按照甘肃农信既有做法完成审计闭环、损失追溯、问题整改和后续持续跟踪。"
    ok, reason = validate_llm_response(foreign, workflow)
    assert not ok and reason.startswith("foreign_entity")
    assert not validate_llm_response("我司太短。", workflow)[0]
    assert not validate_llm_response("我司完全接受并遵守责任要求，但通过制定专项响应措施落实审计闭环并按期完成交付记录。", workflow)[0]
    absolute = "我司完全接受并遵守人为因素赔偿责任要求，通过三审三控和审计留痕预防风险，杜绝人为失误并确保责任可追溯。"
    ok, reason = validate_llm_response(absolute, workflow, "正文仅说明三审三控和审计留痕。")
    assert not ok and reason == "unsupported_absolute"

    workflow.update({
        "requirements": {
            "r1": {"id": "r1", "text": "运维管理咨询服务", "technical_clause": True, "source": {"quote": "运维管理咨询服务"}},
        },
        "technical_outline": {"headings": [{"number": "2", "title": "维保服务方案", "task_id": "t1", "requirement_ids": ["r1"]}]},
    })
    content = "2 维保服务方案\n我司提供12个月原厂维保，按季度完成巡检并提交报告。\n"
    invalid_model = FakeJsonModel([{"id": "r1", "response": "我司太短。"}])
    rows = table_rows(dict(FALLBACK_DEVIATION_SAMPLE), workflow, content=content, model=invalid_model)
    assert rows and "制定专项响应措施" in rows[0][2]


def test_valid_llm_response_replaces_generic_fallback_without_foreign_words():
    workflow = _workflow()
    workflow.update({
        "requirements": {
            "r1": {"id": "r1", "text": "运维管理咨询服务", "technical_clause": True, "source": {"quote": "运维管理咨询服务"}},
        },
        "technical_outline": {"headings": [{"number": "2", "title": "维保服务方案", "task_id": "t1", "requirement_ids": ["r1"]}]},
    })
    content = "2 维保服务方案\n我司提供12个月原厂维保，按季度完成巡检并提交报告。\n"
    response = "我司提供运维管理咨询服务，由项目总监组织月度巡检复盘、容量评估和性能优化建议，形成咨询记录、问题闭环清单与改进跟踪报告。"
    model = FakeJsonModel([{"id": "r1", "response": response}])
    rows = table_rows(dict(FALLBACK_DEVIATION_SAMPLE), workflow, content=content, model=model)
    assert rows[0][2] == response
    assert "历史做法" not in rows[0][2]
    assert "甘肃" not in rows[0][2] and "农信" not in rows[0][2]
    assert workflow["technical_deviation_llm_audit"]["accepted"] == 1


def test_partial_rejection_is_not_cached_as_final_result():
    valid = "我司提供运维管理咨询服务，由项目总监组织月度巡检复盘、容量评估和性能优化建议，形成咨询记录、问题闭环清单与改进跟踪报告。"
    model = FakeJsonModel([
        {"id": "r-valid", "response": valid},
        {"id": "r-short", "response": "我司太短。"},
    ])
    entries = [
        {"id": "r-valid", "clause": "运维管理咨询服务", "section_key": "s2", "section_number": "2", "section_title": "维保服务方案", "body": "我司提供月度巡检复盘、容量评估和性能优化建议。"},
        {"id": "r-short", "clause": "提供7×24小时热线服务", "section_key": "s2", "section_number": "2", "section_title": "维保服务方案", "body": "我司提供7×24小时热线和故障诊断。"},
    ]
    workflow = _workflow()
    responses, audit = refine_deviation_fallbacks(model, workflow, "2 维保服务方案\n正文", entries, max_workers=1)
    assert responses == {"r-valid": valid}
    assert audit["accepted"] == 1 and audit["rejected"] == 1
    # 部分失败不能写入“完成态”缓存，否则重跑导出会永久冻结兜底句，失去重试机会。
    assert not workflow.get("technical_deviation_llm_cache")
