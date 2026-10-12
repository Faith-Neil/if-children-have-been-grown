为什么有这个文件：记录橙色状态标签对比这一轮实际改了什么。

它解决什么问题：避免把本地样式通过写成已经发布，或写成新开了一张任务卡。

# ISSUE-036：橙色状态标签对比度

日期 2026-10-12。关联 [ISSUE-036](../../issues/ISSUE-036.md)。负责人 frontend。优先级 P3。状态 in-review。不新增任务卡。分支 `codex/repository-foundation`。[PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3) 仍待合入，未发布。

## 完成内容与变更文件

`frontend/web/src/styles.css` 把 `.ant-tag-orange`、`.ant-tag-gold`、`.ant-tag-warning` 的文字色设为已有的 `#9a5608`。浅底不动。`!important` 用来压过 Ant Design 运行时样式。`frontend/web/e2e/app-shell.spec.ts` 的既有 4.5:1 检查加上当前可见的这三类标签。

未改 `backend/`、`tests/backend/`、`spec/openapi/`、`docs/reference/` 与 `package.json`。未新增依赖。未把任何 APP 卡标 done。同一提交另按项目经理确认把 APP-M2-T114 与 REV-M0-T22 标为 done（QA f521950，PM 17:13 确认）。ISSUE-033 不关闭。

## 代码解释

入口和限制见 [代码解释](../code/ISSUE-036.md)。

## 验收结果

见 [核对](../testing/2026-10-12-issue-036-orange-contrast.md)。

## 项目进度

不新增任务卡。并入 REV-M0-T23、T24 后，看板因 T114 与 REV-M0-T22 曾改为 381 项：47 done、9 in-review、7 in-progress、265 planned、49 blocked、4 ready。项目经理随后确认 T078 与 REV-M0-T24 为 done（QA 19c4862，PM 17:20 确认），T124 改为 ready。当前看板为 381 项：49 done、7 in-review、7 in-progress、265 planned、48 blocked、5 ready。本 Issue 为 in-review，不标 closed。未合入，未发布。
