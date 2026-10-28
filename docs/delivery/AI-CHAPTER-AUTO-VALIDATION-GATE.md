# AI-CHAPTER-AUTO-VALIDATION-GATE 交付报告：章节生成产物合规性自动即时质检门禁

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | AI-CHAPTER-AUTO-VALIDATION-GATE |
| 代码解释 | [docs/code/AI-CHAPTER-AUTO-VALIDATION-GATE.md](../code/AI-CHAPTER-AUTO-VALIDATION-GATE.md) |
| 验收 | 12 项专属自动化测试全绿（12 passed in 2.17s）；全量 AI 核心套件 85 项全绿（85 passed in 13.51s）；OpenAPI 契约零漂移（100% consistent）；工程治理检查通过（零死链） |
| 项目进度 | 本卡已完成全部功能开发与自动化测试闭环，状态转为 in-review，建议由 QA 与 PD 终验后由 PM 标 done |
<!-- task-delivery:end -->

## 1. 交付目标对照

依据任务派发要求与系统规范（PRD MVP v1.8 §5.7.8《章节生成即时合规门禁》、§5.10《合规检查中心与导出门禁》）：
- **目标**：在 `backend/bid-core/icg/domain/chapter_generation.py`、`domain.py`、`generation_orchestrator.py` 与 `backend/bid-core/icg/api/workflow.py` 中，落地大模型章节生成产物合规性自动即时质检门禁引擎（`validate_chapter_candidate` / `validate_chapter_content`），实现生成即质检（Validation on Generation）、阻断与告警分级标定、质量健康度评级与评分量化、修复建议自适应生成、候选草稿与批量流水线全链路注入，以及涉密项目与多租户安全物理隔离。
- **交付要点对照**：
  1. **生成即质检（Validation on Generation）自动触发**：
     - 单章节生成（`start_chapter_generation`）、批量多章节生成（`batch_generate_chapters`）与大纲批量生成流水线（`schedule_batch_pipeline`）在产出候选正文后，无需人工单独点击，自动即时触发多维度合规质量核验；
     - 提供独立可复用的 `validate_chapter_content` 领域方法与按需质检能力。
  2. **R34 占位符与“待补/待完善”残留字样排查（阻断 blocker）**：
     - 正则扫描排查未替换的草稿标记（`【待定】`、`【待补】`、`待补`、`【待完善】`、`待完善`、`【待确认】`、`待确认`、`【占位】`、`占位符`、`TODO`、`TBD`、`FIXME`、`XXXX`、未替换模板变量 `${...}` 及非合法事实的 `{{...}}`）；
     - 排查 AI 对话客套语句残留（如“希望能帮到您”、“作为AI语言模型”、“作为AI大模型”、“以下是为您生成的”、“祝您投标顺利”等）；
     - 检出即标定为阻断缺陷（`code: PLACEHOLDER_RESIDUAL` / `AI_CONVERSATION_RESIDUAL`），禁止带瑕疵正文直接混入提交候选。
  3. **R37 / R28 负偏离与无法满足排查（阻断 blocker）**：
     - 自动检测正文中负偏离违规关键字（“不满足”、“负偏离”、“无法提供”、“存在差距”、“无法满足”、“不符合要求”、“未能达到”、“指标不满足”、“存在负偏离”、“重大负偏离”、“实质性负偏离”、“技术参数低于要求”等）；
     - 检出即标定阻断缺陷（`code: NEGATIVE_DEVIATION_DETECTED`），防范因 AI 自主表述偏离引发实质性废标。
  4. **R24 签字盖章槽位合规排查（阻断 blocker）**：
     - 识别法定承诺与授权证明章节（如“投标函”、“法定代表人身份证明”、“授权委托书”、“签署页”、“签字盖章页”、“承诺书”等）；
     - 排查显式未盖章标记（如“未盖公章”、“未签字”、“（未盖章）”、“印章缺失”等），或法定表单缺少标准公章与签字槽位（如“【公章】”、“【法定代表人签字】”）；
     - 检出即标定阻断缺陷（`code: MANDATORY_SEAL_SIGNATURE_MISSING`）。
  5. **CITATION_AUTH 引用白名单真实性核验（防编造/防幻觉红线）**：
     - 提取行内引用标记 `[证:eid]` 与 `[片:sid]`；
     - 依据章节关联的已确认证据白名单（`allowed_evidence_ids`）校验证据编号，发现未登记或虚构的假证据，立即标定阻断缺陷（`code: FABRICATED_OR_INVALID_EVIDENCE_CITATION`）；
     - 依据知识库匹配切片白名单（`allowed_snippet_ids`）校验切片编号，发现未匹配切片时标定合规警告（`code: UNVERIFIED_SNIPPET_CITATION`）。
  6. **质量健康度评分（0~100）与评级（Health Rating）梯度**：
     - 综合阻断（blocker）与警告（warning）数量执行量化扣分：
       - 0 blocker + 0 warning：100 分，`excellent`（优秀），`validation_passed: True`；
       - 0 blocker + 1 warning：90 分，`excellent`（优秀），`validation_passed: True`；
       - 0 blocker + 2 warning：80 分，`good`（良好），`validation_passed: True`；
       - 0 blocker + >=3 warning：max(50, 100 - warning*10) 分，`warning`（警告）；
       - 1 blocker：55 分，`warning`（警告），`validation_passed: False`，`validation_failed: True`；
       - >=2 blocker：<= 35 分，`critical`（危险），`validation_passed: False`，`validation_failed: True`。
  7. **自适应修复建议（`remediation_suggestions`）**：
     - 根据检出的缺陷代码智能生成针对性改写建议（如占位符清除、负偏离修正、公章签字槽位补全、虚构证据核实等）。
  8. **候选草稿 candidate 元数据与 demo_job 进度注入**：
     - `candidate` 实体直接持久化 `validation_passed`、`validation_failed`、`quality_health_score`、`quality_health_rating`、`detected_blockers`、`detected_warnings`、`remediation_suggestions`、`validation_report`；
     - `demo_job` 异步进度的 `result_json` 注入质检结果与阻断项计数（`blocker_count`）。
  9. **批量流水线 schedule_batch_pipeline 质量看板与汇聚统计**：
     - 各批次章节元数据（`chapters_metadata`）记录逐章即时质检状态；
     - 全局看板持久化汇总 `validation_summary`（`total_validation_passed`、`total_validation_failed`、`total_detected_blockers`、`average_quality_score`）。
  10. **安全隔离门禁（多租户、RBAC 与涉密本地模型）**：
      - 跨租户跨公司访问严格抛出 404 `NOT_FOUND`；
      - 系统只读角色（`viewer`、`auditor`）调用拦截 403 `FORBIDDEN`；
      - 涉密项目拦截云端外部模型，抛出 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`。
  11. **HTTP API 端点集成与 OpenAPI 零漂移**：
      - 注册 `POST /api/v1/projects/{project_id}/chapters/{chapter_id}/validate-candidate`；
      - 使用 `include_in_schema=False`，OpenAPI 契约零漂移（100% consistent）。

---

## 2. 变更代码清单

| 文件路径 | 模块性质 | 职责说明 |
|---|---|---|
| `backend/bid-core/icg/domain/chapter_generation.py` | 核心领域生成服务 | 实现 `validate_chapter_candidate` 核心门禁判定算法、规则正则与关键字检测、质量健康度评分评级、修复建议生成，以及 `ChapterGenerationService.validate_chapter_content` 即时质检服务与模块快捷入口；更新 `start_chapter_generation` 与 `schedule_batch_pipeline` 注入质检元数据与统计看板 |
| `backend/bid-core/icg/domain/domain.py` | 核心领域门面 | 在 `DemoService` 中暴露 `validate_chapter_content` 委托调用 |
| `backend/bid-core/icg/domain/generation_orchestrator.py` | 编排 Mixin | 在 `GenerationOrchestratorMixin` 中暴露 `validate_chapter_content` 方法，供 `WorkflowService` 继承 |
| `backend/bid-core/icg/api/workflow.py` | HTTP API 路由 | 注册 `POST /projects/{project_id}/chapters/{chapter_id}/validate-candidate` 端点（`include_in_schema=False`） |
| `tests/backend/test_ai_chapter_validation_gate.py` | 自动化测试套件 | 新增专属测试套件，全面覆盖清洁正文通过、R34 占位符/AI 对话残留阻断、R37 负偏离阻断、R24 签字盖章槽位阻断、CITATION_AUTH 证据白名单核验、健康度评分评级梯度、生成入库元数据注入、流水线看板聚合、按需质检、多租户隔离、RBAC 门禁、涉密模型硬阻断及 HTTP API 端点共 12 项测试 |

---

## 3. 验收测试与验证证据

### 3.1 专属自动化测试套件

运行命令：
```bash
pytest tests/backend/test_ai_chapter_validation_gate.py -v
```

执行输出结果：
```text
tests/backend/test_ai_chapter_validation_gate.py::test_clean_generated_chapter_passes_validation PASSED [  8%]
tests/backend/test_ai_chapter_validation_gate.py::test_r34_placeholder_residuals_trigger_blocker PASSED [ 16%]
tests/backend/test_ai_chapter_validation_gate.py::test_r37_negative_deviation_triggers_blocker PASSED [ 25%]
tests/backend/test_ai_chapter_validation_gate.py::test_r24_statutory_form_seal_signature_missing PASSED [ 33%]
tests/backend/test_ai_chapter_validation_gate.py::test_citation_auth_fabricated_evidence_and_unverified_snippet PASSED [ 41%]
tests/backend/test_ai_chapter_validation_gate.py::test_quality_health_score_and_rating_gradation PASSED [ 50%]
tests/backend/test_ai_chapter_validation_gate.py::test_start_chapter_generation_integrates_validation PASSED [ 58%]
tests/backend/test_ai_chapter_validation_gate.py::test_batch_pipeline_aggregates_validation_summary PASSED [ 66%]
tests/backend/test_ai_chapter_validation_gate.py::test_service_validate_chapter_content_on_demand PASSED [ 75%]
tests/backend/test_ai_chapter_validation_gate.py::test_multitenant_isolation_and_rbac_gates PASSED [ 83%]
tests/backend/test_ai_chapter_validation_gate.py::test_sensitive_project_local_model_gate PASSED [ 91%]
tests/backend/test_ai_chapter_validation_gate.py::test_http_api_validate_candidate_endpoint PASSED [100%]

============================= 12 passed in 2.17s =============================
```

### 3.2 全量 AI 核心套件联合回归

运行命令：
```bash
pytest tests/backend/test_ai_*.py -q
```

执行输出结果：
```text
85 passed in 13.51s
```
全量 85 项 AI 核心套件全部绿灯，无任何历史用例受损。

### 3.3 OpenAPI 契约零漂移核验

运行命令：
```bash
python backend/bid-core/export_openapi.py --check
```

执行输出结果：
```text
[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.
```

### 3.4 工程治理与超链接检查

运行命令：
```bash
node scripts/check-project-governance.cjs
```
检查结果：零死链、零未索引文档、原子状态双向同步。

---

## 4. 签署与状态流转

根据《合作项目维护约定》签署与状态流转纪律：
- 本卡当前状态：**`in-review`**（AI subagent 最高推进至 `in-review`，严禁自行标 `done`）；
- 建议流转：建议 QA 执行全套复测签署、PD 执行产品功能与规则对照验收，由人类 PM 最终标 `done`。
