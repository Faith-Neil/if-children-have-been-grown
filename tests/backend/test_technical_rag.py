# 为什么有这个文件：核对技术分册双库名解析、检索 Query 与缺库提示。
# 它解决什么问题：防止再写回 icg-materials 复数旧名或只搜章节标题。

from __future__ import annotations

import os
from types import SimpleNamespace

from icg.domain.knowledge_base import dataset_full_name, dataset_lookup_names, dataset_suffix
from icg.domain.technical_rag import dataset_presence, retrieve_dual, section_query


def test_material_suffix_is_singular_and_configurable(monkeypatch):
    monkeypatch.delenv("ICG_KB_DATASET_MATERIAL", raising=False)
    monkeypatch.delenv("RAGFLOW_DATASET_MATERIAL", raising=False)
    assert dataset_suffix("materials") == "icg-material"
    assert dataset_suffix("history") == "icg-history"
    assert dataset_full_name("alpha", "materials") == "alpha::icg-material"
    assert "alpha::icg-materials" in dataset_lookup_names("alpha", "materials")
    monkeypatch.setenv("ICG_KB_DATASET_MATERIAL", "acme::custom-material")
    assert dataset_suffix("materials") == "custom-material"
    assert dataset_full_name("alpha", "materials") == "alpha::custom-material"


def test_section_query_includes_clause_not_title_only():
    query = section_query("健康检查", {"text": "每月巡检数据库", "response": "按招标执行"})
    assert "健康检查" in query and "每月巡检数据库" in query
    assert "检索目标" in query
    assert query != "健康检查"


def test_dataset_presence_lists_missing_full_names():
    state = SimpleNamespace(service_stores={"kb_index": {"alpha": {"datasets": {"history": {"dataset_id": "h1"}}}}})
    status = dataset_presence(state, "alpha")
    assert status["history"]["configured"] is True
    assert status["material"]["configured"] is False
    assert status["missing"] == ["alpha::icg-material"]
    assert status["ready"] is False


def test_retrieve_dual_audits_both_kinds():
    class Hit:
        def __init__(self, kind, name):
            self.source_id = name
            self.name = name
            self.content = "正文"
            self.score = 0.9
            self.dataset_kind = kind
            self.reference_only = kind == "history"
            self.document_id = "d"
            self.chunk_ids = ["c1"]
            self.cite_tag = f"[片:{name}]"

    class Kb:
        def search(self, company_id, query, *, limit=4, kinds=None):
            kind = next(iter(kinds or {"history"}))
            return [Hit(kind, f"{kind}-doc")], ""

    chunks, audit = retrieve_dual(Kb(), "alpha", "健康检查 巡检")
    assert audit["history_searched"] and audit["material_searched"]
    assert audit["history_hits"] == 1 and audit["material_hits"] == 1
    assert len(chunks) == 2


def test_write_volume_puts_tender_block_before_company():
    from icg.domain.technical_volume import write_volume
    from icg.domain.writing_knowledge_prompt import HISTORY_HEADING, MATERIALS_HEADING, TENDER_HEADING

    class Hit:
        def __init__(self, kind):
            self.source_id = kind
            self.name = kind
            self.content = f"公司{kind}证据"
            self.score = 0.4
            self.dataset_kind = kind
            self.reference_only = kind == "history"
            self.document_id = "d"
            self.chunk_ids = [f"chunk-{kind}"]
            self.cite_tag = f"[片:{kind}]"

    class Kb:
        def search(self, company_id, query, *, limit=4, kinds=None):
            kind = next(iter(kinds or {"history"}))
            return [Hit(kind)], ""

    class Model:
        is_real_model = True
        is_local = True
        base_url = "http://127.0.0.1:9"
        prompts: list[str] = []

        def suggest(self, system, user):
            self.prompts.append(user)
            return (
                "针对「总体方案」按招标要求写数据库巡检，每月一次并留下运行记录。"
                "过程记录供验收核对。"
            )

    chapter = SimpleNamespace(id="c1", content="", revision=1)
    state = SimpleNamespace(
        chapters={"c1": chapter},
        projects={"p": SimpleNamespace(id="p", name="合成项目", company_id="alpha")},
    )
    clause = "每月巡检数据库并出具报告"
    workflow = {
        "plan_confirmed": True,
        "technical_outline": {
            "chapter_id": "c1",
            "headings": [{
                "level": 1, "number": "1", "title": "总体方案",
                "task_id": "t1", "requirement_id": "r1", "requirement_ids": ["r1"],
            }],
        },
        "requirements": {
            "r1": {
                "id": "r1", "technical_clause": True, "text": clause,
                "status": "confirmed", "section_kind": "scoring",
            },
        },
        "response_tasks": {"t1": {"task_id": "t1", "requirement_ids": ["r1"], "response_points": [clause]}},
        "files": {"f1": {"pages": [f"本标要求{clause}"]}},
    }
    model = Model()
    result = write_volume(state, "p", workflow, None, model, knowledge_base=Kb())
    assert result["failed"] == []
    row = workflow["technical_rag_audit"][0]
    assert row["tender_searched"] is True
    assert row["tender_hits"] >= 1
    assert row["tender_dataset"] == "workflow.pages"
    assert row["history_searched"] is True
    assert row["material_searched"] is True
    assert row["history_hits"] == 1
    assert row["material_hits"] == 1
    prompt = model.prompts[0]
    assert prompt.index(TENDER_HEADING) < prompt.index(HISTORY_HEADING)
    assert prompt.index(HISTORY_HEADING) < prompt.index(MATERIALS_HEADING)
    assert "本标要求每月巡检数据库并出具报告" in prompt
    assert "公司history证据" in prompt
    assert "每月巡检数据库并出具报告" in prompt


