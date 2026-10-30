为什么有这个文件：记录 APP-M2-T163 锁定内容（段落锁定）的实际交付和测试证据。

它解决什么问题：说明锁定段落在哪些写入路径被后台拒绝改动、谁能锁和解锁、页面怎么显示，以及还没覆盖的锁定内容。

# APP-M2-T163：锁定内容

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T163 |
| 代码解释 | [APP-M2-T163](../code/APP-M2-T163.md) |
| 验收 | 2026-10-30：有本节编辑权的人按段落键锁定段落；手改提交、对话助手写入（含写入前先提交的草稿）、AI 建议采纳、答案卡插入改动或删除锁定段落时后台返回 409 PARAGRAPH_LOCKED，挪位置允许；锁释放/接管/超时时改动了锁定段落的草稿不自动提交；对话助手选区落在锁定段落上不调用模型（整段在锁定段落内、跨锁定段落两种提示）；章节循环重新检查时锁定段落的问题不自动修，转人工“段落已被人工锁定”；只有锁定人或项目负责人能解锁；只读成员不能锁；系统生成章节整章只读，仍按原规则拒绝 |
| 项目进度 | 看板与任务卡改为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T163](../tasks/APP-M2.md#app-m2-t163)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)；看板工作包 WP-1；依赖 [APP-M2-T161](APP-M2-T161.md) 段落键

## 实际文件
- `backend/bid-core/icg/domain/paragraph_locks.py`（新）、`backend/bid-core/icg/api/paragraph_locks.py`（新）
- 写入路径接入：`icg/domain/domain.py`（提交、草稿自动提交、章节读取标锁定）、`icg/domain/selection_rewrite.py`、`icg/domain/editor_ai_context.py`、`icg/domain/answer_card.py`、`icg/domain/human_queue.py`、`icg/domain/chapter_loop.py`
- 错误码：`PARAGRAPH_LOCKED`、`PARAGRAPH_ALREADY_LOCKED`（`errors.py`、`frozen_error_codes.py`）
- 前端：`frontend/web/src/editor/ParagraphLocksBar.tsx`（新）、`paragraph-keys.ts`、`CiteCapsule.tsx`、`EditorPage.tsx`、`editor-conflict.ts`（409 的锁定与系统章节拒绝不再按版本冲突走合并流程）
- `spec/openapi/demo-v1.json`

## 测试证据
- `tests/backend/test_paragraph_locks.py`：改动与删除被拒、挪位置可提交；解锁权限（他人 403、锁定人与负责人可解）；只读成员不能锁；版本不对与重复锁定；草稿自动提交跳过；对话助手选区整段/跨段拒绝；章节循环转人工；新项目首次锁定后工作区仍可读
- `frontend/web/tests/unit/paragraph-keys.test.mjs`：光标定位段落、锁定按钮禁用原因
- `frontend/web/e2e/paragraph-lock.spec.ts`：浏览器里锁定 → 改动锁定段落提交被拒且正文不变 → 只改其他段可提交 → 解除锁定
- 全量：后端两批、MySQL 套件、前端 lint/test/build、E2E 29 项

## 未实现项与限制
- 编辑中的文本框不能把锁定段落灰显，改为在文本框上方列出锁定段落；只读与未持锁视图灰底并标“已锁定 · 锁定人”。
- “招标原文引用段”还没有段落来源类型，未纳入锁定；要等生成稿逐段来源（T161 限制）补上后再接。
- 整章重新生成后的采纳走普通提交：生成稿缺少锁定段落时提交被拒，不会自动把锁定段落并回生成稿。
- 版本回退（T175）尚未实现，实现时须同样调用 `refuse_locked_change`。
