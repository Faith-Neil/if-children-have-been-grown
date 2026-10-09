# Issue 看板

<!-- governance-baseline:start -->
| 项目 | 内容 |
|---|---|
| 治理版本 | g1.1 |
| 更新日期 | 2026-10-09 |
| 关联 Issue | ISSUE-004 |
<!-- governance-baseline:end -->

管理规则见 [Issue 说明](README.md) 与 [协作工作流](../docs/governance/WORKFLOW.md)。每次需求变更、版本更新或 Bug 必须先登记 Issue；详情使用 [模板](template.md)。任务与进度见 [任务看板](../docs/TASK_BOARD.md)。

<!-- issue-board:start -->
| 编号 | 类型 | 优先级 | 状态 | 验收证据 | 合入状态 | 发布状态 | 事项 | 下一步 |
|---|---|---|---|---|---|---|---|---|
| [ISSUE-001](ISSUE-001.md) | decision | P1 | blocked | 本地整合未验收；[分支评审](../docs/reviews/pr-1-integration.md) | PR #1 未合入 | 未发布 | xqr 系统选型与治理记录待整合 | 等待文档分层、基线材料与技术决策核对，不覆盖 main 前端文档 |
| [ISSUE-002](ISSUE-002.md) | bug | P1 | closed | [6 项回归通过](../docs/testing/2026-10-09-repository-foundation.md) | PR #3 待合入 | 未发布 | 原型编辑锁未阻止 AI Diff 确认写入 | FE-M0-T01 本地验收完成；浏览器、合入与发布分别记录 |
| [ISSUE-003](ISSUE-003.md) | workflow | P1 | closed | 四项验收及独立复核通过；[交付记录](../docs/delivery/FE-M0-T02.md) | PR #3 本轮变更待合入 | 未发布 | Issue 前置、六份基线同步与任务交付治理 | 合入后记录实际提交；后续按新规则逐任务推进 |
| [ISSUE-004](ISSUE-004.md) | workflow | P1 | closed | [双向同步与审查验收](../docs/testing/2026-10-09-workspace-sync.md) | PR #3 待合入 | 未发布 | 全工作区同步、目录/业务/技术审查与brief | 持续运行；按ISSUE-005推进基线与契约决定 |
| [ISSUE-005](ISSUE-005.md) | decision | P0 | blocked | 尚待共同决定与真实验证；[审查与门禁](ISSUE-005.md) | 发现记录在PR #3待合入 | 未发布 | 业务范围、完整性与前后端契约未冻结 | 按DG-01～06推进FE-M0-T03/04，取得缺件或评审替代依据 |
<!-- issue-board:end -->

ISSUE-001 编号沿用合作分支。其原记录在 xqr 内标为 closed，仅表示该分支当时的文档同步验收；本地整合保持 blocked，不据此采纳或发布技术决策。ISSUE-002 的 closed 仅表示本地验收完成。

下一编号为 `ISSUE-006`。只更新此表不能代替详情、任务或验收记录。
