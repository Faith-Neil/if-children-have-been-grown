为什么有这个文件：解释 TV-M0-T21 修改候选数字预检与问答按小节分会话的代码。

# TV-M0-T21 代码说明

| 文件 | 说明 |
|---|---|
| [technical_assistant.py](../../backend/bid-core/icg/domain/technical_assistant.py) | `number_check()`：本节需求用 `technical_volume.inconsistent()` 查偏离类型与数字（与写入后同一规则）；`COMMITMENT` 抽带单位的承诺数字，候选里有而原文、本章其他正文、需求与评分、要点、已确认事实、检索片段里都没有的列为 `unsupported`；`rewrite()` 返回 `numbers` |
| [selection_rewrite.py](../../backend/bid-core/icg/api/selection_rewrite.py) | `SectionNumberCheck`；`TechnicalSectionCandidate.numbers`；会话摘要加 `section_key`、`section_title`；会话列表可按 `section` 过滤 |
| [assistant_sessions.py](../../backend/bid-core/icg/domain/assistant_sessions.py) | 新会话记小节键与标题；`list_sessions()` 按小节过滤 |
| [assistant_qa.py](../../backend/bid-core/icg/domain/assistant_qa.py) | 先解析小节再校验续问：会话小节键与本次小节不同时 403；记录回答时带小节 |
| [technical-assistant.ts](../../frontend/web/src/editor/technical-assistant.ts) | `sessionsForSection()`、`numberIssues()` |
| [SelectionRewritePanel.tsx](../../frontend/web/src/editor/SelectionRewritePanel.tsx) | 会话下拉只列当前小节的会话；换小节回到新会话 |
| [EditorAssistantPanel.tsx](../../frontend/web/src/editor/EditorAssistantPanel.tsx) | 候选数字需核对时显示提示与「已核对」勾选，勾选前不能写入 |
