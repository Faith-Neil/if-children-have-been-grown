为什么有这个文件：集中显示每个任务的状态、依赖和交付入口。

它解决什么问题：帮助判断现在能做什么、卡在哪里、完成后有什么证据。

# 项目任务看板

任务版本：0.3；治理版本：g1.1；更新日期：2026-10-10；当前实现 Issue：[ISSUE-007](../issues/ISSUE-007.md)；生产门禁：[ISSUE-005](../issues/ISSUE-005.md)。

将 [前端 ROADMAP](ROADMAP.md) 的 Phase 0～8 与发布 Milestone 1～5 拆为 **59 张任务卡**，由 FE-M0～FE-M8 管理。前缀 FE 表示前端合作交付；这些编号与参考全系统 M0～M8 的门禁、周期和范围独立。

项目73项中 **done 8、in-progress 7、planned 10、blocked 48、ready 0**。APP-M1的11项产品联调任务中，前5项正在实现，第6项正在验收，第7/8项分别后续拆分和完整审计；T09～11的数值服务承诺子任务已本地验收，完整故障等级/服务时段、规则与Word版式仍待补齐。FE-M0-T03继续来源评审。旧FE59项保留为历史计划，OPS/REV/BE各1项已本地验收；PR #3待合入。以ICG页面/业务为实际目标，旧任务数量和小demo不代表产品完成率。

59张前端卡片估算合计 209 小时，单卡 2～4 小时，处于 0.5～4 小时的任务粒度目标内。该总和是已有基线/接口条件下的前端增量估算，不是项目排期，不含后端、模型、取得输入、评审或等待时间。开工若预计超 4 小时，先继续拆卡并登记 Issue/版本变更，保留原任务 ID 的历史。

## 状态与完成条件

| 状态 | 含义 |
|---|---|
| `planned` | 已分解，尚未启动；范围/优先级或前置条件仍待核对 |
| `blocked` | 明确等待已列出的基线、任务依赖、契约或真实服务 |
| `ready` | 已关联 Issue，基线、依赖、范围、验收与接口条件均已满足，尚未开工 |
| `in-progress` | 正在实施或验收；不能以文件已创建等同完成 |
| `in-review` | 实现及完成材料已提交，等待任务验收 |
| `done` | 验收通过、专属交付文件与代码/文档解释存在，Issue/进度/文档/索引已同步 |
| `cancelled` | 已有明确取舍；链接关联 Issue 的取消决定，保留历史 |

每张卡完成时必须新增自己的 `docs/delivery/<TASK_ID>.md`，说明变更结果、实际文件、验证命令及结果、未实现项和限制。有代码修改时，同时创建独立 `docs/code/<TASK_ID>.md` 并在交付中链接，解释入口、调用顺序、数据/状态流、关键判断与异常、依赖及限制；无代码修改在交付中明确写“无”并说明文档目的。随后同步统一 Issue、任务看板、项目进度、PRD/ROADMAP/ARCHITECTURE 的影响核对和文档索引。相关文档无需修改时，交付中逐项记录所核对章节与理由。

只有任务专属交付文件存在、验收证据齐全且状态同步后才能标 `done`；本地已验收与已合入/已发布分别记录。待产出的路径使用代码文本，不创建虚假的交付链接。

统一 Issue 用于需求变更、版本更新和 Bug；一个 Issue 可关联多张实现任务卡，任务不能替代 Issue 的决定与关闭记录。表中“—”表示尚未登记，开工前必须补真实关联，避免伪造 Issue 编号。

## 里程碑映射

