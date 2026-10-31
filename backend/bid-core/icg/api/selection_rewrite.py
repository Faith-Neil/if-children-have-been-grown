# 为什么有这个文件：编辑台选区改写（对话助手样例）的接口（PRD v1.8 §5.11.4～5.11.8，APP-M2-T178、T180、T185、T187）。
# 它解决什么问题：页面把选中文字的位置和原文交给后端，取回 3～5 条预检后的样例；用户选一条“替换选中内容”或“插在选中内容后”，
# 后端核对编辑锁与选区后写入新版本并返回改动段落的复查结果。另有：公司策略与当前模型（assistant-policy）、
# 流式生成（各写法完成即推送）、本人会话列表与会话详情（项目负责人、公司管理员可看）。

import json
import threading
from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import iterate_in_threadpool, run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import Field

from icg.domain.domain import DemoService, Principal
from icg.domain.schemas import RequestBody, ResponseBody
from icg.domain.assistant_sessions import list_sessions, session_detail
from icg.domain.selection_rewrite import MAX_COUNT, MAX_SELECTION, MIN_COUNT, SelectionRewriteService
from icg.domain.workflow_schemas import v1_error_responses

RewriteMode = Literal["rewrite", "expand", "shorten", "instruction", "rephrase"]


class SelectionRewriteRequest(RequestBody):
    base_revision: int = Field(ge=1, description="选区所在的已提交章节版本")
    start: int = Field(ge=0, description="选区在已提交正文中的起始字符位置")
    end: int = Field(ge=1, description="选区结束位置（不含）")
    selected_text: str = Field(min_length=1, max_length=MAX_SELECTION, description="选中的原文，须与正文 [start, end) 完全一致")
    mode: RewriteMode = Field(default="rewrite", description="改写 / 扩写 / 缩写 / 按指令修改 / 换一种说法")
    instruction: str = Field(default="", max_length=500, description="按指令修改时必填")
    count: int | None = Field(default=None, ge=MIN_COUNT, le=MAX_COUNT, description="样例条数 3～5；不传取公司设置（默认 3）")
    knowledge_base_enabled: bool | None = Field(default=None, description="知识库开关；不传取公司默认值。公司不允许关闭时传 false 返回 422")
    session_id: str | None = Field(default=None, max_length=120, description="接着本人本章的会话提问；不传则新建会话")


class AssistantQuestionRequest(RequestBody):
    question: str = Field(min_length=1, max_length=1000, description="不选中正文时的自由提问")
    knowledge_base_enabled: bool | None = Field(default=None, description="知识库开关；不传取公司默认值")
    session_id: str | None = Field(default=None, max_length=120, description="接着本人本章的会话提问")


class RewriteSource(ResponseBody):
    cite_tag: str = Field(description="写入正文的引用标记，如 [片:lib-1]")
    source_id: str
    source_type: str
    name: str
    item_type: str
    revision: int
    score: float
    content: str
    document_id: str
    chunk_ids: list[str]


class Retrieval(ResponseBody):
    status: Literal["off", "found", "empty"]
    message: str
    count: int | None = None


class RewriteSample(ResponseBody):
    id: str
    style: str
    style_label: str
    text: str = Field(description="预检后的样例文字，写入时原样使用")
    warnings: list[str]
    chars: int
    sources: list[RewriteSource] = Field(description="样例引用的本次检索结果；知识库关闭时为空")
    status: Literal["proposed", "adopted", "not_adopted", "invalidated"]
    model: str | None = Field(default=None, description="实际生成这条样例的模型")
    is_local_model: bool | None = None
    is_fallback: bool = Field(default=False, description="主模型失败后由备用模型生成")
    fallback_reason: str = ""


class FallbackUse(ResponseBody):
    style: str
    model: str = Field(description="改用的备用模型")
    reason: str = Field(description="改用原因：主模型超时、连接失败、限流或暂时不可用")


class DroppedSample(ResponseBody):
    style: str
    reason: str


class SelectionRewriteBatch(ResponseBody):
    id: str
    chapter_id: str
    base_revision: int
    start: int
    end: int
    selected_text: str
    selection_hash: str
    mode: RewriteMode
    mode_label: str
    instruction: str
    samples: list[RewriteSample]
    dropped: list[DroppedSample] = Field(description="未展示的样例及原因（预检不通过、模型失败、相近合并）")
    knowledge_base_enabled: bool
    retrieval: Retrieval
    source_note: str
    session_id: str | None = None
    provider: str
    model: str
    is_local_model: bool
    fallback_used: list[FallbackUse] = Field(default_factory=list, description="改用备用模型的写法")
    models_used: list[str] = Field(default_factory=list, description="本批样例实际用到的模型")
    status: Literal["proposed", "adopted", "invalidated", "no_results"] = Field(
        description="no_results：知识库打开但没有检索到本公司资料，未调用模型")
    created_at: str


