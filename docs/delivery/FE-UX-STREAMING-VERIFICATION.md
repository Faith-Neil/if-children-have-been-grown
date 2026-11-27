# FE-UX-STREAMING-VERIFICATION 交付记录

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | FE-UX-STREAMING-VERIFICATION |
| 代码解释 | [代码说明](../code/FE-UX-STREAMING-VERIFICATION.md) |
| 验收 | tsc -b --noEmit 通过；生产构建通过；流式聚焦单测 27 passed；Playwright 模拟 SSE 2 passed（24.4s）；前端全量单测 647 passed / 14 failed，失败为既有 app-orchestration/evidence-orchestration/company-settings/dict-config 陈旧契约，未冒充通过 |
| 项目进度 | in-review。不得标 done，待 QA/PD/PM 验收 |
<!-- task-delivery:end -->

## 实际修改

新增 streaming-markdown 单测、task.patched 阶段映射单测、text-reveal 速率/纸面契约更新；新增 `streaming-ux.spec.ts`，用模拟 SSE 验证阶段胶囊、表格中间态、加粗下划线、长文滚动、回到底部、完成交接与失败回滚。

## 验收证据

- `pnpm --dir frontend/web exec tsc -b --noEmit`：通过。
- `pnpm --dir frontend/web build`：通过。
- `node --test tests/unit/streaming-markdown.test.mjs tests/unit/section-stream.test.mjs tests/unit/text-reveal.test.mjs`：27 passed。
- `ICG_ALLOW_MEMORY=1 npx playwright test --config e2e/playwright.config.ts e2e/streaming-ux.spec.ts`：2 passed（24.4s）。
- `pnpm --dir frontend/web test`：647 passed / 14 failed；失败集中在既有 app-orchestration、evidence-orchestration、company-settings、dict-config 陈旧/test-double 契约，与本次流式改动无关，未冒充通过。

## 局限

模拟 SSE 只验证前端流式 UX，不代表真实模型或 RAGFlow 生产验收；全量前端单测仍有 14 条既有失败。
