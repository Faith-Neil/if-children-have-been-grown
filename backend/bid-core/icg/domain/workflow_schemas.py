# 为什么有这个文件：给示例主流程提供可生成接口契约的业务字段。
# 它解决什么问题：前后端使用真实且明确的数据结构，不靠猜字段或空响应接通页面。

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .schemas import ChapterSummaryResponse, DemoCompanyRole, RequestBody, ResponseBody, LockSummaryResponse, AccountResponse
from .sla_schemas import ProjectSla

Volume = Literal["technical", "business"]
ReviewStatus = Literal["pending", "confirmed", "rejected"]
LibraryType = Literal["qualification", "personnel", "performance", "sla", "snippet", "history"]


class ProjectPartnerInput(RequestBody):
    partner_entity_id: str = Field(min_length=1, max_length=100)
    agreement_attachment_id: str | None = Field(default=None, max_length=100)


class ProjectPatch(RequestBody):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    tender_number: str | None = Field(default=None, max_length=100)
    deadline: str | None = Field(default=None, max_length=50)
    sensitive: bool | None = None
    project_partners: list[ProjectPartnerInput] | None = None


class FileUpload(RequestBody):
    filename: str = Field(min_length=1, max_length=180)
    content_base64: str = Field(min_length=1, max_length=7_000_000)


class FileDelete(RequestBody):
    reason: str = Field(min_length=1, max_length=2000, description="说明误传或解析失败的原因；只允许无来源引用的未解析/失败文件")


class ParseRequest(RequestBody):
    file_ids: list[str] | None = None


class RequirementPatch(RequestBody):
    text: str | None = Field(default=None, min_length=1, max_length=20_000)
    category: str | None = Field(default=None, min_length=1, max_length=60)
    volume: Volume | None = None
    chapter_id: str | None = None
    status: ReviewStatus | None = None
    response: str | None = Field(default=None, max_length=20_000)
    reason: str | None = Field(default=None, max_length=2000)
    evidence_ids: list[str] | None = None
    deviation_type: str | None = Field(default=None, max_length=50)
    deviation_reason: str | None = Field(default=None, max_length=2000)


class FactPatch(RequestBody):
    value: str | None = Field(default=None, min_length=1, max_length=2000)
    status: ReviewStatus | None = None
    reason: str | None = Field(default=None, max_length=2000)


class ConflictPatch(RequestBody):
    selected_fact_id: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=2000)


