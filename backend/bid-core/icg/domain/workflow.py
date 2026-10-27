# 为什么有这个文件：向下兼容已有的 icg_demo.workflow 导入路径。
# 它解决什么问题：将历史导入平滑代理到 icg.domain 模块，消除 1500+ 行巨石代码。

from __future__ import annotations

from icg.domain.workflow_orchestrator import WorkflowService, SAMPLE_TENDER
from icg.domain.export_service import (
    ExportService,
    CheckBlockerError,
    chapter_export_block,
    DOCX_MEDIA_TYPE,
    WORD_DEFAULT_FORMAT_METADATA,
)
from icg.domain.generation_service import GenerationService
from icg.domain.outline_service import OutlineService, OutlinePlanError, infer_chapter_type
from icg.domain.outline_orchestrator import OutlineOrchestrator, OutlineOrchestratorMixin
from icg.domain.generation_orchestrator import GenerationOrchestrator, GenerationOrchestratorMixin
from icg.domain.check_orchestrator import CheckOrchestrator, CheckOrchestratorMixin
from icg.domain.tender_orchestrator import TenderOrchestrator, TenderOrchestratorMixin
from icg.domain.library_orchestrator import LibraryOrchestrator, LibraryOrchestratorMixin

__all__ = [
    "WorkflowService",
    "ExportService",
    "CheckBlockerError",
    "chapter_export_block",
    "DOCX_MEDIA_TYPE",
    "WORD_DEFAULT_FORMAT_METADATA",
    "SAMPLE_TENDER",
    "GenerationService",
    "OutlineService",
    "OutlinePlanError",
    "infer_chapter_type",
    "OutlineOrchestrator",
    "OutlineOrchestratorMixin",
    "GenerationOrchestrator",
    "GenerationOrchestratorMixin",
    "CheckOrchestrator",
    "CheckOrchestratorMixin",
    "TenderOrchestrator",
    "TenderOrchestratorMixin",
    "LibraryOrchestrator",
    "LibraryOrchestratorMixin",
]
