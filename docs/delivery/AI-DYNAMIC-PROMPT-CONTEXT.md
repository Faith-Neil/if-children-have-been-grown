# AI-DYNAMIC-PROMPT-CONTEXT 交付报告：自适应 Prompt 动态上下文裁剪与 Token 预算控制

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | AI-DYNAMIC-PROMPT-CONTEXT |
| 代码解释 | [docs/code/AI-DYNAMIC-PROMPT-CONTEXT.md](../code/AI-DYNAMIC-PROMPT-CONTEXT.md) |
| 验收 | 10 项专属自动化测试全绿（10 passed in 1.45s）；全量 AI 与 RAG 联合套件全绿（109 passed, 3 skipped in 102.10s）；OpenAPI 契约一致性 100% 保持；工程治理检查通过（零死链） |
| 项目进度 | 已完成核心能力研发与全量回归测试，提交 in-review，建议由 QA 与 PD 终验签署后由人类 PM 标 done |
<!-- task-delivery:end -->

## 1. 交付目标对照

依据任务派发要求与系统规范（PRD MVP v1.8 §5.7.8《动态上下文裁剪与 Token 预算控制》）：
- **目标**：在 `backend/bid-core/icg/domain/`（`prompt_budget.py` 与 `chapter_generation.py`）中，落地自适应 Prompt 动态上下文裁剪与 Token 预算控制引擎。
- **交付要点对照**：
  1. **Token 预算动态分配策略**：
     - 根据模型上下文窗口（`max_context_tokens`，默认 4096，支持 8192 / 16k / 32k 动态配置）与预留生成空间（默认 1024 token）计算可用 `prompt_budget`；
     - 实现了中英文差异化加权 Token 估算算法（中文字符约 0.7 token，英文单词约 1.3 token，空白/标点约 0.3 token）；
  2. **四级优先级动态自适应裁剪机制**：
     - **Priority 1（最高核心指令，绝对不裁剪）**：角色与生成目标、章节分册目标、得分要点小标题、字数预期、事实约束规范、[证] 引用标记规范。无论总预算多么紧张，P1 核心指令绝不裁剪，保证生成任务不偏离主线；
     - **Priority 2（高优先级事实与成熟方案）**：高置信度方案片段（精确匹配得分 >= 0.70）与项目已确认事实变量清单。空间紧张时优先完整保留，若空间有限允许局部截断并附加清晰截断提示；
     - **Priority 3（中优先级条款与有效证据）**：招标文件条款与响应要求、已关联公司证据清单。超出剩余预算时，自适应舍弃并生成裁剪告警记录；
     - **Priority 4（低优先级参考背景）**：RAGFlow 候选参考切片、低相关度方案片段。预算紧张时自适应优先丢弃；
  3. **不可篡改上下文防伪指纹与 Token 指标**：
     - 基于章节 ID、核心要点、保留切片 ID 列表与项目事实快照计算不可伪造的 16 位 SHA-256 `context_fingerprint`；
     - 输出详尽的 `token_budget_usage` 指标（`max_context_tokens`、`reserved_generation_tokens`、`prompt_budget`、`prompt_tokens`、`remaining_prompt_tokens`、`total_estimated_tokens`、`truncated_items_count`、`priority_breakdown` 与 `truncated_items` 详细条目列表）；
  4. **涉密隔离与防编造红线**：
     - 涉密项目（`sensitive=True`）强制使用本地离线模型配置，企图调用云端模型拦截 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`；
     - 事实变量未对齐或缺失占位符如实记录至 `missing_variables`，杜绝模型幻觉瞎编取值；
  5. **服务层全面集成**：
     - 完整集成入 `assemble_writing_prompt_plan` 与 `ChapterGenerationService.start_chapter_generation`；
     - 异步任务 `demo_job` 与章节生成候选产物 `candidate` 自动记录上下文指纹与 Token 预算消耗指标。

---

## 2. 交付物清单

### 2.1 核心代码
- `backend/bid-core/icg/domain/prompt_budget.py`：自适应 Prompt 动态上下文裁剪与 Token 预算管理器核心实现。包含中英加权 Token 估算器（`estimate_tokens`）、上下文防伪指纹计算器（`compute_context_fingerprint`）、涉密模型门禁（`check_sensitive_model_gate`）、`TokenBudgetUsage` 数据结构与 `DynamicPromptContextManager` 四级优先级裁剪装配引擎；
- `backend/bid-core/icg/domain/chapter_generation.py`：深度集成 Token 预算管理器与上下文指纹，在 `assemble_writing_prompt_plan` 中输出预算统计与指纹，并在 `start_chapter_generation` 中持久化记录至异步任务与候选成果；
- `backend/bid-core/icg/domain/domain.py` 与 `icg/domain/generation_service.py`：在门面方法中扩展转发 `max_context_tokens` 与 `snippet_matches` 动态预算参数；
- `backend/bid-core/icg_demo/prompt_budget.py` 与 `backend/bid-core/icg_demo/snippet_retrieval.py`：向后兼容转接层，保障外部与旧测试引用的零中断兼容。

### 2.2 自动化测试
- `tests/backend/test_ai_prompt_budget.py`：10 项专属自动化测试，覆盖中英文加权 Token 估算、P1 核心极紧预算不裁剪、P4 优先裁剪丢弃、P2 方案片段局部截断提示、Token 统计结构完整性、不可篡改上下文指纹唯一性、缺失变量识别防幻觉、敏感项目云端模型阻断、端到端写作计划组装完整性、以及启动生成任务/候选成果指纹与预算落盘。

---

## 3. 验证命令与结果

### 3.1 专属自动化测试套件
```powershell
pytest tests/backend/test_ai_prompt_budget.py -v
```
**运行结果**：
```text
tests/backend/test_ai_prompt_budget.py::test_token_estimation_chinese_and_english_weighted PASSED [ 10%]
tests/backend/test_ai_prompt_budget.py::test_priority_1_core_never_truncated_under_tight_budget PASSED [ 20%]
tests/backend/test_ai_prompt_budget.py::test_priority_adaptive_truncation_p4_dropped_first PASSED [ 30%]
tests/backend/test_ai_prompt_budget.py::test_priority_2_snippet_partial_truncation PASSED [ 40%]
tests/backend/test_ai_prompt_budget.py::test_token_budget_usage_statistics_accuracy PASSED [ 50%]
tests/backend/test_ai_prompt_budget.py::test_context_fingerprint_deterministic_and_tamper_evident PASSED [ 60%]
tests/backend/test_ai_prompt_budget.py::test_missing_variables_detected_without_hallucination PASSED [ 70%]
tests/backend/test_ai_prompt_budget.py::test_sensitive_project_blocks_cloud_model PASSED [ 80%]
tests/backend/test_ai_prompt_budget.py::test_assemble_writing_prompt_plan_end_to_end_integration PASSED [ 90%]
tests/backend/test_ai_prompt_budget.py::test_start_chapter_generation_records_budget_and_fingerprint PASSED [100%]

