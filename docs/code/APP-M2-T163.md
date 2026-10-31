# 代码说明：APP-M2-T163 锁定内容

为什么有这个文件：说明段落锁定的存储、识别方式和各写入路径的拦截点。

它解决什么问题：以后新增写正文的路径时，知道必须在哪里加核对，避免锁定被绕过。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T163 |
| 交付文件 | `docs/delivery/APP-M2-T163.md` |
| 影响模块 | `icg/domain/paragraph_locks.py`、`icg/api/paragraph_locks.py`、`icg/domain/domain.py`、`icg/domain/selection_rewrite.py`、`icg/domain/editor_ai_context.py`、`icg/domain/answer_card.py`、`icg/domain/human_queue.py`、`icg/domain/chapter_loop.py`、`frontend/web/src/editor/ParagraphLocksBar.tsx` |
<!-- code-explanation:end -->

## 存储与识别
锁记录在 `workflow["paragraph_locks"][chapter_id][paragraph_key]`：段落键、段落文字哈希（与 T161 相同算法）、开头 60 字、原因、锁定人、时间、锁定时版本。识别锁定段落靠哈希而不是键：段落挪了位置哈希不变，读取时按哈希在当前正文里重新对上键与行号（`public_locks`、`mark_locked`、`locked_lines`）。同一文字出现多次时按 `Counter` 逐个扣减。

## 拦截点
- `refuse_locked_change(state, chapter, new_content)`：新正文的块哈希里必须原样包含每个锁定段落，否则 409 `PARAGRAPH_LOCKED`，details 列出段落开头与锁定人。调用处：`DemoService.commit_version`、`SelectionRewriteService.apply`（先提交草稿时与写入样例时各一次）、`accept_ai_suggestion`、`insert_answer_card`。
- `violations(...)`：`_auto_commit_draft` 用它判断，草稿改动了锁定段落时不自动提交，草稿保留。
- `refuse_locked_selection(state, chapter, start, end)`：`SelectionRewriteService.prepare` 在选区校验之后、调用模型之前调用；选区所有行都在锁定段落内与部分在内分别提示（details.partial）。
- 章节循环：`recheck_chapter` 把 `locked_lines` 传给 `LoopContext.locked_paragraphs`；`check_paragraphs` 对这些行上原本可自动修的问题改为转人工，原因 `PARAGRAPH_LOCKED`（“段落已被人工锁定”）。

## 权限
锁定：`_chapter_writer`（角色、章节分工、分册未定稿）且非系统生成章节，`base_revision` 须为当前版本。解锁：锁定人或项目负责人（`project_access.lead`），只读角色先被 `ensure_not_readonly` 拒绝。锁与解锁写审计 `paragraph.lock` / `paragraph.unlock`。

## 前端
`ParagraphLocksBar` 放在编辑台工具栏：按光标位置（`paragraphAtOffset`）锁定所在段落，有未提交修改时禁用并说明原因；弹出列表显示锁定段落与解除按钮（`can_unlock`）。`editor-conflict.isRevisionConflict` 对 `PARAGRAPH_LOCKED`、`PARAGRAPH_ALREADY_LOCKED`、`SYSTEM_CHAPTER_READONLY` 返回 false，这类 409 显示原提示，不进入版本冲突合并。
