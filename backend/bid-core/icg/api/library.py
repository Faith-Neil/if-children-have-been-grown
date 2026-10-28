# 为什么有这个文件：将方案片段与知识库管理的 API 路由收敛到统一接口层。
# 它解决什么问题：实现 PRD 知识库片段多租户隔离发布与同步端点。

import json
from fastapi import APIRouter, Depends, Header, Response

from icg.domain.idempotency import IDEMPOTENCY_HEADER_DESCRIPTION
from icg.domain.workflow_schemas import (
    SnippetPublication,
    SnippetPublicationCreate,
    SnippetPublicationDraft,
    SnippetPublicationList,
    SnippetPublishResult,
    SnippetSyncResult,
    v1_error_responses,
)
from icg.domain.schemas import EmptyRequest
from icg.domain.snippet_publication import (
    MemorySnippetPublicationStore,
    SnippetPublicationService,
    content_hash,
)


def _list_etag(items: list) -> str:
    return content_hash(json.dumps(items, ensure_ascii=False, sort_keys=True))


def include_snippet_routes(application, service, current_user) -> None:
    store = MemorySnippetPublicationStore(clock=service._now, repository=service.repository)
    application.state.snippet_publications = store
    service.snippet_publications = store
    publications = SnippetPublicationService(store, service.repository, service._now, service._writer)
    application.state.snippet_publication_service = publications
    router = APIRouter(prefix="/api/v1", responses=v1_error_responses(401, 403, 404, 409, 422, 428, 500))

    @router.get("/snippet-publications", response_model=SnippetPublicationList, operation_id="listSnippetPublications")
    def list_publications(response: Response, user=Depends(current_user)):
        """列出本公司片段。响应头 ETag 是这份列表的指纹，不是单条草稿版本。"""
        result = publications.list(user)
        response.headers["ETag"] = '"' + _list_etag(result["items"]) + '"'
        return result

    @router.post("/snippet-publications", response_model=SnippetPublication, operation_id="createSnippetPublication")
    def create_publication(body: SnippetPublicationCreate, response: Response, user=Depends(current_user),
                           if_match: str | None = Header(default=None),
                           idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        """服务端分配片段 id。公司来自登录身份。不需要 If-Match。"""
        result = publications.create(user, body.model_dump(), idempotency_key, if_match)
        response.headers["ETag"] = f'"{result["draft_revision"]}"'
        return result

    @router.get("/snippet-publications/{snippet_id}", response_model=SnippetPublication, operation_id="getSnippetPublication")
    def get_publication(snippet_id: str, response: Response, user=Depends(current_user)):
        """读取一条。ETag 是 draft_revision，供保存草稿和发布的 If-Match 使用。详情里的 kb_sync_status 就是同步状态，不再另设 GET .../sync。"""
        result = publications.get(user, snippet_id)
        response.headers["ETag"] = f'"{result["draft_revision"]}"'
        return result

    @router.put("/snippet-publications/{snippet_id}", response_model=SnippetPublication, operation_id="saveSnippetPublicationDraft")
    def save_publication(snippet_id: str, body: SnippetPublicationDraft, response: Response, user=Depends(current_user),
                         if_match: str | None = Header(default=None),
                         idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        """保存草稿。If-Match 核对 draft_revision。不替换已发布正文。"""
        result = publications.save_draft(user, snippet_id, body.model_dump(exclude_unset=True), if_match, idempotency_key)
        response.headers["ETag"] = f'"{result["draft_revision"]}"'
        return result

    @router.post("/snippet-publications/{snippet_id}/publish", response_model=SnippetPublishResult, operation_id="publishSnippetPublication")
    def publish_publication(snippet_id: str, body: EmptyRequest, user=Depends(current_user),
                            if_match: str | None = Header(default=None),
                            idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        """发布。If-Match 核对 draft_revision。被拦截时返回 200 和原因，记录与审计不变，但仍记下幂等回执。"""
        return publications.publish(user, snippet_id, body.model_dump(), if_match, idempotency_key)

    @router.post("/snippet-publications/{snippet_id}/sync", response_model=SnippetSyncResult, operation_id="syncSnippetPublication")
    def sync_publication(snippet_id: str, body: EmptyRequest, user=Depends(current_user),
                         if_match: str | None = Header(default=None),
                         idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", description=IDEMPOTENCY_HEADER_DESCRIPTION)):
        """重新同步。If-Match 核对 published_revision。失败不把 kb_sync_status 写成 synced。正文含 [[sync-fail]] 时模拟知识库拒绝。"""
        return publications.sync(user, snippet_id, body.model_dump(), if_match, idempotency_key)

    application.include_router(router)
