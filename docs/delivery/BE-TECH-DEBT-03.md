# 任务交付：workflow_orchestrator 巨石解耦与领域子编排服务细化（BE-TECH-DEBT-03）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-TECH-DEBT-03 |
| 代码解释 | [workflow_orchestrator 巨石解耦与领域子编排代码说明](../code/BE-TECH-DEBT-03.md) |
| 文档登记 | [D-782](../DOCUMENT_INDEX.md) |
| 验收 | 1. 架构解耦达标：`backend/bid-core/icg/domain/workflow_orchestrator.py` 从原 983 行巨石彻底解耦重构为 **330 行** 高内聚门面（Façade），行数严格控制在 **350 行** 阈值以内；<br>2. 领域子编排服务独立抽离：按 DDD 限界上下文抽离 `outline_orchestrator.py`（大纲树构建、章节编号规范化、大纲定稿就绪检查）、`generation_orchestrator.py`（章节生成任务创建、提示词预算管理集成 `DynamicPromptContextManager`、敏感项目本地模型门禁、生成候选归档）、`check_orchestrator.py`（全规则引擎调用 `ComplianceRulesEngine.evaluate_all`、增量复检队列管理 `schedule_incremental_recheck`、阻断缺陷汇总 `aggregate_blockers` 与 `CheckBlockerError` 门禁）、`tender_orchestrator.py`（招标文件上传/预览/删除、文字解析提取、事实冲突消解、解析确认）、`library_orchestrator.py`（企业知识库/资质库 ACL 鉴权与受限资料校验、长任务脱敏管理）；<br>3. 兼容门面平滑代理：`outline_service.py`、`generation_service.py` 与 `export_service.py` 转化为薄兼容继承门面，所有既有类、方法签名与返回值 100% 保持向后兼容；<br>4. 自动化测试 100% 全绿：专属测试 `tests/backend/test_workflow_orchestrator_modular.py`（6 passed），核心回归套件 `test_compliance_rules_p3.py`、`test_checks_export_blocker_gate.py`、`test_reference_flow.py`、`test_ai_prompt_budget.py`、`test_accept_ai_suggestion.py` 全部 55 passed，零失败；<br>5. OpenAPI 契约零漂移：运行 `python backend/bid-core/export_openapi.py --check` 输出 100% 一致；<br>6. 工程治理检查通过：运行 `node scripts/check-project-governance.cjs` 与 `node --test tests/governance/*.test.cjs` 全部绿灯。 |
| 项目进度 | 本卡已完成全部解耦实施与全套测试验证，状态推至 in-review，建议 PM 标 done |
<!-- task-delivery:end -->

## 1. 任务背景与目标

根据架构质量治理规范与 `AGENTS.md` 对后端核心域模块化约束，原 `backend/bid-core/icg/domain/workflow_orchestrator.py`（由原巨石 `workflow.py` 迁入）代码量高达 983 行，违背了单一职责原则。该文件长期混杂了：
1. 大纲树构建、章节增删改查、编号规范化与定稿就绪检查；
2. 章节生成任务创建、AI 伴写、提示词预算调度与生成候选归档；
3. 合规规则引擎评估、废标/星号条款阻断判定与增量复检队列管理；
4. 招标文件上传、解析提取、响应矩阵条款维护与事实冲突消解；
5. 企业资质库 ACL 鉴权、协议挂接校验与长任务脱敏视图。

### 本任务核心目标：
- 严格遵循上下文分包架构，在 `backend/bid-core/icg/domain/` 下抽离出内聚的领域子编排服务；
- 将 `WorkflowService` 单文件行数压缩至 **350 行以内**（实测达到 **330 行**），作为高内聚薄门面；
- 保持所有既有接口、方法签名及调用链 100% 向后兼容；
- 编写专项测试套件 `test_workflow_orchestrator_modular.py` 覆盖行数硬门禁、各子编排器独立挂载、大纲树构建、Prompt 预算计划与合规阻断汇总；
- 确保全量自动化回归测试通过，OpenAPI 契约零漂移。

---

## 2. 架构拆解与文件职责清单

