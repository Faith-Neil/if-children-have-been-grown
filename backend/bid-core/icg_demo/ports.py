# 为什么有这个文件：集中定义数据库和模型服务的替换接口。
# 它解决什么问题：避免业务规则直接依赖内存字典或某一家模型供应商。

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Protocol, TypeVar

if TYPE_CHECKING:
    from .domain import DemoState
    from .parsing import ParsedDocument

T = TypeVar("T")


@dataclass(frozen=True)
class VectorRecord:
    id: str
    company_id: str
    status: str
    record_type: str
    text: str
    vector: tuple[float, ...]


class Repository(Protocol):
    def read(self) -> DemoState:
        """返回与内部存储分离的完整演示快照。"""
        ...

    def transaction(self, operation: Callable[[DemoState], T]) -> T:
        """在隔离副本上执行操作；失败时全部回滚，成功时原子提交。"""
        ...


class ModelProvider(Protocol):
    name: str
    is_real_model: bool
    is_local: bool

    def suggest(self, instruction: str, content: str) -> str:
        """只返回建议文本；适配器明确声明是否为真实模型、是否本地运行。"""
        ...


class ParserProvider(Protocol):
    def parse(self, filename: str, content: bytes) -> ParsedDocument:
        """返回原文页块和能力说明；不修改数据库，也不假冒 OCR 成功。"""
        ...


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """把文本变成向量。当前只有内存实现，不调用外部模型。"""
        ...


class RerankProvider(Protocol):
    def rerank(self, query: str, docs: list[str]) -> list[int]:
        """返回文档下标，从更相关到更不相关。不改写原文。"""
        ...


class VectorStore(Protocol):
    def upsert(self, records: list["VectorRecord"]) -> None:
        """按记录 id 写入或覆盖。不连接外部向量库。"""
        ...

    def search(self, vector: list[float], *, company_id: str, status: str, type: str, limit: int = 8) -> list["VectorRecord"]:
        """只返回公司、状态和类型都匹配的记录。"""
        ...
