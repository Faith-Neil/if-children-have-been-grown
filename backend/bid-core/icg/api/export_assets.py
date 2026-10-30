# 为什么有这个文件：导出素材接口——公司 Word 模板与资料附件扫描件（PRD v1.8 §5.6.2、§5.9.1 规则 1、7；
# APP-M2-T086、T059、T198）。
# 它解决什么问题：公司管理员上传、查看、下载、删除本公司 Word 模板，并看到模板里读到了哪些样式；
# 资料库每条资料上传扫描件（二进制直传）、设插入页码范围、敏感水印、是否带公司标识与功能点标签，下载原件留审计。

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import Field

from icg.api.raw_upload import RAW_BODY_DOC, read_limited_body
from icg.domain.attachments import AttachmentService
from icg.domain.domain import DemoService, Principal
from icg.domain.schemas import RequestBody, ResponseBody
from icg.domain.word_template import WordTemplateService
from icg.domain.workflow_schemas import v1_error_responses

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MEDIA = {"pdf": "application/pdf", "png": "image/png", "jpeg": "image/jpeg"}


class WordTemplate(ResponseBody):
    id: str
    filename: str
    sha256: str
    size_bytes: int
    uploaded_by: str
    uploaded_at: str
    applied: list[str] = Field(description="从模板读到并会用于导出的样式，如“一级标题：黑体，16 磅，居中”")
    defaults: list[str] = Field(description="模板里没有、导出时沿用平台默认的样式项")


class WordTemplateInfo(ResponseBody):
    template: WordTemplate | None = None


class Attachment(ResponseBody):
    id: str
    library_id: str
    filename: str
    kind: str = Field(description="pdf / png / jpeg（按文件头判断）")
    size_bytes: int
    sha256: str
    page_count: int
    page_from: int
    page_to: int
    is_sensitive: bool = Field(description="敏感附件导出时加水印")
    shows_identity: bool = Field(description="附件上有公司名称或标志；暗标分册不插入")
    feature_tags: list[str] = Field(description="功能点标签（R38 证明材料与评分要点对应）")
    uploaded_by: str
    uploaded_at: str
    revision: int


class AttachmentList(ResponseBody):
    items: list[Attachment]


class AttachmentResult(ResponseBody):
    attachment: Attachment
    duplicate: bool | None = Field(default=None, description="同一资料已有相同内容的附件时为 true，返回已有附件")


class AttachmentPatch(RequestBody):
    page_from: int | None = Field(default=None, ge=1)
    page_to: int | None = Field(default=None, ge=1)
    is_sensitive: bool | None = None
    shows_identity: bool | None = None
    feature_tags: list[str] | None = Field(default=None, max_length=30)


class DeleteResult(ResponseBody):
    deleted: bool


def include_export_asset_routes(application, service: DemoService, current_user) -> None:
    templates = WordTemplateService(service)
    attachments = AttachmentService(service)
    application.state.word_templates = templates
    application.state.attachments = attachments
    router = APIRouter(prefix="/api/v1", responses=v1_error_responses(401, 403, 404, 409, 422))

    @router.get("/companies/{company_id}/word-template", response_model=WordTemplateInfo,
                operation_id="getWordTemplate", summary="本公司当前 Word 模板与读到的样式")
    def get_template(company_id: str, user: Principal = Depends(current_user)):
        return templates.get(user, company_id)

    @router.put("/companies/{company_id}/word-template", response_model=WordTemplateInfo,
                operation_id="uploadWordTemplate", summary="上传或替换公司 Word 模板（.docx，二进制）",
                openapi_extra=RAW_BODY_DOC, responses=v1_error_responses(413, 503),
                description="只有公司管理员可上传；只读取模板样式与页边距，不带入模板的属性、批注或正文；上限 20MB。")
    async def upload_template(company_id: str, request: Request, filename: str = Query(min_length=1, max_length=180),
                              user: Principal = Depends(current_user)):
        data = await read_limited_body(request)
        return await run_in_threadpool(templates.upload, user, company_id, filename, data)

    @router.delete("/companies/{company_id}/word-template", response_model=WordTemplateInfo,
                   operation_id="deleteWordTemplate", summary="删除公司 Word 模板，之后导出用平台默认模板")
    def delete_template(company_id: str, user: Principal = Depends(current_user)):
        return templates.delete(user, company_id)

    @router.get("/companies/{company_id}/word-template/file", response_class=Response,
                operation_id="downloadWordTemplate",
                responses={200: {"description": "公司上传的模板原件", "content": {DOCX: {"schema": {"type": "string", "format": "binary"}}}}})
    def download_template(company_id: str, user: Principal = Depends(current_user)):
        filename, data = templates.original(user, company_id)
        return Response(content=data, media_type=DOCX,
                        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"})

    @router.get("/library/{item_id}/attachments", response_model=AttachmentList, operation_id="listLibraryAttachments")
    def list_attachments(item_id: str, user: Principal = Depends(current_user)):
        return attachments.list(user, item_id)

    @router.post("/library/{item_id}/attachments/raw", response_model=AttachmentResult,
                 operation_id="uploadLibraryAttachment", summary="上传资料的附件扫描件（PDF/PNG/JPG，二进制）",
                 openapi_extra=RAW_BODY_DOC, responses=v1_error_responses(413, 503),
                 description="文件加密保存（需 ICG_SECRET_KEY）；默认插入全部页、按敏感附件加水印、视为带公司标识。")
    async def upload_attachment(item_id: str, request: Request, filename: str = Query(min_length=1, max_length=180),
                                user: Principal = Depends(current_user)):
        data = await read_limited_body(request)
        return await run_in_threadpool(attachments.upload, user, item_id, filename, data)

    @router.patch("/library/attachments/{attachment_id}", response_model=AttachmentResult,
                  operation_id="patchLibraryAttachment", summary="设置插入页码范围、敏感水印、公司标识与功能点标签")
    def patch_attachment(attachment_id: str, body: AttachmentPatch, user: Principal = Depends(current_user),
                         if_match: str | None = Header(default=None, description="附件 revision；填写时不一致返回 409")):
        expected = int(if_match.strip('"')) if if_match and if_match.strip('"').isdigit() else None
        return attachments.update(user, attachment_id, body.model_dump(exclude_unset=True, exclude_none=True), expected)

    @router.delete("/library/attachments/{attachment_id}", response_model=DeleteResult,
                   operation_id="deleteLibraryAttachment")
    def delete_attachment(attachment_id: str, user: Principal = Depends(current_user)):
        return attachments.delete(user, attachment_id)

    @router.get("/library/attachments/{attachment_id}/file", response_class=Response,
                operation_id="downloadLibraryAttachment", responses={
                    200: {"description": "附件原件（解密后），下载记审计", "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}},
                    503: {"description": "服务器未配置主密钥"}})
    def download_attachment(attachment_id: str, user: Principal = Depends(current_user)):
        record, data = attachments.original(user, attachment_id)
        return Response(content=data, media_type=MEDIA.get(record["kind"], "application/octet-stream"),
                        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(record['filename'])}"})

    application.include_router(router)
