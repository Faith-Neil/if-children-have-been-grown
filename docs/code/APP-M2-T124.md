# APP-M2-T124：代码解释

- 对应任务 [APP-M2-T124](../tasks/APP-M2.md#app-m2-t124)、[ISSUE-022](../../issues/ISSUE-022.md)、[交付](../delivery/APP-M2-T124.md)。
- 日期：2026-10-12。PR：未创建。

## 改了什么

`spec/openapi/demo-v1.json` 在已导出的接口之外追加草案路径和草案模型。每条草案路径有 `x-contract-status: draft, pending backend review` 和 `x-implemented: false`。`startGeneration` 另有 `x-aligned-with: BE-M0-T06`，表示对齐尚未实现的可恢复任务契约。

`JobStatus` 用 `allOf` 引用已经存在的 `Job`，再追加 `events`。已实现的 `Job.recoverable` 仍是 `const false`。`JobEvent.type` 固定为 `job.model_call`，字段是 `provider`、`model`、`is_real_model`、`is_local`、`duration_ms`、`error_code`。成功时 `error_code` 为 null。

`tests/backend/test_outline_contract_draft.py` 只读这份说明。`tests/backend/test_error_idempotency.py` 与 `tests/backend/qa_error_idempotency_live_http.py` 的 `implemented_contract` 在对比运行中的接口前去掉草案路径、草案模型和根上的 `x-contract-drafts`。因此现有导出仍然必须与应用一致。

## 没改什么

`backend/bid-core` 没有新路由，也没有改 `generation_context.py`。模型输入仍由该文件第 213–217 行组装，范围是整章，对应 REF-08。T15 的按章确认仍在 `workflow.py` 第 637–672 行。

没有新错误码。写操作的 428 与 409 继续使用 `IDEMPOTENCY_KEY_REQUIRED` 和 `IDEMPOTENCY_CONFLICT`。星号或废标行标为不适用时，草案写的是已有的 422 `VALIDATION_ERROR`。

T078 没有代码。计划要求新状态放在独立存储，见 [内存方案](../governance/ISSUE-022-t078-plan.md)。`Repository.read` 与 `Repository.transaction` 未改。
