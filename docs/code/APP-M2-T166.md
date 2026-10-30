# 代码说明：APP-M2-T166 问题标注与侧栏联动

为什么有这个文件：说明本章问题清单从哪几处来、怎样折算到段落键，以及前端定位与标记的接线。

它解决什么问题：以后新增产生问题的规则、换结构化编辑器或改检查批次时，知道段落键在哪里记、定位的顺序与边界。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T166 |
| 交付文件 | `docs/delivery/APP-M2-T166.md` |
| 影响模块 | `icg/domain/chapter_issues.py`、`icg/api/chapter_versions.py`、`icg/domain/check_orchestrator.py`、`icg/domain/chapter_loop.py`、`icg/domain/domain.py`、`frontend/web/src/editor/chapter-issues-core.ts`、`EditorIssuePanel.tsx`、`useChapterIssues.ts`、`issue-focus.ts`、`EditorPage.tsx`、`EditorAssistantPanel.tsx`、`CiteCapsule.tsx`、`project/ProjectPages.tsx` |
<!-- code-explanation:end -->

## 三处来源
`chapter_issues.chapter_issues(service, principal, project_id, chapter_id)`，权限同读取章节（`DemoService._chapter`），只读。
1. **检查批次**：`workflow.checks` 中 `volume` 等于本章分册或 `all` 的最近一条（按 `created_at`）。`stale` 与检查页同一口径：批次 `fingerprint` 不等于当前 `project_input_fingerprint`。处理路径按严重程度：阻断 `must_fix`、警告 `fix_or_release`、其他 `hint`；已放行的状态为 `released`。
2. **章节循环与人工处理队列**：`workflow.human_queue.issues` 中本章、非 `void` 的问题，状态与处理路径（`auto_fix` / `direct_human` / `escalated_human`）原样沿用。
3. **编辑后复查**：`chapter_edit_operations[].recheck.issues`（对话助手写入）与 `edit_rechecks`（粘贴识别，提交正文时写入）。只取版本号大于本章最近一次章节循环 `result_revision` 的记录，之前的已被循环覆盖。每条按写入的文字在当前正文中找段落，再用 `selection_rewrite.text_issues` 重跑：同一规则仍命中为 `open`，否则 `resolved`；段落找不到也算 `resolved`（写入的文字已被改掉）。

## 折算到段落键
`locate(blocks, key, quote, line, line_trusted)` 的顺序：
1. 问题产生时记下的 `paragraph_key` 仍在当前段落表里 → `key`；
2. 原句前 60 字（去掉末尾“…”）在当前正文中只出现在一个段落 → `quote`；
3. 只有正文版本没变时才认行号：检查批次看 `chapter_revisions[chapter_id] == chapter.revision`，队列看 `loop.result_revision == chapter.revision` 且问题未关闭 → `line`；
4. 有过位置信息但都对不上 → `none`（“原段落已改动或删除，未能定位”）；从来没有位置 → `chapter`（“整章问题”）。

段落表用 `paragraph_keys.current(chapter)`，与 `GET /api/chapters/{id}` 返回的 `paragraphs` 同源，所以前端拿到的键与正文 `data-paragraph-key` 一致。行号指 `content.split("\n")` 的下标（含空行），与 `paragraph_keys` 的 `line_start`/`line_end` 同一空间。

段落键在问题产生时记下：`check_orchestrator.run_check` 调 `annotate_check_issues`（只处理带 `details.paragraph_index` 的问题，即 R29、R30、R42 等）；`chapter_loop.record_loop` 对每条问题调 `key_for_line`。段落键随版本沿用（T161 的 `assign`），所以正文插入、移动段落后仍能找到；段落改动幅度超过一半会拿新键，这时靠原句匹配。

## 前端
- `useChapterIssues`：章节、正文版本、项目版本任一变化时重读；请求按序号丢弃过期结果；`takeIssueFocus` 取走检查页带来的问题后交给编辑台定位；定位高亮 4 秒后自动清除。
- `EditorPage.locateIssue`：持锁时用 `lineRangeOffsets` 把行号换成字符区间，`setSelectionRange` 选中整段并滚动编辑框；编辑中的文字与已提交正文不同则不选中、给提示。未持锁或只读视图用 `.rich-paragraph-with-cites p[data-paragraph-key=…]` 滚动到该段，`focusedKey` 让该段整段高亮。
- `RichParagraphWithCites`：`issueMarkers`（段落键 → 待处理数与最重等级）在段落首行前画标记，点标记调用 `onIssueMarkerClick`，侧栏筛选设为这一段。
- 持锁时编辑框 `onSelect` 用 `paragraphAtOffset` 算出光标所在段落键，侧栏把这一段的问题加框。
- 检查页 `locate`：有 `chapter_id` 时先 `requestIssueFocus(chapter_id, issue.id)`，再进入 `/projects/:id/editor/:chapterId`。

## 依赖与限制
无新依赖。检查批次的 `chapter_revisions` 与问题的 `paragraph_key` 只对之后跑的检查生效；更早的批次靠原句匹配。
