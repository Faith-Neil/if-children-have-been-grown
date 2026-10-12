为什么有这个文件：记录 APP-M2-T078 内存发布这一轮实际做成了什么。

它解决什么问题：避免把进程内片段存储写成已经有页面、已经持久化或已经发布。

# APP-M2-T078：版本对比与发布（R31 拦截原因）交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T078 |
| 代码解释 | [内存片段发布](../code/APP-M2-T078.md) |
| 验收 | `python3 -m pytest tests/backend -q`：346 passed，2 skipped。跳过原因是 `ICG_DATABASE_URL is unset`。片段规则见 [核对](../testing/2026-10-12-t078-snippet-publications.md)。页面未做 |
| 项目进度 | 看板 381 项：49 done、7 in-review、7 in-progress、265 planned、48 blocked、5 ready。本卡 done（QA 19c4862，PM 17:20 确认）。页面未做，不挡住 done。T124 改为 ready，本轮不实现。未合入，未发布 |
<!-- task-delivery:end -->

## 关联与状态

- 日期、里程碑、Issue、任务卡：2026-10-12，APP-M2，[ISSUE-022](../../issues/ISSUE-022.md)，父范围仍是 ISSUE-007。[任务卡](../tasks/APP-M2.md#app-m2-t078)。
- 分支、提交、PR：`codex/repository-foundation`。PR 未创建。
- 本地验收状态：done（QA 19c4862，PM 17:20 确认）。后台内存接口已按方案核对。页面、持久化和知识库都没有做，页面不挡住 done。
- 合入 / 发布状态：未合入，未发布。

## 完成内容与变更文件

按 [内存方案](../governance/ISSUE-022-t078-plan.md) 增加了进程内片段发布，没有改 `Repository.read`、`Repository.transaction` 或 `DemoState`。

- 新文件 `backend/bid-core/icg_demo/snippet_publication.py`：独立字典，路径 `/api/v1/snippet-publications`。
- `ports.py` 只增加 `SnippetPublicationStore`。每个方法都带 `company_id`。
- `main.py` 只挂上这组路由。
- `workflow_schemas.py` 只增加请求和响应模型。
- `spec/openapi/demo-v1.json` 写入运行中的接口导出，用来通过去掉草案后的契约对比。大纲草案没有改成已实现。
- 测试 `tests/backend/test_snippet_publications.py`。
- 没有改 `generation_context.py`，没有新依赖，没有新错误码。

偏差：任务卡还要求页面读回。本轮只有后台内存接口。项目经理确认内存发布层为 done（QA 19c4862，PM 17:20 确认），页面不挡住 done。

## 代码解释

入口、版本头、拦截原因和回执见 [代码解释](../code/APP-M2-T078.md)。

## 验收结果

命令与结果见 [核对](../testing/2026-10-12-t078-snippet-publications.md)。全量后台测试 346 passed、2 skipped。没有连接 MySQL，没有调用模型，没有打开页面。

## 项目进度

T078 为 done（QA 19c4862，PM 17:20 确认）。页面未做，不挡住 done。当前看板为 381 项：49 done、7 in-review、7 in-progress、265 planned、48 blocked、5 ready。T124 改为 ready，本轮不实现。ISSUE-022 保持 closed。PRD、ROADMAP、PROJECT_BRIEF 的里程碑快照不改。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 无影响。没有新的页面验收口径。本轮不改任务计数 |
| ROADMAP | 无影响。没有新增或取消任务。本轮不改任务计数 |
| ARCHITECTURE | 无影响。片段仍是进程内内存，不进入 `Repository` 整包读写，架构正文不把演示实现写成持久化 |
| Issue 看板/详情 | ISSUE-022 仍 in-review。T078 节改为内存实现已提交复查。不标 closed |
| TASK_BOARD / PROJECT_STATUS | T078 改为 in-review。看板计数改为 10 in-review、267 planned。三份基线计数不改 |
| DOCUMENT_INDEX | 登记交付、代码解释和核对记录 |

上表是内存实现提交时的同步。项目经理随后确认本卡 done（QA 19c4862，PM 17:20 确认）。ISSUE-022 保持 closed。T124 改为 ready，本轮不实现。看板见上方项目进度。

## 风险与后续

重启丢失片段和幂等回执。`[[sync-fail]]` 只是内存里的知识库拒绝替身，不是 RAGFlow。被拦截的发布不改记录和审计，但会记下幂等回执。页面、编辑锁和跨进程存储都不在本轮。
