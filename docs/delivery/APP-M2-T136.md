为什么有这个文件：记录 APP-M2-T136 异常中断与重试的实际交付和测试证据。

它解决什么问题：说明做到什么、没做什么，避免把未运行的测试或没有真实触发过的失败路径当作已验收。

# APP-M2-T136：异常中断与重试

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T136 |
| 代码解释 | [APP-M2-T136](../code/APP-M2-T136.md) |
| 验收 | 2026-11-01：重新检查或生成后循环中途抛出异常时，正文与既有问题保持原样，本节循环记为“异常中断”（状态 interrupted、停止原因 INTERRUPTED、错误 code/type/message 与重试次数写在 meta），上一次循环进入历史；接口返回 200 且 interrupted=true，不伪造成功。进度页显示红色“异常中断”标签、错误说明和“重试”按钮（调用同一个重新检查接口，仍按 can_recheck 控制）；中断后再次检查成功，meta.retry_count 在上次基础上加一。处理完问题不会把中断改成“人工已处理”。 验证见 [验证记录](../testing/2026-11-01-wp5-batch1-loop-evidence.md) |
| 项目进度 | 看板与任务卡改为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T136](../tasks/APP-M2.md#app-m2-t136)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 依据：PRD v1.8 §5.7.4～5.7.7

## 实际文件
- `chapter_loop.py`：`record_interruption`、`interruption_error`、`interrupted_outcome`；`record_loop` 遇到中断结果转记中断，重试次数累加；`refresh_chapter_status` 不覆盖 interrupted
- `human_queue.py`：`recheck_chapter` 捕获循环异常；`LOOP_STATUS_LABELS`、`list_chapter_loops` 合计加入 interrupted
- `chapter_generation.py`：生成后循环异常时用占位结果记录中断
- `api/chapter_loop.py`：`ChapterRecheckResponse` 增加 `interrupted`、`error`
- 前端：`chapter-loop-core.ts`（`loopStatus`、`retryLabel`、`interruptionText`）、`ChapterLoopPage.tsx`、`shared/types.ts`

## 测试证据
- `tests/backend/test_human_queue.py`：`test_interrupted_recheck_keeps_content_and_records_interruption`、`test_retry_after_interruption_succeeds_and_counts_retry`、`test_interrupted_recheck_still_requires_permission`、`test_interrupted_loop_is_not_overwritten_by_issue_status_refresh`
- `frontend/web/tests/unit/chapter-loop-core.test.mjs`：中断标签、重试文案、时间线条目

## 未实现项与限制
- **没有端到端用例**：浏览器里无法确定性地让循环抛异常（规则循环不依赖外部服务），所以没有写 Playwright 用例，以免出现靠运气通过的分支；中断路径只由后端用例（monkeypatch 抛错）和前端单测覆盖。
- 当前重新检查只走规则修正，不调用模型；“模型超时”类中断在真实模型接入后才会出现，本卡没有用真实模型验证。生成流程里模型修正函数自身的异常原本就被吞掉并退回规则修正，不会产生中断。
- 生成后循环（`chapter_generation.py`）的中断记录没有单独的后端用例，只共用 `record_interruption` 的测试。
- 队列空态沿用已有行为（没有待处理问题的章节不出现在人工队列），本卡未新增空态用例。
- 重试次数只在“中断后再次检查”时累加；人工另行改正文后再检查同样计入。
- 本机没有运行 pytest、tsc、pnpm 构建与 Playwright，后端用例只在 CI 执行；结果以 CI 为准。`spec/openapi/demo-v1.json` 未手改，`recheckChapter` 响应新增 `interrupted`、`error` 由 CI 产物 `openapi-regenerated` 更新。
