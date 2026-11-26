# 为什么有这个文件：字段元数据 API 路由端点。
# 它解决什么问题：保留表单/表格渲染所需的只读字段元数据；ISSUE-056 已下线只写不读的字典配置孤岛，
# 不再暴露 /metadata/dict/* 管理接口。

from fastapi import APIRouter, Depends

from icg.domain.domain import DemoService, Principal
from icg.domain.field_metadata import FieldMetadataService, FieldMetadataListResponse
from icg.domain.workflow_schemas import v1_error_responses


def include_field_metadata_routes(application, service: DemoService, current_user) -> None:
    metadata_service = FieldMetadataService(service)
    application.state.field_metadata_service = metadata_service
    router = APIRouter(prefix="/api/v1", responses=v1_error_responses(401, 403, 404, 500))

    @router.get(
        "/metadata/fields/{category}",
        response_model=FieldMetadataListResponse,
        operation_id="getFieldMetadata",
        summary="获取指定分类的字段元数据",
        description="按表单/表格规范返回分类字段的元数据定义。",
    )
    def get_field_metadata(category: str, user: Principal = Depends(current_user)):
        return metadata_service.get_fields(category, user)

    application.include_router(router)
