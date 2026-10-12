为什么有这个文件：保存错误体和24小时幂等的实际命令、结果和冻结状态表。

它解决什么问题：前端实现请求层时有一份可核对的状态表，而不是从多处路由各自猜测。

# 错误体与幂等验证

日期：2026-10-12。关联：[ISSUE-005](../../issues/ISSUE-005.md)、[BE-M0-T02](../delivery/BE-M0-T02.md)、[BE-M0-T03](../delivery/BE-M0-T03.md)。两张卡为in-review，未合入、未发布。done只由项目经理在QA签收后标记。

## 命令与结果

在仓库根执行：

```text
PYTHONPATH=backend/bid-core python3 -m pytest tests/backend -q --tb=line
```

结果：308 passed，1 warning，84.31秒。警告是既有的 Starlette/httpx `DeprecationWarning`。rebase 到布局回退路由和内存检索之后重跑。未知 `/api/v1` 路径返回统一 404 体，`traceId` 与 `X-Request-ID` 相同；路径里的 `..` 不打开页面目录之外的文件。

前端代码未改。CI工作流仍会构建并运行前端测试。

另两条CI命令在本机通过：`python3 tests/backend/session_live_http.py`为15/15；在`backend/bid-core`运行`python3 smoke_t06.py`为12/12。

治理检查命令与输出在本文末尾，于文档登记完成后执行。检查程序本身未修改，因此未运行`node --test tests/governance/*.test.cjs`。

## 专项覆盖

- v1未登录响应含`code`、`message`、`details`、`traceId`，且`traceId`等于`X-Request-ID`。
- 旧`/api/projects`仍是`error`加`request_id`。
- `VALIDATION_ERROR`的`details.fields`含`body.name`。
- 同键同内容重放，响应头`Idempotent-Replayed`为`true`，正文与第一次相同。
- 同键不同内容返回409 `IDEMPOTENCY_CONFLICT`，不增加新记录；换一个新键可以成功，且第一次成功不带重放头。
- 缺少键、键为`short`返回428。空白内容先返回422，同一键配当前版本和有效内容可以成功，且不带重放头。
- 未过期时，同一键改了`If-Match`为409。时钟前进86401秒后，同一键按当前版本重新执行并成功。
- 上限调成1时，最旧回执被丢弃，较新回执仍可重放。
- `MODEL_UNAVAILABLE`固定502。`/api/v1`候选生成失败时正文是`{code, message, details, traceId}`。旧`/api`章节建议仍是`error`加`request_id`。
- 语法树核对字面`DomainError`与冻结表一致。
- 导出的`spec/openapi/demo-v1.json`与运行中的OpenAPI相同；v1不再引用旧错误模型。

既有用例的两处期望已按冻结表改写：未指定分册负责人的确认从409改为403；解析器不可用从422改为502。

## 冻结的HTTP状态与错误码

共141个code。每个code只出现一次。`HTTP_ERROR`不在表内。

