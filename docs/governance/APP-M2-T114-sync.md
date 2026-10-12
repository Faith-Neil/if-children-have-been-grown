为什么有这个文件：记录挂证据抽屉改了哪些进度说明，以及哪些基线故意不动。

它解决什么问题：避免把一张已 done 的页面卡写成任务计数里程碑，或写成 T124 已经可以开工。

# APP-M2-T114 同步

日期 2026-10-12。状态 done（QA f521950，PM 17:13 确认）。关联 ISSUE-007。REV-M0-T22 同一依据标为 done。缺协议、受限、智能匹配和规则 2 端到端仍挂 ISSUE-033，不关闭。

| 对象 | 是否改动 | 理由 |
|---|---|---|
| PRD | 未改 | 里程碑快照不随单卡更新。需求仍是已登记的 v1.8 |
| ROADMAP | 未改 | 没有新增或取消阶段 |
| ARCHITECTURE | 未改 | 没有新接口。挂接仍是现有条款更新 |
| PROJECT_BRIEF | 未改 | 里程碑快照未变 |
| TASK_BOARD | 已改状态 | T114 与 REV-M0-T22 为 done（QA f521950，PM 17:13 确认）。看板 381 项：47 done、9 in-review、7 in-progress、265 planned、49 blocked、4 ready。T124 仍 blocked，因为 T078 仍 in-review 未 done |
| PROJECT_STATUS | 已改 | 开篇计数与看板一致。T114 已标 done |
| docs/tasks/APP-M2.md | 已改 | T114 状态为 done。T124 依赖改为 T114 已 done、T078 未 done。其余 253 张仍 planned |
| DOCUMENT_INDEX | 已改 | 更新当前行。橙色标签对比另登记 ISSUE-036 |
| issues/index.md、ISSUE-007 | ISSUE-007 详情已改 | 看板行状态仍是 in-progress。ISSUE-033 不关闭。T124 仍 blocked |
| docs/testing/icg-task-mapping.md | 已改 | 映射表和 JSON 的 T114 状态改为 done |
| docs/reference | 未改 | 不改参考原文 |
| spec/openapi | 未改 | 接口以 `73fde1e` 的 JSON 为准。README 不代表接口 |
| backend、tests/backend | 未改 | 本卡不改后台 |

随后项目经理确认 APP-M2-T078 与 REV-M0-T24 为 done，依据是 QA 19c4862，PM 17:20 确认。页面未做，不挡住 done。T124 改为 ready，本轮不实现。看板改为 381 项：49 done、7 in-review、7 in-progress、265 planned、48 blocked、5 ready。
