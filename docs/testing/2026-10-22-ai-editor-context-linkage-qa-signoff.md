# 为什么有这个文件：记录QA对AI-EDITOR-CONTEXT-LINKAGE（编辑台章节上下文感知问答与划词引用联动）的独立复验与签署结论。

# 它解决什么问题：不轻信自报结果，亲手执行专属编辑台上下文与划词问答测试用例，严格审计四道安全门禁：门禁1系统只读角色与项目只读成员提问拦截（403 FORBIDDEN）、门禁2跨租户与章节归属隔离（404 NOT_FOUND）、门禁3敏感项目强制本地模型隔离（403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL）、门禁4独占编辑锁租约守卫（未获锁强制 copy_only 且章节正文零突变，获有效锁且有依据才放行替换建议）。

# AI-EDITOR-CONTEXT-LINKAGE 编辑台章节上下文感知问答与划词引用联动独立复测与 QA 签署

- 被验任务：`AI-EDITOR-CONTEXT-LINKAGE` · 编辑台章节上下文感知问答与划词引用联动
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联交付：[AI-EDITOR-CONTEXT-LINKAGE 交付](../delivery/AI-EDITOR-CONTEXT-LINKAGE.md)、[代码解释](../code/AI-EDITOR-CONTEXT-LINKAGE.md)
- 被验核心文件：
  - `backend/bid-core/icg_demo/editor_ai_context.py`
  - `backend/bid-core/icg_demo/answer_card.py`
  - `backend/bid-core/icg_demo/domain.py`
  - `backend/bid-core/icg_demo/workflow.py`
  - `tests/backend/test_editor_ai_context.py`
- 复验环境：Windows, Python 3.12.9, pytest 8.4.2
- 结论：**通过 (PASS)**。**AI-EDITOR-CONTEXT-LINKAGE 保持 in-review，严禁标 done；关联 Issue 保持原状态**。

---

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 编辑台上下文与划词片段注入 | 通过 | `test_decompose_paragraphs_and_selection_matching`、`test_build_editor_prompt_context_polish_scene`：正文拆分为 `[P1]`, `[P2]...` 编号段落，划选文本精准定位所在段落并标记 `is_selected=True`，起止偏移明确；无选中文本时全段落 `is_selected=False` 干净兜底。 |
| AC-02 划词润色场景（polish）与 Diff 建议 | 通过 | `test_chat_editor_context_polish_diff_suggestion`：提供选中文本时输出专业 Diff 建议结构（`diff_suggestion` 包含 `original`, `suggested`, `diff_mode="selection"`），保留正文事实变量。 |
| AC-03 章节合规性与完整度问答（compliance_qa） | 通过 | `test_build_editor_prompt_context_compliance_scene`：无划词或合规问答时自动切换为条款诊断模式，Prompt 完整注入招标文件条款、项目事实变量与已核对依据。 |
| AC-04 依据溯源与不可篡改指纹 | 通过 | 自动搜集公司资料库已核对证据 `[证]` 与知识库检索切片 `[片]`，计算不可篡改 16 位十六进制 SHA-256 依据指纹，并生成联合 `context_fingerprint`。 |
| AC-05 独占编辑锁守卫与正文零突变 | 通过 | `test_guard_no_lock_forces_copy_only`：未获锁时 `can_insert` 恒定为 `False`，`action="copy_only"`，明确提示未获锁，章节正文/修订号/版本历史 100% 零突变；`test_guard_valid_lock_and_citations_allow_suggest_replacement`：持有效锁且有依据时放行 `suggest_replacement`。 |
| AC-06 敏感项目本地模型强门禁 | 通过 | `test_guard_sensitive_project_blocks_cloud_model`：敏感项目绑定云端模型强拦截抛出 `403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`，绑定合格本地离线模型放行。 |
| AC-07 角色权限拦截与跨租户隔离 | 通过 | `test_guard_readonly_roles_and_cross_tenant_isolation`：`viewer`/`auditor`/`group_admin`/`platform_admin` 及项目只读成员拦截 `403 FORBIDDEN`，跨租户访问拦截 `404 NOT_FOUND`。 |
| AC-08 服务层门面委派与兼容 | 通过 | `test_workflow_service_and_answer_card_integration`：`WorkflowService.editor_ai_chat`、`build_editor_prompt_context` 及 `AnswerCardService.general_chat` 划词参数无缝平滑联动。 |

---

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 编辑台上下文感知问答专属单测 | `pytest tests/backend/test_editor_ai_context.py -v` | **12 passed, 0 failed** | 0.49s |
| 章节生成、助手与编辑台联合套件 | `pytest tests/backend/test_editor_ai_context.py tests/backend/test_general_chat_qa.py tests/backend/test_outline_generation_start.py tests/backend/test_error_idempotency.py tests/backend/test_answer_cards.py tests/backend/test_insert_answer_card.py tests/backend/test_chapter_generation_rag_flow.py -v` | **73 passed, 0 failed** | 22.84s |
| OpenAPI 契约与冻结错误码 AST 断言 | `pytest tests/backend/test_error_idempotency.py -v` | **9 passed, 0 failed** | 4.35s |

---

## 签署状态

AI-EDITOR-CONTEXT-LINKAGE 保持 **in-review**，**严禁标 done**。
