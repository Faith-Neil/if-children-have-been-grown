# 为什么有这个文件：对外暴露公司知识库管控接口（/api/v1/kb-admin/...）。
# 它解决什么问题：资料管理员与公司管理员在本系统内完成 RAGFlow 知识库的全部读写：模型与检索参数、
# ICG 摄入流程部署、数据集建立/重解析/重建/删除、原件上传、文档与分块修正、元数据汇总、检索试查和审计。

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, Query
from pydantic import Field

from icg.domain.domain import DemoService, DomainError, Principal
from icg.domain.kb_admin import KbAdminService
from icg.domain.schemas import RequestBody, ResponseBody
from icg.domain.workflow_schemas import v1_error_responses

Kind = Literal["library", "history", "certificate"]
FileKind = Literal["history", "certificate"]


class KbAdminResult(ResponseBody):
    """管控接口统一响应体：字段随接口而定，见各接口说明。"""


class ProfileOverrides(RequestBody):
    chunk_token_size: int | None = Field(default=None, ge=128, le=2048)
    questions_top_n: int | None = Field(default=None, ge=0, le=10)
    keywords_top_n: int | None = Field(default=None, ge=0, le=10)
    extra_heading_patterns: list[str] | None = Field(default=None, max_length=20)


class KbSettingsUpdate(RequestBody):
    embedding_model: str | None = Field(default=None, max_length=255, description="model@instance@provider；更换后需重建数据集")
    rerank_id: str | None = Field(default=None, max_length=255)
    llm_id: str | None = Field(default=None, max_length=255, description="摄入流程抽取关键词/问题/元数据用的对话模型；生产须为内网模型")
    similarity_threshold: float | None = Field(default=None, ge=0, le=1)
    keywords_weight: float | None = Field(default=None, ge=0, le=1)
    use_pipelines: bool | None = None
    language: str | None = Field(default=None, max_length=32)
    profiles: dict[str, ProfileOverrides] | None = None


class KbDeployRequest(RequestBody):
    kinds: list[Kind] | None = None


class KbDeleteDataset(RequestBody):
    confirm_name: str = Field(min_length=1, max_length=200)


class KbUpload(RequestBody):
    filename: str = Field(min_length=1, max_length=200)
    content_base64: str = Field(min_length=1)
    content_type: str = Field(default="", max_length=200)
    metadata: dict[str, str] = Field(default_factory=dict, description="人工补充的文档元数据，例如 project_name、purchaser")


class KbDocumentPatch(RequestBody):
    enabled: bool | None = None
    metadata: dict[str, str] | None = None


class KbChunkPatch(RequestBody):
    content: str | None = Field(default=None, min_length=1, max_length=20000)
    important_keywords: list[str] | None = Field(default=None, max_length=50)
    questions: list[str] | None = Field(default=None, max_length=20)
    available: bool | None = None


class KbRetrievalTest(RequestBody):
    query: str = Field(min_length=1, max_length=2000)
    kinds: list[Literal["evidence", "snippet", "history"]] | None = None
    limit: int = Field(default=8, ge=1, le=20)
    similarity_threshold: float | None = Field(default=None, ge=0, le=1)
    keywords_weight: float | None = Field(default=None, ge=0, le=1)
    rerank_id: str | None = Field(default=None, max_length=255)


def _revision(if_match: str | None) -> int:
    if if_match is None:
        raise DomainError(428, "IF_MATCH_REQUIRED", "此操作需要最新版本号，请刷新页面再保存。")
    raw = if_match.strip().strip('"')
    if not raw.isdigit():
        raise DomainError(409, "VERSION_CONFLICT", "数据已被更新，请刷新核对后再保存。")
    return int(raw)


