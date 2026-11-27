# 为什么有这个文件：平台与公司安全审计日志查询 API（ISSUE-056）。
# 它解决什么问题：后台审计页原先只能使用前端样例数据；现在从 security_audit 真事实源读取，
# 平台管理员可看全局，公司管理员只能看本公司，跨租户请求由后端强制拦截。

from __future__ import annotations

from typing import Annotated, Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from icg.domain.domain import DemoService, DomainError, Principal
from icg.domain import security_audit
from icg.domain.platform_security import is_platform_admin
from icg.domain.workflow_schemas import v1_error_responses


class AuditLogItem(BaseModel):
    id: str
    action: str
    operator: str
    user_id: str | None = None
    target_user_id: str | None = None
    company_id: str | None = None
    timestamp: float
    at: str
    details: dict[str, Any] = Field(default_factory=dict)


class AuditLogListResponse(BaseModel):
    total: int
    items: list[AuditLogItem]


def _event_company(event: dict, accounts: dict[str, Any]) -> str | None:
    if event.get("company_id"):
        return event.get("company_id")
    for key in ("user_id", "target_user_id", "operator"):
        account = accounts.get(event.get(key) or "")
        if account is not None and getattr(account, "company_id", None) != "system":
            return getattr(account, "company_id", None)
    return None


def include_audit_routes(application, service: DemoService, current_user) -> None:
    router = APIRouter(prefix="/api/v1", responses=v1_error_responses(401, 403, 422, 500))

    @router.get("/audit-logs", response_model=AuditLogListResponse, operation_id="listAuditLogs")
    def list_audit_logs(
        company_id: Annotated[str | None, Query(description="公司租户ID；平台管理员可指定，公司管理员只能为本公司")] = None,
        action: Annotated[str | None, Query(description="审计动作过滤")] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
        user: Principal = Depends(current_user),
    ):
        from icg.domain.project_access import ROLE_COMPANY_ADMIN, normalize_role
        platform = is_platform_admin(user)
        if not platform:
            # CWE-862 越权修复（ISSUE-059）：审计日志含登录失败原因、锁定与敏感操作痕迹，
            # 普通成员一律无权调阅；公司管理员仅限本公司，跨公司查询参数拒绝。
            if normalize_role(user.user.role) != ROLE_COMPANY_ADMIN:
                raise DomainError(403, "FORBIDDEN", "只有平台管理员或公司管理员可以调阅审计日志。")
            if company_id and company_id != user.user.company_id:
                raise DomainError(403, "FORBIDDEN", "公司管理员只能查看本公司审计日志。")
            company_id = user.user.company_id
        state = service.repository.read()
        accounts = state.accounts
        rows: list[AuditLogItem] = []
        for event in reversed(security_audit.events(state, action=action)):
            tenant = _event_company(event, accounts)
            if company_id and tenant != company_id:
                continue
            details = {k: v for k, v in event.items()
                       if k not in {"id", "action", "operator", "user_id", "target_user_id", "company_id", "timestamp", "at"}}
            rows.append(AuditLogItem(id=event["id"], action=event["action"], operator=event.get("operator", "system"),
                                     user_id=event.get("user_id"), target_user_id=event.get("target_user_id"),
                                     company_id=tenant, timestamp=float(event.get("timestamp") or 0),
                                     at=event.get("at") or "", details=details))
            if len(rows) >= limit:
                break
        return {"total": len(rows), "items": rows}

    application.include_router(router)
