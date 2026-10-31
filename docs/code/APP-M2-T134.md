# 代码说明：APP-M2-T134 队列详情单段编辑

为什么有这个文件：说明队列单段编辑的规则所在位置和前后端接线。

它解决什么问题：以后改编辑保护或队列页时，知道哪些规则在后台、前端哪里只是展示。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T134 |
| 交付文件 | `docs/delivery/APP-M2-T134.md` |
| 影响模块 | `queue_paragraph_edit.py`、`human_queue.py`、`api/chapter_loop.py`、`errors.py`、`frozen_error_codes.py`、`frontend/web/src/project/main-path-core.ts`、`ManualQueuePage.tsx`、`shared/types.ts` |
<!-- code-explanation:end -->

## 接线
- 写操作走 `WorkflowService._write`（动作名 `human.edit:{issue_id}`），同事务核对项目成员写权限、项目版本（If-Match）、幂等键并写审计。
- `edit_human_issue_paragraph` 先复用 `_issue_for_write`（问题须待处理、分册未定稿），再用与“标为已处理”相同的 `resolve` 权限；之后依次核对系统章节、章节版本、编辑权占用、`queue_edit_problem`（检查版本一致、段落存在、引文能对上）、锁定段落。
- 段落按 `chapter_loop.split_paragraphs`（按行）定位，与问题的 `paragraph_index` 同口径；只替换该行。
- 新章节版本的 `edit_mode` 为 `queue_paragraph`，带 `issue_id` 与 `paragraph_index`；循环记录里写 `queue_edit_revision`，使同一次检查的其他问题在这次改写后仍可编辑，而其他途径改正文则让问题失效。
- 前端按钮只看 `permissions.edit`；`paragraphEditProblem` 只是提交前预检，最终以后台为准。

## 约束
- `HumanIssueEditRequest` 为 extra=forbid；响应模型继承 `HumanIssueWriteResponse`；operationId `editHumanIssueParagraph` 全局唯一。
- 新错误码 `HUMAN_ISSUE_STALE`（409）已登记 `errors.py` 与 `frozen_error_codes.py`。

## 依赖与限制
无新依赖。限制见交付文档“未实现项与限制”。
