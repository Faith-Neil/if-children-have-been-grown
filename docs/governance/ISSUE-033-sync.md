为什么有这个文件：记录 ISSUE-033 登记时改了哪些基线。

它解决什么问题：避免把字段对照和复用错误码写成已经改了挂接接口。

# ISSUE-033 同步

日期 2026-10-12。revision evidence-mount-1。状态 new。负责人 backend。无接口改动、无新错误码。

| 对象 | 是否改动 | 理由 |
|---|---|---|
| PRD | 未改 | 里程碑快照不改。规则仍以参考 PRD v1.8 为准 |
| ROADMAP | 未改 | 理由同 PRD |
| ARCHITECTURE | 未改 | 本轮不改运行结构 |
| PROJECT_BRIEF | 未改 | 里程碑快照不改 |
| TASK_BOARD | 已改 | 新增 BE-M0-T18，状态 planned。BE-M0 现为 18 项，其中 7 项 done |
| PROJECT_STATUS | 已改 | 活计数为 378 项：44 done、9 in-review、7 in-progress、265 planned、49 blocked、4 ready |
| DOCUMENT_INDEX | 已改 | 登记本表和 ISSUE-033 |
| 错误码与 OpenAPI | 未改 | 建议复用 `EVIDENCE_EXPIRED`、`EVIDENCE_NOT_USABLE`、`FORBIDDEN`。规格增量由 AI bot 另交 |
| 依赖与 CI | 未改 | 不改工作流。排在 BE-M0-T13 之后 |

BE-M0-T13 仍为 in-review。ISSUE-018 仍为 in-progress。APP-M2-T114 仍为 in-review。本卡不标 done，本 Issue 不标 closed。实现后由 QA 重签。
