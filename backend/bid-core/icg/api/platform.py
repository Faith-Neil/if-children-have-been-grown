# 为什么有这个文件：平台管理员专属的全局安全配置 API（ISSUE-056）。
# 它解决什么问题：把密码、锁定、会话策略从公司设置中收走，只有平台管理员能读写，公司管理员调用统一 403。

from fastapi import APIRouter, Depends

from icg.domain.domain import DemoService, Principal
from icg.domain.platform_security import (
    PlatformSecuritySettings,
    UpdatePlatformSecuritySettingsRequest,
    read_policy,
    require_platform_admin,
    update_policy,
)
from icg.domain.workflow_schemas import v1_error_responses


def include_platform_routes(application, service: DemoService, current_user) -> None:
    router = APIRouter(prefix="/api/v1/platform", responses=v1_error_responses(401, 403, 422, 500))

    @router.get("/security-settings", response_model=PlatformSecuritySettings, operation_id="getPlatformSecuritySettings")
    def get_security_settings(user: Principal = Depends(current_user)):
        require_platform_admin(user)
        return read_policy(service)

    @router.patch("/security-settings", response_model=PlatformSecuritySettings, operation_id="updatePlatformSecuritySettings")
    def patch_security_settings(body: UpdatePlatformSecuritySettingsRequest, user: Principal = Depends(current_user)):
        return update_policy(service, user, body)

    application.include_router(router)
