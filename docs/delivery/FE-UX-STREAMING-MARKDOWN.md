# FE-UX-STREAMING-MARKDOWN 交付记录

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | FE-UX-STREAMING-MARKDOWN |
| 代码解释 | [代码说明](../code/FE-UX-STREAMING-MARKDOWN.md) |
| 验收 | tsc -b --noEmit 通过；生产构建通过；流式聚焦单测 21 passed；Playwright 模拟 SSE 2 passed（24.1s）；前端全量单测 647 passed / 14 failed，失败为既有 app-orchestration/evidence-orchestration/company-settings/dict-config 陈旧契约，未冒充通过 |
| 项目进度 | in-review。不得标 done，待 QA/PD/PM 验收 |
<!-- task-delivery:end -->

## 实际修改

新增 `streaming-markdown.ts` 纯函数：尾部未闭合 `**` 与 `<u>` 安全闭合、半截标记隐藏、孤立井号暂缓渲染、未到分隔行的表格渲染柔和占位，分隔行到达后转为正式表格。

## 验收证据

- `pnpm --dir frontend/web exec tsc -b --noEmit`：通过。
- `pnpm --dir frontend/web build`：通过。
- `node --test tests/unit/streaming-markdown.test.mjs tests/unit/section-stream.test.mjs tests/unit/text-reveal.test.mjs`：21 passed。
- `ICG_ALLOW_MEMORY=1 npx playwright test --config e2e/playwright.config.ts e2e/streaming-ux.spec.ts`：2 passed（24.1s）。
- `pnpm --dir frontend/web test`：647 passed / 14 failed；失败集中在既有 app-orchestration、evidence-orchestration、company-settings、dict-config 陈旧/test-double 契约，与本次流式改动无关，未冒充通过。

## 局限

表格单元格当前按纯文本渲染，不在本卡扩展复杂嵌套行内语法。
