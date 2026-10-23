# 为什么有这个文件：把可测试的业务服务接到真实 HTTP 接口和本地操作页面。
# 它解决什么问题：统一认证、错误和请求编号，让浏览器直接验证后台实际行为。

import os
from pathlib import Path
from typing import Annotated, Any, Callable
from datetime import datetime
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from .adapters import DemoModelProvider, build_docx
from .database import repository_from_environment
from .domain import DemoService, DomainError, Principal
from .errors import RETRY_GUIDANCE, enrich_openapi
from .idempotency import IDEMPOTENCY_HEADER_DESCRIPTION, bind_request, replayed_for, reset_request
from .openai_model import openai_provider_from_environment
from .ports import ModelProvider, Repository, ParserProvider
from .parsing import LocalTextParser
from .model_config_storage import include_model_config_routes
from .field_metadata import include_field_metadata_routes
from .snippet_publication import include_snippet_routes
from .workflow_routes import include_workflow_routes
from icg.api import include_volume_routes, include_compliance_routes
from .workflow_schemas import V1Error, v1_error_responses
from .session_navigation import get_application_session
from .schemas import (AccountListResponse, ApplicationSessionResponse, AuditListResponse, ChapterListResponse,
                      ChapterResponse, CheckResponse, DraftRequest, DraftResponse, DraftDiscardRequest, DraftDiscardResponse,
                      EmptyRequest, ErrorResponse, ExportRequest, ExportResponse,
                      HealthResponse, LeaseRequest, LeaseResponse, LockRequest,
                      LoginRequest, LoginResponse, ProjectListResponse, ProjectRequest,
                      ProjectResponse, ReleasedResponse, SuggestionRequest,
                      SuggestionResponse, VersionListResponse, VersionRequest,
                      VersionResponse)


DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def error_responses(*statuses: int) -> dict:
    # 这些声明只补接口说明，全量接口统一使用 V1Error 错误体模型。
    descriptions = {401: "未登录或演示登录已失效", 403: "当前账号无操作权限",
                    404: "资源不存在或当前公司无权访问", 409: "版本、草稿或检查结果冲突",
                    422: "请求字段验证失败", 423: "编辑权被占用或已失效",
                    428: "缺少重复请求标记或标记无效",
                    500: "后端演示服务异常", 502: "建议服务调用失败"}
    return {status: {"model": V1Error, "description": descriptions[status]}
            for status in statuses}


