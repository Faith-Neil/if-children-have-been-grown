为什么有这个文件：登记把三份基线里的任务计数改成与任务看板相同的一组数字。

它解决什么问题：避免 PRD、路线图和接手说明仍写着旧的 356 或 360，而看板已经是 361。

# ISSUE-026：基线任务计数对齐看板

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-026 |
| 类型 | change |
| 优先级 | P1 |
| 状态 | closed |
| 登记 / 更新日期 | 2026-10-12 / 2026-10-12 |
| revision | count-sync-1 |
| 关联 Task | 不新增任务卡。新增一张卡会把 361 改成 362。计数以 [任务看板](../docs/TASK_BOARD.md) 为准 |
| 关联 PR | [PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3) 仍待合入。本轮直接提交在 `codex/repository-foundation`，不新建 PR |
| 本地验收 | 在 `3bb311a` 上重数后，三份基线改为里程碑快照。QA 签署 9bcde17（REV-M0-T13）。项目经理授权后本 Issue 标为 closed。不新增任务卡。见 [签署](../docs/testing/2026-10-12-issue-026-snapshot-signoff.md) |
| 合入 / 发布 | 未合入 / 未发布 |
| 交付说明 | [ISSUE-026 交付](../docs/delivery/ISSUE-026.md) |
| 代码 / 流程解释 | 无应用代码。[说明](../docs/code/ISSUE-026.md) |
| 验证记录 | [2026-10-12 基线复核](../docs/testing/2026-10-12-issue-026-baseline-count-check.md)；早前核对见 [计数核对](../docs/testing/2026-10-12-issue-026-counts.md) |

`issues/` 里已有详情止于 ISSUE-023。ISSUE-024 与 ISSUE-025 没有文件。项目经理指定本变更为 ISSUE-026。

## 现象与证据

看板在并入 `b465316` 之后为 **361** 项：**26 done、6 in-review、7 in-progress、268 planned、50 blocked、4 ready**。BE-M0-T08 与 BE-M0-T10 已由项目经理在 QA 签署 98c5129 后标为 done。APP-M2 的 259 张卡中 T001 与 T002 为 in-review，T008 为 done，T124 为 blocked，其余 **255** planned。

对齐前：

- `docs/PRD.md` 第19行写「其余258卡planned」。
- `docs/ROADMAP.md` 第17行写「当前共356项任务，23done、6in-review、7in-progress、266planned、50blocked、4ready」。
- `docs/PROJECT_BRIEF.md` 第30行写「当前共360项：23done、7in-review、7in-progress、269planned、50blocked、4ready」和「其余256项planned」。

## 影响与分流

只改这三份里的任务计数，以及看板、项目进度、Issue 看板和文档索引里指向这次对齐的句子。不改请求层重试：网络错误、502 和 503 仍最多 3 次（含首次），409、422、423、428 仍不自动重试。不改 `backend/`、`tests/backend/` 和 `docs/reference/`。QA 签署 9bcde17（REV-M0-T13）后，项目经理确认本 Issue 为 closed。不新增任务卡。本里程碑按项目经理在群里的确认，把 APP-M2-T001 与 APP-M2-T002 标为 done。

ARCHITECTURE 第21行仍写「布局、浏览器路由和全页离开保护继续本卡」。ROADMAP 第19行仍写整卡 in-progress 和接下来补布局。PROJECT_BRIEF 第68行仍写接下来补布局组件。这三句不是任务总数，本轮不改。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| 无新卡 | 三份基线计数写成里程碑快照 | `docs/PRD.md`、`docs/ROADMAP.md`、`docs/PROJECT_BRIEF.md` | AC-01、AC-02 | closed |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | PRD、ROADMAP、PROJECT_BRIEF 的任务计数是里程碑快照；APP-M2 其余 255 张 planned | 在 `3bb311a` 上看板为 366 项：30 done、8 in-review。项目经理确认后 T001 与 T002 为 done，快照写成 366 项：32 done、6 in-review、7 in-progress、268 planned、49 blocked、4 ready，并注明 as of commit。见 [复核](../docs/testing/2026-10-12-issue-026-baseline-count-check.md) |
| AC-02 | 不改 `frontend/web/src/api.ts` 的重试，不改后台 | 本提交不包含这些路径 |
| AC-03 | 治理检查通过 | QA 签署 9bcde17（REV-M0-T13）。项目经理确认后本 Issue 为 closed。见交付中的检查输出 |

