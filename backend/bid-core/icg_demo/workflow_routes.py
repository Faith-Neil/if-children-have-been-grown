# 为什么有这个文件：将示例主流程的页面请求接到真实业务服务。
# 它解决什么问题：统一版本和重复请求保护，提供可核对的 OpenAPI 与带登录授权的原件、两册下载。

from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, Response

from .adapters import build_docx
from .domain import Export, Principal
from .schemas import EmptyRequest
from .sla_schemas import (SlaMutationResult, SlaReviewRequest, SlaSelection, SlaTemplateCreate,
                          SlaTemplateList, SlaTemplatePatch, SlaTemplateResult, SlaValuePatch)
from .workflow import DOCX_MEDIA_TYPE, WorkflowService
from .idempotency import IDEMPOTENCY_HEADER_DESCRIPTION
from .workflow_schemas import (CheckList, ConflictPatch, FactPatch, FileDelete, FilePreview, FileUpload,
                               GenerateRequest, JobsList, LibraryCreate, LibraryList,
                               LibraryPatch, LibraryResult, MutationResult, ParseRequest,
                               PlanRequest, ProjectCheckRequest, ProjectExportRequest,
                               ProjectPatch, RequirementPatch, Workspace, WritingInputPreview,
                               TeamUpdate, TeamResult, ChapterAssignment, ChapterPlanPatch,
                               v1_error_responses)


