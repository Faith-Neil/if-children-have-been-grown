# 为什么有这个文件：章节编辑、锁定租约、草稿版本、单章检查与导出的 API 路由端点。
# 它解决什么问题：按领域拆分 API，提供章节维度的编辑台全套 HTTP 端点。

from typing import Annotated
from fastapi import Depends, Header, Response

from icg.infra.adapters import build_docx
from icg.domain.domain import DemoService, Principal
from icg.domain.idempotency import IDEMPOTENCY_HEADER_DESCRIPTION
from icg.domain.schemas import (
    AuditListResponse,
    ChapterListResponse,
    ChapterResponse,
    CheckResponse,
    DraftDiscardRequest,
    DraftDiscardResponse,
    DraftRequest,
    DraftResponse,
    EmptyRequest,
    ExportRequest,
    ExportResponse,
    LeaseRequest,
    LeaseResponse,
    LockRequest,
    ReleasedResponse,
    SuggestionRequest,
    SuggestionResponse,
    VersionListResponse,
    VersionRequest,
    VersionResponse,
)
from icg.domain.workflow_schemas import v1_error_responses


DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def error_responses(*statuses: int) -> dict:
    from icg.domain.workflow_schemas import V1Error
    descriptions = {
        401: "未登录或登录已失效",
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


def include_chapter_routes(application, service: DemoService, current_user) -> None:
    User = Annotated[Principal, Depends(current_user)]

    @application.get("/api/projects/{project_id}/chapters", response_model=ChapterListResponse,
                     operation_id="listChapters", responses=error_responses(401, 404))
    def chapters(project_id: str, user: User):
        return service.chapters(user, project_id)

    @application.get("/api/chapters/{chapter_id}", response_model=ChapterResponse, operation_id="getChapter",
                     responses=error_responses(401, 404))
    def chapter(chapter_id: str, user: User):
        return service.chapter(user, chapter_id)

    @application.post("/api/chapters/{chapter_id}/lock", response_model=LeaseResponse,
                      operation_id="acquireLegacyLock",
                      responses=error_responses(401, 403, 404, 409, 423, 428))
    def acquire_lock(chapter_id: str, body: LockRequest, user: User,
                     idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)] = None):
        return service.acquire_lock(user, chapter_id, body.takeover_reason, idempotency_key=idempotency_key)

    @application.post("/api/chapters/{chapter_id}/lock/renew", response_model=LeaseResponse,
                      operation_id="renewLegacyLock",
                      responses=error_responses(401, 403, 404, 409, 423, 428))
    def renew_lock(chapter_id: str, body: LeaseRequest, user: User,
                   idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)] = None):
        return service.renew_lock(user, chapter_id, body.lease_token, idempotency_key=idempotency_key)

    @application.post("/api/chapters/{chapter_id}/lock/release", response_model=ReleasedResponse,
                      operation_id="releaseLegacyLock",
                      responses=error_responses(401, 403, 404, 409, 423, 428))
    def release_lock(chapter_id: str, body: LeaseRequest, user: User,
                     idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)] = None):
        return service.release_lock(user, chapter_id, body.lease_token, idempotency_key=idempotency_key)

    # 旧 /api 入口留给验证页。产品入口使用同一套租约规则，错误体统一为 v1。
    @application.post("/api/v1/chapters/{chapter_id}/lock", response_model=LeaseResponse,
                      operation_id="acquireChapterLock",
                      responses=v1_error_responses(401, 403, 404, 409, 423, 428))
    def acquire_v1_lock(chapter_id: str, body: LockRequest, user: User,
                        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)] = None):
        return service.acquire_lock(user, chapter_id, body.takeover_reason, idempotency_key=idempotency_key)

    @application.post("/api/v1/chapters/{chapter_id}/lock/renew", response_model=LeaseResponse,
                      operation_id="renewChapterLock",
                      responses=v1_error_responses(401, 403, 404, 409, 423, 428))
    def renew_v1_lock(chapter_id: str, body: LeaseRequest, user: User,
                      idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)] = None):
        return service.renew_lock(user, chapter_id, body.lease_token, idempotency_key=idempotency_key)

    @application.post("/api/v1/chapters/{chapter_id}/lock/release", response_model=ReleasedResponse,
                      operation_id="releaseChapterLock",
                      responses=v1_error_responses(401, 403, 404, 409, 423, 428))
    def release_v1_lock(chapter_id: str, body: LeaseRequest, user: User,
                        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)] = None):
        return service.release_lock(user, chapter_id, body.lease_token, idempotency_key=idempotency_key)

    @application.put("/api/chapters/{chapter_id}/draft", response_model=DraftResponse, operation_id="saveDraft",
                     responses=error_responses(401, 403, 404, 409, 423, 428))
    def save_draft(chapter_id: str, body: DraftRequest, user: User,
                   idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)] = None):
        return service.save_draft(user, chapter_id, **body.model_dump(), idempotency_key=idempotency_key)

    @application.delete("/api/chapters/{chapter_id}/draft", response_model=DraftDiscardResponse,
                        operation_id="discardDraft", responses=error_responses(401, 404, 409, 428))
    def discard_draft(chapter_id: str, body: DraftDiscardRequest, user: User,
                      idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)] = None):
        return service.discard_draft(user, chapter_id, body.sequence, idempotency_key=idempotency_key)

    @application.post("/api/chapters/{chapter_id}/versions", response_model=VersionResponse,
                      operation_id="commitVersion",
                      responses=error_responses(401, 403, 404, 409, 423, 428))
    def commit_version(chapter_id: str, body: VersionRequest, user: User,
                       idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)] = None):
        # 正文 idempotency_key 保留给旧演示页和既有测试；请求头与正文同时出现时必须相同。
        return service.commit_version(user, chapter_id, **body.model_dump(), header_key=idempotency_key)

    @application.get("/api/chapters/{chapter_id}/versions", response_model=VersionListResponse,
                     operation_id="listVersions",
                     responses=error_responses(401, 404))
    def versions(chapter_id: str, user: User):
        return service.versions(user, chapter_id)

    @application.get("/api/chapters/{chapter_id}/audit", response_model=AuditListResponse,
                     operation_id="getAuditTrail",
                     responses=error_responses(401, 404))
    def audit(chapter_id: str, user: User):
        return service.audit(user, chapter_id)

    @application.post("/api/chapters/{chapter_id}/suggestions", response_model=SuggestionResponse,
                      operation_id="suggest",
                      responses=error_responses(401, 403, 404, 502))
    def suggest(chapter_id: str, body: SuggestionRequest, user: User):
        return service.suggest(user, chapter_id, body.instruction)

    @application.post("/api/chapters/{chapter_id}/checks", response_model=CheckResponse,
                      operation_id="checkChapter",
                      responses=error_responses(401, 403, 404, 409, 428))
    def check(chapter_id: str, body: EmptyRequest, user: User,
              idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)] = None):
        return service.check(user, chapter_id, idempotency_key=idempotency_key)

    @application.post("/api/chapters/{chapter_id}/exports", response_model=ExportResponse,
                      operation_id="exportChapter",
                      responses=error_responses(401, 403, 404, 409, 428))
    def export(chapter_id: str, body: ExportRequest, user: User,
               idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)] = None):
        return service.export(user, chapter_id, body.check_id, idempotency_key=idempotency_key)

    @application.get("/api/exports/{export_id}/file", response_class=Response, operation_id="downloadExportFile",
                     responses={**error_responses(401, 404, 409),
                                200: {"description": "已提交章节的真实 Word 演示文件",
                                      "content": {DOCX_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}},
                                      "headers": {"Content-Disposition": {"schema": {"type": "string"},
                                                  "description": "attachment 及实际 .docx 文件名"}}}})
    def download(export_id: str, user: User):
        record = service.download(user, export_id)
        return Response(content=build_docx(record),
                        media_type=DOCX_MEDIA_TYPE,
                        headers={"Content-Disposition": f'attachment; filename="{record.filename}"'})
