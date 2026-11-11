# 为什么有这个文件：核对技术分册以本地模型抽挂载，正则只补漏。
# 它解决什么问题：短行正则读不到业主和服务期，挂载上也没有原文页。

from __future__ import annotations

from icg.domain.technical_clause_extract import apply_technical_extract, extract_technical_clauses
from icg.domain.technical_model_extract import clauses_from_model, extract_with_model, miss_patch
from icg.domain.technical_outline import apply_technical_outline


class _LocalModel:
    is_real_model = True
    is_local = True
    model = "qwen-test"
    base_url = "http://127.0.0.1:11434"

    def suggest(self, system, user):
        assert "读一份招标文件" in system or "JSON" in system
        return """{
          "who": "德阳市人民医院",
          "what": "信息系统运维服务",
          "period": "服务期36个月",
          "sla": "15分钟响应",
          "format_order": ["项目理解", "总体方案"],
          "items": [
            {"role": "response_mount", "text": "数据库巡检", "quote": "提供数据库巡检服务", "kind": "scoring"},
            {"role": "rejection_constraint", "text": "未按格式编制否决", "quote": "未按格式编制的否决其投标", "kind": "spec"}
          ]
        }"""


def test_model_extract_reads_who_and_period_not_only_short_lines():
    pages = [
        "招标人：德阳市人民医院\n采购信息系统运维服务。合同履行期限三十六个日历月。\n"
        "提供数据库巡检服务。\n未按格式编制的否决其投标。"
    ]
    payload = extract_with_model(pages, _LocalModel())
    assert payload["who"] == "德阳市人民医院"
    assert payload["period"] == "服务期36个月"
    texts = [item["text"] for item in payload["items"]]
    assert "数据库巡检" in texts
    roles = {item["text"]: item["role"] for item in payload["items"]}
    assert roles.get("未按格式编制否决") == "rejection_constraint"


def test_regex_only_patches_model_misses():
    model_clauses = clauses_from_model({
        "items": [{"text": "数据库巡检", "quote": "提供数据库巡检服务", "page": 1, "kind": "scoring", "role": "response_mount"}],
    })
    regex = extract_technical_clauses(["提供数据库巡检服务\n故障处理服务\n"])
    patched = miss_patch(regex, model_clauses)
    assert any(item.text == "故障处理" or "故障" in item.text for item in patched)
    assert all(item.extract_source == "regex_patch" for item in patched)
    assert not any("巡检" in item.text for item in patched)


def test_apply_extract_records_model_facts():
    workflow = {"requirements": {}, "technical_sidecars": {"format_lines": [], "rejection_lines": []}}
    apply_technical_extract(workflow, "f1", ["提供数据库巡检服务"], set(), model=_LocalModel())
    assert workflow["technical_facts"]["客户名"] == "德阳市人民医院"
    mounts = [row for row in workflow["requirements"].values() if row.get("extract_source") == "model"]
    assert mounts
    assert mounts[0]["page"] == 1
    assert mounts[0]["source"]["page"] == 1
    assert "未按格式编制" not in {row["text"] for row in workflow["requirements"].values()}
    assert any("否决" in line for line in workflow["technical_sidecars"]["rejection_lines"])
    assert "项目理解" in workflow["technical_sidecars"]["format_lines"]


def test_apply_extract_without_model_stays_on_regex():
    workflow = {"requirements": {}}
    apply_technical_extract(workflow, "f1", ["提供数据库巡检服务\n故障处理服务"], set())
    texts = {row["text"] for row in workflow["requirements"].values()}
    assert any("巡检" in text for text in texts)
    assert any("故障" in text for text in texts)
    assert all(not row.get("extract_source") for row in workflow["requirements"].values())


def test_public_model_does_not_lead_extract():
    class Public:
        is_real_model = True
        is_local = True
        base_url = "https://api.highwayapi.ai/openai"

        def suggest(self, *_args):
            raise AssertionError("公网模型不应读标")

    workflow = {"requirements": {}}
    apply_technical_extract(workflow, "f1", ["提供数据库巡检服务"], set(), model=Public())
    assert "technical_facts" not in workflow
    assert any("巡检" in row["text"] for row in workflow["requirements"].values())


def test_outline_accepts_model_and_drops_it_before_return():
    workflow = {"requirements": {}}
    apply_technical_outline(None, "p", workflow, model=_LocalModel())
    assert "tree_model" not in workflow
