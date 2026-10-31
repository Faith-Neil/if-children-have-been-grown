# 代码说明：APP-M2-T174 提交版本与版本历史

为什么有这个文件：说明版本记录里有哪些字段、页面怎么显示。

它解决什么问题：各写入路径往版本里写的元数据不同，页面要统一成一种“修改方式”。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T174 |
| 交付文件 | `docs/delivery/APP-M2-T174.md` |
| 影响模块 | `icg/domain/schemas.py`、`frontend/web/src/editor/version-compare.ts`、`frontend/web/src/editor/EditorDiffDrawer.tsx` |
<!-- code-explanation:end -->

## 字段来源
- 手改提交 `commit_version`：无 `version_origin`（视为手改），粘贴识别时带 `paragraph_sources`。
- 草稿自动提交：`version_origin/edit_mode = manual`，`note = 自动提交（原因）`。
- 对话助手：`version_origin = assistant_edit`，`edit_mode = assistant_replace / assistant_insert / insert_answer_card`；采纳 AI 建议为 `ai_polish_accepted / accept_ai_suggestion`。
- 章节循环 `source = chapter_loop`；系统章节 `source = system_generated`；回退 `edit_mode = rollback` 与 `rollback_from`。

`versionModeLabel` 按 `source` → 回退 → 自动提交 → `edit_mode` → `version_origin` 的顺序取中文名。
