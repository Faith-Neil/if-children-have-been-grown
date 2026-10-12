为什么有这个文件：记录编辑租约入库这张卡实际交了什么。

它解决什么问题：把 120 秒续期、过期接管，以及和字典 v1.9 的字段偏差，和尚未入库的业务聚合分开。

# BE-M0-T12：编辑租约入库交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-M0-T12 |
| 代码解释 | [BE-M0-T12](../code/BE-M0-T12.md) |
| 验收 | 2026-10-12：未设连接串时后台测试 351 passed、8 skipped。本地 `mysql:8.4` 且 `ICG_REQUIRE_MYSQL=1` 时 `-m mysql` 8 passed。续期后令牌和占用者不变，剩余时间接近 120 秒。未过期时另一个会话得到 423，把到期时间改到过去后可以接管。治理检查见验证记录 |
| 项目进度 | 任务看板是准绳。重数后为 371 项：39 done、6 in-review、7 in-progress、266 planned、49 blocked、4 ready。本卡改为 in-review 后为 371 项：39 done、7 in-review、7 in-progress、265 planned、49 blocked、4 ready。BE-M0 为 15 项，6 项 done。本卡 in-review。T13 仍 planned。ISSUE-018 为 in-progress，不关闭 |
<!-- task-delivery:end -->

## 关联与状态

- 2026-10-12，BE-M0，[ISSUE-018](../../issues/ISSUE-018.md)。
- 分支 `codex/repository-foundation`。未新开 PR，未合入，未发布。
- 本地验收已做。等待项目经理在 QA 后才能标 done。

## 完成内容与变更文件

Alembic `0003_chapter_lease` 建立 `chapter_lease`。一章一行，字段是 `chapter_id`、`token`、`owner_id`、`session_token`、`expires_at`。没有 `chapter` 外键，因为章节表还没建。令牌和会话令牌使用 `utf8mb4_bin`。

`MysqlConnectionRepository` 在每次事务里装载租约，成功后按差量插入、更新或删除。导入和 `create_app()` 仍不连接。未设置 `ICG_DATABASE_URL` 时仍是 `MemoryRepository`，内存上的续期和接管行为不变。

字典 v1.9 的 `edit_lock` 对照写在 [方案第 5 节](../architecture/mysql-8-persistence-plan.md)。每一处偏差都需要项目经理批准。未批准前不补列。

## 代码解释

见 [代码解释](../code/BE-M0-T12.md)。

## 验收结果

证据见 [验证记录](../testing/2026-10-12-be-m0-t12-leases.md)。业务聚合和多副本部署不在本卡。

## 项目进度

任务看板是准绳。BE-M0-T12 改为 in-review 后，看板为 371 项：39 done、7 in-review、7 in-progress、265 planned、49 blocked、4 ready。BE-M0 15 项，6 项 done。T13 仍 planned。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 未改。里程碑快照不改 |
| ROADMAP | 未改。理由同上 |
| ARCHITECTURE | 未改。持久化步骤在方案正文 |
| PROJECT_BRIEF | 未改。理由同 PRD |
| docs/reference | 未改。PRD v1.8 与字典 v1.9 只读 |
| Issue 看板/详情 | ISSUE-018 仍为 in-progress。T12 为 in-review。T13 仍 planned |
| TASK_BOARD / PROJECT_STATUS | 已改为 371 项：39 done、7 in-review、7 in-progress、265 planned、49 blocked、4 ready |
| DOCUMENT_INDEX | 登记本交付、代码解释和验证 |

## 风险与后续

章节正文仍在进程内存里。另一个进程能看见租约，但看不见前一个进程内存中的正文，直到 BE-M0-T13。字典里的心跳、公司隔离、释放历史和两套枚举都还没入库，需要项目经理批准后才能补。未合入，未发布。
