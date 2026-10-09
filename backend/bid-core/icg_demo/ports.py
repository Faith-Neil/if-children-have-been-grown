# 为什么有这个文件：集中定义数据库和模型服务的替换接口。
# 它解决什么问题：避免业务规则直接依赖内存字典或某一家模型供应商。

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Protocol, TypeVar

if TYPE_CHECKING:
    from .domain import DemoState

T = TypeVar("T")


class Repository(Protocol):
    def read(self) -> DemoState:
        """返回与内部存储分离的完整演示快照。"""
        ...

    def transaction(self, operation: Callable[[DemoState], T]) -> T:
        """在隔离副本上执行操作；失败时全部回滚，成功时原子提交。"""
        ...


class ModelProvider(Protocol):
    def suggest(self, instruction: str, content: str) -> str:
        """只返回建议文本，不保存正文，也不能直接访问资料存储。"""
        ...
