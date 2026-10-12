为什么有这个文件：记录 T124 这一轮交出的是接口草案，不是模型输入。

它解决什么问题：避免把待复核的 OpenAPI 草案写成评分行已经进入生成。

# APP-M2-T124：完整证据、片段及评分写作计划

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T124 |
| 代码解释 | 只改 OpenAPI 草案和契约测试。运行时说明见 [代码说明](../code/APP-M2-T124.md) |
| 验收 | 契约形状已核对，见 [记录](../testing/2026-10-12-t124-dependencies.md)。模型输入验收未执行。依赖已由 PM 17:20 解除；本卡 ready，不标 done |
| 项目进度 | T124 已按 PM 17:20 改为 ready。ISSUE-022 已 closed。T114 已 done；T078 看板状态行由前端按 PM 17:20 提交。看板 381 项：47 done、9 in-review、7 in-progress、265 planned、48 blocked、5 ready。不改 PRD、ROADMAP、PROJECT_BRIEF 里程碑快照 |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-12。里程碑 APP-M2。Issue：[ISSUE-022](../../issues/ISSUE-022.md)，已依据 QA 0254102，PM 15:36 确认 closed。父范围仍是 [ISSUE-007](../../issues/ISSUE-007.md)。任务卡：[APP-M2-T124](../tasks/APP-M2.md#app-m2-t124)，状态为 ready（PM 17:20 解除 blocked）。
- 分支：`codex/repository-foundation`。PR：未创建。
- 本地验收状态：契约测试已执行。任务不标 done。
- 合入 / 发布状态：未合入，未发布。

## 完成内容与变更文件

在 `spec/openapi/demo-v1.json` 增加大纲与任务契约，状态现为 frozen：

- `getOutlinePlan`：`GET /api/v1/projects/{project_id}/outline/plan`，成功响应带 ETag
- `confirmOutlinePlan`：`POST /api/v1/projects/{project_id}/outline/plan/confirm`。If-Match 核对整份计划 revision
- `startGeneration`：`POST /api/v1/projects/{project_id}/generation/start`，返回 202，`Location` 指向 `GET /api/v1/jobs/{job_id}`
- `getJob`：`GET /api/v1/jobs/{job_id}`。响应是独立的 `JobStatus`，不继承已实现的 `Job`
- `streamJobEvents`：`GET /api/v1/jobs/{job_id}/events`，未来的 SSE 草案，支持 `Last-Event-ID`
- `cancelJob`：`POST /api/v1/jobs/{job_id}/cancel`，带 `Idempotency-Key`

`JobStatus.status` 为 queued、running、completed、failed、cancelled。旧的按章方案确认、整项目方案和生成三个 POST 在说明里标了 `deprecated: true`，运行时尚未标出。草案对齐尚未实现的可恢复任务 [BE-M0-T06](../tasks/BE-M0.md#be-m0-t06)。没有新增错误码。没有改 `generation_context.py`、检索、页面或仓库读写。

T078 的实现计划写在 [内存方案](../governance/ISSUE-022-t078-plan.md)。路径改为 `/api/v1/snippet-publications`，避免被 `/library/{item_id}` 吞掉。本轮不写那段代码。

适用差异仍是 REF-08。确认仍复用 T15，不把 REF-07 当作剩余缺口。

## 代码解释

见 [代码说明](../code/APP-M2-T124.md)。产品行为没有变化。

## 验收结果

契约测试核对独立 `JobStatus`、按操作列出的错误码、ETag、202 与 `deprecated: true`。实现验收未执行，草案也还没有运行时。T114 现已 done（QA f521950，PM 17:13 确认）。T078 仍 in-review 未 done，所以本卡仍 blocked。

## 项目进度

T124 为 blocked。ISSUE-022 为 in-review，复核对象是契约草案。并入 `b364cd1` 后看板为 361 项：24 done、8 in-review、7 in-progress、268 planned、50 blocked、4 ready。本草案不增减任务。开发者不把本卡标 done。PRD、ROADMAP、PROJECT_BRIEF 的任务计数未改。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 无影响。没有新的验收口径 |
| ROADMAP | 计数无影响。补一句草案待复核，T124 仍 blocked |
| ARCHITECTURE | 无影响。未实现的草案和计划不写入架构正文 |
| Issue 看板/详情 | 有影响。ISSUE-022 改为 in-review |
| TASK_BOARD / PROJECT_STATUS | 有影响。T124 仍 blocked，进度写明草案未接通 |
| DOCUMENT_INDEX | 有影响。更新本轮条目并登记 T078 计划 |
| PROJECT_BRIEF | 计数无影响。排期句补上草案待复核 |

## 风险与后续

后台接受草案之前，不能按这三个 operationId 写实现。T078、T114 具备之前，不能把评分行或片段计划送入模型。本地草案不是合入，也不是发布。

## 契约冻结（outline-contract-frozen-1）

2026-10-12 按第三轮复审把 `x-contract-status` 改为 frozen。运行时仍未实现，T124 仍 blocked，ISSUE-022 仍 in-review。重试说明排除 502 `MODEL_UNAVAILABLE` 与 503 `SECRET_KEY_UNAVAILABLE`。新增 423 与 503 不列 `Idempotent-Replayed`。`job.model_call` 的按事件类型必填字段留到 BE-M0-T06。不改 PRD、ROADMAP、PROJECT_BRIEF 的任务计数。不标 done。

## 解除 blocked（PM 17:20）

项目经理 17:20 确认 APP-M2-T078 与 REV-M0-T24 为 done，并宣布 T114 与 T078 均 done 后 **APP-M2-T124 解除 blocked，改为 ready**。本提交只改 T124 状态与相关看板叙述；T078 / REV-M0-T24 状态行仍由前端提交（T114 / REV-M0-T22 已由前端标 done）。运行时仍未接通，模型输入未改，不标 done，不标 in-progress。三份基线里程碑快照不改。
