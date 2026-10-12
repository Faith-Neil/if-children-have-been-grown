# 为什么有这个文件：给证据候选一条可替换的检索口，并先用内存实现跑通三条路径。
# 它解决什么问题：在向量库和业务库还没选定之前，避免把检索直接绑到某一家数据库，或把历史投标当成可附着证据。

from __future__ import annotations

import math
import zlib
from dataclasses import dataclass

from .ports import EmbeddingProvider, RerankProvider, VectorRecord, VectorStore

_DIM = 32
_CONFIRMED = "confirmed"
_CHUNK = "chunk"
_HISTORY = "history"


class RetrievalError(Exception):
    """检索口拒绝了本次调用。异常文本不包含资料正文。"""


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
    chunks: list[ChunkRecord]
    historical_bids: list[HistoricalBid]


@dataclass(frozen=True)
class EvidenceCandidate:
    path: str
    source_id: str
    company_id: str
    text: str
    attachable: bool
    reference_only: bool


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
    """产出 A/B/C 三条候选。B 或 C 失败，或知识库关闭时，保留 A 并记下跳过原因。"""

    def __init__(self, embedding: EmbeddingProvider, rerank: RerankProvider, store: VectorStore, *,
                 knowledge_base_enabled: bool = True) -> None:
        self.embedding = embedding
        self.rerank = rerank
        self.store = store
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
        try:
            path_b = self._path_b(request)
        except Exception as exc:
            path_b = []
            skipped.append(SkippedPath("B", f"B failed: {type(exc).__name__}"))
        try:
            path_c = self._path_c(request)
        except Exception as exc:
            path_c = []
            skipped.append(SkippedPath("C", f"C failed: {type(exc).__name__}"))
        return CandidateResult(path_a + path_b + path_c, skipped)

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
        bids = [
            bid for bid in request.historical_bids
            if bid.company_id == request.company_id
        ]
        bids.sort(key=lambda bid: bid.id)
        return [
            EvidenceCandidate("C", bid.id, bid.company_id, bid.text, False, True)
            for bid in bids
        ]
