为什么有这个文件：交付契约 N7 在前端请求层的实际结果。

它解决什么问题：避免把 503 `SECRET_KEY_UNAVAILABLE` 写成已经上线，或把普通 503 也停掉。

# ISSUE-030：503 SECRET_KEY_UNAVAILABLE 不自动重试

日期 2026-10-12。关联 [ISSUE-030](../../issues/ISSUE-030.md)。请求层父卡 [APP-M2-T002](APP-M2-T002.md) 保持 done。分支 `codex/repository-foundation`。[PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3) 仍待合入，未发布。本 Issue 为 in-review。

## 完成内容与变更文件

`frontend/web/src/api.ts` 的 `canRetryStatus` 在状态为 503 且 `code` 为 `SECRET_KEY_UNAVAILABLE` 时返回 false。502 `MODEL_UNAVAILABLE` 仍只发一次。没有统一错误体的 502，以及 `code` 不是 `SECRET_KEY_UNAVAILABLE` 的 503，仍按原规则重试。判断只在这一处，GET 和已经带 `Idempotency-Key` 的写入共用它。

未改 `backend/`、`tests/backend/`、`spec/openapi/` 与 `docs/reference/`。未新增依赖。未改任务计数。`spec/openapi/README.md` 仍写客户端重试 502 和 503，那份说明不是接口字段；冻结 JSON 在 `73fde1e` 已经排除这两个 code，本轮不改 README。

## 代码解释

入口和限制见 [代码解释](../code/ISSUE-030.md)。

## 验收结果

见 [验证](../testing/2026-10-12-issue-030-secret-key-retry.md)。节点测试替换了 `fetch`。没有新开浏览器：页面提示仍走已有的 `userFacingMessage`，追踪号规则未改。

## 项目进度

看板计数不变：371 项，39 done、7 in-review、7 in-progress、265 planned、49 blocked、4 ready。APP-M2-T002 仍为 done。ISSUE-030 为 in-review，不标 closed。未合入，未发布。
