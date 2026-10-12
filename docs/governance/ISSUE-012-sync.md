为什么有这个文件：记录离线 CI 这一变更核对了哪些基线。

它解决什么问题：避免只改工作流，却不说明需求、路线和架构为什么没有改正文。

# ISSUE-012 同步

日期 2026-10-12。治理块仍为 g1.1 / 2026-10-11 / ISSUE-007，与 [WORKFLOW](WORKFLOW.md) 一致。业务标识 offline-ci-1。

| 对象 | 实际处理 |
|---|---|
| PRD | 无影响。未改范围、页面、规则或验收。治理块不改 |
| ROADMAP | 无影响。未改阶段、优先级、依赖或发布顺序 |
| ARCHITECTURE | 无影响。未改模块、状态、接口或部署。CI 只调用现有离线命令 |
| Issue 看板/详情 | 新增 ISSUE-012，in-review。ISSUE-013 与 ISSUE-015 保留。下一编号写 ISSUE-016；ISSUE-014 预留给并行的 ProComponents 变更 |
| TASK_BOARD | APP-M2-T008 改为 in-review，关联 ISSUE-012，交付链接到实际文件。完成数在进度中按看板重计 |
| PROJECT_STATUS | 记录本门禁尚未关闭，T001 继续 in-progress |
| DOCUMENT_INDEX | 登记工作流、Issue、交付、代码解释、本同步表和验证记录 |
| WORKFLOW | 在验收一节补上与 CI 相同的命令入口。治理块不升版 |
| 参考原文 | 不改 `docs/reference/` |

PR #3 仍待合入。本轮不新建 PR，不合并，不发布。