| HTTP | 个数 | 含义 | 错误码 |
|---|---|---|---|
| 401 | 2 | 未登录或演示会话失效 | `INVALID_ACCOUNT`, `UNAUTHENTICATED` |
| 403 | 13 | 无权限或缺少所需角色 | `CHAPTER_EDITOR_REQUIRED`, `CHAPTER_STRUCTURE_REQUIRED`, `FACT_MANAGER_REQUIRED`, `FORBIDDEN`, `MATRIX_RESPONSE_FORBIDDEN`, `PROJECT_CREATE_FORBIDDEN`, `PROJECT_LEAD_REQUIRED`, `PROJECT_WRITER_REQUIRED`, `SESSION_ROLE_UNSUPPORTED`, `SESSION_SCOPE_UNSUPPORTED`, `SLA_MANAGER_REQUIRED`, `SUBMISSION_FORBIDDEN`, `VOLUME_OWNER_REQUIRED` |
| 404 | 1 | 资源不存在或当前公司无权访问 | `NOT_FOUND` |
| 409 | 68 | 版本、状态或来源冲突 | `ALL_VOLUMES_CHECK_REQUIRED`, `CHAPTER_HAS_CONTENT`, `CHAPTER_IN_USE`, `CHAPTER_MAPPED`, `CHAPTER_VOLUME_MISMATCH`, `CHECK_FAILED`, `CHECK_STALE`, `CONFIRMED_REQUIREMENTS_EMPTY`, `CONFLICTS_PENDING`, `CONFLICT_SELECTION_INVALID`, `DRAFT_SEQUENCE_CONFLICT`, `EVIDENCE_EXPIRED`, `EVIDENCE_NOT_USABLE`, `EXPORT_STALE`, `FACT_CONFLICT`, `FACT_LITERAL_REPLACEMENT`, `FACT_NOT_FOUND`, `FACT_NOT_READY`, `FACT_SOURCE_CHANGE_REQUIRED`, `FACT_VARIABLE_INVALID`, `FACT_VARIABLE_LOST`, `FACT_VARIABLE_UNIT_DUPLICATED`, `FACT_VARIABLE_UNIT_MISMATCH`, `FILE_IN_USE`, `FILE_NOT_PARSED`, `HANDOFF_REASON_REQUIRED`, `IDEMPOTENCY_CONFLICT`, `INPUT_FINGERPRINT_REQUIRED`, `INPUT_FINGERPRINT_STALE`, `INVALID_CONFLICT_SELECTION`, `LAST_PROJECT_LEAD_REQUIRED`, `LOCAL_MODEL_REQUIRED`, `MATRIX_MAPPING_MISSING`, `PARSE_INCOMPLETE`, `PARSE_NOT_CONFIRMED`, `PLAN_NOT_CONFIRMED`, `PLAN_STALE`, `REFERENCE_REASON_REQUIRED`, `REQUIREMENTS_EMPTY`, `REQUIREMENT_NOT_READY`, `REVIEW_PENDING`, `REVIEW_REASON_REQUIRED`, `REVISION_CONFLICT`, `RULES_INCOMPLETE`, `SLA_COMMITMENT_BLOCKED`, `SLA_FACT_INVALID`, `SLA_FACT_READ_ONLY`, `SLA_FACT_UNCONFIRMED`, `SLA_NOT_READY`, `SLA_PROJECT_EXPORT_REQUIRED`, `SLA_REQUIREMENT_UNBOUND`, `SLA_REVIEW_FORBIDDEN`, `SLA_REVIEW_REQUIRED`, `SLA_SOURCE_INVALID`, `SLA_SOURCE_STALE`, `SLA_TEMPLATE_REQUIRED`, `SLA_TEMPLATE_STALE`, `SLA_TEMPLATE_UNCONFIRMED`, `SLA_TEMPLATE_VARIABLE_UNKNOWN`, `SLA_TEXT_MISMATCH`, `SLA_VALUE_INVALID`, `SLA_VARIABLE_REMOVED`, `SLA_VARIABLE_UNCONFIRMED`, `SLA_VARIABLE_UNIT_MISMATCH`, `SLA_VARIABLE_UNIT_UNRESOLVED`, `SLA_VARIABLE_UNKNOWN`, `TAKEOVER_REASON_REQUIRED`, `VERSION_CONFLICT` |
| 413 | 4 | 超出大小或容量限制 | `FILE_EXPANSION_LIMIT`, `FILE_SIZE_LIMIT`, `GENERATION_CONTEXT_TOO_LARGE`, `PDF_PAGE_LIMIT` |
| 422 | 44 | 字段或请求内容校验失败 | `ASSIGNEE_NOT_WRITABLE`, `DUPLICATE_CHAPTER`, `DUPLICATE_EVIDENCE`, `DUPLICATE_FACT`, `DUPLICATE_MEMBER`, `DUPLICATE_VOLUME`, `EMPTY_CHAPTER_TITLE`, `EMPTY_FACT`, `EMPTY_LIBRARY_FIELD`, `EMPTY_REQUIREMENT`, `EMPTY_SLA_TEMPLATE`, `FILES_REQUIRED`, `FILE_TYPE_UNSUPPORTED`, `INVALID_DATE`, `INVALID_DOCX`, `INVALID_FACT`, `INVALID_FILENAME`, `INVALID_FILE_ENCODING`, `INVALID_LIBRARY_FIELD`, `INVALID_PDF`, `INVALID_PROJECT_FIELD`, `INVALID_PROJECT_NAME`, `INVALID_REQUIREMENT`, `INVALID_SESSION_INPUT`, `INVALID_SLA_DIRECTION`, `INVALID_SLA_GROUP`, `INVALID_SLA_TEMPLATE`, `INVALID_SLA_UNIT`, `INVALID_SLA_VALUE`, `INVALID_SLA_VARIABLE`, `INVALID_TEXT`, `LEAD_ALL_VOLUMES_REQUIRED`, `MEMBER_ROLE_NOT_WRITABLE`, `NO_TEXT`, `OCR_REQUIRED`, `PDF_ADAPTER_UNAVAILABLE`, `PDF_ENCRYPTED`, `PROJECT_LEAD_COMPANY_ROLE_REQUIRED`, `REASON_REQUIRED`, `SLA_FACT_CONFIRM_REQUIRED`, `SLA_SOURCE_REQUIRED`, `TEXT_ENCODING`, `TWO_VOLUMES_REQUIRED`, `VALIDATION_ERROR` |
| 423 | 2 | 编辑权被占用或已失效 | `LOCK_HELD`, `LOCK_LOST` |
| 428 | 2 | 缺少必需的前置请求头 | `IDEMPOTENCY_KEY_REQUIRED`, `IF_MATCH_REQUIRED` |
| 500 | 1 | 服务内部错误 | `INTERNAL_ERROR` |
| 502 | 3 | 下游解析或模型失败 | `MODEL_OUTPUT_INVALID`, `MODEL_UNAVAILABLE`, `PARSER_UNAVAILABLE` |
| 503 | 1 | 页面或依赖尚未就绪 | `UI_NOT_READY` |

