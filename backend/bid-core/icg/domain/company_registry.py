# 为什么有这个文件：公司列表与公司启用、停用（PRD v1.8 §5.10.1 A-01；APP-M2-T260 验收③、APP-M2-T026）。
# 它解决什么问题：原 A-01 页面用写死的示例公司，停用只改页面状态、提示“已阻断登录”却没有后台；
# 现在公司状态存入 service_stores["companies"]，停用后该公司账号不能登录、已有会话立即失效。

from __future__ import annotations

import time
from typing import Literal

from pydantic import Field

from .auth_service import is_super_admin
from .company_settings import company_display_name
from .domain import DomainError, Principal, iso_time
from .password_login import company_record, is_platform_account
from .project_access import ROLE_COMPANY_ADMIN, ROLE_GROUP_ADMIN, ROLE_PLATFORM_ADMIN, normalize_role
from .schemas import RequestBody, ResponseBody


class CompanySummary(ResponseBody):
    id: str
    name: str
    status: Literal["active", "disabled"]
    user_count: int = Field(description="本公司账号数（不含已停用账号）")
    project_count: int = Field(description="本公司未删除的投标项目数")
    status_changed_at: str | None = None
    status_changed_by: str | None = None


class CompanyListResponse(ResponseBody):
    items: list[CompanySummary]
    can_change_status: bool = Field(description="当前账号能否启用或停用公司（仅平台管理员）")


class UpdateCompanyStatusRequest(RequestBody):
    status: Literal["active", "disabled"]
    confirm_name: str | None = Field(default=None, max_length=200, description="停用时须输入完整公司名称")


def _platform_admin(principal: Principal) -> bool:
    return is_super_admin(principal) or normalize_role(principal.user.role) == ROLE_PLATFORM_ADMIN


def known_company_ids(state) -> set[str]:
    ids = {a.company_id for a in state.accounts.values() if a.company_id and not is_platform_account(a)}
    ids |= {p.company_id for p in state.projects.values() if p.company_id}
    ids |= set(state.service_stores.get("company_settings") or {})
    ids |= set(state.service_stores.get("companies") or {})
    return {cid for cid in ids if cid not in ("", "system")}


def _summary(state, company_id: str) -> CompanySummary:
    record = company_record(state, company_id)
    changed_at = record.get("status_changed_at")
    return CompanySummary(
        id=company_id,
        name=company_display_name(state, company_id),
        status="disabled" if record.get("status") == "disabled" else "active",
        user_count=sum(1 for a in state.accounts.values()
                       if a.company_id == company_id and getattr(a, "status", "active") != "disabled"),
        project_count=sum(1 for p in state.projects.values()
                          if p.company_id == company_id and not getattr(p, "is_deleted", False)),
        status_changed_at=iso_time(changed_at) if isinstance(changed_at, (int, float)) else None,
        status_changed_by=record.get("status_changed_by"),
    )


def list_companies(service, principal: Principal) -> CompanyListResponse:
    """平台管理员、集团管理员看全部公司（集团管理员只读）；公司管理员只看本公司；其他角色无此页面。"""
    state = service.repository.read()
    role = normalize_role(principal.user.role)
    if _platform_admin(principal) or role == ROLE_GROUP_ADMIN:
        ids = sorted(known_company_ids(state))
    elif role == ROLE_COMPANY_ADMIN:
        ids = [principal.user.company_id]
    else:
        raise DomainError(403, "FORBIDDEN", "只有平台管理员、集团管理员和公司管理员可以查看公司管理。")
    return CompanyListResponse(items=[_summary(state, cid) for cid in ids],
                               can_change_status=_platform_admin(principal))


def set_company_status(service, principal: Principal, company_id: str,
                       request: UpdateCompanyStatusRequest) -> CompanySummary:
    """仅平台管理员可启用或停用公司。停用须输入完整公司名称；停用后该公司全部会话立即失效。"""
    if not _platform_admin(principal):
        raise DomainError(403, "FORBIDDEN", "只有平台管理员可以启用或停用公司。")
    state = service.repository.read()
    if company_id not in known_company_ids(state):
        raise DomainError(404, "NOT_FOUND", "未找到该公司。")
    name = company_display_name(state, company_id)
    if request.status == "disabled" and (request.confirm_name or "").strip() != name:
        raise DomainError(422, "CONFIRMATION_REQUIRED", "停用公司须输入完整的公司名称确认。",
                          details={"field": "confirm_name"})
    now = time.time()

    def write(s) -> None:
        companies = s.service_stores.setdefault("companies", {})
        record = dict(companies.get(company_id) or {})
        previous = "disabled" if record.get("status") == "disabled" else "active"
        if previous == request.status:
            return
        record.update(status=request.status, status_changed_at=now, status_changed_by=principal.user.id)
        companies[company_id] = record
        revoked = 0
        if request.status == "disabled":
            members = {a.id for a in s.accounts.values() if a.company_id == company_id}
            for token, user_id in list(s.sessions.items()):
                if user_id in members:
                    del s.sessions[token]
                    revoked += 1
        s.audit.append({"action": "company.disable" if request.status == "disabled" else "company.enable",
                        "company_id": company_id, "operator": principal.user.id, "revoked_sessions": revoked,
                        "timestamp": now})

    service.repository.transaction(write)
    return _summary(service.repository.read(), company_id)
