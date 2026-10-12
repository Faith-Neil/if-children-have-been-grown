为什么有这个文件：说明 503 `SECRET_KEY_UNAVAILABLE` 为什么只发一次。

它解决什么问题：避免以后有人在别的分支又把全部 503 当成可重试。

# ISSUE-030：代码解释

- 对应任务、Issue、交付文档：APP-M2-T002（保持 done） / [ISSUE-030](../../issues/ISSUE-030.md) / [交付](../delivery/ISSUE-030.md)
- 日期、实际代码路径、提交 / PR：2026-10-12。`frontend/web/src/api.ts`、`frontend/web/tests/request-layer.test.mjs`。分支 `codex/repository-foundation`。PR #3 未合入

## 改了什么以及为什么

`canRetryStatus` 原先只要状态是 503 就返回 true，不看 `code`。冻结契约 N7 把 `503 SECRET_KEY_UNAVAILABLE` 与 `502 MODEL_UNAVAILABLE` 并列：不是瞬时故障，客户端不要自动重试，后端不发送 `Retry-After`。现在 503 仅在 `code` 不是 `SECRET_KEY_UNAVAILABLE` 时返回 true。502 的判断未改：没有 `code`，或 `code` 为 `REQUEST_FAILED`，才重试。

## 入口和调用顺序

1. `runAttempts` 捕获错误。`ApiError` 交给 `canRetryStatus(status, code)`，`TypeError` 仍可再试。
2. `apiFailure` 从统一错误体读出 `code`。`SECRET_KEY_UNAVAILABLE` 因此能到达 `canRetryStatus`。
3. 返回 false 时立刻抛出，不等待，不再 `fetch`。`userFacingMessage` 仍附上追踪号。
4. 普通 503 和裸 502 仍最多 3 次，含首次，并复用同一把 `Idempotency-Key`。没有键的旧写入仍然第一次失败就停止。

## 数据与状态

不新增字段，不写浏览器存储。错误码字符串与冻结 JSON 一致。

## 关键判断与异常

- 只排除这一个 503 code。`UI_NOT_READY` 一类 503 仍重试。
- `MODEL_UNAVAILABLE` 仍只在 502 路径上由“带 code 的 502 不重试”排除。本文件不把其他 502 code 改成可重试。
- 后台是否发送该 503 不在本轮。客户端即使收到它，也只发一次。

## 验证与限制

验证见 [密钥不可用重试](../testing/2026-10-12-issue-030-secret-key-retry.md)。测试替换了 `fetch`，没有打到真实后台。
