# 代码说明：APP-M2-T020 后台解析任务与进度订阅

为什么有这个文件：说明解析任务的执行方式、事件流的保持与续连，以及前端订阅的状态机。

它解决什么问题：以后把导出、生成等改为后台任务，或部署成多进程时，知道哪些在进程内、事件怎样产生、前端怎样退避与恢复。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T020 |
| 交付文件 | `docs/delivery/APP-M2-T020.md` |
| 影响模块 | `icg/domain/parse_jobs.py`、`icg/domain/recoverable_jobs.py`、`frontend/web/src/status/job-progress-sse.ts`、`useJobProgressSse.ts`、`JobProgress.tsx`、`project/TenderTab.tsx`、`app/App.tsx` |
<!-- code-explanation:end -->

## 后台
`ParseJobRunner`（每个应用一个，挂在 `application.state.parse_job_runner`，注册为 `RecoverableJobs.runners["parse"]`）：
1. `start`：一个事务里核对项目可见、`_authorize("parse.run")`（项目负责人）、幂等重放、同项目已有进行中的解析任务则直接返回它、`If-Match` 为项目版本、所选文件存在；在 `state.recoverable_jobs` 建任务（`live: True`），在 `state.jobs` 写同形状的摘要（任务列表与工作区用，`recoverable: False`）。事务后交给线程池（2 个线程，`parse-job-*`）。
2. `_loop`：排队→执行中；循环调用原 `WorkflowService.parse`（每次用当时的项目版本作 If-Match，遇到版本冲突换新版本重试 3 次；每次用新的幂等键）。原解析每次会记一条同步解析任务，这里随即从 `state.jobs` 删掉，任务列表只显示后台任务。调用后看所选文件里还有没有 `parsing_remote`：没有即完成；有且未等满上限则写一条进度（10%～90% 按已等时长）并睡 `poll_seconds()`；等满上限按 `PARSER_UNAVAILABLE` 失败。解析抛出业务错误时按该错误码失败；未预料的异常按 `INTERNAL_ERROR` 失败，不留在进行中。
3. 每一步在单独事务里改任务、追加事件（复用 `RecoverableJobs._append`，事件按冻结的 `JobEvent` 模型校验）并同步摘要。执行中每轮先看任务是否已被取消。
4. 重试：`RecoverableJobs.retry` 把任务改回排队后，若类型有执行器则 `submit`；执行器结束时若发现任务已被重试（排队），接着执行。

`RecoverableJobs._advance` 只推进没有执行器的类型（生成任务的进程内占位流程），解析任务不会被查询“推进”。

事件流 `stream()`：先发 `Last-Event-ID` 之后的已有事件；任务 `live` 且未结束时，每 0.5 秒查一次新事件推送，10 秒没有新事件发一行 `: keep-alive`，到终态或满 `ICG_SSE_HOLD_SECONDS`（默认 25）秒结束。其他任务发完已有事件即关闭，与原行为一致。响应头 `X-Accel-Buffering: no` 防止反向代理缓冲。

## 前端订阅
`JobStreamSubscriptionManager` 状态：`connecting` → `connected`；结束分三种：
- 正常结束（服务端到时关闭）且任务未结束：`reconnectDelayMs`（300ms）后带 `Last-Event-ID` 续连，不计入失败；
- 网络错误或 5xx：失败次数加一，`calculateBackoffDelay`（1s、2s、4s）后重连，超过 3 次进入 `polling`（`isFallback=true`），每 2 秒 `GET /api/v1/jobs/{id}`，每 5 次轮询试一次事件流，连上即回到 `connected`、`isFallback=false`；
- 401 / 403 / 404：进入 `error` 并停止，附原因。
任务到终态（`job.completed` / `job.failed` / `job.cancelled` 或轮询到终态）即停止全部请求并调用 `onTerminal`。事件读取用 `fetch` 的 `ReadableStream`，按空行切块；没有流式主体时退回 `text()`。

`jobFromStatus` 把后台任务状态换成 `JobProgressData`（`queued`→`pending`、`progress`→`percent`、`message`→`description`、`error`→`errorCode`/`errorMessage`）；`applyJobEvent` 按事件类型更新。

## 页面
`TenderPage`：打开时从 `workspace.jobs` 取最近一条进行中的解析任务继续显示；点“解析招标文件”经 `mutate` 调 `startParseJob`；进度卡 `JobProgressWithSse` 以“任务编号 + 起始状态”为 key，重试后换新订阅；终态时刷新工作区，完成则进入解析结果页。

## 依赖与限制
无新依赖。任务与线程都在进程内，多进程部署需要把执行器换成独立的任务队列，并把任务事件存入数据库。
