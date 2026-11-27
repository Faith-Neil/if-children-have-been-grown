# FE-UX-STREAMING-HANDOFF 交付记录

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | FE-UX-STREAMING-HANDOFF |
| 代码解释 | [代码说明](../code/FE-UX-STREAMING-HANDOFF.md) |
| 验收 | tsc -b --noEmit 通过；生产构建通过；流式聚焦单测 27 passed；Playwright 模拟 SSE 2 passed（24.4s）；前端全量单测 647 passed / 14 failed，失败为既有 app-orchestration/evidence-orchestration/company-settings/dict-config 陈旧契约，未冒充通过 |
| 项目进度 | done。用户验收 PR #55 后按指令收口，ISSUE-058 closed；未发布 |
<!-- task-delivery:end -->

## 实际修改

保留 跟随活跃写作光标和用户上翻不拉回；流式离开底部显示“定位到正在撰写”；完成后 reveal settled、服务端正式正文在绘制前写入 TipTap并恢复滚动位置；光标先 220ms 淡出再交接；失败/取消回滚原正文并给提示。

## 验收证据

- `pnpm --dir frontend/web exec tsc -b --noEmit`：通过。
- `pnpm --dir frontend/web build`：通过。
- `node --test tests/unit/streaming-markdown.test.mjs tests/unit/section-stream.test.mjs tests/unit/text-reveal.test.mjs`：27 passed。
- `ICG_ALLOW_MEMORY=1 npx playwright test --config e2e/playwright.config.ts e2e/streaming-ux.spec.ts`：2 passed（24.4s）。
- `pnpm --dir frontend/web test`：647 passed / 14 failed；失败集中在既有 app-orchestration、evidence-orchestration、company-settings、dict-config 陈旧/test-double 契约，与本次流式改动无关，未冒充通过。

## 局限

浏览器测试验证了无白屏交接与滚动位置，未用真实长时模型会话复测。
