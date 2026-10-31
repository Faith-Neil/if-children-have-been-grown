# 为什么有这个文件：为章节循环进度与人工处理队列（PRD v1.8 §5.7.6～5.7.7）以及解析后兜底扫描（§5.2.4）提供 /api/v1 路由。
# 它解决什么问题：列出待人工问题、查看本节循环、逐条处理或驳回、对本节重新检查；逐条处理疑似遗漏；统一错误体、版本号与幂等键。

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, Path, Query
from pydantic import Field

from icg.domain.domain import Principal
from icg.domain.idempotency import IDEMPOTENCY_HEADER_DESCRIPTION
from icg.domain.schemas import RequestBody, ResponseBody
from icg.domain.workflow_schemas import v1_error_responses


class HumanIssuePermissions(ResponseBody):
    resolve: bool
    reject: bool
    edit: bool = Field(default=False, description="能否在队列里直接改写本段")


class HumanIssue(ResponseBody):
    id: str
    number: str
    chapter_id: str
    volume: str
    code: str
    rule: str
    source: str
    level: str
    severity: str
    status: str
    route: str
    human_reason: str | None = None
    human_reason_label: str = ""
    paragraph_index: int
    quote: str
    message: str
    suggestion: str
    fix_count: int = 0
    loop_no: int = 1
    paragraph_text: str = Field(default="", description="问题所在段落的当前全文；不能在队列里编辑时为空")
    permissions: HumanIssuePermissions


class ChapterLoopState(ResponseBody):
    chapter_id: str
    loop_no: int
    kind: str
    status: str
    status_label: str
    stop_reason: str
    stop_reason_label: str
    rounds: list[dict[str, Any]]
    max_rounds: int
    rolled_back: bool
    started_at: str
    stale: bool
    loop_count: int
    started_by: str | None = None
    checked_revision: int | None = None
    result_revision: int | None = None
    # 轮次依据：任务、模型/配置、修正方式、实际输入规模、前章摘要接力（APP-M2-T131）
    meta: dict[str, Any] = Field(default_factory=dict)


class HumanQueueChapter(ResponseBody):
    chapter_id: str
    title: str
    volume: str
    number: int
    chapter_revision: int = Field(default=0, description="当前正式正文版本号，单段编辑时原样回传")
    assignee_id: str | None = None
    assignee_name: str | None = None
    volume_finalized: bool
    can_recheck: bool
    loop: ChapterLoopState | None = None
    issues: list[HumanIssue]


class HumanQueueReason(ResponseBody):
    reason: str
    label: str
    count: int


class HumanQueueSummary(ResponseBody):
    pending: int
    chapters: int
    by_reason: list[HumanQueueReason]


class HumanQueueResponse(ResponseBody):
    revision: int
    project_id: str
    volume: str
    deadline: str = ""
    summary: HumanQueueSummary
    chapters: list[HumanQueueChapter]


class ChapterLoopRow(ResponseBody):
    chapter_id: str
    title: str
    volume: str
    number: int
    chapter_revision: int
    has_content: bool
    assignee_name: str | None = None
    volume_finalized: bool
    can_recheck: bool
    loop: ChapterLoopState | None = None
    pending: int
    resolved: int


class ChapterLoopListResponse(ResponseBody):
    revision: int
    project_id: str
    volume: str
    totals: dict[str, int]
    chapters: list[ChapterLoopRow]


class ChapterLoopResponse(ResponseBody):
    revision: int
    chapter_id: str
    title: str
    volume: str
    chapter_revision: int
    loop: ChapterLoopState | None = None
    history: list[dict[str, Any]]
    counts: dict[str, int]
    issues: list[HumanIssue]


class HumanIssueResolveRequest(RequestBody):
    method: Literal["edited", "keep_placeholder", "replaced_variable"] = Field(description="处理方式")
    note: str = Field(default="", max_length=500, description="处理说明")
    also_issue_ids: list[str] = Field(default_factory=list, max_length=20, description="同一段落一起标为已处理的其他问题")


class HumanIssueRejectRequest(RequestBody):
    reason_type: Literal["false_positive", "not_adopted"] = Field(description="驳回类型：误报 / 不采纳")
    reason: str = Field(min_length=1, max_length=500, description="驳回理由")


class HumanIssueEditRequest(RequestBody):
    chapter_revision: int = Field(ge=0, description="读取队列时的章节版本号，用于发现他人已改动正文")
    new_text: str = Field(min_length=1, max_length=5000, description="改写后的整段文字，不含换行")
    note: str = Field(default="", max_length=500, description="修改说明")


