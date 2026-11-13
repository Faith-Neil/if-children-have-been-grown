# 为什么有这个文件：公司列表、开通与启用/停用（PRD v1.8 §5.10.1 A-01；APP-M2-T260 验收③、APP-M2-T026；ISSUE-052）。
# 它解决什么问题：原 A-01 页面用写死的示例公司，停用只改页面状态、提示“已阻断登录”却没有后台；
# 现在公司状态存入 service_stores["companies"]，停用后该公司账号不能登录、已有会话立即失效；
# 平台管理员可一次开通公司并创建首个公司管理员（自动生成 company_id）。

from __future__ import annotations

import secrets
import time
from typing import Literal

from pydantic import Field

from . import security_audit
from .auth_service import hash_password, is_super_admin
from .company_settings import company_display_name
from .domain import Account, DomainError, Principal, iso_time
from .password_login import company_record, is_platform_account, require_strong_password
from .project_access import ROLE_COMPANY_ADMIN, ROLE_PLATFORM_ADMIN, normalize_role
from .schemas import RequestBody, ResponseBody
from .user_management import UserModel, account_to_user_model


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


class CreateCompanyRequest(RequestBody):
    name: str = Field(min_length=1, max_length=200, description="公司显示名")
    admin_username: str = Field(min_length=1, max_length=64, description="首个公司管理员登录账号")
    admin_name: str = Field(min_length=1, max_length=100, description="首个公司管理员姓名")
    admin_password: str = Field(min_length=1, max_length=200, description="首个公司管理员初始密码")
    admin_display_name: str | None = Field(default=None, max_length=100, description="首个公司管理员显示名")
    must_change_password: bool = Field(default=True, description="首个管理员首次登录是否强制改密")


class CreateCompanyResponse(ResponseBody):
    company: CompanySummary
    admin: UserModel


def _platform_admin(principal: Principal) -> bool:
    return is_super_admin(principal) or normalize_role(principal.user.role) == ROLE_PLATFORM_ADMIN


def _new_company_id(state) -> str:
    known = known_company_ids(state)
    for _ in range(16):
        cid = "co-" + secrets.token_hex(4)
        if cid not in known:
            return cid
    raise DomainError(500, "INTERNAL_ERROR", "无法生成唯一公司标识，请重试。")


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
    """平台管理员看全部公司；公司管理员只看本公司。"""
    state = service.repository.read()
    role = normalize_role(principal.user.role)
    if _platform_admin(principal):
        ids = sorted(known_company_ids(state))
    elif role == ROLE_COMPANY_ADMIN:
        ids = [principal.user.company_id]
    else:
        raise DomainError(403, "FORBIDDEN", "只有平台管理员和公司管理员可以查看公司管理。")
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
        security_audit.record(s, "company.disable" if request.status == "disabled" else "company.enable",
                              operator=principal.user.id, company_id=company_id, revoked_sessions=revoked)

    service.repository.transaction(write)
    return _summary(service.repository.read(), company_id)


def create_company(service, principal: Principal, request: CreateCompanyRequest) -> CreateCompanyResponse:
    """平台管理员开通公司并原子创建首个公司管理员。"""
    if not _platform_admin(principal):
        raise DomainError(403, "FORBIDDEN", "只有平台管理员可以开通公司。")
    name = (request.name or "").strip()
    if not name:
        raise DomainError(422, "VALIDATION_ERROR", "公司显示名不能为空。", details={"field": "name"})
    username = (request.admin_username or "").strip()
    admin_name = (request.admin_name or "").strip()
    if not username or not admin_name:
        raise DomainError(422, "VALIDATION_ERROR", "管理员账号与姓名不能为空。",
                          details={"field": "admin_username" if not username else "admin_name"})

    state = service.repository.read()
    for cid in known_company_ids(state):
        if company_display_name(state, cid).strip() == name:
            raise DomainError(409, "COMPANY_NAME_DUPLICATED", f"公司名称「{name}」已存在。")
    if username in state.accounts:
        raise DomainError(409, "DICT_CODE_DUPLICATED", f"账号 {username} 已存在，请更换用户名。")

    company_id = _new_company_id(state)
    probe = Account(id=username, name=admin_name, company_id=company_id, role=ROLE_COMPANY_ADMIN)
    require_strong_password(state, probe, request.admin_password, field="admin_password")
    pwd_hash, salt = hash_password(request.admin_password)
    now = time.time()
    display = (request.admin_display_name or "").strip() or admin_name

    def write(s) -> None:
        companies = s.service_stores.setdefault("companies", {})
        companies[company_id] = {
            "status": "active",
            "created_at": now,
            "created_by": principal.user.id,
            "status_changed_at": now,
            "status_changed_by": principal.user.id,
        }
        settings = s.service_stores.setdefault("company_settings", {})
        previous = dict(settings.get(company_id) or {})
        previous.update(company_id=company_id, company_name=name)
        settings[company_id] = previous
        s.accounts[username] = Account(
            id=username,
            name=admin_name,
            company_id=company_id,
            role=ROLE_COMPANY_ADMIN,
            _DEMO_ONLY=False,
            password_hash=pwd_hash,
            salt=salt,
            display_name=display,
            status="active",
            created_at=now,
            updated_at=now,
            must_change_password=bool(request.must_change_password),
        )
        security_audit.record(
            s, "company.create",
            operator=principal.user.id,
            company_id=company_id,
            admin_user_id=username,
        )

    service.repository.transaction(write)
    fresh = service.repository.read()
    return CreateCompanyResponse(
        company=_summary(fresh, company_id),
        admin=account_to_user_model(fresh.accounts[username]),
    )
