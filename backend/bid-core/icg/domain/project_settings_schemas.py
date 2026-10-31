# 为什么有这个文件：项目状态与项目设置各组的请求、响应契约（PRD v1.8 §4.3、§5.1.3、§5.1.4；APP-M2-T097～T100）。
# 它解决什么问题：workflow_schemas.py 已很长，新设置组的字段集中放在这里，由 openapi 导出给前端。

from typing import Any, Literal

from pydantic import Field

from .schemas import RequestBody, ResponseBody

Volume = Literal["technical", "business"]


class ProjectBasicInfo(RequestBody):
    tenderee_name: str | None = Field(default=None, max_length=200, description="招标人")
    agency_name: str | None = Field(default=None, max_length=200, description="代理机构")
    lot_name: str | None = Field(default=None, max_length=200, description="标段")
    client_address: str | None = Field(default=None, max_length=50, description="对招标人称呼，如“贵行”")
    open_at: str | None = Field(default=None, max_length=50, description="开标时间")
    service_period: str | None = Field(default=None, max_length=100, description="服务期")
    project_location: str | None = Field(default=None, max_length=200, description="项目地点")


class ProjectStatusRequest(RequestBody):
    action: Literal["submit", "open", "result", "cancel"] = Field(
        description="submit 登记递交（须已有成功导出的递交版）；open 登记开标；result 登记结果；cancel 取消（仅递交前，不可撤销，取消后只读）")
    reason: str = Field(default="", max_length=2000, description="取消时必填")
    result: Literal["won", "lost", "void", "failed_tender"] | None = Field(default=None, description="登记结果时必填：中标 / 未中标 / 废标 / 流标")


class ProjectStatusInfo(ResponseBody):
    status: str
    label: str
    read_only: bool
    registered: bool = Field(description="false 表示由工作台阶段推出，true 表示负责人已登记")
    result: str | None = None
    result_label: str | None = None
    history: list[dict[str, Any]]


class ProjectStatusResult(ResponseBody):
    revision: int
    status: ProjectStatusInfo


class RuleOverrideInput(RequestBody):
    rule_key: str = Field(min_length=1, max_length=100,
                          description="proof_valid_days.<材料类型>、require_own_staff、social_insurance_months、check_service_period")
    value: bool | int
    source_requirement_id: str | None = Field(default=None, max_length=100, description="依据的招标要求")


class RuleOverridesUpdate(RequestBody):
    overrides: list[RuleOverrideInput] = Field(max_length=50, description="整组替换；空列表清除全部覆盖")


class RuleOverrideRow(ResponseBody):
    rule_key: str
    value: bool | int
    source_requirement_id: str | None = None
    updated_by: str | None = None
    updated_at: str | None = None


class RuleOverridesResult(ResponseBody):
    revision: int
    rule_overrides: list[RuleOverrideRow]


class VolumeSettingInput(RequestBody):
    volume: Volume
    compile_mode: Literal["system", "external"] = Field(description="system 系统编制；external 系统外编制（如报价文件）")
    internal_deadline: str | None = Field(default=None, max_length=50, description="内部截止时间，ISO 格式，未带时区按北京时间")
    separate_seal: bool = False
    page_numbering: Literal["per_volume", "continuous"] = "per_volume"
    blind_bid: bool = False
    cover_template: str | None = Field(default=None, max_length=100)
    submit_file_name: str | None = Field(default=None, max_length=150, description="递交文件名，不得含编写人变量或姓名")


class VolumeSettingsUpdate(RequestBody):
    volumes: list[VolumeSettingInput] = Field(max_length=10)


class VolumeSettingRow(ResponseBody):
    volume: Volume
    compile_mode: str
    internal_deadline: str | None = None
    separate_seal: bool
    page_numbering: str
    blind_bid: bool
    cover_template: str | None = None
    submit_file_name: str | None = None


class VolumeSettingsResult(ResponseBody):
    revision: int
    volume_settings: list[VolumeSettingRow]
    warnings: list[str]


class FullValueUpdate(RequestBody):
    categories: list[Literal["id_number", "phone", "bank_account"]] = Field(
        max_length=3, description="递交版需填完整值的敏感字段类别；仅项目负责人可勾选；空列表表示全部掩码")
    basis_requirement_ids: list[str] = Field(max_length=50, description="依据的招标要求；勾选类别时必填")


class FullValueInfo(ResponseBody):
    categories: list[str]
    basis_requirement_ids: list[str]
    confirmed_by: str | None = None
    confirmed_at: str | None = None


class FullValueResult(ResponseBody):
    revision: int
    submit_full_value: FullValueInfo


class PartnerRow(ResponseBody):
    partner_entity_id: str
    agreement_attachment_id: str | None = None
    agreement_ok: bool
    problem: str | None = Field(default=None, description="缺协议时的说明；缺协议的合作方资料不能被章节引用")


class SettingsTodo(ResponseBody):
    code: str
    title: str
    detail: str = ""
    tab: str = Field(description="可一键跳转的页签")


class SlaSummary(ResponseBody):
    template_name: str
    template_stale: bool
    row_count: int
    exceeds_capability_count: int
    needs_review_count: int


class ProjectSettings(ResponseBody):
    revision: int
    status: ProjectStatusInfo
    basic_info: dict[str, str]
    manual_edits: dict[str, dict[str, Any]] = Field(description="字段 → 最近一次人工修改的人和时间；页面显示“已人工修改”")
    partners: list[PartnerRow]
    rule_overrides: list[RuleOverrideRow]
    volume_settings: list[VolumeSettingRow]
    submit_full_value: FullValueInfo
    sla: SlaSummary | None = None
    staff_occupancy: list[dict[str, Any]] = Field(description="同公司其他在投项目已拟派同一人（只提示，不锁定）")
    todos: list[SettingsTodo]
