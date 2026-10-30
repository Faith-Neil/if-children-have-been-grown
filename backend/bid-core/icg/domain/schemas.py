# 为什么有这个文件：定义浏览器和后端共同使用的请求、成功结果与错误字段。
# 它解决什么问题：拒绝不合法请求，并让接口说明明确列出实际返回内容，避免接入时猜字段。

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    @field_validator("*", mode="after", check_fields=False)
    @classmethod
    def valid_xml_text(cls, value):
        # Word 内部使用 XML，控制字符及孤立代理字符会破坏实际文件。
        if isinstance(value, str):
            for character in value:
                number = ord(character)
                if not (number in (9, 10, 13) or 32 <= number <= 0xD7FF
                        or 0xE000 <= number <= 0xFFFD or 0x10000 <= number <= 0x10FFFF):
                    raise ValueError("文字含有不能写入 Word 的字符")
        return value


class LoginRequest(RequestBody):
    account_id: str = Field(min_length=1, max_length=80)


class UsernamePasswordLoginRequest(RequestBody):
    username: str = Field(min_length=1, max_length=100, description="登录用户名")
    password: str = Field(min_length=1, max_length=128, description="登录密码")


class ProjectRequest(RequestBody):
    name: str = Field(min_length=1, max_length=200)
    volume_mode: Literal["both", "technical_only"] = Field(
        default="both", description="both：技术与商务两册，导出后合标；technical_only：只写技术标，不合标")

    @field_validator("name")
    @classmethod
    def non_blank_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("项目名称不能为空")
        return value


class LockRequest(RequestBody):
    takeover_reason: str | None = Field(default=None, max_length=1000)


class LeaseRequest(RequestBody):
    lease_token: str = Field(min_length=1, max_length=200)


class DraftRequest(LeaseRequest):
    base_revision: int = Field(ge=1)
    sequence: int = Field(ge=1)
    content: str = Field(max_length=100_000)
    input_fingerprint: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$",
                                          description="编辑内容所依据的项目输入指纹；有条款、事实或服务承诺的项目必须提供，来源变化后不能静默刷新")


class DraftDiscardRequest(RequestBody):
    sequence: int = Field(ge=1)


