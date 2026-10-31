# 为什么有这个文件：响应矩阵单条条款的三路证据候选（APP-M2-T118）的 /api/v1 路由与响应模型。
# 它解决什么问题：原“智能匹配”只能批量返回弱类型 dict，抽屉里看不出候选来自规则匹配、知识库片段还是历史标书，
# 也看不出为什么不能挂接；这里按路由分类并写明版本、来源、引用理由和不可挂接原因。挂接仍走条款 PATCH。

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Path
from pydantic import Field

from icg.domain.domain import Principal
from icg.domain.schemas import ResponseBody
from icg.domain.workflow_schemas import v1_error_responses


class EvidenceCandidate(ResponseBody):
    route: Literal["structured", "snippet", "history"] = Field(description="structured 资料库规则匹配 / snippet 知识库片段 / history 历史标书仅参考")
    route_label: str
    id: str | None = None
    name: str | None = None
    version: int | str | None = Field(default=None, description="资料或片段所属资料的版本")
    source: str = Field(description="来源：资料库 / 公司知识库 / 历史标书")
    score: float | None = None
    valid_until: str | None = None
    cite_reason: str = Field(default="", description="为什么推荐")
    blocked_reason: str | None = Field(default=None, description="不能挂接的原因；可挂接时为空")
    attachable: bool
    already_attached: bool = False
    content_preview: str | None = Field(default=None, description="片段或历史标书内容预览，仅供查看")


class EvidenceCandidatesResponse(ResponseBody):
    project_id: str
    requirement_id: str
    revision: int
    kb_status: Literal["available", "unavailable", "disabled"] = Field(description="知识库状态；不可用时仍返回资料库规则匹配结果")
    can_attach: bool = Field(description="当前调用人是否有权挂接证据；只读成员为 false")
    candidates: list[EvidenceCandidate]
    notice: str


def include_evidence_candidate_routes(application: Any, service: Any, current_user: Any) -> APIRouter:
    router = APIRouter(prefix="/api/v1", responses=v1_error_responses(401, 403, 404, 409, 422, 500))

    def workflow():
        current = getattr(application.state, "workflow", None)
        if current is None:
            from icg.domain.parsing import LocalTextParser
            from icg.domain.workflow_orchestrator import WorkflowService
            current = WorkflowService(service, LocalTextParser())
            application.state.workflow = current
        return current

    @router.get("/projects/{project_id}/requirements/{requirement_id}/evidence-candidates",
                response_model=EvidenceCandidatesResponse, operation_id="listEvidenceCandidates",
                summary="单条条款的三路证据候选",
                description="按资料库规则匹配、知识库片段、历史标书三路返回候选，只读不挂接；片段与历史标书不可挂接。")
    def list_candidates(project_id: Annotated[str, Path(description="项目ID")],
                        requirement_id: Annotated[str, Path(description="条款ID")],
                        user: Principal = Depends(current_user)):
        return workflow().list_evidence_candidates(user, project_id, requirement_id)

    application.include_router(router)
    return router
