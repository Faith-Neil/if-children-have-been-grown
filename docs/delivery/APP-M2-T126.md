# 为什么有这个文件：记录 APP-M2-T124 / APP-M2-T126 写作方案组装与逐节确认启动生成功能闭环的交付成果、测试证据与验收结论。
# 它解决什么问题：汇总写作方案 Prompt 输入组装、逐节确认独立启动生成核心门禁、异步任务生命周期与 JobProgress 对接、敏感项目本地模型隔离门禁及全量回归验证，供主 Agent 与 QA 团队复核验收。

# APP-M2-T126 写作方案组装与逐节确认启动生成交付报告

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务目标 | APP-M2-T124 / APP-M2-T126 · 写作方案组装与逐节确认启动生成 |
| 关联 Issue | [ISSUE-007](../../issues/ISSUE-007.md)、[ISSUE-022](../../issues/ISSUE-022.md) |
| 规范出处 | [PRD v1.8 §5.7.2、§5.7.8](../../docs/reference/product/prd-mvp-v1.8.md)、数据字典 v1.9 §4.16 |
| 代码说明 | [APP-M2-T126 代码解释](../code/APP-M2-T126.md) |
| 核心业务代码 | `backend/bid-core/icg_demo/chapter_generation.py`、`backend/bid-core/icg_demo/domain.py`、`backend/bid-core/icg_demo/workflow.py` |
| 专属测试套件 | `tests/backend/test_outline_generation_start.py`（10 项全部通过） |
| 联合验证套件 | `test_outline_generation_start.py` + `test_chapter_generation_rag_flow.py` + `test_general_chat_qa.py` + `test_error_idempotency.py` + `test_answer_cards.py` + `test_insert_answer_card.py`（61 项全部通过） |
| 离线纯洁性 | 100% 离线测试，无任何外部网络外呼，假服务与内存仓库安全闭环 |
| 当前状态 | in-review（待主 Agent / QA 复核，绝不私自标 done，绝不私自关闭 Issue） |
<!-- task-delivery:end -->

---

## 1. 核心交付内容清单

1. **写作方案输入上下文组装（APP-M2-T124）**：
   - 提取各章节得分要点小标题（`writing_points`）作为大纲写作指导；
   - 绑定已关联的公司证据条目，按格式带 `[证]` 标签、证据名称、编号、记录版本 `revision`、有效期及核心内容摘要；
   - 包含 RAGFlow 检索候选切片，带 `[片]` 标签并注明 `chunk_id` 与 `document_id` 溯源出处及不可附着提示；
   - 注入项目已确认事实要点及 SLA 变量，保持 `{{fact:ID}}` 与 `{{sla:KEY}}` 变量标记；
   - 明确字数预期（`target_length`）；
   - 包含严正的事实约束（正文引用事实必须保留变量，严禁私自篡改来源取值）及 `[证]` 引用标记规范。

2. **逐节确认独立启动生成（APP-M2-T126）**：
   - 落地核心入口：`start_chapter_generation(project_id, chapter_id, principal)`；
   - **逐节独立启动原则**：按逐节确认结果独立启动已确认章节的生成任务，未确认分册或未确认章节**绝对不阻塞**已确认章节的独立启动；
   - **未确认前置拦截**：企图启动未确认方案或方案过期的章节时，前置强行拦截并抛出标准的 `PLAN_NOT_CONFIRMED`；
   - **权限守卫**：集团管理员、审计员、查看人等系统只读角色或无权编写人员企图启动生成时拦截抛出 `403 FORBIDDEN` / `PROJECT_WRITER_REQUIRED`；
   - **多租户隔离**：跨公司租户或不存在的项目/章节强隔离抛出 `404 NOT_FOUND`。

3. **敏感项目本地模型强门禁**：
   - 若项目为涉密/敏感项目（`project.sensitive=True` 或 `project.is_sensitive=True`）：
   - 强制核验绑定的模型配置（或公司默认配置），必须为本地离线模型（`is_local=True` 且 `allow_sensitive=True`）；
   - 企图使用云端或非本地模型时，前置拦截并抛出标准的 `403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`。

