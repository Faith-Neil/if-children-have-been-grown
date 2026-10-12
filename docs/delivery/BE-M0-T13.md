为什么有这个文件：记录按聚合迁移这张卡实际交了什么。

它解决什么问题：把已入库的项目聚合，和仍留在内存里的章节及其他聚合分开。

# BE-M0-T13：按聚合迁移仓库交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-M0-T13 |
| 代码解释 | [BE-M0-T13](../code/BE-M0-T13.md) |
| 验收 | 2026-10-12：未设连接串时后台测试 351 passed、11 skipped。本地 `mysql:8.4` 且 `ICG_REQUIRE_MYSQL=1` 时 `-m mysql` 11 passed。另一个进程能看见已提交项目的名称、公司、版本、敏感标记和负责人，看不见该项目的新章节。失败事务不留下项目行。旧版本更新返回 409 `REVISION_CONFLICT`。治理检查见验证记录 |
| 项目进度 | 任务看板是准绳。重数后为 375 项：42 done、9 in-review、7 in-progress、264 planned、49 blocked、4 ready。本卡改为 in-review 后为 375 项：42 done、10 in-review、7 in-progress、263 planned、49 blocked、4 ready。BE-M0 为 16 项，6 项 done。本卡 in-review。ISSUE-018 为 in-progress，不关闭 |
<!-- task-delivery:end -->

## 关联与状态

- 2026-10-12，BE-M0，[ISSUE-018](../../issues/ISSUE-018.md)。
- 分支 `codex/repository-foundation`。未新开 PR，未合入，未发布。
- 本地验收已做。等待项目经理在 QA 后才能标 done。

## 完成内容与变更文件

Alembic `0004_demo_project` 建立 `demo_project` 和 `demo_project_team`。项目字段对应演示里的 id、名称、公司、版本、招标编号、截止时间和是否敏感。分工放在 `team_json`。没有章节表，也不把整份 `DemoState` 写成一条记录。

`MysqlConnectionRepository` 把库里的项目叠到内存种子上。只有发生变化的项目才插入或更新。未改过的种子项目不插入。`UPDATE` 带上装载时的 `revision`，对不上就回滚并返回 409 `REVISION_CONFLICT`。导入和 `create_app()` 仍不连接。未设置 `ICG_DATABASE_URL` 时仍是 `MemoryRepository`。

字典 v1.9 的 `bid_project` 与 `bid_project_member` 对照写在 [方案第 6 节](../architecture/mysql-8-persistence-plan.md)。每一处偏差都需要项目经理批准。未批准前不补列。

## 代码解释

见 [代码解释](../code/BE-M0-T13.md)。

## 验收结果

证据见 [验证记录](../testing/2026-10-12-be-m0-t13-projects.md)。章节、检查与导出、资料与承诺、工作流与任务、审计仍在内存。

## 项目进度

任务看板是准绳。BE-M0-T13 改为 in-review 后，看板为 375 项：42 done、10 in-review、7 in-progress、263 planned、49 blocked、4 ready。BE-M0 16 项，6 项 done。ISSUE-018 仍为 in-progress。

## 限制与未完成

- 不标 done，不关闭 ISSUE-018。
- 不建章节、检查、导出、资料、工作流、任务和审计表。
- 不补字典里尚未批准的列。
- 不改 `.github`，不改 `docs/reference/`，不改 PRD、ROADMAP、PROJECT_BRIEF 的里程碑计数。
