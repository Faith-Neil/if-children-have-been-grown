# 为什么有这个文件：提供 PRD P0 合规规则体系（R15、R23、R34、R37）的 RESTful API 契约与端点。
# 它解决什么问题：
# 1. 在 /api/v1 下暴露合规规则评估（POST .../evaluate）、规则状态获取（GET .../compliance-rules）与规则目录（GET /catalog）；
# 2. 输出结构化结果（rule_id, title, severity, passed, finding_summary, suggestion 等）；
# 3. 严格遵循多租户强隔离语义与 8 角色鉴权。

from __future__ import annotations

from typing import Annotated, Any, Literal
from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, ConfigDict, Field

from icg_demo.domain import DemoService, DomainError, Principal
from icg_demo.schemas import RequestBody, ResponseBody
from icg_demo.workflow_schemas import v1_error_responses


class ComplianceRuleIssueSchema(ResponseBody):
    id: str
    rule_id: str
    code: str
    severity: Literal["blocker", "blocking", "warning", "info"]
    message: str
    requirement_id: str | None = None
    chapter_id: str | None = None
    evidence_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ComplianceRuleResultSchema(ResponseBody):
    rule_id: str = Field(description="合规规则编号，如 R15、R23、R34、R37")
    title: str = Field(description="规则名称")
    severity: Literal["blocker", "blocking", "warning", "info"] = Field(description="规则级别")
    passed: bool = Field(description="是否合规通过")
    finding_summary: str = Field(description="检查发现概要")
    suggestion: str = Field(description="针对性改进建议")
    issues: list[ComplianceRuleIssueSchema] = Field(default_factory=list, description="具体问题项列表")
    details: dict[str, Any] = Field(default_factory=dict, description="额外技术上下文")


class ComplianceRulesEvaluationRequest(RequestBody):
    volume: Literal["technical", "business", "all"] = Field(default="all", description="分册范围")


class ComplianceRulesEvaluationResponse(ResponseBody):
    project_id: str
    volume: str
    passed: bool = Field(description="所有 P0 规则是否全部通过")
    has_blockers: bool = Field(description="是否存在阻断级缺陷")
    total_rules: int = Field(description="核验规则总数")
    passed_rules: int = Field(description="通过规则数")
    failed_rules: int = Field(description="未通过规则数")
    rules: list[ComplianceRuleResultSchema] = Field(description="规则核验明细")
    issues: list[ComplianceRuleIssueSchema] = Field(description="全量问题清单")
    evaluated_at: str = Field(description="核验时间戳（ISO-8601）")


class ComplianceRuleCatalogItem(ResponseBody):
    rule_id: str
    title: str
    category: str
    default_severity: str
    can_disable: bool
    description: str


class ComplianceRulesCatalogResponse(ResponseBody):
    catalog: list[ComplianceRuleCatalogItem]


def include_compliance_routes(application, service: DemoService, current_user):
    router = APIRouter(prefix="/api/v1", tags=["compliance-rules"])

    def _get_workflow():
        workflow = getattr(application.state, "workflow", None)
        if workflow is None:
            from icg.domain.workflow_orchestrator import WorkflowService
            from icg_demo.parsing import LocalTextParser
            workflow = WorkflowService(service, LocalTextParser())
            application.state.workflow = workflow
        return workflow

    @router.post(
        "/projects/{project_id}/compliance-rules/evaluate",
        response_model=ComplianceRulesEvaluationResponse,
        operation_id="evaluateComplianceRules",
        summary="执行 P0 合规规则评估",
        description="按 PRD R15、R23、R34、R37 规则体系执行结构化核验，输出各规则裁决与问题清单。",
        responses=v1_error_responses(401, 403, 404),
    )
    def evaluate_compliance_rules(
        project_id: str,
        body: ComplianceRulesEvaluationRequest | None = None,
        user: Principal = Depends(current_user),
    ):
        vol = body.volume if body else "all"
        return _get_workflow().evaluate_compliance_rules(user, project_id, volume=vol)

    @router.get(
        "/projects/{project_id}/compliance-rules",
        response_model=ComplianceRulesEvaluationResponse,
        operation_id="getProjectComplianceRules",
        summary="获取项目 P0 合规规则核验结果",
        description="读取或评估当前项目分册范围的 P0 合规规则裁决。",
        responses=v1_error_responses(401, 403, 404),
    )
    def get_project_compliance_rules(
        project_id: str,
        volume: Literal["technical", "business", "all"] = Query(default="all"),
        user: Principal = Depends(current_user),
    ):
        return _get_workflow().evaluate_compliance_rules(user, project_id, volume=volume)

    @router.get(
        "/compliance-rules/catalog",
        response_model=ComplianceRulesCatalogResponse,
        operation_id="getComplianceRulesCatalog",
        summary="获取已实现的合规规则目录",
        description="返回当前系统已正式落地的 PRD 合规规则（P0 批次：R15、R23、R34、R37）规范定义与默认级别。",
        responses=v1_error_responses(401),
    )
    def get_compliance_rules_catalog(
        user: Principal = Depends(current_user),
    ):
        return {"catalog": _get_workflow().get_compliance_rules_catalog()}

    application.include_router(router)
