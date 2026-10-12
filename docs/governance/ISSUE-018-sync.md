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

## impl-1（2026-10-12）

项目经理批准方案和四项依赖后，本 Issue 改为 in-progress。BE-M0-T10 实施连接和空基线。T11～T13 登记为 planned，未写代码。依赖引入另见 [ISSUE-023 同步](ISSUE-023-sync.md)。PRD、ROADMAP、ARCHITECTURE 仍未改。进度改为 360 项：23 done、7 in-review、7 in-progress、269 planned、50 blocked、4 ready。
