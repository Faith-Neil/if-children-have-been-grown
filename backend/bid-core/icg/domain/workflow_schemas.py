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
    volume_mode: Literal["both", "technical_only"] | None = Field(
        default=None, description="切换为只写技术标须商务分册尚无正文且未定稿；切回两册时补建商务分册")
    related_bid_reason: str | None = Field(
        default=None, max_length=2000,
        description="R19：集团内其他公司已对同一标段立项时，项目负责人确认无控股、管理关系或单位负责人相同的说明（至少 5 个字）；"
                    "有冲突而未填写时返回 409 RELATED_BID_CONFLICT，details 只含对方公司名称")


class RelatedBidAck(RequestBody):
    reason: str = Field(min_length=5, max_length=2000, description="确认无控股、管理关系或单位负责人相同的说明")


class RelatedBidStatus(ResponseBody):
    match: Literal["exact", "approximate"] | None = Field(description="exact：同招标编号同标段；approximate：编号或标段缺失时近似判断")
    companies: list[str] = Field(description="对方公司名称；不含对方项目任何内容")
    message: str
    statute: str
    needs_ack: bool
    acknowledged: dict | None = Field(description="已确认的说明：company_names、match、reason、by_name、at")


class FileUpload(RequestBody):
    filename: str = Field(min_length=1, max_length=180)
    content_base64: str = Field(min_length=1, description="base64 原件；大文件请用 /files/raw 直接上传二进制")


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
    response_type: Literal["comply", "exceed", "deviate", "not_applicable"] | None = Field(
        default=None, description="响应方式：满足=无偏离、优于=正偏离、偏离=负偏离、不适用；星号/废标条款不能偏离或不适用")
    assignee_id: str | None = Field(default=None, max_length=80, description="本行负责人（须为本项目可编写成员）")
    shared_chapter_id: str | None = Field(default=None, max_length=80,
                                          description="跨分册共用行在另一分册对应的章节（只限项目负责人；行须已标跨分册共用）")


class MatrixMatchRequest(RequestBody):
    requirement_ids: list[str] = Field(min_length=1, max_length=50)


class MatrixRoutingRow(RequestBody):
    id: str = Field(min_length=1, max_length=80)
    volume: Volume | None = None
    is_cross_volume: bool = False


class MatrixRoutingRequest(RequestBody):
    rows: list[MatrixRoutingRow] = Field(min_length=1, max_length=500)


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
    volumes: list[VolumeOwnerInput] = Field(min_length=1, max_length=2)
    assembly_owner_id: str | None
    reason: str = Field(default="", max_length=2000)


class ChapterAssignment(RequestBody):
    assignee_id: str | None
    reason: str = Field(default="", max_length=2000)


class GenerateRequest(RequestBody):
    chapter_ids: list[str] | None = None


class ProjectCheckRequest(RequestBody):
    volume: Literal["technical", "business", "all"] = "all"


class CheckReleaseRequest(RequestBody):
    reason: str = Field(min_length=1, max_length=500, description="放行理由（必填）")
    decision: Literal["keep", "accept"] = Field(default="keep", description="keep：确认保留（如额外数值承诺）；accept：确认无需修改")


class ProposedStaffEntry(RequestBody):
    id: str | None = Field(default=None, max_length=120)
    person_id: str = Field(min_length=1, max_length=120, description="资料库“人员”类资料 ID")
    role: str = Field(min_length=1, max_length=40, description="项目角色，如项目经理、技术负责人、驻场工程师")
    position: Literal["A", "B"] | None = Field(default=None, description="AB 角")
    is_key_person: bool = False


class ProposedStaffUpdate(RequestBody):
    staff: list[ProposedStaffEntry] = Field(max_length=100)


class ExportSettingsUpdate(RequestBody):
    internal_template: str | None = Field(default=None, max_length=200, description="内部稿命名模板；空为“{编写人}_{版本}_{日期}_{项目名称}”")
    submit_rule: str | None = Field(default=None, max_length=200, description="递交版命名规则；不得含 {编写人}；空为“{项目名称}_{分册名称}”")


class NamingVariable(ResponseBody):
    name: str
    description: str


class ExportSettings(ResponseBody):
    revision: int | None = None
    internal_template: str
    submit_rule: str
    updated_by: str | None = None
    updated_at: str | None = None
    variables: list[NamingVariable]


