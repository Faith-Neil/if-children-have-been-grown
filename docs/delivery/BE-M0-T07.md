为什么有这个文件：记录 operationId 规范化检查与修正确认交付。

它解决什么问题：消除框架自动生成的 `_api_` 冗余前缀与接口命名混乱，使所有 OpenAPI 接口具备规范、全局唯一的 lowerCamelCase operationId，保障前后端 API SDK 生成质量与契约一致性。

# BE-M0-T07：operationId 检查交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-M0-T07 |
| 代码解释 | [BE-M0-T07](../code/BE-M0-T07.md) |
| 验收 | 2026-10-13：运行时 70 个操作与契约全量 72 个操作（含 2 个冻结大纲草案）的 operationId 均规范为 lowerCamelCase，全局唯一，无 `_api_` 冗余前缀和下划线。`tests/backend/test_operation_ids.py` 5 项断言全部通过，后台全量 pytest 回归通过，治理检查通过。本卡标为 in-review，**不标 done** |
| 项目进度 | 任务看板是准绳。本卡从 ready 改为 in-review。看板为 397 项：52 done、23 in-review、7 in-progress、266 planned、48 blocked、1 ready。BE-M0 现为 19 项，10 项 done。ISSUE-005 保持 in-progress，不关闭。T04、T05、T06 与 T07 均为 in-review |
<!-- task-delivery:end -->

## 关联与状态

- 2026-10-13，BE-M0，[ISSUE-005](../../issues/ISSUE-005.md) 卡片 (f)。
- 分支 `codex/repository-foundation`。未合入，未发布。
- 本地验收已做。等待 QA 复核与签署（REV）。等待项目经理设置 done。**严禁私自将任务标 done，严禁私自关闭 ISSUE-005**。

## 完成内容与变更文件

1. **路由显式指定 operation_id**：
   - `backend/bid-core/icg_demo/main.py`：对核心路由、演示登录及租约路由显式指定 `operation_id`（如 `getHealth`, `getIndex`, `listAccounts`, `login`, `acquireChapterLock`, `renewChapterLock`, `releaseChapterLock`, `listProjects`, `createProject`, `listChapters`, `getChapter`, `acquireLegacyLock`, `renewLegacyLock`, `releaseLegacyLock`, `saveDraft`, `discardDraft`, `commitVersion`, `listVersions`, `getAuditTrail`, `suggest`, `checkChapter`, `exportChapter`, `downloadExportFile`）。既有 `getSession` 保持不变。
   - `backend/bid-core/icg_demo/workflow_routes.py`：对工作台、团队、章节分工与方案、文件解析、冲突、检查、分册导出、SLA 与资料库等路由显式指定 `operation_id`（如 `getWorkspace`, `getTeam`, `updateTeam`, `updateChapterAssignment`, `saveChapterPlan`, `confirmChapterPlan`, `getWritingInput`, `patchProject`, `uploadFile`, `deleteFile`, `previewFile`, `getOriginalFile`, `parseFiles`, `patchRequirement`, `patchFact`, `patchConflict`, `confirmParse`, `createPlan`, `generateProject`, `listChecks`, `runCheck`, `exportVolume`, `downloadVolume`, `listJobs`, `listSlaTemplates`, `createSlaTemplate`, `patchSlaTemplate`, `selectSlaTemplate`, `patchSlaValue`, `applySlaTender`, `reviewSlaValue`, `exportSlaCommitment`, `downloadSlaCommitment`, `listLibraryItems`, `createLibraryItem`, `patchLibraryItem`）。
   - 既有已命名的接口保持向后兼容：`startGeneration`, `getJob`, `streamJobEvents`, `cancelJob`, `listSnippetPublications`, `createSnippetPublication`, `getSnippetPublication`, `saveSnippetPublicationDraft`, `publishSnippetPublication`, `syncSnippetPublication`。
   - 冻结大纲草案保持：`getOutlinePlan`, `confirmOutlinePlan`。

2. **OpenAPI 契约文件同步**：
   - 更新 `spec/openapi/demo-v1.json` 中所有操作的 `operationId`，使其与运行时 `app.openapi()` 导出的定义完全同步。
   - 完整保留既有的冻结草案、扩展字段（`x-contract-drafts`, `x-issue-033`, `EvidenceMountFields` 等）和已冻结的 143 个错误码枚举。

3. **新增自动化测试**：
   - 创建 `tests/backend/test_operation_ids.py`：
     - `test_running_app_all_operation_ids_valid_camel_case_and_no_api_prefix`：验证运行态所有 operationId 非空、符合 lowerCamelCase 正则，且无 `_api_` 冗余前缀和下划线。
     - `test_running_app_operation_ids_are_globally_unique`：验证运行态所有 operationId 全局唯一。
     - `test_spec_demo_v1_json_all_operation_ids_valid_and_globally_unique`：验证 `demo-v1.json` 全量契约 operationId 合规且全局唯一。
     - `test_well_known_operation_ids`：断言 `getSession`, `listProjects`, `createProject`, `exportVolume` 等关键操作命名符合预期。
     - `test_implemented_contract_matches_running_schema`：断言 `implemented_contract(spec) == app.openapi()`。

## 代码解释

见 [代码解释](../code/BE-M0-T07.md)。

## 验收结果

- `pytest tests/backend/test_operation_ids.py`：5 passed。
- `pytest tests/backend` 全量测试：通过。
- `node --test tests/frontend/*.test.mjs tests/governance/*.test.cjs`：34 passed。
- `node scripts/check-project-governance.cjs`：治理检查通过。

## 限制与未完成

- **不标 done**：本任务为 in-review，需经 QA 签署与 PM 确认。
- **不关闭 ISSUE-005**：ISSUE-005 聚合门禁保持 in-progress。
- 契约中的大纲计划查询与确认仍为冻结草案（`getOutlinePlan`, `confirmOutlinePlan`），运行时尚未实现。
- 旧 `/api` 错误体与幂等统一留待 BE-M0-T09 / ISSUE-021。