def test_produce_section_mounts_points_skips_global_sla_and_marks_empty_knowledge():
    from icg.domain.technical_volume import produce_section

    class Model:
        is_real_model = True
        is_local = True
        base_url = "http://127.0.0.1:9"
        prompts: list[str] = []

        def suggest(self, system, user):
            self.prompts.append(user)
            return (
                "针对「备份恢复与容灾方案」按招标要求写备份策略，每日全量备份并留下恢复演练记录，"
                "演练记录供验收核对。"
            )

    model = Model()
    produce_section(
        "备份恢复与容灾方案",
        {
            "text": "每日全量备份", "response": "按招标执行", "response_type": "comply",
            "extracted_summary": "每日全量备份",
        },
        model,
        knowledge="",
        task={"response_points": ["每日全量备份", "7*24小时响应"]},
        requirements=[{
            "extracted_summary": "每日全量备份", "text": "每日全量备份", "risk_level": "high",
        }],
        workflow={"technical_promises": {"响应时限": "7*24小时响应"}},
    )
    prompt = model.prompts[0]
    assert "响应要点" in prompt
    assert "每日全量备份" in prompt
    assert "7*24" not in prompt
    assert "【待确认】" in prompt

    produce_section(
        "运维保障与巡检",
        {"text": "每月巡检", "response": "按招标执行", "response_type": "comply"},
        model,
        knowledge="历史技术方案参考：每月巡检记录模板",
        task={"response_points": ["每月巡检", "7*24小时响应"]},
        requirements=[{"extracted_summary": "每月巡检", "text": "每月巡检"}],
        workflow={"technical_promises": {"响应时限": "7*24小时响应"}},
    )
    later = model.prompts[-1]
    assert "7*24小时响应" in later
    assert "历史技术方案参考：每月巡检记录模板" in later
    assert "无命中" not in later


def _tender_chunk() -> dict:
    return {
        "dataset_kind": "tender",
        "cite_tag": "[标:0fc36992]",
        "name": "本标切片",
        "content": "一般故障，恢复时间不超过2个小时。",
        "chunk_id": "0fc36992",
        "document_id": "doc-tender",
    }


def test_tender_block_is_project_fact_and_missing_capability_is_unconfirmed():
    from icg.domain.writing_knowledge_prompt import format_retrieved_knowledge_prompt_lines

    prompt = "\n".join(format_retrieved_knowledge_prompt_lines([_tender_chunk()]))
    assert "[标:0fc36992]" in prompt
    assert "一般故障，恢复时间不超过2个小时。" in prompt
    assert "项目事实" in prompt
    assert "改写" in prompt
    assert "只陈述" not in prompt
    assert "企业知识检索" not in prompt
    assert "【待确认】" in prompt
    assert "能力" in prompt
    assert "不要写成【待补】" in prompt


def test_company_evidence_omits_capability_gap():
    from icg.domain.writing_knowledge_prompt import format_retrieved_knowledge_prompt_lines

    prompt = "\n".join(format_retrieved_knowledge_prompt_lines([
        _tender_chunk(),
        {
            "dataset_kind": "history",
            "cite_tag": "[片:h1]",
            "content": "我司巡检每月一次并留记录",
            "reference_only": True,
            "chunk_id": "h1",
        },
        {
            "dataset_kind": "materials",
            "cite_tag": "[证:m1]",
            "content": "到场时限2小时见产品说明",
            "chunk_id": "m1",
        },
    ]))
    assert "项目事实" in prompt
    assert "改写" in prompt
    assert "[标:0fc36992]" in prompt
    assert prompt.index("一般故障，恢复时间不超过2个小时。") < prompt.index("我司巡检每月一次并留记录")
    assert prompt.index("我司巡检每月一次并留记录") < prompt.index("到场时限2小时见产品说明")
    assert "【待确认】" not in prompt


