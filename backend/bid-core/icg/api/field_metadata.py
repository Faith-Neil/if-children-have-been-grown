# 为什么有这个文件：字段元数据相关的 API 路由端点。
# 它解决什么问题：按领域拆分 API，提供分类字段元数据查询接口。

from fastapi import APIRouter, Depends

from icg.domain.domain import DemoService, Principal
from icg.domain.field_metadata import (
    FieldMetadataService,
    FieldMetadataListResponse,
)
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
        description="按数据字典与表单/表格规范返回分类字段的元数据定义，包含字段键、标签、类型、必填、可编辑性、宽度、对齐、渲染类型等属性。",
    )
    def get_field_metadata(category: str, user: Principal = Depends(current_user)):
        return metadata_service.get_fields(category, user)

    application.include_router(router)