def create_app(repository: Repository | None = None, model_provider: ModelProvider | None = None,
               clock: Callable[[], float | datetime] | None = None,
               parser_provider: ParserProvider | None = None, *,
               use_configured_model: bool = False,
               model_transport: Any | None = None,
               evidence_service: Any | None = None) -> FastAPI:
    # 未传入仓库时读取 ICG_DATABASE_URL；未设置则仍用内存仓库。显式传入的仓库优先。
    # 模型仍只在进程入口打开开关时读取环境变量，未打开时保持演示替身。
    if model_provider is None and use_configured_model:
        model_provider = openai_provider_from_environment()
    if evidence_service is None and os.environ.get("ICG_RAGFLOW_BASE_URL", "").strip():
        try:
            from .ragflow_client import RagflowConfig, RagflowRetrievalClient
            from .retrieval import EvidenceCandidateService
            rag_cfg = RagflowConfig.from_env()
            rag_client = RagflowRetrievalClient(rag_cfg)
            evidence_service = EvidenceCandidateService(ragflow_client=rag_client)
        except Exception:
            evidence_service = None
    service = DemoService(repository if repository is not None else repository_from_environment(),
                          model_provider if model_provider is not None else DemoModelProvider(),
                          clock, model_transport=model_transport,
                          evidence_service=evidence_service)
    application = FastAPI(title="ICG 投标产品本地实现", version="reference-1",
                          description="本地演示接口。使用统一错误体；" + RETRY_GUIDANCE,
                          docs_url=None, redoc_url=None,
                          responses=error_responses(422, 500))
    application.state.service = service
    static_directory = Path(__file__).resolve().parent / "static"
    application.mount("/static", StaticFiles(directory=static_directory, check_dir=False), name="static")
    product_directory = Path(__file__).resolve().parents[3] / "frontend" / "web" / "dist"
    application.mount("/assets", StaticFiles(directory=product_directory / "assets", check_dir=False), name="product-assets")

    @application.middleware("http")
    async def request_identity(request: Request, call_next):
        request.state.request_id = uuid4().hex
        token = bind_request(request)
        try:
            response = await call_next(request)
        finally:
            reset_request(token)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        if request.url.path.startswith("/api/demo"):
            response.headers["Deprecation"] = "true"
        if replayed_for(request):
            response.headers["Idempotent-Replayed"] = "true"
        return response

    def error_response(request: Request, status: int, code: str, message: str,
                       headers: dict | None = None, details: dict | None = None):
        request_id = getattr(request.state, "request_id", uuid4().hex)
        content = {"code": code, "message": message, "details": details or {}, "traceId": request_id}
        if request.url.path.startswith("/api/chapters/") and "/suggestions" in request.url.path:
            content["error"] = {"code": code, "message": message}
            content["request_id"] = request_id
        resp_headers = {"X-Request-ID": request_id, "Cache-Control": "no-store", **(headers or {})}
        if request.url.path.startswith("/api/demo"):
            resp_headers["Deprecation"] = "true"
        return JSONResponse(status_code=status,
                            content=content,
                            headers=resp_headers)

    @application.exception_handler(DomainError)
    async def business_error(request: Request, error: DomainError):
        return error_response(request, error.status, error.code, error.message,
                              {"WWW-Authenticate": "Bearer"} if error.status == 401 else None,
                              error.details)

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError):
        fields = sorted({".".join(str(part) for part in item["loc"]) for item in error.errors()})
        message = "请求字段不符合演示接口要求：" + "、".join(fields)
        return error_response(request, 422, "VALIDATION_ERROR", message, details={"fields": fields})

    @application.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException):
        return error_response(request, error.status_code, "NOT_FOUND" if error.status_code == 404 else "HTTP_ERROR",
                              "未找到此页面或接口。" if error.status_code == 404 else "请求不能执行。", error.headers)

    @application.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception):
        # 不向浏览器暴露服务器堆栈、目录或底层适配器的异常内容。
        return error_response(request, 500, "INTERNAL_ERROR", "演示服务暂时失败，请凭请求编号核对日志。")

    def current_user(authorization: Annotated[str | None, Header()] = None) -> Principal:
        scheme, _, token = (authorization or "").partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise DomainError(401, "UNAUTHENTICATED", "请先选择演示账号登录。")
        return service.authenticate(token.strip())

    User = Annotated[Principal, Depends(current_user)]

    @application.get("/health", response_model=HealthResponse, operation_id="getHealth")
    def health():
        return {"status": "ok", "mode": "local-demo", "repository": getattr(service.repository, "mode", "injected"),
                "model": "real" if getattr(service.model_provider, "is_real_model", False) else "mock",
                "persistent": False, "single_process": True}

    @application.get("/", response_class=FileResponse, operation_id="getIndex",
                     responses={**error_responses(404), 200: {"description": "本地操作页面",
                                "content": {"text/html": {"schema": {"type": "string"}}}}})
    def index():
        path = product_directory / "index.html"
        if not path.is_file():
            raise DomainError(503, "UI_NOT_READY", "产品页面尚未构建，请按前端运行说明先构建页面。")
        return FileResponse(path)

    @application.get("/demo", response_class=FileResponse, include_in_schema=False)
    def developer_demo():
        # 原后台验证页保留作开发工具，产品主入口使用同一后台的 ICG 页面。
        return FileResponse(static_directory / "index.html")

    @application.get("/api/demo/accounts", response_model=AccountListResponse, operation_id="listAccounts", deprecated=True)
    def accounts():
        return service.accounts()

    @application.post("/api/demo/login", response_model=LoginResponse, operation_id="login",
                      responses=error_responses(401), deprecated=True)
    def login(body: LoginRequest):
        return service.login(body.account_id)

    @application.get("/api/v1/session", response_model=ApplicationSessionResponse,
                     response_model_exclude_unset=True, operation_id="getSession",
                     responses=v1_error_responses(401, 403, 404, 422, 500))
    async def get_session(request: Request, user: User,
                          project_id: Annotated[str | None, Query(min_length=1, max_length=100)] = None):
        if (set(request.query_params) - {"project_id"}
                or len(request.query_params.getlist("project_id")) > 1 or await request.body()):
            raise DomainError(422, "INVALID_SESSION_INPUT", "会话只接受可选的项目ID，公司与角色范围由后台身份决定。")
        return get_application_session(service, user, project_id)

    @application.get("/api/projects", response_model=ProjectListResponse, operation_id="listProjects",
                     responses=error_responses(401))
    def projects(user: User):
        return service.projects(user)

    @application.get("/api/projects/{project_id}", response_model=ProjectResponse, operation_id="getProject",
                     responses=error_responses(401, 404))
    def project(project_id: str, user: User):
        return service.project(user, project_id)

    @application.post("/api/projects", response_model=ProjectResponse, operation_id="createProject",
                      responses=error_responses(401, 403, 409, 428))
    def create_project(body: ProjectRequest, user: User,
                       idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)] = None):
        return service.create_project(user, body.name, idempotency_key=idempotency_key)

    @application.get("/api/v1/projects", response_model=ProjectListResponse, operation_id="listV1Projects",
                     responses=v1_error_responses(401))
    def list_v1_projects(user: User):
        return service.projects(user)

    @application.post("/api/v1/projects", response_model=ProjectResponse, operation_id="createV1Project",
                      responses=v1_error_responses(401, 403, 409, 428))
    def create_v1_project(body: ProjectRequest, user: User,
                          idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)] = None):
        return service.create_project(user, body.name, idempotency_key=idempotency_key)

    @application.get("/api/v1/projects/{project_id}", response_model=ProjectResponse, operation_id="getV1Project",
                     responses=v1_error_responses(401, 404))
    def get_v1_project(project_id: str, user: User):
        return service.project(user, project_id)

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

    include_workflow_routes(application, service, current_user,
                            parser_provider if parser_provider is not None else LocalTextParser())
    include_volume_routes(application, service, current_user)
    include_compliance_routes(application, service, current_user)
    include_snippet_routes(application, service, current_user)
    include_model_config_routes(application, service, current_user)
    include_field_metadata_routes(application, service, current_user)

    @application.get("/{full_path:path}", include_in_schema=False)
    def product_page(full_path: str):
        # 深链接和刷新必须回到同一张页面；接口、静态资源和构建产物仍按原路径返回。
        # 只返回固定的 index.html，不按请求路径打开文件，因此 .. 不能读出页面目录之外的内容。
        # 大小写不敏感处理 /api 前缀，满足 QA 200a105 E2E-D5：/API、/Api/... 均返回 JSON 404
        normalized = full_path.lower()
        if (".." in full_path.split("/")
                or normalized == "api"
                or normalized.startswith("api/")
                or full_path.startswith(("static/", "assets/"))):
            raise HTTPException(status_code=404)
        index = (product_directory / "index.html").resolve()
        if index.parent != product_directory.resolve():
            raise HTTPException(status_code=404)
        if not index.is_file():
            raise DomainError(503, "UI_NOT_READY", "产品页面尚未构建，请按前端运行说明先构建页面。")
        return FileResponse(index)

    def custom_openapi():
        if application.openapi_schema:
            return application.openapi_schema
        schema = get_openapi(title=application.title, version=application.version,
                             description=application.description, routes=application.routes)
        application.openapi_schema = enrich_openapi(schema)
        return application.openapi_schema

    application.openapi = custom_openapi
    return application


app = create_app(use_configured_model=True)
