为什么有这个文件：解释人工处理队列与章节循环的实际代码路径。

它解决什么问题：说明问题从哪里产生、如何判定转人工、存在哪里、谁能处理。

# APP-M2-T133：代码解释

- 对应任务 APP-M2-T133；Issue [ISSUE-040](../../issues/ISSUE-040.md)；交付 [APP-M2-T133 交付](../delivery/APP-M2-T133.md)
- 提交 `06f107d`、`2c8d51c`

## 改了什么以及为什么

原来没有队列，整改引擎把所有问题都尝试自动改写（含编造，见 [ISSUE-039](../../issues/ISSUE-039.md)）。现在由 `chapter_loop.run_chapter_loop` 按 PRD §5.7.4 规则编排，自动修不了的问题写入 `workflow["human_queue"]`，由页面逐条处理。

## 入口和调用顺序

1. 生成路径：`ChapterGenerationService.start_chapter_generation(auto_remediate=True)` 或 `remediate_chapter_candidate` → `run_chapter_loop(content, LoopContext, model_fix)` → 同一事务内 `record_loop(...)`。
2. 重新检查：`POST /api/v1/projects/{pid}/chapters/{cid}/loop/recheck` → `HumanQueueMixin.recheck_chapter` → `WorkflowService._write`（If-Match、幂等键、`_authorize` 的 `chapter.loop.recheck` 分支要求本节编辑权）→ `run_chapter_loop`（仅确定性修正）→ 正文有变化时追加章节版本（`source=chapter_loop`）→ `record_loop`。
3. 列表：`GET /human-queue?volume=` → `list_human_queue`；单章：`GET /chapters/{cid}/loop` → `get_chapter_loop`。
4. 处理：`POST /human-queue/issues/{id}/resolve`（`method` 三选一，可 `also_issue_ids` 合并同段）；驳回：`.../reject`（`reason_type` + 必填理由）。
5. 前端 `ManualQueuePage` 读取列表，按钮只看接口返回的 `permissions.resolve / reject` 与 `can_recheck`；写入经 `mutate` 带 If-Match 与 Idempotency-Key，成功后 workspace 版本变化触发重读。

## 数据与状态

```text
workflow["human_queue"] = {
  "loops":   {chapter_id: {loop_no, kind, status, stop_reason, rounds[], max_rounds, rolled_back, checked_revision, history[]}},
  "issues":  {issue_id: {number "章序-001", fingerprint, code, rule, level, route, human_reason, paragraph_index, quote,
                          message, suggestion, fix_count, status, resolution?, rejection?, history[]}},
  "sequence": {chapter_id: n}
}
```

- 循环状态：`completed`（全部解决）/ `pending_human` / `human_handled`。
- 问题状态：`pending_human` → `human_handled` / `rejected`；新循环未再出现的记 `resolved`；已驳回的警告不再重新打开。
- 持久化：MySQL 模式写入 `demo_project_workflow_state`（见 [BE-WORKFLOW-STATE-PERSIST](BE-WORKFLOW-STATE-PERSIST.md)）。

## 关键判断与异常

- 直接转人工判定（`check_paragraphs`）：系统生成章节 → `SYSTEM_CHAPTER`；★/废标章节 → `STAR_OR_DISQUALIFY`；【待补】无已确认事实 → 金额/人员/缺证据；偏离 → `BUSINESS_DEVIATION`；依据外证据 → `EVIDENCE_CITATION`。
- 处理权限（`_issue_permissions`）：项目负责人全项目；本节编辑权限者本节；额外承诺/披露类仅负责人；阻断级不可驳回；规则警告仅负责人驳回；分册已定稿时全部不可写（409 `VOLUME_FINALIZED`）。
- 查看权限：项目成员或本公司公司管理员；跨公司 404。

## 验证与限制

见 [Wave 11 验证](../testing/2026-10-28-wave-11-verification.md)。循环规则层只含 6 类检查；模型评审未接入；审查清单候选、站内提醒未实现。
