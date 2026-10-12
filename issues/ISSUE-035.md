为什么有这个文件：登记把演示项目表对齐字典 v1.9 的 bid_project。

它解决什么问题：第 6 节偏差已获项目经理有条件批准，但 demo_project 仍不是字典表，需要一张排在正式项目表之后的卡来对齐，并且不能删掉已有项目。

# ISSUE-035：demo_project 对齐字典 bid_project

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-035 |
| 类型 | change |
| 优先级 | P1 |
| 状态 | new |
| 负责人 | backend |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | bid-project-align-1 |
| 关联 Task | [BE-M0-T19](../docs/tasks/BE-M0.md#be-m0-t19) |
| 关联 PR | 未创建。随既有分支提交，不新开 PR |
| 本地验收 | 未执行。本轮只登记，不改表 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | 尚未建立。任务为 planned，无运行时代码 |
| 代码 / 流程解释 | 无代码影响。对照仍在 [方案第 6 节](../docs/architecture/mysql-8-persistence-plan.md) |
| 验证记录 | 未执行。实现后再补 |

登记时 Issue 看板没有 planned。本项已登记、未开工、未关闭，因此状态记为 new。任务卡状态是 planned。不另开 ISSUE-034 或 ISSUE-036。

## 现象与证据

BE-M0-T13 把当前项目和分工写入 `demo_project`、`demo_project_team`。方案第 6 节对照字典 v1.9 的 `bid_project`、`bid_project_member`，列出的偏差需要项目经理批准。项目经理已有条件批准这些偏差。对齐工作要等正式项目表、成员表和投标主体存在之后再做。本轮不改表、不补列、不删行。

## 影响与分流

- 开工条件：正式 `bid_project`、`bid_project_member` 以及投标主体已经存在。
- 对齐范围：GUID 主键、`project_status`、投标主体、一成员一行、A 组审计列、时间型 `bid_deadline_at`。索引为 `(company_id, status)`、`(company_id, bid_deadline_at)`、`(tender_no, lot_no)`。成员唯一 `(project_id, user_id)`。
- 迁移必须保留历史项目和成员，禁止用删除清空旧行。
- 不改 `docs/reference/`。不改 PRD、ROADMAP、PROJECT_BRIEF 的里程碑快照。不改工作流文件。
- ISSUE-018 仍为 in-progress。BE-M0-T13 已依据 QA ae38ec3，PM 17:16 确认 done。本 Issue 仍为 new，不标 closed。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| BE-M0-T19 | `demo_project` 对齐 `bid_project`，保留历史行 | 方案第 6 节；实现时再写迁移 | AC-01～AC-04 | planned |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 正式表存在后，项目主键为 GUID，并有状态、投标主体和时间型投标截止时间 | 未执行 |
| AC-02 | 成员是独立行，含角色与分册，并有 A 组审计列 | 未执行 |
| AC-03 | 项目索引和成员唯一约束与字典一致 | 未执行 |
| AC-04 | 迁移保留历史项目和成员，不删除旧数据。卡片完成后为 in-review，不由开发者标 done | 未执行 |

未做浏览器、服务或发布验收。new 不是 closed，planned 不是 done。

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。里程碑快照不改。本卡不改产品规则 | 不改 `docs/PRD.md` | bid-project-align-1 / ISSUE-035 / 2026-10-12 | 已核对 |
| ROADMAP | 无影响。理由同 PRD | 不改 `docs/ROADMAP.md` | bid-project-align-1 / ISSUE-035 / 2026-10-12 | 已核对 |
| ARCHITECTURE | 无影响。对齐步骤写在持久化方案，不改架构基线 | 不改 `docs/ARCHITECTURE.md` | bid-project-align-1 / ISSUE-035 / 2026-10-12 | 已核对 |
| TASK_BOARD | 有影响。新增 BE-M0-T19，状态 planned | `docs/TASK_BOARD.md`、`docs/tasks/BE-M0.md` | bid-project-align-1 / ISSUE-035 / 2026-10-12 | 已改 |
| PROJECT_STATUS | 有影响。活计数加一张 planned 卡，并把 T18 改为 in-review | `docs/PROJECT_STATUS.md` | bid-project-align-1 / ISSUE-035 / 2026-10-12 | 已改 |
| DOCUMENT_INDEX | 有影响。登记本 Issue 与同步表 | `docs/DOCUMENT_INDEX.md` | bid-project-align-1 / ISSUE-035 / 2026-10-12 | 已改 |
| PROJECT_BRIEF | 无影响。里程碑快照不改 | 不改 `docs/PROJECT_BRIEF.md` | bid-project-align-1 / ISSUE-035 / 2026-10-12 | 已核对 |

同步摘要见 [ISSUE-035 同步](../docs/governance/ISSUE-035-sync.md)。

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | bid-project-align-1 / new | 项目经理有条件批准第 6 节偏差。本项只登记，等正式项目表和成员表存在再迁移。不删历史行 | 方案第 6 节 |
| 2026-10-12 | bid-project-align-1 / new | BE-M0-T13 已依据 QA ae38ec3，PM 17:16 确认 done。本 Issue 仍为 new。BE-M0-T19 仍为 planned。不改表 | 方案第 6 节 |

## 本地验收与后续合入发布

- 本地验收：未执行。本轮不改表。
- 未覆盖：迁移、GUID、成员行和历史行保留。
- 六份基线：见上表与 [同步表](../docs/governance/ISSUE-035-sync.md)。
- PR：未新开。合入与发布均未发生。