def test_section_prompt_forbids_paraphrasing_tender_and_blanket_placeholders():
    from icg.domain.technical_volume import produce_section
    from icg.domain.writing_knowledge_prompt import format_retrieved_knowledge_prompt_lines

    class Model:
        is_real_model = True
        is_local = True
        base_url = "http://127.0.0.1:9"
        system = ""
        user = ""

        def suggest(self, system, user):
            self.system = system
            self.user = user
            return "针对「运维保障与巡检」按既有巡检制度执行，每月一次并留下运行记录。过程记录供验收核对。"

    model = Model()
    knowledge = "\n".join(format_retrieved_knowledge_prompt_lines([_tender_chunk()]))
    produce_section(
        "运维保障与巡检",
        {"text": "日常巡检", "response": "按招标执行", "response_type": "comply"},
        model,
        knowledge=knowledge,
    )
    assert "依据检索块写可追溯句子" not in model.system
    assert "无命中标【待确认】" not in model.system
    assert "其他客户或其他项目名称写成【待补】" not in model.system
    assert "改写" in model.system
    assert "不要写成【待补】" in model.system
    assert "[标:" in model.system
    assert "企业知识检索" not in model.user
    assert "[标:0fc36992]" in model.user
    assert "【待确认】" in model.user
    assert "能力" in model.user

    empty = Model()
    produce_section(
        "运维保障与巡检",
        {"text": "日常巡检", "response": "按招标执行", "response_type": "comply"},
        empty,
        knowledge="",
    )
    assert "企业知识检索" not in empty.user
    assert "【待确认】" in empty.user
    assert "能力" in empty.user


def test_stand_in_does_not_treat_tender_slices_as_company_evidence():
    from icg.domain.technical_volume import produce_section
    from icg.domain.writing_knowledge_prompt import format_retrieved_knowledge_prompt_lines

    class Model:
        is_real_model = False

    knowledge = "\n".join(format_retrieved_knowledge_prompt_lines([_tender_chunk()]))
    text = produce_section(
        "总体方案",
        {"text": "日常巡检", "response": "按招标执行", "response_type": "comply"},
        Model(),
        knowledge=knowledge,
    )
    assert "已参考企业知识库" not in text
    assert "【待确认】" in text


def test_tender_only_retrieval_marks_section_needs_confirm():
    from icg.domain.technical_volume import write_volume

    class Kb:
        def search(self, company_id, query, *, limit=4, kinds=None):
            return [], ""

    class Model:
        is_real_model = True
        is_local = True
        base_url = "http://127.0.0.1:9"
        system = ""
        user = ""

        def suggest(self, system, user):
            self.system = system
            self.user = user
            return "针对「总体方案」按既有巡检制度写步骤，每月一次并留下运行记录。过程记录供验收核对。"

    clause = "每月巡检数据库并出具报告"
    workflow = {
        "plan_confirmed": True,
        "technical_outline": {
            "chapter_id": "c1",
            "headings": [{
                "level": 1, "number": "1", "title": "总体方案",
                "task_id": "t1", "requirement_id": "r1", "requirement_ids": ["r1"],
            }],
        },
        "requirements": {
            "r1": {
                "id": "r1", "technical_clause": True, "text": clause,
                "status": "confirmed", "section_kind": "scoring",
            },
        },
        "response_tasks": {"t1": {"task_id": "t1", "requirement_ids": ["r1"], "response_points": [clause]}},
        "files": {"f1": {"pages": [f"本标要求{clause}。一般故障恢复不超过2小时。"]}},
    }
    model = Model()
    result = write_volume(
        SimpleNamespace(
            chapters={"c1": SimpleNamespace(id="c1", content="", revision=1)},
            projects={"p": SimpleNamespace(id="p", name="合成项目", company_id="alpha")},
        ),
        "p",
        workflow,
        None,
        model,
        knowledge_base=Kb(),
    )
    assert result["failed"] == []
    assert workflow["response_tasks"]["t1"]["response_status"] == "needs_confirm"
    assert workflow["technical_rag_audit"][0]["tender_hits"] >= 1
    assert workflow["technical_rag_audit"][0]["history_hits"] == 0
    assert workflow["technical_rag_audit"][0]["material_hits"] == 0
    assert "企业知识检索" not in model.user
    assert "项目事实" in model.user
    assert "[标:p" in model.user
    assert "【待确认】" in model.user
    assert "改写" in model.system


def test_company_chunks_stay_when_tender_fills_the_window():
    from icg.domain.technical_rag import knowledge_prompt_block, retrieve_for_section

    class Hit:
        def __init__(self, kind):
            self.source_id = kind
            self.name = kind
            self.content = f"公司{kind}证据"
            self.score = 0.4
            self.dataset_kind = kind
            self.reference_only = kind == "history"
            self.document_id = "d"
            self.chunk_ids = [f"chunk-{kind}"]
            self.cite_tag = f"[片:{kind}]"

    class Kb:
        def search(self, company_id, query, *, limit=4, kinds=None):
            kind = next(iter(kinds or {"history"}))
            return [Hit(kind)], ""

    pages = [f"数据库巡检每月一次，第{index}页" for index in range(1, 6)]
    chunks, audit = retrieve_for_section(
        Kb(), "alpha", "数据库巡检", {"files": {"f1": {"pages": pages}}}, limit=2,
    )
    assert audit["tender_hits"] >= 2
    assert audit["history_hits"] == 1
    kinds = [item.get("dataset_kind") for item in chunks]
    assert "tender" in kinds
    assert "history" in kinds or "materials" in kinds
    prompt = knowledge_prompt_block(chunks)
    assert "公司history证据" in prompt or "公司materials证据" in prompt
    assert "【待确认】" not in prompt
