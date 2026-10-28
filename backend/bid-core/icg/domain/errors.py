# 为什么有这个文件：冻结每个业务错误码唯一对应的 HTTP 状态。
# 它解决什么问题：避免同一 code 在不同路由返回不同状态，并让 OpenAPI 与代码使用同一张表。

from __future__ import annotations

# 状态语义与已批准的 ISSUE-005 契约一致。检查结果里的发现码只有在被提升为 HTTP 错误时才列入本表。
STATUS_MEANING: dict[int, str] = {
    401: "未登录或演示会话失效",
    403: "无权限或缺少所需角色",
    404: "资源不存在或当前公司无权访问",
    409: "版本、状态或来源冲突",
    413: "超出大小或容量限制",
    422: "字段或请求内容校验失败",
    423: "编辑权被占用或已失效",
    428: "缺少必需的前置请求头",
    500: "服务内部错误",
    502: "下游解析或模型失败",
    503: "页面或依赖尚未就绪",
}


def _bind(table: dict[str, int], status: int, codes: tuple[str, ...]) -> None:
    for code in codes:
        if code in table:
            raise RuntimeError(f"错误码 {code} 重复登记")
        table[code] = status


def _frozen_status() -> dict[str, int]:
    table: dict[str, int] = {}
    _bind(table, 401, ("UNAUTHENTICATED", "INVALID_ACCOUNT", "INVALID_CREDENTIALS"))
    _bind(table, 403, (
        "FORBIDDEN", "PROJECT_CREATE_FORBIDDEN", "PROJECT_WRITER_REQUIRED",
        "CHAPTER_STRUCTURE_REQUIRED", "CHAPTER_EDITOR_REQUIRED", "PROJECT_LEAD_REQUIRED",
        "FACT_MANAGER_REQUIRED", "SLA_MANAGER_REQUIRED", "MATRIX_RESPONSE_FORBIDDEN",
        "SUBMISSION_FORBIDDEN", "SESSION_ROLE_UNSUPPORTED", "SESSION_SCOPE_UNSUPPORTED",
        # 角色类 *_REQUIRED。原先“尚未指定负责人”也使用本码并返回 409，现统一为 403。
        "VOLUME_OWNER_REQUIRED",
        # ISSUE-024 登记。startGeneration 在适配器不是本地模型时拒绝敏感项目。这里不保存模型配置。
        "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL",
        # 超管角色不可被修改/降权与管理员防自降权 (APP-M2-T028 / PRD v1.8 §5.10.1)
        "SUPER_ADMIN_PROTECTED", "CANNOT_DEMOTE_SELF",
    ))
    _bind(table, 404, ("NOT_FOUND",))
    _bind(table, 409, (
        "VERSION_CONFLICT", "REVISION_CONFLICT", "IDEMPOTENCY_CONFLICT",
        "CHECK_STALE", "CHECK_FAILED", "EXPORT_STALE", "INPUT_FINGERPRINT_STALE",
        "INPUT_FINGERPRINT_REQUIRED", "DRAFT_SEQUENCE_CONFLICT", "TAKEOVER_REASON_REQUIRED",
        "FILE_NOT_PARSED", "FILE_IN_USE", "CHAPTER_VOLUME_MISMATCH", "EVIDENCE_NOT_USABLE",
        "EVIDENCE_EXPIRED", "REFERENCE_REASON_REQUIRED", "INVALID_CONFLICT_SELECTION",
        "PARSE_INCOMPLETE", "PARSE_NOT_CONFIRMED", "REQUIREMENTS_EMPTY", "REVIEW_PENDING",
        "CONFIRMED_REQUIREMENTS_EMPTY", "CONFLICTS_PENDING", "CONFLICT_SELECTION_INVALID",
        "SLA_NOT_READY", "FACT_NOT_READY", "FACT_NOT_FOUND", "FACT_CONFLICT",
        "CHAPTER_IN_USE", "CHAPTER_HAS_CONTENT", "CHAPTER_MAPPED", "MATRIX_MAPPING_MISSING",
        "ALL_VOLUMES_CHECK_REQUIRED", "RULES_INCOMPLETE", "REVIEW_REASON_REQUIRED",
        "HANDOFF_REASON_REQUIRED", "LAST_PROJECT_LEAD_REQUIRED", "LOCAL_MODEL_REQUIRED",
        "SLA_PROJECT_EXPORT_REQUIRED", "PLAN_STALE", "PLAN_NOT_CONFIRMED",
        "REQUIREMENT_NOT_READY", "SLA_VARIABLE_UNKNOWN", "SLA_VARIABLE_UNCONFIRMED",
        "SLA_VARIABLE_UNIT_UNRESOLVED", "SLA_VARIABLE_UNIT_MISMATCH",
        "SLA_TEMPLATE_VARIABLE_UNKNOWN", "SLA_TEMPLATE_UNCONFIRMED", "SLA_VARIABLE_REMOVED",
        "SLA_TEMPLATE_STALE", "SLA_SOURCE_INVALID", "SLA_TEMPLATE_REQUIRED", "SLA_SOURCE_STALE",
        "SLA_REVIEW_FORBIDDEN", "SLA_FACT_READ_ONLY", "SLA_FACT_INVALID", "SLA_REVIEW_REQUIRED",
        "SLA_COMMITMENT_BLOCKED", "SLA_REQUIREMENT_UNBOUND", "SLA_VALUE_INVALID",
        "SLA_FACT_UNCONFIRMED", "SLA_TEXT_MISMATCH", "FACT_SOURCE_CHANGE_REQUIRED",
        "FACT_VARIABLE_INVALID", "FACT_VARIABLE_UNIT_MISMATCH", "FACT_VARIABLE_UNIT_DUPLICATED",
        "FACT_VARIABLE_LOST", "FACT_LITERAL_REPLACEMENT",
        # 字典配置与元数据停用/保护红线 (APP-M2-T024 / PRD v1.8 §5.10.3 / §6.9)
        "DICT_ITEM_IN_USE", "DICT_CODE_DUPLICATED",
        # 用户管理停用前资产转交门禁 (APP-M2-T027 / PRD v1.8 §5.10.1)
        "USER_TRANSFER_REQUIRED",
    ))
    _bind(table, 413, (
        "FILE_SIZE_LIMIT", "FILE_EXPANSION_LIMIT", "PDF_PAGE_LIMIT", "GENERATION_CONTEXT_TOO_LARGE",
    ))
    _bind(table, 422, (
        "VALIDATION_ERROR", "INVALID_SESSION_INPUT", "INVALID_PROJECT_FIELD", "INVALID_PROJECT_NAME",
        "INVALID_FILENAME", "FILE_TYPE_UNSUPPORTED", "INVALID_FILE_ENCODING", "FILES_REQUIRED",
        "INVALID_REQUIREMENT", "EMPTY_REQUIREMENT", "DUPLICATE_EVIDENCE", "INVALID_FACT",
        "EMPTY_FACT", "DUPLICATE_FACT", "EMPTY_CHAPTER_TITLE", "DUPLICATE_CHAPTER", "INVALID_DATE",
        "INVALID_LIBRARY_FIELD", "EMPTY_LIBRARY_FIELD", "TEXT_ENCODING", "INVALID_TEXT", "NO_TEXT",
        "INVALID_DOCX", "PDF_ADAPTER_UNAVAILABLE", "PDF_ENCRYPTED", "INVALID_PDF", "OCR_REQUIRED",
        "ASSIGNEE_NOT_WRITABLE", "DUPLICATE_MEMBER", "DUPLICATE_VOLUME", "MEMBER_ROLE_NOT_WRITABLE",
        "PROJECT_LEAD_COMPANY_ROLE_REQUIRED", "LEAD_ALL_VOLUMES_REQUIRED", "INVALID_SLA_VALUE",
        "INVALID_SLA_VARIABLE", "INVALID_SLA_GROUP", "INVALID_SLA_UNIT", "INVALID_SLA_DIRECTION",
        "EMPTY_SLA_TEMPLATE", "INVALID_SLA_TEMPLATE", "REASON_REQUIRED", "SLA_SOURCE_REQUIRED",
        "SLA_FACT_CONFIRM_REQUIRED",
        # 请求或已保存结构缺少两册。导出原先返回 409，现与大纲、团队设置同为 422。
        "TWO_VOLUMES_REQUIRED",
        # 企业设置与安全策略越界校验 (APP-M2-T025 / PRD v1.8 §5.10.2 / §6.9)
        "SETTING_VALUE_OUT_OF_BOUNDS",
        # 密码强度策略不足 (PRD v1.8 §5.10.2 / Q28)
        "PASSWORD_WEAK",
    ))
    _bind(table, 423, ("LOCK_HELD", "LOCK_LOST", "ACCOUNT_LOCKED"))
    _bind(table, 428, ("IF_MATCH_REQUIRED", "IDEMPOTENCY_KEY_REQUIRED"))
    _bind(table, 500, ("INTERNAL_ERROR",))
    _bind(table, 502, ("MODEL_UNAVAILABLE", "MODEL_OUTPUT_INVALID", "PARSER_UNAVAILABLE"))
    # SECRET_KEY_UNAVAILABLE 不是瞬时故障：客户端不得自动重试，服务端不得发送 Retry-After。
    # 与 MODEL_UNAVAILABLE 相同。实现 ISSUE-024 时再断言响应没有该头。
    _bind(table, 503, ("UI_NOT_READY", "SECRET_KEY_UNAVAILABLE"))
    return table


