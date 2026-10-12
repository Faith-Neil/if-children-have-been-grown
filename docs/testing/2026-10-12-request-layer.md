为什么有这个文件：留下请求层错误体、追踪号、重复请求标记和重试规则的实际命令结果。

它解决什么问题：避免把「应该复用同一把键」写成已经核对，却没有测试输出。

# 2026-10-12 请求层验证

关联 APP-M2-T002 / ISSUE-009。状态 in-review。契约文件仍是 `cba6282` 冻结的 `spec/openapi/demo-v1.json`。其中 `x-idempotency.retry` 仍写重试全部 502。本轮客户端更窄：带 `MODEL_UNAVAILABLE` 的 502 不重试。未改后台，未改契约。

## 行为

- `/api/v1` 错误体 `{code, message, details, traceId}` 与旧 `/api` 的 `{error, request_id}` 都能进 `ApiError`。
- 响应头 `X-Request-ID` 优先于正文 `traceId`。有追踪号时，提示为「消息（追踪号 id）」。
- 一次 `/api/v1` 写入只生成一把 `Idempotency-Key`。没有统一错误体的网关 502（HTML `Bad Gateway`）失败两次再成功时，三次请求的键相同，等待为 200ms、400ms。下一次 `request()` 换新键。
- 统一错误体 `code: MODEL_UNAVAILABLE` 的 502 只发一次。`userFacingMessage` 为「模型暂不可用。（追踪号 trace-model）」。页面 `App.report` 用的就是这句。
- 网络错误接着带 `code` 的 503：同一把键，第 3 次后停止。503 即使有统一错误体也重试。
- 409、422、423、428、401、500 各只发一次。GET 的裸网关 502 重试不带 `Idempotency-Key`。
- `POST /api/chapters/{id}/versions`：正文已有 `idempotency_key` 时，请求头等于该值，网络错误和 503 重试后仍相等。正文没有该字段且返回 `MODEL_UNAVAILABLE` 时，只发一次，生成的键同时写入头和正文，提示为「模型暂不可用。（追踪号 legacy-502）」；下一次点击若传入另一把正文键，请求头改用那一把。
- 旧的锁定释放只发原正文，不加 `Idempotency-Key`。

「最多 3 次」在这里是 3 次尝试含首次。

## 命令

工作目录为仓库根。Node 为 v24.21.0。

```text
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
```

结果：tests 90，pass 90，fail 0。Node v24.21.0。

```text
pnpm --dir frontend/web exec tsc -b --pretty false
```

结果：退出码 0，无类型错误。

```text
node scripts/check-project-governance.cjs
```

结果：治理检查通过：213 份 Markdown、362 项任务、27 项 Issue。

## 局限

`fetch` 由测试替身提供，没有对运行中的后台发送章节提交。下载函数共用重试，但对象 URL 和链接点击需要浏览器，本轮没有单独点下载。布局、路由和离开保护未改，没有重跑 Playwright。401 的退出仍由既有页面测试间接覆盖；本记录只断言 401 不重试。
