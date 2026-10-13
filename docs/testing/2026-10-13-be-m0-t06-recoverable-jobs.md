为什么有这个文件：记录可恢复生成任务这次本地核对的命令和结果。

它解决什么问题：把 202、断线查询、取消和失败的证据留在仓库里，而不是只写“已联调”。

# BE-M0-T06 核对

日期：2026-10-13。任务 [BE-M0-T06](../tasks/BE-M0.md#be-m0-t06)。未设 `ICG_DATABASE_URL` 与 `ICG_REQUIRE_MYSQL`。

## 行为

`tests/backend/test_recoverable_jobs.py` 覆盖：

- 启动返回 202，`Location` 指向该任务，重放保持同一个 id。
- 同步 `POST /generate` 不是 202，任务列表不含这条可恢复任务。
- 查询把排队任务推进到 `completed`，SSE 的 `Last-Event-ID` 跳过已发送序号。
- 其他公司查询返回 404 `NOT_FOUND`。
- 取消为 `cancelled`，再次用新键取消已结束任务为 409 `VERSION_CONFLICT`。
- 模型调用抛错时状态为 `failed`，`error_code` 为 `MODEL_UNAVAILABLE`。
- 缺少幂等键、缺少 If-Match、版本不符、非分册负责人、锁占用、过期方案、模型不可用、主密钥不可用和敏感项目云端适配器，都使用已有错误码。

## 结果

未设 `ICG_DATABASE_URL` 与 `ICG_REQUIRE_MYSQL` 时，`python3 -m pytest tests/backend -q --tb=line` 为 386 passed、13 skipped。其中一条警告是 StarletteDeprecationWarning，sqlite 日期适配器另有 DeprecationWarning，都不记失败。`node scripts/check-project-governance.cjs` 通过：333 份 Markdown、393 项任务、36 项 Issue。ISSUE-005 仍为 in-progress。BE-M0-T06 为 in-review。T04 与 T05 仍为 in-review，本轮没有改它们的交付。T07 仍为 ready。

本环境没有把 MySQL 标记当作通过条件。未设置连接串时单元测试使用内存仓库。
