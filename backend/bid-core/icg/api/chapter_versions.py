# 为什么有这个文件：编辑台版本回退与变量节点的接口（APP-M2-T175、T164，PRD v1.8 §5.11.9、§5.11.2）。
# 它解决什么问题：持有编辑锁的人把正文回退到某个历史版本，后台生成新版本（修改方式“版本回退”）并保留全部历史；
# 权限、编辑锁、来源依据、系统章节与锁定段落在后台重新核对。
# 变量节点：按当前数据源解析正文里的变量，返回显示值（或掩码）与失效原因；只读，不写正文。

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import Field

from icg.domain.domain import DemoService, Principal
from icg.domain.schemas import RequestBody, ResponseBody
from icg.domain.variable_nodes import VariableNodeService
from icg.domain.version_rollback import VersionRollbackService
from icg.domain.workflow_schemas import v1_error_responses


class RollbackRequest(RequestBody):
    lease_token: str = Field(min_length=1, max_length=200, description="本章编辑锁凭据")
    base_revision: int = Field(ge=1, description="页面看到的当前正文版本；不是最新时 409")
    target_revision: int = Field(ge=1, description="回退到的历史版本号")
    input_fingerprint: str | None = Field(default=None, max_length=200, description="当前来源依据指纹；项目有条款、事实或 SLA 时必填")


class RollbackResult(ResponseBody):
    revision: int = Field(description="回退后生成的新版本号")
    content: str
    rollback_from: int = Field(description="回退到的历史版本号")


class VariableResolveRequest(RequestBody):
    content: str | None = Field(default=None, max_length=200_000,
                                description="要解析的正文（编辑中的文字）；不传则解析已提交正文")


class VariableNode(ResponseBody):
    token: str = Field(description="正文中的变量原文，例如 {{fact:f-1}}")
    kind: Literal["fact", "sla"]
    ref: str = Field(description="事实 ID 或服务承诺变量键；格式不完整时为空")
    label: str = Field(description="字段名或指标名")
    start: int = Field(description="在正文中的起始字符位置")
    end: int
    line: int = Field(description="所在行（0 起）")
    display: str = Field(description="当前已确认的取值（含单位）；敏感号码为掩码；失效时为空")
    masked: bool
    status: Literal["valid", "unknown", "invalid"] = Field(description="valid 有效；unknown 数据源里没有；invalid 未确认、来源失效或单位不符")
    code: str | None = Field(description="失效时对应的错误码")
    message: str
    source: Literal["facts", "matrix"] = Field(description="去哪里改取值：facts 项目事实表；matrix 服务承诺矩阵")


class VariableNodeList(ResponseBody):
    chapter_id: str
    revision: int
    variables: list[VariableNode]
    invalid: int = Field(description="失效变量个数")


def include_chapter_version_routes(application, service: DemoService, current_user) -> None:
    rollback = VersionRollbackService(service)
    variables = VariableNodeService(service)
    router = APIRouter(prefix="/api/v1/projects/{project_id}/chapters/{chapter_id}",
                       responses=v1_error_responses(401, 403, 404, 409, 422, 423))

    @router.post("/rollback", response_model=RollbackResult, operation_id="rollbackChapterVersion",
                 summary="把正文回退到某个历史版本（生成新版本）",
                 description="须持有本章编辑锁与本节编辑权；有未提交草稿时 409 DRAFT_PENDING；目标与当前相同 409 ROLLBACK_NOOP；"
                             "系统生成章节 409 SYSTEM_CHAPTER_READONLY；会改动或删除锁定段落时 409 PARAGRAPH_LOCKED；来源依据过期 409 INPUT_FINGERPRINT_STALE；"
                             "会写回当前已失效的变量时 409 FACT_VARIABLE_INVALID / SLA_VARIABLE_*。")
    def rollback_version(project_id: str, chapter_id: str, body: RollbackRequest, user: Principal = Depends(current_user)):
        return rollback.rollback(user, project_id, chapter_id, body.model_dump())

    @router.post("/variables", response_model=VariableNodeList, operation_id="resolveChapterVariables",
                 summary="解析正文中的变量节点",
                 description="按当前项目事实与服务承诺矩阵解析 {{fact:…}} / {{sla:…}}：返回当前已确认取值（敏感号码为掩码）或失效原因。"
                             "只读，有本章读取权限即可；不写正文、不改取值。")
    def resolve_variables(project_id: str, chapter_id: str, body: VariableResolveRequest, user: Principal = Depends(current_user)):
        return variables.resolve(user, project_id, chapter_id, body.content)

    application.include_router(router)
