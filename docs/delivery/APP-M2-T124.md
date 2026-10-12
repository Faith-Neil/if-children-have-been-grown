为什么有这个文件：记录 T124 这一轮没有实现，以及它停在 blocked 的原因。

它解决什么问题：避免把未写入模型输入的评分行和片段计划写成已经完成。

# APP-M2-T124：完整证据、片段及评分写作计划

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T124 |
| 代码解释 | 无产品代码。原因见 [说明](../code/APP-M2-T124.md) |
| 验收 | 未执行实现验收。依赖核对见 [记录](../testing/2026-10-12-t124-dependencies.md)。T078、T114 和三个具名 operationId 不具备 |
| 项目进度 | T124 为 blocked。354 项中 21 done、7 in-review、7 in-progress、265 planned、50 blocked、4 ready |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-12。里程碑 APP-M2。Issue：[ISSUE-022](../../issues/ISSUE-022.md)。父范围仍是 [ISSUE-007](../../issues/ISSUE-007.md)。任务卡：[APP-M2-T124](../tasks/APP-M2.md#app-m2-t124)。
- 分支：`codex/repository-foundation`。PR：未创建。
- 本地验收状态：未执行。状态为 blocked，不标 done。
- 合入 / 发布状态：未合入，未发布。

## 完成内容与变更文件

没有修改模型输入、检索、OpenAPI 或页面。本轮只登记阻塞，并同步看板、进度和索引。

适用差异是 REF-08。REF-07 已由 T15 的按章确认覆盖，不是本轮剩余范围的缺口。

## 代码解释

无代码变化。入口仍是 `generation_context.py` 的整章组装，见代码说明。

## 验收结果

实现验收未执行。只读核对见验证记录。没有运行后台 pytest，因为没有行为变化。

## 项目进度

T124 为 blocked。APP-M1-T15 已 done，APP-M2-T078 与 APP-M2-T114 仍 planned。当前看板 354 项：21 done、7 in-review、7 in-progress、265 planned、50 blocked、4 ready。开发者不把本卡标 done。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 无影响。没有新的验收口径 |
| ROADMAP | 有影响。当前计数改为 354 项，并把一张 planned 改为 blocked |
| ARCHITECTURE | 无影响。整章 `source_scope` 句子保持，模块未改 |
| Issue 看板/详情 | 有影响。新增 ISSUE-022，状态 blocked |
| TASK_BOARD / PROJECT_STATUS | 有影响。T124 为 blocked，planned 265、blocked 50 |
| DOCUMENT_INDEX | 有影响。登记本交付、Issue、说明和核对记录 |
| PROJECT_BRIEF | 有影响。排期改为 354 项、265 planned、50 blocked |

## 风险与后续

在 T078、T114 和三个具名 operationId 具备之前，不能把评分行或片段计划送入模型。本地文档登记不是合入，也不是发布。
