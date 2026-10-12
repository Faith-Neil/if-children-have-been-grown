为什么有这个文件：记录 ISSUE-035 登记时改了哪些基线。

它解决什么问题：避免把有条件批准写成已经把 demo_project 改成了 bid_project。

# ISSUE-035 同步

日期 2026-10-12。revision bid-project-align-1。状态 new。负责人 backend。无迁移、无删行。

| 对象 | 是否改动 | 理由 |
|---|---|---|
| PRD | 未改 | 里程碑快照不改 |
| ROADMAP | 未改 | 理由同 PRD |
| ARCHITECTURE | 未改 | 对齐步骤在持久化方案第 6 节 |
| PROJECT_BRIEF | 未改 | 里程碑快照不改 |
| TASK_BOARD | 已改 | 新增 BE-M0-T19，状态 planned。BE-M0 现为 19 项，其中 7 项 done |
| PROJECT_STATUS | 已改 | 活计数为 386 项：49 done、12 in-review、7 in-progress、265 planned、48 blocked、5 ready |
| DOCUMENT_INDEX | 已改 | 登记本表和 ISSUE-035 |
| 持久化方案 | 已改 | 第 6 节对照表下补一句：偏差已获 PM 有条件批准，待 ISSUE-035 对齐 |
| 依赖与 CI | 未改 | 不改工作流。正式 `bid_project`、`bid_project_member` 尚未作为开工条件满足 |

BE-M0-T13 仍为 in-review。ISSUE-018 仍为 in-progress。本卡不标 done，本 Issue 不标 closed。迁移必须保留历史项目和成员，禁止删除旧行。不另开 ISSUE-034。ISSUE-036 已由上游登记，本提交不改它。