ERROR_STATUS: dict[str, int] = _frozen_status()

NON_TRANSIENT_RETRY_EXCEPTION = (
    "502 MODEL_UNAVAILABLE 与 503 SECRET_KEY_UNAVAILABLE 不是瞬时故障，"
    "客户端不要自动重试，后端不发送 Retry-After。"
)

RETRY_GUIDANCE = (
    "客户端只自动重试网络错误、502 和 503，并且必须复用同一个 Idempotency-Key；"
    "建议指数退避，最多 3 次。409、422、423、428 不重试，交给用户处理。401 重新登录。"
    "GET 可以重试。服务端不代替客户端重发请求。"
    + NON_TRANSIENT_RETRY_EXCEPTION
)


def status_for(code: str) -> int:
    try:
        return ERROR_STATUS[code]
    except KeyError as error:
        raise KeyError(f"错误码 {code} 不在已冻结的 HTTP 状态表中") from error


def codes_for(status: int) -> list[str]:
    return sorted(code for code, value in ERROR_STATUS.items() if value == status)


def status_table() -> dict[str, list[str]]:
    return {str(status): codes_for(status) for status in sorted(STATUS_MEANING)}


def enrich_openapi(schema: dict) -> dict:
    """把冻结的错误表、追踪头、幂等语义和重试说明写进从代码导出的 OpenAPI。"""
    from .idempotency import IDEMPOTENCY_HEADER_DESCRIPTION, IDEMPOTENCY_TTL_SECONDS, MAX_IDEMPOTENCY_RECEIPTS
    info = schema.setdefault("info", {})
    info["description"] = (
        "错误体统一为 {code, message, details, traceId}，traceId 与响应头 X-Request-ID 相同，"
        "由服务端生成。"
        f"每个 code 只对应一个 HTTP 状态。Idempotency-Key 回执保留 {IDEMPOTENCY_TTL_SECONDS // 3600} 小时，"
        f"内存最多 {MAX_IDEMPOTENCY_RECEIPTS} 条。{RETRY_GUIDANCE}"
    )
    components = schema.setdefault("components", {})
    components["x-error-status"] = {
        "description": "每个业务 code 只对应一个 HTTP 状态。VOLUME_OWNER_REQUIRED 为 403，TWO_VOLUMES_REQUIRED 为 422。",
        "statuses": status_table(),
    }
    components["x-idempotency"] = {
        "header": "Idempotency-Key",
        "pattern": "^[A-Za-z0-9_-]{8,120}$",
        "scope": "scope_id + user_id + key；项目写入的 scope_id 为 project_id，公司资料与服务承诺模板为 library:{company_id}",
        "fingerprint": "action + canonical payload + If-Match",
        "replay": "同键同指纹返回首次成功结果，并设置响应头 Idempotent-Replayed: true",
        "conflict": "同键不同指纹返回 409 IDEMPOTENCY_CONFLICT",
        "missing": "缺少或格式不符返回 428 IDEMPOTENCY_KEY_REQUIRED",
        "failures": "失败不登记回执，同一标记可以重试",
        "ttl_seconds": IDEMPOTENCY_TTL_SECONDS,
        "max_receipts": MAX_IDEMPOTENCY_RECEIPTS,
        "legacy_body_field": "仅 POST /api/chapters/{chapter_id}/versions 仍接受正文 idempotency_key；同时出现请求头时两者必须相同",
        "retry": RETRY_GUIDANCE,
        "description": IDEMPOTENCY_HEADER_DESCRIPTION,
    }
    headers = components.setdefault("headers", {})
    headers["X-Request-ID"] = {
        "description": "32 位十六进制请求编号，与统一错误体 traceId 相同。服务端生成，不接受客户端传入。",
        "schema": {"type": "string", "pattern": "^[0-9a-f]{32}$"},
    }
    headers["Idempotent-Replayed"] = {
        "description": "同键同指纹重放首次成功结果时为 true；首次成功和失败响应不发送该头。",
        "schema": {"type": "string", "enum": ["true"]},
    }
    error = components.get("schemas", {}).get("V1Error")
    if error and "properties" in error:
        error["properties"]["code"]["enum"] = sorted(ERROR_STATUS)
    for path, item in schema.get("paths", {}).items():
        for operation in item.values():
            if not isinstance(operation, dict) or "responses" not in operation:
                continue
            writes = any(parameter.get("name") == "Idempotency-Key" and parameter.get("in") == "header"
                         for parameter in operation.get("parameters", []))
            for response in operation["responses"].values():
                if not isinstance(response, dict):
                    continue
                content = response.get("content", {}).get("application/json", {})
                ref = content.get("schema", {}).get("$ref", "")
                if ref.endswith("/ErrorResponse"):
                    content["schema"]["$ref"] = "#/components/schemas/V1Error"
                response_headers = response.setdefault("headers", {})
                response_headers.setdefault("X-Request-ID", {"$ref": "#/components/headers/X-Request-ID"})
                if writes:
                    response_headers.setdefault("Idempotent-Replayed", {"$ref": "#/components/headers/Idempotent-Replayed"})
    # 冻结契约：startGeneration 的 423 与 503 失败不登记回执，响应头不列 Idempotent-Replayed。
    started = schema.get("paths", {}).get("/api/v1/projects/{project_id}/generation/start", {}).get("post")
    if isinstance(started, dict):
        for code in ("423", "503"):
            headers = started.get("responses", {}).get(code, {}).get("headers")
            if isinstance(headers, dict):
                headers.pop("Idempotent-Replayed", None)
    return schema
