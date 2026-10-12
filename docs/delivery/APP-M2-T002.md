为什么有这个文件：交付请求层对错误体、追踪号、重复请求标记和自动重试的实际结果。

它解决什么问题：避免每次重试换一把新键，或把章节版本的请求头和正文标成两把不同的键。

# APP-M2-T002：请求层细化交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T002 |
| 代码解释 | [请求层](../code/APP-M2-T002.md) |
| 验收 | 前端 92 项通过、类型检查通过。T002-F1：没有幂等键的写入不自动重试。QA 于 REV-M0-T11 签署通过，项目经理在群里确认后本卡标为 done。证据见 [请求层验证](../testing/2026-10-12-request-layer.md) |
| 项目进度 | 本卡 done。看板 366 项：32 done、6 in-review、7 in-progress、268 planned、49 blocked、4 ready。APP-M2：T001、T002 与 T008 done，T124 blocked，其余 255 planned |
<!-- task-delivery:end -->

日期 2026-10-12。关联 [ISSUE-009](../../issues/ISSUE-009.md)，产品父项仍是 [ISSUE-007](../../issues/ISSUE-007.md)。分支 `codex/repository-foundation`。[PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3) 仍待合入，未发布。QA 于 REV-M0-T11 签署通过后，项目经理在群里确认，本卡标为 done。ISSUE-009 已由项目经理在 QA 签署 d55d507（REV-M0-T11）后确认 closed。

## 完成内容与变更文件

`frontend/web/src/api.ts` 现在按冻结契约解析两类错误体。`/api/v1` 读取 `{code, message, details, traceId}`，旧 `/api` 读取 `{error, request_id}`。响应头 `X-Request-ID` 优先于正文里的追踪号。页面提示在有追踪号时附上「追踪号 …」。

非 GET 的 `/api/v1/` 写入在一次 `request()` 里只生成一把 `Idempotency-Key`。自动重试只给两类请求：GET，以及这次调用已经带上 `Idempotency-Key` 的写入。可再试的失败仍是网络错误（`TypeError`）、没有统一错误体的 502，以及 503。没有统一错误体，是指正文解析后没有 `code`（顶层或旧体 `error.code`）；网关 HTML 或空对象会落到 `REQUEST_FAILED`，这时才重试 502。带统一错误体且 `code` 为 `MODEL_UNAVAILABLE` 的 502 不重试，第一次响应就抛出。`App.report` 调用 `userFacingMessage`，有追踪号时提示为「消息（追踪号 id）」。其他带 `code` 的 502 同样不重试。503 即使带统一错误体仍重试。最多 3 次含首次，等待 200ms 再 400ms。409、422、423、428、401 和 500 不自动重试。GET 的裸 502 和 503 可以重试，且不带重复请求标记。

没有幂等键的写入第一次失败就停止。例如旧的 `POST /api/chapters/{id}/lock`，503、网关 502 和网络错误都只发一次，请求头里也没有 `Idempotency-Key`。这条限制在 [ISSUE-021](../../issues/ISSUE-021.md) 给这些旧接口补上幂等键之后解除：补键之后它们按「有键的写入」重试，本轮不改后台。

`POST /api/chapters/{id}/versions` 继续接受正文 `idempotency_key`。这次同时发送 `Idempotency-Key`，两处使用同一字符串。调用方已经放入正文的键会被原样复制到请求头；正文没有该字段时，生成一把 UUID 并同时写入正文和请求头。同一次 `request()` 里允许重试的失败不再换键。章节版本若返回 `MODEL_UNAVAILABLE`，只发一次，提示带上追踪号。编辑台每次点击仍自己生成正文键，请求层不另造一把。其他旧 `/api` 写入不添加该请求头，因此也不自动重试。

未改 `backend/` 与 `tests/backend/`。未新增依赖。

## 代码解释

入口、调用顺序和限制见 [代码解释](../code/APP-M2-T002.md)。

## 验收结果

仓库根执行 `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs`：90 通过，0 失败。其中请求层 12 项覆盖错误体、追踪号优先级、键复用、重试停表，以及章节版本请求头与正文同一把键。新增两项：`MODEL_UNAVAILABLE` 的 502 只发一次并带出追踪号；裸网关 502 仍重试且三把 `Idempotency-Key` 相同。`pnpm --dir frontend/web exec tsc -b` 通过。没有新开浏览器：本轮不改布局，离开保护和路由未动。下载仍走同一套重试，对象 URL 点击依赖浏览器，节点测试没有点下载链接。

