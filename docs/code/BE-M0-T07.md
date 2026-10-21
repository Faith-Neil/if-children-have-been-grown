为什么有这个文件：说明后端各路由 operationId 的命名规范、配置入口与契约校验方式。

它解决什么问题：消除 FastAPI 框架默认生成的 `_api_` 冗余前缀和长路径拼接名，确保所有 OpenAPI 操作拥有清晰、全局唯一且符合 lowerCamelCase 的 operationId，保持既有契约向后兼容。

# BE-M0-T07：operationId 检查代码说明

## 1. 路由配置入口与命名规范

在 `backend/bid-core/icg_demo/` 中，所有对外暴露的 HTTP 路由均显式指定 `operation_id`，遵循 `lowerCamelCase` 命名规范（正则 `^[a-z][A-Za-z0-9]*$`），严禁包含 `_api_` 冗余前缀或下划线：

1. **核心会话与演示路由（`main.py`）**：
   - `GET /health` -> `getHealth`
   - `GET /` -> `getIndex`
   - `GET /api/demo/accounts` -> `listAccounts`
   - `POST /api/demo/login` -> `login`
   - `GET /api/v1/session` -> 保持 `getSession`（向后兼容）
   - `GET /api/projects` -> `listProjects`
   - `POST /api/projects` -> `createProject`
   - `GET /api/projects/{project_id}/chapters` -> `listChapters`
   - `GET /api/chapters/{chapter_id}` -> `getChapter`
   - `PUT /api/chapters/{chapter_id}/draft` -> `saveDraft`
   - `DELETE /api/chapters/{chapter_id}/draft` -> `discardDraft`
   - `POST /api/chapters/{chapter_id}/versions` -> `commitVersion`
   - `GET /api/chapters/{chapter_id}/versions` -> `listVersions`
   - `GET /api/chapters/{chapter_id}/audit` -> `getAuditTrail`
   - `POST /api/chapters/{chapter_id}/suggestions` -> `suggest`
   - `POST /api/chapters/{chapter_id}/checks` -> `checkChapter`
   - `POST /api/chapters/{chapter_id}/exports` -> `exportChapter`
   - `GET /api/exports/{export_id}/file` -> `downloadExportFile`

2. **v1 编辑租约与旧 /api 区分（`main.py`）**：
   - v1 正式接口：`POST /api/v1/chapters/{chapter_id}/lock` -> `acquireChapterLock`，`/renew` -> `renewChapterLock`，`/release` -> `releaseChapterLock`
   - 旧演示接口：`POST /api/chapters/{chapter_id}/lock` -> `acquireLegacyLock`，`/renew` -> `renewLegacyLock`，`/release` -> `releaseLegacyLock`

3. **工作流与业务路由（`workflow_routes.py`）**：
   - 工作台与团队：`getWorkspace`、`getTeam`、`updateTeam`、`updateChapterAssignment`
   - 方案与写作：`saveChapterPlan`、`confirmChapterPlan`、`getWritingInput`、`patchProject`
   - 文件与解析：`uploadFile`、`deleteFile`、`previewFile`、`getOriginalFile`、`parseFiles`、`confirmParse`
   - 需求与冲突：`patchRequirement`、`patchFact`、`patchConflict`
   - 计划与生成（旧同步）：`createPlan`、`generateProject`
   - 检查与导出：`listChecks`、`runCheck`、`exportVolume`、`downloadVolume`
   - SLA 承诺：`listSlaTemplates`、`createSlaTemplate`、`patchSlaTemplate`、`selectSlaTemplate`、`patchSlaValue`、`applySlaTender`、`reviewSlaValue`、`exportSlaCommitment`、`downloadSlaCommitment`
   - 资料库与任务：`listLibraryItems`、`createLibraryItem`、`patchLibraryItem`、`listJobs`

4. **可恢复任务与片段发布（`recoverable_jobs.py` / `snippet_publication.py`）**：
   - 保持向后兼容已有实现：`startGeneration`、`getJob`、`streamJobEvents`、`cancelJob`、`listSnippetPublications`、`createSnippetPublication`、`getSnippetPublication`、`saveSnippetPublicationDraft`、`publishSnippetPublication`、`syncSnippetPublication`。
   - 冻结大纲草案保持：`getOutlinePlan`、`confirmOutlinePlan`。

## 2. 自动化验证（`tests/backend/test_operation_ids.py`）

新增测试文件覆盖 5 项核心验证：
- `test_running_app_all_operation_ids_valid_camel_case_and_no_api_prefix`：遍历 `create_app().openapi()` 运行时所有路径操作，断言 `operationId` 非空、不含 `_api_`、不含 `_`，并严格匹配 `^[a-z][A-Za-z0-9]*$`。
- `test_running_app_operation_ids_are_globally_unique`：断言运行态所有 operationId 全局唯一无重名。
- `test_spec_demo_v1_json_all_operation_ids_valid_and_globally_unique`：验证 `spec/openapi/demo-v1.json` 全量契约（含冻结草案）所有 operationId 合规且全局唯一（共 72 个操作）。
- `test_well_known_operation_ids`：针对关键接口（`getSession`, `listProjects`, `createProject`, `exportVolume`, `startGeneration`, `getJob`, `streamJobEvents`, `cancelJob` 等）进行显式断言。
- `test_implemented_contract_matches_running_schema`：确保 `implemented_contract(spec)` 与运行时 `app.openapi()` 严格全等。

## 3. 边界与限制

- 本任务未引入任何第三方依赖或额外路由。
- 契约中的冻结草案（`getOutlinePlan`, `confirmOutlinePlan`）与历史扩展注解（`x-contract-drafts`, `x-issue-033`, `EvidenceMountFields` 等）完整保留。
- 开发者严格遵循规范，仅将任务标至 `in-review`，绝不私自标 `done` 或关闭 Issue。
