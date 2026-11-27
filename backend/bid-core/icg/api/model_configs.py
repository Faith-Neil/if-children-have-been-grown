# 为什么有这个文件：AI 模型配置相关的 API 路由端点。
# 它解决什么问题：按领域拆分 API，提供模型配置 CRUD、连通性测试与项目绑定接口。

from fastapi import APIRouter, Depends, Header, Response

from icg.domain.domain import DemoService, Principal
from icg.infra.model_config_storage import (
    ModelConfigService,
    ModelConfigListResponse,
    ModelConfigResponse,
    ModelConfigCreateRequest,
    ModelConfigUpdateRequest,
    ModelConfigTestResponse,
    ProjectModelConfigBindingRequest,
    ProjectModelConfigBindingResponse,
)
from icg.domain.workflow_schemas import v1_error_responses


def include_model_config_routes(application, service: DemoService, current_user) -> None:
    config_service = ModelConfigService(service)
    application.state.model_config_service = config_service
    router = APIRouter(prefix="/api/v1", responses=v1_error_responses(401, 403, 404, 409, 422, 428, 500, 503))

    @router.get("/model-configs", response_model=ModelConfigListResponse, operation_id="listModelConfigs")
    def list_model_configs(user: Principal = Depends(current_user)):
        """列出当前公司的模型配置。响应中绝不暴露明文密钥，只返回 api_key_masked 与 has_api_key。"""
        return config_service.list(user)

    @router.post("/model-configs", response_model=ModelConfigResponse, operation_id="createModelConfig")
    def create_model_config(body: ModelConfigCreateRequest, response: Response, user: Principal = Depends(current_user)):
        """新建模型配置。若提供 api_key，需环境变量 ICG_SECRET_KEY 可用以进行 Fernet 加密；若未配置则返回 503 SECRET_KEY_UNAVAILABLE。"""
        result = config_service.create(user, body.model_dump(exclude_unset=True))
        response.headers["ETag"] = f'"{result["revision"]}"'
        return result

    @router.get("/model-configs/{id}", response_model=ModelConfigResponse, operation_id="getModelConfig")
    def get_model_config(id: str, response: Response, user: Principal = Depends(current_user)):
        """获取单个模型配置详情。响应头 ETag 为当前 revision。"""
        result = config_service.get(user, id)
        response.headers["ETag"] = f'"{result["revision"]}"'
        return result

    @router.put("/model-configs/{id}", response_model=ModelConfigResponse, operation_id="updateModelConfig")
    def update_model_config(id: str, body: ModelConfigUpdateRequest, response: Response,
                            user: Principal = Depends(current_user),
                            if_match: str | None = Header(default=None)):
        """更新模型配置。需通过 If-Match 请求头核对 revision 进行乐观锁并发保护。省略 api_key 表示保留原密钥，空字符串表示清除，传回掩码表示不修改。若需要加密新密钥且 ICG_SECRET_KEY 未配置，返回 503 SECRET_KEY_UNAVAILABLE。"""
        result = config_service.update(user, id, body.model_dump(exclude_unset=True), if_match)
        response.headers["ETag"] = f'"{result["revision"]}"'
        return result

    @router.post("/model-configs/{id}/test", response_model=ModelConfigTestResponse, operation_id="testModelConfig")
    def test_model_config(id: str, user: Principal = Depends(current_user)):
        """测试模型配置连通性。返回 ok、provider、model 与 duration_ms。若配置包含加密密钥且 ICG_SECRET_KEY 不可用，返回 503 SECRET_KEY_UNAVAILABLE 且无 Retry-After。"""
        return config_service.test_connectivity(user, id)

    @router.post("/model-configs/test", response_model=ModelConfigTestResponse, include_in_schema=False)
    def test_model_config_direct(body: dict | None = None, user: Principal = Depends(current_user)):
        """兼容 /api/v1/model-configs/test 直接测试（不传 id 默认测试 default 配置）。"""
        config_id = (body or {}).get("model_config_id") or (body or {}).get("id") or "default"
        return config_service.test_connectivity(user, config_id)

    @router.post("/projects/{project_id}/model-config", response_model=ProjectModelConfigBindingResponse,
                 operation_id="bindProjectModelConfig")
    def bind_project_model_config(project_id: str, body: ProjectModelConfigBindingRequest,
                                  user: Principal = Depends(current_user)):
        """将模型配置绑定到指定项目。敏感项目尝试绑定非本地或未标记敏感可用的模型时，返回 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL。"""
        return config_service.bind_project(user, project_id, body.model_config_id)

    @router.get("/projects/{project_id}/model-config", response_model=ModelConfigResponse,
                operation_id="getProjectModelConfig")
    def get_project_model_config(project_id: str, response: Response, user: Principal = Depends(current_user)):
        """获取项目绑定的模型配置（未单独绑定时返回公司默认配置）。"""
        result = config_service.get_project_config(user, project_id)
        response.headers["ETag"] = f'"{result["revision"]}"'
        return result

    application.include_router(router)
