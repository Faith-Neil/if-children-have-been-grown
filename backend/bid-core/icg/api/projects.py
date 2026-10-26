# 为什么有这个文件：项目生命周期与项目管理的 API 路由端点。
# 它解决什么问题：按领域拆分 API，提供项目查询、新建与详情查询接口（支持 legacy 与 v1 契约）。

from typing import Annotated
from fastapi import Depends, Header

from icg.domain.domain import DemoService, Principal
from icg.domain.idempotency import IDEMPOTENCY_HEADER_DESCRIPTION
from icg.domain.schemas import ProjectListResponse, ProjectRequest, ProjectResponse
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


def include_project_routes(application, service: DemoService, current_user) -> None:
    User = Annotated[Principal, Depends(current_user)]

    @application.get("/api/projects", response_model=ProjectListResponse, operation_id="listProjects",
                     responses=error_responses(401))
    def projects(user: User):
        return service.projects(user)

    @application.get("/api/projects/{project_id}", response_model=ProjectResponse, operation_id="getProject",
                     responses=error_responses(401, 404))
    def project(project_id: str, user: User):
        return service.project(user, project_id)

    @application.post("/api/projects", response_model=ProjectResponse, operation_id="createProject",
                      responses=error_responses(401, 403, 409, 428))
    def create_project(body: ProjectRequest, user: User,
                       idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)] = None):
        return service.create_project(user, body.name, idempotency_key=idempotency_key)

    @application.get("/api/v1/projects", response_model=ProjectListResponse, operation_id="listV1Projects",
                     responses=v1_error_responses(401))
    def list_v1_projects(user: User):
        return service.projects(user)

    @application.post("/api/v1/projects", response_model=ProjectResponse, operation_id="createV1Project",
                      responses=v1_error_responses(401, 403, 409, 428))
    def create_v1_project(body: ProjectRequest, user: User,
                          idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)] = None):
        return service.create_project(user, body.name, idempotency_key=idempotency_key)

    @application.get("/api/v1/projects/{project_id}", response_model=ProjectResponse, operation_id="getV1Project",
                     responses=v1_error_responses(401, 404))
    def get_v1_project(project_id: str, user: User):
        return service.project(user, project_id)