class PlannedChapter(RequestBody):
    id: str | None = Field(default=None, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    volume: Volume
    fact_ids: list[str] = Field(default_factory=list, max_length=500)
    writing_points: str = Field(default="", max_length=5000)
    target_length: int | None = Field(default=None, ge=1, le=100_000)
    assignee_id: str | None = Field(default=None, max_length=100)

    @field_validator("fact_ids")
    @classmethod
    def fact_identifiers(cls, values):
        if any(not value.strip() or len(value) > 100 for value in values):
            raise ValueError("事实标识必须完整且不超过100字")
        return values


class PlanRequest(RequestBody):
    chapters: list[PlannedChapter] = Field(min_length=1, max_length=100)
    scope: Literal["all", "technical", "business"] = "all"
    reason: str = Field(default="", max_length=2000)


class ChapterPlanPatch(RequestBody):
    fact_ids: list[str] = Field(default_factory=list, max_length=500)
    writing_points: str = Field(default="", max_length=5000)
    target_length: int | None = Field(default=None, ge=1, le=100_000)


class TeamMemberInput(RequestBody):
    user_id: str = Field(min_length=1, max_length=100)
    project_role: Literal["lead", "writer", "readonly"]
    volumes: list[Volume] = Field(default_factory=list, max_length=2)


class VolumeOwnerInput(RequestBody):
    volume: Volume
    owner_id: str | None


class TeamUpdate(RequestBody):
    members: list[TeamMemberInput] = Field(min_length=1, max_length=500)
    volumes: list[VolumeOwnerInput] = Field(min_length=2, max_length=2)
    assembly_owner_id: str | None
    reason: str = Field(default="", max_length=2000)


class ChapterAssignment(RequestBody):
    assignee_id: str | None
    reason: str = Field(default="", max_length=2000)


class GenerateRequest(RequestBody):
    chapter_ids: list[str] | None = None


class ProjectCheckRequest(RequestBody):
    volume: Literal["technical", "business", "all"] = "all"


class ProjectExportRequest(RequestBody):
    check_id: str = Field(min_length=1, max_length=100)
    kind: Literal["internal", "submission", "internal_review"] = "internal"
    volume: Literal["all", "technical", "business"] = "all"


SourceTier = Literal["own", "partner", "reference"]


class LibraryCreate(RequestBody):
    name: str = Field(min_length=1, max_length=200)
    type: LibraryType
    content: str = Field(min_length=1, max_length=100_000)
    valid_until: str | None = Field(default=None, max_length=10)
    status: Literal["pending", "confirmed"] = "pending"
    reason: str = Field(default="", max_length=2000)
    valid_to: str | None = Field(default=None, max_length=10)
    is_long_term: bool = False
    source_tier: SourceTier = "own"
    partner_entity_id: str | None = Field(default=None, max_length=100)
    is_restricted: bool = False
    acl_user_ids: list[str] = Field(default_factory=list, max_length=500)


class LibraryPatch(RequestBody):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    type: LibraryType | None = None
    content: str | None = Field(default=None, min_length=1, max_length=100_000)
    valid_until: str | None = Field(default=None, max_length=10)
    status: Literal["pending", "confirmed", "rejected"] | None = None
    reason: str | None = Field(default=None, max_length=2000,
                               description="实质内容修改后同次重新确认必须填写本次核对依据")
    valid_to: str | None = Field(default=None, max_length=10)
    is_long_term: bool = False
    source_tier: SourceTier = "own"
    partner_entity_id: str | None = Field(default=None, max_length=100)
    is_restricted: bool = False
    acl_user_ids: list[str] = Field(default_factory=list, max_length=500)


class ProjectDetail(ResponseBody):
    id: str
    name: str
    company_id: str
    revision: int
    tender_number: str
    deadline: str
    sensitive: bool


class Source(ResponseBody):
    file_id: str
    page: int
    quote: str


class TenderFile(ResponseBody):
    id: str
    filename: str
    size: int
    sha256: str
    media_type: str
    status: Literal["uploaded", "parsed", "failed"]
    page_count: int
    pagination: str
    warnings: list[str]
    download_url: str


class SourcePage(ResponseBody):
    page: int
    text: str


class FilePreview(ResponseBody):
    file_id: str
    filename: str
    pagination: str
    warnings: list[str]
    pages: list[SourcePage]


class Requirement(ResponseBody):
    id: str
    text: str
    category: str
    volume: Volume
    chapter_id: str | None
    status: ReviewStatus
    response: str
    reason: str
    evidence_ids: list[str]
    source: Source
    references: list[str]
    reference_status: Literal["none", "unresolved", "resolved"]


class Fact(ResponseBody):
    id: str
    key: str
    value: str
    status: Literal["pending", "confirmed", "rejected", "needs_review"]
    reason: str
    source: Source | None
    source_type: str = "parsed"
    sla_var_key: str | None = None
    unit: str = ""
    required: bool = False
    label: str = ""
    variable_token: str | None = None


class ChapterWritingInput(ResponseBody):
    id: str
    fact_ids: list[str]
    writing_points: str
    target_length: int | None
    confirmed_by: str | None = None
    confirmed_by_name: str | None = None
    confirmed_at: str | None = None
    confirmed_input_fingerprint: str | None = None
    is_current: bool = False


class WritingPlan(ResponseBody):
    confirmed_by: str | None
    confirmed_by_name: str | None = None
    confirmed_at: str | None
    chapters: list[ChapterWritingInput]


class ConfirmedWritingInput(ChapterWritingInput):
    confirmed_by: str | None
    confirmed_by_name: str | None
    confirmed_at: str | None


class WritingFact(Fact):
    variable: str


class WritingEvidence(ResponseBody):
    id: str
    name: str
    revision: int
    type: LibraryType
    valid_until: str | None
    status: ReviewStatus
    content: str
    requirement_ids: list[str]
    tag: str = "[证]"


class OmittedInput(ResponseBody):
    kind: str
    id: str
    label: str
    reason: str


class WritingInputSnapshot(ResponseBody):
    scope: Literal["whole_chapter"]
    created_at: str
    input_fingerprint: str
    project: dict[str, Any]
    chapter: dict[str, Any]
    plan: ConfirmedWritingInput
    requirements: list[dict[str, Any]]
    evidence: list[WritingEvidence]
    facts: list[WritingFact]
    omitted_inputs: list[OmittedInput]
    official_content: str
    model_input: str | None = None
    model_instruction: str | None = None
    retrieved_evidence: list[dict[str, Any]] = Field(default_factory=list)


class WritingInputPreview(ResponseBody):
    source_scope: Literal["whole_chapter"]
    input_snapshot: WritingInputSnapshot
    ready: bool
    issues: list[dict[str, Any]]


class Conflict(ResponseBody):
    id: str
    key: str
    fact_ids: list[str]
    selected_fact_id: str | None
    status: Literal["pending", "resolved"]
    reason: str


class Candidate(ResponseBody):
    id: str
    content: str
    base_revision: int
    input_fingerprint: str
    provider: str
    is_real_model: bool
    created_at: str
    source_scope: Literal["whole_chapter"]
    input_snapshot: WritingInputSnapshot
    status: Literal["valid", "stale"] = "valid"


class WorkflowChapter(ChapterSummaryResponse):
    content: str
    lock: LockSummaryResponse | None
    candidate: Candidate | None
    requirement_ids: list[str]
    writing_input: ChapterWritingInput
    assignee_id: str | None
    assignee_name: str | None
    permissions: dict[str, bool]


class ParagraphDetail(ResponseBody):
    id: str
    order: int
    text: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str
    updated_at: str


class ChapterEditDetail(ResponseBody):
    id: str
    project_id: str
    title: str
    chapter_number: str
    outline_type: str
    is_mandatory: bool
    locked_by: str | None = None
    lock_expires_at: str | None = None
    revision: int
    paragraphs: list[ParagraphDetail] = Field(default_factory=list)
    volume: str | None = None
    can_edit: bool | None = None
    permissions: dict[str, bool] | None = None


class TeamMember(TeamMemberInput):
    name: str
    company_role: DemoCompanyRole


class VolumeOwner(VolumeOwnerInput):
    owner_name: str | None


class Handoff(ResponseBody):
    id: str
    actor_id: str
    at: str
    reason: str
    chapter_ids: list[str]
    previous_user_ids: list[str]
    preserved_draft_count: int
    revoked_lock_count: int


class Team(ResponseBody):
    members: list[TeamMember]
    volumes: list[VolumeOwner]
    assembly_owner_id: str | None
    available_accounts: list[AccountResponse]
    handoffs: list[Handoff]


class TeamResult(Team):
    revision: int


class ProjectPermissions(ResponseBody):
    manage_team: bool
    manage_project: bool
    manage_structure: bool
    prepare_sources: bool
    manage_sla: bool
    edit_facts: bool
    confirm_facts: bool
    check_all: bool
    export_internal: bool
    check_volumes: list[Volume]
    export_volumes: list[Volume]


class JobError(ResponseBody):
    code: str
    message: str


class Job(ResponseBody):
    id: str
    project_id: str
    type: str
    status: Literal["completed", "failed"]
    progress: int
    message: str
    created_at: str
    completed_at: str
    error: JobError | None
    recoverable: Literal[False]


JobRunStatus = Literal["queued", "running", "completed", "failed", "cancelled"]


class StartGenerationRequest(RequestBody):
    """启动生成。长任务。If-Match 核对已确认大纲计划的 revision。没有 fingerprint 字段。"""

    chapter_ids: list[Annotated[str, Field(min_length=1)]] | None = Field(default=None, max_length=200)


class StatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    from_status: JobRunStatus = Field(alias="from")
    to: JobRunStatus


class ProgressPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    progress: int = Field(ge=0, le=100)
    message: str


class CompletedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["completed"]
    completed_at: str
    error: None


class FailedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["failed"]
    completed_at: str
    error: str


class CancelledPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["cancelled"]
    completed_at: str
    error: None


class _EventCore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seq: int = Field(ge=1)
    id: str = Field(description="格式为 <job_id>:<seq>。")
    occurred_at: str


class ModelCallEvent(_EventCore):
    type: Literal["job.model_call"]
    provider: str
    model: str
    is_real_model: bool
    is_local: bool
    duration_ms: int = Field(ge=0)
    error_code: str | None


class StatusChangedEvent(_EventCore):
    type: Literal["job.status_changed"]
    payload: StatusChange


class ProgressEvent(_EventCore):
    type: Literal["job.progress"]
    payload: ProgressPayload


class CompletedEvent(_EventCore):
    type: Literal["job.completed"]
    payload: CompletedPayload


class FailedEvent(_EventCore):
    type: Literal["job.failed"]
    payload: FailedPayload


class CancelledEvent(_EventCore):
    type: Literal["job.cancelled"]
    payload: CancelledPayload


JobEvent = Annotated[
    ModelCallEvent | StatusChangedEvent | ProgressEvent | CompletedEvent | FailedEvent | CancelledEvent,
    Field(discriminator="type"),
]


class JobStatus(BaseModel):
    """独立的任务状态，不继承已实现的 Job。由 BE-M0-T06 实现。"""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"x-aligned-with": "BE-M0-T06"}, populate_by_name=True)
    id: str
    project_id: str
    type: str
    status: JobRunStatus
    progress: int = Field(ge=0, le=100)
    message: str
    created_at: str
    completed_at: str | None
    error: JobError | None
    events: list[JobEvent]
    recoverable: bool
    allowed_actions: list[str] | None = None
    allowedActions: list[str] | None = None