两处原先一个码对应两个状态的决定：

- `VOLUME_OWNER_REQUIRED` → 403。角色类`*_REQUIRED`已是403；确认路径里“尚未指定负责人”的409并入403。
- `TWO_VOLUMES_REQUIRED` → 422。大纲和团队设置已是422；导出的409并入422。

## 幂等规则核对

| 规则 | 结果 |
|---|---|
| 范围 | 项目写入为项目编号+账号+键；资料库和模板为`library:{company_id}`+账号+键 |
| 同键同指纹 | 重放首次成功，响应头`Idempotent-Replayed: true` |
| 同键不同指纹 | 409 `IDEMPOTENCY_CONFLICT`，无新副作用 |
| 缺少或格式不符 | 428 `IDEMPOTENCY_KEY_REQUIRED`；格式`^[A-Za-z0-9_-]{8,120}$` |
| 失败 | 不登记，同一键可再试；解析失败仍保存失败任务并增加版本，再试需要新的`If-Match` |
| 过期 | 24小时，即86400秒 |
| 内存上限 | 2048条，先丢过期再丢最旧 |
| 重试 | 只自动重试网络错误、502、503，并复用同一键；409/422/423/428不重试 |
| 旧正文 | 仅`POST /api/chapters/{chapter_id}/versions`仍要正文`idempotency_key`；头同时出现时必须相同 |

## 未验证

没有浏览器页面，没有前端测试，没有真实多进程，没有重启后的回执恢复。202、SSE、锁迁到v1、导出快照和operationId改名未实现。数据库未接入。

## 治理检查

命令：`node scripts/check-project-governance.cjs`

输出：`治理检查通过：154 份 Markdown、350 项任务、16 项 Issue。`退出码0。检查程序未修改。另在仓库根运行`node --test tests/governance/*.test.cjs tests/prototype/*.test.cjs tests/workspace-sync/*.test.cjs tests/backend/demo-page.test.cjs`：35 passed。前端构建通过；当时 `node --experimental-strip-types --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs`：72 passed。本机 Node 22 需要该实验开关，CI 使用 Node 24.9.0。布局切片之后的前端测试由该切片自己的记录覆盖，本轮没有改前端。
