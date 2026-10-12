# 为什么有这个文件：把可测试的业务服务接到真实 HTTP 接口和本地操作页面。
# 它解决什么问题：统一认证、错误和请求编号，让浏览器直接验证后台实际行为。

from pathlib import Path
from typing import Annotated, Callable
from datetime import datetime
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from .adapters import DemoModelProvider, MemoryRepository, build_docx
from .domain import DemoService, DomainError, Principal
from .openai_model import openai_provider_from_environment
from .ports import ModelProvider, Repository, ParserProvider
from .parsing import LocalTextParser
from .workflow_routes import include_workflow_routes
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
    # 这些声明只补接口说明，实际错误仍由既有异常处理器统一返回。
    descriptions = {401: "未登录或演示登录已失效", 403: "当前账号无操作权限",
                    404: "资源不存在或当前公司无权访问", 409: "版本、草稿或检查结果冲突",
                    422: "请求字段验证失败", 423: "编辑权被占用或已失效",
                    500: "后端演示服务异常", 502: "建议服务调用失败"}
    return {status: {"model": ErrorResponse, "description": descriptions[status]}
            for status in statuses}


def create_app(repository: Repository | None = None, model_provider: ModelProvider | None = None,
               clock: Callable[[], float | datetime] | None = None,
               parser_provider: ParserProvider | None = None, *,
               use_configured_model: bool = False) -> FastAPI:
    # 未传入适配器且未打开开关时保持演示替身。只有进程入口显式打开开关，才读取环境变量。
    if model_provider is None and use_configured_model:
        model_provider = openai_provider_from_environment()
    service = DemoService(repository if repository is not None else MemoryRepository(),
                          model_provider if model_provider is not None else DemoModelProvider(), clock)
    application = FastAPI(title="ICG 投标产品本地实现", version="reference-1",
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
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        return response

    def error_response(request: Request, status: int, code: str, message: str,
                       headers: dict | None = None, details: dict | None = None):
        request_id = getattr(request.state, "request_id", uuid4().hex)
        content = ({"code": code, "message": message, "details": details or {}, "traceId": request_id}
                   if request.url.path.startswith("/api/v1/")
                   else {"error": {"code": code, "message": message}, "request_id": request_id})
        return JSONResponse(status_code=status,
                            content=content,
                            headers={"X-Request-ID": request_id, "Cache-Control": "no-store", **(headers or {})})

    @application.exception_handler(DomainError)
    async def business_error(request: Request, error: DomainError):
        return error_response(request, error.status, error.code, error.message,
                              {"WWW-Authenticate": "Bearer"} if error.status == 401 else None,
                              error.details)

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError):
        fields = sorted({".".join(str(part) for part in item["loc"]) for item in error.errors()})
        message = "请求字段不符合演示接口要求：" + "、".join(fields)
        return error_response(request, 422, "VALIDATION_ERROR", message)

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

    @application.get("/health", response_model=HealthResponse)
    def health():
        return {"status": "ok", "mode": "local-demo", "repository": getattr(service.repository, "mode", "injected"),
                "model": "real" if getattr(service.model_provider, "is_real_model", False) else "mock",
                "persistent": False, "single_process": True}

    @application.get("/", response_class=FileResponse,
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

    @application.get("/api/demo/accounts", response_model=AccountListResponse)
    def accounts():
        return service.accounts()

    @application.post("/api/demo/login", response_model=LoginResponse,
                      responses=error_responses(401))
    def login(body: LoginRequest):
        return service.login(body.account_id)

    @application.get("/api/v1/session", response_model=ApplicationSessionResponse,
                     response_model_exclude_unset=True, operation_id="getSession",
                     responses=error_responses(401, 403, 404, 422))
    async def get_session(request: Request, user: User,
                          project_id: Annotated[str | None, Query(min_length=1, max_length=100)] = None):
        if (set(request.query_params) - {"project_id"}
                or len(request.query_params.getlist("project_id")) > 1 or await request.body()):
            raise DomainError(422, "INVALID_SESSION_INPUT", "会话只接受可选的项目ID，公司与角色范围由后台身份决定。")
        return get_application_session(service, user, project_id)

    @application.get("/api/projects", response_model=ProjectListResponse,
                     responses=error_responses(401))
    def projects(user: User):
        return service.projects(user)

    @application.post("/api/projects", response_model=ProjectResponse,
                      responses=error_responses(401, 403))
    def create_project(body: ProjectRequest, user: User):
        return service.create_project(user, body.name)

    @application.get("/api/projects/{project_id}/chapters", response_model=ChapterListResponse,
                     responses=error_responses(401, 404))
    def chapters(project_id: str, user: User):
        return service.chapters(user, project_id)

    @application.get("/api/chapters/{chapter_id}", response_model=ChapterResponse,
                     responses=error_responses(401, 404))
    def chapter(chapter_id: str, user: User):
        return service.chapter(user, chapter_id)

    @application.post("/api/chapters/{chapter_id}/lock", response_model=LeaseResponse,
                      responses=error_responses(401, 403, 404, 409, 423))
    def acquire_lock(chapter_id: str, body: LockRequest, user: User):
        return service.acquire_lock(user, chapter_id, body.takeover_reason)

    @application.post("/api/chapters/{chapter_id}/lock/renew", response_model=LeaseResponse,
                      responses=error_responses(401, 403, 404, 423))
    def renew_lock(chapter_id: str, body: LeaseRequest, user: User):
        return service.renew_lock(user, chapter_id, body.lease_token)

    @application.post("/api/chapters/{chapter_id}/lock/release", response_model=ReleasedResponse,
                      responses=error_responses(401, 403, 404, 423))
    def release_lock(chapter_id: str, body: LeaseRequest, user: User):
        return service.release_lock(user, chapter_id, body.lease_token)

    @application.put("/api/chapters/{chapter_id}/draft", response_model=DraftResponse,
                     responses=error_responses(401, 403, 404, 409, 423))
    def save_draft(chapter_id: str, body: DraftRequest, user: User):
        return service.save_draft(user, chapter_id, **body.model_dump())

    @application.delete("/api/chapters/{chapter_id}/draft", response_model=DraftDiscardResponse, responses=error_responses(401, 404, 409))
    def discard_draft(chapter_id: str, body: DraftDiscardRequest, user: User):
        return service.discard_draft(user, chapter_id, body.sequence)

    @application.post("/api/chapters/{chapter_id}/versions", response_model=VersionResponse,
                      responses=error_responses(401, 403, 404, 409, 423))
    def commit_version(chapter_id: str, body: VersionRequest, user: User):
        return service.commit_version(user, chapter_id, **body.model_dump())

    @application.get("/api/chapters/{chapter_id}/versions", response_model=VersionListResponse,
                     responses=error_responses(401, 404))
    def versions(chapter_id: str, user: User):
        return service.versions(user, chapter_id)

    @application.get("/api/chapters/{chapter_id}/audit", response_model=AuditListResponse,
                     responses=error_responses(401, 404))
    def audit(chapter_id: str, user: User):
        return service.audit(user, chapter_id)

    @application.post("/api/chapters/{chapter_id}/suggestions", response_model=SuggestionResponse,
                      responses=error_responses(401, 403, 404, 502))
    def suggest(chapter_id: str, body: SuggestionRequest, user: User):
        return service.suggest(user, chapter_id, body.instruction)

    @application.post("/api/chapters/{chapter_id}/checks", response_model=CheckResponse,
                      responses=error_responses(401, 403, 404))
    def check(chapter_id: str, body: EmptyRequest, user: User):
        return service.check(user, chapter_id)

    @application.post("/api/chapters/{chapter_id}/exports", response_model=ExportResponse,
                      responses=error_responses(401, 403, 404, 409))
    def export(chapter_id: str, body: ExportRequest, user: User):
        return service.export(user, chapter_id, body.check_id)

    @application.get("/api/exports/{export_id}/file", response_class=Response,
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

    @application.get("/{full_path:path}", include_in_schema=False)
    def product_page(full_path: str):
        # 深链接和刷新必须回到同一张页面；接口、静态资源和构建产物仍按原路径返回。
        if full_path == "api" or full_path.startswith(("api/", "static/", "assets/")):
            raise HTTPException(status_code=404)
        path = product_directory / "index.html"
        if not path.is_file():
            raise DomainError(503, "UI_NOT_READY", "产品页面尚未构建，请按前端运行说明先构建页面。")
        return FileResponse(path)

    return application


app = create_app(use_configured_model=True)
