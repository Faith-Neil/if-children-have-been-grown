为什么有这个文件：记录幂等回执和登录会话入库这张卡实际交了什么。

它解决什么问题：把跨进程重放、重启后仍在，以及迁移能降回基线再升回来，和尚未入库的租约分开。

# BE-M0-T11：幂等回执与登录会话入库交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-M0-T11 |
| 代码解释 | [BE-M0-T11](../code/BE-M0-T11.md) |
| 验收 | 2026-10-12：未设连接串时后台测试 349 passed、6 skipped。本地 `mysql:8.4` 且 `ICG_REQUIRE_MYSQL=1` 时 `-m mysql` 6 passed。不可达地址加 `ICG_REQUIRE_MYSQL=1` 时单条测试约 1.53 秒，摘要为 failed，不是 error，输出不含密码。治理检查见验证记录。QA M1 的 downgrade base 再 upgrade head 已包含在 mysql 标记测试中 |
| 项目进度 | as of commit e6215d4, task board is source of truth。本提交后看板为 366 项：32 done、8 in-review、7 in-progress、266 planned、49 blocked、4 ready。BE-M0 为 15 项，6 项 done。本卡 in-review。T12、T13 仍 planned。ISSUE-018 为 in-progress，不关闭 |
<!-- task-delivery:end -->

## 关联与状态

- 2026-10-12，BE-M0，[ISSUE-018](../../issues/ISSUE-018.md)。
- 分支 `codex/repository-foundation`。未新开 PR，未合入，未发布。
- 本地验收已做。QA 5e4a627，PM 确认 REV-M0-T28，本卡为 done。ISSUE-018 仍为 in-progress。REV-M0-T28 仍为 in-review。未合入，未发布。
- QA 已复验 BE-M0-T15 的 Q1～Q3（159b96c，核对 f989af7）。该卡当时仍为 in-review。
- 随后项目经理于 18:01 确认 BE-M0-T15 为 done。用户已在 Word/WPS 目视 OK。ISSUE-027 已 closed。本卡已依据 QA 5e4a627，PM 确认 REV-M0-T28 标为 done。ISSUE-018 仍为 in-progress。

## 完成内容与变更文件

`MysqlConnectionRepository` 在导入和 `create_app()` 时不连接。第一次使用 `.engine`、`read()` 或 `transaction()` 才连接，`connect_timeout` 仍为 3 秒。未设置 `ICG_DATABASE_URL` 时仍是 `MemoryRepository`。显式传入的仓库优先。

Alembic `0002_sessions_receipts` 建立 `idempotency_receipt` 和 `user_session`。密码只来自环境变量。会话和未过期回执写入 MySQL，业务数据仍在内存。失败不写回执。MySQL 不按 2048 条删除未过期回执。过期比较使用 MySQL `NOW(6)`。

QA M1：mysql 标记测试执行 `alembic downgrade base` 再 `upgrade head`，确认两张表消失后再出现。现有 `backend-mysql` 作业已经执行 `python -m pytest tests/backend -m mysql`，因此会跑到这条测试。DevOps 若要单独一步，可以在该作业的 Alembic 步骤旁自行加入：

```text
alembic -c backend/bid-core/alembic.ini downgrade base
alembic -c backend/bid-core/alembic.ini upgrade head
```

本卡不修改 `.github` 工作流。

## 代码解释

见 [代码解释](../code/BE-M0-T11.md)。

## 验收结果

证据见 [验证记录](../testing/2026-10-12-be-m0-t11-sessions-receipts.md)。租约、业务聚合和多副本部署不在本卡。

## 项目进度

as of commit e6215d4, task board is source of truth。BE-M0-T11 改为 in-review 后，看板为 366 项：32 done、8 in-review、7 in-progress、266 planned、49 blocked、4 ready。BE-M0 15 项，6 项 done。下一张相关卡是 BE-M0-T12，本提交不开始它。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 未改。计数句子仍是较早的 364 项，看板才是当前数字 |
| ROADMAP | 未改。理由同上 |
| ARCHITECTURE | 未改。ISSUE-005 的“本轮不引入表结构”是该轮历史记录。持久化步骤在方案正文 |
| PROJECT_BRIEF | 未改。理由同 PRD |
| Issue 看板/详情 | ISSUE-018 仍为 in-progress。T11 为 in-review。T12、T13 仍 planned |
| TASK_BOARD / PROJECT_STATUS | 已改为 366 项：32 done、8 in-review、7 in-progress、266 planned、49 blocked、4 ready。PRD、ROADMAP、PROJECT_BRIEF 的里程碑快照未改 |
| DOCUMENT_INDEX | 登记本交付、代码解释和验证 |

## 风险与后续

业务写入仍在进程内存里。另一个进程能重放回执，但看不到前一个进程内存中的资料行，直到 BE-M0-T13。同一事务只能保证回执和会话一起提交。租约未建表。未合入，未发布。
