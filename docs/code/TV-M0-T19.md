为什么有这个文件：解释 TV-M0-T19 写作助手改动的代码。

# TV-M0-T19 代码说明

| 文件 | 说明 |
|---|---|
| [technical_assistant.py](../../backend/bid-core/icg/domain/technical_assistant.py) | `section_context()` 取本节要点、评分标准、废标清单；`splice_section()` 只换一节正文；`precheck()` 跑废标约束检查；`TechnicalSectionAssistant.rewrite()` 生成按节候选 |
| [selection_rewrite.py](../../backend/bid-core/icg/api/selection_rewrite.py) | 问答请求增加 `section`；`POST /api/v1/projects/{project_id}/technical-sections/rewrite` |
| [assistant_qa.py](../../backend/bid-core/icg/domain/assistant_qa.py) | 有小节时检索词按本节，提示词带本节上下文 |
| [technical-assistant.ts](../../frontend/web/src/editor/technical-assistant.ts) | 小节列表、快捷指令、覆盖视图预填 |
| [EditorAssistantPanel.tsx](../../frontend/web/src/editor/EditorAssistantPanel.tsx) | 小节选择；问答走流式问答框；修改走按节候选，显示预检与来源 |
| [useEditorOperations.ts](../../frontend/web/src/editor/useEditorOperations.ts) | `suggestSection()` |
| [AssistantAskBox.tsx](../../frontend/web/src/editor/AssistantAskBox.tsx)、[SelectionRewritePanel.tsx](../../frontend/web/src/editor/SelectionRewritePanel.tsx) | 透传小节 |
| [CoverageView.tsx](../../frontend/web/src/project/CoverageView.tsx) | 「目标章节」写入预填后跳编辑台 |
