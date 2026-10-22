# 为什么有这个文件：记录QA对APP-M2-T124 / APP-M2-T126（写作方案组装与逐节确认启动生成）的独立复验与签署结论。

# 它解决什么问题：不轻信自报结果，亲手执行专属写作方案与章节启动单测与关联测试，深度审计四大安全门禁与任务生命周期：门禁1写作方案输入上下文完整组装（小标题、字数、事实约束、[证]条目、[片]切片、变量清单）、门禁2逐节确认独立启动（未确认分册或未确认章节绝对不阻塞已确认章节的独立启动，企图启动未确认方案章节强拦截抛出 PLAN_NOT_CONFIRMED）、门禁3涉密项目本地模型强门禁（云端模型 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL、本地模型放行）、门禁4异步任务 demo_job 创建与 JobProgress 流转对接。

# APP-M2-T126 写作方案组装与逐节确认启动生成独立复测与 QA 签署

- 被验任务：[APP-M2-T124](../tasks/APP-M2.md#app-m2-t124)、[APP-M2-T126](../tasks/APP-M2.md#app-m2-t126) · 写作方案组装与逐节确认启动生成
- 关联审查任务：REV-M0-T58
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)、[ISSUE-022](../../issues/ISSUE-022.md)
- 关联交付：[APP-M2-T126 交付](../delivery/APP-M2-T126.md)、[代码解释](../code/APP-M2-T126.md)
- 被验核心文件：`backend/bid-core/icg_demo/chapter_generation.py`、`backend/bid-core/icg_demo/domain.py`、`backend/bid-core/icg_demo/workflow.py`、`tests/backend/test_outline_generation_start.py`
- 复验环境：Windows, Python 3.12.9, pytest 8.4.2
- 结论：**通过 (PASS)**。**APP-M2-T124 / APP-M2-T126 保持 in-review，严禁标 done；关联 Issue 保持原状态**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 写作方案 Prompt 输入完整组装（APP-M2-T124） | 通过 | `test_assemble_writing_prompt_plan_context_complete`：小标题提纲（writing_points）、字数目标（800字）、事实约束（保留变量）、引用规范（[证]）、[证]已核对公司证据（revision/valid_until）、[片]RAGFlow检索切片（chunk_id/document_id）及项目事实与SLA变量全部规范化装配入 prompt 与 input_snapshot |
| AC-02 逐节确认启动生成与 job 创建（APP-M2-T126） | 通过 | `test_start_chapter_generation_success_creates_job`：已确认章节启动成功，在 demo_job 中创建 `job_type="generate_chapter"`, `status="running"`, `progress=0`, `step_name="准备生成提示词"`, `created_by=user_id`；支持 repository.read_job 读取与 recoverable_jobs 同步 |
| AC-03 逐节独立启动核心门禁（APP-M2-T126） | 通过 | `test_independent_start_unconfirmed_chapters_do_not_block_confirmed_chapter`：alpha-tech 方案确认，alpha-business 方案未确认；alpha-tech 独立启动成功，未确认章节不产生阻塞；企图启动 alpha-business 时前置强拦截并抛出 `DomainError(409, "PLAN_NOT_CONFIRMED")` |
| AC-04 方案过期指纹失效拦截 | 通过 | `test_start_generation_stale_plan_rejected`：事实取值被修改导致来源指纹不一致时，启动生成被拦截抛出 `DomainError(409, "PLAN_NOT_CONFIRMED")` |
| AC-05 涉密项目本地模型强门禁 | 通过 | `test_sensitive_project_blocks_cloud_model`（敏感项目绑定云端模型拦截抛出 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL）、`test_sensitive_project_allows_local_model`（敏感项目绑定合格本地离线模型正常放行） |
| AC-06 角色权限与多租户隔离 | 通过 | `test_readonly_roles_interception`（只读系统角色 viewer / group_admin 拦截 403）、`test_cross_tenant_isolation`（跨租户访问拦截 404 NOT_FOUND） |
| AC-07 同步执行与候选生成流转 | 通过 | `test_sync_execution_generates_candidate_and_completes_job`：指定 sync_execute=True 触发模型推理与输出校验，任务状态推进至 progress=100, status="completed", 候选保存至 workflow["candidates"] |
| AC-08 统一门面与全局函数委派 | 通过 | `test_workflow_service_delegation`：WorkflowService.start_chapter_generation 与 assemble_writing_prompt_plan 及模块顶层全局函数委派正常 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 写作方案与启动生成专属单测 | `pytest tests/backend/test_outline_generation_start.py -v` | **10 passed, 0 failed** | 0.49s |
| 章节生成与关联套件联合验证 | `pytest tests/backend/test_outline_generation_start.py tests/backend/test_chapter_generation_rag_flow.py tests/backend/test_general_chat_qa.py tests/backend/test_error_idempotency.py tests/backend/test_answer_cards.py tests/backend/test_insert_answer_card.py -v` | **61 passed, 0 failed** | 21.29s |
| OpenAPI 契约与冻结错误码 | `pytest tests/backend/test_error_idempotency.py -v` | **9 passed, 0 failed** | 3.85s |
| 后端全量测试套件回归 | `pytest tests/backend/ -q` | **548 passed, 42 skipped, 0 failed** | 204.80s |

## 签署状态

APP-M2-T124 与 APP-M2-T126 保持 **in-review**，**严禁标 done**。
