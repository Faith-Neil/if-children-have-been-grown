为什么有这个文件：记录 T124 这一轮交出的是接口草案，不是模型输入。

它解决什么问题：避免把待复核的 OpenAPI 草案写成评分行已经进入生成。

# APP-M2-T124：完整证据、片段及评分写作计划

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T124 |
| 代码解释 | 只改 OpenAPI 草案和契约测试。运行时说明见 [代码说明](../code/APP-M2-T124.md) |
| 验收 | 契约形状已核对，见 [记录](../testing/2026-10-12-t124-dependencies.md)。模型输入验收未执行。T078 与 T114 仍 planned |
| 项目进度 | T124 仍为 blocked。ISSUE-022 为 in-review。356 项中 23 done、6 in-review、7 in-progress、266 planned、50 blocked、4 ready |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-12。里程碑 APP-M2。Issue：[ISSUE-022](../../issues/ISSUE-022.md)，状态 in-review。父范围仍是 [ISSUE-007](../../issues/ISSUE-007.md)。任务卡：[APP-M2-T124](../tasks/APP-M2.md#app-m2-t124)，状态仍是 blocked。
- 分支：`codex/repository-foundation`。PR：未创建。
- 本地验收状态：契约测试已执行。任务不标 done。
- 合入 / 发布状态：未合入，未发布。

## 完成内容与变更文件

在 `spec/openapi/demo-v1.json` 增加草案，契约状态为 draft, pending backend review：

- `getOutlinePlan`：`GET /api/v1/projects/{project_id}/outline/plan`
- `confirmOutlinePlan`：`POST /api/v1/projects/{project_id}/outline/plan/confirm`，带 `Idempotency-Key`
- `startGeneration`：`POST /api/v1/projects/{project_id}/generation/start`，返回 202，`Location` 指向 `GET /api/v1/jobs/{id}`
- `getJob`：查询上述任务。响应复用已有 `Job`，并追加 `job.model_call` 事件

草案对齐尚未实现的可恢复任务 [BE-M0-T06](../tasks/BE-M0.md#be-m0-t06)。没有新增错误码。没有改 `generation_context.py`、检索、页面或仓库读写。

T078 的实现计划写在 [内存方案](../governance/ISSUE-022-t078-plan.md)，本轮不写那段代码。新状态将放在独立存储，不改 `Repository.read` 与 `Repository.transaction`。

适用差异仍是 REF-08。确认仍复用 T15，不把 REF-07 当作剩余缺口。

## 代码解释

见 [代码说明](../code/APP-M2-T124.md)。产品行为没有变化。

## 验收结果

契约测试核对 operationId、错误体引用、幂等头、202 与 `Job` 复用。rebase 前 `python3 -m pytest tests/backend -q` 为 313 项通过。冲突解开后治理检查为 183 份 Markdown、356 项任务、22 项 Issue。实现验收未执行，因为 T078 和 T114 仍不存在，草案也还没有运行时。

## 项目进度

T124 为 blocked。ISSUE-022 为 in-review，复核对象是契约草案。rebase 后看板为 356 项：23 done、6 in-review、7 in-progress、266 planned、50 blocked、4 ready。本草案不增减任务。开发者不把本卡标 done。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 无影响。没有新的验收口径 |
| ROADMAP | 计数无影响。补一句草案待复核，T124 仍 blocked |
| ARCHITECTURE | 无影响。未实现的草案和计划不写入架构正文 |
| Issue 看板/详情 | 有影响。ISSUE-022 改为 in-review |
| TASK_BOARD / PROJECT_STATUS | 有影响。T124 仍 blocked，进度写明草案未接通 |
| DOCUMENT_INDEX | 有影响。更新本轮条目并登记 T078 计划 |
| PROJECT_BRIEF | 计数无影响。排期句补上草案待复核 |

## 风险与后续

后台接受草案之前，不能按这三个 operationId 写实现。T078、T114 具备之前，不能把评分行或片段计划送入模型。本地草案不是合入，也不是发布。
