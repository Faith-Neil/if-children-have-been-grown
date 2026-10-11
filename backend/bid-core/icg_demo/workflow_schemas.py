# 为什么有这个文件：给示例主流程提供可生成接口契约的业务字段。
# 它解决什么问题：前后端使用真实且明确的数据结构，不靠猜字段或空响应接通页面。

from typing import Any, Literal

from pydantic import Field, field_validator

from .schemas import ChapterSummaryResponse, RequestBody, ResponseBody, LockSummaryResponse, AccountResponse
from .sla_schemas import ProjectSla

Volume = Literal["technical", "business"]
ReviewStatus = Literal["pending", "confirmed", "rejected"]
LibraryType = Literal["qualification", "personnel", "performance", "sla", "snippet", "history"]


class ProjectPatch(RequestBody):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    tender_number: str | None = Field(default=None, max_length=100)
    deadline: str | None = Field(default=None, max_length=50)
    sensitive: bool | None = None


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
    kind: Literal["internal", "submission"] = "internal"
    volume: Literal["all", "technical", "business"] = "all"


class LibraryCreate(RequestBody):
    name: str = Field(min_length=1, max_length=200)
    type: LibraryType
    content: str = Field(min_length=1, max_length=100_000)
    valid_until: str | None = Field(default=None, max_length=10)
    status: Literal["pending", "confirmed"] = "pending"
    reason: str = Field(default="", max_length=2000)


class LibraryPatch(RequestBody):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    type: LibraryType | None = None
    content: str | None = Field(default=None, min_length=1, max_length=100_000)
    valid_until: str | None = Field(default=None, max_length=10)
    status: Literal["pending", "confirmed", "rejected"] | None = None
    reason: str | None = Field(default=None, max_length=2000,
                               description="实质内容修改后同次重新确认必须填写本次核对依据")


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


class TeamMember(TeamMemberInput):
    name: str
    company_role: Literal["editor", "manager", "viewer"]


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


class CheckIssue(ResponseBody):
    id: str
    code: str
    severity: Literal["blocking", "warning"]
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


class ProjectExport(ResponseBody):
    id: str
    kind: Literal["internal", "submission"]
    check_id: str
    fingerprint: str
    created_at: str
    excludes_drafts: Literal[True]
    volumes: list[ExportVolume]
    status: Literal["valid", "stale"]


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


class V1Error(ResponseBody):
    code: str
    message: str
    details: dict[str, Any]
    traceId: str
