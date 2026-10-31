为什么有这个文件：记录 APP-M2-T135 一键重新检查 的实际交付和测试证据。

它解决什么问题：2026-10-30 看板整治核对后，本卡功能已在代码中实现，但没有交付文档；本文件补齐证据，状态改为 in-review。

# APP-M2-T135：一键重新检查

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T135 |
| 代码解释 | [APP-M2-T135](../code/APP-M2-T135.md) |
| 验收 | 2026-10-30：章节循环页与人工队列页按章节“重新检查”；本节负责人或项目负责人可用，分册定稿、无正文时置灰并说明原因；只采纳最近一次请求的回包 |
| 项目进度 | 看板与任务卡同步为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T135](../tasks/APP-M2.md#app-m2-t135)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)

## 实际文件
- `frontend/web/src/project/ChapterLoopPage.tsx`
- `frontend/web/src/project/ManualQueuePage.tsx`
- `backend/bid-core/icg/api/chapter_loop.py`

## 测试证据
- `tests/backend/test_human_queue.py::test_recheck_fixes_safe_items_and_queues_the_rest`
- `tests/backend/test_human_queue.py::test_recheck_refuses_locked_chapter_and_needs_version`
- `tests/backend/test_compliance_rules_scope.py::test_recheck_routes_extra_commitment_to_project_lead`
- `frontend/web/e2e/chapter-loop.spec.ts`

验证命令：后端全量 `pytest tests/backend`（分两批）、前端 `pnpm lint && pnpm test`、E2E `run-e2e.sh`，均在提交前执行并通过。

## 未实现项与限制
“全项目一键重新检查”入口不在本卡；分册检查与全文检查走检查页。
