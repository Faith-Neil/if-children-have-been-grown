# 为什么有这个文件：用户管理与账号停用资产交接相关的 API 路由端点（APP-M2-T027 / PRD v1.8 §5.10.1、§5.10.2）。
# 它解决什么问题：按领域拆分 API，提供非演示模式下的用户增删改查、密码强度校验及停用前资产强制转交门禁接口。

from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends, Query

from icg.domain.domain import DemoService, Principal
from icg.domain.user_management import (
    CreateUserRequest,
    TransferUserAssetsRequest,
    TransferUserAssetsResponse,
    UpdateUserRequest,
    UpdateUserStatusRequest,
    UserListResponse,
    UserManagementService,
    UserModel,
)
from icg.domain.workflow_schemas import v1_error_responses


def include_user_routes(application, service: DemoService, current_user) -> None:
    user_mgmt_service = getattr(application.state, "user_management_service", None)
    if not user_mgmt_service:
        user_mgmt_service = UserManagementService(service)
        application.state.user_management_service = user_mgmt_service
    setattr(service, "user_management_service", user_mgmt_service)

    router = APIRouter(prefix="/api/v1", responses=v1_error_responses(401, 403, 404, 409, 422, 500))

    @router.get(
        "/users",
        response_model=UserListResponse,
        operation_id="listUsers",
        summary="调阅用户列表",
        description="按条件调阅用户列表。超级管理员可调阅全平台或指定企业，企业管理员与其他成员严格按所属企业隔离，密码哈希严格脱敏。",
        tags=["users"],
    )
    def list_users(
        company_id: str | None = Query(default=None, description="所属企业租户ID"),
        role: str | None = Query(default=None, description="系统角色代码过滤"),
        status: str | None = Query(default=None, description="状态过滤：active / disabled"),
        keyword: str | None = Query(default=None, description="关键字检索（账号/姓名/昵称）"),
        user: Principal = Depends(current_user),
    ):
        return user_mgmt_service.list_users(
            principal=user,
            company_id=company_id,
            role=role,
            status=status,
            keyword=keyword,
        )

    @router.post(
        "/users",
        response_model=UserModel,
        status_code=201,
        operation_id="createUser",
        summary="新增企业用户",
        description="创建新账号并执行 Q28 定案密码强度校验（最少8位且至少含3类字符，不足拦截 422 PASSWORD_WEAK）。超级管理员可为任意企业创建，企业管理员仅可为本企业创建，其他角色拦截 403 FORBIDDEN。",
        tags=["users"],
    )
    def create_user(
        request: CreateUserRequest,
        user: Principal = Depends(current_user),
    ):
        return user_mgmt_service.create_user(request, user)

    @router.get(
        "/users/{user_id}",
        response_model=UserModel,
        operation_id="getUser",
        summary="获取指定用户详情",
        description="获取用户详情信息，严格脱敏密码哈希与盐，跨企业访问拦截 404 NOT_FOUND。",
        tags=["users"],
    )
    def get_user(
        user_id: str,
        user: Principal = Depends(current_user),
    ):
        return user_mgmt_service.get_user(user_id, user)

    @router.patch(
        "/users/{user_id}",
        response_model=UserModel,
        operation_id="updateUser",
        summary="修改用户信息或停用账号",
        description="更新用户属性或停用账号。停用负责在投项目的用户时，若未指定 successor_user_id 严格拦截 409 USER_TRANSFER_REQUIRED 并返回未结清清单；指定交接人时原子完成项目交接。",
        tags=["users"],
    )
    def update_user(
        user_id: str,
        request: UpdateUserRequest,
        user: Principal = Depends(current_user),
    ):
        return user_mgmt_service.update_user(user_id, request, user)

    @router.patch(
        "/users/{user_id}/status",
        response_model=UserModel,
        operation_id="updateUserStatus",
        summary="修改用户账号状态或停用转交",
        description="更新用户账号状态（active / disabled）。当停用负责在投项目或未完结章节的用户时，若未指定 successor_user_id 严格拦截 409 USER_TRANSFER_REQUIRED；若指定合法交接人则原子完成在投项目与章节编写人转交。",
        tags=["users"],
    )
    def update_user_status(
        user_id: str,
        request: UpdateUserStatusRequest,
        user: Principal = Depends(current_user),
    ):
        return user_mgmt_service.update_user(
            user_id=user_id,
            request=UpdateUserRequest(
                status=request.status,
                successor_user_id=request.successor_user_id,
                reason=request.reason,
            ),
            principal=user,
        )

    @router.post(
        "/users/{user_id}/transfer",
        response_model=TransferUserAssetsResponse,
        operation_id="transferUserAssets",
        summary="转交用户在投项目资产",
        description="在停用前独立将用户负责的在投项目（项目负责人、编写人、总装责任）转交至同一企业的指定接收人。",
        tags=["users"],
    )
    def transfer_user_assets(
        user_id: str,
        request: TransferUserAssetsRequest,
        user: Principal = Depends(current_user),
    ):
        return user_mgmt_service.transfer_assets(user_id, request, user)

    application.include_router(router)
