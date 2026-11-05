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
