# 为什么有这个文件：自动化核对 EvidenceCandidateService 接入 RAGFlow 检索适配器后的各项行为。
# 它解决什么问题：验证路径 B/C 走 RAGFlow、零命中/异常降级、跨公司隔离、知识库关闭门禁以及路径 C 查询词过滤。

from __future__ import annotations

import json
import os
import pytest

from fake_ragflow import (
    MODE_BUSINESS_ERROR,
    MODE_CHUNKS,
    MODE_EMPTY,
    MODE_HTTP_ERROR,
    MODE_TIMEOUT,
    SYNTHETIC_CONTENT,
    real_ragflow_skip_reason,
)
from icg_demo.ragflow_client import RagflowRetrievalClient
from icg_demo.retrieval import (
    CandidateRequest,
    ChunkRecord,
    EvidenceCandidate,
    EvidenceCandidateService,
    HistoricalBid,
    InMemoryEmbeddingProvider,
    InMemoryRerankProvider,
    InMemoryVectorStore,
    LibraryRecord,
    RetrievalError,
)

COMPANY_A = "company-alpha"
COMPANY_B = "company-beta"
COMPANY_C = "company-gamma"
QUERY = "机房巡检"
DATASET_A = "syntheticdataset0001"
DATASET_B = "dataset-beta-0002"
API_KEY = "synthetic-ragflow-key"


def library(item_id, company_id, status="confirmed", record_type="qualification", content="合成机房巡检记录"):
    return LibraryRecord(item_id, company_id, record_type, status, item_id, content)


def chunk(item_id, company_id, status="confirmed", record_type="chunk", text="合成机房巡检每周一次"):
    return ChunkRecord(item_id, company_id, status, record_type, text)


def history(item_id, company_id, title=None, text="往年合成投标，机房巡检"):
    t = title or item_id
    return HistoricalBid(item_id, company_id, t, text)


def sample_request(**overrides):
    values = dict(
        company_id=COMPANY_A,
        query=QUERY,
        library_items=[
            library("lib-a", COMPANY_A),
            library("lib-b", COMPANY_B),
            library("lib-pending", COMPANY_A, status="pending"),
            library("lib-history", COMPANY_A, record_type="history", content="历史库记录不应走路径A"),
        ],
        chunks=[
            chunk("chunk-a", COMPANY_A),
            chunk("chunk-far", COMPANY_A, text="食堂菜单合成"),
        ],
        historical_bids=[
            history("hist-a", COMPANY_A, text="往年合成投标，机房巡检"),
            history("hist-b", COMPANY_B, text="往年合成投标，机房巡检"),
        ],
    )
    values.update(overrides)
    return CandidateRequest(**values)


def ids(result, path):
    return [item.source_id for item in result.candidates if item.path == path]


def test_ragflow_retrieval_success_paths_b_and_c(fake_ragflow):
    fake_ragflow.mode = MODE_CHUNKS
    client = RagflowRetrievalClient(
        base_url=fake_ragflow.base_url,
        api_key=API_KEY,
        timeout_seconds=5.0,
    )
    svc = EvidenceCandidateService(
        ragflow_client=client,
        company_datasets={COMPANY_A: DATASET_A},
        rerank_id="rerank-model-01",
    )

    result = svc.collect(sample_request())

    # 路径 A：本公司已确认非历史资料，可附着
    assert ids(result, "A") == ["lib-a"]
    cand_a = next(c for c in result.candidates if c.path == "A")
    assert cand_a.attachable is True
    assert cand_a.reference_only is False

    # 路径 B：RAGFlow 片段，可附着，非参考
    assert ids(result, "B") == ["syntheticchunk0001"]
    cand_b = next(c for c in result.candidates if c.path == "B")
    assert cand_b.attachable is True
    assert cand_b.reference_only is False
    assert cand_b.company_id == COMPANY_A
    assert cand_b.text == SYNTHETIC_CONTENT

    # 路径 C：RAGFlow 历史投标，不可附着，仅供参考
    assert ids(result, "C") == ["syntheticchunk0001"]
    cand_c = next(c for c in result.candidates if c.path == "C")
    assert cand_c.attachable is False
    assert cand_c.reference_only is True
    assert cand_c.company_id == COMPANY_A
    assert cand_c.text == SYNTHETIC_CONTENT

    assert result.skipped == []

    # 验证网络调用：B 与 C 各发起一次请求
    assert len(fake_ragflow.calls) == 2
    for call in fake_ragflow.calls:
        assert call.method == "POST"
        assert call.path == "/api/v1/retrieval"
        assert call.header("Authorization") == f"Bearer {API_KEY}"
        body = json.loads(call.body.decode("utf-8"))
        assert body["question"] == QUERY
        assert body["dataset_ids"] == [DATASET_A]
        assert body["rerank_id"] == "rerank-model-01"