4. **异步任务生命周期与 JobProgress 对接**：
   - 启动生成后在 `demo_job` 中创建异步任务（`job_type="generate_chapter"`, `status="running"`, `progress=0`, `step_name="准备生成提示词"`）；
   - 随上下文组装与模型推理推进流转（progress -> 25 -> 60 -> 100 completed）；
   - 任务类型与状态严格契合前端 `JobProgress`（AI 模型与智能生成类任务专属紫色 `#722ed1`）状态机规范；
   - 同步映射并持久化于 `repository.save_job`、`state.jobs` 与 `state.recoverable_jobs`。

5. **统一门面委派**：
   - 在 `WorkflowService` 与 `DemoService` 顶层统一暴露 `start_chapter_generation` 与 `assemble_writing_prompt_plan`，同时提供模块级快捷入口 `start_chapter_generation`。

---

## 2. 变更文件清单

- **业务核心逻辑**：
  - `backend/bid-core/icg_demo/chapter_generation.py`：新建章节写作计划组装与按逐节确认结果启动生成核心服务模块。
  - `backend/bid-core/icg_demo/domain.py`：在 `DemoService` 挂载 `ChapterGenerationService` 并暴露统一方法。
  - `backend/bid-core/icg_demo/workflow.py`：在 `WorkflowService` 暴露 `start_chapter_generation` 与 `assemble_writing_prompt_plan` 门面委派。
- **专属测试套件**：
  - `tests/backend/test_outline_generation_start.py`：新建 10 项全方位单元测试用例，覆盖写作方案组装、逐节确认启动、未确认拦截、敏感项目门禁、只读权限拦截、跨租户与同步执行流转。
- **交付与设计文档**：
  - `docs/code/APP-M2-T126.md`：代码实现机制、门禁流转与契约映射文档。
  - `docs/delivery/APP-M2-T126.md`：本交付验收报告。
  - `docs/testing/2026-10-22-app-m2-t126-qa-signoff.md`：独立 QA 签署复验报告。

---

## 3. 验收测试执行证据

### 3.1 专属单元测试（10 项全部通过）

```bash
pytest tests/backend/test_outline_generation_start.py -v
```

实测输出：
```
tests/backend/test_outline_generation_start.py::test_assemble_writing_prompt_plan_context_complete PASSED [ 10%]
tests/backend/test_outline_generation_start.py::test_start_chapter_generation_success_creates_job PASSED [ 20%]
tests/backend/test_outline_generation_start.py::test_independent_start_unconfirmed_chapters_do_not_block_confirmed_chapter PASSED [ 30%]
tests/backend/test_outline_generation_start.py::test_start_generation_stale_plan_rejected PASSED [ 40%]
tests/backend/test_outline_generation_start.py::test_sensitive_project_blocks_cloud_model PASSED [ 50%]
tests/backend/test_outline_generation_start.py::test_sensitive_project_allows_local_model PASSED [ 60%]
tests/backend/test_outline_generation_start.py::test_readonly_roles_interception PASSED [ 70%]
tests/backend/test_outline_generation_start.py::test_cross_tenant_isolation PASSED [ 80%]
tests/backend/test_outline_generation_start.py::test_sync_execution_generates_candidate_and_completes_job PASSED [ 90%]
tests/backend/test_outline_generation_start.py::test_workflow_service_delegation PASSED [100%]

============================= 10 passed in 0.49s ==============================
```

### 3.2 章节生成与关联套件联合验证（61 项全部通过）

```bash
pytest tests/backend/test_outline_generation_start.py tests/backend/test_chapter_generation_rag_flow.py tests/backend/test_general_chat_qa.py tests/backend/test_error_idempotency.py tests/backend/test_answer_cards.py tests/backend/test_insert_answer_card.py -v
```

实测输出：
```
============================= 61 passed in 21.29s =============================
```

### 3.3 契约与冻结错误码一致性

- 运行 `pytest tests/backend/test_error_idempotency.py`：**9 passed, 0 failed**。
- `spec/openapi/demo-v1.json` 保持严格冻结状态，零动态路径污染。

---

## 4. 边界与限制说明

1. 逐节启动生成严格遵循逐节确认逻辑：只有写作方案已确认且来源未过期的章节可独立启动；未确认章节绝对不影响已确认章节的启动执行；
2. 敏感项目必须显式绑定本地模型配置或在公司默认模型配置中启用 `is_local=True` 与 `allow_sensitive=True`；
3. 状态标记为 **in-review**，严格等待主 Agent 与 QA 团队确认，绝不私自标记为 done，绝不私自关闭相关 Issue。
