为什么有这个文件：记下在最新提交上重数任务看板，并与三份基线的计数字句对照。

它解决什么问题：避免 QA 新增 done 卡之后，PRD、路线图和接手说明仍停在上一组数字。

# 2026-10-12 ISSUE-026 基线计数复核

关联 ISSUE-026。状态 in-review。不标 closed。不改 `docs/reference/`，不改后台，不改请求层。

## 核对对象

核对发生在拉取之后的 `84a3fca4c5e8f59410d2e0a100bc358100d0b0b6`（`docs: QA sign-off for BE-M0-T15 Word default style with checker and sample (REV-M0-T10)`）。工作目录为仓库根。只数 `docs/TASK_BOARD.md` 里 `<!-- task-board:start -->` 与 `<!-- task-board:end -->` 之间、状态列属于 done、in-review、in-progress、planned、blocked、ready、cancelled 的任务行。三份正文取该提交上的计数字句，不把更早的历史句算进这一次。

## 计数

| 来源 | 合计 | done | in-review | in-progress | planned | blocked | ready |
|---|---:|---:|---:|---:|---:|---:|---:|
| 任务看板表格 | 364 | 27 | 9 | 7 | 268 | 49 | 4 |
| `docs/PRD.md` 第19行（84a3fca） | 363 | 26 | 9 | 7 | 268 | 49 | 4 |
| `docs/ROADMAP.md` 第17行（84a3fca） | 363 | 26 | 9 | 7 | 268 | 49 | 4 |
| `docs/PROJECT_BRIEF.md` 排期行（84a3fca） | 363 | 26 | 9 | 7 | 268 | 49 | 4 |

看板开篇已写「364项中 done 27、in-review 9、in-progress 7、planned 268、blocked 49、ready 4」，与表格一致。多出的 done 卡是 REV-M0-T10（BE-M0-T15 Word 默认版式 QA 签署复核）。in-review 仍是九张：OPS-M0-T02、REV-M0-T06、REV-M0-T08、BE-M0-T14、BE-M0-T15、APP-M2-T001、APP-M2-T002、AI-01、AI-03。APP-M2 仍是 T001 与 T002 in-review、T008 done、T124 blocked、其余 255 planned。

## 结论

三份正文与看板不一致，不是 no change needed。本提交把 PRD 第19行、ROADMAP 第17行、PROJECT_BRIEF 排期行改成 `364项：27done、9in-review、7in-progress、268planned、49blocked、4ready`。改完后四者的合计与六个状态数相同。ISSUE-026 仍为 in-review。

```text
node scripts/check-project-governance.cjs
治理检查通过：223 份 Markdown、364 项任务、28 项 Issue。
```

## 局限

这是文档计数，不是产品完成率。没有重跑前端测试，也没有重跑 Playwright。治理检查只证明记录之间的链接和状态词一致。

## 2026-10-12 第二次重数：里程碑快照

`bde8e9e` 写下的 364 项、27 done 在拉取后已经过时。看板最后一次变动在 `3bb311ad3ab86c0de2f871876a50c7d50f9bb985`（`ci: mark the MySQL job done and fail on any skip`）。随后的 `2bdbff5` 只把 BE-M0-T14 交付里的计数改成截至该提交的快照，表格没有变化。其中 `d55d507` 把 REV-M0-T11 标为 done，`b20b844` 把 REV-M0-T12 标为 done，`3bb311a` 把 BE-M0-T14 标为 done 并关闭 ISSUE-025。计数方法与上一节相同。

| 来源 | 合计 | done | in-review | in-progress | planned | blocked | ready |
|---|---:|---:|---:|---:|---:|---:|---:|
| 任务看板表格（3bb311a，T001/T002 仍 in-review） | 366 | 30 | 8 | 7 | 268 | 49 | 4 |
| `docs/PRD.md`、`docs/ROADMAP.md`、`docs/PROJECT_BRIEF.md`（3bb311a 上的正文） | 364 | 27 | 9 | 7 | 268 | 49 | 4 |
| 本里程碑标完 T001 与 T002 之后的任务看板 | 366 | 32 | 6 | 7 | 268 | 49 | 4 |
| 三份正文的里程碑快照 | 366 | 32 | 6 | 7 | 268 | 49 | 4 |

3bb311a 上的 in-review 八张是 OPS-M0-T02、REV-M0-T06、REV-M0-T08、BE-M0-T15、APP-M2-T001、APP-M2-T002、AI-01、AI-03。QA 已在 [REV-M0-T11](2026-10-12-qa-t001-t002-signoff.md) 签署 T001 与 T002 通过，并写明 done 由项目经理设置。项目经理在群里确认后，本提交把这两张卡标为 done。标完后 in-review 剩六张：OPS-M0-T02、REV-M0-T06、REV-M0-T08、BE-M0-T15、AI-01、AI-03。APP-M2 仍是 259 张：T001、T002 与 T008 为 done，T124 为 blocked，其余 255 张 planned。

快照不能写成「as of 3bb311a 已经是 32 done」。3bb311a 当时仍是 30 done、8 in-review。三份正文写成：366 项、32 done、6 in-review、7 in-progress、268 planned、49 blocked、4 ready（as of commit `3bb311ad3ab86c0de2f871876a50c7d50f9bb985`，并计入本里程碑将 APP-M2-T001 与 APP-M2-T002 标为 done）。任务看板是准绳。这组数字只在里程碑更新。

规则记在 [ISSUE-026](../../issues/ISSUE-026.md)、[同步表](../governance/ISSUE-026-sync.md) 和 [WORKFLOW](../governance/WORKFLOW.md) 第4节。治理块仍是 g1.1 / 2026-10-11 / ISSUE-007。

`scripts/check-project-governance.cjs` 不比较 PRD、ROADMAP、PROJECT_BRIEF 的任务计数和活看板。它核对治理块、链接、索引，以及 done 卡是否有 `docs/delivery/` 里的 task-delivery 块。因此没有改检查程序，也没有为「计数必须相等」加测试。

模拟：把已有交付的 in-review 卡 AI-03 临时改成 done。表格变成 366 项：33 done、5 in-review、7 in-progress、268 planned、49 blocked、4 ready。三份快照仍写 32 done、6 in-review。检查仍然通过，没有要求快照与活看板相等。随后把 AI-03 改回 in-review。这次改动不入库。ISSUE-026 仍为 in-review。

```text
node scripts/check-project-governance.cjs
治理检查通过：228 份 Markdown、366 项任务、28 项 Issue。

# AI-03 临时标为 done 后再跑同一命令
治理检查通过：228 份 Markdown、366 项任务、28 项 Issue。
```
