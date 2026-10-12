为什么有这个文件：记录托管 MySQL 作业实际加了什么，以及它还没有变成内网部署。

它解决什么问题：避免把一条 CI 作业说成业务数据已经持久，或把数据库密码留在仓库里。

# BE-M0-T14：托管 MySQL CI 作业

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-M0-T14 |
| 代码解释 | [工作流说明](../code/BE-M0-T14.md)。只改 `.github/workflows/offline-check.yml` 及相关记录 |
| 验收 | [核对](../testing/2026-10-12-backend-mysql-ci.md)。作业 in-review。未标 done |
| 项目进度 | 本卡 in-review。362 项：26 done、7 in-review、7 in-progress、268 planned、50 blocked、4 ready。done 待项目经理 |
<!-- task-delivery:end -->

## 关联与状态

- 日期、里程碑、Issue、任务卡：2026-10-12；BE-M0；[ISSUE-025](../../issues/ISSUE-025.md)；[任务卡](../tasks/BE-M0.md#be-m0-t14)。关联 ISSUE-018 的连接实现 `7d97369`。
- 分支、提交、PR：`codex/repository-foundation`。不新建 PR。
- 本地验收状态：in-review。
- 合入 / 发布状态：未合入，未发布。

## 完成内容与变更文件

`.github/workflows/offline-check.yml` 增加并行作业 `backend-mysql`。它在 ubuntu-24.04 上使用 Python 3.13.5，权限只有 `contents: read`，不引用密钥。MySQL 8.4 由步骤内 `docker run` 启动，字符集 `utf8mb4`，排序规则 `utf8mb4_unicode_ci`，并做健康检查。密码用 `openssl rand -hex 24` 生成，`::add-mask::` 之后写入 `$GITHUB_ENV`。库名 `icg_demo`。然后从仓库根执行 Alembic，再跑 `python -m pytest tests/backend -m mysql`，并用 junit 拒绝 0 条或全部跳过。

原 `backend` 作业不设置 `ICG_DATABASE_URL`。

## 代码解释

见 [代码说明](../code/BE-M0-T14.md)。业务读写仍在内存。本作业不持久会话或幂等回执。

## 验收结果

核对方式见 [测试记录](../testing/2026-10-12-backend-mysql-ci.md)。治理检查在提交前执行。

## 项目进度

本卡保持 in-review。看板为 362 项：26 done、7 in-review、7 in-progress、268 planned、50 blocked、4 ready。ISSUE-018 仍 in-progress。PR 未合入，未发布。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 只改任务计数字句。页面和验收口径未改 |
| ROADMAP | 只改任务计数字句。阶段和发布顺序未改 |
| ARCHITECTURE | 无影响。未改 `docs/ARCHITECTURE.md` |
| PROJECT_BRIEF | 只改排期行的任务计数 |
| Issue 看板/详情 | 新增 ISSUE-025，in-review。ISSUE-024 不建档。ISSUE-018 不关闭 |
| TASK_BOARD / PROJECT_STATUS | BE-M0-T14 为 in-review。计数见上 |
| DOCUMENT_INDEX | 登记本卡交付、说明、核对和同步表 |

同步表见 [ISSUE-025-sync](../governance/ISSUE-025-sync.md)。

## 风险与后续

守卫只看 junit 计数，不证明业务表已经存在。两个进程共享回执仍是 BE-M0-T11。作业通过不是内网部署。
