为什么有这个文件：记录挂证据抽屉改了哪些进度说明，以及哪些基线故意不动。

它解决什么问题：避免把一张 in-review 的页面卡写成任务计数里程碑，或写成 T124 已经可以开工。

# APP-M2-T114 同步

日期 2026-10-12。状态 in-review。关联 ISSUE-007。ISSUE-022 仍 in-review。

| 对象 | 是否改动 | 理由 |
|---|---|---|
| PRD | 未改 | 里程碑快照不随单卡更新。需求仍是已登记的 v1.8 |
| ROADMAP | 未改 | 没有新增或取消阶段 |
| ARCHITECTURE | 未改 | 没有新接口。挂接仍是现有条款更新 |
| PROJECT_BRIEF | 未改 | 里程碑快照未变 |
| TASK_BOARD | 已改 | T114 改为 in-review。并入 BE-M0-T16 与 REV-M0-T18、T19 后为 374 项、41 done、9 in-review、264 planned。T124 仍 blocked |
| PROJECT_STATUS | 已改 | 同一计数，并写明 T114 未标 done。BE-M0 仍为 16 项，T16 仍 in-review |
| docs/tasks/APP-M2.md | 已改 | T114 状态和开头的剩余 planned 数。T124 依赖改为 T114 未 done |
| DOCUMENT_INDEX | 已改 | 登记交付、代码解释、核对和本表 |
| issues/index.md、ISSUE-007、ISSUE-022 | 已改 | ISSUE-007 仍 in-progress。ISSUE-022 仍 in-review。T124 仍 blocked |
| docs/testing/icg-task-mapping.md | 已改 T114 状态 | 映射表和 JSON 与任务卡一致。历史核对记录不改 |
| docs/reference | 未改 | 不改参考原文 |
| spec/openapi | 未改 | 接口以 `73fde1e` 的 JSON 为准。README 不代表接口 |
| backend、tests/backend | 未改 | 本卡不改后台 |
