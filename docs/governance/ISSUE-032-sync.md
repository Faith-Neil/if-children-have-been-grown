为什么有这个文件：记录 ISSUE-032 登记时改了哪些基线。

它解决什么问题：避免把有条件批准写成已经把 chapter_lease 改成了 edit_lock。

# ISSUE-032 同步

日期 2026-10-12。revision edit-lock-align-1。状态 new。负责人 backend。无迁移、无删行。

| 对象 | 是否改动 | 理由 |
|---|---|---|
| PRD | 未改 | 里程碑快照不改 |
| ROADMAP | 未改 | 理由同 PRD |
| ARCHITECTURE | 未改 | 对齐步骤在持久化方案第 5 节 |
| PROJECT_BRIEF | 未改 | 里程碑快照不改 |
| TASK_BOARD | 已改 | 新增 BE-M0-T17，状态 planned。BE-M0 现为 17 项，其中 6 项 done |
| PROJECT_STATUS | 已改 | 活计数为 376 项：42 done、10 in-review、7 in-progress、264 planned、49 blocked、4 ready |
| DOCUMENT_INDEX | 已改 | 登记本表和 ISSUE-032 |
| 持久化方案 | 已改 | 第 5 节对照表下补一句：偏差已获 PM 有条件批准，待 ISSUE-032 对齐 |
| 依赖与 CI | 未改 | 不改工作流。`bid_outline_node`、`sys_user`、`company` 尚未作为开工条件满足 |

BE-M0-T12 已依据 QA ae6fd10，PM 15:32 确认 done。BE-M0-T13 已依据 QA ae38ec3，PM 17:16 确认 done。ISSUE-018 仍为 in-progress。本卡不标 done，本 Issue 不标 closed。迁移必须保留历史锁行，禁止删除旧租约。`token` 与 `session_token` 要么删除，要么另写保留理由并请项目经理批准。
