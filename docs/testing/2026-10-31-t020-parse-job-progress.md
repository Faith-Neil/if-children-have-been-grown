为什么有这个文件：记录 APP-M2-T020 后台解析任务与进度订阅的验证方式、结果与局限。

它解决什么问题：说明本机与 CI 各跑了什么，以及哪些情形没有验证。

# APP-M2-T020 后台解析任务与进度订阅验证（2026-10-31）

## 环境
同 [T260 验证](2026-10-31-t260-password-login.md)。后端用例把取回间隔设为 0.05 秒（`ICG_PARSE_JOB_POLL_SECONDS`）、事件流保持 5 秒（`ICG_SSE_HOLD_SECONDS`）；RAGFlow 识别中的情形用替换 `_pending_files` 模拟，没有连真实 RAGFlow。

## 结果
| 验证 | 命令 / 位置 | 结果 |
|---|---|---|
| 本机前端单测 | `node --test tests/unit/job-progress-sse.test.mjs tests/job-progress.test.mjs` | 12 通过（`job-progress-sse.ts` 不再依赖 React，本机也能运行） |
| 本机前端单测全量 | `node --test tests/*.test.mjs tests/**/*.test.mjs` | 543 通过，4 个文件因本机缺 antd/react 失败（与改前相同的那几个） |
| CI（`afc31f4`） | offline-check | 结论写入交付文档 |

## 局限
- 未连真实 RAGFlow 跑扫描件的后台取回；真实取回仍走原 `RemoteTenderParser.poll`，本卡未改。
- 未验证应用重启时进行中任务的丢失提示（任务在进程内，重启后消失）。
- 未在内网反向代理（Nginx）后验证事件流不被缓冲；已加 `X-Accel-Buffering: no`。
