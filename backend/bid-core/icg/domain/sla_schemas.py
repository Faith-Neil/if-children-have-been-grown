# 为什么有这个文件：给服务承诺模板、项目取值和确认操作规定明确字段。
# 它解决什么问题：拒绝多余字段、非法数值和伪造能力，供前端与接口说明共同使用。

from typing import Literal

from pydantic import Field, StrictFloat, StrictInt, StrictStr

from .schemas import RequestBody, ResponseBody

SlaValue = StrictStr | StrictInt | StrictFloat
SlaStatus = Literal["pending", "confirmed", "rejected"]
SlaFactStatus = Literal["pending", "confirmed", "needs_review"]


class SlaVariable(RequestBody):
    var_key: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=100)
    group: str = Field(min_length=1, max_length=100)
    value_type: Literal["integer", "decimal", "text"]
    default_value: SlaValue
    unit: str = Field(default="", max_length=30)
    compare_direction: Literal["lower_better", "higher_better", "exact"]
    best_committable_value: SlaValue | None = None


class SlaTemplateCreate(RequestBody):
    name: str = Field(min_length=1, max_length=200)
    edition: Literal["standard", "finance", "government"] = "standard"
    service_hours: Literal["h5x8", "h5x8_holiday", "h7x24"] = "h7x24"
    version_no: str = Field(default="1.0", min_length=1, max_length=20)
    body_text: str = Field(min_length=1, max_length=100_000)
    status: SlaStatus = "pending"
    reason: str = Field(default="", max_length=2000)
    variables: list[SlaVariable] = Field(min_length=1, max_length=100)


class SlaTemplatePatch(RequestBody):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    edition: Literal["standard", "finance", "government"] | None = None
    service_hours: Literal["h5x8", "h5x8_holiday", "h7x24"] | None = None
    version_no: str | None = Field(default=None, min_length=1, max_length=20)
    body_text: str | None = Field(default=None, min_length=1, max_length=100_000)
    status: SlaStatus | None = None
    reason: str | None = Field(default=None, max_length=2000)
    variables: list[SlaVariable] | None = Field(default=None, min_length=1, max_length=100)


class SlaSelection(RequestBody):
    template_id: str = Field(min_length=1, max_length=100)
    reason: str = Field(default="", max_length=2000)


class SlaValuePatch(RequestBody):
    project_value: SlaValue | None = None
    project_unit: str | None = Field(default=None, max_length=30)
    requirement_id: str | None = Field(default=None, min_length=1, max_length=100)
    tender_required_value: SlaValue | None = None
    tender_unit: str | None = Field(default=None, max_length=30)
    reason: str = Field(default="", max_length=2000)


class SlaReviewRequest(RequestBody):
    reason: str = Field(min_length=1, max_length=2000)


class SlaTemplate(ResponseBody):
    id: str
    company_id: str
    revision: int
    version_no: str
    name: str
    edition: str
    service_hours: str
    body_text: str
    status: SlaStatus
    reason: str
    variables: list[SlaVariable]


class SlaTemplateList(ResponseBody):
    revision: int
    items: list[SlaTemplate]


class SlaTemplateResult(ResponseBody):
    revision: int
    item: SlaTemplate


class SlaReview(ResponseBody):
    actor_id: str
    actor_name: str
    at: str
    reason: str
    fingerprint: str


class SlaSource(ResponseBody):
    file_id: str
    page: int
    quote: str


class SlaRow(ResponseBody):
    var_key: str
    label: str
    group: str
    value_type: Literal["integer", "decimal", "text"]
    default_value: SlaValue
    unit: str
    compare_direction: Literal["lower_better", "higher_better", "exact"]
    best_committable_value: SlaValue | None
    project_value: SlaValue | None
    project_unit: str
    requirement_id: str | None
    tender_required_value: SlaValue | None
    tender_unit: str
    source: SlaSource | None
    source_stale: bool
    judgment: Literal["satisfied", "not_satisfied", "exceeds_capability", "missing", "manual", "not_required", "unquantified"]
    judgment_label: str
    message: str
    exceeds_capability: bool
    review: SlaReview | None
    fact_status: SlaFactStatus
    variable_token: str


class SlaCommitment(ResponseBody):
    id: str
    filename: str
    download_url: str
    created_at: str
    fingerprint: str
    status: Literal["valid", "stale"]


class ProjectSla(ResponseBody):
    template_id: str
    template_name: str
    template_revision: int
    template_stale: bool
    rows: list[SlaRow]
    commitments: list[SlaCommitment]


class SlaMutationResult(ResponseBody):
    revision: int
    sla: ProjectSla | None = None
    commitment: SlaCommitment | None = None
