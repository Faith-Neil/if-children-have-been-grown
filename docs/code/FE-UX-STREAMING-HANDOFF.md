# FE-UX-STREAMING-HANDOFF 代码说明

关联 Issue：ISSUE-058。

主要代码：`frontend/web/src/editor/PaperEditor.tsx`、`frontend/web/src/editor/EditorPage.tsx`。

关键决策：滚动容器用 scroll 事件记录是否仍在 24px 钉底范围；只有仍钉底时才在 markdown 增长后补底。用户上翻后出现 sticky 半透明回到底部按钮。完成时先等 reveal settled，再读取服务端章节，在 `useLayoutEffect` 绘制前写入 TipTap并恢复 scrollTop，最后结束流式画布。
