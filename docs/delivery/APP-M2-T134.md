为什么有这个文件：记录 APP-M2-T134 队列详情单段编辑的实际交付和测试证据。

它解决什么问题：说明做到什么、没做什么，避免把未运行的测试或未接真实模型的结果当作已验收。

# APP-M2-T134：队列详情单段编辑

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T134 |
| 代码解释 | [APP-M2-T134](../code/APP-M2-T134.md) |
| 验收 | 2026-11-02：新增 `POST /api/v1/projects/{project_id}/human-queue/issues/{issue_id}/edit`（`editHumanIssueParagraph`）。有处理权的人在人工处理队列里直接改写问题所在的那一段：只替换该段，其余段落逐字不变；生成新章节版本（来源记为队列单段修改）并写审计，同时把该问题标为“人工已处理（已修改正文）”。后台拒绝：只读成员与额外承诺/披露类越权（403）、他公司项目（404）、章节版本已变（409 REVISION_CONFLICT）、本节正被编辑（409 CHAPTER_IN_USE）、系统生成章节（409 SYSTEM_CHAPTER_READONLY）、分册已定稿（409 VOLUME_FINALIZED）、改动锁定段落（409 PARAGRAPH_LOCKED）、检查后正文已变或段落对不上（新增 409 HUMAN_ISSUE_STALE）、空内容、多行、超长、与原文相同（422）。队列返回每个问题的 `permissions.edit` 与当前段落全文 `paragraph_text`，章节组返回 `chapter_revision`；页面“改写本段”按钮只看后台的 `permissions.edit`。改写不代替重新检查，本节循环记录仍显示需复查。 验证见 [验证记录](../testing/2026-11-02-wp5-batch2-sla-queue-edit.md) |
| 项目进度 | 看板与任务卡改为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T134](../tasks/APP-M2.md#app-m2-t134)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 依据：PRD v1.8 §5.7.7

## 实际文件
- `queue_paragraph_edit.py`：`QueueParagraphEditMixin.edit_human_issue_paragraph`、`queue_edit_problem`
- `human_queue.py`：`HumanQueueMixin` 继承该混入；`_issue_permissions` 增加 `edit`，`_public_issue` 返回 `paragraph_text`，队列章节组返回 `chapter_revision`
- `api/chapter_loop.py`：`HumanIssueEditRequest`、`HumanIssueEditResponse`、路由 `editHumanIssueParagraph`
- `errors.py`、`frozen_error_codes.py`：新增 `HUMAN_ISSUE_STALE`（409）
- 前端：`main-path-core.ts`（`queuePaths.edit`、`paragraphEditProblem`、`paragraphEditPayload`）、`ManualQueuePage.tsx`、`shared/types.ts`

## 测试证据
- `tests/backend/test_human_queue.py`：`test_queue_edit_rewrites_only_that_paragraph_and_resolves_the_issue`、`test_queue_edit_rejects_stale_revision_empty_multiline_and_unchanged`、`test_queue_edit_denied_for_readonly_and_for_other_company`、`test_queue_edit_refused_when_chapter_is_being_edited_or_text_changed_after_check`、`test_queue_edit_refuses_changing_a_locked_paragraph`；原有两处权限断言随新增 `edit` 字段更新
- `frontend/web/tests/unit/main-path-core.test.mjs`：预检、请求体、接线
- `frontend/web/e2e/queue-paragraph-edit.spec.ts`：负责人在队列里改写第 2 段，读回正文只有该段变化

## 未实现项与限制
- 只支持单段、单行改写；多段修改、段落拆分仍回编辑台。
- 一次只处理被点的问题；同一段落的其他问题仍需“标为已处理”或重新检查（行数不变，其余问题序号仍有效）。
- 未做“驳回模型腔调意见”的新入口，沿用既有驳回接口（警告只能负责人驳回）。
- 来自生成候选的问题若检查版本与正式正文不一致，会被 `HUMAN_ISSUE_STALE` 拒绝，需先重新检查；这条路径没有单独用例。
- 不调用模型，没有真实模型润色；改写内容完全来自人工输入。
- 只读账号不出现按钮由后端用例覆盖；e2e 因新建项目里没有该账号成员关系而未写。
- 本机没有运行 pytest、tsc、pnpm 构建与 Playwright，后端和 e2e 用例只在 CI 执行；结果以 CI 为准。`spec/openapi/demo-v1.json` 未手改，新增 `editHumanIssueParagraph`、队列响应新增字段由 CI 产物更新。