def test_cross_company_isolation_uses_only_injected_dataset_id(fake_ragflow):
    fake_ragflow.mode = MODE_CHUNKS
    client = RagflowRetrievalClient(
        base_url=fake_ragflow.base_url,
        api_key=API_KEY,
    )
    svc = EvidenceCandidateService(
        ragflow_client=client,
        company_datasets={
            COMPANY_A: DATASET_A,
            COMPANY_B: DATASET_B,
        },
    )

    # 以 COMPANY_A 发起检索
    res_a = svc.collect(sample_request(company_id=COMPANY_A))
    assert all(c.company_id == COMPANY_A for c in res_a.candidates)
    calls_a = [json.loads(c.body.decode("utf-8")) for c in fake_ragflow.calls]
    assert len(calls_a) == 2
    for b in calls_a:
        assert b["dataset_ids"] == [DATASET_A]
        assert DATASET_B not in b["dataset_ids"]

    fake_ragflow.calls.clear()

    # 以 COMPANY_B 发起检索
    res_b = svc.collect(sample_request(company_id=COMPANY_B))
    assert all(c.company_id == COMPANY_B for c in res_b.candidates)
    calls_b = [json.loads(c.body.decode("utf-8")) for c in fake_ragflow.calls]
    assert len(calls_b) == 2
    for b in calls_b:
        assert b["dataset_ids"] == [DATASET_B]
        assert DATASET_A not in b["dataset_ids"]

    fake_ragflow.calls.clear()

    # 以未配置 dataset 的 COMPANY_C 发起检索：安全降级，不发起网络请求
    req_c = sample_request(
        company_id=COMPANY_C,
        library_items=[library("lib-c", COMPANY_C)],
    )
    res_c = svc.collect(req_c)
    assert ids(res_c, "A") == ["lib-c"]
    assert ids(res_c, "B") == []
    assert ids(res_c, "C") == []
    assert len(fake_ragflow.calls) == 0
    assert [(s.path, s.reason) for s in res_c.skipped] == [
        ("B", "RAGFlow dataset not configured"),
        ("C", "RAGFlow dataset not configured"),
    ]


def test_separate_datasets_for_snippets_and_history(fake_ragflow):
    fake_ragflow.mode = MODE_CHUNKS
    client = RagflowRetrievalClient(
        base_url=fake_ragflow.base_url,
        api_key=API_KEY,
    )
    # 方式一：通过 company_history_datasets 指定独立历史投标库
    svc = EvidenceCandidateService(
        ragflow_client=client,
        company_datasets={COMPANY_A: "ds-alpha-snippets"},
        company_history_datasets={COMPANY_A: "ds-alpha-history"},
    )
    svc.collect(sample_request())
    assert len(fake_ragflow.calls) == 2
    body_b = json.loads(fake_ragflow.calls[0].body.decode("utf-8"))
    body_c = json.loads(fake_ragflow.calls[1].body.decode("utf-8"))
    assert body_b["dataset_ids"] == ["ds-alpha-snippets"]
    assert body_c["dataset_ids"] == ["ds-alpha-history"]

    fake_ragflow.calls.clear()

    # 方式二：通过嵌套字典配置
    svc_nested = EvidenceCandidateService(
        ragflow_client=client,
        company_datasets={COMPANY_A: {"B": "ds-nested-snippets", "C": "ds-nested-history"}},
    )
    svc_nested.collect(sample_request())
    assert len(fake_ragflow.calls) == 2
    body_b2 = json.loads(fake_ragflow.calls[0].body.decode("utf-8"))
    body_c2 = json.loads(fake_ragflow.calls[1].body.decode("utf-8"))
    assert body_b2["dataset_ids"] == ["ds-nested-snippets"]
    assert body_c2["dataset_ids"] == ["ds-nested-history"]


