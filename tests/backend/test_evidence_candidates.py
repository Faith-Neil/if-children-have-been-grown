# 为什么有这个文件：用合成资料核对三条证据候选的公司隔离、历史不可附着和失败回退。
# 它解决什么问题：避免内存检索口在未接真实库时漏出其他公司的片段，或把历史投标当成可附着证据。

import pytest

from icg_demo.ports import VectorRecord
from icg_demo.retrieval import (
    CandidateRequest, ChunkRecord, EvidenceCandidateService, HistoricalBid, InMemoryEmbeddingProvider,
    InMemoryRerankProvider, InMemoryVectorStore, LibraryRecord, RetrievalError,
)


COMPANY_A = "company-alpha"
COMPANY_B = "company-beta"
QUERY = "机房巡检"


def library(item_id, company_id, status="confirmed", record_type="qualification", content="合成机房巡检记录"):
    return LibraryRecord(item_id, company_id, record_type, status, item_id, content)


def chunk(item_id, company_id, status="confirmed", record_type="chunk", text="合成机房巡检每周一次"):
    return ChunkRecord(item_id, company_id, status, record_type, text)


def history(item_id, company_id, text="往年合成投标，机房巡检"):
    return HistoricalBid(item_id, company_id, item_id, text)


def request(**overrides):
    values = dict(company_id=COMPANY_A, query=QUERY, library_items=[
        library("lib-a", COMPANY_A),
        library("lib-b", COMPANY_B),
        library("lib-pending", COMPANY_A, status="pending"),
        library("lib-history", COMPANY_A, record_type="history", content="历史库记录不应走路径A"),
    ], chunks=[
        chunk("chunk-a", COMPANY_A),
        chunk("chunk-far", COMPANY_A, text="食堂菜单合成"),
        chunk("chunk-b", COMPANY_B),
        chunk("chunk-pending", COMPANY_A, status="pending"),
        chunk("chunk-note", COMPANY_A, record_type="note"),
    ], historical_bids=[
        history("hist-a", COMPANY_A),
        history("hist-b", COMPANY_B),
    ])
    values.update(overrides)
    return CandidateRequest(**values)


def service(**overrides):
    values = dict(embedding=InMemoryEmbeddingProvider(), rerank=InMemoryRerankProvider(),
                  store=InMemoryVectorStore(), knowledge_base_enabled=True)
    values.update(overrides)
    return EvidenceCandidateService(**values)


def ids(result, path):
    return [item.source_id for item in result.candidates if item.path == path]


def test_three_paths_keep_company_and_block_history_attachment():
    result = service().collect(request())

    assert ids(result, "A") == ["lib-a"]
    assert ids(result, "B") == ["chunk-a", "chunk-far"]
    assert ids(result, "C") == ["hist-a"]
    assert result.skipped == []
    by_id = {item.source_id: item for item in result.candidates}
    assert by_id["lib-a"].attachable is True and by_id["lib-a"].reference_only is False
    assert by_id["chunk-a"].company_id == COMPANY_A
    assert by_id["hist-a"].attachable is False and by_id["hist-a"].reference_only is True
    assert "lib-b" not in by_id and "chunk-b" not in by_id and "hist-b" not in by_id
    assert "lib-pending" not in by_id and "chunk-pending" not in by_id and "chunk-note" not in by_id


def test_rerank_places_the_closer_chunk_first():
    result = service().collect(request())
    assert ids(result, "B")[0] == "chunk-a"


def test_vector_search_requires_company_status_and_type():
    embedding = InMemoryEmbeddingProvider()
    store = InMemoryVectorStore()
    vector = embedding.embed([QUERY])[0]
    same = tuple(vector)
    store.upsert([
        VectorRecord("own", COMPANY_A, "confirmed", "chunk", "own", same),
        VectorRecord("other-company", COMPANY_B, "confirmed", "chunk", "other", same),
        VectorRecord("other-status", COMPANY_A, "pending", "chunk", "pending", same),
        VectorRecord("other-type", COMPANY_A, "confirmed", "note", "note", same),
    ])

    found = store.search(vector, company_id=COMPANY_A, status="confirmed", type="chunk")

    assert [item.id for item in found] == ["own"]
    with pytest.raises(RetrievalError):
        store.search(vector, company_id="", status="confirmed", type="chunk")


def test_knowledge_base_off_uses_only_path_a():
    calls = {"embed": 0}

    class SpyEmbed(InMemoryEmbeddingProvider):
        def embed(self, texts):
            calls["embed"] += 1
            return super().embed(texts)

    result = service(embedding=SpyEmbed(), knowledge_base_enabled=False).collect(request())

    assert ids(result, "A") == ["lib-a"]
    assert ids(result, "B") == [] and ids(result, "C") == []
    assert [(item.path, item.reason) for item in result.skipped] == [
        ("B", "knowledge base is off"),
        ("C", "knowledge base is off"),
    ]
    assert calls["embed"] == 0


def test_path_b_failure_keeps_a_and_c():
    class FailingEmbed:
        def embed(self, texts):
            raise RuntimeError("synthetic embed failure with 机房正文")

    result = service(embedding=FailingEmbed()).collect(request())

    assert ids(result, "A") == ["lib-a"]
    assert ids(result, "B") == []
    assert ids(result, "C") == ["hist-a"]
    assert [(item.path, item.reason) for item in result.skipped] == [("B", "B failed: RuntimeError")]
    assert "机房" not in result.skipped[0].reason


def test_path_c_failure_keeps_a_and_b():
    class FailingHistory:
        def __iter__(self):
            raise RuntimeError("synthetic history failure")

    result = service().collect(request(historical_bids=FailingHistory()))

    assert ids(result, "A") == ["lib-a"]
    assert ids(result, "B") == ["chunk-a", "chunk-far"]
    assert ids(result, "C") == []
    assert [(item.path, item.reason) for item in result.skipped] == [("C", "C failed: RuntimeError")]


def test_upsert_replaces_the_same_id():
    store = InMemoryVectorStore()
    embedding = InMemoryEmbeddingProvider()
    first = tuple(embedding.embed(["旧片段"])[0])
    second = tuple(embedding.embed(["新片段"])[0])
    store.upsert([VectorRecord("same", COMPANY_A, "confirmed", "chunk", "旧片段", first)])
    store.upsert([VectorRecord("same", COMPANY_A, "confirmed", "chunk", "新片段", second)])

    found = store.search(list(second), company_id=COMPANY_A, status="confirmed", type="chunk")

    assert [item.text for item in found] == ["新片段"]
