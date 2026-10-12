为什么有这个文件：记录ISSUE-005本轮契约卡如何对齐需求、方案和交付。

它解决什么问题：避免错误体已经改变，计划和任务仍各写各的状态。

# ISSUE-005本轮同步

当前日期2026-10-12。治理版本保持g1.1，治理块仍是2026-10-11 / ISSUE-007，没有改治理规则。本轮只实施DG-05的卡片(a)(b)，状态停在in-review。已rebase到包含离线CI、QA复跑、T06冒烟和OpenAI兼容适配器的`codex/repository-foundation`。

| 对象 | 是否改动 | 理由 | 对应 ISSUE-005 |
|---|---|---|---|
| PRD | 未改 | 没有改页面、角色、业务规则或验收口径 | “将按每项最终决定同步业务正文”；本轮不是页面范围决定 |
| ROADMAP | 未改 | 六张卡记在任务看板和 BE-M0。路线图同日已有其他更新，本轮不覆盖 | 同段：最终决定才同步路线正文 |
| ARCHITECTURE | 未改 | 项目经理要求本轮不改 ARCHITECTURE。建议日后补一句：v1 错误体和 24 小时幂等已提交复查，且本轮无驱动或迁移。MySQL 8 已由并行提交写入该文 | “将按每项最终决定同步业务正文”；本轮不改该基线 |
| PROJECT_BRIEF | 已改 | 后台一行改为业务库已决定为 MySQL 8 但未接入；排期改为 350 项：20done、4in-review、7in-progress、266planned、49blocked、4ready。T008 与 AI-02 保持项目经理已确认的 done，AI-03 保持 in-review | 同一决定段；卡片表的 in-review |
| Issue看板/详情 | 已改 | ISSUE-005 由 blocked 改为 in-review，revision 为 review-3。不标 closed。并行提交已把 MySQL 8 写入 ISSUE-010；本轮不改那个文件 | 状态行与 DG-05 拆卡段 |
| TASK_BOARD | 已改 | BE-M0-T02、T03 为 in-review；T04～T07 为 ready。APP-M2-T002 仍 planned。当前 350 项：20done、4in-review、7in-progress、266planned、49blocked、4ready。T008 与 AI-02 保持项目经理已确认的 done，AI-03 保持 in-review | 卡片表 |
| PROJECT_STATUS | 已改 | 增加契约阶段段落、MySQL 8 未接入和 350 项计数。344 项、20done、2in-review、7in-progress 是加入本轮六张卡之前的计数 | 卡片表与业务库决定段 |
| DOCUMENT_INDEX | 已改 | 登记两张交付、两份代码解释、验证和本同步表 | 同步表链接 |
| OpenAPI | 已从代码导出 | 不手改。49 路径、57 操作。新增错误表和幂等说明，没有新路由 | DG-05 证据列 |

数据库决定只记在文档里。本轮没有 MySQL 驱动、迁移、连接配置或表结构。PR #3 未合入，也没有新开 PR。in-review 不是 done，也不是发布。

DG-01～DG-04、DG-06，以及 DG-05 的锁迁移、导出快照、202/SSE、operationId，都还没有验收。