class CheckIssue(ResponseBody):
    id: str
    code: str
    severity: Literal["blocking", "warning", "blocker"]
    message: str
    requirement_id: str | None = None
    chapter_id: str | None = None
    evidence_id: str | None = None


class Coverage(ResponseBody):
    implemented_rules: list[str]
    unimplemented_rules: list[str]
    complete: Literal[False]


class ProjectCheck(ResponseBody):
    id: str
    volume: Literal["technical", "business", "all"]
    passed: bool
    status: Literal["passed", "failed", "stale"]
    issues: list[CheckIssue]
    coverage: Coverage
    fingerprint: str
    created_at: str


class ExportVolume(ResponseBody):
    volume: Volume
    filename: str
    download_url: str
    sha256: str | None = None
    format_metadata: dict[str, Any] | None = None


class ProjectExport(ResponseBody):
    id: str
    kind: Literal["internal", "submission", "internal_review"]
    check_id: str
    fingerprint: str
    created_at: str
    excludes_drafts: Literal[True]
    volumes: list[ExportVolume]
    status: Literal["valid", "stale"]
    has_blockers: bool = False
    compliance_notice: str | None = None
    sha256: str | None = None
    format_metadata: dict[str, Any] | None = None
    is_submission: bool = False


class LibraryItem(ResponseBody):
    id: str
    company_id: str
    name: str
    type: LibraryType
    content: str
    valid_until: str | None
    status: ReviewStatus
    revision: int
    usable_as_evidence: bool
    reason: str
    source_tier: SourceTier = "own"
    is_restricted: bool = False
    is_long_term: bool = False
    valid_to: str | None = None
    partner_entity_id: str | None = None


