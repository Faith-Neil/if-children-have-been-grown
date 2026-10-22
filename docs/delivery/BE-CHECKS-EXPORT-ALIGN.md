为什么有这个文件：记录 BE-CHECKS-EXPORT-ALIGN 检查阻断红线与整本导出快照版式核对的交付事实、测试证据与验收记录。

它解决什么问题：作为质量门禁依据，证明废标红线与星号条款已建立 blocker 判定逻辑、整本正式递交导出 400 CHECK_BLOCKER_EXISTS 强拦截门禁已生效、内部评审稿放行与合规标记正常工作、导出的 64 位 SHA-256 版式指纹与 Word 默认版式元数据完整挂载，并将任务标为 in-review，绝不私自标 done。

# BE-CHECKS-EXPORT-ALIGN：检查阻断红线与整本导出快照版式核对交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-CHECKS-EXPORT-ALIGN |
| 代码解释 | [BE-CHECKS-EXPORT-ALIGN](../code/BE-CHECKS-EXPORT-ALIGN.md) |
| 验收 | 2026-10-22：合规检查成功识别废标红线与关键星号条款未有效响应或缺资质证据的缺陷，严重度准确标记为 blocker；整本导出在 submission 模式下存在 blocker 时强拦截返回 HTTP 400 CHECK_BLOCKER_EXISTS；internal_review 模式放行并标记 has_blockers=True 与合规告警；导出快照成功注入 64 位 SHA-256 版式指纹与 Word 默认版式元数据；专属测试 4 项全绿，回归套件全量通过，OpenAPI 冻结 143 错误码零漂移 |
| 项目进度 | 任务看板是准绳。本卡状态流转为 in-review，严禁私自标 done，等待项目经理复审验收 |
<!-- task-delivery:end -->

## 关联与状态
- **关联 Issue**：[ISSUE-006](../../issues/ISSUE-006.md)、[ISSUE-027](../../issues/ISSUE-027.md)、[ISSUE-005](../../issues/ISSUE-005.md)
- **依赖任务**：BE-CHECKS-EXPORTS-PERSISTENCE、[BE-M0-T15](../tasks/BE-M0.md#be-m0-t15)
- **状态流转**：推进至 `in-review`。严格遵守开发规范，绝不私自将任务看板标为 `done`，绝不私自关闭 Issue。

## 完成内容与变更清单
1. **废标红线与关键星号条款检查强化 (`run_check`)**：
   - 识别 `is_disqualification=True`、`category="disqualification"` 以及文本含“废标”/“否决”的红线条款；
   - 识别 `importance="star"`、`category="star"` 以及文本含“★”/“标星”的关键星号条款；
   - 当上述条款未被有效响应（未映射章节、响应状态未确认、章节正文为空或包含“待补”、或缺少已核验企业资质证据）时，将缺陷的 `severity` 设为 `"blocker"`。普通缺陷设为 `"blocking"`。
2. **整本导出强门禁与内部评审稿放行 (`export`)**：
   - 在 `POST /api/v1/projects/{project_id}/exports` 时，读取当前分册最新检查结果；
   - 若导出模式为 `submission` 且存在 `blocker`，强拦截返回 HTTP 400 与业务错误码 `CHECK_BLOCKER_EXISTS`，严禁带病递交；
   - 若导出模式为 `internal_review` 且存在 `blocker`，允许放行导出以供内部审阅，并在快照中标记 `has_blockers=True` 与合规警示文本 `compliance_notice`。
3. **Word 默认版式元数据与 64 位 SHA-256 指纹注入**：
   - 基于 BE-M0-T15 Word 版式规范，定义 `WORD_DEFAULT_FORMAT_METADATA`（包含 A4 纵向、上下 2.54cm / 左 2.80cm / 右 2.60cm 页边距、仿宋_GB2312 16pt 正文、28pt 行距、560 缇首行缩进、方正小标宋 22pt 大标题、黑体 16pt 一级标题等）；
   - 在生成导出分册与整本文档时，通过标准 SHA-256 算法生成 64 位十六进制内容哈希指纹；
   - 将 `sha256` 与 `format_metadata` 注入至 `documents`、`volumes` 与整本导出记录中。
4. **数据库与适配器阻塞计数对齐**：
   - 强化 `save_check` 中阻塞项统计逻辑，将 `severity in ("blocking", "blocker")` 均计入 `blocking_count`。
5. **OpenAPI 规范与错误码冻结保护**：
   - 同步更新 `spec/openapi/demo-v1.json`，补充 `blocker` 与 `internal_review` 枚举及版式元数据字段；
   - 严格守护 143 个冻结业务错误码名单（`ERROR_STATUS`），未引入任何未冻结错误码，AST 契约测试 100% 通过。

## 变更文件清单
- `backend/bid-core/icg_demo/workflow_schemas.py`: 扩充 `CheckIssue.severity`（支持 blocker）、`ProjectExportRequest.kind`（支持 internal_review）、`ExportVolume` 与 `ProjectExport` 版式及阻断字段。
- `backend/bid-core/icg_demo/workflow.py`: 实现 `CheckBlockerError`、强化 `run_check` 红线判定、整本导出 400 门禁拦截与 Word 默认版式 SHA-256 元数据注入。
- `backend/bid-core/icg_demo/database.py`: 优化 `save_check` 阻塞缺陷计数统计（涵盖 blocker）。
- `backend/bid-core/icg_demo/adapters.py`: 同步对齐内存仓储 `save_check` 阻塞计数。
- `backend/bid-core/icg_demo/main.py`: 重构 `error_response`，使全局路由标准统一为 v1 错误体。
- `spec/openapi/demo-v1.json`: 同步 OpenAPI 契约定义。
- `tests/backend/test_checks_export_blocker_gate.py`: 新增 4 项专属端到端自动化测试。
- `docs/code/BE-CHECKS-EXPORT-ALIGN.md`: 代码说明文档。
- `docs/delivery/BE-CHECKS-EXPORT-ALIGN.md`: 本交付文档。

## 自动化测试与验收结果
- **专属门禁测试**：
  - `pytest tests/backend/test_checks_export_blocker_gate.py`:
    - `test_disqualification_and_star_clauses_yield_blocker_severity` PASSED
    - `test_submission_export_blocked_with_400_when_blocker_exists` PASSED
    - `test_internal_review_export_allowed_with_blocker_flag_and_compliance_notice` PASSED
    - `test_export_contains_64bit_sha256_and_word_default_format_metadata` PASSED
    - **4 passed in 1.48s**
- **错误码与契约回归**：
  - `pytest tests/backend/test_error_idempotency.py tests/backend/test_operation_ids.py tests/backend/test_evidence_mount_contract.py`:
    - **18 passed in 10.42s** (143 错误码基线 100% 保持一致，操作 ID 与已实现路由全匹配)
- **业务主流程回归**：
  - `pytest tests/backend/test_generation_context.py tests/backend/test_reference_flow.py`:
    - **59 passed in 34.23s**
- **治理检查**：
  - `node scripts/check-project-governance.cjs` 通过。

## 限制与未完成事项
- 严格遵循后端开发规范，本卡状态标为 `in-review`，绝不私自标为 `done`。
- 后续待项目经理组织测试与合规团队复审签署后方可关闭。
