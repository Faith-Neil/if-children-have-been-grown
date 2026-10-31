# 为什么有这个文件：会话、鉴权与角色导航相关的 API 路由端点。
# 它解决什么问题：按领域拆分 API，提供账号列表、登录鉴权与 8 角色会话上下文接口。

from typing import Annotated
from fastapi import APIRouter, Depends, Header, Query, Request, Response

from icg.domain.domain import DemoService, DomainError, Principal
from icg.domain import password_login
from icg.domain.schemas import (
    ApplicationSessionResponse, BrandingResponse, ChangePasswordRequest, ChangePasswordResponse, LoginResponse,
    LogoutResponse, PasswordPolicyResponse, UsernamePasswordLoginRequest,
)
from icg.domain.session_navigation import get_application_session
from icg.domain.workflow_schemas import v1_error_responses

DEFAULT_PRODUCT_NAME = "智能投标系统"


def error_responses(*statuses: int) -> dict:
    from icg.domain.workflow_schemas import V1Error
    descriptions = {
        401: "未登录或登录已失效",
        403: "当前账号无操作权限",
        404: "资源不存在或当前公司无权访问",
        409: "版本、草稿或检查结果冲突",
        422: "请求字段验证失败",
        423: "编辑权被占用或已失效",
        428: "缺少重复请求标记或标记无效",
        500: "后端演示服务异常",
        502: "建议服务调用失败",
    }
    return {status: {"model": V1Error, "description": descriptions[status]} for status in statuses}


def include_session_routes(application, service: DemoService, current_user) -> None:
    User = Annotated[Principal, Depends(current_user)]

    @application.post(
        "/api/v1/auth/login",
        response_model=LoginResponse,
        operation_id="authLogin",
        summary="账号密码登录认证",
        description="账号密码登录。超级管理员 admin 的初始密码由部署时的 ICG_ADMIN_INITIAL_PASSWORD 设定；"
                    "账号不存在、密码错误、账号停用都返回 401 INVALID_CREDENTIALS 且提示相同；连续错误达到公司上限返回 423 ACCOUNT_LOCKED，"
                    "锁定满 ICG_LOGIN_LOCK_MINUTES（默认 15）分钟自动解锁；凭据正确但所属公司已停用返回 403 COMPANY_DISABLED。"
                    "must_change_password 为 true 时须先修改密码。",
        responses=v1_error_responses(401, 403, 422, 423, 500),
    )
    def auth_login(body: UsernamePasswordLoginRequest, response: Response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        return service.auth_login(body.username, body.password)

    @application.post(
        "/api/v1/auth/password",
        response_model=ChangePasswordResponse,
        operation_id="changeOwnPassword",
        summary="本人修改密码",
        description="核对原密码，按本人适用的密码规则（公司账号取本公司安全设置，平台级账号取平台默认）校验新密码；"
                    "成功后清除须改密标记并注销本人其他会话。须改密的会话也可调用。",
        responses=v1_error_responses(401, 422, 500),
    )
    def change_own_password(body: ChangePasswordRequest, user: User):
        return password_login.change_own_password(service, user, body.old_password, body.new_password)

    @application.get(
        "/api/v1/auth/password-policy",
        response_model=PasswordPolicyResponse,
        operation_id="getPasswordPolicy",
        summary="本人适用的密码规则",
        description="设置新密码时页面显示的规则，与服务端校验同一口径。须改密的会话也可调用。",
        responses=v1_error_responses(401, 500),
    )
    def get_password_policy(user: User):
        return password_login.password_policy_response(service, user)

    @application.post(
        "/api/v1/auth/logout",
        response_model=LogoutResponse,
        operation_id="authLogout",
        summary="退出登录",
        description="本次会话令牌立即作废并记审计。",
        responses=v1_error_responses(401, 500),
    )
    def auth_logout(user: User):
        return password_login.logout(service, user)

    @application.get(
        "/api/v1/branding",
        response_model=BrandingResponse,
        operation_id="getBranding",
        summary="登录页品牌",
        description="登录前即可读取的产品名与横版 Logo（PRD v1.8 §5.12.1 版式分区、§5.12.7）。未设置时为平台默认产品名。",
        responses=v1_error_responses(500),
    )
    def get_branding():
        stored = (service.repository.read().service_stores.get("branding") or {}).get("platform") or {}
        name = stored.get("product_name")
        logo = stored.get("logo_horizontal_url")
        return {"product_name": name if isinstance(name, str) and name.strip() else DEFAULT_PRODUCT_NAME,
                "logo_horizontal_url": logo if isinstance(logo, str) and logo else None}

    @application.get("/api/v1/session", response_model=ApplicationSessionResponse,
                     response_model_exclude_unset=True, operation_id="getSession",
                     responses=v1_error_responses(401, 403, 404, 422, 500))
    async def get_session(request: Request, user: User,
                          project_id: Annotated[str | None, Query(min_length=1, max_length=100)] = None):
        if (set(request.query_params) - {"project_id"}
                or len(request.query_params.getlist("project_id")) > 1 or await request.body()):
            raise DomainError(422, "INVALID_SESSION_INPUT", "会话只接受可选的项目ID，公司与角色范围由后台身份决定。")
        return get_application_session(service, user, project_id)