class SelectionApplyRequest(RequestBody):
    lease_token: str = Field(min_length=1, max_length=500)
    sample_id: str = Field(min_length=1, max_length=120)
    action: Literal["replace", "insert_after"] = Field(description="替换选中内容 / 插在选中内容后")
    confirm_start: int | None = Field(default=None, ge=0,
                                      description="原文位置变化后，用户核对过的新起始位置（取自上一次 409 的 details.start）")


class RecheckIssue(ResponseBody):
    rule_id: str
    severity: str
    message: str


class EditOperation(ResponseBody):
    id: str
    chapter_id: str
    edit_mode: Literal["assistant_replace", "assistant_insert"]
    edit_mode_label: str
    base_revision: int
    result_revision: int
    selection: dict
    changed_range: list[int]
    batch_id: str
    sample_id: str
    style: str
    mode: str
    knowledge_base_enabled: bool
    sources: list[dict]
    source_note: str
    session_id: str | None = None
    original_text: str
    written_text: str
    actor_id: str
    actor_name: str
    created_at: str
    recheck: dict = Field(description="改动段落的文字规则复查：scope、issues（rule_id/severity/message）、checked_at")


class SelectionApplyResult(ResponseBody):
    invalidated: bool
    revision: int
    content: str
    operation: EditOperation
    batch: SelectionRewriteBatch


class EditOperationList(ResponseBody):
    operations: list[EditOperation]


class AssistantPolicy(ResponseBody):
    enabled: bool
    kb_default: bool = Field(description="新会话知识库开关默认值（公司设置）")
    allow_kb_off: bool = Field(description="是否允许关闭知识库（公司设置）")
    count: int = Field(description="默认样例条数")
    model: str
    is_real_model: bool
    is_local_model: bool
    sensitive_project: bool
    knowledge_base_connected: bool
    fallback_model: str | None = Field(default=None, description="已配置且本项目可用的备用模型；敏感项目只列本地备用")
    streaming: bool = Field(default=False, description="主模型是否逐字流式输出")


class SessionSummary(ResponseBody):
    id: str
    chapter_id: str
    chapter_title: str
    owner_id: str
    owner_name: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class SessionList(ResponseBody):
    sessions: list[SessionSummary]


class SessionDetail(SessionSummary):
    messages: list[dict] = Field(description="按时间排列、只追加的消息：selection_request / samples（含 batch）/ applied / question / answer")
    read_only: bool = Field(description="不是本人的会话（负责人或公司管理员查看）时为 true")