class VersionRequest(LeaseRequest):
    base_revision: int = Field(ge=1)
    content: str = Field(max_length=100_000)
    idempotency_key: str = Field(min_length=1, max_length=120)
    input_fingerprint: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$",
                                          description="本次提交实际核对的项目输入指纹；在同一写事务内验证，旧候选或旧草稿不能绕过")

    @field_validator("idempotency_key")
    @classmethod
    def non_blank_key(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("重复请求标记不能为空")
        return value


class SuggestionRequest(RequestBody):
    instruction: str = Field(min_length=1, max_length=2000)

    @field_validator("instruction")
    @classmethod
    def non_blank_instruction(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("修改要求不能为空")
        return value


class EmptyRequest(RequestBody):
    pass


class ExportRequest(RequestBody):
    check_id: str = Field(min_length=1, max_length=100)


class ResponseBody(BaseModel):
    # 已知字段明确声明；额外元数据继续保留，避免响应校验悄悄删掉实际必要信息。
    # 添加正式字段时仍须在这里声明，不能用额外字段替代接口约定维护。
    model_config = ConfigDict(extra="allow", strict=True)


DemoCompanyRole = Literal["editor", "manager", "viewer", "readonly", "reviewer", "auditor",
                          "company_admin", "data_admin", "project_lead", "bid_writer",
                          "platform_admin", "group_admin"]


class AccountResponse(ResponseBody):
    id: str
    name: str
    company_id: str
    role: DemoCompanyRole
    username: str | None = None
    display_name: str | None = None


class AccountListResponse(ResponseBody):
    accounts: list[AccountResponse]


class LoginResponse(ResponseBody):
    access_token: str
    token_type: Literal["bearer"]
    user: AccountResponse


ApplicationRole = Literal["platform_admin", "group_admin", "company_admin", "data_admin",
                          "project_lead", "bid_writer", "reviewer", "readonly", "auditor", "viewer"]


class SessionUserResponse(AccountResponse):
    roles: list[ApplicationRole]
    primary_role: ApplicationRole


class SessionScopeResponse(ResponseBody):
    kind: Literal["company", "system"]
    active_company_id: str
    allowed_company_ids: list[str]


class SessionNavigationResponse(ResponseBody):
    route_id: str
    path: str
    access: Literal["read", "write"]


class SessionStateResponse(ResponseBody):
    expires_at: str | None
    renew_supported: Literal[False]


class SessionProjectPermissions(ResponseBody):
    manage_team: bool
    manage_project: bool
    manage_structure: bool
    prepare_sources: bool
    manage_sla: bool
    edit_facts: bool
    confirm_facts: bool
    check_all: bool
    export_internal: bool
    check_volumes: list[Literal["technical", "business"]]
    export_volumes: list[Literal["technical", "business"]]


class SessionChapterPermissions(ResponseBody):
    edit: bool
    confirm_plan: bool
    generate: bool
    manage_structure: bool
    assign: bool
    takeover: bool


class SessionChapterAccess(ResponseBody):
    id: str
    volume: Literal["technical", "business"]
    permissions: SessionChapterPermissions


class SessionProjectAccess(ResponseBody):
    id: str
    revision: int
    route_permissions: list[str]
    permissions: SessionProjectPermissions
    chapters: list[SessionChapterAccess]


class ApplicationSessionResponse(ResponseBody):
    auth_mode: Literal["synthetic-demo", "authenticated"]
    role_mode: Literal["legacy-demo-compat", "rbac-8roles"]
    user: SessionUserResponse
    scope: SessionScopeResponse
    navigation: list[SessionNavigationResponse]
    allowedActions: list[str]
    home_path: str
    session: SessionStateResponse
    project_access: SessionProjectAccess | None = None


class ProjectResponse(ResponseBody):
    id: str
    name: str
    company_id: str
    revision: int = 1
    tender_number: str = ""
    deadline: str = ""
    sensitive: bool = False
    tender_type: str = "comprehensive"
    budget_amount_cents: int | None = None
    deadline_at: str | None = None
    security_level: str = "internal"
    industry: str = "it"
    is_archived: bool = False
    created_by: str | None = None
    created_at: str | None = None
    updated_by: str | None = None
    updated_at: str | None = None
    record_version: int = 1
    is_deleted: bool = False
    volume_mode: Literal["both", "technical_only"] = "both"


class ProjectListResponse(ResponseBody):
    projects: list[ProjectResponse]


class ChapterSummaryResponse(ResponseBody):
    id: str
    title: str
    volume: Literal["technical", "business"]
    revision: int = Field(ge=1)


class ChapterListResponse(ResponseBody):
    chapters: list[ChapterSummaryResponse]


class LockSummaryResponse(ResponseBody):
    owner_id: str
    owner_name: str | None = Field(default=None, description="持锁人姓名，供其他成员看到“某某正在编辑”")
    # 只给文档增加日期格式提示，保留实际返回字符串的原写法。
    expires_at: str = Field(description="UTC 的 ISO 8601 到期时间",
                            json_schema_extra={"format": "date-time"})


class LeaseResponse(LockSummaryResponse):
    lease_token: str = Field(description="只供本次登录会话使用的编辑凭据")


class DraftResponse(ResponseBody):
    sequence: int = Field(ge=1)
    content: str
    base_revision: int = Field(ge=1)
    input_fingerprint: str | None = Field(default=None, description="草稿最初保存时核对的输入指纹，读取或恢复草稿不会自动改为当前来源")


class ParagraphKeyResponse(ResponseBody):
    key: str = Field(description="段落键：跨版本不变；改了几个字仍沿用，新增的块才拿新键")
    kind: Literal["heading", "para", "bullet", "ordered", "table"]
    level: int = Field(ge=0, description="标题级别（1～8），其他块为 0")
    line_start: int = Field(ge=0, description="本块在正文中的起始行（0 起）")
    line_end: int = Field(ge=0, description="本块在正文中的结束行（含）")
    hash: str
    source: Literal["manual", "assistant", "assistant_pasted", "chapter_loop", "system"]
    source_label: str
    locked: bool = Field(default=False, description="段落已锁定（APP-M2-T163）：任何写入都不能改动或删除")
    locked_by_name: str | None = Field(default=None, description="锁定人")


class ChapterResponse(ChapterSummaryResponse):
    project_id: str
    content: str = Field(description="已提交的当前正式正文，不包含草稿")
    lock: LockSummaryResponse | None = Field(description="有效编辑权的摘要，不含租约凭据")
    draft: DraftResponse | None = Field(description="当前登录人自己的草稿；没有则为 null")
    paragraphs: list[ParagraphKeyResponse] = Field(default_factory=list, description="当前正文逐块的段落键与来源（APP-M2-T161）")
    assignee_id: str | None
    permissions: dict[str, bool] = Field(description="按当前公司角色、项目成员与本册/本节分工实时核对的操作权限")


class DraftDiscardResponse(ResponseBody):
    discarded: bool


class ReleasedResponse(ResponseBody):
    released: Literal[True]


class VersionResponse(ResponseBody):
    revision: int = Field(ge=1)
    content: str
    paste_detected: list[dict] | None = Field(default=None, description="与近期对话助手输出高度重合的新段落（粘贴识别）：段落序号、重合比例、来源与复查问题")


class VersionRecordResponse(VersionResponse):
    actor_id: str
    paragraphs: list[ParagraphKeyResponse] = Field(default_factory=list, description="本版本逐块的段落键与来源")
    version_origin: str | None = Field(default=None, description="写入方式：manual / assistant_edit / ai_polish_accepted / rollback；章节循环与系统生成见 source")
    edit_mode: str | None = Field(default=None, description="修改方式明细，如 assistant_replace、assistant_insert、rollback")
    source: str | None = Field(default=None, description="chapter_loop / system_generated")
    rollback_from: int | None = Field(default=None, description="版本回退时回退到的历史版本号")
    note: str | None = None
    created_at: str = Field(description="UTC 的 ISO 8601 创建时间",
                            json_schema_extra={"format": "date-time"})


class VersionListResponse(ResponseBody):
    versions: list[VersionRecordResponse]


class AuditEventResponse(ResponseBody):
    id: str
    action: str = Field(description="实际业务动作，如 lock.takeover、version.commit、export.create")
    actor_id: str
    chapter_id: str
    revision: int = Field(ge=1)
    at: str = Field(description="UTC 的 ISO 8601 操作时间",
                    json_schema_extra={"format": "date-time"})
    details: dict[str, Any] = Field(description="动作附加信息；如接管理由 reason、检查 check_id、输出 export_id")


class AuditListResponse(ResponseBody):
    events: list[AuditEventResponse]


class SuggestionResponse(ResponseBody):
    content: str
    base_revision: int = Field(ge=1)
    provider: str
    is_real_model: bool
    input_fingerprint: str = Field(description="包含正文、项目事实、矩阵和证据的输入指纹")
    source_scope: Literal["whole_chapter"] | None = Field(default=None, description="整章输入范围，不能代表逐段溯源")
    input_snapshot: dict[str, Any] | None = Field(default=None, description="实际送入模型的整章来源与文字快照；独立旧demo为空")


class CheckIssueResponse(ResponseBody):
    code: str
    message: str


class CheckResponse(ResponseBody):
    id: str
    passed: bool
    revision: int = Field(ge=1)
    issues: list[CheckIssueResponse]


class ExportResponse(ResponseBody):
    id: str
    filename: str
    download_url: str = Field(description="同源相对路径；下载时仍须带 Bearer 登录凭据")
    excludes_drafts: Literal[True] = Field(description="文件只含已提交正文，始终排除未提交草稿")
    check_id: str = Field(description="导出当时绑定的检查")
    revision: int = Field(ge=1, description="导出当时的已提交版本")
    content_hash: str = Field(description="导出当时的已提交正文摘要")
    input_fingerprint: str = Field(description="导出当时的项目输入摘要")


class HealthResponse(ResponseBody):
    status: str
    mode: str
    repository: str
    model: str
    persistent: bool
    single_process: bool


class ErrorDetailResponse(ResponseBody):
    code: str
    message: str


class ErrorResponse(ResponseBody):
    error: ErrorDetailResponse
    request_id: str = Field(description="与响应头 X-Request-ID 相同的请求编号")
