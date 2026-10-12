为什么有这个文件：记录Playwright端到端检查的交付。

它解决什么问题：说明依赖范围、运行命令、覆盖与发现的缺陷。

# REV-M0-T06：Playwright端到端检查交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | REV-M0-T06 |
| 代码解释 | [代码解释](../code/REV-M0-T06.md)；新增测试文件与仅测试依赖，未改应用代码 |
| 验收 | `pnpm --dir frontend/web e2e`约40秒，11项按预期（7正向通过、4已知缺陷test.fail）；见[记录](../testing/2026-10-12-e2e-t001-signoff.md) |
| 项目进度 | 354项；本卡in-review，待项目经理确认 |
<!-- task-delivery:end -->

## 关联与状态

- 2026-10-12；[ISSUE-019](../../issues/ISSUE-019.md)；[任务卡](../tasks/REV-M0.md#rev-m0-t06)；PR #3待合入，未发布。

## 完成内容与变更文件

`frontend/web/package.json`（devDependencies `@playwright/test` 1.64.0、`e2e`脚本）、`frontend/web/pnpm-lock.yaml`、`frontend/web/e2e/playwright.config.ts`、`frontend/web/e2e/app-shell.spec.ts`、3张截图`docs/testing/assets/e2e-*.png`；同步ISSUE-019、issues/index、REV-M0任务卡、TASK_BOARD、PROJECT_STATUS、DOCUMENT_INDEX。

## 同步与剩余

PRD/ROADMAP/ARCHITECTURE/BRIEF无影响（只加测试依赖）。导出过期与版本冲突页面提示未覆盖。用户与项目经理确认 D3/D4 修复后，offline-check 的 `e2e` 作业改为必需，失败会阻断工作流。本卡仍为 in-review，不标 done。
