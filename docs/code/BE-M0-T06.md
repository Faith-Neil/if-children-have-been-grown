为什么有这个文件：说明可恢复生成任务的路由和事件记在哪。

它解决什么问题：避免把新的 JobStatus 当成已实现的同步 Job，或把进程内队列写成重启后仍在。

# BE-M0-T06：可恢复任务代码说明

`RecoverableJobs` 在 `backend/bid-core/icg_demo/recoverable_jobs.py`。任务放在 `DemoState.recoverable_jobs`，不进入 `state.jobs`，因此 `GET /api/v1/jobs` 的列表仍是同步任务。

启动先核对幂等键、`If-Match`、项目成员、编写权限和 `outline_revision`。省略 `chapter_ids` 时只收下 confirmation 为 current 的章。点名未确认章返回 409 `PLAN_NOT_CONFIRMED`，点名过期章返回 409 `PLAN_STALE`。非本分册负责人返回 403 `VOLUME_OWNER_REQUIRED`。同一键和同一指纹重放第一次的 202、同一个 job id 和同一个 `Location`。

查询和事件流在本进程内把 `queued` 推进到终态，并记下状态变化、进度、模型调用和终态。模型调用使用任务开始时从当前适配器读到的 provider 与 model。调用失败时任务状态为 `failed`，`job.model_call.error_code` 为已有的 `MODEL_UNAVAILABLE`。取消把未结束的任务写成 `cancelled`。这些调用不写章节正文。

同步 `POST /api/v1/projects/{project_id}/generate` 和解析路由没有改成 202。

OpenAPI 的四条路径和事件模型从当时运行中的接口写入 `spec/openapi/demo-v1.json`。`startGeneration` 的 423 与 503 不列 `Idempotent-Replayed`。
