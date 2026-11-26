# FE-UX-STREAMING-MARKDOWN 代码说明

关联 Issue：ISSUE-058。

主要代码：`frontend/web/src/editor/streaming-markdown.ts`、`frontend/web/tests/unit/streaming-markdown.test.mjs`。

关键决策：解析器先把 Markdown 分成 heading/paragraph/list/table/table-placeholder/blank 块。行内扫描把未闭合粗体和下划线视为暂时闭合，把尾部半截 `*`、`<u`、`</u` 隐藏；表格首行未遇到分隔行时只产出占位块。
