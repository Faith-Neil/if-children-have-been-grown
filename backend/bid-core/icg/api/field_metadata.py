# 为什么有这个文件：字段元数据与数据字典配置相关的 API 路由端点（APP-M2-T024 / PRD v1.8 §5.10.3、§6.9）。
# 它解决什么问题：按领域拆分 API，提供分类字段元数据查询、字典类型列表、字典项增删改查及启停用接口。

from typing import Annotated
from fastapi import APIRouter, Depends, Query

from icg.domain.domain import DemoService, Principal
from icg.domain.field_metadata import (
    FieldMetadataService,
    FieldMetadataListResponse,
)
from icg.domain.dict_config import (
    DictConfigService,
    DictTypeListResponse,
    DictItemListResponse,
    DictItemModel,
    CreateDictItemRequest,
    UpdateDictItemRequest,
    DeleteDictItemResponse,
)
from icg.domain.workflow_schemas import v1_error_responses


def include_field_metadata_routes(application, service: DemoService, current_user) -> None:
    metadata_service = FieldMetadataService(service)
    application.state.field_metadata_service = metadata_service

    dict_service = getattr(application.state, "dict_config_service", None)
    if not dict_service:
        dict_service = DictConfigService()
        application.state.dict_config_service = dict_service
    dict_service.repository = service.repository
    setattr(service, "dict_config_service", dict_service)

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

    # 字典配置接口（A-03 / APP-M2-T024）
    @router.get(
        "/metadata/dict/types",
        response_model=DictTypeListResponse,
        operation_id="listDictTypes",
        summary="获取全部数据字典类型列表",
        description="返回系统当前注册的所有数据字典分类，含状态码表、需求分类、信源层级、SLA 指标等，以及各分类项统计。",
    )
    def list_dict_types(user: Principal = Depends(current_user)):
        return dict_service.list_dict_types(user)

    @router.get(
        "/metadata/dict/types/{type_code}/items",
        response_model=DictItemListResponse,
        operation_id="listDictItems",
        summary="获取指定字典类型下的代码项列表",
        description="按字典分类获取其下的代码项列表，支持关键词过滤与停用项过滤；内置项与租户自定义项根据当前登录用户角色隔离。",
    )
    def list_dict_items(
        type_code: str,
        include_disabled: Annotated[bool, Query(description="是否包含已停用代码项")] = True,
        keyword: Annotated[str | None, Query(description="按代码或名称模糊过滤")] = None,
        user: Principal = Depends(current_user),
    ):
        return dict_service.list_dict_items(
            type_code=type_code,
            principal=user,
            include_disabled=include_disabled,
            keyword=keyword,
        )

    @router.post(
        "/metadata/dict/items",
        response_model=DictItemModel,
        status_code=201,
        operation_id="createDictItem",
        summary="新增自定义字典代码项",
        description="仅平台管理员或公司管理员可新增字典项；若同类型下存在同名代码，将拦截返回 409 DICT_CODE_DUPLICATED。",
        responses=v1_error_responses(401, 403, 404, 409, 422, 500),
    )
    def create_dict_item(payload: CreateDictItemRequest, user: Principal = Depends(current_user)):
        return dict_service.create_dict_item(payload, user)

    @router.patch(
        "/metadata/dict/items/{type_code}/{item_code}",
        response_model=DictItemModel,
        operation_id="updateDictItem",
        summary="修改字典代码项与启停用",
        description="仅平台管理员或公司管理员可修改；支持更新显示标签、描述、排序权重，以及切换启用/停用状态（is_disabled）。",
        responses=v1_error_responses(401, 403, 404, 409, 422, 500),
    )
    def update_dict_item(
        type_code: str,
        item_code: str,
        payload: UpdateDictItemRequest,
        user: Principal = Depends(current_user),
    ):
        return dict_service.update_dict_item(type_code, item_code, payload, user)

    @router.delete(
        "/metadata/dict/items/{type_code}/{item_code}",
        response_model=DeleteDictItemResponse,
        operation_id="deleteDictItem",
        summary="物理删除未使用的自定义字典代码项",
        description="仅平台管理员或公司管理员可操作。核心红线：系统内置代码或已在业务中引用的代码严禁删除，拦截返回 409 DICT_ITEM_IN_USE，仅允许停用。",
        responses=v1_error_responses(401, 403, 404, 409, 422, 500),
    )
    def delete_dict_item(
        type_code: str,
        item_code: str,
        user: Principal = Depends(current_user),
    ):
        return dict_service.delete_dict_item(type_code, item_code, user)

    application.include_router(router)
