为什么有这个文件：解释写作助手双模式如何挂到编辑台。

它解决什么问题：避免助手在初稿前抢主路径，或问答模式误写正文。

# TV-M0-T14 代码说明

- `EditorAssistantPanel.tsx`：`technicalAssistant` / `draftReady` / `generating`；模式按钮与芯片。
- `EditorPage.tsx`：技术分册传入上述门控；标书修改仍复用 `onSuggest` + diff 写入。
