# 为什么有这个文件：由原 workflow.py 模块化解耦生成的领域服务。
# 它解决什么问题：按领域上下文治理巨石 workflow.py，向后兼容转接 outline_orchestrator。

from __future__ import annotations

from icg.domain.outline_plan import OutlinePlanError, infer_chapter_type, OutlinePlanService
from icg.domain.outline_auto_tree import AutoTreeBuildEngine, check_tree_finalization_readiness
from icg.domain.outline_orchestrator import OutlineOrchestratorMixin, OutlineOrchestrator

class OutlineServiceMixin(OutlineOrchestratorMixin):
    """向后兼容 OutlineServiceMixin 别名。"""
    pass

class OutlineService(OutlineOrchestrator):
    """向后兼容 OutlineService 别名。"""
    pass

__all__ = [
    "OutlineOrchestratorMixin",
    "OutlineOrchestrator",
    "OutlineServiceMixin",
    "OutlineService",
    "OutlinePlanError",
    "infer_chapter_type",
    "OutlinePlanService",
    "AutoTreeBuildEngine",
    "check_tree_finalization_readiness",
]
