# 为什么有这个文件：集中定义数据库和模型服务的替换接口。
# 它解决什么问题：避免业务规则直接依赖内存字典或某一家模型供应商。

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Protocol, TypeVar

if TYPE_CHECKING:
    from .domain import DemoState
    from .parsing import ParsedDocument

T = TypeVar("T")


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
