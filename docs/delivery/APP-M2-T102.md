为什么有这个文件：记录 APP-M2-T102 解析进度页（JobProgress 接入）的前端与测试交付。

它解决什么问题：说明页面实际做到什么、哪些没做，避免把未运行的测试或未连接的服务当作已验收。

# APP-M2-T102：解析进度页（JobProgress 接入）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T102 |
| 代码解释 | [APP-M2-T102](../code/APP-M2-T102.md) |
| 验收 | 2026-10-31：文件表增加“解析服务 / 耗时”列（本地文字提取或 RAGFlow DeepDOC，复用时标“复用”）；已解析或失败的文件可“换服务重试”，在自动、只用本地、RAGFlow DeepDOC 三种服务中选一种，请求体 `{file_ids, service}` 提交后台解析任务，进度沿用 T020 的事件流卡片。验证见 [验证记录](../testing/2026-10-31-wp4-parse-postprocess-frontend.md) |
| 项目进度 | 看板与任务卡改为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T102](../tasks/APP-M2.md#app-m2-t102)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 依据：PRD v1.8 §5.1.1～5.1.5、§5.2.1～5.2.4；后端见提交 `229d05f`

## 实际文件
- 接口：`ParseRequest.service` 与 `TenderFile.parse_service_label`、`parse_duration_ms`、`reused`；前端 `retryBody`、`durationLabel`。
- 前端：`frontend/web/src/project/` 下 `TenderTab.tsx`、`ParseTab.tsx`、`ConflictCards.tsx`、`MergeSuggestionsDrawer.tsx`（新）、`AddendumDiffDrawer.tsx`（新）、`parse-postprocess-core.ts`（新）；`shared/types.ts`
- 测试：“解析耗时和换服务重试的请求体”用例；`tests/backend/test_tender_files.py`；e2e `retry-service-button` 可见

## 说明
进度订阅与取消、重试沿用 T020，本卡不改。

## 未实现项与限制
- 换服务重试按文件重新解析，不比较两次结果；RAGFlow 未连接时如实显示后台失败原因；本机未连真实 RAGFlow，换服务重试没有实跑。
- 本机没有运行 pytest、tsc、pnpm 构建与 Playwright，以上后端与 e2e 用例只在 CI 执行；结果以 CI 为准，不在此处声明通过。