class ChapterRecheckRequest(RequestBody):
    max_rounds: int = Field(default=3, ge=1, le=5, description="本次循环最多检查几轮")


class HumanIssueWriteResponse(ResponseBody):
    revision: int
    issue_ids: list[str]
    chapter_id: str
    chapter_status: str | None = None


class HumanIssueEditResponse(HumanIssueWriteResponse):
    chapter_revision: int
    paragraph_index: int
    paragraph_text: str


class ChapterRecheckResponse(ResponseBody):
    revision: int
    chapter_id: str
    chapter_revision: int
    content_fixed: bool
    interrupted: bool = Field(default=False, description="循环中途异常中断；正文未改动，可再次调用重试")
    error: dict[str, Any] | None = Field(default=None, description="中断时的错误说明 code/type/message")
    loop: ChapterLoopState | None = None
    stop_reason: str
    stop_reason_label: str
    pending_issues: int


ProjectId = Annotated[str, Path(description="项目ID")]
ChapterId = Annotated[str, Path(description="章节ID")]
IssueId = Annotated[str, Path(description="问题ID")]
VolumeFilter = Annotated[Literal["all", "technical", "business"], Query(description="分册筛选")]


class ScanHit(ResponseBody):
    id: str
    file_id: str
    filename: str = ""
    page: int
    quote: str
    terms: list[str]
    status: str
    state: str = Field(description="suspected 疑似遗漏 / covered 已覆盖 / added 已新增为条目 / excluded 已排除")
    covered_by: str | None = None
    reason: str = ""
    scan_version: str


class ScanSummary(ResponseBody):
    total: int
    suspected: int
    covered: int
    added: int
    excluded: int
    too_many: bool


class ScanHitListResponse(ResponseBody):
    revision: int
    project_id: str
    scan_version: str
    summary: ScanSummary
    can_handle: bool
    hits: list[ScanHit]


class ScanHitAddRequest(RequestBody):
    category: Literal["star", "disqualification"] = Field(description="新增条目的类别：星号 / 废标")
    volume: Literal["technical", "business"] = Field(default="technical", description="归入分册")
    text: str = Field(default="", max_length=2000, description="条款原文；为空时取命中原文")


class ScanHitExcludeRequest(RequestBody):
    reason: str = Field(min_length=1, max_length=500, description="排除理由")


class ScanHitWriteResponse(ResponseBody):
    revision: int
    hit: ScanHit
    requirement: dict[str, Any] | None = None


ScanHitId = Annotated[str, Path(description="兜底扫描命中ID")]


