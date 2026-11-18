# 为什么有这个文件：核对空的 kb_index 仍能采用 RAGFlow 里已有的历史投标与资料原件。
# 它解决什么问题：entries 与 files 都空时检索会直接返回，公司库里 history/、materials/ 下的未托管文档永远不会被召回。

from __future__ import annotations

from types import SimpleNamespace

from icg.domain.domain import DemoState
from icg.domain.knowledge_base import KnowledgeBaseService, read_index
from icg.domain.technical_rag import retrieve_dual
from icg.infra.memory_repository import MemoryRepository
from icg.infra.ragflow_client import RagflowChunk, RagflowDataset, RagflowDocument, RagflowRetrievalResult

COMPANY = "alpha"
HISTORY_DATASET = "ds-alpha"
FOREIGN_DATASET = "ds-beta"
HISTORY_DOC = "doc-history"
MATERIAL_DOC = "doc-material"
SCHEME_DOC = "doc-scheme"
FOREIGN_DOC = "doc-foreign"
HISTORY_TEXT = "三级运维服务体系覆盖一线服务台与二线专家。"
MATERIAL_TEXT = "等保三级测评结论：符合。"


def _doc(doc_id: str, dataset_id: str, name: str, location: str) -> RagflowDocument:
    return RagflowDocument(
        id=doc_id,
        name=name,
        dataset_id=dataset_id,
        run="COMPLETED",
        chunk_count=1,
        raw={"location": location, "ingestion_status": "COMPLETED", "chunk_count": 1, "enabled": 1},
    )


class ListingClient:
    """只列出数据集和文档，并按调用方给出的 document_ids 回放分块。"""

    def __init__(self, datasets: list[RagflowDataset], documents: dict[str, list[RagflowDocument]], texts: dict[str, str]) -> None:
        self.datasets = datasets
        self.documents = documents
        self.texts = texts
        self.list_calls: list[str | None] = []
        self.retrieve_calls: list[dict] = []

    def list_datasets(self, *, company_id: str | None = None, page: int = 1, page_size: int = 30) -> list[RagflowDataset]:
        self.list_calls.append(company_id)
        if page > 1:
            return []
        return list(self.datasets)

    def list_documents(self, dataset_id: str, *, run: str | None = None, page: int = 1, page_size: int = 30,
                       document_id: str | None = None) -> list[RagflowDocument]:
        if page > 1:
            return []
        docs = list(self.documents.get(dataset_id, []))
        if document_id:
            docs = [doc for doc in docs if doc.id == document_id]
        return docs

    def retrieve(self, question: str, dataset_ids: list[str], **kwargs) -> RagflowRetrievalResult:
        document_ids = [doc_id for doc_id in (kwargs.get("document_ids") or []) if doc_id]
        self.retrieve_calls.append({
            "question": question,
            "dataset_ids": list(dataset_ids),
            "document_ids": document_ids,
            "rerank_id": kwargs.get("rerank_id"),
        })
        allowed = set(document_ids)
        chunks = [
            RagflowChunk(id=f"chunk-{doc_id}", content=self.texts[doc_id], document_id=doc_id,
                         dataset_id=next(item for item in dataset_ids if item), similarity=0.91)
            for doc_id in allowed if doc_id in self.texts
        ]
        return RagflowRetrievalResult(chunks=chunks, doc_aggs=[], total=len(chunks), skipped=not chunks,
                                      skip_reason="" if chunks else "zero hits")


def _service(client: ListingClient) -> KnowledgeBaseService:
    demo = SimpleNamespace(repository=MemoryRepository(DemoState()), _now=lambda: 1_700_000_000)
    return KnowledgeBaseService(demo, client_factory=lambda state, company_id: client, background=False)


def _alpha_bundle() -> tuple[ListingClient, KnowledgeBaseService]:
    documents = {
        HISTORY_DATASET: [
            _doc(HISTORY_DOC, HISTORY_DATASET, "2023运维.docx", "history/2023运维.docx"),
            _doc(MATERIAL_DOC, HISTORY_DATASET, "等保.docx", "materials/等保.docx"),
            _doc(SCHEME_DOC, HISTORY_DATASET, "片段.md", "scheme/片段.md"),
        ],
        FOREIGN_DATASET: [
            _doc(FOREIGN_DOC, FOREIGN_DATASET, "机密.docx", "history/机密.docx"),
        ],
    }
    client = ListingClient(
        [
            RagflowDataset(id=HISTORY_DATASET, name=f"{COMPANY}::icg-history", company_id=COMPANY),
            RagflowDataset(id=FOREIGN_DATASET, name="beta::icg-history", company_id="beta"),
        ],
        documents,
        {HISTORY_DOC: HISTORY_TEXT, MATERIAL_DOC: MATERIAL_TEXT, FOREIGN_DOC: "其他公司的历史方案。"},
    )
    return client, _service(client)


