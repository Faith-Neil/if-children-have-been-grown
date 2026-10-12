为什么有这个文件：记录QA对前端请求层重试修复（0a5b655）签署的交付。

它解决什么问题：说明签署结论、证据位置和剩余观察项。

# REV-M0-T21：0a5b655请求层重试修复 QA签署交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | REV-M0-T21 |
| 代码解释 | 无代码变更；仅验收记录 |
| 验收 | 探针34/34；502 MODEL_UNAVAILABLE与503 SECRET_KEY_UNAVAILABLE各1次请求；普通503与无错误体502照常重试，无Idempotency-Key写入不重试；Node 24.9.0前端单测97/97；见[签署记录](../testing/2026-10-12-0a5b655-retry-signoff.md) |
| 项目进度 | 被验卡和Issue的状态不变，等项目经理设置 |
<!-- task-delivery:end -->

## 关联与状态

- 2026-10-12；[ISSUE-013](../../issues/ISSUE-013.md)；被验 前端请求层重试修复（0a5b655）；[任务卡](../tasks/REV-M0.md#rev-m0-t21)；PR #3待合入，未发布。

## 完成内容与变更文件

`docs/testing/2026-10-12-0a5b655-retry-signoff.md`；同步ISSUE-013、REV-M0任务卡、TASK_BOARD、PROJECT_STATUS、DOCUMENT_INDEX。未改被验代码或其卡片、Issue状态。

## 同步与剩余

PRD/ROADMAP/ARCHITECTURE/PROJECT_BRIEF无影响（只读复核；计数为里程碑快照，以任务看板为准）。无观察项。

项目经理恢复后确认本卡为 done，依据是 QA 3e91aee，PM 恢复确认。ISSUE-030 仍为 in-review。APP-M2-T002 仍为 done。未合入，未发布。