class ProjectExportRequest(RequestBody):
    check_id: str = Field(min_length=1, max_length=100)
    kind: Literal["internal", "submission", "internal_review"] = "internal"
    volume: Literal["all", "technical", "business"] = "all"
    template: Literal["auto", "company", "platform"] = Field(
        default="auto", description="Word 模板：auto 有公司模板用公司模板，否则平台默认；company 必须用公司模板；platform 平台默认")
    insert_attachments: bool = Field(default=True, description="是否插入条款挂接资料的附件扫描件")
    attachment_watermark: str | None = Field(default=None, max_length=60,
                                             description="敏感附件水印文字；不填为“仅用于{项目名称}投标”")


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
    submitted_on: str | None = Field(default=None, max_length=10, description="历史标书递交日期 YYYY-MM-DD（R29 比对年限）")


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
    submitted_on: str | None = Field(default=None, max_length=10, description="历史标书递交日期 YYYY-MM-DD（R29 比对年限）")


class ProjectDetail(ResponseBody):
    id: str
    name: str
    company_id: str
    revision: int
    tender_number: str
    deadline: str
    sensitive: bool
    volume_mode: Literal["both", "technical_only"] = "both"


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
    status: Literal["uploaded", "parsed", "failed", "parsing_remote"]
    page_count: int
    pagination: str
    warnings: list[str]
    download_url: str


class TextRegion(ResponseBody):
    """扫描件识别出的一段文字及其在原件页面上的位置框 [x0, x1, top, bottom]（PDF 点，左上角为原点）。"""
    text: str
    boxes: list[list[float]]


class SourcePage(ResponseBody):
    page: int
    text: str
    regions: list[TextRegion] = Field(default_factory=list)


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
    manually_edited: bool = Field(default=False, description="人工改过原文；重新抽取时不覆盖")
    confidence: float | None = Field(default=None, description="0～1；低于公司阈值（默认 0.8）在解析页高亮；扫描件识别的条目最高 0.9")
    unreadable: bool = Field(default=False, description="原文不可读（识别乱码）：须对照原页补录文字后才能确认")
    unreadable_reason: str = ""


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


class ReviewedFact(Fact):
    """项目事实表与解析核对用：带解析置信度与补录标记（生成输入快照不含这些字段）。"""
    confidence: float | None = Field(default=None, description="0～1；低于公司阈值（默认 0.8）在解析页高亮")
    unreadable: bool = Field(default=False, description="原文不可读：须对照原页补录取值后才能确认")
    unreadable_reason: str = ""
    manually_edited: bool = False


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
    volume_mode: Literal["both", "technical_only"] = "both"
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
    status: str
    progress: int = 0
    message: str = ""
    created_at: str = ""
    completed_at: str | None = None
    error: JobError | None = None
    recoverable: Literal[False] = False
    duration_ms: int | None = None
    company_id: str | None = None
    masked_company: str | None = None
    summary: str | None = None
    masked_summary: str | None = None
    is_masked: bool | None = None
    error_code: str | None = None
    allowed_actions: list[str] | None = None
    allowedActions: list[str] | None = None


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
    batch_no: str | None = Field(default=None, description="导出批次号；同一次导出的各分册文件同号")
    docx_sha256: str | None = Field(default=None, description="导出时生成的 Word 快照文件摘要；过期后下载仍是这份文件")
    size_bytes: int | None = None
    template: dict[str, Any] | None = Field(default=None, description="本册所用 Word 模板：source=company/platform、filename、sha256")
    format_overrides: list[dict[str, Any]] | None = Field(default=None, description="按招标格式要求覆盖模板的项：项目、取值、依据原文、条款 ID")
    attachments: list[dict[str, Any]] | None = Field(default=None, description="插入本册的附件扫描件：资料名、文件名、页码范围、是否加水印")
    skipped_attachments: list[dict[str, Any]] | None = Field(default=None, description="未插入的附件与原因（如暗标分册不插带公司标识的附件）")


class BoundVolume(ResponseBody):
    is_finalized: bool
    finalized_by: str | None = None
    finalized_at: str | None = None
    snapshot_sha256: str | None = None