def include_chapter_loop_routes(application: Any, service: Any, current_user: Any) -> APIRouter:
    """注册章节循环与人工处理队列路由。"""
    router = APIRouter(prefix="/api/v1", responses=v1_error_responses(401, 403, 404, 409, 422, 428, 500))

    def workflow():
        current = getattr(application.state, "workflow", None)
        if current is None:
            from icg.domain.parsing import LocalTextParser
            from icg.domain.workflow_orchestrator import WorkflowService
            current = WorkflowService(service, LocalTextParser())
            application.state.workflow = current
        return current

    IfMatch = Header(default=None, alias="If-Match", description="项目当前版本号")
    IdemKey = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)

    @router.get("/projects/{project_id}/human-queue", response_model=HumanQueueResponse,
                operation_id="listHumanQueue", summary="人工处理队列",
                description="按章节列出自动修不了、须由人处理的问题；可按分册筛选。只读成员可看不可操作。")
    def list_queue(project_id: ProjectId,
                   volume: VolumeFilter = "all",
                   user: Principal = Depends(current_user)):
        return workflow().list_human_queue(user, project_id, volume)

    @router.get("/projects/{project_id}/chapter-loops", response_model=ChapterLoopListResponse,
                operation_id="listChapterLoops", summary="全部章节循环进度",
                description="按章节顺序列出每章最近一次生成→检查→修正→复查循环的状态、停止原因与待处理数，含尚未开始的章节。")
    def list_loops(project_id: ProjectId,
                   volume: VolumeFilter = "all",
                   user: Principal = Depends(current_user)):
        return workflow().list_chapter_loops(user, project_id, volume)

    @router.get("/projects/{project_id}/chapters/{chapter_id}/loop", response_model=ChapterLoopResponse,
                operation_id="getChapterLoop", summary="章节循环进度",
                description="返回本节最近一次循环的轮次、停止原因和本节全部问题记录。历史记录只读。")
    def get_loop(project_id: ProjectId, chapter_id: ChapterId,
                 user: Principal = Depends(current_user)):
        return workflow().get_chapter_loop(user, project_id, chapter_id)

    @router.post("/projects/{project_id}/human-queue/issues/{issue_id}/resolve", response_model=HumanIssueWriteResponse,
                 operation_id="resolveHumanIssue", summary="标记问题已处理",
                 description="本节负责人或项目负责人标记待人工问题已处理；额外承诺、披露类问题只能由项目负责人处理。")
    def resolve(project_id: ProjectId, issue_id: IssueId,
                body: HumanIssueResolveRequest, user: Principal = Depends(current_user),
                if_match: str | None = IfMatch, idempotency_key: str | None = IdemKey):
        return workflow().resolve_human_issue(user, project_id, issue_id, body.model_dump(), if_match, idempotency_key)

    @router.post("/projects/{project_id}/human-queue/issues/{issue_id}/reject", response_model=HumanIssueWriteResponse,
                 operation_id="rejectHumanIssue", summary="驳回问题",
                 description="驳回须填写理由；阻断级问题不能驳回，规则警告只能由项目负责人驳回。")
    def reject(project_id: ProjectId, issue_id: IssueId,
               body: HumanIssueRejectRequest, user: Principal = Depends(current_user),
               if_match: str | None = IfMatch, idempotency_key: str | None = IdemKey):
        return workflow().reject_human_issue(user, project_id, issue_id, body.model_dump(), if_match, idempotency_key)

    @router.post("/projects/{project_id}/human-queue/issues/{issue_id}/edit", response_model=HumanIssueEditResponse,
                 operation_id="editHumanIssueParagraph", summary="队列内改写问题所在段落",
                 description="只改写问题所在的这一段并生成新章节版本，同时把该问题标为已处理（已修改正文）。系统章节、定稿分册、他人正在编辑、锁定段落和基于旧正文的问题都会被拒绝。")
    def edit_paragraph(project_id: ProjectId, issue_id: IssueId,
                       body: HumanIssueEditRequest, user: Principal = Depends(current_user),
                       if_match: str | None = IfMatch, idempotency_key: str | None = IdemKey):
        return workflow().edit_human_issue_paragraph(user, project_id, issue_id, body.model_dump(), if_match, idempotency_key)

    @router.post("/projects/{project_id}/chapters/{chapter_id}/loop/recheck", response_model=ChapterRecheckResponse,
                 operation_id="recheckChapter", summary="重新检查本节",
                 description="以当前正式版本为起点开始新一次循环，不重新生成；只做不编造的确定性修正，修正产生新章节版本。")
    def recheck(project_id: ProjectId, chapter_id: ChapterId,
                body: ChapterRecheckRequest, user: Principal = Depends(current_user),
                if_match: str | None = IfMatch, idempotency_key: str | None = IdemKey):
        return workflow().recheck_chapter(user, project_id, chapter_id, body.model_dump(), if_match, idempotency_key)

    @router.get("/projects/{project_id}/parse/omissions", response_model=ScanHitListResponse,
                operation_id="listScanHits", summary="星号/废标兜底扫描结果",
                description="列出兜底扫描命中：疑似遗漏须由项目负责人逐条新增为条目或写明理由排除，处理完才能确认解析结果。")
    def list_hits(project_id: ProjectId, user: Principal = Depends(current_user)):
        return workflow().list_scan_hits(user, project_id)

    @router.post("/projects/{project_id}/parse/omissions/{hit_id}/add", response_model=ScanHitWriteResponse,
                 operation_id="addScanHitAsRequirement", summary="疑似遗漏新增为条目",
                 description="按命中原文新增（或升级同一原文的条目为）星号/废标条目，状态回到待确认。只能逐条处理。")
    def add_hit(project_id: ProjectId, hit_id: ScanHitId, body: ScanHitAddRequest,
                user: Principal = Depends(current_user), if_match: str | None = IfMatch,
                idempotency_key: str | None = IdemKey):
        return workflow().add_scan_hit(user, project_id, hit_id, body.model_dump(), if_match, idempotency_key)

    @router.post("/projects/{project_id}/parse/omissions/{hit_id}/exclude", response_model=ScanHitWriteResponse,
                 operation_id="excludeScanHit", summary="排除疑似遗漏",
                 description="排除须写明理由；只能逐条处理，不提供批量。")
    def exclude_hit(project_id: ProjectId, hit_id: ScanHitId, body: ScanHitExcludeRequest,
                    user: Principal = Depends(current_user), if_match: str | None = IfMatch,
                    idempotency_key: str | None = IdemKey):
        return workflow().exclude_scan_hit(user, project_id, hit_id, body.model_dump(), if_match, idempotency_key)

    application.include_router(router)
    return router
