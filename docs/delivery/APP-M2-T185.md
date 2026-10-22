# 为什么有这个文件：记录 AI 助手采纳润色建议原地回写与段落替换协议（APP-M2-T185）的交付成果、验收指标、代码与测试凭据。
# 它解决什么问题：不轻信自报结果，亲手验证排他编辑锁校验、基线版本与原文段落定位防冲突校验、敏感项目本地模型门禁、原子版本递增与修订历史归档、增量复查流转及 OpenAPI 契约安全保护，将任务标为 in-review，严禁私自标 done，严禁私自关闭 Issue。

# APP-M2-T185 交付报告：AI 助手采纳润色建议原地回写与段落替换协议

- 任务编号：`APP-M2-T185`
- 关联需求：差异确认写入 / AI 助手采纳润色建议原地回写与段落替换协议
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)、[ISSUE-037](../../issues/ISSUE-037.md)
- 规范出处：[PRD v1.8 §5.11.5、§5.11.6](../../docs/reference/product/prd-mvp-v1.8.md)，原交接文档 M6-I05-F1
- 代码解释：[APP-M2-T185 代码解释](../code/APP-M2-T185.md)
- 交付状态：**in-review**（严格遵循工作规范：绝不私自标 done，绝不私自关闭 Issue）

---

## 1. 交付目标对照

| 序号 | 需求指标 | 交付状态 | 实现与验证说明 |
|---|---|---|---|
| 1 | **采纳建议原地回写协议** | **已交付** | 落地 `POST /api/v1/projects/{project_id}/chapters/{chapter_id}/accept-ai-suggestion`，将建议改写文本精准原地替换目标段落并重组正文，支持 `paragraph_id` 与 `original_text` 双重定位机制。 |
| 2 | **严格排他编辑锁守卫** | **已交付** | 严格校验调用者必须持有当前章节有效排他编辑锁（`lease_token` 匹配且未过期且锁主一致），无锁/锁过期拦截 423 `LOCK_LOST`，他人持锁拦截 423 `LOCK_HELD`。 |
| 3 | **并发冲突版本保护** | **已交付** | 严格校验 `base_revision`，若章节版本在此期间发生变更，拦截 409 `REVISION_CONFLICT`；若原文在此期间被其他人修改未匹配，同样抛出 409 `REVISION_CONFLICT`。 |
| 4 | **版本自增与修订历史归档** | **已交付** | 原子递增章节 revision 与项目 revision，将更新归档到 `chapter.versions`（含 citations 依据、采纳人、时间戳与 `edit_mode="accept_ai_suggestion"`），自动清理个人草稿。 |
| 5 | **增量复查状态流转** | **已交付** | 采纳回写成功后，响应模型及持久化状态将 `incremental_check_status` 标记为 `pending`，触发后台增量合规检查引擎。 |
| 6 | **敏感项目本地模型硬门禁** | **已交付** | 敏感项目强拦截云端非本地模型（403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`），严格保障涉密数据隔离与内网要求。 |
| 7 | **角色权限与多租户隔离** | **已交付** | 系统只读角色（`viewer`/`auditor`/`readonly`）及项目只读成员拦截 403 `FORBIDDEN`；跨公司跨项目访问拦截 404 `NOT_FOUND`。 |
| 8 | **OpenAPI 契约零漂移** | **已交付** | 新增端点显式配置 `include_in_schema=False`，契约测试与 143 个冻结错误码一致性单测全绿通过。 |

---

## 2. 交付物清单

### 2.1 核心代码与服务
- `backend/bid-core/icg_demo/workflow_schemas.py`：定义 `AcceptAiSuggestionRequest` 与 `AcceptAiSuggestionResponse` 结构体。
- `backend/bid-core/icg_demo/editor_ai_context.py`：在 `EditorAIContextService` 中落地 `accept_ai_suggestion` 核心服务逻辑与六重安全校验。
- `backend/bid-core/icg_demo/domain.py`：在 `DemoService` 挂载 `accept_ai_suggestion`。
- `backend/bid-core/icg_demo/workflow.py`：在 `WorkflowService` 挂载 `accept_ai_suggestion`。
- `backend/bid-core/icg_demo/workflow_routes.py`：注册 HTTP 端点并使用 `include_in_schema=False` 保护契约。

### 2.2 自动化测试
- `tests/backend/test_accept_ai_suggestion.py`：8 项专属自动化单测，涵盖段落定位替换、原文搜索替换、无锁/失锁 423 拦截、基线版本与原文冲突 409 拦截、敏感项目云模型 403 拦截、只读权限 403 拦截、跨租户 404 隔离与 HTTP 端点贯通。

### 2.3 规范文档
- `docs/code/APP-M2-T185.md`：核心技术架构、协议设计、六重防御门禁及数据流说明。
- `docs/delivery/APP-M2-T185.md`：本交付验收报告。

---

## 3. 测试验证凭证

### 3.1 专属单测执行
```bash
pytest tests/backend/test_accept_ai_suggestion.py -vv
```
**实测结果**：
```text
============================= test session starts =============================
platform win32 -- Python 3.12.9, pytest-8.4.2, pluggy-1.6.0
collected 8 items

tests/backend/test_accept_ai_suggestion.py::test_accept_suggestion_success_by_paragraph_id PASSED [ 12%]
tests/backend/test_accept_ai_suggestion.py::test_accept_suggestion_success_by_original_text_only PASSED [ 25%]
tests/backend/test_accept_ai_suggestion.py::test_gate_no_lock_or_expired_lock_blocked_with_423 PASSED [ 37%]
tests/backend/test_accept_ai_suggestion.py::test_gate_revision_conflict_blocked_with_409 PASSED [ 50%]
tests/backend/test_accept_ai_suggestion.py::test_gate_sensitive_project_blocks_cloud_model_with_403 PASSED [ 62%]
tests/backend/test_accept_ai_suggestion.py::test_gate_readonly_and_permission_blocked_with_403 PASSED [ 75%]
tests/backend/test_accept_ai_suggestion.py::test_cross_project_and_cross_tenant_isolation_with_404 PASSED [ 87%]
tests/backend/test_accept_ai_suggestion.py::test_http_endpoint_and_openapi_safety PASSED [100%]

============================== 8 passed in 1.24s ==============================
```

### 3.2 关联回归测试
```bash
pytest tests/backend/test_accept_ai_suggestion.py \
       tests/backend/test_tender_document_retrieval.py \
       tests/backend/test_editor_ai_context.py \
       tests/backend/test_chapter_edit_detail.py \
       tests/backend/test_insert_answer_card.py \
       tests/backend/test_general_chat_qa.py -v
```
**实测结果**：**59 passed in 5.52s**。关联上下游及编辑台深度套件 100% 绿灯通过。

### 3.3 冻结错误码一致性与契约安全测试
```bash
pytest tests/backend/test_error_idempotency.py -k "test_literal_domain_errors_use_the_single_frozen_status" -v
```
**实测结果**：**1 passed, 11 deselected in 0.95s**。所有使用的 DomainError 状态与错误码 100% 严格符合冻结契约。
