# 为什么有这个文件：核对本标索引与节生成检索审计。
# 它解决什么问题：防止写正文时只搜公司库，或把招标页写进 history / materials。

from __future__ import annotations

from types import SimpleNamespace

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


def test_rewrite_prompt_includes_tender_slice():
    from types import SimpleNamespace

    from icg.domain.selection_rewrite import SelectionRewriteService
    from icg.domain.technical_tender_index import index_current_tender

    class Demo:
        knowledge_base = None

    service = SelectionRewriteService(Demo())
    workflow = {"files": {"f1": {"pages": ["本标要求数据库巡检每月一次并出具报告"]}}}
    index_current_tender(workflow)
    principal = SimpleNamespace(user=SimpleNamespace(id="u1"))
    hits, retrieval = service._retrieve(
        principal, "alpha", "运维保障与巡检", "每月巡检", "", workflow, company_kb=False,
    )
    assert hits and hits[0]["source_type"] == "tender"
    assert hits[0]["cite_tag"].startswith("[标:")
    assert retrieval["tender_hits"] >= 1
    user = SelectionRewriteService._user_content(
        "运维保障与巡检", ["每月巡检"], [], "", "每月巡检", "", "", hits=hits,
    )
    assert "本标优先" in user
    assert hits[0]["cite_tag"] in user
    assert "数据库巡检" in user


def test_editor_context_cites_tender_slices():
    from types import SimpleNamespace

    from icg.domain.editor_ai_context import collect_chapter_citations
    from icg.domain.technical_tender_index import index_current_tender

    workflow = {"files": {"f1": {"pages": ["本标要求数据库巡检每月一次"]}}, "requirements": {}}
    index_current_tender(workflow)
    state = SimpleNamespace(workflows={"p1": workflow}, library={})
    project = SimpleNamespace(id="p1", company_id="alpha", name="合成项目")
    citations = collect_chapter_citations(state, project, "c1", query="巡检", knowledge_base_enabled=False)
    assert any(item.get("source_type") == "tender" for item in citations)
    assert any(str(item.get("tag") or "").startswith("[标") for item in citations)


def test_workspace_fields_expose_audit(monkeypatch):
    from icg.domain.technical_outline import workspace_fields
    from icg.domain.workflow_schemas import (
        TechnicalKbStatus,
        TechnicalRagAuditRow,
        TenderIndexStatus,
        WriterModelStatus,
    )

    class Provider:
        display_name = "mock-writer"
        is_real_model = False
        is_local = False

    state = SimpleNamespace(
        projects={"p1": SimpleNamespace(company_id="alpha")},
        chapters={},
        service_stores={"kb_index": {}},
    )
    provider = Provider()
    workflow = {
        "technical_outline": {"chapter_id": "c1", "title": "服务方案", "headings": []},
        "plan_confirmed": True,
        "parse_confirmed": True,
        "technical_rag_audit": [{
            "query": "巡检",
            "section": "技术服务方案",
            "tender_searched": True,
            "tender_hits": 2,
            "history_searched": True,
            "material_searched": True,
            "history_hits": 1,
            "material_hits": 0,
            "tender_dataset": "workflow.pages",
            "skip_reason": "",
            "top": [{"name": "本标第1页", "dataset_kind": "tender", "score": 2}],
        }],
        "tender_index": {
            "backend": "local",
            "dataset_name": "workflow.pages",
            "chunk_count": 3,
            "skip_reason": "",
            "chunks": [{"id": "p1", "text": "招标页正文不应出现在工作区"}],
        },
        "writer_model": {"name": "qwen", "is_real": True, "is_local": True},
    }
    monkeypatch.setattr("icg.domain.technical_sources.technical_only", lambda *args, **kwargs: True)
    fields = workspace_fields(state, "p1", workflow)
    assert fields["technical_rag_audit"][0]["tender_hits"] == 2
    assert fields["technical_rag_audit"][0]["query"] == "巡检"
    assert fields["tender_index"]["backend"] == "local"
    assert fields["tender_index"]["chunk_count"] == 3
    assert "chunks" not in fields["tender_index"]
    assert "招标页正文" not in str(fields["tender_index"])
    assert fields["writer_model"]["name"] == "qwen"
    assert fields["technical_kb"]["tender"]["configured"] is True
    assert fields["technical_kb"]["tender"]["name"] == "workflow.pages"
    TechnicalRagAuditRow.model_validate(fields["technical_rag_audit"][0])
    TenderIndexStatus.model_validate(fields["tender_index"])
    WriterModelStatus.model_validate(fields["writer_model"])
    TechnicalKbStatus.model_validate(fields["technical_kb"])

    workflow["writer_model"] = provider
    labeled = workspace_fields(state, "p1", workflow)
    assert labeled["writer_model"] == {"name": "mock-writer", "is_real": False, "is_local": False}
    assert workflow["writer_model"] is provider