def include_selection_rewrite_routes(application, service: DemoService, current_user) -> None:
    rewrite = SelectionRewriteService(service)
    application.state.selection_rewrite = rewrite
    from icg.domain.assistant_qa import AssistantQAService
    qa = AssistantQAService(service, rewrite)
    application.state.assistant_qa = qa
    router = APIRouter(prefix="/api/v1/projects/{project_id}/chapters/{chapter_id}",
                       responses=v1_error_responses(401, 403, 404, 409, 422, 423, 502, 503))

    @router.post("/selection-rewrites", response_model=SelectionRewriteBatch, operation_id="createSelectionRewrite",
                 summary="对选中文字生成 3～5 条改写样例",
                 description="只交给模型选区及前后段落、本章已确认条款和项目事实；样例经预检（变量与证据标记保留、敏感号码过滤、"
                             "对不上来源的数值换成【待补：数值来源】、相近合并）后保存。未接入真实模型时返回 502 MODEL_UNAVAILABLE，不给模拟样例。")
    def create(project_id: str, chapter_id: str, body: SelectionRewriteRequest, user: Principal = Depends(current_user)):
        return rewrite.generate(user, project_id, chapter_id, body.model_dump())

    @router.post("/selection-rewrites/stream", response_class=StreamingResponse, operation_id="streamSelectionRewrite",
                 summary="流式生成选区改写样例",
                 description="与 createSelectionRewrite 相同的核对在开始前完成（出错按 HTTP 状态返回）；之后以 text/event-stream 推送："
                             "started（写法、检索结果、主模型与备用模型）→ delta（逐字文字，按写法）/ fallback（该写法改用备用模型）→ "
                             "sample / dropped（每种写法完成即推送）→ done（含 batch）；中途失败推送 error。客户端断开连接即停止生成、不保存。",
                 responses={200: {"description": "SSE 事件流", "content": {"text/event-stream": {"schema": {"type": "string"}}}}})
    async def stream(project_id: str, chapter_id: str, body: SelectionRewriteRequest, request: Request,
                     user: Principal = Depends(current_user)):
        prepared = await run_in_threadpool(rewrite.prepare, user, project_id, chapter_id, body.model_dump())
        cancel = threading.Event()
        iterator = rewrite.stream(prepared, cancel=cancel)

        async def events():
            # 用户点“停止”或关闭页面即断开连接：置位 cancel，模型调用停下，本次样例不保存
            try:
                async for event in iterate_in_threadpool(iterator):
                    if await request.is_disconnected():
                        cancel.set()
                        break
                    yield f"event: {event['event']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            finally:
                cancel.set()

        return StreamingResponse(events(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})

    @router.post("/assistant-questions/stream", response_class=StreamingResponse, operation_id="streamAssistantReply",
                 summary="自由提问（流式，只回答不写入）",
                 description="先按词表判断直查本项目或本公司数据，命中且查到时返回答案卡（不调用模型）；否则逐字流式回答，知识库打开时只能引用本次检索结果。"
                             "事件：started → answer_card 或 delta / fallback / queued → done（含 answer，can_insert 恒为 false）；失败推送 error。"
                             "未接入真实模型返回 502 MODEL_UNAVAILABLE。客户端断开即停止、不保存。",
                 responses={200: {"description": "SSE 事件流", "content": {"text/event-stream": {"schema": {"type": "string"}}}}})
    async def ask(project_id: str, chapter_id: str, body: AssistantQuestionRequest, request: Request,
                  user: Principal = Depends(current_user)):
        prepared = await run_in_threadpool(qa.prepare, user, project_id, chapter_id, body.model_dump())
        cancel = threading.Event()
        iterator = qa.stream(prepared, cancel=cancel)

        async def events():
            try:
                async for event in iterate_in_threadpool(iterator):
                    if await request.is_disconnected():
                        cancel.set()
                        break
                    yield f"event: {event['event']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            finally:
                cancel.set()

        return StreamingResponse(events(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})

    @router.get("/assistant-policy", response_model=AssistantPolicy, operation_id="getAssistantPolicy",
                summary="对话助手的公司策略与当前模型")
    def policy(project_id: str, chapter_id: str, user: Principal = Depends(current_user)):
        return rewrite.policy(user, project_id, chapter_id)

    @router.get("/assistant-sessions", response_model=SessionList, operation_id="listAssistantSessions",
                summary="本章的对话助手会话", description="本人只看自己的会话；项目负责人和本公司公司管理员可看全部。")
    def sessions(project_id: str, chapter_id: str, user: Principal = Depends(current_user)):
        return list_sessions(service, user, project_id, chapter_id)

    @router.post("/selection-rewrites/{batch_id}/apply", response_model=SelectionApplyResult,
                 operation_id="applySelectionRewrite", summary="把选定样例替换选中内容或插在其后",
                 description="须持有本章编辑锁；写入服务端保存的样例原文。选区被改动但能唯一找到时返回 409 REVISION_CONFLICT，"
                             "details.relocated=true 和新位置，用户再次核对后带 confirm_start 重试；找不到或多处时样例失效（relocated=false）。")
    def apply(project_id: str, chapter_id: str, batch_id: str, body: SelectionApplyRequest,
              user: Principal = Depends(current_user)):
        return rewrite.apply(user, project_id, chapter_id, {**body.model_dump(), "batch_id": batch_id})

    @router.get("/edit-operations", response_model=EditOperationList, operation_id="listChapterEditOperations",
                summary="本章的对话助手编辑记录")
    def operations(project_id: str, chapter_id: str, user: Principal = Depends(current_user)):
        return rewrite.operations(user, project_id, chapter_id)

    application.include_router(router)

    project_router = APIRouter(prefix="/api/v1/projects/{project_id}", responses=v1_error_responses(401, 403, 404))

    @project_router.get("/assistant-sessions/{session_id}", response_model=SessionDetail, operation_id="getAssistantSession",
                        summary="对话助手会话详情（只追加的消息记录）")
    def session(project_id: str, session_id: str, user: Principal = Depends(current_user)):
        return session_detail(service, user, project_id, session_id)

    application.include_router(project_router)
