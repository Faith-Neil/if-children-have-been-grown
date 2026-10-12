为什么有这个文件：记录错误码名字冻结这张卡实际交了什么。

它解决什么问题：把“总数仍是 143”和“名字必须逐个对上冻结名单”分开。

# BE-M0-T16：冻结错误码名字交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-M0-T16 |
| 代码解释 | [BE-M0-T16](../code/BE-M0-T16.md) |
| 验收 | 2026-10-12：未设连接串时后台测试 351 passed、8 skipped。`set(ERROR_STATUS)` 与 spec 枚举都等于 `FROZEN_NAMES`。临时替换一个码并重新导出后对照失败，探测码已还原 |
| 项目进度 | 任务看板是准绳。本卡加入前为 371 项：39 done、7 in-review、7 in-progress、265 planned、49 blocked、4 ready。本卡为 in-review 后为 372 项：39 done、8 in-review、7 in-progress、265 planned、49 blocked、4 ready。BE-M0 为 16 项，6 项 done。本卡 in-review。ISSUE-031 为 in-review，不关闭 |
<!-- task-delivery:end -->

## 关联与状态

- 2026-10-12，BE-M0，[ISSUE-031](../../issues/ISSUE-031.md)。
- 分支 `codex/repository-foundation`。未新开 PR，未合入，未发布。
- 本地验收已做。等待项目经理在 QA 后才能标 done。

## 完成内容与变更文件

`backend/bid-core/icg_demo/frozen_error_codes.py` 列出当前 143 个错误码名字。`FROZEN_NAMES` 是这份名单的集合。`errors.py` 的运行时表没有改。`export_openapi.py` 仍从 `ERROR_STATUS` 写枚举，不会改写这份名单。

契约测试要求 `set(ERROR_STATUS) == FROZEN_NAMES`，并且已保存的 spec 与运行中 OpenAPI 的 `V1Error.code` 枚举都等于同一份名单。QA 真实 HTTP 脚本增加同样的两条对照，总数 143 的检查保留。

[接口约定](../../spec/openapi/README.md) 写明：新增或删除错误码时，必须在同一提交里更新冻结名单。

## 代码解释

见 [代码解释](../code/BE-M0-T16.md)。

## 验收结果

证据见 [验证记录](../testing/2026-10-12-issue-031-frozen-error-codes.md)。

## 项目进度

任务看板是准绳。BE-M0-T16 为 in-review 后，看板为 372 项：39 done、8 in-review、7 in-progress、265 planned、49 blocked、4 ready。BE-M0 16 项，6 项 done。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 未改。里程碑快照不改 |
| ROADMAP | 未改。理由同上 |
| ARCHITECTURE | 未改。名单在接口约定和代码里 |
| PROJECT_BRIEF | 未改。理由同 PRD |
| docs/reference | 未改 |
| Issue 看板/详情 | ISSUE-031 为 in-review。不关闭 |
| TASK_BOARD / PROJECT_STATUS | 已改为 372 项：39 done、8 in-review、7 in-progress、265 planned、49 blocked、4 ready |
| DOCUMENT_INDEX | 登记本交付、代码解释和验证 |

## 风险与后续

以后若只改 `errors.py` 再导出 OpenAPI，而忘记改冻结名单，测试会失败。这是本卡要的结果。未合入，未发布。
