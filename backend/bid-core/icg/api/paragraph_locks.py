# 为什么有这个文件：编辑台段落锁定的接口（APP-M2-T163，PRD v1.8 §5.11.8）。
# 它解决什么问题：页面按段落键锁定或解除锁定一个段落，并读回本章全部锁定段落（含锁定人、能否解锁）；
# 锁定后的段落在各写入路径由后台拒绝改动，页面不能绕过。

from fastapi import APIRouter, Depends
from pydantic import Field

from icg.domain.domain import DemoService, Principal
from icg.domain.paragraph_locks import ParagraphLockService
from icg.domain.schemas import RequestBody, ResponseBody
from icg.domain.workflow_schemas import v1_error_responses


class ParagraphLockRequest(RequestBody):
    paragraph_key: str = Field(min_length=1, max_length=200, description="当前正文中的段落键（章节接口 paragraphs[].key）")
    base_revision: int = Field(ge=1, description="页面看到的正文版本；不是最新版本时 409")
    reason: str = Field(default="", max_length=200, description="锁定原因（可选），写入审计")


class ParagraphLockItem(ResponseBody):
    paragraph_key: str = Field(description="该段落在当前正文中的段落键")
    hash: str
    excerpt: str = Field(description="段落开头 60 字")
    reason: str
    locked_by: str
    locked_by_name: str
    locked_at: str = Field(json_schema_extra={"format": "date-time"})
    revision: int = Field(description="锁定时的正文版本")
    line_start: int | None = Field(description="当前正文中的起始行（0 起）；当前正文找不到原样段落时为 null")
    line_end: int | None
    present: bool = Field(description="当前正文中是否仍有原样的这一段")
    can_unlock: bool = Field(description="当前登录人能否解除（锁定人或项目负责人）")


class ParagraphLockList(ResponseBody):
    chapter_id: str
    revision: int
    locks: list[ParagraphLockItem]


def include_paragraph_lock_routes(application, service: DemoService, current_user) -> None:
    locks = ParagraphLockService(service)
    router = APIRouter(prefix="/api/v1/projects/{project_id}/chapters/{chapter_id}/paragraph-locks",
                       responses=v1_error_responses(401, 403, 404, 409, 422))

    @router.get("", response_model=ParagraphLockList, operation_id="listParagraphLocks", summary="本章锁定的段落")
    def list_locks(project_id: str, chapter_id: str, user: Principal = Depends(current_user)):
        return locks.list(user, project_id, chapter_id)

    @router.post("", response_model=ParagraphLockList, operation_id="lockParagraph", summary="锁定一个段落",
                 description="须有本节编辑权；系统生成章节整章只读，不能逐段锁。锁定后手改提交、对话助手、AI 建议采纳、答案卡、"
                             "草稿自动提交都不能改动或删除该段（409 PARAGRAPH_LOCKED），章节循环不自动修正该段的问题。")
    def lock(project_id: str, chapter_id: str, body: ParagraphLockRequest, user: Principal = Depends(current_user)):
        return locks.lock(user, project_id, chapter_id, body.model_dump())

    @router.delete("/{paragraph_key}", response_model=ParagraphLockList, operation_id="unlockParagraph",
                   summary="解除段落锁定", description="只有锁定人或项目负责人可以解除。")
    def unlock(project_id: str, chapter_id: str, paragraph_key: str, user: Principal = Depends(current_user)):
        return locks.unlock(user, project_id, chapter_id, paragraph_key)

    application.include_router(router)
