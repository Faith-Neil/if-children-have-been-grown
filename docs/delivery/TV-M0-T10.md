为什么有这个文件：记录工单 3（矩阵后台化 + 覆盖视图）实际改了什么。

它解决什么问题：避免技术分册仍把矩阵确认当操作中心。

# TV-M0-T10 交付

| 项 | 内容 |
|---|---|
| 任务 | [TV-M0-T10](../tasks/TV-M0.md#tv-m0-t10) |
| Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 日期 | 2026-11-05 |
| 状态 | in-review。建议 PM 在 QA/PD 签署后再标 done；本 Agent 不标 done |
| 代码解释 | [TV-M0-T10](../code/TV-M0-T10.md) |

## 实际变更

- `coverageSummary`：覆盖/缺口/偏离/无依据统计。
- 技术分册 Matrix 页改为覆盖视图文案与指标；去掉「确认历史做法」；编辑态隐藏「人工确认」。
- 页签「分析」→「覆盖视图」；技术分册 analyze 页不再叠 Parse 页。
- `guard_technical_confirm` 文案改为「标确认」语义，不再暗示挡生成。

## 验收证据

- `pnpm --dir frontend/web exec node --test tests/unit/matrix-core.test.mjs`（含 coverageSummary）。
- 未宣称：双库强制检索（工单 4）、质量八条（工单 5）、Figma 编辑台（工单 6）、写作助手（工单 7）。

## 项目进度

工单 3 实现已到 in-review。下一张：工单 4 双库 RAG。分支仍不合 main。

## 基线同步

| 基线 | impact | 同步 |
|---|---|---|
| PRD / ROADMAP | 有影响 | 最短路径指针 |
| ARCHITECTURE | 有影响 | 矩阵后台化 |
| TASK_BOARD / PROJECT_STATUS / DOCUMENT_INDEX / Issue | 有影响 | 本轮已更新 |
| 参考原文 | 无影响 | 不改 |
