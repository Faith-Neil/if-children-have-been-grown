# 为什么有这个文件：给证据候选一条可替换的检索口，并先用内存实现跑通三条路径。
# 它解决什么问题：在向量库和业务库还没选定之前，避免把检索直接绑到某一家数据库，或把历史投标当成可附着证据。

from __future__ import annotations

import math
import zlib
from dataclasses import dataclass, field
from typing import Any, Mapping

from icg.domain.ports import EmbeddingProvider, RerankProvider, VectorRecord, VectorStore
from .ragflow_client import RagflowRetrievalClient

_DIM = 32
_CONFIRMED = "confirmed"
_CHUNK = "chunk"
_HISTORY = "history"


class RetrievalError(Exception):
    """检索口拒绝了本次调用。异常文本不包含资料正文。"""


class RetrievalSkip(Exception):
    """内部标记某条检索路径被跳过。不包含资料正文。"""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class LibraryRecord:
    id: str
    company_id: str
    record_type: str
    status: str
    name: str
    content: str


@dataclass(frozen=True)
class ChunkRecord:
    id: str
    company_id: str
    status: str
    record_type: str
    text: str


@dataclass(frozen=True)
class HistoricalBid:
    id: str
    company_id: str
    title: str
    text: str


@dataclass(frozen=True)
class CandidateRequest:
    company_id: str
    query: str
    library_items: list[LibraryRecord]
    chunks: list[ChunkRecord] = field(default_factory=list)
    historical_bids: list[HistoricalBid] = field(default_factory=list)
    dataset_ids: list[str] | None = None
    history_dataset_ids: list[str] | None = None
    rerank_id: str | None = None


@dataclass(frozen=True)
class EvidenceCandidate:
    path: str
    source_id: str
    company_id: str
    text: str
    attachable: bool
    reference_only: bool
    document_id: str = ""
    chunk_id: str = ""


@dataclass(frozen=True)
class SkippedPath:
    path: str
    reason: str


@dataclass(frozen=True)
class CandidateResult:
    candidates: list[EvidenceCandidate]
    skipped: list[SkippedPath]


def _pieces(text: str) -> list[str]:
    compact = "".join(text.casefold().split())
    if len(compact) < 2:
        return [compact] if compact else []
    return [compact[index:index + 2] for index in range(len(compact) - 1)]


def _vector(text: str) -> list[float]:
    values = [0.0] * _DIM
    for piece in _pieces(text):
        values[zlib.crc32(piece.encode("utf-8")) % _DIM] += 1.0
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0.0:
        return values
    return [value / norm for value in values]


