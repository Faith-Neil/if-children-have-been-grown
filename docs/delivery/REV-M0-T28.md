为什么有这个文件：记录QA对BE-M0-T11（回执与会话入库）正式签署的交付。

它解决什么问题：说明签署结论、证据位置和剩余观察项；T27 留给 PR #4 改号，本卡为 T28。

# REV-M0-T28：BE-M0-T11 回执与会话入库 QA签署交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | REV-M0-T28 |
| 代码解释 | 无代码变更；仅验收记录 |
| 验收 | 真实 MySQL 8.4：`-m mysql` 12 passed；downgrade/upgrade 往返通过；Q2 约 1s failed 非 error；双 worker + 重启会话/回执存活；CI 38212536927 全绿；见[签署记录](../testing/2026-10-12-be-m0-t11-qa-signoff.md)。**不标 done** |
| 项目进度 | BE-M0-T11 / ISSUE-018 / 本卡均 in-review（或 Issue in-progress），不标 done。未合入，未发布。REV-M0-T27 预留给 Codex PR #4 / ISSUE-034 |
<!-- task-delivery:end -->

## 关联与状态

- 2026-10-12；[ISSUE-013](../../issues/ISSUE-013.md)；被验 [BE-M0-T11](BE-M0-T11.md) / [ISSUE-018](../../issues/ISSUE-018.md)（`631d4c9`）；[任务卡](../tasks/REV-M0.md#rev-m0-t28)；PR #3待合入，未发布。
- REV-M0-T25/T26 已用于 ISSUE-036 / ISSUE-033；T27 预留；本卡为 T28。

## 完成内容与变更文件

`docs/testing/2026-10-12-be-m0-t11-qa-signoff.md`；同步 ISSUE-013、ISSUE-018 变更记录、REV-M0任务卡、TASK_BOARD、PROJECT_STATUS、DOCUMENT_INDEX。未改被验代码；未把 BE-M0-T11 / ISSUE-018 标为 done。

## 同步与剩余

PRD/ROADMAP/ARCHITECTURE/PROJECT_BRIEF无影响（只读复核；计数为里程碑快照，以任务看板为准）。O-1 health `single_process` 标志。本卡不标 done。未合入，未发布。
