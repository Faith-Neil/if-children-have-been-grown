为什么有这个文件：登记把演示项目表对齐字典 v1.9 的 bid_project。

它解决什么问题：第 6 节偏差已获项目经理有条件批准，但 demo_project 仍不是字典表，需要一张排在正式项目表之后的卡来对齐，并且不能删掉已有项目。

# ISSUE-035：demo_project 对齐字典 bid_project

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-035 |
| 类型 | change |
| 优先级 | P1 |
| 状态 | in-review |
| 负责人 | backend |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-22 |
| revision | bid-project-align-1 |
| 关联 Task | [BE-M0-T19](../docs/tasks/BE-M0.md#be-m0-t19) |
| 关联 PR | 未创建。随既有分支提交，不新开 PR |
| 本地验收 | [BE-M0-T19 交付](../docs/delivery/BE-M0-T19.md) |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [BE-M0-T19 交付](../docs/delivery/BE-M0-T19.md) |
| 代码 / 流程解释 | [BE-M0-T19 代码解释](../docs/code/BE-M0-T19.md) |
| 验证记录 | [test_project_dictionary_alignment.py](../tests/backend/test_project_dictionary_alignment.py) 5 项通过；全量回归 43 项通过 |

本项开发完成，进入 in-review 阶段，等待主 Agent 与项目经理验收，绝不私自关闭 Issue。任务卡状态流转为 in-review。

## 现象与证据

BE-M0-T13 把当前项目和分工写入 `demo_project`、`demo_project_team`。方案第 6 节对照字典 v1.9 的 `bid_project`、`bid_project_member`，列出的偏差需要项目经理批准。项目经理已有条件批准这些偏差。本轮通过 BE-M0-T19 实施对齐，扩充 tender_type, budget_amount_cents, deadline_at, security_level, industry, is_archived 与 A 组系统审计字段，并通过 Alembic 0011 增量脚本实现无损迁移，保留历史记录不删除。

## 影响与分流

- 开工条件：正式 `bid_project`、`bid_project_member` 以及投标主体已经存在。
- 对齐范围：扩充业务属性字段与 A 组审计列，时间型 `deadline_at`，支持软删除过滤。
- 迁移必须保留历史项目和成员，禁止用删除清空旧行。
- 不改 `docs/reference/`。不改 PRD、ROADMAP、PROJECT_BRIEF 的里程碑快照。不改工作流文件。
- ISSUE-018 仍为 in-progress。BE-M0-T19 已交付并流转为 in-review。本 Issue 标为 in-review，不标 closed。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| BE-M0-T19 | `demo_project` 对齐 `bid_project`，保留历史行 | [代码解释](../docs/code/BE-M0-T19.md)；[交付报告](../docs/delivery/BE-M0-T19.md) | AC-01～AC-04 | in-review |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 正式表存在后，项目包含业务属性、保密级别与时间型投标截止时间 | 已通过：[BE-M0-T19 交付](../docs/delivery/BE-M0-T19.md) |
| AC-02 | 支持 A 组系统审计列，兼容旧版与 v1 接口返回 | 已通过：[BE-M0-T19 交付](../docs/delivery/BE-M0-T19.md) |
| AC-03 | 契约对齐，spec/openapi/demo-v1.json 与运行时通过双重一致性校验 | 已通过：[test_operation_ids.py](../tests/backend/test_operation_ids.py) |
| AC-04 | 迁移保留历史项目和成员，不删除旧数据。卡片完成后为 in-review，不由开发者标 done | 已通过：Alembic 0011 增量脚本落地，状态保持 in-review |

本卡保持 in-review，不私自标 closed。

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
