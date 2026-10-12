为什么有这个文件：登记APP-M1-T06端到端验收计划的编制。

它解决什么问题：在执行T06验收前统一步骤、证据要求和缺口，避免以按钮能点或内部稿冒充验收。

# ISSUE-015：APP-M1-T06端到端验收计划

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-015 |
| 类型 | change |
| 优先级 | P1 |
| 状态 | in-review |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | t06-plan-1 |
| 关联 Task | [REV-M0-T03](../docs/tasks/REV-M0.md#rev-m0-t03)；被验收[APP-M1-T06](../docs/tasks/APP-M1.md#app-m1-t06)保持in-progress |
| 关联 PR | [PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3)，待合入 |
| 本地验收 | 计划待项目经理评审；T06本身未执行验收 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [REV-M0-T03交付](../docs/delivery/REV-M0-T03.md) |
| 代码 / 流程解释 | 无代码变更：仅计划文档，交付中说明 |
| 验证记录 | [T06验收计划](../docs/testing/2026-10-12-app-m1-t06-acceptance-plan.md) |

## 现象与证据

APP-M1-T06卡要求合成招标包整链、失败路径、真实HTTP、Word文件及四个基准页截图，但证据分散在多份冒烟和专项测试中，Word视觉渲染10-10记录失败。

## 影响与分流

- 本次只编制计划并映射现有测试、标出缺口；不改代码，不改变T06状态。
- 依赖：无。执行验收另行进行。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| REV-M0-T03 | T06验收计划 | `docs/testing/2026-10-12-app-m1-t06-acceptance-plan.md` | AC-01～02 | in-review |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 覆盖端到端、Word版式、多角色、权限反例、过期数据，逐项映射现有测试并标缺口 | 已编制，待评审 |
| AC-02 | 治理检查通过，看板/进度/索引同步 | 通过，2026-10-12 |

## 六份基线 impact 与同步表

| 基线 | impact | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响：未改需求 | 无 | — / ISSUE-015 / 2026-10-12 | 已核对 |
| ROADMAP | 无影响：未改阶段 | 无 | — / ISSUE-015 / 2026-10-12 | 已核对 |
| ARCHITECTURE | 无影响：未改接口或结构 | 无 | — / ISSUE-015 / 2026-10-12 | 已核对 |
| TASK_BOARD | 有影响：新增REV-M0-T03 in-review | `docs/TASK_BOARD.md` | 0.6 / ISSUE-015 / 2026-10-12 | 已同步 |
| PROJECT_STATUS | 有影响：计数与计划说明 | `docs/PROJECT_STATUS.md` | — / ISSUE-015 / 2026-10-12 | 已同步 |
| DOCUMENT_INDEX | 有影响：D-178～D-180 | `docs/DOCUMENT_INDEX.md` | g1.1 / ISSUE-015 / 2026-10-12 | 已同步 |

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | t06-plan-1 / in-review | 计划完成，待项目经理评审后执行 | 成长测试QA |
