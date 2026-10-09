# ISSUE-003：建立需求、版本与 Bug 的协作治理

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-003 |
| 类型 | workflow |
| 优先级 | P1 |
| 登记日期 | 2026-10-09 |
| 最后更新日期 | 2026-10-09 |
| revision | g1.0 |
| 状态 | closed |
| 关联 Task | FE-M0-T02；[任务看板](../docs/TASK_BOARD.md) |
| 关联 PR | [PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3)，本轮治理变更待合入 |
| 本地验收 | AC-01～AC-04与独立复核通过；结构检查及10项检查器回归通过 |
| 合入 / 发布 | 本轮尚未合入 / 未发布 |
| 交付说明 | [FE-M0-T02](../docs/delivery/FE-M0-T02.md) |
| 代码解释 | [FE-M0-T02](../docs/code/FE-M0-T02.md) |
| 流程解释 | [协作工作流](../docs/governance/WORKFLOW.md) |

## 需求与影响

用户要求每次需求变更、版本更新和 Bug 都通过 Issue、任务与基线同步闭环，避免只改局部文件、文档口径失配或把本地验收当成合入发布。现有看板只登记历史事项，缺少统一类型、状态、模板、impact 表和互链要求。

本轮建立协作规则与可执行任务入口，新增治理检查脚本及测试，保留 ISSUE-001 外部分支待整合和 ISSUE-002 已本地验收关闭的事实。治理版本 g1.0 表示协作规则，不替换产品 PRD 版本，不调整产品范围、业务原型、技术选型或应用运行行为。

## 实施任务

| Task ID | 目标 | 涉及路径 | 状态 |
|---|---|---|---|
| FE-M0-T02 | 建立 Issue 前置、六份基线同步、任务与解释交付互链规则，并验证治理检查 | `issues/`、`docs/governance/WORKFLOW.md`、`docs/TASK_BOARD.md`、`docs/delivery/FE-M0-T02.md`、`docs/code/FE-M0-T02.md`、`scripts/check-project-governance.cjs`、`tests/governance/` 与基线入口 | done；本地验收通过、待合入 |

工程检查代码有影响：新增检查脚本和测试，需要实际验证及独立代码解释。业务原型无影响：本轮不修改编辑锁、AI、保存或其他原型行为，不宣称实现服务端能力。

## 四项验收

| 编号 | 完成条件 | 当前结果与证据 |
|---|---|---|
| AC-01 | 每次需求变更、版本更新、Bug 在实施前登记或关联 Issue；统一五类类型、七种状态，与 Task ID 和看板互链 | 通过：[管理说明](README.md)、[模板](template.md)、[Issue看板](index.md)定义类型与状态；[任务看板](../docs/TASK_BOARD.md)登记59项，开工须补真实Issue |
| AC-02 | 模板与规则逐项评估 PRD、ROADMAP、ARCHITECTURE、TASK_BOARD、PROJECT_STATUS、DOCUMENT_INDEX；有影响更新实际路径，无影响写具体原因 | 通过：六份基线已按下表更新；[逐项同步记录](../docs/governance/ISSUE-003-sync.md)说明业务参考、运行时栈等无影响依据 |
| AC-03 | revision、Issue ID 和日期口径一致；Issue、Task、PR、交付、代码解释互链；本地验收、合入、发布分别记录 | 通过：g1.0 / ISSUE-003 / 2026-10-09一致；[交付](../docs/delivery/FE-M0-T02.md)、[代码解释](../docs/code/FE-M0-T02.md)与PR #3互链；本地验收关闭，合入/发布仍未完成 |
| AC-04 | WORKFLOW、Issue 说明与模板、TASK_BOARD 及基线入口成为可用新规；治理检查与必要测试、路径及历史状态复核通过后再关闭 | 通过：[工作流](../docs/governance/WORKFLOW.md)、AGENTS及Cursor规则已落地；[验证记录](../docs/testing/2026-10-09-project-governance.md)记录42份Markdown、59任务、3Issue、10项回归及独立复核 |

## 本次六份基线 impact 与同步表

| 基线 | impact 与原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 当前状态 |
|---|---|---|---|---|
| PRD | 有影响：增加工程治理验收要求；产品页面与范围无语义变化 | `docs/PRD.md` 治理基线头与工程验收附录 | g1.0 / ISSUE-003 / 2026-10-09 | 已核对 |
| ROADMAP | 有影响：关联治理任务与修订；产品阶段计划不因本轮改变 | `docs/ROADMAP.md` 治理基线头与FE里程碑映射；任务执行放 TASK_BOARD | g1.0 / ISSUE-003 / 2026-10-09 | 已核对 |
| ARCHITECTURE | 有影响：增加协作文件结构与检查边界；产品模块、接口、数据库与模型栈无变化 | `docs/ARCHITECTURE.md` 治理基线头与治理附录 | g1.0 / ISSUE-003 / 2026-10-09 | 已核对 |
| TASK_BOARD | 有影响：新增59项任务与 FE-M0-T02 验收证据 | `docs/TASK_BOARD.md` 总看板；`docs/tasks/FE-M0.md` FE-M0-T02 | g1.0 / ISSUE-003 / 2026-10-09 | 已核对；T02本地done |
| PROJECT_STATUS | 有影响：记录新规则、工程检查与进度、验收/合入边界 | `docs/PROJECT_STATUS.md` 任务进度与下一步 | g1.0 / ISSUE-003 / 2026-10-09 | 已核对；当前2/59本地done |
| DOCUMENT_INDEX | 有影响：登记工作流、看板、Issue 模板、说明、代码解释与交付 | `docs/DOCUMENT_INDEX.md` 更新字段与新增入口条目 | g1.0 / ISSUE-003 / 2026-10-09 | 已核对；43项入口 |

其他受影响入口：`AGENTS.md`、根 README、`.cursor/rules/project-governance.mdc` 和 `issues/index.md` 已核对。看板治理头与本 Issue 同为 g1.0 / ISSUE-003 / 2026-10-09。产品参考原文和 xqr 选型无影响：本轮没有修改参考资产或采纳合作分支方案。

## 处理记录与后续状态

- 2026-10-09：登记用户本轮治理需求，关联 FE-M0-T02，状态 in-progress。
- 2026-10-09：新规、任务拆分、交付与代码解释落实，结构检查及10项回归通过；独立复核提出的状态缺项与Issue类型检查问题已修正并复核通过。本地验收关闭，FE-M0-T02转done；PR #3待合入，未发布。

后续从FE-M0-T03推进基线整合，并执行已建立的Issue与逐任务交付流程。PR 合入和版本发布使用独立字段，在实际发生后追加提交、版本与日期。
