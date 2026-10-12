为什么有这个文件：登记托管运行器上的 MySQL 作业。

它解决什么问题：避免把连接测试只留在某台内网机器，或把固定数据库密码写进仓库。

# ISSUE-025：托管 MySQL CI 作业

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-025 |
| 类型 | workflow |
| 优先级 | P1 |
| 状态 | closed |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | mysql-ci-1 |
| 关联 Task | [BE-M0-T14](../docs/tasks/BE-M0.md#be-m0-t14) |
| 关联 PR | 未创建。沿用既有 PR #3 的分支，本轮不新建 PR |
| 本地验收 | BE-M0-T14 为 done。依据 QA 签署 `b20b844`。Issue 用 closed：看板没有 done 这个 Issue 状态 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [BE-M0-T14 交付](../docs/delivery/BE-M0-T14.md) |
| 代码 / 流程解释 | [BE-M0-T14 代码说明](../docs/code/BE-M0-T14.md) |
| 验证记录 | [MySQL CI 核对](../docs/testing/2026-10-12-backend-mysql-ci.md)；[QA 签署](../docs/testing/2026-10-12-be-m0-t14-mysql-ci-signoff.md) |

## 现象与证据

ISSUE-018 的连接与空迁移已在 `7d97369` 进入仓库，BE-M0-T08 与 BE-M0-T10 已由项目经理标为 done。`.github/workflows/offline-check.yml` 的 `backend` 作业仍不设置 `ICG_DATABASE_URL`，标记 `mysql` 的测试在该作业里跳过。ISSUE-024 留给后台，本轮不建档。

## 影响与分流

- 影响：新增 `backend-mysql` 作业、本 Issue、任务卡、交付、代码说明、核对记录和同步表。
- 不涉及：不改业务读写，不建业务表，不把会话或幂等回执写入 MySQL。不改 `backend`、`frontend`、`governance`、`e2e` 四个既有作业的命令。不使用仓库密钥，不连接公司内网。
- 依赖：连接行为以 BE-M0-T10 为准。多 worker 和多副本仍等 ISSUE-018 的 BE-M0-T11。
- 与 ISSUE-018 的关系：本作业只跑已有的 mysql 标记测试和空迁移。不把 ISSUE-018 标成 closed。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| BE-M0-T14 | 在离线检查中增加不保存固定密码的 MySQL 8.4 作业 | `.github/workflows/offline-check.yml` | AC-01～AC-04 | done |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 作业使用 ubuntu-24.04、Python 3.13.5、`contents: read`，不引用 `secrets` | 已写入工作流。Actions 结果见核对记录 |
| AC-02 | MySQL 8.4 由步骤内 `docker run` 启动。字符集 `utf8mb4`，排序规则 `utf8mb4_unicode_ci`。密码在运行时生成并 `::add-mask::`，仓库里没有固定密码。库名 `icg_demo` | 已写入工作流。日志不打印密码 |
| AC-03 | 设置 `ICG_DATABASE_URL` 与 `ICG_REQUIRE_MYSQL=1` 后，从仓库根执行 `alembic -c backend/bid-core/alembic.ini upgrade head`，再执行 `python -m pytest tests/backend -m mysql` 并写出 junit | 已写入工作流 |
| AC-04 | 若 junit 缺失、收集到 0 条、有跳过，或有失败/错误，作业失败。原 `backend` 作业仍不连接 MySQL | 守卫已改为任一跳过即失败。原作业未改命令。QA 签署 `b20b844` 的 M2 |

本 Issue 依据 QA 签署 `b20b844` 关闭。未合入，未发布。

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 有影响。只改任务计数字句，不改页面或规则 | `docs/PRD.md` 任务计数 | mysql-ci-1 / ISSUE-025 / 2026-10-12 | 已同步 |
| ROADMAP | 有影响。只改任务计数字句，不改阶段或发布顺序 | `docs/ROADMAP.md` 任务计数 | mysql-ci-1 / ISSUE-025 / 2026-10-12 | 已同步 |
| ARCHITECTURE | 无影响。未改已实现的模块或接口。连接行为仍是 BE-M0-T10 | 不改 `docs/ARCHITECTURE.md` | mysql-ci-1 / ISSUE-025 / 2026-10-12 | 已核对 |
| PROJECT_BRIEF | 有影响。只改排期行的任务计数 | `docs/PROJECT_BRIEF.md` 排期行 | mysql-ci-1 / ISSUE-025 / 2026-10-12 | 已同步 |
| TASK_BOARD | 有影响。BE-M0-T14 为 done。看板 366 项：30 done、8 in-review | `docs/TASK_BOARD.md`、`docs/tasks/BE-M0.md` | mysql-ci-1 / ISSUE-025 / 2026-10-12 | 已同步 |
| PROJECT_STATUS | 有影响。记录托管作业跑 MySQL 8.4 容器，仍不访问公司内网 | `docs/PROJECT_STATUS.md` | mysql-ci-1 / ISSUE-025 / 2026-10-12 | 已同步 |
| DOCUMENT_INDEX | 有影响。登记本 Issue、交付、说明、核对和同步表 | `docs/DOCUMENT_INDEX.md` | mysql-ci-1 / ISSUE-025 / 2026-10-12 | 已同步 |

治理块保持 g1.1 / 2026-10-11 / ISSUE-007。`docs/reference/` 未改。

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | mysql-ci-1 / in-review | 增加 `backend-mysql`。密码运行时生成。ISSUE-024 不建档。done 待项目经理 | [核对](../docs/testing/2026-10-12-backend-mysql-ci.md) |
| 2026-10-12 | mysql-ci-1 / in-review | `b91d331` 的作业成功：2 passed、320 deselected，junit tests=2 skipped=0 failures=0 errors=0。不标 done | [run 38207508936](https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/38207508936) |
| 2026-10-12 | mysql-ci-1 / closed | 依据 QA 签署 `b20b844` 把 BE-M0-T14 标为 done，本 Issue 标为 closed。守卫改为任一跳过即失败。`ICG_MYSQL_PASSWORD` 不再写入后续步骤。未合入 | [QA 签署](../docs/testing/2026-10-12-be-m0-t14-mysql-ci-signoff.md) |

## 本地验收与后续合入发布

- 本地验收结论与日期：2026-10-12 依据 QA 签署 `b20b844` 关闭。任务为 done。未合入。
- 验证方式：治理检查，以及推送后的 `backend-mysql` 作业。没有把密码写入仓库。
- PR 状态：未创建。
- 合入提交与日期：未合入。
- 发布版本与日期：未发布。
