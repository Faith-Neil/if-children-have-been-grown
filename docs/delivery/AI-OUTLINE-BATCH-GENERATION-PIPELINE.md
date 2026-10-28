# AI-OUTLINE-BATCH-GENERATION-PIPELINE 交付报告：基于优先级推荐队列的大纲多章节批量生成流水线调度引擎

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | AI-OUTLINE-BATCH-GENERATION-PIPELINE |
| 代码解释 | [docs/code/AI-OUTLINE-BATCH-GENERATION-PIPELINE.md](../code/AI-OUTLINE-BATCH-GENERATION-PIPELINE.md) |
| 验收 | 9 项专属自动化测试全绿（9 passed in 3.21s）；大纲与核心 AI 测试 73 项全绿（73 passed in 12.15s）；OpenAPI 契约零漂移（100% consistent）；工程治理检查通过（零死链） |
| 项目进度 | 本卡已完成全部功能开发与全量测试闭环，状态转为 in-review，建议由 QA 与 PD 终验后由 PM 标 done |
<!-- task-delivery:end -->

## 1. 交付目标对照

依据任务派发要求与系统规范（PRD MVP v1.8 §5.7.1《生成闭环总览》、§5.7.8《批量生成编排》）：
- **目标**：在 `backend/bid-core/icg/domain/chapter_generation.py`、`domain.py`、`generation_orchestrator.py` 与 `backend/bid-core/icg/api/workflow.py` 中，落地基于优先级推荐队列的大纲多章节批量生成流水线调度引擎（`schedule_batch_pipeline`），实现多章节并发受控切片、废标红线与星标必保优先调度、未确认章节隔离不阻塞、全局 Token 预算聚合与多租户/涉密模型物理隔离硬门禁。
- **交付要点对照**：
  1. **优先级推荐队列自适应排序与调度**：
     - 依据前序 `calculate_score_weights_and_priorities` 计算得出的大纲评分项权重与推荐编写序列（`recommended_writing_order`），自动按 `(-priority_score, -total_score, section_number)` 倒序排序；
     - 确保 `critical` 紧急关键章节（一票否决废标条款 bonus 100 与 ★关键必保条款 bonus 60）优先编入前置批次执行，次之 `high` 高分核心章节（分值 >= 15分），再次 `medium`（分值 >= 5分）与 `low`（基础支撑常规履约）；
     - 支持动态元数据回退：若工作流中未提前持久化 `recommended_writing_order`，自动提取项目条款动态推导章节权重与优先级元数据。
  2. **并发门限受控切片（Concurrency Controlled Batch Slicing）**：
     - 严格受控于 `concurrency_limit: int = 2`（支持 1~5 钳制，默认 2），将待生成章节列表自适应切分为按阶段推进的批次（`Stage 1 (Batch 1)`、`Stage 2 (Batch 2)`...）；
     - 严格防止本地私有大模型瞬时高并发导致显存崩溃（VRAM OOM）或 Token 预算枯竭。
  3. **PRD §5.7.8 关键红线：未确认章节与单章失败绝对不阻塞后续生成**：
     - 若章节写作方案未确认（`PLAN_NOT_CONFIRMED`）或方案指纹过期（`plan_is_current` 为 False），自动隔离跳过并记录至 `skipped_unconfirmed_chapters`（记录 `reason: "PLAN_NOT_CONFIRMED", status: "skipped"`）；
     - 坚决保障流水线正常推进，绝不允许未确认章节或偶发单章失败阻塞后续已确认章节的批量生成调度与执行；
     - 流水线状态语义明确：全数成功标定 `completed`，部分跳过/失败但有成功标定 `partial_completed`，全数未执行/失败标定 `failed`。
  4. **优先级门限过滤（`priority_threshold`）**：
     - 支持传入 `critical`、`high`、`medium`、`low` 门限参数，仅调度达到指定优先级及以上的章节，支持紧急抢工与分阶段生成策略。
  5. **全局 Token 预算仪表盘与执行耗时聚合**：
     - 汇聚各批次任务状态、单章耗时与流水线总耗时 `duration_ms`；
     - 自动聚合全局 Token 消耗仪表盘 `token_budget_dashboard`：`total_prompt_tokens`、`total_completion_tokens`、`total_tokens`、`max_context_tokens_limit`、`average_prompt_tokens_per_chapter` 及单章细粒度消耗映射 `by_chapter`；
     - 输出 `priority_execution_summary` 优先级分层执行分布统计（critical/high/medium/low 的计划、成功与失败计数）。
  6. **单事务原子落盘持久化**：
     - 流水线执行快照原子写入项目工作流 `workflow["batch_pipeline_runs"]` 与 `workflow["latest_batch_pipeline_run"]`，便于前端工作台看板展示与恢复任务追踪。
  7. **多租户强隔离与 RBAC 权限门禁**：
     - 跨企业租户调用流水线严格拦截并抛出 404 `NOT_FOUND`；
     - 系统只读角色（`viewer`、`auditor`）及项目只读成员拦截 403 `FORBIDDEN` / `PROJECT_WRITER_REQUIRED`。
  8. **涉密项目本地模型硬门禁（Airgap Boundary）**：
     - 涉密项目（`project.sensitive = True`）前置校验模型提供方，企图使用外部云端大模型时严格拦截 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`；
     - 只有内网私有化本地模型（`is_local=True`）方可放行。
  9. **HTTP API 端点集成与 OpenAPI 零漂移**：
     - 暴露 `POST /api/v1/projects/{project_id}/outline/batch-pipeline`；
     - 配置 `include_in_schema=False`，OpenAPI 契约零漂移（100% consistent）。

---

## 2. 变更代码清单

| 文件路径 | 模块性质 | 职责说明 |
|---|---|---|
| `backend/bid-core/icg/domain/chapter_generation.py` | 核心领域生成服务 | 实现 `ChapterGenerationService.schedule_batch_pipeline` 流水线调度引擎，提供优先级队列排序、并发批次切片、未确认章节隔离跳过、Token 消耗聚合与原子落盘，并提供模块顶级入口函数 |
| `backend/bid-core/icg/domain/domain.py` | 核心领域门面 | 在 `DemoService` 中暴露 `schedule_batch_pipeline` 委托调用 |
| `backend/bid-core/icg/domain/generation_orchestrator.py` | 编排 Mixin | 在 `GenerationOrchestratorMixin` 中暴露 `schedule_batch_pipeline` 方法，供 `WorkflowService` 多重继承复用 |
| `backend/bid-core/icg/api/workflow.py` | HTTP API 路由 | 注册 `POST /projects/{project_id}/outline/batch-pipeline` 端点（`include_in_schema=False`） |
| `tests/backend/test_ai_outline_batch_pipeline.py` | 自动化测试套件 | 新增专属测试套件，覆盖并发切片、优先级排序、PRD §5.7.8 未确认不阻塞、门限过滤、Token 仪表盘、多租户隔离、RBAC 门禁、涉密模型硬阻断及 HTTP 端点共 9 项测试 |

---

## 3. 验收测试与验证证据

### 3.1 专属自动化测试套件

运行命令：
```bash
pytest tests/backend/test_ai_outline_batch_pipeline.py -v
```

执行输出结果：
```text
tests/backend/test_ai_outline_batch_pipeline.py::test_batch_pipeline_priority_sorting_and_slicing PASSED [ 11%]
tests/backend/test_ai_outline_batch_pipeline.py::test_batch_pipeline_unconfirmed_chapter_non_blocking PASSED [ 22%]
tests/backend/test_ai_outline_batch_pipeline.py::test_batch_pipeline_priority_threshold_filtering PASSED [ 33%]
tests/backend/test_ai_outline_batch_pipeline.py::test_batch_pipeline_token_budget_and_metrics_aggregation PASSED [ 44%]
tests/backend/test_ai_outline_batch_pipeline.py::test_batch_pipeline_concurrency_limit_boundaries PASSED [ 55%]
tests/backend/test_ai_outline_batch_pipeline.py::test_batch_pipeline_multi_tenant_isolation PASSED [ 66%]
tests/backend/test_ai_outline_batch_pipeline.py::test_batch_pipeline_rbac_permission_gate PASSED [ 77%]
tests/backend/test_ai_outline_batch_pipeline.py::test_batch_pipeline_sensitive_project_local_model_gate PASSED [ 88%]
tests/backend/test_ai_outline_batch_pipeline.py::test_batch_pipeline_http_api_endpoint PASSED [100%]

============================== 9 passed in 3.21s ==============================
```

### 3.2 全量 AI 与大纲核心回归测试

运行命令：
```bash
pytest tests/backend/test_ai_outline_batch_pipeline.py tests/backend/test_ai_outline_score_weight.py tests/backend/test_ai_outline_generation_expand.py tests/backend/test_ai_outline_auto_tree_build.py tests/backend/test_ai_prompt_budget.py tests/backend/test_ai_snippet_retrieval.py tests/backend/test_ai_compliance_cross_check.py -q
```

执行输出结果：
```text
73 passed in 12.15s
```

### 3.3 OpenAPI 契约零漂移核验

运行命令：
```bash
python backend/bid-core/export_openapi.py --check
```

执行输出结果：
```text
[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.
```

---

## 4. 签署与状态流转

- **当前状态**：`in-review`（严格遵守各 subagent 最高只推至 `in-review` 纪律，严禁自行标 `done`）。
- **建议**：建议 QA 与 PD 角色核查上述 9 项专属自动化测试、73 项全量 AI 核心套件回归、OpenAPI 零漂移证据，确认满足 PRD MVP v1.8 §5.7.8 验收准则后，书面建议 PM 标 `done`。
