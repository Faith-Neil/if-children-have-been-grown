为什么有这个文件：记录 MySQL 8 持久化方案这张卡实际交了什么。

它解决什么问题：把“方案已提交复查”和“数据库已接入”分开。

# BE-M0-T08：MySQL 8 持久化方案交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-M0-T08 |
| 代码解释 | [无代码说明](../code/BE-M0-T08.md)。未改运行时代码，未加依赖 |
| 验收 | 2026-10-12 治理检查。未连接 MySQL，未跑迁移。不能标 done |
| 项目进度 | 356 项：23 done、6 in-review、7 in-progress、266 planned、50 blocked、4 ready。本卡 in-review。BE-M0-T09 为 planned，含 E2E-D5，本轮不实施。APP-M2-T124 仍 blocked |
<!-- task-delivery:end -->

## 关联与状态

- 2026-10-12，BE-M0，[ISSUE-018](../../issues/ISSUE-018.md)。
- 分支 `codex/repository-foundation`。未新开 PR，未合入，未发布。
- 本地验收：只有治理检查。无服务验收。

## 完成内容与变更文件

方案在 [mysql-8-persistence-plan.md](../architecture/mysql-8-persistence-plan.md)。选择 SQLAlchemy 2.0、PyMySQL、cryptography、Alembic，四项都未安装。字符集 `utf8mb4` / `utf8mb4_0900_ai_ci`，键列 `utf8mb4_bin`。回执表保留 24 小时，租约表 120 秒，含续期和接管。单元测试继续用内存仓库。集成测试提案使用镜像 `mysql:8.4`，命令为 `alembic -c backend/bid-core/alembic.ini upgrade head`，且只在内网执行。

## 代码解释

无代码变更。原因见代码说明。

## 验收结果

- 治理检查：见提交说明中的命令输出。
- 未运行 pytest，因为没有改 Python。
- 未启动 MySQL，未执行 Alembic。

## 项目进度

BE-M0 共 9 项：T01 done，T02、T03、T08 in-review，T04～T07 ready，T09 planned。下一实施项不是本卡自动开始；要等方案被接受并逐项批准依赖。
