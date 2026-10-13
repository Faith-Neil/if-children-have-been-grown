为什么有这个文件：记录ISSUE-005本轮契约卡如何对齐需求、方案和交付。

它解决什么问题：避免错误体已经改变，计划和任务仍各写各的状态。

# ISSUE-005本轮同步

当前日期2026-10-12。治理版本保持g1.1，治理块仍是2026-10-11 / ISSUE-007，没有改治理规则。DG-05 的卡片 (a)(b) 已由项目经理于 10-12 12:28 在 QA 签署后确认。ISSUE-005 保持 in-progress，因为 T04～T07 未完成，不关闭。

| 对象 | 是否改动 | 理由 | 对应 ISSUE-005 |
|---|---|---|---|
| PRD | 未改 | 没有改页面、角色、业务规则或验收口径 | “将按每项最终决定同步业务正文”；本轮不是页面范围决定 |
| ROADMAP | 未改 | 六张卡记在任务看板和 BE-M0。路线图同日已有其他更新，本轮不覆盖 | 同段：最终决定才同步路线正文 |
| ARCHITECTURE | 已改 | 只补一句：2026-10-12（ISSUE-005）`/api/v1` 错误体和 24 小时幂等回执已提交复查；本轮不引入驱动、迁移或表结构，测试仍用内存仓库；状态表不在该文重复。持久化方案留在 ISSUE-018 | 与建议句一致；本轮补上 |
| 接口约定 | 已改（补登） | `docs/architecture/icg-reference-contract.md` 在契约提交里写了 v1 错误体和 24 小时幂等。QA 缺口 Q1 指出同步表此前未列该文件。本行补登，不另改约定正文 | Q1 |
| PROJECT_BRIEF | 已改 | 后台一行改为业务库已决定为 MySQL 8 但未接入。T02 与 T03 现为 done。现行 356 项由本轮与 ISSUE-018 另计 | 同一决定段；卡片表现为 done |
| Issue看板/详情 | 已改 | ISSUE-005 现为 in-progress，revision 为 progress-4。T02 与 T03 为 done。不标 closed。并行提交已把 MySQL 8 写入 ISSUE-010 | 状态行与 DG-05 拆卡段 |
| TASK_BOARD | 已改 | BE-M0-T02、T03 为 done，注明项目经理于 10-12 12:28 在 QA 签署后确认。T04～T07 仍为 ready。现行 356 项 | 卡片表 |
| PROJECT_STATUS | 已改 | 增加契约阶段段落、MySQL 8 未接入和 350 项计数。344 项、20done、2in-review、7in-progress 是加入本轮六张卡之前的计数 | 卡片表与业务库决定段 |
| DOCUMENT_INDEX | 已改 | 登记两张交付、两份代码解释、验证和本同步表 | 同步表链接 |
| OpenAPI | 已从代码导出 | 不手改。49 路径、57 操作。新增错误表和幂等说明，没有新路由 | DG-05 证据列 |

数据库决定只记在文档里。本轮没有 MySQL 驱动、迁移、连接配置或表结构。PR #3 未合入，也没有新开 PR。T02 与 T03 的 done 不是 Issue 关闭，也不是发布。

DG-01～DG-04、DG-06，以及 DG-05 的锁迁移、导出快照、202/SSE、operationId，都还没有验收。

## lease-v1

2026-10-12：BE-M0-T04 改为 in-review。三条 `POST /api/v1/chapters/{chapter_id}/lock`、`/lock/renew`、`/lock/release` 调用原租约规则，时长 120 秒。旧 `/api` 三条锁路由保留给编辑页和 `/demo`。没有重跑 `export_openapi.py`，没有新增错误码。`operationId` 留给 BE-M0-T07。ISSUE-005 仍为 in-progress，revision 为 progress-5。看板为 387 项：51 done、12 in-review、7 in-progress、265 planned、48 blocked、4 ready。BE-M0 为 19 项，9 项 done。T05～T07 仍为 ready。上文表格里的 356 项和 progress-4 是当时记录，不回写。

## export-snapshot

2026-10-12：BE-M0-T05 改为 in-review。单章导出响应写明 `check_id`、`revision`、`content_hash`、`input_fingerprint`。不返回 `stale`。资料变化后旧检查返回 409 `CHECK_STALE`，旧下载返回 409 `EXPORT_STALE`。没有重跑 `export_openapi.py`，没有新增错误码。ISSUE-005 仍为 in-progress，revision 为 progress-6。看板为 387 项：51 done、13 in-review、7 in-progress、265 planned、48 blocked、3 ready。BE-M0 为 19 项，9 项 done。T04 仍为 in-review。T06～T07 仍为 ready。上文 lease-v1 段的 12 in-review 和 progress-5 是当时记录，不回写。

## 2026-10-13 QA

QA 签署 BE-M0-T04 / BE-M0-T05（REV-M0-T32 / T33，tip `90b2334`）通过。ISSUE-005 仍 in-progress，不关闭。不改 `docs/reference/` 与三份基线快照。