def test_empty_index_adopts_history_materials_and_search_returns_them():
    client, kb = _alpha_bundle()
    hits, audit = retrieve_dual(kb, COMPANY, "三级运维服务体系")
    assert audit["history_searched"] is True
    assert audit["history_hits"] >= 1
    assert audit["material_hits"] >= 1
    assert audit["skip_reason"] != "knowledge base has no synced documents"
    assert any(HISTORY_TEXT in hit["content"] for hit in hits)
    assert any(MATERIAL_TEXT in hit["content"] for hit in hits)
    assert any(hit["dataset_kind"] == "history" and hit["reference_only"] is True for hit in hits)
    assert client.retrieve_calls
    assert all(FOREIGN_DATASET not in call["dataset_ids"] for call in client.retrieve_calls)

    index = read_index(kb.repository.read(), COMPANY)
    files = list(index["files"].values())
    by_doc = {entry["document_id"]: entry for entry in files}
    assert index["entries"] == {}
    assert set(by_doc) == {HISTORY_DOC, MATERIAL_DOC}
    assert by_doc[HISTORY_DOC]["source_type"] == "file"
    assert by_doc[HISTORY_DOC]["dataset_kind"] == "history"
    assert by_doc[MATERIAL_DOC]["source_type"] == "file"
    assert by_doc[MATERIAL_DOC]["dataset_kind"] == "materials"
    assert index["datasets"]["history"]["dataset_id"] == HISTORY_DATASET
    assert index["datasets"]["materials"]["dataset_id"] == HISTORY_DATASET

    retrieve_dual(kb, COMPANY, "三级运维服务体系")
    again = read_index(kb.repository.read(), COMPANY)
    assert set(again["files"]) == set(index["files"])


def test_bare_filename_in_history_dataset_is_searched_and_not_relisted():
    bare_name = "甘肃农信2025-2027年数据库产品升级服务技术服务方案V2.8-(主标)任登科.docx"
    client = ListingClient(
        [RagflowDataset(id=HISTORY_DATASET, name=f"{COMPANY}::icg-history", company_id=COMPANY)],
        {
            HISTORY_DATASET: [
                _doc(HISTORY_DOC, HISTORY_DATASET, bare_name, bare_name),
                _doc(SCHEME_DOC, HISTORY_DATASET, "片段.md", "scheme/片段.md"),
            ],
        },
        {HISTORY_DOC: HISTORY_TEXT},
    )
    kb = _service(client)
    hits, audit = retrieve_dual(kb, COMPANY, "三级运维服务体系")
    assert audit["history_hits"] >= 1
    assert any(HISTORY_TEXT in hit["content"] for hit in hits)
    assert any(hit["dataset_kind"] == "history" and hit["reference_only"] is True for hit in hits)
    assert client.list_calls == [COMPANY]

    index = read_index(kb.repository.read(), COMPANY)
    files = list(index["files"].values())
    by_doc = {entry["document_id"]: entry for entry in files}
    assert index["entries"] == {}
    assert set(by_doc) == {HISTORY_DOC}
    assert by_doc[HISTORY_DOC]["source_type"] == "file"
    assert by_doc[HISTORY_DOC]["dataset_kind"] == "history"
    assert SCHEME_DOC not in by_doc

    retrieve_dual(kb, COMPANY, "三级运维服务体系")
    assert client.list_calls == [COMPANY]


def test_search_passes_icg_kb_rerank_id_to_retrieve(monkeypatch):
    monkeypatch.setenv("ICG_KB_RERANK_ID", "bge-reranker-v2-m3")
    client, kb = _alpha_bundle()
    kb.search(COMPANY, "三级运维服务体系", kinds={"history"})
    assert client.retrieve_calls
    assert client.retrieve_calls[0]["rerank_id"] == "bge-reranker-v2-m3"


def test_tenant_mismatch_does_not_adopt_unmanaged_documents():
    client = ListingClient(
        [RagflowDataset(id=FOREIGN_DATASET, name="beta::icg-history", company_id="beta")],
        {FOREIGN_DATASET: [_doc(FOREIGN_DOC, FOREIGN_DATASET, "机密.docx", "history/机密.docx")]},
        {FOREIGN_DOC: "其他公司的历史方案。"},
    )
    kb = _service(client)
    hits, reason = kb.search(COMPANY, "历史方案", kinds={"history"})
    assert client.list_calls == [COMPANY]
    assert hits == []
    assert reason == "knowledge base has no synced documents"
    assert client.retrieve_calls == []
    index = read_index(kb.repository.read(), COMPANY)
    assert index["files"] == {}
    assert index["entries"] == {}
