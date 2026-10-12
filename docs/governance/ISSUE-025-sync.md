为什么有这个文件：记录托管 MySQL 作业核对了哪些基线。

它解决什么问题：避免一个 CI 作业被写成产品已经改用数据库，或把固定密码留在说明里。

# ISSUE-025 同步

日期 2026-10-12。治理块仍为 g1.1 / 2026-10-11 / ISSUE-007，与 [WORKFLOW](WORKFLOW.md) 一致。业务标识 mysql-ci-1。

| 对象 | 实际处理 |
|---|---|
| PRD | 只改任务计数字句为 362 项。不改范围、页面、规则或验收 |
| ROADMAP | 只改任务计数字句为 362 项。不改阶段、依赖或发布顺序 |
| ARCHITECTURE | 无影响。未改 `docs/ARCHITECTURE.md`。连接行为仍是 BE-M0-T10 |
| PROJECT_BRIEF | 只改排期行的任务计数为 362 项 |
| Issue 看板/详情 | 新增 ISSUE-025，in-review。ISSUE-024 不建档。ISSUE-018 仍为 in-progress，只补一条互链 |
| TASK_BOARD | 新增 BE-M0-T14，in-review。362 项：26 done、7 in-review、7 in-progress、268 planned、50 blocked、4 ready |
| PROJECT_STATUS | 写明托管作业使用 MySQL 8.4 容器，仍不访问公司内网。完成数与看板一致 |
| DOCUMENT_INDEX | 登记本 Issue、交付、代码说明、核对记录和本同步表。核对条目改为已核对，并记下 run 38207508936 |
| 持久化方案 | 删去“不要把 mysql:8.4 加进工作流”的禁令，改记为本作业。原 `backend` 作业仍不设置连接串 |
| icg-task-mapping | 不改 |
| 参考原文 | 不改 `docs/reference/` |

PR 未创建。未合入，未发布。密码不进仓库。ISSUE-018 不关闭。
