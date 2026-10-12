为什么有这个文件：记录挂证据抽屉改了哪些进度说明，以及哪些基线故意不动。

它解决什么问题：避免把一张 in-review 的页面卡写成任务计数里程碑，或写成 T124 已经可以开工。

# APP-M2-T114 同步

日期 2026-10-12。状态 in-review。关联 ISSUE-007。缺协议字段引用已登记的后台 ISSUE-033，本轮不改它。

| 对象 | 是否改动 | 理由 |
|---|---|---|
| PRD | 未改 | 里程碑快照不随单卡更新。需求仍是已登记的 v1.8 |
| ROADMAP | 未改 | 没有新增或取消阶段 |
| ARCHITECTURE | 未改 | 没有新接口。挂接仍是现有条款更新 |
| PROJECT_BRIEF | 未改 | 里程碑快照未变 |
| TASK_BOARD | 未改状态 | T114 仍 in-review。当前表为 378 项、44 done、9 in-review、7 in-progress、265 planned、49 blocked、4 ready。本轮不改开篇计数。T124 仍 blocked |
| PROJECT_STATUS | 未改 | 开篇计数已由上游写成当前看板。T114 仍未标 done |
| docs/tasks/APP-M2.md | 已改 | T114 状态和开头的剩余 planned 数。T124 依赖改为 T114 未 done |
| DOCUMENT_INDEX | 已改 | 登记交付、代码解释、核对和本表 |
| issues/index.md、ISSUE-007 | ISSUE-007 详情已改 | 看板行状态仍是 in-progress，不新开 Issue。ISSUE-033 已由后台登记，本轮不改。T124 仍 blocked |
| docs/testing/icg-task-mapping.md | 未改 | 映射表和 JSON 已是 in-review。本轮状态不变 |
| docs/reference | 未改 | 不改参考原文 |
| spec/openapi | 未改 | 接口以 `73fde1e` 的 JSON 为准。README 不代表接口 |
| backend、tests/backend | 未改 | 本卡不改后台 |
