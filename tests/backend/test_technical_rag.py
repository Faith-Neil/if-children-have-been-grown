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
