为什么有这个文件：记录 APP-M2-T106 批量确认（星号 / 废标 / 资格禁用）与置信度高亮 的实际交付和测试证据。

它解决什么问题：2026-10-30 看板整治核对后，本卡功能已在代码中实现，但没有交付文档；本文件补齐证据，状态改为 in-review。

# APP-M2-T106：批量确认（星号 / 废标 / 资格禁用）与置信度高亮

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T106 |
| 代码解释 | [APP-M2-T106](../code/APP-M2-T106.md) |
| 验收 | 2026-10-30：星号、废标、资格三类不出现批量确认；含“详见/参照”引用的条目不能批量确认；低置信度条目按公司阈值标橙 |
| 项目进度 | 看板与任务卡同步为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T106](../tasks/APP-M2.md#app-m2-t106)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)

## 实际文件
- `frontend/web/src/project/ParseTab.tsx`
- `frontend/web/src/project/parse-review-core.ts`
- `backend/bid-core/icg/api/workflow.py`
- `backend/bid-core/icg/domain/parse_review.py`

## 测试证据
- `tests/backend/test_parse_review.py::test_star_disqualification_and_qualification_cannot_be_batch_confirmed`
- `frontend/web/tests/unit/parse-review-core.test.mjs（batch candidates / low confidence）`

验证命令：后端全量 `pytest tests/backend`（分两批）、前端 `pnpm lint && pnpm test`、E2E `run-e2e.sh`，均在提交前执行并通过。

## 未实现项与限制
无。
