为什么有这个文件：记录 APP-M2-T108 “确认解析结果”闸门（悬停列未满足项） 的实际交付和测试证据。

它解决什么问题：2026-10-30 看板整治核对后，本卡功能已在代码中实现，但没有交付文档；本文件补齐证据，状态改为 in-review。

# APP-M2-T108：“确认解析结果”闸门（悬停列未满足项）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T108 |
| 代码解释 | [APP-M2-T108](../code/APP-M2-T108.md) |
| 验收 | 2026-10-30：存在上传文件未全部解析成功（含解析失败）、待处理冲突、未处理疑似遗漏、关键条目未逐条确认时按钮不可用，悬停列出每项还差几条；未解析引用只提示 |
| 项目进度 | 看板与任务卡同步为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T108](../tasks/APP-M2.md#app-m2-t108)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)

## 实际文件
- `frontend/web/src/project/ParseTab.tsx`
- `frontend/web/src/project/parse-review-core.ts`
- `backend/bid-core/icg/domain/parse_review.py`

## 测试证据
- `tests/backend/test_parse_review.py::test_confirm_gates_are_listed_and_enforced（参数化覆盖冲突、遗漏、星号、文件未解析完四个闸门）`
- `frontend/web/tests/unit/parse-review-core.test.mjs（gate summary）`

验证命令：后端全量 `pytest tests/backend`（分两批）、前端 `pnpm lint && pnpm test`、E2E `run-e2e.sh`，均在提交前执行并通过。

## 未实现项与限制
无。
