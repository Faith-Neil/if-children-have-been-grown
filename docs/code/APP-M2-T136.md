# 代码说明：APP-M2-T136 异常中断与重试

为什么有这个文件：说明章节循环异常中断的记录方式、状态流转和前端展示所在位置。

它解决什么问题：以后改循环状态、重试口径或进度页时，知道规则在哪个文件、前端哪里只是展示。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T136 |
| 交付文件 | `docs/delivery/APP-M2-T136.md` |
| 影响模块 | `chapter_loop.py`、`human_queue.py`、`chapter_generation.py`、`api/chapter_loop.py`、`frontend/web/src/project/chapter-loop-core.ts`、`ChapterLoopPage.tsx`、`shared/types.ts` |
<!-- code-explanation:end -->

## 接线
- `human_queue.recheck_chapter` 用 try/except 包住 `run_chapter_loop`；异常时不改正文、不新增章节版本，调用 `chapter_loop.record_interruption` 写入 `workflow["human_queue"]["loops"]`，仍通过 `WorkflowService._write`（Idempotency-Key、If-Match、审计）提交，权限与定稿分册检查在循环之前，因此无权限或已定稿时仍返回 403/409。
- `record_interruption`：状态 `interrupted`，停止原因 `INTERRUPTED`，`rounds` 为空，`meta.error={code:LOOP_INTERRUPTED,type,message,at}`，`meta.retry_count`；上一次循环进入 `history`；已有问题记录不动。
- `record_loop` 发现上一次是 `interrupted` 时，把 `meta.retry_count` 设为上次值加一。
- `chapter_generation` 里生成后循环异常时用 `interrupted_outcome` 占位，经同一个 `record_loop` 落成中断。
- 数据放在 `meta` 字典，OpenAPI 只新增 `ChapterRecheckResponse.interrupted/error`。

## 约束
- 中断不是成功：接口返回 `interrupted=true`，前端显示红色标签与“重试”，不显示“已完成”。
- `refresh_chapter_status` 不会把 interrupted 改成 pending_human/human_handled。
- `workflow_orchestrator.py` 未改动。

## 依赖与限制
无新依赖。限制见交付文档“未实现项与限制”。
