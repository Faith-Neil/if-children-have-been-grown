# 为什么有这个文件：为分册定稿（finalize）状态机与安全门禁提供标准 /api/v1 路由端点。
# 它解决什么问题：按领域分包架构组织分册定稿与状态查询 API，统一错误体与 OpenAPI 契约。

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Path
from pydantic import BaseModel, Field

from icg.domain.domain import Principal
from icg.domain.idempotency import IDEMPOTENCY_HEADER_DESCRIPTION
from icg.domain.schemas import RequestBody, ResponseBody
from icg.domain.workflow_schemas import v1_error_responses


class VolumeFinalizeRequest(RequestBody):
    check_id: str | None = Field(default=None, max_length=100, description="可选的检查批次ID")


class VolumeUnlockRequest(RequestBody):
    reason: str = Field(min_length=1, max_length=500, description="解锁已定稿分册的原因说明")


class CrossReviewState(ResponseBody):
    status: str = Field(description="none 未指定 / pending 待复核 / approved 复核通过 / returned 退回修改")
    stale: bool = False
    reviewer_id: str | None = None
    reviewer_name: str | None = None
    assigned_by: str | None = None
    assigned_at: str | None = None
    decided_at: str | None = None
    decision_note: str = ""
    history: list[dict[str, Any]] = Field(default_factory=list)


class CrossReviewAssignRequest(RequestBody):
    reviewer_id: str = Field(min_length=1, max_length=120, description="交叉复核人账号ID（不能是本分册编写人）")


class CrossReviewConfirmRequest(RequestBody):
    decision: str = Field(pattern="^(approved|returned)$", description="approved 复核通过 / returned 退回修改")
    note: str = Field(default="", max_length=500, description="复核意见；退回时必填")


class CrossReviewResponse(ResponseBody):
    revision: int
    volume_id: str
    cross_review: CrossReviewState


class VolumeStatus(ResponseBody):
    volume_id: str
    project_id: str
    is_finalized: bool
    finalized_by: str | None = None
    finalized_at: str | None = None
    unlocked_by: str | None = None
    unlocked_at: str | None = None
    unlock_reason: str | None = None
    cross_review: CrossReviewState | None = None
    pending_human_issues: int = 0


class VolumeFinalizeResponse(ResponseBody):
    revision: int
    project_id: str
    volume_id: str
    is_finalized: bool
    finalized_by: str | None = None
    finalized_at: str | None = None
    volume: VolumeStatus | None = None


class VolumeStatusResponse(ResponseBody):
    revision: int
    project_id: str
    volume_id: str
    is_finalized: bool
    finalized_by: str | None = None
    finalized_at: str | None = None
    unlocked_by: str | None = None
    unlocked_at: str | None = None
    unlock_reason: str | None = None
    cross_review: CrossReviewState | None = None
    volume: VolumeStatus | None = None


class VolumeListResponse(ResponseBody):
    revision: int
    project_id: str
    volumes: list[VolumeStatus]


