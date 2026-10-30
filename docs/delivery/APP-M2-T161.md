为什么有这个文件：记录 APP-M2-T161 章节加载与段落键的实际交付和测试证据。

它解决什么问题：说明正文现在有跨版本不变的段落键与逐段来源，存进每个版本，MySQL 重新加载后不丢；也写清还没做的部分。

# APP-M2-T161：章节加载与段落键

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T161 |
| 代码解释 | [APP-M2-T161](../code/APP-M2-T161.md) |
| 验收 | 2026-10-30：正文按导出同一套分块切成标题、段落、列表项、表格；每块有段落键并存入版本；改几个字、在前面插段、删段后其他块键不变；逐块来源（人工编写、对话助手写入、粘贴自对话助手、章节循环修正、系统生成）随版本保存；`GET /api/chapters/{id}` 与版本列表返回段落表；MySQL 版本表新增 meta 列，写入方式与段落键重新加载后仍在 |
| 项目进度 | 看板与任务卡改为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T161](../tasks/APP-M2.md#app-m2-t161)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)；看板工作包 WP-1

## 实际文件
- `backend/bid-core/icg/domain/paragraph_keys.py`（新）
- `backend/bid-core/icg/domain/domain.py`、`backend/bid-core/icg/domain/schemas.py`
- `backend/bid-core/icg/infra/repositories/chapters.py`、`backend/bid-core/icg/infra/repositories/mysql_repository.py`
- `backend/bid-core/alembic/versions/0014_chapter_version_meta.py`（新）
- `spec/openapi/demo-v1.json`
- `frontend/web/src/editor/paragraph-keys.ts`（新）、`frontend/web/src/editor/CiteCapsule.tsx`、`frontend/web/src/editor/EditorPage.tsx`、`frontend/web/src/shared/types.ts`

## 测试证据
- `tests/backend/test_paragraph_keys.py`：分块、改/插/删后键稳定、整段换掉算新段、五种来源、同一历史重算结果相同、接口返回、MySQL 重新加载（`-m mysql`）
- `frontend/web/tests/unit/paragraph-keys.test.mjs`：多行块归属、来源标签、正文本地改动后不套用旧行号
- 全量：后端两批、MySQL 套件、前端 lint/test/build、E2E 28 项，提交前执行并通过

## 未实现项与限制
- 编辑区仍是纯文本框。来源标签只在只读和未取得编辑权的视图显示；编辑中的文本框没有逐段标记。结构化编辑器、段落锁定（T163）、变量节点（T164）、问题标注联动（T166）在后续卡做。
- 检查结果仍按行号定位问题，尚未改用段落键（T166）。
- 采纳整章生成稿时走普通提交，来源记为“人工编写”；生成稿的逐段来源要等生成稿采纳流程改造后再分。
- 卡片原交接约束里的三种宽度截图、与 04a 并排截图属于 T160 布局卡，本卡未做。
