# 为什么有这个文件：对外暴露公司知识库（RAGFlow）的同步状态、手动对账和检索试查接口。
# 它解决什么问题：资料管理员能看到每条资料是否已进入知识库、失败原因，并能手动重试；检索试查用于核对召回质量。

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import Field

from icg.domain.domain import DemoService, DomainError, Principal
from icg.domain.schemas import RequestBody, ResponseBody
from icg.domain.workflow_schemas import v1_error_responses


class KnowledgeBaseItem(ResponseBody):
    key: str
    source_type: str = Field(description="library 或 snippet")
    source_id: str
    name: str
    item_type: str
    revision: int
    status: str = Field(description="unsynced / parsing / synced / failed")
    message: str = ""
    chunk_count: int = 0
    updated_at: str | None = None
    document_id: str = ""


class KnowledgeBaseStatus(ResponseBody):
    enabled: bool = Field(description="是否已配置并启用 RAGFlow（含 API Key）")
    dataset_id: str = ""
    last_sync_at: str | None = None
    last_error: str = ""
    counts: dict[str, int] = Field(default_factory=dict)
    items: list[KnowledgeBaseItem] = Field(default_factory=list)


class KnowledgeBaseSyncResult(ResponseBody):
    enabled: bool
    uploaded: int = 0
    deleted: int = 0
    failed: int = 0
    unchanged: int = 0
    message: str = ""
    status_counts: dict[str, int] = Field(default_factory=dict)


class KnowledgeSearchRequest(RequestBody):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=6, ge=1, le=20)
    kinds: list[str] | None = Field(default=None, description="evidence / snippet / history，留空为全部")


class KnowledgeSearchHit(ResponseBody):
    source_type: str
    source_id: str
    name: str
    item_type: str
    revision: int
    score: float
    content: str
    document_id: str
    chunk_ids: list[str] = Field(default_factory=list)
    attachable: bool = Field(description="是否可由人挂接为 [证]；检索命中本身永远不是 [证]")
    reference_only: bool
    cite_tag: str


class KnowledgeSearchResult(ResponseBody):
    items: list[KnowledgeSearchHit] = Field(default_factory=list)
    skipped_reason: str = ""


def include_knowledge_base_routes(application, service: DemoService, current_user) -> None:
    kb = service.knowledge_base
    router = APIRouter(prefix="/api/v1/knowledge-base", responses=v1_error_responses(401, 403, 422, 500))

    @router.get("/status", response_model=KnowledgeBaseStatus, operation_id="getKnowledgeBaseStatus")
    def kb_status(refresh: bool = Query(default=False, description="为 true 时向 RAGFlow 刷新解析中的文档状态"),
                  user: Principal = Depends(current_user)):
        """本公司资料与已发布片段在知识库中的同步状态。只列出应当在知识库中的内容。"""
        company = user.user.company_id
        return kb.refresh_status(company) if refresh else kb.status(company)

    @router.post("/sync", response_model=KnowledgeBaseSyncResult, operation_id="syncKnowledgeBase")
    def kb_sync(user: Principal = Depends(current_user)):
        """手动全量对账：上传新增/改版资料，删除旧版本与已撤销、过期资料对应的文档。需要资料写权限。"""
        service._writer(user)
        return kb.sync_company(user.user.company_id)

    @router.post("/search", response_model=KnowledgeSearchResult, operation_id="searchKnowledgeBase")
    def kb_search(body: KnowledgeSearchRequest, user: Principal = Depends(current_user)):
        """检索试查。命中按资料聚合并实时复核状态；受限资料只对有权限的账号返回。"""
        allowed = {"evidence", "snippet", "history"}
        kinds = set(body.kinds or allowed)
        if not kinds <= allowed:
            raise DomainError(422, "VALIDATION_ERROR", "kinds 只能是 evidence、snippet、history。")
        try:
            hits, reason = kb.search(user.user.company_id, body.query, limit=body.limit, kinds=kinds, user=user.user)
        except Exception as exc:
            return {"items": [], "skipped_reason": f"检索失败：{type(exc).__name__}"}
        return {"items": [h.to_public() for h in hits], "skipped_reason": reason}

    application.include_router(router)


__all__: list[Any] = ["include_knowledge_base_routes"]