def _cosine(left: list[float] | tuple[float, ...], right: list[float] | tuple[float, ...]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    return sum(one * other for one, other in zip(left, right))


def _matches_query(query: str, text: str) -> bool:
    compact_query = "".join(query.casefold().split())
    if not compact_query:
        return True
    return compact_query in "".join(text.casefold().split())


class InMemoryEmbeddingProvider:
    """用固定字块计数生成向量。它不是嵌入模型，也不访问网络。"""

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not isinstance(texts, list) or any(not isinstance(text, str) for text in texts):
            raise RetrievalError("embed texts must be a list of strings")
        return [_vector(text) for text in texts]


class InMemoryRerankProvider:
    """按查询与文档的共有字块多少排序。分数相同则保持原顺序。"""

    def rerank(self, query: str, docs: list[str]) -> list[int]:
        if not isinstance(query, str) or not isinstance(docs, list) or any(not isinstance(doc, str) for doc in docs):
            raise RetrievalError("rerank requires a query and a list of strings")
        query_pieces = set(_pieces(query))
        scored = []
        for index, doc in enumerate(docs):
            score = sum(1 for piece in _pieces(doc) if piece in query_pieces)
            scored.append((score, -index, index))
        scored.sort(reverse=True)
        return [index for _, _, index in scored]


class InMemoryVectorStore:
    """进程内向量表。搜索必须同时给出公司、状态和类型。"""

    def __init__(self) -> None:
        self._records: dict[str, VectorRecord] = {}

    def upsert(self, records: list[VectorRecord]) -> None:
        if not isinstance(records, list):
            raise RetrievalError("upsert records must be a list")
        for record in records:
            if not isinstance(record, VectorRecord):
                raise RetrievalError("upsert record has the wrong type")
            if not record.id or not record.company_id or not record.status or not record.record_type:
                raise RetrievalError("upsert record is missing id, company, status or type")
            self._records[record.id] = record

    def search(self, vector: list[float], *, company_id: str, status: str, type: str, limit: int = 8) -> list[VectorRecord]:
        if not isinstance(vector, list) or any(not isinstance(value, (int, float)) for value in vector):
            raise RetrievalError("search vector must be a list of numbers")
        if not company_id or not status or not type:
            raise RetrievalError("search requires company_id, status and type")
        if limit < 1:
            raise RetrievalError("search limit must be positive")
        matched = [
            record for record in self._records.values()
            if record.company_id == company_id and record.status == status and record.record_type == type
        ]
        matched.sort(key=lambda record: (-_cosine(vector, record.vector), record.id))
        return matched[:limit]


class EvidenceCandidateService:
    """产出 A/B/C 三条候选。

    路径 A：已确认资料上的本地规则，不经过 RAGFlow。
    路径 B：按公司注入的 dataset id 检索片段（当注入 RagflowRetrievalClient 时走 RAGFlow，否则走内存实现）。
    路径 C：不可附着历史投标，仅供参考，并按查询词过滤（当注入 RagflowRetrievalClient 时走 RAGFlow，否则走内存实现）。
    B 或 C 失败、零命中（skipped=True）或知识库关闭时，安全回退到路径 A 并记录跳过原因。
    知识库关闭时不调用外部服务。
    """

    def __init__(
        self,
        embedding: EmbeddingProvider | None = None,
        rerank: RerankProvider | None = None,
        store: VectorStore | None = None,
        *,
        ragflow_client: RagflowRetrievalClient | None = None,
        company_datasets: Mapping[str, Any] | None = None,
        company_history_datasets: Mapping[str, Any] | None = None,
        dataset_ids: Mapping[str, Any] | None = None,
        history_dataset_ids: Mapping[str, Any] | None = None,
        rerank_id: str | None = None,
        knowledge_base_enabled: bool = True,
    ) -> None:
        self.embedding = embedding
        self.rerank = rerank
        self.store = store
        self.ragflow_client = ragflow_client
        self.company_datasets = dataset_ids if company_datasets is None else company_datasets
        self.company_history_datasets = history_dataset_ids if company_history_datasets is None else company_history_datasets
        self.rerank_id = rerank_id
        self.knowledge_base_enabled = knowledge_base_enabled

    def collect(self, request: CandidateRequest) -> CandidateResult:
        if not request.company_id.strip():
            raise RetrievalError("company_id is required")
        path_a = self._path_a(request)
        if not self.knowledge_base_enabled:
            return CandidateResult(path_a, [
                SkippedPath("B", "knowledge base is off"),
                SkippedPath("C", "knowledge base is off"),
            ])
        skipped: list[SkippedPath] = []
        path_b: list[EvidenceCandidate] = []
        path_c: list[EvidenceCandidate] = []

        try:
            path_b = self._path_b(request)
        except RetrievalSkip as exc:
            skipped.append(SkippedPath("B", exc.reason))
        except Exception as exc:
            skipped.append(SkippedPath("B", f"B failed: {type(exc).__name__}"))

        try:
            path_c = self._path_c(request)
        except RetrievalSkip as exc:
            skipped.append(SkippedPath("C", exc.reason))
        except Exception as exc:
            skipped.append(SkippedPath("C", f"C failed: {type(exc).__name__}"))

        return CandidateResult(path_a + path_b + path_c, skipped)

    def _resolve_dataset_ids(self, request: CandidateRequest, path: str) -> list[str]:
        # 1. 请求级别的显式指定
        if path == "B" and request.dataset_ids:
            return [request.dataset_ids] if isinstance(request.dataset_ids, str) else list(request.dataset_ids)
        if path == "C" and request.history_dataset_ids:
            return [request.history_dataset_ids] if isinstance(request.history_dataset_ids, str) else list(request.history_dataset_ids)

        # 2. 路径 C 的特定历史库映射
        if path == "C" and self.company_history_datasets and request.company_id in self.company_history_datasets:
            cfg = self.company_history_datasets[request.company_id]
            if isinstance(cfg, str):
                return [cfg.strip()] if cfg.strip() else []
            if isinstance(cfg, (list, tuple)):
                return [item.strip() for item in cfg if isinstance(item, str) and item.strip()]

        # 3. 查 company_datasets 配置
        if self.company_datasets and request.company_id in self.company_datasets:
            cfg = self.company_datasets[request.company_id]
            if isinstance(cfg, dict):
                val = cfg.get(path)
                if val is None and path == "B":
                    val = cfg.get("chunks") or cfg.get("snippet") or cfg.get("dataset_id") or cfg.get("dataset_ids")
                elif val is None and path == "C":
                    val = cfg.get("history") or cfg.get("history_dataset_id") or cfg.get("history_dataset_ids")
                if val:
                    if isinstance(val, str):
                        return [val.strip()] if val.strip() else []
                    if isinstance(val, (list, tuple)):
                        return [item.strip() for item in val if isinstance(item, str) and item.strip()]
            elif isinstance(cfg, str):
                return [cfg.strip()] if cfg.strip() else []
            elif isinstance(cfg, (list, tuple)):
                return [item.strip() for item in cfg if isinstance(item, str) and item.strip()]

        # 4. 路径 C 若未单独指定 history dataset，退回使用 request.dataset_ids（若有）
        if path == "C" and request.dataset_ids:
            return [request.dataset_ids] if isinstance(request.dataset_ids, str) else list(request.dataset_ids)

        return []

    def _path_a(self, request: CandidateRequest) -> list[EvidenceCandidate]:
        chosen = [
            item for item in request.library_items
            if item.company_id == request.company_id and item.status == _CONFIRMED and item.record_type != _HISTORY
            and _matches_query(request.query, f"{item.name} {item.content}")
        ]
        chosen.sort(key=lambda item: item.id)
        return [
            EvidenceCandidate("A", item.id, item.company_id, item.content, True, False)
            for item in chosen
        ]

    def _path_b(self, request: CandidateRequest) -> list[EvidenceCandidate]:
        if self.ragflow_client is not None:
            return self._path_b_ragflow(request)
        if self.store is not None and self.embedding is not None and self.rerank is not None:
            return self._path_b_memory(request)
        raise RetrievalSkip("RAGFlow is not configured")

    def _path_b_ragflow(self, request: CandidateRequest) -> list[EvidenceCandidate]:
        dataset_ids = self._resolve_dataset_ids(request, "B")
        if not dataset_ids:
            raise RetrievalSkip("RAGFlow dataset not configured")
        if not request.query.strip():
            raise RetrievalSkip("query is empty")
        effective_rerank_id = request.rerank_id if request.rerank_id is not None else self.rerank_id
        result = self.ragflow_client.retrieve(
            question=request.query,
            dataset_ids=dataset_ids,
            rerank_id=effective_rerank_id,
        )
        if result.skipped:
            raise RetrievalSkip(result.skip_reason or "zero hits")
        if not result.chunks:
            raise RetrievalSkip("zero hits")
        for chunk in result.chunks:
            if chunk.dataset_id and chunk.dataset_id not in dataset_ids:
                raise RetrievalError("search returned a chunk outside the requested datasets")
        return [
            EvidenceCandidate(
                "B", chunk.id, request.company_id, chunk.content, True, False,
                document_id=chunk.document_id, chunk_id=chunk.id
            )
            for chunk in result.chunks
        ]

    def _path_b_memory(self, request: CandidateRequest) -> list[EvidenceCandidate]:
        vectors = self.embedding.embed([chunk.text for chunk in request.chunks])
        if len(vectors) != len(request.chunks):
            raise RetrievalError("embed count mismatch")
        self.store.upsert([
            VectorRecord(chunk.id, chunk.company_id, chunk.status, chunk.record_type, chunk.text, tuple(vector))
            for chunk, vector in zip(request.chunks, vectors)
        ])
        query_vector = self.embedding.embed([request.query])
        if len(query_vector) != 1:
            raise RetrievalError("query embed count mismatch")
        hits = self.store.search(query_vector[0], company_id=request.company_id, status=_CONFIRMED, type=_CHUNK)
        if any(hit.company_id != request.company_id or hit.status != _CONFIRMED or hit.record_type != _CHUNK for hit in hits):
            raise RetrievalError("search returned a record outside the filter")
        order = self.rerank.rerank(request.query, [hit.text for hit in hits])
        if sorted(order) != list(range(len(hits))):
            raise RetrievalError("rerank did not return each hit once")
        return [
            EvidenceCandidate("B", hits[index].id, hits[index].company_id, hits[index].text, True, False)
            for index in order
        ]

    def _path_c(self, request: CandidateRequest) -> list[EvidenceCandidate]:
        if self.ragflow_client is not None:
            return self._path_c_ragflow(request)
        if self.store is not None or self.embedding is not None:
            return self._path_c_memory(request)
        raise RetrievalSkip("RAGFlow is not configured")

    def _path_c_ragflow(self, request: CandidateRequest) -> list[EvidenceCandidate]:
        dataset_ids = self._resolve_dataset_ids(request, "C")
        if not dataset_ids:
            raise RetrievalSkip("RAGFlow dataset not configured")
        if not request.query.strip():
            raise RetrievalSkip("query is empty")
        effective_rerank_id = request.rerank_id if request.rerank_id is not None else self.rerank_id
        result = self.ragflow_client.retrieve(
            question=request.query,
            dataset_ids=dataset_ids,
            rerank_id=effective_rerank_id,
        )
        if result.skipped:
            raise RetrievalSkip(result.skip_reason or "zero hits")
        if not result.chunks:
            raise RetrievalSkip("zero hits")
        for chunk in result.chunks:
            if chunk.dataset_id and chunk.dataset_id not in dataset_ids:
                raise RetrievalError("search returned a chunk outside the requested datasets")
        return [
            EvidenceCandidate(
                "C", chunk.id, request.company_id, chunk.content, False, True,
                document_id=chunk.document_id, chunk_id=chunk.id
            )
            for chunk in result.chunks
        ]

    def _path_c_memory(self, request: CandidateRequest) -> list[EvidenceCandidate]:
        bids = [
            bid for bid in request.historical_bids
            if bid.company_id == request.company_id and _matches_query(request.query, f"{bid.title} {bid.text}")
        ]
        bids.sort(key=lambda bid: bid.id)
        return [
            EvidenceCandidate("C", bid.id, bid.company_id, bid.text, False, True)
            for bid in bids
        ]