def test_candidate_request_overrides_datasets(fake_ragflow):
    fake_ragflow.mode = MODE_CHUNKS
    client = RagflowRetrievalClient(
        base_url=fake_ragflow.base_url,
        api_key=API_KEY,
    )
    svc = EvidenceCandidateService(
        ragflow_client=client,
        company_datasets={COMPANY_A: "ds-service-level"},
        rerank_id="service-rerank",
    )
    req = sample_request(
        dataset_ids=["req-b-dataset"],
        history_dataset_ids=["req-c-dataset"],
        rerank_id="request-rerank",
    )
    svc.collect(req)

    assert len(fake_ragflow.calls) == 2
    body_b = json.loads(fake_ragflow.calls[0].body.decode("utf-8"))
    body_c = json.loads(fake_ragflow.calls[1].body.decode("utf-8"))
    assert body_b["dataset_ids"] == ["req-b-dataset"]
    assert body_b["rerank_id"] == "request-rerank"
    assert body_c["dataset_ids"] == ["req-c-dataset"]
    assert body_c["rerank_id"] == "request-rerank"


def test_zero_hits_safely_falls_back_to_path_a(fake_ragflow):
    fake_ragflow.mode = MODE_EMPTY
    client = RagflowRetrievalClient(
        base_url=fake_ragflow.base_url,
        api_key=API_KEY,
    )
    svc = EvidenceCandidateService(
        ragflow_client=client,
        company_datasets={COMPANY_A: DATASET_A},
    )

    result = svc.collect(sample_request())

    assert ids(result, "A") == ["lib-a"]
    assert ids(result, "B") == []
    assert ids(result, "C") == []
    assert [(s.path, s.reason) for s in result.skipped] == [
        ("B", "zero hits"),
        ("C", "zero hits"),
    ]


def test_ragflow_http_500_falls_back_to_path_a(fake_ragflow):
    fake_ragflow.mode = MODE_HTTP_ERROR
    client = RagflowRetrievalClient(
        base_url=fake_ragflow.base_url,
        api_key=API_KEY,
    )
    svc = EvidenceCandidateService(
        ragflow_client=client,
        company_datasets={COMPANY_A: DATASET_A},
    )

    result = svc.collect(sample_request())

    assert ids(result, "A") == ["lib-a"]
    assert ids(result, "B") == []
    assert ids(result, "C") == []
    assert [(s.path, s.reason) for s in result.skipped] == [
        ("B", "B failed: RagflowHttpError"),
        ("C", "C failed: RagflowHttpError"),
    ]
    # 确认机密与 URL 不进跳过原因
    for s in result.skipped:
        assert API_KEY not in s.reason
        assert fake_ragflow.base_url not in s.reason


def test_ragflow_business_error_falls_back_to_path_a(fake_ragflow):
    fake_ragflow.mode = MODE_BUSINESS_ERROR
    client = RagflowRetrievalClient(
        base_url=fake_ragflow.base_url,
        api_key=API_KEY,
    )
    svc = EvidenceCandidateService(
        ragflow_client=client,
        company_datasets={COMPANY_A: DATASET_A},
    )

    result = svc.collect(sample_request())

    assert ids(result, "A") == ["lib-a"]
    assert ids(result, "B") == []
    assert ids(result, "C") == []
    assert [(s.path, s.reason) for s in result.skipped] == [
        ("B", "B failed: RagflowBusinessError"),
        ("C", "C failed: RagflowBusinessError"),
    ]


def test_ragflow_timeout_falls_back_to_path_a(fake_ragflow):
    fake_ragflow.mode = MODE_TIMEOUT
    fake_ragflow.hold_responses()
    client = RagflowRetrievalClient(
        base_url=fake_ragflow.base_url,
        api_key=API_KEY,
        timeout_seconds=0.2,
    )
    svc = EvidenceCandidateService(
        ragflow_client=client,
        company_datasets={COMPANY_A: DATASET_A},
    )

    try:
        result = svc.collect(sample_request())
        assert ids(result, "A") == ["lib-a"]
        assert ids(result, "B") == []
        assert ids(result, "C") == []
        assert [(s.path, s.reason) for s in result.skipped] == [
            ("B", "B failed: RagflowTimeoutError"),
            ("C", "C failed: RagflowTimeoutError"),
        ]
    finally:
        fake_ragflow.release_responses()


def test_knowledge_base_disabled_sends_no_ragflow_requests(fake_ragflow):
    fake_ragflow.mode = MODE_CHUNKS
    client = RagflowRetrievalClient(
        base_url=fake_ragflow.base_url,
        api_key=API_KEY,
    )
    svc = EvidenceCandidateService(
        ragflow_client=client,
        company_datasets={COMPANY_A: DATASET_A},
        knowledge_base_enabled=False,
    )

    result = svc.collect(sample_request())

    assert ids(result, "A") == ["lib-a"]
    assert ids(result, "B") == []
    assert ids(result, "C") == []
    assert [(s.path, s.reason) for s in result.skipped] == [
        ("B", "knowledge base is off"),
        ("C", "knowledge base is off"),
    ]
    # 严禁产生任何网络调用
    assert len(fake_ragflow.calls) == 0


