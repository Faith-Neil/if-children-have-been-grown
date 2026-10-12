为什么有这个文件：记录引入 MySQL 依赖时改了哪些基线。

它解决什么问题：避免把四个包的批准写成业务表已经落地。

# ISSUE-023 同步

日期 2026-10-12。revision deps-1。状态 in-review。

| 对象 | 是否改动 | 理由 |
|---|---|---|
| PRD | 未改 | 未改业务规则 |
| ROADMAP | 未改 | 路线图正文不记录这次依赖 |
| ARCHITECTURE | 未改 | ISSUE-005 那一句仍只描述当时的错误体和幂等复查，不在本轮改写 |
| PROJECT_BRIEF | 已改 | 排期改为 360 项：23 done、7 in-review、7 in-progress、269 planned、50 blocked、4 ready |
| TASK_BOARD | 已改 | BE-M0 现为 13 项。T10 in-review，T11～T13 planned。T08 仍 in-review |
| PROJECT_STATUS | 已改 | 写明连接和空基线已进入仓库，业务数据仍在内存 |
| DOCUMENT_INDEX | 已改 | 登记本表、Issue、交付、代码说明和验证 |
| 公网 CI | 未改 | `.github/workflows/offline-check.yml` 不增加 MySQL 服务 |

给运维的命令在 [验证记录](../testing/2026-10-12-mysql-connection.md)。环境变量是 `ICG_DATABASE_URL`。迁移命令是 `alembic -c backend/bid-core/alembic.ini upgrade head`。内网作业使用 `ICG_REQUIRE_MYSQL=1 python -m pytest tests/backend -m mysql`。镜像是 `mysql:8.4`。
