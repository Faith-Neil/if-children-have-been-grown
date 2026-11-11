# 为什么有这个文件：核对本标索引与节生成检索审计。
# 它解决什么问题：防止写正文时只搜公司库，或把招标页写进 history / materials。

from __future__ import annotations

from icg.domain.technical_rag import retrieve_for_section
from icg.domain.technical_tender_index import (
    FORBIDDEN_KINDS,
    index_current_tender,
    project_dataset_suffix,
    retrieve_tender,
)
from icg.domain.writing_knowledge_prompt import TENDER_HEADING, format_retrieved_knowledge_prompt_lines


def test_retrieve_for_section_audits_tender_and_company():
    class Hit:
        def __init__(self, kind):
            self.source_id = kind
            self.name = kind
            self.content = "公司库切片"
            self.score = 0.4
            self.dataset_kind = kind
            self.reference_only = kind == "history"
            self.document_id = "d"
            self.chunk_ids = [f"c-{kind}"]
            self.cite_tag = f"[片:{kind}]"

    class Kb:
        def search(self, company_id, query, *, limit=4, kinds=None):
            kind = next(iter(kinds or {"history"}))
            return [Hit(kind)], ""

    workflow = {"files": {"f1": {"pages": ["本标要求数据库巡检每月一次"]}}}
    chunks, audit = retrieve_for_section(Kb(), "alpha", "数据库巡检", workflow)
    assert audit["tender_searched"] is True
    assert audit["tender_hits"] >= 1
    assert audit["tender_dataset"] == "workflow.pages"
    assert audit["history_searched"] is True
    assert audit["material_searched"] is True
    assert audit["history_hits"] == 1
    assert audit["material_hits"] == 1
    kinds = [item.get("dataset_kind") for item in chunks]
    assert kinds[0] == "tender"
    assert "history" in kinds and "materials" in kinds
    prompt = "\n".join(format_retrieved_knowledge_prompt_lines(chunks))
    assert prompt.index(TENDER_HEADING) < prompt.index("公司库切片")


def test_project_dataset_name_stays_off_company_libraries():
    suffix = project_dataset_suffix("proj/1")
    assert suffix == "project-tender-proj-1"
    for kind in ("history", "materials", "library", "snippet"):
        assert kind in FORBIDDEN_KINDS
        assert kind not in suffix


def test_index_uploads_only_project_tender_dataset():
    created: list[tuple[str, str]] = []
    uploaded: list[str] = []

    class Doc:
        id = "doc1"

    class Dataset:
        def __init__(self, dataset_id, name):
            self.id = dataset_id
            self.name = name

    class Client:
        def list_datasets(self, company_id=None, page_size=100):
            return []

        def create_dataset(self, suffix, company_id=None):
            created.append((suffix, company_id))
            return Dataset("ds-tender", f"{company_id}::{suffix}")

        def upload_file(self, dataset_id, filename, blob, mime):
            uploaded.append(dataset_id)
            assert "数据库巡检".encode() in blob
            return Doc()

        def trigger_parse(self, dataset_id, document_ids):
            return None

    class Kb:
        repository = None

        def client_for(self, company_id, state):
            return Client()

    workflow = {"files": {"f1": {"pages": ["数据库巡检每月一次"]}}}
    index = index_current_tender(workflow, kb=Kb(), company_id="alpha", project_id="proj/1")
    assert created == [("project-tender-proj-1", "alpha")]
    assert uploaded == ["ds-tender"]
    assert index["dataset_name"] == "alpha::project-tender-proj-1"
    assert index["backend"] == "ragflow"
    assert "icg-history" not in index["dataset_name"]
    assert "icg-material" not in index["dataset_name"]


def test_empty_pages_skip_upload_and_record_reason():
    class Kb:
        def client_for(self, company_id, state):
            raise AssertionError("empty tender pages must not open a dataset client")

    workflow = {"files": {"f1": {"pages": ["  "]}}}
    index = index_current_tender(workflow, kb=Kb(), company_id="alpha", project_id="p1")
    assert index["chunk_count"] == 0
    assert index["skip_reason"] == "no tender pages"
    hits, audit = retrieve_tender(workflow, "数据库巡检")
    assert hits == []
    assert audit["tender_searched"] is True
    assert audit["skip_reason"] == "no tender pages"


def test_retrieve_refuses_company_dataset_backend():
    workflow = {
        "tender_index": {
            "backend": "history",
            "dataset_name": "alpha::icg-history",
            "chunks": [{"id": "a", "page": 1, "text": "数据库巡检每月一次"}],
        },
    }
    hits, audit = retrieve_tender(workflow, "数据库巡检")
    assert hits == []
    assert audit["tender_searched"] is False
    assert audit["skip_reason"] == "refused company dataset"
