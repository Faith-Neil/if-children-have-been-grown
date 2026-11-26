# FE-UX-STREAMING-RENDER 代码说明

关联 Issue：ISSUE-058。

主要代码：`frontend/web/src/editor/StreamingPaperView.tsx`、`frontend/web/src/editor/PaperEditor.tsx`、`frontend/web/src/editor/section-stream.ts`、`frontend/web/src/editor/text-reveal.ts`、`frontend/web/src/shared/styles.css`。

关键决策：流式期间 `PaperEditor` 隐藏但保留同一个 TipTap 实例，正文由 `StreamingPaperView` 只读渲染；`task.patched` 进入前端事件模型并映射阶段文案；活跃尾部 chunk 使用起点稳定的 key，CSS 一次性渐显，光标以独立类淡出。
