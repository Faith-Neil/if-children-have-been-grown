# 为什么有这个文件：组织 ICG API 路由与契约子包。
# 它解决什么问题：按领域分拆与收敛对外 HTTP 端点。

"""API 路由层。"""

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