class Workspace(ResponseBody):
    revision: int
    input_fingerprint: str
    project: ProjectDetail
    stage: str
    files: list[TenderFile]
    requirements: list[Requirement]
    facts: list[Fact]
    conflicts: list[Conflict]
    chapters: list[WorkflowChapter]
    checks: list[ProjectCheck]
    exports: list[ProjectExport]
    jobs: list[Job]
    parse_confirmed: bool
    plan_confirmed: bool
    sla: ProjectSla | None = None
    writing_plan: WritingPlan
    team: Team
    permissions: ProjectPermissions


class MutationResult(ResponseBody):
    revision: int
    deleted_file_id: str | None = None
    project: ProjectDetail | None = None
    file: TenderFile | None = None
    job: Job | None = None
    requirement: Requirement | None = None
    fact: Fact | None = None
    conflict: Conflict | None = None
    requirements: list[Requirement] | None = None
    facts: list[Fact] | None = None
    conflicts: list[Conflict] | None = None
    chapters: list[WorkflowChapter] | None = None
    check: ProjectCheck | None = None
    export: ProjectExport | None = None
    parse_confirmed: bool | None = None
    plan_confirmed: bool | None = None
    writing_plan: WritingPlan | None = None
    team: Team | None = None
    chapter: WorkflowChapter | None = None


class CheckList(ResponseBody):
    revision: int
    checks: list[ProjectCheck]