| 前端里程碑 | 原路线图来源 | 任务数 | 当前完成 | 可并行关系 |
|---|---|---|---|---|
| [FE-M0 基线与基础](tasks/FE-M0.md) | ROADMAP Phase 0；发布 Milestone 1～5 的共用基础 | 10 | 2/10 | 来源评审与现有原型维护可独立推进；生产底座等待选型契约。 |
| [FE-M1 项目主流程](tasks/FE-M1.md) | ROADMAP Phase 1；发布 Milestone 1 | 7 | 0/7 | 项目创建、解析与资料列表依各自基础卡启动；事实不必等待全部矩阵界面。 |
| [FE-M2 章节生成](tasks/FE-M2.md) | ROADMAP Phase 2；发布 Milestone 2 | 5 | 0/5 | 章节树与方案接入按矩阵/事实依赖推进；任务卡默认能力依契约，不等待管理界面完成。 |
| [FE-M3 编辑台](tasks/FE-M3.md) | ROADMAP Phase 3；发布 Milestone 3 | 9 | 0/9 | 文档模型、草稿和锁可在全部章节闭环之前开发；来源与助手按数据依赖接入。 |
| [FE-M4 检查导出](tasks/FE-M4.md) | ROADMAP Phase 4；发布 Milestone 4 | 6 | 0/6 | 检查中心可与生成结果及编辑器联调并行；真实导出等待有效检查与权限。 |
| [FE-M5 资料写作管理](tasks/FE-M5.md) | ROADMAP Phase 5～6；发布 Milestone 5；参考 PRD 通用与运维页面补差异 | 11 | 0/11 | 资料库在基础客户端/Shell 到位后可与 FE-M1 并行；管理模块按具体接口拆开。 |
| [FE-M6 协作](tasks/FE-M6.md) | ROADMAP Phase 7；一期可延后范围 | 4 | 0/4 | 后续范围确认后按负责人、评论、引用等具体依赖推进，彼此无需整阶段串行。 |
| [FE-M7 效率](tasks/FE-M7.md) | ROADMAP Phase 8；一期可延后范围 | 4 | 0/4 | 可选效率增强按相关模块依赖推进，不是一期发布前置。 |
| [FE-M8 发布门禁](tasks/FE-M8.md) | ROADMAP §11 MVP Cut Line、§13 Gate A/B/C；贯穿发布 Milestone 1～5 | 3 | 0/3 | 发布验证覆盖一期必需任务；无需等待可选 FE-M6/FE-M7。 |
| [OPS-M0 工作区运维](tasks/OPS-M0.md) | ISSUE-004工作区同步；独立于业务MVP | 1 | 1/1 | 真实双向同步与持续运行验收完成。 |
| [REV-M0 接手审查](tasks/REV-M0.md) | ISSUE-004目录与业务/技术审查 | 1 | 1/1 | 审查/brief交付完成，设计决定留ISSUE-005。 |
| [BE-M0 后端链路](tasks/BE-M0.md) | ISSUE-006本地后端demo | 1 | 1/1 | 核心后台流程已本地验收，模型/数据库保留接口。 |
| [APP-M1 示例实现](tasks/APP-M1.md) | ISSUE-007示例与后台联调 | 11 | 3/11 | T09～11数值服务承诺已本地验收；核心完整卡与其他页面继续推进。 |

发布 Milestone 1～5 分别映射 FE-M1～FE-M5；FE-M0 为共用基础，FE-M6/FE-M7 为原 Phase 7/8 的可选增强，FE-M8 为贯穿原 Gate A/B/C 的发布验收。

依赖按**任务**记录：只等待表中所列任务及其真实接口，不要求先完成上一整个里程碑。MVP Cut Line 以已评审范围为准；推迟任务需在 Issue、路线图和交付中保留原因，不能将未实现卡改为 done。

## 总看板

