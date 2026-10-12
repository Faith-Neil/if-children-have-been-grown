# APP-M2-T124：代码解释

- 对应任务 [APP-M2-T124](../tasks/APP-M2.md#app-m2-t124)、[ISSUE-022](../../issues/ISSUE-022.md)、[交付](../delivery/APP-M2-T124.md)。
- 日期：2026-10-12。PR：未创建。

## 改了什么

`spec/openapi/demo-v1.json` 在已导出的接口之外追加草案路径和草案模型。每条草案路径有 `x-contract-status: draft, pending backend review` 和 `x-implemented: false`。`startGeneration` 另有 `x-aligned-with: BE-M0-T06`，表示对齐尚未实现的可恢复任务契约。

`JobStatus` 是独立模型，不用 `allOf` 继承 `Job`。它的 `status` 是 `queued`、`running`、`completed`、`failed`、`cancelled`。已实现的 `Job.recoverable` 仍是 `const false`，本草案不改它。`JobEvent` 增加 `seq`、`id`（`<job_id>:<seq>`）和 `occurred_at`，`type` 改为枚举，当前只有 `job.model_call`。`getJob` 的路径参数是 `job_id`。`streamJobEvents` 与 `cancelJob` 也是草案。

三个仍在运行的 POST（`/plan`、`/generate`、`/chapters/{chapter_id}/plan/confirm`）在说明文件里标了 `deprecated: true`。运行中的应用还没有这个标记。`implemented_contract` 在对比前去掉草案路径，并去掉这三处的 `deprecated` 和废弃说明，所以其余已实现接口仍必须与应用一致。

`tests/backend/test_outline_contract_draft.py` 只读这份说明。`tests/backend/test_error_idempotency.py` 与 `tests/backend/qa_error_idempotency_live_http.py` 使用同一套过滤。

## 没改什么

`backend/bid-core` 没有新路由，也没有改 `generation_context.py`。模型输入仍由该文件第 213–217 行组装，范围是整章，对应 REF-08。T15 的按章确认仍在 `workflow.py` 第 637–672 行。

没有新错误码。写操作的 428 与 409 继续使用 `IDEMPOTENCY_KEY_REQUIRED` 和 `IDEMPOTENCY_CONFLICT`。星号或废标行标为不适用时，草案写的是已有的 422 `VALIDATION_ERROR`。

T078 没有代码。计划要求新状态放在独立存储，见 [内存方案](../governance/ISSUE-022-t078-plan.md)。`Repository.read` 与 `Repository.transaction` 未改。
