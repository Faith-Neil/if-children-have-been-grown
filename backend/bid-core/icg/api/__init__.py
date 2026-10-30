# 为什么有这个文件：组织 ICG API 路由与契约子包。
# 它解决什么问题：按领域分拆与收敛对外 HTTP 端点。

"""API 路由层。"""

from icg.api.session import include_session_routes
from icg.api.projects import include_project_routes
from icg.api.chapters import include_chapter_routes
from icg.api.workflow import include_workflow_routes
from icg.api.library import include_snippet_routes
from icg.api.model_configs import include_model_config_routes
from icg.api.field_metadata import include_field_metadata_routes
from icg.api.companies import include_company_routes
from icg.api.users import include_user_routes
from icg.api.chapter_loop import include_chapter_loop_routes
from icg.api.knowledge_base import include_knowledge_base_routes
from icg.api.kb_admin import include_kb_admin_routes
from icg.api.selection_rewrite import include_selection_rewrite_routes
from icg.api.notifications import include_notification_routes
from icg.api.export_assets import include_export_asset_routes
from icg.api.task_model_routes import include_task_model_route_routes
from icg.api.volumes import (
    include_volume_routes,
    VolumeFinalizeRequest,
    VolumeUnlockRequest,
    VolumeStatus,
    VolumeFinalizeResponse,
    VolumeStatusResponse,
    VolumeListResponse,
)
from icg.api.compliance import (
    include_compliance_routes,
    ComplianceRuleIssueSchema,
    ComplianceRuleResultSchema,
    ComplianceRulesEvaluationRequest,
    ComplianceRulesEvaluationResponse,
    ComplianceRuleCatalogItem,
    ComplianceRulesCatalogResponse,
)
from icg.api.ragflow import (
    include_ragflow_routes,
    RagflowConfigResponse,
    RagflowConfigUpdateRequest,
    RagflowConfigTestRequest,
    RagflowConfigTestResponse,
)

__all__ = [
    "include_notification_routes",
    "include_export_asset_routes",
    "include_task_model_route_routes",
    "include_selection_rewrite_routes",
    "include_session_routes",
    "include_project_routes",
    "include_chapter_routes",
    "include_workflow_routes",
    "include_snippet_routes",
    "include_model_config_routes",
    "include_field_metadata_routes",
    "include_company_routes",
    "include_user_routes",
    "include_chapter_loop_routes",
    "include_knowledge_base_routes",
    "include_kb_admin_routes",
    "include_volume_routes",
    "VolumeFinalizeRequest",
    "VolumeUnlockRequest",
    "VolumeStatus",
    "VolumeFinalizeResponse",
    "VolumeStatusResponse",
    "VolumeListResponse",
    "include_compliance_routes",
    "ComplianceRuleIssueSchema",
    "ComplianceRuleResultSchema",
    "ComplianceRulesEvaluationRequest",
    "ComplianceRulesEvaluationResponse",
    "ComplianceRuleCatalogItem",
    "ComplianceRulesCatalogResponse",
    "include_ragflow_routes",
    "RagflowConfigResponse",
    "RagflowConfigUpdateRequest",
    "RagflowConfigTestRequest",
    "RagflowConfigTestResponse",
]