| 模块文件 | 类型 | 职责说明 |
|---|---|---|
| `backend/bid-core/icg/domain/outline_orchestrator.py` | 新增 | 大纲领域子编排服务：`OutlineOrchestratorMixin` 与 `OutlineOrchestrator`。实现大纲树构建 `build_outline_tree`、章节序号规范化、大纲计划确认、章节增删改及大纲定稿就绪检查 `check_outline_finalization_readiness`。 |
| `backend/bid-core/icg/domain/generation_orchestrator.py` | 新增 | 章节生成领域子编排服务：`GenerationOrchestratorMixin` 与 `GenerationOrchestrator`。实现写作提示词预算组装 `assemble_writing_prompt_plan`（集成 `DynamicPromptContextManager`）、敏感项目本地模型硬门禁 `check_sensitive_model_gate`、章节生成任务创建 `start_chapter_generation`、候选结果归档与 AI 伴写。 |
| `backend/bid-core/icg/domain/check_orchestrator.py` | 新增 | 合规检查领域子编排服务：`CheckOrchestratorMixin` 与 `CheckOrchestrator`。实现全量规则引擎评估 `ComplianceRulesEngine.evaluate_all`、阻断缺陷汇总 `aggregate_blockers`、废标/星号条款门禁 `CheckBlockerError`、增量复检队列管理 `schedule_incremental_recheck`。 |
| `backend/bid-core/icg/domain/tender_orchestrator.py` | 新增 | 招标文件与响应矩阵子编排服务：`TenderOrchestratorMixin` 与 `TenderOrchestrator`。实现招标文件上传、预览、删除、文字解析提取、响应矩阵条款维护、事实冲突消解与解析确认。 |
| `backend/bid-core/icg/domain/library_orchestrator.py` | 新增 | 企业知识库与后台任务子编排服务：`LibraryOrchestratorMixin` 与 `LibraryOrchestrator`。实现企业资料库列表查询、维护与重新确认、ACL 权限鉴权与合作方协议挂接校验、后台异步任务脱敏视图。 |
| `backend/bid-core/icg/domain/workflow_orchestrator.py` | 重构 | 工作流统一门面：继承上述各 Mixin，代码行数由 983 行精简至 **330 行**，保留乐观锁、事务隔离 `_write`、前置校验 `_preflight` 与工作区汇总 `workspace`。 |
| `backend/bid-core/icg/domain/outline_service.py` | 适配 | 兼容门面：继承 `OutlineOrchestratorMixin` 与 `OutlineOrchestrator`，保持导入零断裂。 |
| `backend/bid-core/icg/domain/generation_service.py` | 适配 | 兼容门面：继承 `GenerationOrchestratorMixin` 与 `GenerationOrchestrator`，保持导入零断裂。 |
| `backend/bid-core/icg/domain/export_service.py` | 适配 | 兼容门面：继承 `CheckOrchestratorMixin`，保持 `CheckBlockerError` 与导出方法向下兼容。 |
| `backend/bid-core/icg/domain/__init__.py` | 更新 | 集中导出各领域子编排器及其 Mixin。 |
| `backend/bid-core/icg/domain/workflow.py` | 更新 | 向下兼容导出各领域子编排器及其 Mixin。 |
| `tests/backend/test_workflow_orchestrator_modular.py` | 新增 | 专项单元测试：覆盖代码行数 <= 350、子编排器挂载与委托、大纲树与定稿就绪、提示词预算计划组装、合规阻断汇总与复检队列。 |

---

## 3. 测试验证与质量证据

### 3.1 专属模块化单元测试

```bash
pytest tests/backend/test_workflow_orchestrator_modular.py -v
```
测试结果：
```
tests/backend/test_workflow_orchestrator_modular.py::test_workflow_orchestrator_line_count PASSED [ 16%]
tests/backend/test_workflow_orchestrator_modular.py::test_sub_orchestrators_mounted PASSED [ 33%]
tests/backend/test_workflow_orchestrator_modular.py::test_outline_orchestrator_tree_and_readiness PASSED [ 50%]
tests/backend/test_workflow_orchestrator_modular.py::test_generation_orchestrator_prompt_plan_and_candidate PASSED [ 66%]
tests/backend/test_workflow_orchestrator_modular.py::test_check_orchestrator_and_blocker_aggregation PASSED [ 83%]
tests/backend/test_workflow_orchestrator_modular.py::test_backward_compatibility_facades PASSED [100%]
============================== 6 passed in 0.84s ==============================
```

### 3.2 关联回归测试套件（55 passed）

```bash
pytest tests/backend/test_workflow_orchestrator_modular.py tests/backend/test_compliance_rules_p3.py tests/backend/test_checks_export_blocker_gate.py tests/backend/test_reference_flow.py tests/backend/test_ai_prompt_budget.py tests/backend/test_accept_ai_suggestion.py -v
```
测试结果：
`55 passed in 39.07s`，全量绿灯，无任何功能回退或断裂。

### 3.3 OpenAPI 契约一致性校验

```bash
python backend/bid-core/export_openapi.py --check
```
输出：
`[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.`

### 3.4 工程治理核验

```bash
node scripts/check-project-governance.cjs
node --test tests/governance/*.test.cjs
```
输出：
- 治理检查通过：572 份 Markdown、422 项任务、38 项 Issue。
- 12 passed, 0 fail。

---

## 4. 交付总结

`BE-TECH-DEBT-03` 彻底解决了后端核心域 `workflow_orchestrator.py` 的巨石债务问题，将 983 行巨石精简拆解为 5 大领域子编排服务，主门面代码量严格控制在 330 行（目标 <= 350 行）。所有子服务既可独立作为上下文组件使用，也可经由 `WorkflowService` 门面调用。全量测试与契约校验 100% 通过，现提交至 `in-review`，建议人类 PM 标 done。
