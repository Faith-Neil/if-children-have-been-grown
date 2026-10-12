为什么有这个文件：记录内网部署草案核对了哪些基线。

它解决什么问题：避免一份部署说明悄悄改掉需求、路线或架构正文。

# ISSUE-017 同步

日期 2026-10-12。治理块仍为 g1.1 / 2026-10-11 / ISSUE-007，与 [WORKFLOW](WORKFLOW.md) 一致。业务标识 intranet-plan-1。

| 对象 | 实际处理 |
|---|---|
| PRD | 无影响。未改范围、页面、规则或验收 |
| ROADMAP | 无影响。未改阶段、依赖或发布顺序。不改计数字句，当前计数以任务看板为准 |
| ARCHITECTURE | 无影响。草案不改变已实现的内存仓库和单进程入口 |
| PROJECT_BRIEF | 无影响。不改接手快照 |
| Issue 看板/详情 | 新增 ISSUE-017，in-review。不创建 ISSUE-018。不改 ISSUE-007、ISSUE-010、ISSUE-011 |
| TASK_BOARD | 新增 OPS-M0-T02，in-review。351 项：20 done、5 in-review、7 in-progress、266 planned、49 blocked、4 ready |
| PROJECT_STATUS | 记录草案未部署，完成数与看板一致 |
| DOCUMENT_INDEX | 新增草案、Issue、交付、核对记录和本同步表。既有条目里的 T008 用词不改 |
| icg-task-mapping | 不改 |
| 参考原文 | 不改 `docs/reference/` |

PR 未创建。未合入，未发布。数据库节跟随 ISSUE-010 已登记的 MySQL 8。向量库、对话模型、嵌入和重排仍待决，ISSUE-010 不关闭。PRD、ROADMAP、ARCHITECTURE、PROJECT_BRIEF、icg-task-mapping 与 ISSUE-007 里仍可能有过时的 T008 用词，留给项目经理下一次基线同步。
