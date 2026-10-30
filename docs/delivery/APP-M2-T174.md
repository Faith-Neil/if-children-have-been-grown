为什么有这个文件：记录 APP-M2-T174 提交版本与版本历史的交付事实。

它解决什么问题：提交、草稿、心跳、超时提示此前已在 T172/T173 交付，本卡补上版本历史里的修改方式与段落表，说明还缺什么。

# APP-M2-T174：提交版本与版本历史

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T174 |
| 代码解释 | [APP-M2-T174](../code/APP-M2-T174.md) |
| 验收 | 2026-10-30：“提交本节”生成正式版本并清掉本人草稿、通知他人草稿过期；版本列表（新版本在前）显示版本号、修改方式（手改、对话助手替换/插入、采纳 AI 建议、插入答案卡、章节循环修正、系统生成、版本回退、自动提交）、提交账号与时间；每个版本带段落键与逐段来源；MySQL 重新加载后写入方式不丢（T161 的 meta 列）。心跳只在有操作时发送、释放前 5 分钟提示见 T172/T173 |
| 项目进度 | 看板与任务卡改为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T174](../tasks/APP-M2.md#app-m2-t174)
- 相关交付：[APP-M2-T161](APP-M2-T161.md)、APP-M2-T172（见任务卡）、[APP-M2-T173](APP-M2-T173.md)、[APP-M2-T175](APP-M2-T175.md)

## 实际文件
- `backend/bid-core/icg/domain/schemas.py`（`VersionRecordResponse` 声明 `version_origin`、`edit_mode`、`source`、`rollback_from`、`note`、`paragraphs`）
- `frontend/web/src/editor/EditorDiffDrawer.tsx`、`frontend/web/src/editor/version-compare.ts`

## 测试证据
- `tests/backend/test_demo.py`（提交、草稿、租约、接管相关用例）、`tests/backend/test_paragraph_keys.py`（版本带段落表）、`tests/backend/test_version_rollback.py`（版本列表读回修改方式）
- `frontend/web/tests/unit/version-compare.test.mjs`（修改方式标签）、`frontend/web/tests/unit/autosave-core.test.mjs`（心跳与超时提示）

## 未实现项与限制
- 版本列表显示提交账号 ID，未换成姓名。
