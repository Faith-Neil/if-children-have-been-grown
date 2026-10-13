为什么有这个文件：记录QA对BE-M0-T06（可恢复生成任务 202/SSE/取消）的正式签署。

它解决什么问题：相对开发者本地核对，独立复跑并确认失败/取消状态与冻结契约字段。

# BE-M0-T06 可恢复任务 QA签署（REV-M0-T36）

- 被验 tip：`0cb6c38`（`codex/repository-foundation`；含 `4a7e095`）。
- 环境：未设 `ICG_DATABASE_URL` / `ICG_REQUIRE_MYSQL`；仅合成数据。
- 结论：**通过**。**BE-M0-T06 / ISSUE-005 / 本卡均不标 done / closed**。

## 验收对照

| 检查 | 结果 | 证据 |
|---|---|---|
| AC-01 启动 202 + Location | 通过 | `test_start_returns_202_and_sync_generate_stays_separate`：`status=queued`、`recoverable=true`、`Location=/api/v1/jobs/{id}`；幂等重放同 id；同步 `POST /generate` 非 202；任务列表不含可恢复任务 |
| AC-02 查询推进 + SSE | 通过 | `test_get_advances_to_completed_and_sse_honors_last_event_id`：推进至 `completed`；事件序 status_changed→progress→model_call→progress→completed；`Last-Event-ID` 只发更大 seq；`text/event-stream` |
| AC-03 取消与失败 | 通过 | `test_cancel_and_failure_are_explicit`：取消→`cancelled`、无 Location；终态再取消 409 `VERSION_CONFLICT`；模型抛错→`failed` + `MODEL_UNAVAILABLE` |
| AC-04 前置拒绝不新增错误码 | 通过 | `test_start_rejects_bad_preconditions_without_a_new_error_code`：428/409/403/423/502/503 复用既有码 |
| 契约字段 | 通过 | `test_live_contract_uses_the_frozen_operation_ids`：`startGeneration`/`getJob`/`streamJobEvents`/`cancelJob`；`Job.recoverable` const false；`JobStatus.recoverable` 为 boolean；status enum 含 cancelled |
| 专项 + 无库全量 | 通过 | `test_recoverable_jobs.py` **5 passed**；全量 **386 passed，13 skipped** |

## 独立复跑命令

```text
env -u ICG_DATABASE_URL -u ICG_REQUIRE_MYSQL python -m pytest tests/backend/test_recoverable_jobs.py -q --tb=line
env -u ICG_DATABASE_URL -u ICG_REQUIRE_MYSQL python -m pytest tests/backend -q --tb=line
node scripts/check-project-governance.cjs
```

## 观察项

- O-1：任务仅进程内内存，重启消失；非多进程/跨机恢复。
- O-2：查询或事件流才会把排队任务推进到终态；正式正文仍由同步 `POST /generate` 写入。
- O-3：`getOutlinePlan` / `confirmOutlinePlan` 仍未接通；大纲 ETag 不能从读取接口取得。
- O-4：503 `SECRET_KEY_UNAVAILABLE` 与 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL` 仅在适配器明确标出时返回。

## 状态

BE-M0-T06、ISSUE-005、REV-M0-T36 均保持 **in-review**（Issue 为 in-progress），**不标 done / closed**。
