# 为什么有这个文件：编辑台选区改写（对话助手样例）的接口（PRD v1.8 §5.11.4～5.11.8，APP-M2-T178、T180、T185、T187）。
# 它解决什么问题：页面把选中文字的位置和原文交给后端，取回 3～5 条预检后的样例；用户选一条“替换选中内容”或“插在选中内容后”，
# 后端核对编辑锁与选区后写入新版本并返回改动段落的复查结果。

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import Field

from icg.domain.domain import DemoService, Principal
from icg.domain.schemas import RequestBody, ResponseBody
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
    count: int = Field(default=3, ge=MIN_COUNT, le=MAX_COUNT, description="样例条数，3～5，默认 3")


class RewriteSample(ResponseBody):
    id: str
    style: str
    style_label: str
    text: str = Field(description="预检后的样例文字，写入时原样使用")
    warnings: list[str]
    chars: int
    sources: list[dict]
    status: Literal["proposed", "adopted", "not_adopted", "invalidated"]


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
    source_note: str
    provider: str
    model: str
    is_local_model: bool
    status: Literal["proposed", "adopted", "invalidated"]
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


def include_selection_rewrite_routes(application, service: DemoService, current_user) -> None:
    rewrite = SelectionRewriteService(service)
    application.state.selection_rewrite = rewrite
    router = APIRouter(prefix="/api/v1/projects/{project_id}/chapters/{chapter_id}",
                       responses=v1_error_responses(401, 403, 404, 409, 422, 423, 502, 503))

    @router.post("/selection-rewrites", response_model=SelectionRewriteBatch, operation_id="createSelectionRewrite",
                 summary="对选中文字生成 3～5 条改写样例",
                 description="只交给模型选区及前后段落、本章已确认条款和项目事实；样例经预检（变量与证据标记保留、敏感号码过滤、"
                             "对不上来源的数值换成【待补：数值来源】、相近合并）后保存。未接入真实模型时返回 502 MODEL_UNAVAILABLE，不给模拟样例。")
    def create(project_id: str, chapter_id: str, body: SelectionRewriteRequest, user: Principal = Depends(current_user)):
        return rewrite.generate(user, project_id, chapter_id, body.model_dump())

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
