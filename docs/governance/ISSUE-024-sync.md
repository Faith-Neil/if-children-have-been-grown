为什么有这个文件：核对模型配置存储契约登记时，哪些基线没有改。

它解决什么问题：避免把一次只登记错误码的文档提交写成已经实现了加密或 API。

# ISSUE-024 基线同步记录

日期：2026-10-12。治理版本：g1.1。范围：模型配置的存储与 API。状态 new。负责人 backend。无运行代码。

| 文档 | 本次影响 | 实际处理 | 版本与状态 |
|---|---|---|---|
| PRD.md | 无 | 不改里程碑快照 | 2026-10-12 |
| ROADMAP.md | 无 | 不改里程碑快照 | 2026-10-12 |
| PROJECT_BRIEF.md | 无 | 不改里程碑快照 | 2026-10-12 |
| ARCHITECTURE.md | 无 | 不改正文 | 2026-10-12 |
| TASK_BOARD.md | 无 | 不新增任务，不改计数 | 2026-10-12 |
| PROJECT_STATUS.md | 无 | 不改任务计数 | 2026-10-12 |
| DOCUMENT_INDEX.md | 有 | 登记 ISSUE-024、本同步表和 ISSUE-022 复审记录 | model-config-storage-1 |
| issues/index.md | 有 | 增加 ISSUE-024，状态 new | new |
| issues/ISSUE-024.md | 有 | 新建。冻结 403 与 503 两码 | new |
| issues/ISSUE-028.md | 有 | 改为指向已存在的 ISSUE-024。不改 Provider 字段 | in-review |
| model-config-provider.md | 有 | 删去“不创建 ISSUE-024 文件”。不补回字段表 | in-review |
| spec/openapi/demo-v1.json | 有 | 两码写入 V1Error.code 与 x-error-status。不改 ISSUE-022 操作说明 | 2026-10-12 |
| errors.py | 有 | 冻结表登记两码。运行时仍不返回它们 | 2026-10-12 |
| docs/reference/ | 无 | 不改 | 2026-10-12 |

`SECRET_KEY_UNAVAILABLE` 在 ISSUE-024 的表里标为非瞬时：客户端不得自动重试，服务端不得发送 `Retry-After`。两码已进入 `V1Error.code` 与 `x-error-status`。无 `Retry-After` 的测试留到实现时再加。ISSUE-022 的操作说明未改。

未合入，未发布。不标 closed。`node scripts/check-project-governance.cjs` 通过，输出为「治理检查通过：247 份 Markdown、371 项任务、29 项 Issue。」检查程序未修改。`tests/backend/test_outline_contract_draft.py` 与 `tests/backend/test_error_idempotency.py` 为 13 passed。本提交不改任务状态。
