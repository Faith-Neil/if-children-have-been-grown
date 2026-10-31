为什么有这个文件：记录 APP-M2-T020 任务进度实时订阅、断线提示与轮询回退的实际交付和测试证据。

它解决什么问题：说明招标解析怎样变成后台任务、页面怎样实时看进度、断线时怎样提示和回退，以及原实现为什么用不了。

# APP-M2-T020：JobProgress：SSE 订阅、断线提示与轮询回退

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T020 |
| 代码解释 | [APP-M2-T020](../code/APP-M2-T020.md) |
| 验收 | 2026-10-31：招标文件页点“解析招标文件”后立即返回任务（202），页面显示任务进度（状态、百分比、当前说明），完成后自动进入解析结果；扫描件交给 RAGFlow 识别时后台每 10 秒（`ICG_PARSE_JOB_POLL_SECONDS`）取回一次，直到全部取回、失败、被取消或等满 30 分钟（`ICG_PARSE_JOB_MAX_WAIT_SECONDS`），每次取回写一条进度，不用再手动点“开始解析”；可离开页面，回来时继续显示进行中的任务。进度经事件流实时推送：后台对进行中的任务保持连接最多 25 秒并保活，到时关闭后页面带上最后的事件编号立即续连；网络出错时 1s→2s→4s 重连 3 次，仍不行改为每 2 秒查询任务状态并显示“实时流已断开，已切换为定时刷新”，轮询期间每 5 次再试一次实时流，连上即恢复；登录失效或任务不可见时停止并提示。失败可重试（接着取回）、进行中可取消。任务中心的“重试”现在真正调用重试接口。验证见 [验证记录](../testing/2026-10-31-t020-parse-job-progress.md) |
| 项目进度 | 看板与任务卡改为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T020](../tasks/APP-M2.md#app-m2-t020)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)；看板工作包 WP-6
- 依据：PRD v1.8 §5.12.4 后台任务中心、§5.2.1 招标文件页；任务卡验收“模拟 SSE 断开 → 提示 → 轮询 → 恢复”

## 原实现的问题
- 浏览器 `EventSource` 不能带登录令牌，后台只认 `Authorization` 头，事件流一连就是 401。
- 监听的事件名（`job_progress`、`done`、`terminal`…）与后台发出的 `job.progress`、`job.completed` 等对不上，事件全部被丢弃。
- 回退轮询不带令牌，401 时无限轮询；轮询结果没有换成页面用的字段（`progress`→百分比、`queued`→排队、`error`→错误码与说明）。
- `JobProgressWithSse` 没有任何页面使用；解析与导出都是同步请求，任务生来就是终态，没有进行中的任务可订阅。任务中心“重试”只刷新列表，从不调用重试接口。

## 实际文件
- 后端：`backend/bid-core/icg/domain/parse_jobs.py`（新）；`icg/domain/recoverable_jobs.py`（`POST /api/v1/projects/{p}/parse/jobs` 即 `startParseJob`；事件流对后台执行中的任务保持连接；重试后交回执行器；生成任务的进程内占位推进只作用于生成任务）
- 前端：`frontend/web/src/status/job-progress-sse.ts`（重写，不依赖 React）、`useJobProgressSse.ts`（新，订阅钩子）、`JobProgress.tsx`（显示任务说明、带令牌与 `onTerminal`、订阅停止原因）、`project/TenderTab.tsx`（启动解析任务、进度卡、取消与重试、完成后进入解析结果）、`app/App.tsx`（任务中心重试调用接口）
- `spec/openapi/demo-v1.json`

## 测试证据
- `tests/backend/test_parse_jobs.py`（5 项）：202 与 Location、后台完成、事件序号连续且以 `job.completed` 结束、任务列表只列一次解析任务、`Last-Event-ID` 续传；RAGFlow 仍在识别时取回 3 次后完成、事件流保持到任务结束；等满上限失败（PARSER_UNAVAILABLE）后重试接着完成；进行中重复启动返回同一任务、取消后停止；只读成员 403、他公司 404、缺 If-Match 428、他公司看不到任务
- `frontend/web/tests/unit/job-progress-sse.test.mjs`（7 项，测试 4～7 按新实现重写）：状态与事件换成页面数据；事件流带令牌、第二次连接带 `Last-Event-ID`、到终态停止；出错退避后带令牌轮询、轮询中恢复实时流；401/404 只请求一次即停止、断开后不再请求、初始已终态不发请求
- `frontend/web/e2e/parse-job.spec.ts`（2 项）：点解析 → 202 → 进入解析结果；拦截事件流（连接重置）并延迟状态查询 → 页面显示“实时流已断开，已切换为定时刷新” → 靠轮询完成并进入解析结果

## 未实现项与限制
- 只有招标解析改为后台任务。导出、检查、章节生成仍是同步请求（几秒内完成）；`startGeneration` 仍是原有的进程内占位任务，不写正文。
- 任务与执行线程在应用进程内：部署为单进程（`/health` 的 `single_process`），重启后进行中的解析任务丢失，需重新点解析（已取回的结果保留）。
- 后台线程用发起人的登录会话执行解析：发起人在解析期间退出登录或会话失效时，任务按“无权访问”失败，重新登录后重试即可。
- 取消不能打断正在进行中的一次取回；那一次取回的结果仍会写入。
- 解析步骤（提取文字、抽取条款、后处理）没有拆成子步骤进度，只有整体百分比与当前说明。
- 原 `/parse` 同步接口保留，供脚本与测试使用。