def include_kb_admin_routes(application, service: DemoService, current_user) -> None:
    admin = KbAdminService(service, service.knowledge_base)
    application.state.kb_admin = admin
    router = APIRouter(prefix="/api/v1/kb-admin", tags=["knowledge-base-admin"],
                       responses=v1_error_responses(401, 403, 404, 409, 413, 422, 428, 500, 502))
    R = KbAdminResult

    @router.get("/overview", response_model=R, operation_id="getKbAdminOverview")
    def overview(user: Principal = Depends(current_user)):
        """连接状态、设置、各类数据集与摄入流程部署情况、同步计数。"""
        return admin.overview(user)

    @router.get("/models", response_model=R, operation_id="listKbModels")
    def models(user: Principal = Depends(current_user)):
        """RAGFlow 租户已配置的嵌入、重排、对话模型（供设置下拉）。"""
        return admin.models(user)

    @router.get("/settings", response_model=R, operation_id="getKbSettings")
    def get_settings(user: Principal = Depends(current_user)):
        """知识库设置；revision 用于 If-Match。"""
        return admin.get_settings(user)

    @router.put("/settings", response_model=R, operation_id="updateKbSettings")
    def put_settings(body: KbSettingsUpdate, user: Principal = Depends(current_user),
                     if_match: str | None = Header(default=None, alias="If-Match")):
        """修改检索参数、嵌入/重排/抽取模型与流程可调项。更换嵌入模型会把数据集标为需要重建。"""
        payload = body.model_dump(exclude_unset=True)
        if "profiles" in payload and payload["profiles"] is not None:
            payload["profiles"] = {k: {f: v for f, v in o.items() if v is not None} for k, o in payload["profiles"].items()}
        return admin.update_settings(user, payload, _revision(if_match))

    @router.get("/pipelines", response_model=R, operation_id="listKbPipelines")
    def pipelines(user: Principal = Depends(current_user)):
        """ICG 摄入流程定义与本公司部署情况。"""
        return admin.pipelines(user)

    @router.get("/pipelines/{key}/dsl", response_model=R, operation_id="getKbPipelineDsl")
    def pipeline_dsl(key: str, user: Principal = Depends(current_user)):
        """按当前设置生成的 RAGFlow 画布 DSL（预览，不部署）。"""
        return admin.pipeline_dsl(user, key)

    @router.post("/pipelines/deploy", response_model=R, operation_id="deployKbPipelines")
    def deploy(body: KbDeployRequest, user: Principal = Depends(current_user)):
        """部署或升级 ICG 摄入流程，建立并绑定各类数据集。已有文档需重新解析才按新流程切块。"""
        return admin.deploy(user, body.kinds)

    @router.get("/datasets", response_model=R, operation_id="listKbDatasets")
    def datasets(user: Principal = Depends(current_user)):
        return admin.datasets(user)

    @router.post("/datasets/{kind}/ensure", response_model=R, operation_id="ensureKbDataset")
    def ensure(kind: Kind, user: Principal = Depends(current_user)):
        return admin.ensure(user, kind)

    @router.post("/datasets/{kind}/reparse", response_model=R, operation_id="reparseKbDataset")
    def reparse(kind: Kind, user: Principal = Depends(current_user)):
        """按当前流程重新解析该类全部文档。"""
        return admin.reparse(user, kind)

    @router.post("/datasets/{kind}/rebuild", response_model=R, operation_id="rebuildKbDataset")
    def rebuild(kind: Kind, user: Principal = Depends(current_user)):
        """换嵌入模型后重建：新建数据集、迁移原件、重新同步资料、删除旧数据集。"""
        return admin.rebuild(user, kind)

    @router.post("/datasets/{kind}/delete", response_model=R, operation_id="deleteKbDataset")
    def delete_dataset(kind: Kind, body: KbDeleteDataset, user: Principal = Depends(current_user)):
        """删除整类数据集（仅公司管理员，需输入数据集全名确认）。"""
        return admin.delete_dataset(user, kind, body.confirm_name)

    @router.get("/datasets/{kind}/metadata", response_model=R, operation_id="getKbMetadataSummary")
    def metadata(kind: Kind, user: Principal = Depends(current_user)):
        return admin.metadata_summary(user, kind)

    @router.get("/datasets/{kind}/documents", response_model=R, operation_id="listKbDocuments")
    def documents(kind: Kind, page: int = Query(default=1, ge=1), page_size: int = Query(default=30, ge=1, le=100),
                  keywords: str | None = Query(default=None, max_length=100), user: Principal = Depends(current_user)):
        return admin.documents(user, kind, page=page, page_size=page_size, keywords=keywords)

    @router.post("/datasets/{kind}/documents", response_model=R, operation_id="uploadKbDocument")
    def upload(kind: FileKind, body: KbUpload, user: Principal = Depends(current_user)):
        """上传历史投标文件或证书附件原件（base64），按对应 ICG 流程解析。"""
        return admin.upload(user, kind, body.model_dump())

    @router.patch("/datasets/{kind}/documents/{document_id}", response_model=R, operation_id="patchKbDocument")
    def patch_document(kind: Kind, document_id: str, body: KbDocumentPatch, user: Principal = Depends(current_user)):
        """启停文档、修改原件元数据。资料与片段文档的元数据由系统维护。"""
        return admin.update_document(user, kind, document_id, body.model_dump(exclude_unset=True))

    @router.post("/datasets/{kind}/documents/{document_id}/reparse", response_model=R, operation_id="reparseKbDocument")
    def reparse_document(kind: Kind, document_id: str, user: Principal = Depends(current_user)):
        return admin.reparse_document(user, kind, document_id)

    @router.post("/datasets/{kind}/documents/{document_id}/stop", response_model=R, operation_id="stopKbDocumentParse")
    def stop(kind: Kind, document_id: str, user: Principal = Depends(current_user)):
        return admin.stop_parse(user, kind, document_id)

    @router.delete("/datasets/{kind}/documents/{document_id}", response_model=R, operation_id="deleteKbDocument")
    def delete_document(kind: Kind, document_id: str, user: Principal = Depends(current_user)):
        return admin.delete_document(user, kind, document_id)

    @router.get("/datasets/{kind}/documents/{document_id}/chunks", response_model=R, operation_id="listKbChunks")
    def chunks(kind: Kind, document_id: str, keywords: str | None = Query(default=None, max_length=100),
               page: int = Query(default=1, ge=1), page_size: int = Query(default=30, ge=1, le=100),
               user: Principal = Depends(current_user)):
        return admin.chunks(user, kind, document_id, keywords=keywords, page=page, page_size=page_size)

    @router.patch("/datasets/{kind}/documents/{document_id}/chunks/{chunk_id}", response_model=R,
                  operation_id="patchKbChunk")
    def patch_chunk(kind: Kind, document_id: str, chunk_id: str, body: KbChunkPatch,
                    user: Principal = Depends(current_user)):
        """修正分块关键词/问题、停用错误分块；原件分块可改正文。"""
        return admin.update_chunk(user, kind, document_id, chunk_id, body.model_dump(exclude_unset=True))

    @router.post("/certificates/{document_id}/library-draft", response_model=R, operation_id="draftLibraryFromCertificate")
    def certificate_draft(document_id: str, user: Principal = Depends(current_user)):
        """用证书附件的抽取字段生成“待核验”资料，须资料管理员在资料库核对确认。"""
        return admin.certificate_draft(user, document_id)

    @router.post("/retrieval-test", response_model=R, operation_id="testKbRetrieval")
    def retrieval_test(body: KbRetrievalTest, user: Principal = Depends(current_user)):
        """检索试查：可临时覆盖阈值、关键词权重、重排模型，结果与写作检索走同一条过滤与复核链路。"""
        return admin.retrieval_test(user, body.model_dump(exclude_none=True))

    @router.get("/audit", response_model=R, operation_id="listKbAudit")
    def audit(limit: int = Query(default=100, ge=1, le=500), user: Principal = Depends(current_user)):
        return admin.audit(user, limit)

    application.include_router(router)


__all__: list[Any] = ["include_kb_admin_routes"]