class JobsList(ResponseBody):
    jobs: list[Job]


class LibraryList(ResponseBody):
    revision: int
    items: list[LibraryItem]


class LibraryResult(ResponseBody):
    revision: int
    item: LibraryItem


SnippetSyncStatus = Literal["unsynced", "synced", "failed", "blocked"]
SnippetBlockCode = Literal[
    "real_report", "hardcoded_promise", "unknown_variable", "unpublished_body", "cross_company_reference"]


class SnippetPublicationCreate(RequestBody):
    product: str = Field(min_length=1, max_length=200)
    snippet_type: str = Field(min_length=1, max_length=200)
    variables: list[str] = Field(default_factory=list, max_length=100)
    source_group: str = Field(default="", max_length=200)
    boilerplate_group: str = Field(default="", max_length=200)
    draft_body: str = Field(default="", max_length=100_000)

    @field_validator("variables")
    @classmethod
    def variable_names(cls, values):
        if any(not value.strip() or len(value) > 80 or "{{" in value or "}}" in value for value in values):
            raise ValueError("变量名必须完整、不超过80字，且不能再包含变量括号")
        return values


class SnippetPublicationDraft(RequestBody):
    product: str | None = Field(default=None, min_length=1, max_length=200)
    snippet_type: str | None = Field(default=None, min_length=1, max_length=200)
    variables: list[str] | None = Field(default=None, max_length=100)
    source_group: str | None = Field(default=None, max_length=200)
    boilerplate_group: str | None = Field(default=None, max_length=200)
    draft_body: str | None = Field(default=None, max_length=100_000)

    @field_validator("variables")
    @classmethod
    def variable_names(cls, values):
        if values is not None and any(
                not value.strip() or len(value) > 80 or "{{" in value or "}}" in value for value in values):
            raise ValueError("变量名必须完整、不超过80字，且不能再包含变量括号")
        return values


class SnippetPublication(ResponseBody):
    id: str
    company_id: str
    product: str
    snippet_type: str
    variables: list[str]
    source_group: str
    boilerplate_group: str
    draft_body: str
    published_body: str
    draft_revision: int
    published_revision: int
    kb_sync_status: SnippetSyncStatus
    updated_at: str


class SnippetPublicationList(ResponseBody):
    items: list[SnippetPublication]


class SnippetBlockReason(ResponseBody):
    code: SnippetBlockCode
    message: str


class SnippetPublishResult(ResponseBody):
    item: SnippetPublication
    blocked: bool
    reasons: list[SnippetBlockReason]


class SnippetSyncResult(ResponseBody):
    item: SnippetPublication
    synced: bool


class SnippetMatchRequest(RequestBody):
    chapter_id: str | None = Field(default=None, description="可选关联合同章节 ID")
    chapter_title: str | None = Field(default=None, description="可选章节标题")
    scoring_points: list[str] = Field(default_factory=list, description="评分项要点或条款要求")
    query: str = Field(default="", description="检索补充查询词或上下文提示词")
    limit: int = Field(default=5, ge=1, le=20, description="最大召回数量")
    min_score: float = Field(default=0.05, ge=0.0, le=1.0, description="最低匹配相关度得分")
    model_config_id: str | None = Field(default=None, description="指定模型配置 ID，涉密项目校验")


class SnippetMatchItem(ResponseBody):
    snippet_id: str
    company_id: str
    product: str
    snippet_type: str
    source_group: str
    boilerplate_group: str
    published_revision: int
    original_body: str
    rendered_body: str
    variables: list[str]
    matched_variables: dict[str, str]
    missing_variables: list[str]
    score: float
    cite_tag: str
    citation_clause: str
    fingerprint: str
    cite_metadata: dict[str, Any]


class SnippetMatchResponse(ResponseBody):
    project_id: str
    chapter_id: str | None
    company_id: str
    total_matched: int
    items: list[SnippetMatchItem]
    extracted_fact_count: int
    has_missing_variables: bool


class V1Error(ResponseBody):
    code: str = Field(description="已冻结错误码；每个 code 只对应一个 HTTP 状态，见 OpenAPI components.x-error-status")
    message: str = Field(description="给用户阅读的中文说明")
    details: dict[str, Any] = Field(description="补充数据。current_revision 表示版本冲突时的当前版本；job_id 与 revision 表示失败任务；fields 是校验失败的字段位置；issues 是成组阻断项")
    traceId: str = Field(description="32 位十六进制请求编号，与响应头 X-Request-ID 相同；由服务端生成，不接受客户端传入")