class ProjectExport(ResponseBody):
    id: str
    kind: Literal["internal", "submission", "internal_review"]
    check_id: str
    fingerprint: str
    created_at: str
    excludes_drafts: Literal[True]
    volumes: list[ExportVolume]
    status: Literal["valid", "stale", "failed"] = Field(
        description="valid 有效；stale 内容已改动或分册解锁（快照仍可下载）；failed 有分册生成失败，整批作废、无可下载文件")
    batch_no: str | None = Field(default=None, description="批次号：S（递交版）/ I（内部稿）+ 日期 + 当日序号")
    export_status: Literal["completed", "failed"] | None = None
    error_message: str | None = None
    failed_volume: Volume | None = None
    volume: Literal["technical", "business", "all"] | None = None
    created_by: str | None = None
    bound_volumes: dict[str, BoundVolume] | None = Field(default=None, description="本批次绑定的分册定稿记录")
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
    submitted_on: str | None = None


class Workspace(ResponseBody):
    revision: int
    input_fingerprint: str
    project: ProjectDetail
    stage: str
    files: list[TenderFile]
    requirements: list[Requirement]
    facts: list[ReviewedFact]
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
    human_queue_pending: int = Field(default=0, description="人工处理队列中待处理的问题数")
    omissions_pending: int = Field(default=0, description="兜底扫描中尚未处理的疑似遗漏数")


class StaffProfile(ResponseBody):
    degree: str | None = None
    major: str | None = None
    work_start: str | None = Field(default=None, description="参加工作年月（YYYY-MM-01）")
    years: int | None = None
    certificates: list[str] | None = Field(default=None, description="None 表示人员资料里没有证书信息")


class ProposedStaff(ResponseBody):
    id: str
    person_id: str
    person_name: str
    role: str
    position: Literal["A", "B"] | None = None
    is_key_person: bool = False
    profile: StaffProfile | None = Field(default=None, description="从人员资料正文读出的学历、专业、参加工作时间与证书")


class ProposedStaffResult(ResponseBody):
    revision: int | None = None
    staff: list[ProposedStaff]
    roles: list[str]
    r33: dict[str, Any] = Field(description="按当前拟派人员运行的 R33 结果（排人时即提示）")


class MutationResult(ResponseBody):
    revision: int
    deleted_file_id: str | None = None
    project: ProjectDetail | None = None
    file: TenderFile | None = None
    job: Job | None = None
    requirement: Requirement | None = None
    fact: ReviewedFact | None = None
    conflict: Conflict | None = None
    requirements: list[Requirement] | None = None
    facts: list[ReviewedFact] | None = None
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


class BatchGenerateChaptersRequest(RequestBody):
    chapter_ids: list[str] = Field(min_length=1, max_length=100)
    sync_execute: bool = False
    max_context_tokens: int | None = None
    snippet_matches_by_chapter: dict[str, list[dict[str, Any]]] | None = None




class MergeChecklistRow(ResponseBody):
    text: str
    source: str | None = None
    status: str | None = None


class MergeChecklistSection(ResponseBody):
    no: int
    item: str
    action: str
    rows: list[MergeChecklistRow]


class MergeChecklist(ResponseBody):
    export_id: str
    check_id: str | None = None
    project_name: str
    generated_at: str
    volumes: list[str]
    sections: list[MergeChecklistSection]


class MergeChecklistResponse(ResponseBody):
    checklist: MergeChecklist
    stale: bool


class BatchConfirmRequest(RequestBody):
    requirement_ids: list[str] = Field(min_length=1, max_length=500)


class ParseGate(ResponseBody):
    code: str
    label: str
    count: int
    blocking: bool = Field(description="false：只提示，不阻断确认")
    ok: bool


class ParseScoringGroup(ResponseBody):
    name: str
    score: float | None = None
    ids: list[str]
    pending: int


class ParseCategory(ResponseBody):
    no: int
    key: str
    label: str
    requirements: int
    facts: int
    total: int
    pending: int
    batch_allowed: bool = Field(description="星号、废标、资格三类为 false：必须逐条确认")
    groups: list[ParseScoringGroup] | None = Field(default=None, description="评分类：评分项及其得分要点")


class ParseReview(ResponseBody):
    categories: list[ParseCategory]
    requirement_categories: dict[str, str]
    fact_categories: dict[str, str]
    gates: list[ParseGate]
    can_confirm: bool
    parse_confirmed: bool
    confidence_threshold: float = Field(default=0.8, description="低于此置信度的条目高亮（公司设置 parse_confidence_threshold）")
