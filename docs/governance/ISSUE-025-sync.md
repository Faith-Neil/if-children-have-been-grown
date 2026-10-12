为什么有这个文件：记录托管 MySQL 作业核对了哪些基线。

它解决什么问题：避免一个 CI 作业被写成产品已经改用数据库，或把固定密码留在说明里。

# ISSUE-025 同步

日期 2026-10-12。治理块仍为 g1.1 / 2026-10-11 / ISSUE-007，与 [WORKFLOW](WORKFLOW.md) 一致。业务标识 mysql-ci-1。

| 对象 | 实际处理 |
|---|---|
| PRD | 本轮不改计数字句。正文仍是 364 项、27 done、9 in-review。不改范围、页面、规则或验收 |
| ROADMAP | 本轮不改计数字句。正文仍是 364 项、27 done、9 in-review。不改阶段、依赖或发布顺序 |
| ARCHITECTURE | 无影响。未改 `docs/ARCHITECTURE.md`。连接行为仍是 BE-M0-T10 |
| PROJECT_BRIEF | 排期句把 BE-M0-T14 从 in-review 改为依据 `b20b844` 已 done。计数字句仍是 364 项，不在本提交重开对齐 |
| Issue 看板/详情 | ISSUE-025 为 closed，依据 QA 签署 `b20b844`。看板没有 done 状态，所以 Issue 用 closed，任务用 done。ISSUE-024 不建档。ISSUE-018 仍为 in-progress |
| TASK_BOARD | BE-M0-T14 为 done。366 项：30 done、8 in-review、7 in-progress、268 planned、49 blocked、4 ready。BE-M0 为 6/15 |
| PROJECT_STATUS | 写明 T14 已 done，托管作业仍不访问公司内网。完成数与看板一致 |
| DOCUMENT_INDEX | ISSUE-025 与交付改为 closed / done。登记守卫核对 |
| 持久化方案 | 删去“不要把 mysql:8.4 加进工作流”的禁令，改记为本作业。原 `backend` 作业仍不设置连接串 |
| icg-task-mapping | 不改 |
| 参考原文 | 不改 `docs/reference/` |

PR 未创建。未合入，未发布。密码不进仓库。ISSUE-018 不关闭。QA 签署 `b20b844` 的 M2 已把守卫改成任一跳过即失败。M3 已停止把 `ICG_MYSQL_PASSWORD` 写入 `$GITHUB_ENV`。M1 记在 BE-M0-T11，业务表出现之前不把 downgrade 再 upgrade 加进作业。