def v1_error_responses(*statuses: int) -> dict:
    from .errors import STATUS_MEANING
    return {status: {"model": V1Error, "description": (
        f"{STATUS_MEANING[status]}。响应体为 code、message、details、traceId，traceId 与响应头 X-Request-ID 相同。"
        "code 与 HTTP 状态的唯一对应见 components.x-error-status。")}
        for status in statuses}


class TenderSearchRequest(RequestBody):
    query: str = Field(min_length=1, max_length=1000)
    enabled: bool | None = None
    top_k: int = Field(default=10, ge=1, le=50)
    clause_type: str | None = Field(default=None, max_length=50)


class TenderIndexingSwitchRequest(RequestBody):
    enabled: bool


class InjectTenderClausesRequest(RequestBody):
    slice_ids: list[str] | None = None
    slices: list[dict[str, Any]] | None = None


class AcceptAiSuggestionRequest(RequestBody):
    lease_token: str = Field(min_length=1, max_length=128, description="当前会话持有的独占编辑租约锁 Token")
    base_revision: int = Field(ge=1, description="客户端当前章节的版本号基准")
    suggested_text: str = Field(min_length=1, max_length=50_000, description="采纳并写入正文的 AI 润色建议改写内容")
    paragraph_id: str | None = Field(default=None, max_length=128, description="目标被润色/替换的段落编号，如 alpha-tech-p1")
    original_text: str | None = Field(default=None, max_length=50_000, description="被改写的段落/片段原文快照，用于一致性比对校验")
    citations: list[dict[str, Any]] | None = Field(default=None, description="本次润色建议所依据的公司证据或招标文件切片溯源引用")
    input_fingerprint: str | None = Field(default=None, max_length=128, description="输入上下文快照指纹")


class AcceptAiSuggestionResponse(ResponseBody):
    chapter_id: str
    project_id: str
    revision: int
    content: str
    paragraph_id: str | None = None
    updated_paragraph: dict[str, Any] | None = None
    paragraphs: list[dict[str, Any]]
    version_entry: dict[str, Any]
    incremental_check_status: str
    message: str


class ComplianceFinding(ResponseBody):
    finding_id: str
    paragraph_id: str
    claim_type: str = Field(description="声明类型：sla_metric、qualification、personnel、case_experience、general_promise")
    claim_text: str
    cited_evidence_id: str | None = None
    evidence_status: str = Field(default="valid", description="证据状态：valid、pending_verification、expired、missing_agreement、missing、cross_company")
    tender_clause_id: str | None = None
    document_id: str | None = Field(default=None, description="RAGFlow 原始文档 ID 或知识库来源文档 ID")
    chunk_id: str | None = Field(default=None, description="RAGFlow 原始分块 ID")
    is_discrepancy: bool = Field(default=False, description="是否判定为合规依据差距/异常项")
    discrepancy_type: str | None = Field(default=None, description="差距类型：cross_check_discrepancy 等")
    confidence_score: float = Field(ge=0.0, le=1.0, description="依据置信度得分 0.0 ~ 1.0")
    confidence_level: str = Field(description="置信度等级：high、medium、low、unsupported")
    risk_level: str = Field(description="风险等级：block（阻断）、warning（警告）、info（提示）")
    gap_description: str = Field(description="依据与声明差距诊断分析描述")
    suggestion: str = Field(description="针对性改进建议")


class ComplianceCrossCheckRequest(RequestBody):
    chapter_id: str | None = None
    model_config_id: str | None = None
    strict_mode: bool = True


class ComplianceCrossCheckResponse(ResponseBody):
    chapter_id: str
    project_id: str
    overall_confidence: float = Field(ge=0.0, le=1.0)
    compliance_status: str = Field(description="合规状态：compliant、warning、non_compliant")
    total_claims: int
    verified_claims: int
    warning_claims: int
    unsupported_claims: int
    discrepancy_count: int = Field(default=0, description="依据差距与异常项计数")
    findings: list[ComplianceFinding]
    checks_summary: dict[str, Any] = Field(default_factory=dict)
    checked_at: str
    message: str = "合规依据交叉核验与差距诊断完成"


