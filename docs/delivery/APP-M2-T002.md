为什么有这个文件：交付请求层对错误体、追踪号、重复请求标记和自动重试的实际结果。

它解决什么问题：避免每次重试换一把新键，或把章节版本的请求头和正文标成两把不同的键。

# APP-M2-T002：请求层细化交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T002 |
| 代码解释 | [请求层](../code/APP-M2-T002.md) |
| 验收 | 前端 89 项通过、类型检查通过。证据见 [请求层验证](../testing/2026-10-12-request-layer.md)。本卡 in-review，项目经理尚未标 done |
| 项目进度 | 本卡 in-review。360 项中 23 done、8 in-review、7 in-progress、268 planned、50 blocked、4 ready。APP-M2：T001 与 T002 为 in-review，T008 done，T124 blocked，其余 255 planned |
<!-- task-delivery:end -->

日期 2026-10-12。关联 [ISSUE-009](../../issues/ISSUE-009.md)，产品父项仍是 [ISSUE-007](../../issues/ISSUE-007.md)。分支 `codex/repository-foundation`。[PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3) 仍待合入，未发布。此文提交复核，不把任务或 Issue 标成 done/closed。

## 完成内容与变更文件

`frontend/web/src/api.ts` 现在按冻结契约解析两类错误体。`/api/v1` 读取 `{code, message, details, traceId}`，旧 `/api` 读取 `{error, request_id}`。响应头 `X-Request-ID` 优先于正文里的追踪号。页面提示在有追踪号时附上「追踪号 …」。

非 GET 的 `/api/v1/` 写入在一次 `request()` 里只生成一把 `Idempotency-Key`。网络错误（`TypeError`）、502 和 503 用同一把键再试。最多 3 次含首次，等待 200ms 再 400ms。409、422、423、428、401 和 500 不自动重试。GET 可以重试，且不带重复请求标记。

`POST /api/chapters/{id}/versions` 继续接受正文 `idempotency_key`。这次同时发送 `Idempotency-Key`，两处使用同一字符串。调用方已经放入正文的键会被原样复制到请求头；正文没有该字段时，生成一把 UUID 并同时写入正文和请求头。同一次 `request()` 的重试不再换键。编辑台每次点击仍自己生成正文键，请求层不另造一把。其他旧 `/api` 写入不添加该请求头。

未改 `backend/` 与 `tests/backend/`。未新增依赖。

## 代码解释

入口、调用顺序和限制见 [代码解释](../code/APP-M2-T002.md)。

## 验收结果

仓库根执行 `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs`：89 通过，0 失败。其中请求层 11 项覆盖错误体、追踪号优先级、键复用、重试停表，以及章节版本请求头与正文同一把键。`pnpm --dir frontend/web exec tsc -b` 通过。没有新开浏览器：本轮不改布局，离开保护和路由未动。下载仍走同一套重试，对象 URL 点击依赖浏览器，节点测试没有点下载链接。

## 项目进度

360 项中 23 done、8 in-review、7 in-progress、268 planned、50 blocked、4 ready。APP-M2 的 259 张卡里 T001 与 T002 为 in-review，T008 为 done，T124 为 blocked，其余 255 张 planned。ISSUE-009 与 ISSUE-014 仍为 in-review。ISSUE-005 仍为 in-progress。下一张未开工的页面卡仍是 APP-M2-T003。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 未改。第19行仍写「其中T001共同底座已开工，其余258卡planned」。第21行仍写「整个T001、OIDC和完整资料库仍未完成」 |
| ROADMAP | 未改。第17行仍写「当前共356项任务，23done、6in-review、7in-progress、266planned、50blocked、4ready」。第19行仍写「整卡继续in-progress。接下来补实际ProLayout、浏览器路由/返回和全页未保存保护」 |
| ARCHITECTURE | 未改。第21行仍写「布局、浏览器路由和全页离开保护继续本卡」 |
| PROJECT_BRIEF | 未改。第30行仍写「当前共360项：23done、7in-review、7in-progress、269planned、50blocked、4ready」。第68行仍写「整卡仍进行中：接下来补实际布局组件、浏览器地址/返回与全页离开保护」 |
| Issue 看板/详情 | ISSUE-009 补上 T002 提交复核，状态仍 in-review。ISSUE-005 只改「T002 仍 planned」这句，Issue 仍 in-progress。ISSUE-007 的活计数改为其余 255 张 planned |
| TASK_BOARD / PROJECT_STATUS | T002 改为 in-review，计数改为 8 in-review、268 planned |
| DOCUMENT_INDEX | 登记本交付、代码解释、验证和同步表，编号 D-277～D-280 |
| WORKFLOW | 无规则变化。治理块保持 g1.1 / 2026-10-11 / ISSUE-007 |

同步表见 [APP-M2-T002 同步](../governance/APP-M2-T002-sync.md)。

## 风险与后续

服务端在请求头和正文同时出现且不一致时返回 409。本轮客户端保证两处相同，没有改服务端比较逻辑。401 仍由页面退出，不自动重试。500 不自动重试，任务卡里写过的 MSW 500 以冻结契约为准。演示会话仍在内存，刷新后需要重新登录。PR #3 未合入，产品未发布。
