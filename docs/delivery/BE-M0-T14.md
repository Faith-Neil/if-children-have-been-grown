为什么有这个文件：记录托管 MySQL 作业实际加了什么，以及它还没有变成内网部署。

它解决什么问题：避免把一条 CI 作业说成业务数据已经持久，或把数据库密码留在仓库里。

# BE-M0-T14：托管 MySQL CI 作业

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-M0-T14 |
| 代码解释 | [工作流说明](../code/BE-M0-T14.md)。只改 `.github/workflows/offline-check.yml` 及相关记录 |
| 验收 | [核对](../testing/2026-10-12-backend-mysql-ci.md)；[QA 签署](../testing/2026-10-12-be-m0-t14-mysql-ci-signoff.md) `b20b844`。本卡 done |
| 项目进度 | 本卡 done。截至提交 3bb311a 的快照（as of commit 3bb311a）：366 项，30 done、8 in-review、7 in-progress、268 planned、49 blocked、4 ready。之后以任务看板为准。未合入 |
<!-- task-delivery:end -->

## 关联与状态

- 日期、里程碑、Issue、任务卡：2026-10-12；BE-M0；[ISSUE-025](../../issues/ISSUE-025.md)；[任务卡](../tasks/BE-M0.md#be-m0-t14)。关联 ISSUE-018 的连接实现 `7d97369`。
- 分支、提交、PR：`codex/repository-foundation`。不新建 PR。
- 本地验收状态：done。依据 QA 签署 `b20b844`。ISSUE-025 为 closed。
- 合入 / 发布状态：未合入，未发布。

## 完成内容与变更文件

`.github/workflows/offline-check.yml` 增加并行作业 `backend-mysql`。它在 ubuntu-24.04 上使用 Python 3.13.5，权限只有 `contents: read`，不引用密钥。MySQL 8.4 由步骤内 `docker run` 启动，字符集 `utf8mb4`，排序规则 `utf8mb4_unicode_ci`，并做健康检查。密码用 `openssl rand -hex 24` 生成并 `::add-mask::`。密码文件只给启动步骤使用。后续步骤只收到 `ICG_DATABASE_URL` 和 `ICG_REQUIRE_MYSQL=1`，不再收到单独的 `ICG_MYSQL_PASSWORD`。库名 `icg_demo`。然后从仓库根执行 Alembic，再跑 `python -m pytest tests/backend -m mysql`。junit 缺失、0 条、任一跳过，或有失败/错误时作业失败。

原 `backend` 作业不设置 `ICG_DATABASE_URL`。

## 代码解释

见 [代码说明](../code/BE-M0-T14.md)。业务读写仍在内存。本作业不持久会话或幂等回执。

## 验收结果

核对方式见 [测试记录](../testing/2026-10-12-backend-mysql-ci.md) 与 [QA 签署](../testing/2026-10-12-be-m0-t14-mysql-ci-signoff.md)。依据 `b20b844`。守卫负例见 [本轮核对](../testing/2026-10-12-backend-mysql-guard.md)。治理检查在提交前执行。本卡为 done。

## 项目进度

本卡为 done。计数是截至提交 `3bb311a` 的快照（as of commit 3bb311a）：366 项，30 done、8 in-review、7 in-progress、268 planned、49 blocked、4 ready。之后的汇总以任务看板为准。ISSUE-018 仍 in-progress。PR 未合入，未发布。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 无影响于本轮。计数字句仍是 364 项、27 done、9 in-review，不在本提交重开对齐 |
| ROADMAP | 无影响于本轮。计数字句仍是上一轮的 364 项，阶段和发布顺序未改 |
| ARCHITECTURE | 无影响。未改 `docs/ARCHITECTURE.md` |
| PROJECT_BRIEF | 排期句去掉 BE-M0-T14 的 in-review，改为依据 `b20b844` 已 done。计数字句仍是 364 项，不在本提交重开对齐 |
| Issue 看板/详情 | ISSUE-025 为 closed。ISSUE-024 不建档。ISSUE-018 不关闭。BE-M0-T11 增加往返验收 |
| TASK_BOARD / PROJECT_STATUS | BE-M0-T14 为 done。交付里的 366 项、30 done、8 in-review 只是截至提交 3bb311a 的快照。任务看板是计数依据 |
| DOCUMENT_INDEX | 本卡与 Issue 改为 done / closed，并登记守卫核对 |

同步表见 [ISSUE-025-sync](../governance/ISSUE-025-sync.md)。

## 风险与后续

守卫只看 junit 计数，不证明业务表已经存在。真实业务表进入仓库后的 downgrade 再 upgrade 记在 BE-M0-T11，本作业现在仍只做 `upgrade head`。两个进程共享回执仍是 BE-M0-T11。作业通过不是内网部署。
