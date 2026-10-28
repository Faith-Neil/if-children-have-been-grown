# 为什么有这个文件：把可测试的业务服务接到真实 HTTP 接口和本地操作页面。
# 它解决什么问题：标准应用工厂、统一中间件、错误处理与领域路由挂载装配。

import os
import sys
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

from icg.infra.adapters import DemoModelProvider, build_docx
from icg.infra.database import repository_from_environment
from icg.domain.domain import DemoService, DomainError, Principal
from icg.domain.errors import RETRY_GUIDANCE, enrich_openapi
from icg.domain.idempotency import IDEMPOTENCY_HEADER_DESCRIPTION, bind_request, replayed_for, reset_request
from icg.infra.openai_model import openai_provider_from_environment
from icg.domain.ports import ModelProvider, Repository, ParserProvider
from icg.domain.parsing import LocalTextParser
from icg.domain.workflow_schemas import V1Error, v1_error_responses
from icg.domain.schemas import HealthResponse

from icg.api import (
    include_session_routes,
    include_project_routes,
    include_chapter_routes,
    include_workflow_routes,
    include_volume_routes,
    include_compliance_routes,
    include_snippet_routes,
    include_model_config_routes,
    include_ragflow_routes,
    include_field_metadata_routes,
    include_company_routes,
    include_user_routes,
    include_chapter_loop_routes,
)


DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def error_responses(*statuses: int) -> dict:
    descriptions = {
        401: "未登录或演示登录已失效",
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


def create_app(repository: Repository | None = None, model_provider: ModelProvider | None = None,
               clock: Callable[[], float | datetime] | None = None,
               parser_provider: ParserProvider | None = None, *,
               use_configured_model: bool = False,
               model_transport: Any | None = None,
               evidence_service: Any | None = None) -> FastAPI:
    if model_provider is None and use_configured_model:
        model_provider = openai_provider_from_environment()
    if evidence_service is None and os.environ.get("ICG_RAGFLOW_BASE_URL", "").strip():
        try:
            from icg.infra.ragflow_client import RagflowConfig, RagflowRetrievalClient
            from icg.infra.retrieval import EvidenceCandidateService
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

    static_directory = Path(__file__).resolve().parents[2] / "icg_demo" / "static"
    if not static_directory.exists():
        static_directory = Path(__file__).resolve().parent / "static"
    application.mount("/static", StaticFiles(directory=static_directory, check_dir=False), name="static")

    product_directory = Path(__file__).resolve().parents[4] / "frontend" / "web" / "dist"
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
            response.headers["Sunset"] = "Sun, 15 Nov 2026 00:00:00 GMT"
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
            resp_headers["Sunset"] = "Sun, 15 Nov 2026 00:00:00 GMT"
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
        return error_response(request, 500, "INTERNAL_ERROR", "演示服务暂时失败，请凭请求编号核对日志。")

    def current_user(authorization: Annotated[str | None, Header()] = None) -> Principal:
        scheme, _, token = (authorization or "").partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise DomainError(401, "UNAUTHENTICATED", "请先选择演示账号登录。")
        return service.authenticate(token.strip())

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
        return FileResponse(static_directory / "index.html")

    # 按域收口注册 API 端点
    include_session_routes(application, service, current_user)
    include_project_routes(application, service, current_user)
    include_chapter_routes(application, service, current_user)
    include_workflow_routes(application, service, current_user,
                            parser_provider if parser_provider is not None else LocalTextParser())
    include_volume_routes(application, service, current_user)
    include_compliance_routes(application, service, current_user)
    include_snippet_routes(application, service, current_user)
    include_model_config_routes(application, service, current_user)
    include_ragflow_routes(application, service, current_user)
    include_field_metadata_routes(application, service, current_user)
    include_company_routes(application, service, current_user)
    include_user_routes(application, service, current_user)
    include_chapter_loop_routes(application, service, current_user)

    @application.get("/{full_path:path}", include_in_schema=False)
    def product_page(full_path: str):
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


app = create_app(use_configured_model=True) if "pytest" not in sys.modules else None