def include_volume_routes(application: Any, service: Any, current_user: Any) -> APIRouter:
    """注册分册定稿与状态机路由至 /api/v1。"""
    router = APIRouter(
        prefix="/api/v1",
        responses=v1_error_responses(401, 403, 404, 409, 422, 428, 500),
    )

    @router.post(
        "/projects/{project_id}/volumes/{volume_id}/finalize",
        response_model=VolumeFinalizeResponse,
        operation_id="finalizeVolume",
        summary="分册定稿与安全门禁锁定",
        description="核对章节锁定、正文提交与 blocker 缺陷前置门禁，通过后流转至已定稿状态并锁定分册。",
    )
    def finalize_volume(
        project_id: Annotated[str, Path(description="项目ID")],
        volume_id: Annotated[str, Path(description="分册标识，如 technical 或 business")],
        body: VolumeFinalizeRequest | None = None,
        user: Principal = Depends(current_user),
        if_match: str | None = Header(default=None, alias="If-Match"),
        idempotency_key: str | None = Header(
            default=None,
            alias="Idempotency-Key",
            description=IDEMPOTENCY_HEADER_DESCRIPTION,
        ),
    ):
        workflow = getattr(application.state, "workflow", None)
        if workflow is None:
            from icg.domain.workflow_orchestrator import WorkflowService
            from icg.domain.parsing import LocalTextParser
            workflow = WorkflowService(service, LocalTextParser())
            application.state.workflow = workflow

        payload = body.model_dump() if body is not None else {}
        return workflow.finalize_volume(
            user,
            project_id,
            volume_id,
            payload=payload,
            expected=if_match,
            key=idempotency_key,
        )

    @router.post(
        "/projects/{project_id}/volumes/{volume_id}/unlock",
        response_model=VolumeStatusResponse,
        operation_id="unlockVolume",
        summary="解锁定稿分册以支持修改",
        description="解锁已定稿分册，记录解锁原因与时间戳，流转至未定稿状态。",
    )
    def unlock_volume(
        project_id: Annotated[str, Path(description="项目ID")],
        volume_id: Annotated[str, Path(description="分册标识，如 technical 或 business")],
        body: VolumeUnlockRequest,
        user: Principal = Depends(current_user),
        if_match: str | None = Header(default=None, alias="If-Match"),
        idempotency_key: str | None = Header(
            default=None,
            alias="Idempotency-Key",
            description=IDEMPOTENCY_HEADER_DESCRIPTION,
        ),
    ):
        workflow = getattr(application.state, "workflow", None)
        if workflow is None:
            from icg.domain.workflow_orchestrator import WorkflowService
            from icg.domain.parsing import LocalTextParser
            workflow = WorkflowService(service, LocalTextParser())
            application.state.workflow = workflow

        return workflow.unlock_volume(
            user,
            project_id,
            volume_id,
            payload=body.model_dump(),
            expected=if_match,
            key=idempotency_key,
        )

    @router.get(
        "/projects/{project_id}/volumes/{volume_id}",
        response_model=VolumeStatusResponse,
        operation_id="getVolumeStatus",
        summary="获取指定分册定稿状态",
    )
    def get_volume_status(
        project_id: Annotated[str, Path(description="项目ID")],
        volume_id: Annotated[str, Path(description="分册标识")],
        user: Principal = Depends(current_user),
    ):
        workflow = getattr(application.state, "workflow", None)
        if workflow is None:
            from icg.domain.workflow_orchestrator import WorkflowService
            from icg.domain.parsing import LocalTextParser
            workflow = WorkflowService(service, LocalTextParser())
            application.state.workflow = workflow

        return workflow.get_volume_status(user, project_id, volume_id)

    @router.get(
        "/projects/{project_id}/volumes",
        response_model=VolumeListResponse,
        operation_id="listVolumesStatus",
        summary="获取项目中所有分册定稿状态列表",
    )
    def list_volumes_status(
        project_id: Annotated[str, Path(description="项目ID")],
        user: Principal = Depends(current_user),
    ):
        workflow = getattr(application.state, "workflow", None)
        if workflow is None:
            from icg.domain.workflow_orchestrator import WorkflowService
            from icg.domain.parsing import LocalTextParser
            workflow = WorkflowService(service, LocalTextParser())
            application.state.workflow = workflow

        return workflow.list_volumes_status(user, project_id)

    def _workflow():
        workflow = getattr(application.state, "workflow", None)
        if workflow is None:
            from icg.domain.workflow_orchestrator import WorkflowService
            from icg.domain.parsing import LocalTextParser
            workflow = WorkflowService(service, LocalTextParser())
            application.state.workflow = workflow
        return workflow

    @router.post(
        "/projects/{project_id}/volumes/{volume_id}/cross-review",
        response_model=CrossReviewResponse,
        operation_id="assignCrossReviewer",
        summary="指定分册交叉复核人",
        description="项目负责人或本册负责人指定一名不是本分册编写人的项目成员做定稿前交叉复核（PRD v1.8 §2.3）。",
    )
    def assign_cross_reviewer(
        project_id: Annotated[str, Path(description="项目ID")],
        volume_id: Annotated[str, Path(description="分册标识（technical / business）")],
        body: CrossReviewAssignRequest,
        user: Principal = Depends(current_user),
        if_match: str | None = Header(default=None, alias="If-Match"),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION),
    ):
        return _workflow().assign_cross_reviewer(user, project_id, volume_id, body.model_dump(), if_match, idempotency_key)

    @router.post(
        "/projects/{project_id}/volumes/{volume_id}/cross-review/confirm",
        response_model=CrossReviewResponse,
        operation_id="confirmCrossReview",
        summary="确认分册交叉复核",
        description="被指定的复核人确认通过或退回；通过时绑定本分册章节版本快照，正文之后改动即失效。",
    )
    def confirm_cross_review(
        project_id: Annotated[str, Path(description="项目ID")],
        volume_id: Annotated[str, Path(description="分册标识（technical / business）")],
        body: CrossReviewConfirmRequest,
        user: Principal = Depends(current_user),
        if_match: str | None = Header(default=None, alias="If-Match"),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION),
    ):
        return _workflow().confirm_cross_review(user, project_id, volume_id, body.model_dump(), if_match, idempotency_key)

    application.include_router(router)
    return router
