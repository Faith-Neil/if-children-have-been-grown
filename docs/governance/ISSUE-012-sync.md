为什么有这个文件：记录离线 CI 这一变更核对了哪些基线。

它解决什么问题：避免只改工作流，却不说明需求、路线和架构为什么没有改正文。

# ISSUE-012 同步

日期 2026-10-12。治理块仍为 g1.1 / 2026-10-11 / ISSUE-007，与 [WORKFLOW](WORKFLOW.md) 一致。业务标识 offline-ci-1。

| 对象 | 实际处理 |
|---|---|
| PRD | 无影响。未改范围、页面、规则或验收。治理块不改 |
| ROADMAP | 无影响。未改阶段、优先级、依赖或发布顺序 |
| ARCHITECTURE | 无影响。未改模块、状态、接口或部署。CI 只调用现有离线命令 |
| Issue 看板/详情 | ISSUE-012 与 APP-M2-T008 为 in-review。ISSUE-013 与 ISSUE-015 保留。下一编号仍是 ISSUE-016；ISSUE-014 预留给并行的 ProComponents 变更 |
| TASK_BOARD | APP-M2-T008 从 done 改回 in-review。343 项中 done 19、in-review 1、in-progress 8、planned 266、blocked 49、ready 0 |
| PROJECT_STATUS | 保留离线 CI 运行证据，卡片状态改为 in-review，未部署；T001 继续 in-progress |
| PROJECT_BRIEF | 2026-10-12 曾把维护日期改为当天，关联加上 ISSUE-012 / APP-M2-T008，排期计数写成 340 项、18 done。原因是把离线 CI 计入接手说明。本轮去掉排期格里重复的「T008离线CI已本地验收」，并把该卡改回 in-review。排期现为 343 项：19 done、1 in-review、8 in-progress、266 planned、49 blocked、0 ready |
| DOCUMENT_INDEX | 登记工作流、Issue、交付、代码解释、本同步表和验证记录，状态改为 in-review |
| WORKFLOW | 验收一节保留 CI 命令，并写明开发者只标 in-review、运行器为 ubuntu-24.04。治理块不升版 |
| ROADMAP | 只把 APP-M2-T008 的「已本地验收」改回 in-review。阶段和发布顺序未改 |
| 参考原文 | 不改 `docs/reference/` |

PR #3 仍待合入。本轮不新建 PR，不合并，不发布。