<!-- task-board:start -->
| 任务ID | 任务 | 状态 | 依赖 | 关联Issue | 交付文档 |
|---|---|---|---|---|---|
| [FE-M0-T01](tasks/FE-M0.md#fe-m0-t01) | 仓库整理与原型编辑锁修复 | done | — | [ISSUE-002](../issues/ISSUE-002.md) | [交付](delivery/FE-M0-T01.md) |
| [FE-M0-T02](tasks/FE-M0.md#fe-m0-t02) | 任务治理与交付闭环 | done | [FE-M0-T01](tasks/FE-M0.md#fe-m0-t01) | [ISSUE-003](../issues/ISSUE-003.md) | [交付](delivery/FE-M0-T02.md) |
| [FE-M0-T03](tasks/FE-M0.md#fe-m0-t03) | 评审系统与前端来源边界 | in-progress | [FE-M0-T02](tasks/FE-M0.md#fe-m0-t02) | [ISSUE-005](../issues/ISSUE-005.md) | `docs/delivery/FE-M0-T03.md` |
| [FE-M0-T04](tasks/FE-M0.md#fe-m0-t04) | 确认选型与首批接口边界 | blocked | [FE-M0-T03](tasks/FE-M0.md#fe-m0-t03) | [ISSUE-005](../issues/ISSUE-005.md) | `docs/delivery/FE-M0-T04.md` |
| [FE-M0-T05](tasks/FE-M0.md#fe-m0-t05) | 建立正式前端最小运行工程 | blocked | [FE-M0-T04](tasks/FE-M0.md#fe-m0-t04) | — | `docs/delivery/FE-M0-T05.md` |
| [FE-M0-T06](tasks/FE-M0.md#fe-m0-t06) | 登录与权限导航最小接入 | blocked | [FE-M0-T05](tasks/FE-M0.md#fe-m0-t05)、[FE-M0-T04](tasks/FE-M0.md#fe-m0-t04) | — | `docs/delivery/FE-M0-T06.md` |
| [FE-M0-T07](tasks/FE-M0.md#fe-m0-t07) | 全局与项目 Shell 及路由 | blocked | [FE-M0-T05](tasks/FE-M0.md#fe-m0-t05)、[FE-M0-T06](tasks/FE-M0.md#fe-m0-t06) | — | `docs/delivery/FE-M0-T07.md` |
| [FE-M0-T08](tasks/FE-M0.md#fe-m0-t08) | API 客户端与错误审计通路 | blocked | [FE-M0-T04](tasks/FE-M0.md#fe-m0-t04)、[FE-M0-T05](tasks/FE-M0.md#fe-m0-t05) | — | `docs/delivery/FE-M0-T08.md` |
| [FE-M0-T09](tasks/FE-M0.md#fe-m0-t09) | 基础组件与离线资源 | blocked | [FE-M0-T05](tasks/FE-M0.md#fe-m0-t05)、[FE-M0-T07](tasks/FE-M0.md#fe-m0-t07) | — | `docs/delivery/FE-M0-T09.md` |
| [FE-M0-T10](tasks/FE-M0.md#fe-m0-t10) | 统一长任务状态组件 | blocked | [FE-M0-T08](tasks/FE-M0.md#fe-m0-t08)、[FE-M0-T09](tasks/FE-M0.md#fe-m0-t09) | — | `docs/delivery/FE-M0-T10.md` |
| [FE-M1-T01](tasks/FE-M1.md#fe-m1-t01) | 项目列表与创建入口 | blocked | [FE-M0-T07](tasks/FE-M0.md#fe-m0-t07)、[FE-M0-T08](tasks/FE-M0.md#fe-m0-t08)、[FE-M0-T09](tasks/FE-M0.md#fe-m0-t09) | — | `docs/delivery/FE-M1-T01.md` |
| [FE-M1-T02](tasks/FE-M1.md#fe-m1-t02) | 项目概览与分册风险 | blocked | [FE-M1-T01](tasks/FE-M1.md#fe-m1-t01)、[FE-M0-T10](tasks/FE-M0.md#fe-m0-t10) | — | `docs/delivery/FE-M1-T02.md` |
| [FE-M1-T03](tasks/FE-M1.md#fe-m1-t03) | 招标文件上传与解析任务 | blocked | [FE-M1-T01](tasks/FE-M1.md#fe-m1-t01)、[FE-M0-T08](tasks/FE-M0.md#fe-m0-t08)、[FE-M0-T10](tasks/FE-M0.md#fe-m0-t10) | — | `docs/delivery/FE-M1-T03.md` |
| [FE-M1-T04](tasks/FE-M1.md#fe-m1-t04) | 原文查看与页码定位 | blocked | [FE-M1-T03](tasks/FE-M1.md#fe-m1-t03) | — | `docs/delivery/FE-M1-T04.md` |
| [FE-M1-T05](tasks/FE-M1.md#fe-m1-t05) | 解析后处理与确认门 | blocked | [FE-M1-T03](tasks/FE-M1.md#fe-m1-t03)、[FE-M1-T04](tasks/FE-M1.md#fe-m1-t04)、[FE-M0-T04](tasks/FE-M0.md#fe-m0-t04) | — | `docs/delivery/FE-M1-T05.md` |
| [FE-M1-T06](tasks/FE-M1.md#fe-m1-t06) | 响应矩阵最小编辑与证据 | blocked | [FE-M1-T05](tasks/FE-M1.md#fe-m1-t05)、[FE-M0-T08](tasks/FE-M0.md#fe-m0-t08)、[FE-M5-T01](tasks/FE-M5.md#fe-m5-t01) | — | `docs/delivery/FE-M1-T06.md` |
| [FE-M1-T07](tasks/FE-M1.md#fe-m1-t07) | 项目事实编辑与确认 | blocked | [FE-M1-T01](tasks/FE-M1.md#fe-m1-t01)、[FE-M1-T05](tasks/FE-M1.md#fe-m1-t05)、[FE-M0-T08](tasks/FE-M0.md#fe-m0-t08) | — | `docs/delivery/FE-M1-T07.md` |
| [FE-M2-T01](tasks/FE-M2.md#fe-m2-t01) | 章节树与状态导航 | blocked | [FE-M1-T06](tasks/FE-M1.md#fe-m1-t06)、[FE-M0-T07](tasks/FE-M0.md#fe-m0-t07) | — | `docs/delivery/FE-M2-T01.md` |
| [FE-M2-T02](tasks/FE-M2.md#fe-m2-t02) | 写作方案查看确认与启动 | blocked | [FE-M2-T01](tasks/FE-M2.md#fe-m2-t01)、[FE-M1-T07](tasks/FE-M1.md#fe-m1-t07)、[FE-M0-T04](tasks/FE-M0.md#fe-m0-t04) | — | `docs/delivery/FE-M2-T02.md` |
| [FE-M2-T03](tasks/FE-M2.md#fe-m2-t03) | 生成轮次与长任务 Timeline | blocked | [FE-M2-T02](tasks/FE-M2.md#fe-m2-t02)、[FE-M0-T10](tasks/FE-M0.md#fe-m0-t10) | — | `docs/delivery/FE-M2-T03.md` |
| [FE-M2-T04](tasks/FE-M2.md#fe-m2-t04) | 检查与定位修正结果 | blocked | [FE-M2-T03](tasks/FE-M2.md#fe-m2-t03)、[FE-M1-T04](tasks/FE-M1.md#fe-m1-t04) | — | `docs/delivery/FE-M2-T04.md` |
| [FE-M2-T05](tasks/FE-M2.md#fe-m2-t05) | 停止条件与人工处理交接 | blocked | [FE-M2-T04](tasks/FE-M2.md#fe-m2-t04)、[FE-M0-T10](tasks/FE-M0.md#fe-m0-t10) | — | `docs/delivery/FE-M2-T05.md` |
| [FE-M3-T01](tasks/FE-M3.md#fe-m3-t01) | 编辑文档模型与段落元数据 | blocked | [FE-M0-T04](tasks/FE-M0.md#fe-m0-t04)、[FE-M0-T05](tasks/FE-M0.md#fe-m0-t05)、[FE-M0-T08](tasks/FE-M0.md#fe-m0-t08) | — | `docs/delivery/FE-M3-T01.md` |
| [FE-M3-T02](tasks/FE-M3.md#fe-m3-t02) | 长文基础编辑与只读保护 | blocked | [FE-M3-T01](tasks/FE-M3.md#fe-m3-t01)、[FE-M0-T09](tasks/FE-M0.md#fe-m0-t09) | — | `docs/delivery/FE-M3-T02.md` |
| [FE-M3-T03](tasks/FE-M3.md#fe-m3-t03) | 草稿自动保存与并发冲突 | blocked | [FE-M3-T01](tasks/FE-M3.md#fe-m3-t01)、[FE-M0-T08](tasks/FE-M0.md#fe-m0-t08) | — | `docs/delivery/FE-M3-T03.md` |
| [FE-M3-T04](tasks/FE-M3.md#fe-m3-t04) | 真实编辑锁与心跳接管 | blocked | [FE-M3-T01](tasks/FE-M3.md#fe-m3-t01)、[FE-M0-T06](tasks/FE-M0.md#fe-m0-t06)、[FE-M0-T08](tasks/FE-M0.md#fe-m0-t08) | — | `docs/delivery/FE-M3-T04.md` |
| [FE-M3-T05](tasks/FE-M3.md#fe-m3-t05) | 段落来源与问题抽屉 | blocked | [FE-M3-T01](tasks/FE-M3.md#fe-m3-t01)、[FE-M1-T04](tasks/FE-M1.md#fe-m1-t04)、[FE-M1-T07](tasks/FE-M1.md#fe-m1-t07) | — | `docs/delivery/FE-M3-T05.md` |
| [FE-M3-T06](tasks/FE-M3.md#fe-m3-t06) | 普通问答与结构化答案卡 | blocked | [FE-M0-T08](tasks/FE-M0.md#fe-m0-t08)、[FE-M1-T07](tasks/FE-M1.md#fe-m1-t07)、[FE-M5-T01](tasks/FE-M5.md#fe-m5-t01) | — | `docs/delivery/FE-M3-T06.md` |
| [FE-M3-T07](tasks/FE-M3.md#fe-m3-t07) | 选区样例与上下文快照 | blocked | [FE-M3-T01](tasks/FE-M3.md#fe-m3-t01)、[FE-M3-T04](tasks/FE-M3.md#fe-m3-t04)、[FE-M3-T06](tasks/FE-M3.md#fe-m3-t06) | — | `docs/delivery/FE-M3-T07.md` |
| [FE-M3-T08](tasks/FE-M3.md#fe-m3-t08) | Diff 确认与安全写入 | blocked | [FE-M3-T07](tasks/FE-M3.md#fe-m3-t07)、[FE-M3-T03](tasks/FE-M3.md#fe-m3-t03)、[FE-M3-T04](tasks/FE-M3.md#fe-m3-t04) | — | `docs/delivery/FE-M3-T08.md` |
| [FE-M3-T09](tasks/FE-M3.md#fe-m3-t09) | 版本比较与回退 | blocked | [FE-M3-T03](tasks/FE-M3.md#fe-m3-t03)、[FE-M3-T04](tasks/FE-M3.md#fe-m3-t04)、[FE-M3-T08](tasks/FE-M3.md#fe-m3-t08) | — | `docs/delivery/FE-M3-T09.md` |
| [FE-M4-T01](tasks/FE-M4.md#fe-m4-t01) | 检查中心筛选与问题定位 | blocked | [FE-M0-T10](tasks/FE-M0.md#fe-m0-t10)、[FE-M3-T05](tasks/FE-M3.md#fe-m3-t05) | — | `docs/delivery/FE-M4-T01.md` |
| [FE-M4-T02](tasks/FE-M4.md#fe-m4-t02) | 编辑后增量复查反馈 | blocked | [FE-M3-T08](tasks/FE-M3.md#fe-m3-t08)、[FE-M4-T01](tasks/FE-M4.md#fe-m4-t01) | — | `docs/delivery/FE-M4-T02.md` |
| [FE-M4-T03](tasks/FE-M4.md#fe-m4-t03) | 分册检查定稿与解锁 | blocked | [FE-M4-T01](tasks/FE-M4.md#fe-m4-t01)、[FE-M2-T05](tasks/FE-M2.md#fe-m2-t05)、[FE-M3-T09](tasks/FE-M3.md#fe-m3-t09) | — | `docs/delivery/FE-M4-T03.md` |
| [FE-M4-T04](tasks/FE-M4.md#fe-m4-t04) | 全文检查与跨分册门禁 | blocked | [FE-M4-T03](tasks/FE-M4.md#fe-m4-t03)、[FE-M1-T06](tasks/FE-M1.md#fe-m1-t06) | — | `docs/delivery/FE-M4-T04.md` |
| [FE-M4-T05](tasks/FE-M4.md#fe-m4-t05) | 内部稿与递交版导出入口 | blocked | [FE-M4-T04](tasks/FE-M4.md#fe-m4-t04)、[FE-M0-T06](tasks/FE-M0.md#fe-m0-t06)、[FE-M0-T10](tasks/FE-M0.md#fe-m0-t10) | — | `docs/delivery/FE-M4-T05.md` |
| [FE-M4-T06](tasks/FE-M4.md#fe-m4-t06) | 导出历史下载与版式核对 | blocked | [FE-M4-T05](tasks/FE-M4.md#fe-m4-t05) | — | `docs/delivery/FE-M4-T06.md` |
| [FE-M5-T01](tasks/FE-M5.md#fe-m5-t01) | 资料库列表与治理状态 | blocked | [FE-M0-T07](tasks/FE-M0.md#fe-m0-t07)、[FE-M0-T08](tasks/FE-M0.md#fe-m0-t08)、[FE-M0-T09](tasks/FE-M0.md#fe-m0-t09) | — | `docs/delivery/FE-M5-T01.md` |
| [FE-M5-T02](tasks/FE-M5.md#fe-m5-t02) | 主体资质与附件表单切片 | blocked | [FE-M5-T01](tasks/FE-M5.md#fe-m5-t01) | — | `docs/delivery/FE-M5-T02.md` |
| [FE-M5-T03](tasks/FE-M5.md#fe-m5-t03) | 人员证书与授权关联 | blocked | [FE-M5-T01](tasks/FE-M5.md#fe-m5-t01)、[FE-M5-T02](tasks/FE-M5.md#fe-m5-t02) | — | `docs/delivery/FE-M5-T03.md` |
| [FE-M5-T04](tasks/FE-M5.md#fe-m5-t04) | 业绩与能力资料首批视图 | blocked | [FE-M5-T01](tasks/FE-M5.md#fe-m5-t01)、[FE-M5-T02](tasks/FE-M5.md#fe-m5-t02) | — | `docs/delivery/FE-M5-T04.md` |
| [FE-M5-T05](tasks/FE-M5.md#fe-m5-t05) | 方案片段与历史参考管理 | blocked | [FE-M5-T01](tasks/FE-M5.md#fe-m5-t01)、[FE-M1-T04](tasks/FE-M1.md#fe-m1-t04) | — | `docs/delivery/FE-M5-T05.md` |
| [FE-M5-T06](tasks/FE-M5.md#fe-m5-t06) | 公司写作档案与模板风格 | blocked | [FE-M5-T01](tasks/FE-M5.md#fe-m5-t01)、[FE-M0-T08](tasks/FE-M0.md#fe-m0-t08) | — | `docs/delivery/FE-M5-T06.md` |
| [FE-M5-T07](tasks/FE-M5.md#fe-m5-t07) | 任务卡版本与模型参数管理 | blocked | [FE-M5-T06](tasks/FE-M5.md#fe-m5-t06)、[FE-M0-T04](tasks/FE-M0.md#fe-m0-t04) | — | `docs/delivery/FE-M5-T07.md` |
| [FE-M5-T08](tasks/FE-M5.md#fe-m5-t08) | 用户角色与公司设置 | blocked | [FE-M0-T06](tasks/FE-M0.md#fe-m0-t06)、[FE-M5-T01](tasks/FE-M5.md#fe-m5-t01) | — | `docs/delivery/FE-M5-T08.md` |
| [FE-M5-T09](tasks/FE-M5.md#fe-m5-t09) | 站内提醒与一期全局搜索 | blocked | [FE-M0-T07](tasks/FE-M0.md#fe-m0-t07)、[FE-M0-T08](tasks/FE-M0.md#fe-m0-t08)、[FE-M1-T01](tasks/FE-M1.md#fe-m1-t01)、[FE-M5-T01](tasks/FE-M5.md#fe-m5-t01) | — | `docs/delivery/FE-M5-T09.md` |
| [FE-M5-T10](tasks/FE-M5.md#fe-m5-t10) | 规则配置与兜底扫描版本 | blocked | [FE-M0-T08](tasks/FE-M0.md#fe-m0-t08)、[FE-M5-T08](tasks/FE-M5.md#fe-m5-t08)、[FE-M1-T05](tasks/FE-M1.md#fe-m1-t05) | — | `docs/delivery/FE-M5-T10.md` |
| [FE-M5-T11](tasks/FE-M5.md#fe-m5-t11) | 服务状态品牌与任务中心入口 | blocked | [FE-M0-T10](tasks/FE-M0.md#fe-m0-t10)、[FE-M5-T08](tasks/FE-M5.md#fe-m5-t08)、[FE-M0-T09](tasks/FE-M0.md#fe-m0-t09) | — | `docs/delivery/FE-M5-T11.md` |
| [FE-M6-T01](tasks/FE-M6.md#fe-m6-t01) | 章节负责人分派与待办 | planned | [FE-M2-T01](tasks/FE-M2.md#fe-m2-t01)、[FE-M5-T08](tasks/FE-M5.md#fe-m5-t08) | — | `docs/delivery/FE-M6-T01.md` |
| [FE-M6-T02](tasks/FE-M6.md#fe-m6-t02) | 评论批注与提及解决 | planned | [FE-M3-T01](tasks/FE-M3.md#fe-m3-t01)、[FE-M3-T05](tasks/FE-M3.md#fe-m3-t05)、[FE-M5-T09](tasks/FE-M5.md#fe-m5-t09) | — | `docs/delivery/FE-M6-T02.md` |
| [FE-M6-T03](tasks/FE-M6.md#fe-m6-t03) | 知识引用地图 | planned | [FE-M3-T05](tasks/FE-M3.md#fe-m3-t05)、[FE-M5-T05](tasks/FE-M5.md#fe-m5-t05) | — | `docs/delivery/FE-M6-T03.md` |
| [FE-M6-T04](tasks/FE-M6.md#fe-m6-t04) | 项目模板复制 | planned | [FE-M1-T01](tasks/FE-M1.md#fe-m1-t01)、[FE-M1-T06](tasks/FE-M1.md#fe-m1-t06)、[FE-M5-T06](tasks/FE-M5.md#fe-m5-t06) | — | `docs/delivery/FE-M6-T04.md` |
| [FE-M7-T01](tasks/FE-M7.md#fe-m7-t01) | 快捷命令与跳转 | planned | [FE-M0-T07](tasks/FE-M0.md#fe-m0-t07)、[FE-M5-T09](tasks/FE-M5.md#fe-m5-t09) | — | `docs/delivery/FE-M7-T01.md` |
| [FE-M7-T02](tasks/FE-M7.md#fe-m7-t02) | 能力与写作质量指标视图 | planned | [FE-M5-T04](tasks/FE-M5.md#fe-m5-t04)、[FE-M5-T06](tasks/FE-M5.md#fe-m5-t06)、[FE-M2-T03](tasks/FE-M2.md#fe-m2-t03) | — | `docs/delivery/FE-M7-T02.md` |
| [FE-M7-T03](tasks/FE-M7.md#fe-m7-t03) | 历史复用推荐预览 | planned | [FE-M5-T05](tasks/FE-M5.md#fe-m5-t05)、[FE-M3-T07](tasks/FE-M3.md#fe-m3-t07)、[FE-M3-T08](tasks/FE-M3.md#fe-m3-t08) | — | `docs/delivery/FE-M7-T03.md` |
| [FE-M7-T04](tasks/FE-M7.md#fe-m7-t04) | 高频批量操作 | planned | [FE-M1-T06](tasks/FE-M1.md#fe-m1-t06)、[FE-M2-T02](tasks/FE-M2.md#fe-m2-t02)、[FE-M0-T10](tasks/FE-M0.md#fe-m0-t10) | — | `docs/delivery/FE-M7-T04.md` |
| [FE-M8-T01](tasks/FE-M8.md#fe-m8-t01) | 一期完整主链路联调 | blocked | [FE-M1-T07](tasks/FE-M1.md#fe-m1-t07)、[FE-M2-T05](tasks/FE-M2.md#fe-m2-t05)、[FE-M3-T09](tasks/FE-M3.md#fe-m3-t09)、[FE-M4-T06](tasks/FE-M4.md#fe-m4-t06)、[FE-M5-T07](tasks/FE-M5.md#fe-m5-t07)、[FE-M5-T08](tasks/FE-M5.md#fe-m5-t08)、[FE-M5-T09](tasks/FE-M5.md#fe-m5-t09)、[FE-M5-T10](tasks/FE-M5.md#fe-m5-t10)、[FE-M5-T11](tasks/FE-M5.md#fe-m5-t11) | — | `docs/delivery/FE-M8-T01.md` |
| [FE-M8-T02](tasks/FE-M8.md#fe-m8-t02) | 安全离线长文与恢复验证 | blocked | [FE-M0-T09](tasks/FE-M0.md#fe-m0-t09)、[FE-M3-T02](tasks/FE-M3.md#fe-m3-t02)、[FE-M3-T03](tasks/FE-M3.md#fe-m3-t03)、[FE-M3-T04](tasks/FE-M3.md#fe-m3-t04)、[FE-M4-T05](tasks/FE-M4.md#fe-m4-t05)、[FE-M8-T01](tasks/FE-M8.md#fe-m8-t01) | — | `docs/delivery/FE-M8-T02.md` |
| [FE-M8-T03](tasks/FE-M8.md#fe-m8-t03) | 版本发布与交付资料封版 | blocked | [FE-M8-T01](tasks/FE-M8.md#fe-m8-t01)、[FE-M8-T02](tasks/FE-M8.md#fe-m8-t02)、[FE-M0-T02](tasks/FE-M0.md#fe-m0-t02) | — | `docs/delivery/FE-M8-T03.md` |
| [OPS-M0-T01](tasks/OPS-M0.md#ops-m0-t01) | 全工作区云端同步 | done | [FE-M0-T02](tasks/FE-M0.md#fe-m0-t02) | [ISSUE-004](../issues/ISSUE-004.md) | [交付](delivery/OPS-M0-T01.md) |
| [REV-M0-T01](tasks/REV-M0.md#rev-m0-t01) | 目录、业务与技术审查及brief | done | [FE-M0-T02](tasks/FE-M0.md#fe-m0-t02) | [ISSUE-004](../issues/ISSUE-004.md) | [交付](delivery/REV-M0-T01.md) |
| [BE-M0-T01](tasks/BE-M0.md#be-m0-t01) | 后端开发准备与本地demo | done | [FE-M0-T02](tasks/FE-M0.md#fe-m0-t02) | [ISSUE-006](../issues/ISSUE-006.md) | [交付](delivery/BE-M0-T01.md) |
| [APP-M1-T01](tasks/APP-M1.md#app-m1-t01) | 示例外壳与项目工作台 | in-progress | BE-M0-T01 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T01.md` |
| [APP-M1-T02](tasks/APP-M1.md#app-m1-t02) | 上传解析与确认 | in-progress | APP-M1-T01工作区接口 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T02.md` |
| [APP-M1-T03](tasks/APP-M1.md#app-m1-t03) | 矩阵事实与证据 | in-progress | APP-M1-T02条款结构 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T03.md` |
| [APP-M1-T04](tasks/APP-M1.md#app-m1-t04) | 大纲章节与示例编辑台 | in-progress | APP-M1-T03映射接口 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T04.md` |
| [APP-M1-T05](tasks/APP-M1.md#app-m1-t05) | 检查与两册输出 | in-progress | APP-M1-T03/04数据结构 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T05.md` |
| [APP-M1-T06](tasks/APP-M1.md#app-m1-t06) | 核心流程端到端验收 | in-progress | APP-M1-T01～05 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T06.md` |
| [APP-M1-T07](tasks/APP-M1.md#app-m1-t07) | 其他页面和完整规则拆分 | planned | 核心结构验证 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T07.md` |
| [APP-M1-T08](tasks/APP-M1.md#app-m1-t08) | 完整示例交付审计 | planned | 核心与后续任务完成 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T08.md` |
| [APP-M1-T09](tasks/APP-M1.md#app-m1-t09) | 服务承诺模板与公司能力 | done | 公司资料接口已接通 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M1-T09.md) |
| [APP-M1-T10](tasks/APP-M1.md#app-m1-t10) | 三方对照、判断与事实引用 | done | T09模板、T03原文要求 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M1-T10.md) |
| [APP-M1-T11](tasks/APP-M1.md#app-m1-t11) | 承诺变量、检查与承诺函 | done | T10取值、T04/05正文输出 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M1-T11.md) |
<!-- task-board:end -->

## 每次推进的同步顺序

1. 读取关联 Issue、任务卡、项目状态与当前版本；确认范围变化是否需要新需求/版本 Issue。
2. 确认任务依赖、API 和基线后转 ready，开工转 in-progress；阻塞时写具体原因和所需输入。
3. 完成实际变更与必要验证，先写 `docs/delivery/<TASK_ID>.md` 的结果、证据和限制；有代码修改时创建并链接 `docs/code/<TASK_ID>.md`，再转 in-review 等待验收。
4. 同步 PRD/ROADMAP/ARCHITECTURE 的受影响章节，或在交付中逐项记录无需修改的核对依据。
5. 更新 Issue、任务卡和本看板状态、PROJECT_STATUS 进度，最后登记 DOCUMENT_INDEX；检查链接/状态一致后转 done。
6. 把本地验收、合入、发布分别记录；功能只有真实接口联调通过才计生产完成。

当前优先：APP-M1按ICG示例实施和联调，来源差异同步核对；模型/数据库保留接口不阻止本地产品流程开发。生产门禁继续验证，不能用主链路内部稿替代完整交付。
