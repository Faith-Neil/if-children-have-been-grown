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
