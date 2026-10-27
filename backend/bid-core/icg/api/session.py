# 为什么有这个文件：会话、鉴权与角色导航相关的 API 路由端点。
# 它解决什么问题：按领域拆分 API，提供账号列表、登录鉴权与 8 角色会话上下文接口。

from typing import Annotated
from fastapi import APIRouter, Depends, Header, Query, Request, Response

from icg.domain.domain import DemoService, DomainError, Principal
from icg.domain.schemas import AccountListResponse, ApplicationSessionResponse, LoginRequest, LoginResponse, UsernamePasswordLoginRequest
from icg.domain.session_navigation import get_application_session
from icg.domain.workflow_schemas import v1_error_responses


def error_responses(*statuses: int) -> dict:
    from icg.domain.workflow_schemas import V1Error
    descriptions = {
        401: "未登录或演示登录已失效",
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

    @application.get("/api/demo/accounts", response_model=AccountListResponse, operation_id="listAccounts", deprecated=True)
    def accounts():
        return service.accounts()

    @application.post("/api/demo/login", response_model=LoginResponse, operation_id="login",
                      responses=error_responses(401), deprecated=True)
    def login(body: LoginRequest):
        return service.login(body.account_id)

    @application.post(
        "/api/v1/auth/login",
        response_model=LoginResponse,
        operation_id="authLogin",
        summary="账号密码登录认证",
        description="正式非演示模式下基于账号密码凭据进行身份认证。支持超级管理员 admin（初始密码 X_2026）及已注册账号登录；凭据错误返回 401 INVALID_CREDENTIALS。",
        responses=v1_error_responses(401, 422, 500),
    )
    def auth_login(body: UsernamePasswordLoginRequest, response: Response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        return service.auth_login(body.username, body.password)

    @application.get("/api/v1/session", response_model=ApplicationSessionResponse,
                     response_model_exclude_unset=True, operation_id="getSession",
                     responses=v1_error_responses(401, 403, 404, 422, 500))
    async def get_session(request: Request, user: User,
                          project_id: Annotated[str | None, Query(min_length=1, max_length=100)] = None):
        if (set(request.query_params) - {"project_id"}
                or len(request.query_params.getlist("project_id")) > 1 or await request.body()):
            raise DomainError(422, "INVALID_SESSION_INPUT", "会话只接受可选的项目ID，公司与角色范围由后台身份决定。")
        return get_application_session(service, user, project_id)