============================= 10 passed in 1.45s ==============================
```

### 3.2 全量 AI 与 RAG 联合测试回归
```powershell
pytest tests/backend/test_fake_ragflow.py tests/backend/test_ragflow_client.py tests/backend/test_ragflow_config_api.py tests/backend/test_ragflow_kb_sync.py tests/backend/test_chapter_generation_rag_flow.py tests/backend/test_ai_compliance_cross_check.py tests/backend/test_editor_ai_context.py tests/backend/test_ai_snippet_retrieval.py tests/backend/test_ai_prompt_budget.py tests/backend/test_outline_generation_start.py -v
```
**运行结果**：
```text
================= 109 passed, 3 skipped in 102.10s (0:01:42) ==================
```

### 3.3 OpenAPI 契约一致性校验
```powershell
python backend/bid-core/export_openapi.py --check
```
**运行结果**：
```text
[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.
```

### 3.4 工程治理一致性检查
```powershell
node scripts/check-project-governance.cjs
```
**运行结果**：
```text
治理检查通过：无死链，文档与任务卡严格对齐。
```

---

## 4. 签署建议

本卡已严格实现 PRD MVP v1.8 §5.7.8 自适应 Prompt 动态上下文裁剪与 Token 预算控制规范。专属测试 10 项全绿，全量 AI 测试 109 passed 全绿，OpenAPI 契约零漂移，多租户隔离与涉密门禁完备。
**状态建议**：在 `TASK_BOARD.md` 与 `AI-M0.md` 中标记为 `in-review`，建议由 QA 终验签署与 PD 产品核准后，由人类 PM 标 `done`。
