# FE-UX-VISUAL-TOKENS 代码说明

关联 Issue：ISSUE-057。

主要代码：`frontend/web/src/editor/EditorPage.tsx`、`frontend/web/src/editor/text-reveal.ts`、`frontend/web/src/project/ProjectListPage.tsx`、`frontend/web/src/project/CoverageView.tsx`、`frontend/web/src/project/coverage-live.ts`、`frontend/web/src/shared/styles.css`、`frontend/web/src/main.tsx`、`frontend/web/e2e/responsive-audit.spec.ts`。

关键决策：普通 busy/loading 不再触发“AI 正在撰写”；只有活跃 SSE 会话进入撰写态。列表排序、关键词和状态参数直接传后端，不回退全量客户端过滤。
