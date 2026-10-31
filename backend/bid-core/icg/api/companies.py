# 为什么有这个文件：企业租户与企业安全设置相关的 API 路由端点（APP-M2-T025 / PRD v1.8 §5.10.2、§6.9）。
# 它解决什么问题：按领域拆分 API，提供企业设置查询与安全策略更新接口，落地租户强隔离与不可调宽红线。

from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends

from icg.domain import company_registry
from icg.domain.company_registry import CompanyListResponse, CompanySummary, UpdateCompanyStatusRequest
from icg.domain.domain import DemoService, Principal
from icg.domain.company_settings import (
    CompanySettingsModel,
    CompanySettingsService,
    UpdateCompanySettingsRequest,
)
from icg.domain.workflow_schemas import v1_error_responses


def include_company_routes(application, service: DemoService, current_user) -> None:
    settings_service = getattr(application.state, "company_settings_service", None)
    if not settings_service:
        settings_service = CompanySettingsService()
        application.state.company_settings_service = settings_service
    settings_service.repository = service.repository
    setattr(service, "company_settings_service", settings_service)

    router = APIRouter(prefix="/api/v1", responses=v1_error_responses(401, 403, 404, 422, 500))

    @router.get(
        "/companies/{company_id}/settings",
        response_model=CompanySettingsModel,
        operation_id="getCompanySettings",
        summary="获取企业设置与安全策略",
        description="按公司租户ID获取企业级配置参数（密码策略、编辑锁超时、自动保存间隔、生成循环轮数等）。平台超级管理员可查询任意公司，非超级管理员跨公司访问拦截 404 NOT_FOUND。",
        tags=["companies"],
    )
    def get_company_settings(company_id: str, user: Principal = Depends(current_user)):
        return settings_service.get_settings(company_id, user)

    @router.patch(
        "/companies/{company_id}/settings",
        response_model=CompanySettingsModel,
        operation_id="updateCompanySettings",
        summary="更新企业设置与安全策略",
        description="更新指定企业的配置参数。严格贯彻“只能调严不能调宽”基线安全策略（越界抛出 422 SETTING_VALUE_OUT_OF_BOUNDS）。超级管理员可管理任意公司，企业管理员仅可更新本公司设置，其他角色拦截 403 FORBIDDEN。",
        tags=["companies"],
    )
    def update_company_settings(company_id: str, request: UpdateCompanySettingsRequest, user: Principal = Depends(current_user)):
        return settings_service.update_settings(company_id, request, user)

    @router.get(
        "/companies",
        response_model=CompanyListResponse,
        operation_id="listCompanies",
        summary="公司列表",
        description="平台管理员与集团管理员看全部公司（集团管理员只读），公司管理员只看本公司；含启用状态、账号数与项目数。",
        tags=["companies"],
    )
    def list_companies(user: Principal = Depends(current_user)):
        return company_registry.list_companies(service, user)

    @router.post(
        "/companies/{company_id}/status",
        response_model=CompanySummary,
        operation_id="updateCompanyStatus",
        summary="启用或停用公司",
        description="仅平台管理员。停用须在 confirm_name 填完整公司名称（422 CONFIRMATION_REQUIRED）；"
                    "停用后该公司账号登录返回 403 COMPANY_DISABLED，已有会话立即失效；数据保留。",
        tags=["companies"],
    )
    def update_company_status(company_id: str, request: UpdateCompanyStatusRequest,
                              user: Principal = Depends(current_user)):
        return company_registry.set_company_status(service, user, company_id, request)

    application.include_router(router)
