# 为什么有这个文件：编辑台版本回退的接口（APP-M2-T175，PRD v1.8 §5.11.9）。
# 它解决什么问题：持有编辑锁的人把正文回退到某个历史版本，后台生成新版本（修改方式“版本回退”）并保留全部历史；
# 权限、编辑锁、来源依据、系统章节与锁定段落在后台重新核对。

from fastapi import APIRouter, Depends
from pydantic import Field

from icg.domain.domain import DemoService, Principal
from icg.domain.schemas import RequestBody, ResponseBody
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


def include_chapter_version_routes(application, service: DemoService, current_user) -> None:
    rollback = VersionRollbackService(service)
    router = APIRouter(prefix="/api/v1/projects/{project_id}/chapters/{chapter_id}",
                       responses=v1_error_responses(401, 403, 404, 409, 422, 423))

    @router.post("/rollback", response_model=RollbackResult, operation_id="rollbackChapterVersion",
                 summary="把正文回退到某个历史版本（生成新版本）",
                 description="须持有本章编辑锁与本节编辑权；有未提交草稿时 409 DRAFT_PENDING；目标与当前相同 409 ROLLBACK_NOOP；"
                             "系统生成章节 409 SYSTEM_CHAPTER_READONLY；会改动或删除锁定段落时 409 PARAGRAPH_LOCKED；来源依据过期 409 INPUT_FINGERPRINT_STALE。")
    def rollback_version(project_id: str, chapter_id: str, body: RollbackRequest, user: Principal = Depends(current_user)):
        return rollback.rollback(user, project_id, chapter_id, body.model_dump())

    application.include_router(router)
