# FE-UX-STREAMING-VERIFICATION 代码说明

关联 Issue：ISSUE-058。

主要代码：`frontend/web/tests/unit/section-stream.test.mjs`、`frontend/web/tests/unit/text-reveal.test.mjs`、`frontend/web/tests/unit/streaming-markdown.test.mjs`、`frontend/web/e2e/streaming-ux.spec.ts`。

关键决策：单元测试覆盖解析、事件、速率和 key 稳定；Playwright 通过 route 模拟 SSE 与工作区大纲，不调用真实模型，验证浏览器中的胶囊、表格占位、滚动按钮、完成交接与失败提示。
