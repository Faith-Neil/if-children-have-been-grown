为什么有这个文件：留下这次计数对齐实际改了哪些句子。

它解决什么问题：避免只在 Issue 里写「已对齐」，却没有交付和核对记录。

# ISSUE-026：基线任务计数对齐交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | ISSUE-026 |
| 代码解释 | 无应用代码。[说明](../code/ISSUE-026.md) |
| 验收 | 看板 recount 为 361 项：26 done、6 in-review、7 in-progress、268 planned、50 blocked、4 ready。三份基线已写成同一组数字。[核对](../testing/2026-10-12-issue-026-counts.md)。本 Issue 为 in-review |
| 项目进度 | 不新增任务。361 项计数不变。APP-M2：T001 与 T002 in-review，T008 done，T124 blocked，其余 255 planned |
<!-- task-delivery:end -->

日期 2026-10-12。关联 [ISSUE-026](../../issues/ISSUE-026.md)。分支 `codex/repository-foundation`。[PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3) 待合入，未发布。不标 done，不标 closed。

## 完成内容与变更文件

`docs/PRD.md` 第19行、`docs/ROADMAP.md` 第17行、`docs/PROJECT_BRIEF.md` 排期行改成看板的 361 项。APP-M2 剩余 planned 改为 255，并写明 T001 与 T002 为 in-review、T008 为 done、T124 为 blocked。Brief 版本从 brief-8 改为 brief-9。

`docs/TASK_BOARD.md` 与 `docs/PROJECT_STATUS.md` 只增加指向本 Issue 的句子，数字保持 361。没有新任务行。

没有修改 `frontend/web/src/api.ts`。章节版本的请求头和正文仍用同一把键。自动重试仍只覆盖网络错误、502 和 503。

## 代码解释

无应用代码，原因见 [代码说明](../code/ISSUE-026.md)。

## 验收结果

用任务看板表格逐行统计，结果与开篇 361 项一致。三份基线能检索到 `26done、6in-review、7in-progress、268planned、50blocked、4ready`。治理检查在验证文件里。没有浏览器验收。

## 项目进度

361 项中 26 done、6 in-review、7 in-progress、268 planned、50 blocked、4 ready。本 Issue 使 in-review 的 Issue 多一张，任务数不变。下一张未开工的页面卡仍是 APP-M2-T003。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 第19行改为 361 项与其余 255 张 planned |
| ROADMAP | 第17行改为 361 项。第19行仍写整卡 in-progress 和接下来补布局，因为那句不是任务总数 |
| ARCHITECTURE | 未改。第21行没有任务总数 |
| PROJECT_BRIEF | 排期行改为 361 项、6 in-review、其余 255 项 planned。第68行仍写接下来补布局组件 |
| Issue 看板/详情 | 新增 ISSUE-026，in-review |
| TASK_BOARD / PROJECT_STATUS | 数字保持 361，补本 Issue |
| DOCUMENT_INDEX | D-283～D-287 |
| WORKFLOW | 治理块不升版 |

同步表见 [ISSUE-026 同步](../governance/ISSUE-026-sync.md)。

## 风险与后续

ROADMAP 第19行和 PROJECT_BRIEF 第68行仍把布局写成尚未动手。活的状态是 T001 已提交 in-review。项目经理签收前不把那两句改成完成。请求层重试策略另等项目经理决定，本轮没有改。
