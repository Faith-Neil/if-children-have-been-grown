为什么有这个文件：说明请求层怎样解析错误、复用重复请求标记，以及章节版本为什么头和正文是同一把键。

它解决什么问题：避免只看到函数名，却不知道重试会不会换成另一把键。

# APP-M2-T002：代码解释

- 对应任务、Issue、交付文档：APP-M2-T002 / [ISSUE-009](../../issues/ISSUE-009.md) / [交付](../delivery/APP-M2-T002.md)
- 日期、实际代码路径、提交 / PR：2026-10-12。`frontend/web/src/api.ts`、`frontend/web/src/App.tsx`、`frontend/web/tests/request-layer.test.mjs`。分支 `codex/repository-foundation`。PR #3 未合入

## 改了什么以及为什么

原先每次进入 `request()` 都为 `/api/v1/` 写操作新造一把 `Idempotency-Key`。调用方如果自己再发一次，或将来在函数内部重试，就会变成另一把键。同一次用户动作的重试复用同一把键。项目经理随后收窄客户端：带统一错误体且 `code` 为 `MODEL_UNAVAILABLE` 的 502 不自动重试，立刻把追踪号交给提示。冻结的 `x-idempotency.retry` 仍写重试全部 502，本文件不改那份契约。

旧章节提交 `POST /api/chapters/{id}/versions` 的正文已经带 `idempotency_key`。服务端允许同时出现请求头，但两处必须相同，否则返回 409。编辑台每次点击仍生成正文键；请求层把这把键抄到 `Idempotency-Key`，重试时两处都不换。

## 入口和调用顺序

1. 页面调用 `request(path, token, method, body, revision)`。编辑台提交正文走 `EditorPage.commit()`，正文里已经有本次点击的 `idempotency_key`。
2. 路径去掉查询串后，若方法不是 GET 且匹配 `/api/chapters/{id}/versions`，从正文取出非空 `idempotency_key`；没有则生成一把 UUID，写回即将发送的正文副本。
3. 其他非 GET 且以 `/api/v1/` 开头的路径，在这次调用开始时生成一把请求头键，不改正文。GET 和其他旧 `/api` 路径不加该头。
4. `runAttempts` 最多执行 3 次。`ApiError` 交给 `canRetryStatus(status, code)`：503 始终可再试；502 仅在没有应用 `code`，或解析兜底为 `REQUEST_FAILED` 时可再试。`TypeError` 也可再试。可再试时先等 200ms、再等 400ms，然后用同一组头和正文再发。`MODEL_UNAVAILABLE` 和其他带 `code` 的 502 立刻抛出。
5. 失败响应经 `apiFailure`：优先 `X-Request-ID`，其次正文 `traceId`，再次旧体 `request_id`。缺 `code` 时用 `REQUEST_FAILED`，所以网关 HTML 会重试，带 `code` 的统一错误体不会。`App.report` 用 `userFacingMessage` 显示「追踪号 …」，401 仍退出。`MODEL_UNAVAILABLE` 因此第一次就弹出追踪号。

`download()` 使用同一套尝试次数，下载是 GET，不带重复请求标记。

## 数据与状态

重复请求标记只活在这一次 `request()` 调用里，不写入浏览器存储。正文副本不改调用方原来的对象。演示登录、项目和章节数据仍是内存；本文件不持久化回执。回执 24 小时和 409 冲突由后台处理，前端不保存成功回执。

## 关键判断与异常

- 可自动重试的是网络错误、没有统一错误体的 502，以及 503。带 `MODEL_UNAVAILABLE` 的 502 不重试。409、422、423、428 交给用户。401 不重试，页面退出。500 不重试。
- 「最多 3 次」含第一次请求，所以自动重试最多两次。
- 章节版本的请求头和正文键在发送前就定下来。重试不会再调用 `crypto.randomUUID()`。
- 锁定释放、草稿和章节建议仍是旧路径，不注入 `/api/v1` 的请求头。
- 追踪号以响应头为准。头和正文不一致时，用户看到的是头里的值。

## 验证与限制

验证见 [请求层验证](../testing/2026-10-12-request-layer.md)。节点测试替换了 `fetch`，没有打到真实后台。下载点击没有在节点里执行。服务端比较逻辑未改。
