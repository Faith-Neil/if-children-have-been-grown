# 为什么有这个文件：将示例主流程的页面请求接到真实业务服务。
# 它解决什么问题：统一版本和重复请求保护，提供可核对的 OpenAPI 与带登录授权的原件、两册下载。

from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, Query, Response

from icg.infra.adapters import build_docx
from icg.domain.domain import Export, Principal
from icg.domain.schemas import EmptyRequest
from icg.domain.sla_schemas import (SlaMutationResult, SlaReviewRequest, SlaSelection, SlaTemplateCreate,
                          SlaTemplateList, SlaTemplatePatch, SlaTemplateResult, SlaValuePatch)
from icg.domain.recoverable_jobs import include_recoverable_routes
from icg.domain.workflow import DOCX_MEDIA_TYPE, WorkflowService
from icg.domain.idempotency import IDEMPOTENCY_HEADER_DESCRIPTION
from icg.domain.workflow_schemas import (CheckList, ConflictPatch, FactPatch, FileDelete, FilePreview, FileUpload,
                               GenerateRequest, JobsList, LibraryCreate, LibraryList,
                               LibraryPatch, LibraryResult, MutationResult, ParseRequest,
                               PlanRequest, ProjectCheckRequest, ProjectExportRequest,
                               ProjectPatch, RequirementPatch, Workspace, WritingInputPreview,
                               TeamUpdate, TeamResult, ChapterAssignment, ChapterPlanPatch,
                               ChapterEditDetail, v1_error_responses, TenderSearchRequest,
                               TenderIndexingSwitchRequest, InjectTenderClausesRequest,
                               AcceptAiSuggestionRequest, ComplianceCrossCheckRequest,
                               ComplianceCrossCheckResponse, SnippetMatchRequest,
                               SnippetMatchResponse, BatchGenerateChaptersRequest)


