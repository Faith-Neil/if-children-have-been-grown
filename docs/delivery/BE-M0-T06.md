为什么有这个文件：记录可恢复生成任务这张卡实际交了什么。

它解决什么问题：让长任务先返回 202，断线后仍能查询状态，同时不把同步生成说成已经恢复。

# BE-M0-T06：可恢复任务（202 与 SSE）交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-M0-T06 |
| 代码解释 | [BE-M0-T06](../code/BE-M0-T06.md) |
| 验收 | 2026-10-13：启动返回 202 和 Location；查询、SSE 和取消使用独立 JobStatus。失败为 failed，取消为 cancelled。未设连接串时后台测试 386 passed、13 skipped。治理检查通过：333 份 Markdown、393 项任务、36 项 Issue |
| 项目进度 | 任务看板是准绳。本卡从 ready 改为 in-review。看板为 393 项：52 done、19 in-review、7 in-progress、265 planned、48 blocked、2 ready。BE-M0 为 19 项，10 项 done。本卡 in-review。ISSUE-005 为 in-progress，不关闭。T04 与 T05 仍为 in-review。T07 仍为 ready |
<!-- task-delivery:end -->

## 关联与状态

- 2026-10-13，BE-M0，[ISSUE-005](../../issues/ISSUE-005.md) 卡片 (e)。
- 分支 `codex/repository-foundation`。未新开 PR，未合入，未发布。
- 本地验收已做。等待 QA 与项目经理。不标 done。

## 完成内容与变更文件

`POST /api/v1/projects/{project_id}/generation/start` 返回 202。`Location` 是 `GET /api/v1/jobs/{job_id}`。响应体是 `JobStatus`，不继承已实现的 `Job`。`recoverable` 为布尔值，已实现 `Job.recoverable` 仍是 `const false`。

`GET /api/v1/jobs/{job_id}` 返回同一状态。不属于本公司或本项目的任务返回 404 `NOT_FOUND`。

`GET /api/v1/jobs/{job_id}/events` 是 `text/event-stream`。事件 id 为 `<job_id>:<seq>`。`Last-Event-ID` 只发送更大的 seq。没有新增 SSE 库。

`POST /api/v1/jobs/{job_id}/cancel` 需要 `Idempotency-Key`。成功响应没有 `Location`。已经结束的任务返回已有的 409 `VERSION_CONFLICT`。

状态为 `queued`、`running`、`completed`、`failed`、`cancelled`。事件按类型要求字段：`job.model_call` 带 provider、model、is_real_model、is_local、duration_ms、error_code；状态变化带 from/to；进度带 progress 和 message；三种终态带 status、completed_at 和 error。

没有新增错误码。没有重跑 `export_openapi.py`。`getOutlinePlan` 与 `confirmOutlinePlan` 仍是冻结草案。没有 ISSUE-024 的模型配置存储。没有改前端页面。

## 代码解释

见 [代码解释](../code/BE-M0-T06.md)。

## 验收结果

证据见 [验证记录](../testing/2026-10-13-be-m0-t06-recoverable-jobs.md)。

## 限制与未完成

- 不标 done，不关闭 ISSUE-005。
- 任务只在当前进程内存。重启后消失。这不是多进程恢复。
- 查询或事件流才会把排队任务推进到终态。正式正文仍由同步 `POST /generate` 写入。
- 大纲计划的 ETag 还不能从 `getOutlinePlan` 读到。现有 `POST /plan` 确认时把 `outline_revision` 加一。
- 503 `SECRET_KEY_UNAVAILABLE` 与 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL` 只在适配器明确标出时返回，不读取配置库。
