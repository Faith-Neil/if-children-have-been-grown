为什么有这个文件：记录这次只把任务计数写进三份基线，没有改请求层或后台。

它解决什么问题：避免把计数对齐写成布局、幂等或数据库已经完成。

# ISSUE-026 同步

日期 2026-10-12。revision count-sync-1。状态 in-review。治理块仍为 g1.1 / 2026-10-11 / ISSUE-007，与 [WORKFLOW](WORKFLOW.md) 一致。

活的计数来自 [任务看板](../TASK_BOARD.md)：361 项，26 done、6 in-review、7 in-progress、268 planned、50 blocked、4 ready。APP-M2 其余 255 张 planned。不新增任务卡。BE-M0-T08 与 BE-M0-T10 保持项目经理已确认的 done。

| 对象 | 实际处理 |
|---|---|
| PRD | 第19行改为 361 项与 APP-M2 其余 255 张 planned。治理块不升版 |
| ROADMAP | 第17行改为同一组 361 项，并写上 T002 为 in-review。第19行仍写「整卡继续in-progress。接下来补实际ProLayout、浏览器路由/返回和全页未保存保护」 |
| ARCHITECTURE | 未改。第21行仍写「布局、浏览器路由和全页离开保护继续本卡」 |
| PROJECT_BRIEF | 排期行改为 brief-9 的 361 项，in-review 名单加上 T002，其余 255 项 planned。第68行仍写「整卡仍进行中：接下来补实际布局组件、浏览器地址/返回与全页离开保护」 |
| Issue 看板/详情 | 新增 ISSUE-026，状态 in-review。ISSUE-009 的请求层小节改为指向这次计数。ISSUE-005、T001、T002 状态不改 |
| TASK_BOARD | 开篇补 ISSUE-026。361 项数字不改 |
| PROJECT_STATUS | 补一句指向 ISSUE-026。361 项数字不改 |
| DOCUMENT_INDEX | D-283～D-287，并更新 PRD、路线图、brief、看板和项目状态的说明 |
| WORKFLOW | 无规则变化 |
| 参考原文 | 不改 `docs/reference/` |
| 后台与请求层 | 不改 `backend/`、`tests/backend/`、`frontend/web/src/api.ts`。重试仍是网络错误、502 和 503，最多 3 次含首次 |

## 跟进

看板现为 362 项：26 done、8 in-review、7 in-progress、268 planned、49 blocked、4 ready。AI-01 为 in-review。三份基线的计数字句改成同一组。ARCHITECTURE 第21行、ROADMAP 第19行、PROJECT_BRIEF 第68行仍不改。不改 `api.ts`、后台和 `docs/reference/`。Issue 仍为 in-review。

PR #3 仍待合入。本轮不新建 PR，不合并，不发布。

## 跟进：364 项、27 done

核对提交 `84a3fca4c5e8f59410d2e0a100bc358100d0b0b6`。看板表格为 364 项：27 done、9 in-review、7 in-progress、268 planned、49 blocked、4 ready。当时 PRD 第19行、ROADMAP 第17行、PROJECT_BRIEF 排期行仍是 363 项、26 done。结论不是 no change needed。三句已改成与看板相同的 364 项、27 done。新增的 done 卡是 REV-M0-T10。in-review 仍是九张，BE-M0-T15 仍 in-review。ARCHITECTURE 第21行、ROADMAP 第19行、PROJECT_BRIEF 第68行仍不改。不改 `api.ts`、后台和 `docs/reference/`。Issue 仍为 in-review。记录见 [基线复核](../testing/2026-10-12-issue-026-baseline-count-check.md)。

## 里程碑快照

项目经理规定：PRD、ROADMAP、PROJECT_BRIEF 的任务计数写成 `as of commit <sha>`，并写明任务看板是准绳、这三份只在里程碑更新。不要求快照与之后的活看板逐项相等。规则写入 [WORKFLOW](WORKFLOW.md) 第4节。

本里程碑核对提交 `3bb311ad3ab86c0de2f871876a50c7d50f9bb985`。当时表格为 366 项：30 done、8 in-review、7 in-progress、268 planned、49 blocked、4 ready。REV-M0-T12 与 BE-M0-T14 已是 done，ISSUE-025 已 closed。APP-M2-T001 与 APP-M2-T002 仍是 in-review。QA 已在 REV-M0-T11 签署通过，项目经理在群里确认这两张卡标为 done。标完后仍是 366 项：32 done、6 in-review、7 in-progress、268 planned、49 blocked、4 ready。三份正文使用这组数字，并注明 as of commit `3bb311ad3ab86c0de2f871876a50c7d50f9bb985` 加上本次 done。

`scripts/check-project-governance.cjs` 不比较这三份的任务计数和活看板。它核对治理块、链接、索引和 done 卡的交付块。因此没有改检查程序。模拟再把一张已有交付的 in-review 卡标为 done 后，检查仍通过；该模拟不入库。ISSUE-026 仍为 in-review。不改 `docs/reference/`。

## 项目经理关闭

QA 签署提交 `9bcde17`，记录为 REV-M0-T13。项目经理授权后，ISSUE-026 标为 closed。不新增任务卡。PRD、ROADMAP、PROJECT_BRIEF 的里程碑快照不改。活看板手写摘要另按表格重数。不改 `docs/reference/`。