def include_workflow_routes(application, service, current_user, parser):
    workflow = WorkflowService(service, parser)
    application.state.workflow = workflow
    router = APIRouter(prefix="/api/v1", responses=v1_error_responses(
        401, 403, 404, 409, 413, 422, 423, 428, 500, 502))

    @router.get("/projects/{project_id}/workspace", response_model=Workspace)
    def workspace(project_id: str, response: Response, user: Principal = Depends(current_user)):
        result = workflow.workspace(user, project_id)
        response.headers["ETag"] = f'"{result["revision"]}"'
        return result

    @router.get("/projects/{project_id}/team", response_model=TeamResult)
    def team(project_id: str, response: Response, user: Principal = Depends(current_user)):
        result = workflow.team.get(user, project_id)
        response.headers["ETag"] = f'"{result["revision"]}"'
        return result

    @router.put("/projects/{project_id}/team", response_model=MutationResult, response_model_exclude_none=True)
    def update_team(project_id: str, body: TeamUpdate, user: Principal = Depends(current_user),
                    if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.team.update(user, project_id, body.model_dump(), if_match, idempotency_key)

    @router.patch("/projects/{project_id}/chapters/{chapter_id}/assignment", response_model=MutationResult,
                  response_model_exclude_none=True)
    def assignment(project_id: str, chapter_id: str, body: ChapterAssignment, user: Principal = Depends(current_user),
                   if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.team.assignment(user, project_id, chapter_id, body.model_dump(), if_match, idempotency_key)

    @router.patch("/projects/{project_id}/chapters/{chapter_id}/plan", response_model=MutationResult,
                  response_model_exclude_none=True)
    def save_chapter_plan(project_id: str, chapter_id: str, body: ChapterPlanPatch, user: Principal = Depends(current_user),
                          if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.chapter_plan_save(user, project_id, chapter_id, body.model_dump(), if_match, idempotency_key)

    @router.post("/projects/{project_id}/chapters/{chapter_id}/plan/confirm", response_model=MutationResult,
                 response_model_exclude_none=True)
    def confirm_chapter_plan(project_id: str, chapter_id: str, body: EmptyRequest, user: Principal = Depends(current_user),
                            if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.chapter_plan_confirm(user, project_id, chapter_id, body.model_dump(), if_match, idempotency_key)

    @router.get("/projects/{project_id}/chapters/{chapter_id}/writing-input", response_model=WritingInputPreview)
    def writing_input(project_id: str, chapter_id: str, user: Principal = Depends(current_user)):
        return workflow.writing_input(user, project_id, chapter_id)

    @router.patch("/projects/{project_id}", response_model=MutationResult, response_model_exclude_none=True)
    def patch_project(project_id: str, body: ProjectPatch, user: Principal = Depends(current_user),
                      if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.patch_project(user, project_id, body.model_dump(exclude_unset=True), if_match, idempotency_key)

    @router.post("/projects/{project_id}/files", response_model=MutationResult, response_model_exclude_none=True)
    def upload(project_id: str, body: FileUpload, user: Principal = Depends(current_user),
               if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.upload(user, project_id, body.model_dump(), if_match, idempotency_key)

    @router.delete("/projects/{project_id}/files/{file_id}", response_model=MutationResult,
                   response_model_exclude_none=True)
    def delete_file(project_id: str, file_id: str, body: FileDelete, user: Principal = Depends(current_user),
                    if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.delete_file(user, project_id, file_id, body.model_dump(), if_match, idempotency_key)

    @router.get("/projects/{project_id}/files/{file_id}/preview", response_model=FilePreview)
    def preview(project_id: str, file_id: str, user: Principal = Depends(current_user)):
        return workflow.file(user, project_id, file_id, preview=True)

    @router.get("/projects/{project_id}/files/{file_id}", response_class=Response,
                responses={200: {"description": "真实上传原件，登录和公司隔离持续生效",
                                 "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}})
    def original(project_id: str, file_id: str, user: Principal = Depends(current_user)):
        record = workflow.file(user, project_id, file_id)
        return Response(content=record["content"], media_type=record["media_type"],
                        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(record['filename'])}"})

    @router.post("/projects/{project_id}/parse", response_model=MutationResult, response_model_exclude_none=True)
    def parse(project_id: str, body: ParseRequest, user: Principal = Depends(current_user),
              if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.parse(user, project_id, body.model_dump(), if_match, idempotency_key)

    @router.patch("/projects/{project_id}/requirements/{requirement_id}", response_model=MutationResult,
                  response_model_exclude_none=True)
    def requirement(project_id: str, requirement_id: str, body: RequirementPatch,
                    user: Principal = Depends(current_user), if_match: str | None = Header(default=None),
                    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.patch_requirement(user, project_id, requirement_id, body.model_dump(exclude_unset=True), if_match, idempotency_key)

    @router.patch("/projects/{project_id}/facts/{fact_id}", response_model=MutationResult,
                  response_model_exclude_none=True)
    def fact(project_id: str, fact_id: str, body: FactPatch, user: Principal = Depends(current_user),
             if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.patch_fact(user, project_id, fact_id, body.model_dump(exclude_unset=True), if_match, idempotency_key)

    @router.patch("/projects/{project_id}/conflicts/{conflict_id}", response_model=MutationResult,
                  response_model_exclude_none=True)
    def conflict(project_id: str, conflict_id: str, body: ConflictPatch, user: Principal = Depends(current_user),
                 if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.resolve_conflict(user, project_id, conflict_id, body.model_dump(), if_match, idempotency_key)

    @router.post("/projects/{project_id}/parse/confirm", response_model=MutationResult,
                 response_model_exclude_none=True)
    def confirm_parse(project_id: str, body: EmptyRequest, user: Principal = Depends(current_user),
                      if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.confirm_parse(user, project_id, body.model_dump(), if_match, idempotency_key)

    @router.post("/projects/{project_id}/plan", response_model=MutationResult,
                 response_model_exclude_none=True)
    def plan(project_id: str, body: PlanRequest, user: Principal = Depends(current_user),
             if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.plan(user, project_id, body.model_dump(exclude_unset=True), if_match, idempotency_key)

    @router.post("/projects/{project_id}/generate", response_model=MutationResult)
    def generate(project_id: str, body: GenerateRequest, user: Principal = Depends(current_user),
                 if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.generate(user, project_id, body.model_dump(), if_match, idempotency_key)

    @router.get("/projects/{project_id}/checks", response_model=CheckList)
    def checks(project_id: str, user: Principal = Depends(current_user)):
        return workflow.checks(user, project_id)

    @router.post("/projects/{project_id}/checks", response_model=MutationResult,
                 response_model_exclude_none=True)
    def check(project_id: str, body: ProjectCheckRequest, user: Principal = Depends(current_user),
              if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.run_check(user, project_id, body.model_dump(), if_match, idempotency_key)

    @router.post("/projects/{project_id}/exports", response_model=MutationResult,
                 response_model_exclude_none=True)
    def export(project_id: str, body: ProjectExportRequest, user: Principal = Depends(current_user),
               if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.export(user, project_id, body.model_dump(), if_match, idempotency_key)

    @router.get("/projects/{project_id}/exports/{export_id}/{volume}", response_class=Response,
                responses={200: {"description": "独立的技术或商务 Word 分册，排除未提交草稿",
                                 "content": {DOCX_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}}}})
    def download(project_id: str, export_id: str, volume: str, user: Principal = Depends(current_user)):
        document = workflow.download(user, project_id, export_id, volume)
        record = Export(export_id, "", 1, "", "", document["filename"], document["title"], document["content"])
        return Response(content=build_docx(record, project_name=document.get("project_name")), media_type=DOCX_MEDIA_TYPE,
                        headers={"Content-Disposition": f'attachment; filename="{document["filename"]}"'})

    @router.get("/jobs", response_model=JobsList)
    def jobs(user: Principal = Depends(current_user)):
        return workflow.jobs(user)

    @router.get("/sla/templates", response_model=SlaTemplateList)
    def sla_templates(response: Response, user: Principal = Depends(current_user)):
        result = workflow.sla.templates(user)
        response.headers["ETag"] = f'"{result["revision"]}"'
        return result

    @router.post("/sla/templates", response_model=SlaTemplateResult)
    def create_sla_template(body: SlaTemplateCreate, user: Principal = Depends(current_user),
                            if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.sla.write_template(user, body.model_dump(), if_match, idempotency_key)

    @router.patch("/sla/templates/{template_id}", response_model=SlaTemplateResult)
    def patch_sla_template(template_id: str, body: SlaTemplatePatch, user: Principal = Depends(current_user),
                           if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.sla.write_template(user, body.model_dump(exclude_unset=True), if_match, idempotency_key, template_id)

    @router.post("/projects/{project_id}/sla/template", response_model=SlaMutationResult, response_model_exclude_none=True)
    def select_sla_template(project_id: str, body: SlaSelection, user: Principal = Depends(current_user),
                            if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.sla.select(user, project_id, body.model_dump(), if_match, idempotency_key)

    @router.patch("/projects/{project_id}/sla/values/{var_key}", response_model=SlaMutationResult, response_model_exclude_none=True)
    def patch_sla_value(project_id: str, var_key: str, body: SlaValuePatch, user: Principal = Depends(current_user),
                        if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.sla.patch_value(user, project_id, var_key, body.model_dump(exclude_unset=True), if_match, idempotency_key)

    @router.post("/projects/{project_id}/sla/apply-tender", response_model=SlaMutationResult, response_model_exclude_none=True)
    def apply_sla_tender(project_id: str, body: EmptyRequest, user: Principal = Depends(current_user),
                         if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.sla.apply_tender(user, project_id, body.model_dump(), if_match, idempotency_key)

    @router.post("/projects/{project_id}/sla/values/{var_key}/review", response_model=SlaMutationResult, response_model_exclude_none=True)
    def review_sla_value(project_id: str, var_key: str, body: SlaReviewRequest, user: Principal = Depends(current_user),
                         if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.sla.review(user, project_id, var_key, body.model_dump(), if_match, idempotency_key)

    @router.post("/projects/{project_id}/sla/commitment", response_model=SlaMutationResult, response_model_exclude_none=True)
    def export_sla_commitment(project_id: str, body: EmptyRequest, user: Principal = Depends(current_user),
                              if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.sla.commitment(user, project_id, body.model_dump(), if_match, idempotency_key)

    @router.get("/projects/{project_id}/sla/commitment/{export_id}", response_class=Response,
                responses={200: {"description": "服务承诺函实际Word表格，仅内部稿；过期数据拒绝下载",
                                 "content": {DOCX_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}}}})
    def download_sla_commitment(project_id: str, export_id: str, user: Principal = Depends(current_user)):
        document = workflow.sla.download(user, project_id, export_id)
        record = Export(export_id, "", 1, "", "", document["filename"], document["title"], document["content"])
        return Response(content=build_docx(record, document["table"]), media_type=DOCX_MEDIA_TYPE,
                        headers={"Content-Disposition": f'attachment; filename="{document["filename"]}"'})

    @router.get("/library", response_model=LibraryList)
    def library(response: Response, user: Principal = Depends(current_user)):
        result = workflow.library(user)
        response.headers["ETag"] = f'"{result["revision"]}"'
        return result

    @router.post("/library", response_model=LibraryResult)
    def create_library(body: LibraryCreate, user: Principal = Depends(current_user),
                       if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.write_library(user, body.model_dump(), if_match, idempotency_key)

    @router.patch("/library/{item_id}", response_model=LibraryResult)
    def patch_library(item_id: str, body: LibraryPatch, user: Principal = Depends(current_user),
                      if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.write_library(user, body.model_dump(exclude_unset=True), if_match, idempotency_key, item_id)

    application.include_router(router)