## 六份基线 impact 与同步表

| 基线 | impact | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 有影响。任务总数和 APP-M2 剩余 planned | `docs/PRD.md` 第19行 | count-sync-1 / ISSUE-026 / 2026-10-12 | 已改，治理块仍为 g1.1 / 2026-10-11 / ISSUE-007 |
| ROADMAP | 有影响。第17行任务总数；点名 T002 为 in-review | `docs/ROADMAP.md` 第17行 | 同上 | 已改。第19行未改 |
| ARCHITECTURE | 无影响。没有任务总数 | `docs/ARCHITECTURE.md` 第21行仍是布局句子 | 同上 | 已核对，未改 |
| TASK_BOARD | 有影响。只加 ISSUE-026 一句，计数保持 361 | `docs/TASK_BOARD.md` 开篇 | 同上 | 已改 |
| PROJECT_STATUS | 有影响。计数原本已是 361，补一句指向本 Issue | `docs/PROJECT_STATUS.md` 任务进度口径 | 同上 | 已改 |
| DOCUMENT_INDEX | 有影响 | D-001、D-002、D-004、D-012、D-017、D-049 与 D-283～D-287 | 同上 | 已改 |

细节见 [同步表](../docs/governance/ISSUE-026-sync.md)。

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 |
|---|---|---|---|
| 2026-10-12 | count-sync-1 / in-review | 三份基线已写成看板数字。请求层重试未动。等待项目经理签收 | [验证](../docs/testing/2026-10-12-issue-026-counts.md) |
| 2026-10-12 | count-sync-1 / in-review | ISSUE-025 新增 BE-M0-T14 后，三份计数字句改为 362 项、7 in-review。本 Issue 仍 in-review，不改请求层 | [ISSUE-025](ISSUE-025.md) |
| 2026-10-12 | count-sync-2 / in-review | AI-01 进入 in-review 后，三份基线改为 26 done、8 in-review、7 in-progress、268 planned、49 blocked、4 ready。不改 api.ts。仍 in-review | [验证](../docs/testing/2026-10-12-issue-026-counts.md) |
| 2026-10-12 | count-sync-3 / in-review | `84a3fca` 新增 REV-M0-T10 为 done。看板 364 项、27 done。三份正文从 363 项、26 done 改成同一组。仍 in-review，不标 closed | [复核](../docs/testing/2026-10-12-issue-026-baseline-count-check.md) |
| 2026-10-12 | count-sync-4 / in-review | `3bb311a` 看板为 366 项、30 done、8 in-review。项目经理在群里确认后，T001 与 T002 标为 done，成为 32 done、6 in-review。三份基线改为 as of commit 快照。检查程序不比较快照与活看板。仍 in-review | [复核](../docs/testing/2026-10-12-issue-026-baseline-count-check.md) |
| 2026-10-12 | count-sync-4 / closed | 项目经理在 QA 签署 9bcde17（REV-M0-T13）后确认 closed。不新增任务卡。三份基线仍是里程碑快照，不按之后的活看板改写。未合入、未发布 | [签署](../docs/testing/2026-10-12-issue-026-snapshot-signoff.md) |

## 本地验收与后续合入发布

- 本地核对已完成。QA 签署 9bcde17（REV-M0-T13）后，项目经理确认 closed。
- 未跑浏览器。这次不改页面。
- PR #3 未合入，产品未发布。
