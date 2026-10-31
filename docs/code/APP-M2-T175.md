# 代码说明：APP-M2-T175 版本对比与回退

为什么有这个文件：说明回退的核对顺序、版本记录与前端逐段对比的算法。

它解决什么问题：复审时能看出回退没有绕过手改提交的任何核对，段落追溯没有断。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T175 |
| 交付文件 | `docs/delivery/APP-M2-T175.md` |
| 影响模块 | `icg/domain/version_rollback.py`、`icg/api/chapter_versions.py`、`icg/domain/paragraph_keys.py`、`frontend/web/src/editor/version-compare.ts`、`frontend/web/src/editor/EditorDiffDrawer.tsx` |
<!-- code-explanation:end -->

## 后台
`VersionRollbackService.rollback` 在一个事务里依次核对：章节属于项目 → `_chapter_writer`（角色、分工、分册定稿）→ `_lease`（本人本会话的有效编辑锁）→ `_revision`（基于最新版本）→ `refuse_manual_edit`（系统章节）→ 目标版本存在且与当前不同 → `refuse_locked_change`（锁定段落）→ `_writing_input`（来源依据指纹）→ 本人没有与正文不同的草稿。通过后追加版本 `{version_origin: rollback, edit_mode: rollback, rollback_from, note, rollback_paragraphs}`，通知草稿过期的其他人，写审计 `version.rollback`。

`rollback_paragraphs` 是目标版本的段落键、哈希与来源；`paragraph_keys.assign` 对未与上一版对上的块，按哈希从中取回原键和原来源（键未被占用时），所以回来的段落还是原来那一段。版本列表接口不返回这个内部字段。

## 前端
`compareVersions(older, newer)` 按段落键对上：两边都有且文字相同为“未改”，文字不同为“改动”并用 `diffText` 逐字标增删，只在新版本有为“新增”，只在旧版本有为“删除”并插在它原来前一段之后。`EditorDiffDrawer` 的版本卡片显示 `versionModeLabel`；“回退到此版本”经 `Popconfirm` 确认后调用接口，`rollbackBlocker` 给出禁用原因（未持锁、当前版本、有未提交修改、系统章节）。成功后重新读取章节与版本列表。