def include_workflow_routes(application, service, current_user, parser):
    workflow = WorkflowService(service, parser)
    application.state.workflow = workflow
    router = APIRouter(prefix="/api/v1", responses=v1_error_responses(
        401, 403, 404, 409, 413, 422, 423, 428, 500, 502))

    @router.get("/projects/{project_id}/workspace", response_model=Workspace, operation_id="getWorkspace")
    def workspace(project_id: str, response: Response, user: Principal = Depends(current_user)):
        result = workflow.workspace(user, project_id)
        response.headers["ETag"] = f'"{result["revision"]}"'
        return result

    @router.get("/projects/{project_id}/team", response_model=TeamResult, operation_id="getTeam")
    def team(project_id: str, response: Response, user: Principal = Depends(current_user)):
        result = workflow.team.get(user, project_id)
        response.headers["ETag"] = f'"{result["revision"]}"'
        return result

    @router.put("/projects/{project_id}/team", response_model=MutationResult, response_model_exclude_none=True,
                operation_id="updateTeam")
    def update_team(project_id: str, body: TeamUpdate, user: Principal = Depends(current_user),
                    if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.team.update(user, project_id, body.model_dump(), if_match, idempotency_key)

    @router.patch("/projects/{project_id}/chapters/{chapter_id}/assignment", response_model=MutationResult,
                  response_model_exclude_none=True, operation_id="updateChapterAssignment")
    def assignment(project_id: str, chapter_id: str, body: ChapterAssignment, user: Principal = Depends(current_user),
                   if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.team.assignment(user, project_id, chapter_id, body.model_dump(), if_match, idempotency_key)

    @router.patch("/projects/{project_id}/chapters/{chapter_id}/plan", response_model=MutationResult,
                  response_model_exclude_none=True, operation_id="saveChapterPlan")
    def save_chapter_plan(project_id: str, chapter_id: str, body: ChapterPlanPatch, user: Principal = Depends(current_user),
                          if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.chapter_plan_save(user, project_id, chapter_id, body.model_dump(), if_match, idempotency_key)

    @router.post("/projects/{project_id}/chapters/{chapter_id}/plan/confirm", response_model=MutationResult,
                 response_model_exclude_none=True, operation_id="confirmChapterPlan")
    def confirm_chapter_plan(project_id: str, chapter_id: str, body: EmptyRequest, user: Principal = Depends(current_user),
                            if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.chapter_plan_confirm(user, project_id, chapter_id, body.model_dump(), if_match, idempotency_key)

    @router.get("/projects/{project_id}/chapters/{chapter_id}/writing-input", response_model=WritingInputPreview,
                operation_id="getWritingInput")
    def writing_input(project_id: str, chapter_id: str, user: Principal = Depends(current_user)):
        return workflow.writing_input(user, project_id, chapter_id)

    @router.get("/projects/{project_id}/chapters/{chapter_id}", response_model=ChapterEditDetail,
                operation_id="getChapterEditDetail")
    def chapter_edit_detail(project_id: str, chapter_id: str, user: Principal = Depends(current_user)):
        return workflow.chapter_edit_detail(user, project_id, chapter_id)

    @router.patch("/projects/{project_id}", response_model=MutationResult, response_model_exclude_none=True,
                  operation_id="patchProject")
    def patch_project(project_id: str, body: ProjectPatch, user: Principal = Depends(current_user),
                      if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.patch_project(user, project_id, body.model_dump(exclude_unset=True), if_match, idempotency_key)

    @router.post("/projects/{project_id}/files", response_model=MutationResult, response_model_exclude_none=True,
                 operation_id="uploadFile")
    def upload(project_id: str, body: FileUpload, user: Principal = Depends(current_user),
               if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.upload(user, project_id, body.model_dump(), if_match, idempotency_key)

    @router.delete("/projects/{project_id}/files/{file_id}", response_model=MutationResult,
                   response_model_exclude_none=True, operation_id="deleteFile")
    def delete_file(project_id: str, file_id: str, body: FileDelete, user: Principal = Depends(current_user),
                    if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.delete_file(user, project_id, file_id, body.model_dump(), if_match, idempotency_key)

    @router.get("/projects/{project_id}/files/{file_id}/preview", response_model=FilePreview,
                operation_id="previewFile")
    def preview(project_id: str, file_id: str, user: Principal = Depends(current_user)):
        return workflow.file(user, project_id, file_id, preview=True)

    @router.get("/projects/{project_id}/files/{file_id}", response_class=Response,
                operation_id="getOriginalFile",
                responses={200: {"description": "真实上传原件，登录和公司隔离持续生效",
                                 "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}})
    def original(project_id: str, file_id: str, user: Principal = Depends(current_user)):
        record = workflow.file(user, project_id, file_id)
        return Response(content=record["content"], media_type=record["media_type"],
                        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(record['filename'])}"})

    @router.post("/projects/{project_id}/parse", response_model=MutationResult, response_model_exclude_none=True,
                 operation_id="parseFiles")
    def parse(project_id: str, body: ParseRequest, user: Principal = Depends(current_user),
              if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.parse(user, project_id, body.model_dump(), if_match, idempotency_key)

    @router.patch("/projects/{project_id}/requirements/{requirement_id}", response_model=MutationResult,
                  response_model_exclude_none=True, operation_id="patchRequirement")
    def requirement(project_id: str, requirement_id: str, body: RequirementPatch,
                    user: Principal = Depends(current_user), if_match: str | None = Header(default=None),
                    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.patch_requirement(user, project_id, requirement_id, body.model_dump(exclude_unset=True), if_match, idempotency_key)

    @router.patch("/projects/{project_id}/facts/{fact_id}", response_model=MutationResult,
                  response_model_exclude_none=True, operation_id="patchFact")
    def fact(project_id: str, fact_id: str, body: FactPatch, user: Principal = Depends(current_user),
             if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.patch_fact(user, project_id, fact_id, body.model_dump(exclude_unset=True), if_match, idempotency_key)

    @router.patch("/projects/{project_id}/conflicts/{conflict_id}", response_model=MutationResult,
                  response_model_exclude_none=True, operation_id="patchConflict")
    def conflict(project_id: str, conflict_id: str, body: ConflictPatch, user: Principal = Depends(current_user),
                 if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.resolve_conflict(user, project_id, conflict_id, body.model_dump(), if_match, idempotency_key)

    @router.post("/projects/{project_id}/parse/confirm", response_model=MutationResult,
                 response_model_exclude_none=True, operation_id="confirmParse")
    def confirm_parse(project_id: str, body: EmptyRequest, user: Principal = Depends(current_user),
                      if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.confirm_parse(user, project_id, body.model_dump(), if_match, idempotency_key)

    @router.post("/projects/{project_id}/plan", response_model=MutationResult,
                 response_model_exclude_none=True, operation_id="createPlan")
    def plan(project_id: str, body: PlanRequest, user: Principal = Depends(current_user),
             if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.plan(user, project_id, body.model_dump(exclude_unset=True), if_match, idempotency_key)

    @router.post("/projects/{project_id}/generate", response_model=MutationResult, operation_id="generateProject")
    def generate(project_id: str, body: GenerateRequest, user: Principal = Depends(current_user),
                 if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.generate(user, project_id, body.model_dump(), if_match, idempotency_key)

    @router.get("/projects/{project_id}/checks", response_model=CheckList, operation_id="listChecks")
    def checks(project_id: str, user: Principal = Depends(current_user)):
        return workflow.checks(user, project_id)

    @router.post("/projects/{project_id}/checks", response_model=MutationResult,
                 response_model_exclude_none=True, operation_id="runCheck")
    def check(project_id: str, body: ProjectCheckRequest, user: Principal = Depends(current_user),
              if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.run_check(user, project_id, body.model_dump(), if_match, idempotency_key)

    @router.post("/projects/{project_id}/exports", response_model=MutationResult,
                 response_model_exclude_none=True, operation_id="exportVolume")
    def export(project_id: str, body: ProjectExportRequest, user: Principal = Depends(current_user),
               if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.export(user, project_id, body.model_dump(), if_match, idempotency_key)

    @router.get("/projects/{project_id}/exports/{export_id}/{volume}", response_class=Response,
                operation_id="downloadVolume",
                responses={200: {"description": "独立的技术或商务 Word 分册，排除未提交草稿",
                                 "content": {DOCX_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}}}})
    def download(project_id: str, export_id: str, volume: str, user: Principal = Depends(current_user)):
        document = workflow.download(user, project_id, export_id, volume)
        record = Export(export_id, "", 1, "", "", document["filename"], document["title"], document["content"])
        return Response(content=build_docx(record, project_name=document.get("project_name")), media_type=DOCX_MEDIA_TYPE,
                        headers={"Content-Disposition": f'attachment; filename="{document["filename"]}"'})

    @router.get("/jobs", response_model=JobsList, operation_id="listJobs")
    def jobs(user: Principal = Depends(current_user), masked: bool = Query(default=False, description="是否脱敏返回任务运维审计视图")):
        return workflow.jobs(user, masked=masked)

    @router.get("/jobs/masked", response_model=JobsList, operation_id="listJobsMasked", include_in_schema=False)
    def jobs_masked(user: Principal = Depends(current_user)):
        return workflow.jobs(user, masked=True)

    @router.get("/sla/templates", response_model=SlaTemplateList, operation_id="listSlaTemplates")
    def sla_templates(response: Response, user: Principal = Depends(current_user)):
        result = workflow.sla.templates(user)
        response.headers["ETag"] = f'"{result["revision"]}"'
        return result

    @router.post("/sla/templates", response_model=SlaTemplateResult, operation_id="createSlaTemplate")
    def create_sla_template(body: SlaTemplateCreate, user: Principal = Depends(current_user),
                            if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.sla.write_template(user, body.model_dump(), if_match, idempotency_key)

    @router.patch("/sla/templates/{template_id}", response_model=SlaTemplateResult, operation_id="patchSlaTemplate")
    def patch_sla_template(template_id: str, body: SlaTemplatePatch, user: Principal = Depends(current_user),
                           if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.sla.write_template(user, body.model_dump(exclude_unset=True), if_match, idempotency_key, template_id)

    @router.post("/projects/{project_id}/sla/template", response_model=SlaMutationResult, response_model_exclude_none=True,
                 operation_id="selectSlaTemplate")
    def select_sla_template(project_id: str, body: SlaSelection, user: Principal = Depends(current_user),
                            if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.sla.select(user, project_id, body.model_dump(), if_match, idempotency_key)

    @router.patch("/projects/{project_id}/sla/values/{var_key}", response_model=SlaMutationResult, response_model_exclude_none=True,
                  operation_id="patchSlaValue")
    def patch_sla_value(project_id: str, var_key: str, body: SlaValuePatch, user: Principal = Depends(current_user),
                        if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.sla.patch_value(user, project_id, var_key, body.model_dump(exclude_unset=True), if_match, idempotency_key)

    @router.post("/projects/{project_id}/sla/apply-tender", response_model=SlaMutationResult, response_model_exclude_none=True,
                 operation_id="applySlaTender")
    def apply_sla_tender(project_id: str, body: EmptyRequest, user: Principal = Depends(current_user),
                         if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.sla.apply_tender(user, project_id, body.model_dump(), if_match, idempotency_key)

    @router.post("/projects/{project_id}/sla/values/{var_key}/review", response_model=SlaMutationResult, response_model_exclude_none=True,
                 operation_id="reviewSlaValue")
    def review_sla_value(project_id: str, var_key: str, body: SlaReviewRequest, user: Principal = Depends(current_user),
                         if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.sla.review(user, project_id, var_key, body.model_dump(), if_match, idempotency_key)

    @router.post("/projects/{project_id}/sla/commitment", response_model=SlaMutationResult, response_model_exclude_none=True,
                 operation_id="exportSlaCommitment")
    def export_sla_commitment(project_id: str, body: EmptyRequest, user: Principal = Depends(current_user),
                              if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.sla.commitment(user, project_id, body.model_dump(), if_match, idempotency_key)

    @router.get("/projects/{project_id}/sla/commitment/{export_id}", response_class=Response,
                operation_id="downloadSlaCommitment",
                responses={200: {"description": "服务承诺函实际Word表格，仅内部稿；过期数据拒绝下载",
                                 "content": {DOCX_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}}}})
    def download_sla_commitment(project_id: str, export_id: str, user: Principal = Depends(current_user)):
        document = workflow.sla.download(user, project_id, export_id)
        record = Export(export_id, "", 1, "", "", document["filename"], document["title"], document["content"])
        return Response(content=build_docx(record, document["table"], project_name=document.get("project_name")),
                        media_type=DOCX_MEDIA_TYPE,
                        headers={"Content-Disposition": f'attachment; filename="{document["filename"]}"'})

    @router.get("/library", response_model=LibraryList, operation_id="listLibraryItems")
    def library(response: Response, user: Principal = Depends(current_user)):
        result = workflow.library(user)
        response.headers["ETag"] = f'"{result["revision"]}"'
        return result

    @router.post("/library", response_model=LibraryResult, operation_id="createLibraryItem")
    def create_library(body: LibraryCreate, user: Principal = Depends(current_user),
                       if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.write_library(user, body.model_dump(), if_match, idempotency_key)

    @router.patch("/library/{item_id}", response_model=LibraryResult, operation_id="patchLibraryItem")
    def patch_library(item_id: str, body: LibraryPatch, user: Principal = Depends(current_user),
                      if_match: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        return workflow.write_library(user, body.model_dump(exclude_unset=True), if_match, idempotency_key, item_id)

    @router.post("/projects/{project_id}/tender/search", include_in_schema=False)
    def search_tender_slices_endpoint(project_id: str, body: TenderSearchRequest, user: Principal = Depends(current_user)):
        return workflow.search_tender_slices(
            principal=user,
            project_id=project_id,
            query=body.query,
            enabled=body.enabled,
            top_k=body.top_k,
            clause_type=body.clause_type,
        )

    @router.patch("/projects/{project_id}/tender/indexing-switch", include_in_schema=False)
    def update_tender_indexing_switch_endpoint(project_id: str, body: TenderIndexingSwitchRequest, user: Principal = Depends(current_user)):
        res = workflow.set_tender_indexing_switch(user, project_id, body.enabled)
        return {"project_id": project_id, "tender_indexing_enabled": res}

    @router.post("/projects/{project_id}/chapters/{chapter_id}/inject-tender-clauses", include_in_schema=False)
    def inject_tender_clauses_endpoint(project_id: str, chapter_id: str, body: InjectTenderClausesRequest, user: Principal = Depends(current_user)):
        return workflow.inject_tender_clauses(
            principal=user,
            project_id=project_id,
            chapter_id=chapter_id,
            slice_ids=body.slice_ids,
            slices=body.slices,
        )

    @router.get("/projects/{project_id}/chapters/{chapter_id}/injected-tender-clauses", include_in_schema=False)
    def get_injected_tender_clauses_endpoint(project_id: str, chapter_id: str, user: Principal = Depends(current_user)):
        clauses = workflow.get_injected_tender_clauses(user, project_id, chapter_id)
        return {"chapter_id": chapter_id, "project_id": project_id, "injected_clauses": clauses, "count": len(clauses)}

    @router.delete("/projects/{project_id}/chapters/{chapter_id}/injected-tender-clauses", include_in_schema=False)
    def clear_injected_tender_clauses_endpoint(project_id: str, chapter_id: str, user: Principal = Depends(current_user)):
        cleared = workflow.clear_injected_tender_clauses(user, project_id, chapter_id)
        return {"chapter_id": chapter_id, "project_id": project_id, "cleared": cleared}

    @router.post("/projects/{project_id}/chapters/{chapter_id}/accept-ai-suggestion", include_in_schema=False)
    def accept_ai_suggestion_endpoint(
        project_id: str,
        chapter_id: str,
        body: AcceptAiSuggestionRequest,
        user: Principal = Depends(current_user),
    ):
        return workflow.accept_ai_suggestion(
            principal=user,
            project_id=project_id,
            chapter_id=chapter_id,
            lease_token=body.lease_token,
            base_revision=body.base_revision,
            suggested_text=body.suggested_text,
            paragraph_id=body.paragraph_id,
            original_text=body.original_text,
            citations=body.citations,
            input_fingerprint=body.input_fingerprint,
        )

    @router.post(
        "/projects/{project_id}/chapters/{chapter_id}/compliance-cross-check",
        response_model=ComplianceCrossCheckResponse,
        include_in_schema=False,
    )
    def compliance_cross_check_endpoint(
        project_id: str,
        chapter_id: str,
        body: ComplianceCrossCheckRequest | None = None,
        user: Principal = Depends(current_user),
    ):
        model_cfg = body.model_config_id if body else None
        strict = body.strict_mode if body else True
        return workflow.compliance_cross_check(
            principal=user,
            project_id=project_id,
            chapter_id=chapter_id,
            model_config_id=model_cfg,
            strict_mode=strict,
        )

    @router.post(
        "/projects/{project_id}/snippets/match",
        response_model=SnippetMatchResponse,
        include_in_schema=False,
    )
    def match_snippets_endpoint(
        project_id: str,
        body: SnippetMatchRequest,
        user: Principal = Depends(current_user),
    ):
        return workflow.match_snippets(
            principal=user,
            project_id=project_id,
            chapter_id=body.chapter_id,
            chapter_title=body.chapter_title,
            scoring_points=body.scoring_points,
            query=body.query,
            limit=body.limit,
            min_score=body.min_score,
            model_config_id=body.model_config_id,
        )

    @router.post(
        "/projects/{project_id}/chapters/batch-generate",
        include_in_schema=False,
    )
    def batch_generate_chapters_endpoint(
        project_id: str,
        body: BatchGenerateChaptersRequest,
        user: Principal = Depends(current_user),
    ):
        return workflow.batch_generate_chapters(
            project_id=project_id,
            chapter_ids=body.chapter_ids,
            principal=user,
            sync_execute=body.sync_execute,
            max_context_tokens=body.max_context_tokens,
            snippet_matches_by_chapter=body.snippet_matches_by_chapter,
        )

    @router.post(
        "/projects/{project_id}/outline/auto-tree-build",
        include_in_schema=False,
    )
    def auto_build_outline_tree_endpoint(
        project_id: str,
        options: dict | None = None,
        user: Principal = Depends(current_user),
    ):
        return workflow.auto_build_outline_tree(
            principal=user,
            project_id=project_id,
            options=options,
        )

    application.include_router(router)
    include_recoverable_routes(application, workflow, current_user)
