# 为什么有这个文件：为保持向后兼容保留的 generation_service 兼容入口（BE-TECH-DEBT-03）。
# 它解决什么问题：实际领域编排能力已完全下沉收敛至 generation_orchestrator.py，本文件提供平滑过渡别名。

from __future__ import annotations

from icg.domain.generation_orchestrator import (
    GenerationOrchestratorMixin,
    GenerationOrchestrator,
)

class GenerationServiceMixin(GenerationOrchestratorMixin):
    """向后兼容别名。"""
    pass

class GenerationService(GenerationOrchestrator):
    """向后兼容别名。"""
    pass