def test_unconfigured_ragflow_safely_falls_back_to_path_a():
    # 构造空服务（未注入 ragflow_client 且无内存存储实现）
    svc = EvidenceCandidateService()

    result = svc.collect(sample_request())

    assert ids(result, "A") == ["lib-a"]
    assert ids(result, "B") == []
    assert ids(result, "C") == []
    assert [(s.path, s.reason) for s in result.skipped] == [
        ("B", "RAGFlow is not configured"),
        ("C", "RAGFlow is not configured"),
    ]


def test_path_c_query_filtering_in_memory_mode():
    svc = EvidenceCandidateService(
        embedding=InMemoryEmbeddingProvider(),
        rerank=InMemoryRerankProvider(),
        store=InMemoryVectorStore(),
    )
    req = sample_request(
        query="机房巡检",
        historical_bids=[
            history("hist-inspect", COMPANY_A, title="机房巡检项目", text="历年机房巡检及运维维保"),
            history("hist-catering", COMPANY_A, title="食堂承包项目", text="员工食堂餐饮外包服务"),
        ],
    )
    res_inspect = svc.collect(req)
    # 命中巡检的历史标书返回，未命中的食堂被过滤
    assert ids(res_inspect, "C") == ["hist-inspect"]

    # 换成查询“食堂”
    req_catering = sample_request(
        query="食堂",
        historical_bids=req.historical_bids,
    )
    res_catering = svc.collect(req_catering)
    assert ids(res_catering, "C") == ["hist-catering"]

    # 查询完全无关词
    req_unrelated = sample_request(
        query="完全无关词语",
        historical_bids=req.historical_bids,
    )
    res_unrelated = svc.collect(req_unrelated)
    assert ids(res_unrelated, "C") == []


def test_empty_query_handling_in_ragflow_mode(fake_ragflow):
    fake_ragflow.mode = MODE_CHUNKS
    client = RagflowRetrievalClient(
        base_url=fake_ragflow.base_url,
        api_key=API_KEY,
    )
    svc = EvidenceCandidateService(
        ragflow_client=client,
        company_datasets={COMPANY_A: DATASET_A},
    )

    req_blank = sample_request(
        query="   ",
        library_items=[library("lib-blank", COMPANY_A, content="空白查询测试")],
    )
    result = svc.collect(req_blank)

    assert ids(result, "A") == ["lib-blank"]
    assert ids(result, "B") == []
    assert ids(result, "C") == []
    assert [(s.path, s.reason) for s in result.skipped] == [
        ("B", "query is empty"),
        ("C", "query is empty"),
    ]
    # 空查询不向 RAGFlow 发送无效请求
    assert len(fake_ragflow.calls) == 0


def test_empty_company_id_raises_retrieval_error():
    svc = EvidenceCandidateService()
    req = sample_request(company_id="")
    with pytest.raises(RetrievalError) as exc_info:
        svc.collect(req)
    assert "company_id is required" in str(exc_info.value)


def test_chunk_outside_dataset_rejected_by_path_b_and_c():
    from unittest.mock import MagicMock
    from icg_demo.ragflow_client import RagflowChunk, RagflowRetrievalResult

    # 模拟 RAGFlow 异常返回了非请求数据集的 chunk
    bad_chunk = RagflowChunk(
        id="bad-chunk",
        content="越界片段",
        document_id="doc-other",
        dataset_id="other-dataset-id",
        similarity=0.99,
    )
    mock_client = MagicMock()
    mock_client.retrieve.return_value = RagflowRetrievalResult(
        chunks=[bad_chunk],
        doc_aggs=[],
        total=1,
        skipped=False,
    )

    svc = EvidenceCandidateService(
        ragflow_client=mock_client,
        company_datasets={COMPANY_A: DATASET_A},
    )

    result = svc.collect(sample_request())
    assert ids(result, "A") == ["lib-a"]
    assert ids(result, "B") == []
    assert ids(result, "C") == []
    assert [(s.path, s.reason) for s in result.skipped] == [
        ("B", "B failed: RetrievalError"),
        ("C", "C failed: RetrievalError"),
    ]


@pytest.mark.live_ragflow
def test_live_ragflow_evidence_probe_skipped_by_default():
    skip_reason = real_ragflow_skip_reason()
    if skip_reason:
        pytest.skip(skip_reason)
    base = os.environ.get("ICG_RAGFLOW_BASE_URL", "").strip()
    assert base.startswith("http")
