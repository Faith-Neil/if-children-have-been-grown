# 代码说明：APP-M2-T161 章节加载与段落键

为什么有这个文件：说明段落键怎么分配、存在哪里、谁在读。

它解决什么问题：以后段落锁定、变量节点、问题定位、版本对比都要按段落键找段落，先把规则写清楚。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T161 |
| 交付文件 | `docs/delivery/APP-M2-T161.md` |
| 影响模块 | `icg/domain/paragraph_keys.py`、`icg/domain/domain.py`、`icg/domain/schemas.py`、`icg/infra/repositories/chapters.py`、`icg/infra/repositories/mysql_repository.py`、`alembic/versions/0014_chapter_version_meta.py`、`frontend/web/src/editor/paragraph-keys.ts`、`frontend/web/src/editor/CiteCapsule.tsx` |
<!-- code-explanation:end -->

## 分块
`split(content)` 调用导出用的 `icg/infra/docx_markdown.blocks`，所以“一块”的定义和 Word 导出完全一致：一行一个标题、段落或列表项，表格（表头行 + 分隔行 + 数据行）整体一块；空行不算块。每块记 `line_start`/`line_end`（0 起，含两端）和去首尾空白后文字的哈希。

## 分键
`assign(chapter_id, previous, previous_content, content, version)`：
1. 用 `difflib.SequenceMatcher` 按块哈希比对上一版与新版。
2. `equal` 的块沿用原键与原来源。
3. `replace` 区间里逐个新块找最像的旧块（先用 `quick_ratio` 筛，最多看 30 个），相似度 ≥ 0.5 沿用原键，配对保持先后顺序。
4. 其余块拿新键 `pk-{章节}-r{首次出现的版本号}-{序号}`。键只由历史决定，所以 `ensure(chapter)` 给缺段落表的旧版本补算时结果与当初一致。

## 来源
改动块的来源取本次写入方式 `version_source(version)`：`source=system_generated` → 系统生成；`source=chapter_loop` → 章节循环修正；`version_origin` 为 `assistant_edit`/`ai_polish_accepted` → 对话助手写入；其余为人工编写。粘贴识别（`paragraph_sources` 里 `assistant_pasted` 的行号）覆盖到的块记“粘贴自对话助手”。未改动的块保留上一版来源。

## 存取
- 读：`DemoService.chapter` 返回 `paragraphs`（`current()`：最新版本内容与正文一致时用其段落表，否则按正文补算）；`versions` 先 `ensure` 再返回每版的段落表。
- 写：各写入路径照旧往 `chapter.versions` 追加记录；MySQL `save_chapter` 插入新版本行前调用 `ensure`，把正文以外的字段（写入方式、粘贴识别、段落键）序列化进 `meta` 列；`read_chapter` 与 `_load_shared` 读回时合并。旧行 `meta` 为空，读回后按版本链补算。

## 前端
`paragraph-keys.ts` 把段落表转成“行号 → 段落”映射；`RichParagraphWithCites` 给每行加 `data-paragraph-key`，非人工段落首行显示来源标签。只有当前文字与已提交正文一致时才传段落表，避免本地改动后行号错位。

## 限制
见交付文档“未实现项与限制”。
