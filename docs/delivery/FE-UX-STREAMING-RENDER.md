# FE-UX-STREAMING-RENDER 交付记录

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | FE-UX-STREAMING-RENDER |
| 代码解释 | [代码说明](../code/FE-UX-STREAMING-RENDER.md) |
| 验收 | tsc -b --noEmit 通过；生产构建通过；流式聚焦单测 27 passed；Playwright 模拟 SSE 2 passed（24.4s）；前端全量单测 647 passed / 14 failed，失败为既有 app-orchestration/evidence-orchestration/company-settings/dict-config 陈旧契约，未冒充通过 |
| 项目进度 | in-review。不得标 done，待 QA/PD/PM 验收 |
<!-- task-delivery:end -->

## 实际修改

移除 `.paper-wait` 不透明遮罩；新增 `StreamingPaperView` 与阶段呼吸胶囊、shimmer 骨架、稳定 key 渐显 chunk、渐变呼吸光标；流式期间 TipTap 不再随每个 reveal tick 整树重建。

## 验收证据

- `pnpm --dir frontend/web exec tsc -b --noEmit`：通过。
- `pnpm --dir frontend/web build`：通过。
- `node --test tests/unit/streaming-markdown.test.mjs tests/unit/section-stream.test.mjs tests/unit/text-reveal.test.mjs`：27 passed。
- `ICG_ALLOW_MEMORY=1 npx playwright test --config e2e/playwright.config.ts e2e/streaming-ux.spec.ts`：2 passed（24.4s）。
- `pnpm --dir frontend/web test`：647 passed / 14 failed；失败集中在既有 app-orchestration、evidence-orchestration、company-settings、dict-config 陈旧/test-double 契约，与本次流式改动无关，未冒充通过。

## 局限

真实模型阶段性耗时未做生产验收；胶囊首包前的准备态由前端本地状态呈现。