## 项目进度

看板现为 363 项：26 done、9 in-review、7 in-progress、268 planned、49 blocked、4 ready。APP-M2 的 259 张卡里 T001 与 T002 为 in-review，T008 为 done，T124 为 blocked，其余 255 张 planned。ISSUE-009 与 ISSUE-014 仍为 in-review。ISSUE-005 仍为 in-progress。ISSUE-010 已 closed，AI-01 为 in-review。下一张未开工的页面卡仍是 APP-M2-T003。本轮不改任务计数。三份基线已是同一组 363 项数字。上文表格里的 362 项是 T002 初交时的记录。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | T002 提交未改。ISSUE-026 跟进后第19行是「项目共362项：26done、8in-review、7in-progress、268planned、49blocked、4ready」。第21行仍写「整个T001、OIDC和完整资料库仍未完成」 |
| ROADMAP | T002 提交未改。ISSUE-026 跟进后第17行是「当前共362项任务，26done、8in-review、7in-progress、268planned、49blocked、4ready」。第19行仍写「整卡继续in-progress。接下来补实际ProLayout、浏览器路由/返回和全页未保存保护」 |
| ARCHITECTURE | 未改。第21行仍写「布局、浏览器路由和全页离开保护继续本卡」。本轮不改架构 |
| PROJECT_BRIEF | T002 提交未改。ISSUE-026 跟进后第30行是「当前共362项：26done、8in-review、7in-progress、268planned、49blocked、4ready」。第68行仍写「整卡仍进行中：接下来补实际布局组件、浏览器地址/返回与全页离开保护」 |
| Issue 看板/详情 | ISSUE-009 的请求层段落改为：`MODEL_UNAVAILABLE` 不重试。状态仍 in-review。ISSUE-005、ISSUE-007、ISSUE-014 状态不改 |
| TASK_BOARD | 未改。T002 保持 in-review。开篇已是 26 done、8 in-review、49 blocked |
| PROJECT_STATUS | 补一句：带 `MODEL_UNAVAILABLE` 的 502 不自动重试。保留向量库已定为 RAGFlow。计数不改 |
| DOCUMENT_INDEX | D-277～D-280 与 D-084、D-141 的说明改为这次重试例外。不新增编号 |
| WORKFLOW | 无规则变化。治理块保持 g1.1 / 2026-10-11 / ISSUE-007 |
| OpenAPI | 未改。`x-idempotency.retry` 仍写客户端重试全部 502。项目经理把客户端收窄为：无统一错误体的 502 才重试。冻结契约不在本轮改写 |

同步表见 [APP-M2-T002 同步](../governance/APP-M2-T002-sync.md)。

## 风险与后续

服务端在请求头和正文同时出现且不一致时返回 409。本轮客户端保证两处相同，没有改服务端比较逻辑。401 仍由页面退出，不自动重试。500 不自动重试，任务卡里写过的 MSW 500 以冻结契约为准。`MODEL_UNAVAILABLE` 立刻提示，不再自动打三次。冻结契约仍写「重试 502」；本轮只收窄客户端，不改 `spec/openapi/`。演示会话仍在内存，刷新后需要重新登录。PR #3 未合入，产品未发布。APP-M2-T002、ISSUE-009 与 ISSUE-014 保持 in-review。

## T002-F1：没有键的写入不重试（仍 in-review）

QA 重签把旧写请求在没有幂等键时自动重试记为 T002-F1。`POST /api/chapters/c-one/lock` 遇到 503、网关 502 或网络错误时现在只发一次，且没有 `Idempotency-Key`。GET 的 503 仍会重试，有键的 `/api/v1` 写入和章节版本写入仍按原停表重试。`MODEL_UNAVAILABLE` 仍只发一次。

仓库根 `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs`：92 通过，0 失败。`pnpm --dir frontend/web exec tsc -b --pretty false` 退出码 0。没有改 `backend/`、`tests/backend/`、`spec/openapi/` 和 `docs/reference/`。任务计数不改，仍是 363 项：26 done、9 in-review、7 in-progress、268 planned、49 blocked、4 ready。ISSUE-021 仍 planned，本轮不给旧接口补键。T002 仍 in-review，不标 done。
