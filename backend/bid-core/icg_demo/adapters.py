# 为什么有这个文件：提供内存存储、模拟建议和真实 Word 文件的演示实现。
# 它解决什么问题：不接数据库或外部模型，也能验证事务、替换接口和下载结果。

from __future__ import annotations

from typing import TypeVar

from .docx_style import DEFAULT_DOCX_STYLE, DocxStyle, build_docx
from .domain import Account, Chapter, DemoState, DomainError, Project, iso_time

from icg.infra.memory_repository import MemoryRepository, seed_state

T = TypeVar("T")


class DemoModelProvider:
    name = "demo"
    is_real_model = False
    is_local = True

    def suggest(self, instruction: str, content: str) -> str:
        return (f"{content}\n\n[模拟建议，未调用真实模型]\n"
                f"修改要求：{instruction}\n请由编写人核对内容；确认提交前不会写入正式正文。")


__all__ = [
    "DEFAULT_DOCX_STYLE",
    "DocxStyle",
    "build_docx",
    "seed_state",
    "MemoryRepository",
    "DemoModelProvider",
]
