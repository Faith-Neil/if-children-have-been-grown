为什么有这个文件：记录 APP-M2-T105 条目卡片编辑与逐条确认 的实际交付和测试证据。

它解决什么问题：2026-10-30 看板整治核对后，本卡功能已在代码中实现，但没有交付文档；本文件补齐证据，状态改为 in-review。

# APP-M2-T105：条目卡片编辑与逐条确认

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T105 |
| 代码解释 | [APP-M2-T105](../code/APP-M2-T105.md) |
| 验收 | 2026-10-30：解析页条目卡片可修改、确认、排除（排除须写理由）；修改后加人工锁，重新抽取不覆盖；点条目定位左侧原文页 |
| 项目进度 | 看板与任务卡同步为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T105](../tasks/APP-M2.md#app-m2-t105)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)

## 实际文件
- `frontend/web/src/project/ParseTab.tsx`
- `frontend/web/src/project/parse-review-core.ts`
- `frontend/web/src/project/PdfLocator.tsx`
- `backend/bid-core/icg/domain/parse_review.py`

## 测试证据
- `tests/backend/test_parse_review.py::test_manually_edited_requirement_survives_reparse`
- `frontend/web/tests/unit/parse-review-core.test.mjs`
- `frontend/web/e2e/parse-review.spec.ts`
- `frontend/web/e2e/pdf-locator.spec.ts`

验证命令：后端全量 `pytest tests/backend`（分两批）、前端 `pnpm lint && pnpm test`、E2E `run-e2e.sh`，均在提交前执行并通过。

## 未实现项与限制
乱码条目须对照原页补录（`needsReentry`），不能直接确认。与 02d 的并排截图未存档。
