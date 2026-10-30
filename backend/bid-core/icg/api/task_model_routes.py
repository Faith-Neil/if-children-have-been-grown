# 为什么有这个文件：任务与模型对应表接口（PRD v1.8 §6.4、§5.10.5 A-10；APP-M2-T040）。
# 它解决什么问题：公司管理员读取和保存每类模型任务的首选、备用模型；保存时按“首选本地则备用只能本地”等口径核对。

from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from pydantic import Field

from icg.domain.domain import DemoService, Principal
from icg.domain.schemas import RequestBody, ResponseBody
from icg.domain.task_model_routes import TaskModelRouteService
from icg.domain.workflow_schemas import v1_error_responses


class TaskModelRoute(ResponseBody):
    task: str
    name: str
    local_only: bool = Field(description="该任务只能使用本地模型")
    primary_config_id: str | None = None
    fallback_config_id: str | None = None


class TaskModelRoutes(ResponseBody):
    tasks: list[TaskModelRoute]
    revision: int
    updated_by: str | None = None
    updated_at: str | None = None


class TaskModelRouteInput(RequestBody):
    task: str = Field(min_length=1, max_length=60)
    primary_config_id: str | None = Field(default=None, max_length=120, description="空为沿用项目绑定或本公司默认模型")
    fallback_config_id: str | None = Field(default=None, max_length=120)


class TaskModelRoutesUpdate(RequestBody):
    routes: list[TaskModelRouteInput] = Field(max_length=20)


def include_task_model_route_routes(application, service: DemoService, current_user) -> None:
    routes = TaskModelRouteService(service)
    router = APIRouter(prefix="/api/v1", responses=v1_error_responses(401, 403, 409, 422))

    @router.get("/task-model-routes", response_model=TaskModelRoutes, operation_id="listTaskModelRoutes",
                summary="本公司任务与模型对应表")
    def get_routes(user: Principal = Depends(current_user)):
        return routes.get(user)

    @router.put("/task-model-routes", response_model=TaskModelRoutes, operation_id="updateTaskModelRoute",
                summary="保存任务与模型对应表（公司管理员）",
                description="首选为本地模型时备用只能是本地；备用不能与首选相同；只能选本公司真实模型。If-Match 填当前 revision。")
    def put_routes(body: TaskModelRoutesUpdate, user: Principal = Depends(current_user),
                   if_match: str | None = Header(default=None)):
        expected = int(if_match.strip('"')) if if_match and if_match.strip('"').isdigit() else None
        return routes.update(user, body.model_dump(), expected)

    application.include_router(router)
