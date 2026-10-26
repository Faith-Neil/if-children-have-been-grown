# 为什么有这个文件：提供企业租户 RAGFlow 知识库检索配置的 RESTful API 端点与契约。
# 它解决什么问题：在 /api/v1 下暴露获取配置（GET /ragflow-config）、更新配置（PUT /ragflow-config）与连通性测试（POST /ragflow-config/test），支持并发乐观锁与密钥防泄露。

from __future__ import annotations

from typing import Annotated, Any
from fastapi import APIRouter, Depends, Header, Response
from pydantic import Field

from icg.domain.domain import DemoService, Principal
from icg.domain.schemas import RequestBody, ResponseBody
from icg.domain.workflow_schemas import v1_error_responses
from icg.domain.ragflow_config import RagflowConfigService


class RagflowConfigResponse(ResponseBody):
    company_id: str
    base_url: str = Field(description="RAGFlow 基础服务地址")
    has_api_key: bool = Field(description="是否已配置 API Key")
    api_key_masked: str | None = Field(default=None, description="掩码后的 API Key，明文绝不泄露")
    dataset_ids: list[str] = Field(default_factory=list, description="检索绑定的数据集 ID 列表")
    timeout_seconds: float = Field(default=30.0, description="超时时间秒数")
    is_enabled: bool = Field(default=True, description="是否启用知识库检索")
    revision: int = Field(default=1, description="配置版本号（乐观锁）")


class RagflowConfigUpdateRequest(RequestBody):
    base_url: str | None = Field(default=None, min_length=1, max_length=500, description="RAGFlow 基础地址")
    api_key: str | None = Field(default=None, max_length=1000, description="新 API Key（留空不改，空串清除）")
    dataset_ids: list[str] | None = Field(default=None, description="数据集 ID 列表")
    timeout_seconds: float | None = Field(default=None, gt=0, le=600, description="超时秒数")
    is_enabled: bool | None = Field(default=None, description="是否启用")


class RagflowConfigTestRequest(RequestBody):
    base_url: str | None = Field(default=None, max_length=500, description="可选覆盖测试基础地址")
    api_key: str | None = Field(default=None, max_length=1000, description="可选覆盖测试 API Key")
    timeout_seconds: float | None = Field(default=None, gt=0, le=600, description="超时秒数")


class RagflowConfigTestResponse(ResponseBody):
    ok: bool = Field(description="测试连通是否成功")
    duration_ms: int = Field(ge=0, description="测试请求耗时（毫秒）")
    message: str = Field(description="测试反馈信息")
    health: dict[str, Any] = Field(default_factory=dict, description="健康检查原始返回结果")


def include_ragflow_routes(application, service: DemoService, current_user) -> None:
    pub_store = getattr(application.state, "snippet_publications", None) or getattr(service, "snippet_publications", None)
    config_service = RagflowConfigService(service, snippet_publications=pub_store)
    application.state.ragflow_config_service = config_service
    router = APIRouter(prefix="/api/v1", responses=v1_error_responses(401, 403, 404, 409, 422, 428, 500, 503))

    @router.get("/ragflow-config", response_model=RagflowConfigResponse, operation_id="getRagflowConfig")
    def get_ragflow_config(user: Principal = Depends(current_user)):
        """获取当前企业租户的 RAGFlow 知识库检索配置。响应绝不输出明文 API Key。"""
        return config_service.get(user)

    @router.put("/ragflow-config", response_model=RagflowConfigResponse, operation_id="updateRagflowConfig")
    def update_ragflow_config(
        body: RagflowConfigUpdateRequest,
        response: Response,
        user: Principal = Depends(current_user),
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ):
        """更新当前企业租户的 RAGFlow 配置。强制校验 If-Match 版本号，新密钥使用 Fernet 对称加密保护。"""
        result = config_service.update(user, body.model_dump(exclude_unset=True), if_match)
        response.headers["ETag"] = f'"{result["revision"]}"'
        return result

    @router.post("/ragflow-config/test", response_model=RagflowConfigTestResponse, operation_id="testRagflowConfig")
    def test_ragflow_config(
        body: RagflowConfigTestRequest | None = None,
        user: Principal = Depends(current_user),
    ):
        """测试 RAGFlow 知识库服务的网络连通性与健康状态。"""
        payload = body.model_dump(exclude_unset=True) if body else {}
        return config_service.test_connectivity(user, payload)

    @router.get("/ragflow/datasets", include_in_schema=False)
    def list_ragflow_datasets(user: Principal = Depends(current_user)):
        """列出当前租户绑定的 RAGFlow 数据集。"""
        return {"items": config_service.list_datasets(user)}

    @router.post("/ragflow/datasets", include_in_schema=False)
    def create_ragflow_dataset(body: dict[str, Any], user: Principal = Depends(current_user)):
        """为当前租户创建专属前缀隔离的 RAGFlow 数据集。"""
        name = str(body.get("name") or "knowledge-base")
        parser_id = str(body.get("parser_id") or "general")
        return config_service.create_dataset(user, name, parser_id=parser_id)

    @router.get("/ragflow/datasets/{dataset_id}", include_in_schema=False)
    def get_ragflow_dataset(dataset_id: str, user: Principal = Depends(current_user)):
        """获取指定数据集详情，严格核实租户所有权。"""
        return config_service.get_dataset(user, dataset_id)

    @router.post("/ragflow/sync", include_in_schema=False)
    def sync_ragflow_knowledge_base(body: dict[str, Any] | None = None, user: Principal = Depends(current_user)):
        """将已发布方案片段或知识库内容同步至 RAGFlow 知识库中。"""
        payload = body or {}
        snippet_id = payload.get("snippet_id") or payload.get("id")
        return config_service.sync_knowledge_base(user, snippet_id, payload)

    application.include_router(router)
