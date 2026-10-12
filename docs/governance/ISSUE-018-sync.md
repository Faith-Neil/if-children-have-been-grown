为什么有这个文件：记录 ISSUE-018 方案轮次改了哪些基线。

它解决什么问题：避免把持久化方案误写成已经接入 MySQL。

# ISSUE-018 同步

日期 2026-10-12。revision plan-1。状态 in-review。无驱动、无迁移、无表。

| 对象 | 是否改动 | 理由 |
|---|---|---|
| PRD | 未改 | 未改业务规则 |
| ROADMAP | 未改 | 路线图计数留待方案被接受后另记。本文件不改它 |
| ARCHITECTURE | 未改 | 持久化步骤在方案正文。同日 ISSUE-005 补的一句不属于本 Issue |
| PROJECT_BRIEF | 已改 | 排期改为 356 项：23 done、6 in-review、7 in-progress、266 planned、50 blocked、4 ready。其中 50 blocked 含已有的 APP-M2-T124 |
| TASK_BOARD | 已改 | BE-M0-T08 为 in-review。BE-M0 现为 9 项 |
| PROJECT_STATUS | 已改 | 契约段指向方案；进度为 352 项 |
| DOCUMENT_INDEX | 已改 | 登记方案、交付、代码说明、本表和 ISSUE-021 |
| 依赖与 CI | 依赖已加入。MySQL CI 未在本表实施 | SQLAlchemy、PyMySQL、cryptography、Alembic 已在 ISSUE-023 下加入并锁定。传递依赖已精确锁定，含 MarkupSafe。MySQL CI 由 ISSUE-025 负责，进行中 |

ISSUE-021 的任务是 planned，Issue 状态是 blocked，因为看板没有 planned 这一档。它排在本方案之后，本轮不实施。范围另含 QA `200a105` 的 E2E-D5：`/API/...` 目前返回页面壳，将来要把 `/api` 前缀按大小写不敏感处理。本轮不改兜底路由。方案要求回执和登录会话跨进程共享，并在重启后仍在；这是验收条件，不是本轮实现。

## impl-4（2026-10-12）

BE-M0-T13 提交 `demo_project` 与 `demo_project_team`，状态 in-review。ISSUE-018 仍为 in-progress。章节、检查与导出、资料与承诺、工作流与任务、审计仍在内存。重数后任务看板为 375 项：42 done、9 in-review、7 in-progress、264 planned、49 blocked、4 ready。本提交把 T13 从 planned 改为 in-review 后，为 375 项：42 done、10 in-review、7 in-progress、263 planned、49 blocked、4 ready。任务看板是准绳。PRD、ROADMAP、PROJECT_BRIEF 的里程碑快照不改。`docs/reference/` 不改。方案第 6 节增加字典 v1.9 字段对照表。`demo_project`、`demo_project_team` 与 `bid_project`、`bid_project_member` 的每一处偏差都需要项目经理批准，未批准前不补列。工作流文件未改。

## impl-3（2026-10-12）

BE-M0-T12 提交 `chapter_lease`，状态 in-review。ISSUE-018 仍为 in-progress。T13 仍 planned。并入 ISSUE-016、ISSUE-029 关闭之后，任务看板为 371 项：39 done、6 in-review、7 in-progress、266 planned、49 blocked、4 ready。本提交把 T12 从 planned 改为 in-review 后，为 371 项：39 done、7 in-review、7 in-progress、265 planned、49 blocked、4 ready。任务看板是准绳。PRD、ROADMAP、PROJECT_BRIEF 的里程碑快照不改。`docs/reference/` 不改。方案第 5 节增加字典 v1.9 字段对照表。`chapter_lease` 与 `edit_lock` 的每一处偏差都需要项目经理批准，未批准前不补列。工作流文件未改。

## impl-2（2026-10-12）

BE-M0-T11 提交回执表和会话表，状态 in-review。ISSUE-018 仍为 in-progress。T12、T13 仍 planned。as of commit e6215d4, task board is source of truth。该提交看板为 366 项：32 done、7 in-review、7 in-progress、267 planned、49 blocked、4 ready。本提交后为 366 项：32 done、8 in-review、7 in-progress、266 planned、49 blocked、4 ready。PRD、ROADMAP、PROJECT_BRIEF 已是里程碑快照，本提交不改这三份。ARCHITECTURE 未改：ISSUE-005 那句 “本轮不引入驱动、迁移或表结构” 是该轮的历史记录，持久化步骤仍在方案正文。`docs/reference` 未改。工作流文件未改。QA M1 的降级再升级由 mysql 标记测试覆盖；现有 `backend-mysql` 的 `pytest -m mysql` 会执行它。DevOps 可以另加显式的 `downgrade base` 与 `upgrade head`，本卡不代改 `.github`。

## impl-1（2026-10-12）

项目经理批准方案和四项依赖后，本 Issue 改为 in-progress。BE-M0-T10 实施连接和空基线。T11～T13 登记为 planned，未写代码。依赖引入另见 [ISSUE-023 同步](ISSUE-023-sync.md)。PRD、ROADMAP、ARCHITECTURE 仍未改。进度改为 360 项：23 done、7 in-review、7 in-progress、269 planned、50 blocked、4 ready。

## QA 签署（REV-M0-T28）

2026-10-12 QA 对 BE-M0-T11（631d4c9）正式签署通过，见 [签署记录](../testing/2026-10-12-be-m0-t11-qa-signoff.md)。ISSUE-018 仍 in-progress；T11 仍 in-review，不标 done。REV-M0-T27 已用于 ISSUE-034 / PR #4，状态 in-review，不标 done。

## PM 确认（BE-M0-T13 / REV-M0-T23）

2026-10-12 项目经理确认 BE-M0-T13 与 REV-M0-T23 为 done，依据是 QA ae38ec3，PM 17:16 确认。ISSUE-018 仍为 in-progress。ISSUE-035 仍为 new，BE-M0-T19 仍为 planned。ISSUE-033 与 BE-M0-T18 仍为 in-review。看板为 386 项：50 done、11 in-review、7 in-progress、265 planned、48 blocked、5 ready。BE-M0 为 8/19 done。不改 PRD、ROADMAP、PROJECT_BRIEF 的里程碑快照。
