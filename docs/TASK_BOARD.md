为什么有这个文件：集中显示每个任务的状态、依赖和交付入口。

它解决什么问题：帮助判断现在能做什么、卡在哪里、完成后有什么证据。

# 项目任务看板

任务版本：0.6；治理版本：g1.1；更新日期：2026-10-12；当前实现 Issue：[ISSUE-007](../issues/ISSUE-007.md)；离线检查：[ISSUE-012](../issues/ISSUE-012.md)；生产门禁：[ISSUE-005](../issues/ISSUE-005.md)；模型决定：[ISSUE-010](../issues/ISSUE-010.md)（closed）。

将 [前端 ROADMAP](ROADMAP.md) 的 Phase 0～8 与发布 Milestone 1～5 拆为 **59 张任务卡**，由 FE-M0～FE-M8 管理。前缀 FE 表示前端合作交付；这些编号与参考全系统 M0～M8 的门禁、周期和范围独立。

项目366项中 **done 32、in-review 8、in-progress 7、planned 266、blocked 49、ready 4**。APP-M1的16项中，T01～05继续实现，T06继续完整联调验收，T07已完成范围拆分，T08等待最终审计；T09～16限定子任务已本地验收，T16完成资料及公司模板旧表单保护。APP-M2的259卡中T001布局、路由和离开保护为 done，T002请求层为 done。项目经理在群里确认 QA 签署后标为 done，T008离线CI为 done，T078 内存发布为 in-review，T124因 T078 未 done 且 T114 仍 planned 而仍为 blocked，其 OpenAPI 草案随 ISSUE-022 待复核，其余254卡planned，47组页面、190原WBS细项及44规则已逐项映射，见[完整后续卡](tasks/APP-M2.md)与[来源核对](testing/icg-task-mapping.md)。BE-M0现为15项：T01已验收；T02与T03由项目经理于 10-12 12:28 在 QA 签署后确认，标为 done；MySQL 8 方案与连接空迁移由项目经理在 QA 签署 98c5129 后确认，标为 done；锁迁移、导出快照、202/SSE、operationId四张卡 ready；旧接口错误体、租约入库、按聚合迁移为 planned。T11 回执与会话为 in-review。T14 托管 MySQL 作业已依据 QA 签署 b20b844 标为 done。Word 默认版式 BE-M0-T15 为 in-review。旧接口含 E2E-D5 的大小写 `/api` 前缀。ISSUE-005 保持 in-progress，T04～T07 未完成，不关闭。旧FE59项保留来源，OPS 2项中 T01 已本地验收、T02 内网部署草案为 in-review，REV 8项中 6 项已本地验收、T06 与 T08 为 in-review（REV-M0-T02为ISSUE-013 QA复跑，REV-M0-T03/T04为ISSUE-015，REV-M0-T05为T008与AI-02的QA签署，REV-M0-T07为T02/T03的QA签署）。AI-01改为 in-review：对话模型由配置页提供，嵌入与向量库用 RAGFlow 自带，生产生成仅内网；真实端点另计验收。业务库已定为 MySQL 8，方案与连接空迁移已由项目经理在 QA 签署 98c5129 后确认 done，回执和登录会话由 T11 提交 in-review，租约和聚合表未接入；AI-02 与 T008 均已由项目经理于 10-12 12:10 在 QA 签署后确认，标为 done。AI-03 为 in-review，只使用内存检索。开发者只能把卡片标到 in-review，done 由项目经理在 QA 签署后设置。ISSUE-009 与 ISSUE-014 仍为 in-review。T001 与 T002 已由项目经理在群里确认、QA 签署后标为 done。QA 于 2026-10-12 签署 T001 本切片不通过；浅色内容、顶栏和前进/后退修复后，REV-M0-T11 签署通过。ISSUE-020 路由分包为 in-review。ISSUE-018 已批准并改为 in-progress：方案与连接空迁移已 done，T11 回执与会话为 in-review，T12 与 T13 仍 planned。ISSUE-023 已由项目经理在 QA 签署 16cf971 后确认，状态为 closed。ISSUE-021 排队且任务为 planned，ISSUE-022 的契约草案待复核，T124 仍为 blocked。PR #3待合入。ISSUE-026 仍为 in-review。PRD、ROADMAP 与 PROJECT_BRIEF 的任务计数是里程碑快照 as of commit 3bb311ad3ab86c0de2f871876a50c7d50f9bb985，并计入本提交将 T001 与 T002 标为 done：366 项、32 done、6 in-review、7 in-progress、268 planned、49 blocked、4 ready。任务看板是准绳，三份基线只在里程碑更新。这些数量不是产品完成率。

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
| [OPS-M0 工作区运维](tasks/OPS-M0.md) | ISSUE-004工作区同步；ISSUE-017内网部署草案 | 2 | 1/2 | T01同步已验收。T02只是草案，in-review，未部署。多副本仍 blocked 在 ISSUE-018。 |
| [REV-M0 接手审查](tasks/REV-M0.md) | ISSUE-004目录与业务/技术审查；ISSUE-013 QA复跑；ISSUE-015 T06计划；ISSUE-013 签署；ISSUE-019 E2E、T001签署 | 8 | 6/8 | 审查/brief交付完成，设计决定留ISSUE-005；QA复跑、T06计划及贯通冒烟/Word渲染完成。T06 与 T08 为 in-review。 |
| [BE-M0 后端链路](tasks/BE-M0.md) | ISSUE-006本地后端demo；ISSUE-005契约卡；ISSUE-018实施中；ISSUE-023已关闭；ISSUE-025托管MySQL作业；ISSUE-027版式；ISSUE-021排队 | 15 | 6/15 | T01～T03已验收。T02与T03由项目经理于 10-12 12:28 在 QA 签署后确认。T08与T10由项目经理在 QA 签署 98c5129 后确认，标为 done；T04～T07 ready；T09、T12、T13 planned。T11 回执与会话为 in-review。T14 已依据 QA 签署 b20b844 标为 done。T15 Word 默认版式为 in-review。ISSUE-005 仍 in-progress。ISSUE-023 已 closed。 |
| [APP-M1 示例实现](tasks/APP-M1.md) | ISSUE-007示例与后台联调；ISSUE-008资料保护 | 16 | 9/16 | T07及T09～16已本地验收；完整父任务继续。 |
| [AI-M0 模型接入准备](tasks/AI-M0.md) | ISSUE-010已关闭；ISSUE-011兼容适配器；ISSUE-016内存检索 | 3 | 1/3 | AI-01为in-review；AI-02为done，项目经理于 10-12 12:10 在 QA 签署后确认；AI-03为in-review。对话模型、RAGFlow 与内网范围已登记，真实端点未验收。 |

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
| [OPS-M0-T02](tasks/OPS-M0.md#ops-m0-t02) | 内网部署草案 | in-review | [BE-M0-T01](tasks/BE-M0.md#be-m0-t01) | [ISSUE-017](../issues/ISSUE-017.md) | [交付](delivery/OPS-M0-T02.md) |
| [REV-M0-T01](tasks/REV-M0.md#rev-m0-t01) | 目录、业务与技术审查及brief | done | [FE-M0-T02](tasks/FE-M0.md#fe-m0-t02) | [ISSUE-004](../issues/ISSUE-004.md) | [交付](delivery/REV-M0-T01.md) |
| [REV-M0-T02](tasks/REV-M0.md#rev-m0-t02) | QA独立复跑与会话真实HTTP复核入库 | done | [APP-M2-T001](tasks/APP-M2.md#app-m2-t001) | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T02.md) |
| [REV-M0-T03](tasks/REV-M0.md#rev-m0-t03) | APP-M1-T06端到端验收计划 | done | [APP-M1-T06](tasks/APP-M1.md#app-m1-t06) | [ISSUE-015](../issues/ISSUE-015.md) | [交付](delivery/REV-M0-T03.md) |
| [REV-M0-T04](tasks/REV-M0.md#rev-m0-t04) | T06贯通冒烟与Word渲染 | done | [REV-M0-T03](tasks/REV-M0.md#rev-m0-t03) | [ISSUE-015](../issues/ISSUE-015.md) | [交付](delivery/REV-M0-T04.md) |
| [REV-M0-T05](tasks/REV-M0.md#rev-m0-t05) | APP-M2-T008与AI-02 QA签署复核 | done | APP-M2-T008、AI-02 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T05.md) |
| [REV-M0-T07](tasks/REV-M0.md#rev-m0-t07) | BE-M0-T02与BE-M0-T03 QA签署复核 | done | BE-M0-T02、BE-M0-T03 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T07.md) |
| [REV-M0-T09](tasks/REV-M0.md#rev-m0-t09) | BE-M0-T08与BE-M0-T10 QA签署复核 | done | BE-M0-T08、BE-M0-T10 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T09.md) |
| [REV-M0-T10](tasks/REV-M0.md#rev-m0-t10) | BE-M0-T15 Word 默认版式 QA 签署复核 | done | BE-M0-T15 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T10.md) |
| [REV-M0-T11](tasks/REV-M0.md#rev-m0-t11) | APP-M2-T001与APP-M2-T002 QA复验签署 | done | APP-M2-T001、APP-M2-T002 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T11.md) |
| [REV-M0-T12](tasks/REV-M0.md#rev-m0-t12) | BE-M0-T14 托管 MySQL CI QA签署 | done | BE-M0-T14 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T12.md) |
| [REV-M0-T06](tasks/REV-M0.md#rev-m0-t06) | Playwright浏览器端到端检查 | in-review | [APP-M2-T001](tasks/APP-M2.md#app-m2-t001) | [ISSUE-019](../issues/ISSUE-019.md) | [交付](delivery/REV-M0-T06.md) |
| [REV-M0-T08](tasks/REV-M0.md#rev-m0-t08) | APP-M2-T001 QA签署复核 | in-review | [REV-M0-T06](tasks/REV-M0.md#rev-m0-t06) | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T08.md) |
| [BE-M0-T01](tasks/BE-M0.md#be-m0-t01) | 后端开发准备与本地demo | done | [FE-M0-T02](tasks/FE-M0.md#fe-m0-t02) | [ISSUE-006](../issues/ISSUE-006.md) | [交付](delivery/BE-M0-T01.md) |
| [BE-M0-T02](tasks/BE-M0.md#be-m0-t02) | v1统一错误体与HTTP状态码表 | done | [BE-M0-T01](tasks/BE-M0.md#be-m0-t01) | [ISSUE-005](../issues/ISSUE-005.md) | [交付](delivery/BE-M0-T02.md) |
| [BE-M0-T03](tasks/BE-M0.md#be-m0-t03) | v1幂等键与24小时回执 | done | [BE-M0-T02](tasks/BE-M0.md#be-m0-t02) | [ISSUE-005](../issues/ISSUE-005.md) | [交付](delivery/BE-M0-T03.md) |
| [BE-M0-T04](tasks/BE-M0.md#be-m0-t04) | 编辑租约迁到 /api/v1 | ready | [BE-M0-T02](tasks/BE-M0.md#be-m0-t02)、[BE-M0-T03](tasks/BE-M0.md#be-m0-t03) | [ISSUE-005](../issues/ISSUE-005.md) | `docs/delivery/BE-M0-T04.md` |
| [BE-M0-T05](tasks/BE-M0.md#be-m0-t05) | 导出快照语义 | ready | [BE-M0-T02](tasks/BE-M0.md#be-m0-t02)、[BE-M0-T03](tasks/BE-M0.md#be-m0-t03) | [ISSUE-005](../issues/ISSUE-005.md) | `docs/delivery/BE-M0-T05.md` |
| [BE-M0-T06](tasks/BE-M0.md#be-m0-t06) | 可恢复任务（202 与 SSE） | ready | [BE-M0-T02](tasks/BE-M0.md#be-m0-t02)、[BE-M0-T03](tasks/BE-M0.md#be-m0-t03) | [ISSUE-005](../issues/ISSUE-005.md) | `docs/delivery/BE-M0-T06.md` |
| [BE-M0-T07](tasks/BE-M0.md#be-m0-t07) | operationId 检查 | ready | [BE-M0-T02](tasks/BE-M0.md#be-m0-t02) | [ISSUE-005](../issues/ISSUE-005.md) | `docs/delivery/BE-M0-T07.md` |
| [BE-M0-T08](tasks/BE-M0.md#be-m0-t08) | MySQL 8 持久化方案 | done | [BE-M0-T01](tasks/BE-M0.md#be-m0-t01) | [ISSUE-018](../issues/ISSUE-018.md) | [交付](delivery/BE-M0-T08.md) |
| [BE-M0-T09](tasks/BE-M0.md#be-m0-t09) | 旧 /api 统一错误体与幂等 | planned | [BE-M0-T08](tasks/BE-M0.md#be-m0-t08) | [ISSUE-021](../issues/ISSUE-021.md) | `docs/delivery/BE-M0-T09.md` |
| [BE-M0-T10](tasks/BE-M0.md#be-m0-t10) | 连接配置与迁移骨架 | done | [BE-M0-T08](tasks/BE-M0.md#be-m0-t08) | [ISSUE-023](../issues/ISSUE-023.md) | [交付](delivery/BE-M0-T10.md) |
| [BE-M0-T11](tasks/BE-M0.md#be-m0-t11) | 幂等回执与登录会话入库 | in-review | [BE-M0-T10](tasks/BE-M0.md#be-m0-t10) | [ISSUE-018](../issues/ISSUE-018.md) | [交付](delivery/BE-M0-T11.md) |
| [BE-M0-T12](tasks/BE-M0.md#be-m0-t12) | 编辑租约入库 | planned | [BE-M0-T11](tasks/BE-M0.md#be-m0-t11) | [ISSUE-018](../issues/ISSUE-018.md) | `docs/delivery/BE-M0-T12.md` |
| [BE-M0-T13](tasks/BE-M0.md#be-m0-t13) | 按聚合迁移仓库 | planned | [BE-M0-T12](tasks/BE-M0.md#be-m0-t12) | [ISSUE-018](../issues/ISSUE-018.md) | `docs/delivery/BE-M0-T13.md` |
| [BE-M0-T14](tasks/BE-M0.md#be-m0-t14) | 托管 MySQL CI 作业 | done | [BE-M0-T10](tasks/BE-M0.md#be-m0-t10) | [ISSUE-025](../issues/ISSUE-025.md) | [交付](delivery/BE-M0-T14.md) |
| [BE-M0-T15](tasks/BE-M0.md#be-m0-t15) | Word 导出默认版式 | in-review | [BE-M0-T01](tasks/BE-M0.md#be-m0-t01) | [ISSUE-027](../issues/ISSUE-027.md) | [交付](delivery/BE-M0-T15.md) |
| [APP-M1-T01](tasks/APP-M1.md#app-m1-t01) | 示例外壳与项目工作台 | in-progress | BE-M0-T01 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T01.md` |
| [APP-M1-T02](tasks/APP-M1.md#app-m1-t02) | 上传解析与确认 | in-progress | APP-M1-T01工作区接口 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T02.md` |
| [APP-M1-T03](tasks/APP-M1.md#app-m1-t03) | 矩阵事实与证据 | in-progress | APP-M1-T02条款结构 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T03.md` |
| [APP-M1-T04](tasks/APP-M1.md#app-m1-t04) | 大纲章节与示例编辑台 | in-progress | APP-M1-T03映射接口 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T04.md` |
| [APP-M1-T05](tasks/APP-M1.md#app-m1-t05) | 检查与两册输出 | in-progress | APP-M1-T03/04数据结构 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T05.md` |
| [APP-M1-T06](tasks/APP-M1.md#app-m1-t06) | 核心流程端到端验收 | in-progress | APP-M1-T01～05 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T06.md` |
| [APP-M1-T07](tasks/APP-M1.md#app-m1-t07) | 其他页面和完整规则拆分 | done | 核心结构验证 | [ISSUE-007](../issues/ISSUE-007.md) | [本地交付](delivery/APP-M1-T07.md) |
| [APP-M1-T08](tasks/APP-M1.md#app-m1-t08) | 完整示例交付审计 | planned | 核心与后续任务完成 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T08.md` |
| [APP-M1-T09](tasks/APP-M1.md#app-m1-t09) | 服务承诺模板与公司能力 | done | 公司资料接口已接通 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M1-T09.md) |
| [APP-M1-T10](tasks/APP-M1.md#app-m1-t10) | 三方对照、判断与事实引用 | done | T09模板、T03原文要求 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M1-T10.md) |
| [APP-M1-T11](tasks/APP-M1.md#app-m1-t11) | 承诺变量、检查与承诺函 | done | T10取值、T04/05正文输出 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M1-T11.md) |
| [APP-M1-T12](tasks/APP-M1.md#app-m1-t12) | 本章事实写作输入与保护 | done | T03/10事实、T04方案接口 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M1-T12.md) |
| [APP-M1-T13](tasks/APP-M1.md#app-m1-t13) | 本章方案与候选来源预览 | done | T12共同字段、现有编辑台 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M1-T13.md) |
| [APP-M1-T14](tasks/APP-M1.md#app-m1-t14) | 项目成员与分册分工 | done | T01项目、T04章节、T12方案 | [ISSUE-007](../issues/ISSUE-007.md) | [本地交付](delivery/APP-M1-T14.md) |
| [APP-M1-T15](tasks/APP-M1.md#app-m1-t15) | 逐章分工与独立方案确认 | done | T14成员分册、T12输入 | [ISSUE-007](../issues/ISSUE-007.md) | [本地交付](delivery/APP-M1-T15.md) |
| [APP-M1-T16](tasks/APP-M1.md#app-m1-t16) | 资料库旧表单依据保护 | done | 已有公司资料版本接口；T14/15保护经验 | [ISSUE-008](../issues/ISSUE-008.md) | [交付](delivery/APP-M1-T16.md) |
| [APP-M2-T001](tasks/APP-M2.md#app-m2-t001) | ProLayout 布局、路由、权限守卫、请求层 | done | BE-M0-T01 | [ISSUE-009](../issues/ISSUE-009.md) | [交付](delivery/APP-M2-T001.md) |
| [APP-M2-T002](tasks/APP-M2.md#app-m2-t002) | 请求层细化：错误体、traceId 复制、Idempotency-Key 注入、重试策略 | done | BE-M0-T01、BE-M0-T02、BE-M0-T03、APP-M2-T001 | [ISSUE-009](../issues/ISSUE-009.md) | [交付](delivery/APP-M2-T002.md) |
| [APP-M2-T003](tasks/APP-M2.md#app-m2-t003) | 通用状态组件（骨架、空态、错误、无权限、已过期、只读） | planned | BE-M0-T01、APP-M2-T001 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T003.md` |
| [APP-M2-T004](tasks/APP-M2.md#app-m2-t004) | 业务小组件：LevelTag、AiTag、DirectTag、Cite、SourceBar | planned | BE-M0-T01、APP-M2-T003 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T004.md` |
| [APP-M2-T005](tasks/APP-M2.md#app-m2-t005) | 元数据驱动表格（ProTable 封装、列合并、无横滚优先） | planned | BE-M0-T01、APP-M2-T003 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T005.md` |
| [APP-M2-T006](tasks/APP-M2.md#app-m2-t006) | 元数据驱动表单（★ 字段、系统键两行标签、不支持字段置灰） | planned | BE-M0-T01、APP-M2-T003 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T006.md` |
| [APP-M2-T007](tasks/APP-M2.md#app-m2-t007) | 表单通用：底部保存条、离开未保存提示、就近报错 | planned | BE-M0-T01、APP-M2-T006 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T007.md` |
| [APP-M2-T008](tasks/APP-M2.md#app-m2-t008) | 主题运行时接口位与离线检查纳入 CI（应用级） | done | BE-M0-T01、APP-M2-T001 | [ISSUE-012](../issues/ISSUE-012.md) | [交付](delivery/APP-M2-T008.md) |
| [APP-M2-T009](tasks/APP-M2.md#app-m2-t009) | 断点与侧栏记忆（1280 / 1440 / 1680）、面包屑 | planned | BE-M0-T01、APP-M2-T001 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T009.md` |
| [APP-M2-T010](tasks/APP-M2.md#app-m2-t010) | OIDC 登录跳转、会话续期、401 回登录并返回原页 | planned | APP-M2-T001 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T010.md` |
| [APP-M2-T011](tasks/APP-M2.md#app-m2-t011) | 会话超时处理、用户菜单与退出登录 | planned | APP-M2-T001、APP-M2-T010 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T011.md` |
| [APP-M2-T012](tasks/APP-M2.md#app-m2-t012) | Keycloak 自定义登录主题（离线；错误、锁定、超时，已有示例卡） | planned | APP-M2-T010 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T012.md` |
| [APP-M2-T013](tasks/APP-M2.md#app-m2-t013) | 登录主题：首次登录强制改密、公司停用提示、读取品牌设置 | planned | APP-M2-T010 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T013.md` |
| [APP-M2-T014](tasks/APP-M2.md#app-m2-t014) | 路由守卫与 403 页 | planned | APP-M2-T010 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T014.md` |
| [APP-M2-T015](tasks/APP-M2.md#app-m2-t015) | 权限指令 `<Can>` 与按钮隐藏 | planned | APP-M2-T010 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T015.md` |
| [APP-M2-T016](tasks/APP-M2.md#app-m2-t016) | 数据权限的前端表现：只读态切换（项目 / 分册 / 章节） | planned | APP-M2-T010 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T016.md` |
| [APP-M2-T017](tasks/APP-M2.md#app-m2-t017) | MaskedField 与“查看完整值”弹窗（原因必填） | planned | APP-M2-T014 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T017.md` |
| [APP-M2-T018](tasks/APP-M2.md#app-m2-t018) | 掩码规则读取与查看留痕提示 | planned | APP-M2-T014、APP-M2-T017 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T018.md` |
| [APP-M2-T019](tasks/APP-M2.md#app-m2-t019) | JobProgress：步骤、子进度、AI 紫进度条 | planned | APP-M2-T014 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T019.md` |
| [APP-M2-T020](tasks/APP-M2.md#app-m2-t020) | JobProgress：SSE 订阅、断线提示与轮询回退 | planned | APP-M2-T014、APP-M2-T019 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T020.md` |
| [APP-M2-T021](tasks/APP-M2.md#app-m2-t021) | 任务中心页基础 + 顶栏任务角标与抽屉 | planned | APP-M2-T014、APP-M2-T019、APP-M2-T020 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T021.md` |
| [APP-M2-T022](tasks/APP-M2.md#app-m2-t022) | 平台管理员脱敏视图；从失败步骤重试、取消权限 | planned | APP-M2-T021 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T022.md` |
| [APP-M2-T023](tasks/APP-M2.md#app-m2-t023) | StatusTag 状态注册表（9.3 全部代码表） | planned | APP-M2-T005 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T023.md` |
| [APP-M2-T024](tasks/APP-M2.md#app-m2-t024) | A-03 字典配置页 | planned | APP-M2-T005 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T024.md` |
| [APP-M2-T025](tasks/APP-M2.md#app-m2-t025) | 扩展字段与公司设置键表单框架 | planned | APP-M2-T005、APP-M2-T024 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T025.md` |
| [APP-M2-T026](tasks/APP-M2.md#app-m2-t026) | A-01 公司管理 | planned | APP-M2-T014 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T026.md` |
| [APP-M2-T027](tasks/APP-M2.md#app-m2-t027) | A-02 用户列表、新增、停用前转交；“账号安全设置”面板（公司密码策略，只能调严） | planned | APP-M2-T014、APP-M2-T026 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T027.md` |
| [APP-M2-T028](tasks/APP-M2.md#app-m2-t028) | A-02 角色分配、解锁、重置密码 | planned | APP-M2-T014、APP-M2-T027 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T028.md` |
| [APP-M2-T029](tasks/APP-M2.md#app-m2-t029) | 顶栏铃铛与未读数 | planned | APP-M2-T010 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T029.md` |
| [APP-M2-T030](tasks/APP-M2.md#app-m2-t030) | 提醒下拉：最近 7 条、标已读、全部已读 | planned | APP-M2-T010、APP-M2-T029 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T030.md` |
| [APP-M2-T031](tasks/APP-M2.md#app-m2-t031) | G-02 站内提醒列表页（筛选、已读 / 未读、合并显示） | planned | APP-M2-T029 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T031.md` |
| [APP-M2-T032](tasks/APP-M2.md#app-m2-t032) | 17 类提醒的跳转目标映射与“对象已不存在”提示 | planned | APP-M2-T029、APP-M2-T031 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T032.md` |
| [APP-M2-T033](tasks/APP-M2.md#app-m2-t033) | BrandProvider 运行时主题 + 品牌校验函数（对比度、ΔE） | planned | APP-M2-T008 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T033.md` |
| [APP-M2-T034](tasks/APP-M2.md#app-m2-t034) | A-12 界面品牌页（表单 + 预览 + 恢复默认） | planned | APP-M2-T008、APP-M2-T033 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T034.md` |
| [APP-M2-T035](tasks/APP-M2.md#app-m2-t035) | 全局搜索：顶栏下拉与结果页 | planned | APP-M2-T014 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T035.md` |
| [APP-M2-T036](tasks/APP-M2.md#app-m2-t036) | A-08 模型列表与 `service_status` | planned | APP-M2-T014 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T036.md` |
| [APP-M2-T037](tasks/APP-M2.md#app-m2-t037) | 模型登记表单（不支持字段置灰）与测试连接 | planned | APP-M2-T014、APP-M2-T036 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T037.md` |
| [APP-M2-T038](tasks/APP-M2.md#app-m2-t038) | 模型配置版本与回滚 | planned | APP-M2-T014、APP-M2-T037 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T038.md` |
| [APP-M2-T039](tasks/APP-M2.md#app-m2-t039) | A-09 文档解析服务（云端 / 本地两组页签） | planned | APP-M2-T014、APP-M2-T021 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T039.md` |
| [APP-M2-T040](tasks/APP-M2.md#app-m2-t040) | A-10 任务与模型对应表（首选本地 → 备用只列本地） | planned | APP-M2-T036 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T040.md` |
| [APP-M2-T041](tasks/APP-M2.md#app-m2-t041) | A-05 公司模型开放 | planned | APP-M2-T036 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T041.md` |
| [APP-M2-T042](tasks/APP-M2.md#app-m2-t042) | A-11 部署与服务状态页 | planned | APP-M2-T036 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T042.md` |
| [APP-M2-T043](tasks/APP-M2.md#app-m2-t043) | CrossFieldHint 组件与 9.11 规则函数 | planned | APP-M2-T025 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T043.md` |
| [APP-M2-T044](tasks/APP-M2.md#app-m2-t044) | A-05 生成闭环参数 | planned | APP-M2-T025、APP-M2-T043 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T044.md` |
| [APP-M2-T045](tasks/APP-M2.md#app-m2-t045) | 编辑台与对话助手参数（自动保存、心跳 15～120、锁超时） | planned | APP-M2-T025、APP-M2-T043 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T045.md` |
| [APP-M2-T046](tasks/APP-M2.md#app-m2-t046) | 资料列表通用页 | planned | APP-M2-T005、APP-M2-T006、APP-M2-T017 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T046.md` |
| [APP-M2-T047](tasks/APP-M2.md#app-m2-t047) | 资料详情通用页（附件槽位、来源） | planned | APP-M2-T005、APP-M2-T006、APP-M2-T017 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T047.md` |
| [APP-M2-T048](tasks/APP-M2.md#app-m2-t048) | 确认 / 审核状态机界面（★ 字段重确认） | planned | APP-M2-T005、APP-M2-T006、APP-M2-T017、APP-M2-T047、APP-M2-T203 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T048.md` |
| [APP-M2-T049](tasks/APP-M2.md#app-m2-t049) | 受限资料与转交 | planned | APP-M2-T005、APP-M2-T006、APP-M2-T017、APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T049.md` |
| [APP-M2-T050](tasks/APP-M2.md#app-m2-t050) | 变更历史与被引用情况 | planned | APP-M2-T005、APP-M2-T006、APP-M2-T017、APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T050.md` |
| [APP-M2-T051](tasks/APP-M2.md#app-m2-t051) | 厂商产品树 | planned | APP-M2-T024 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T051.md` |
| [APP-M2-T052](tasks/APP-M2.md#app-m2-t052) | 证书类别与附件槽位 | planned | APP-M2-T024、APP-M2-T051 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T052.md` |
| [APP-M2-T053](tasks/APP-M2.md#app-m2-t053) | 中小企业划型标准 | planned | APP-M2-T024、APP-M2-T051 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T053.md` |
| [APP-M2-T054](tasks/APP-M2.md#app-m2-t054) | 公司主体（含关联关系） | planned | APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T054.md` |
| [APP-M2-T055](tasks/APP-M2.md#app-m2-t055) | 证明材料 | planned | APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T055.md` |
| [APP-M2-T056](tasks/APP-M2.md#app-m2-t056) | 资质证书 | planned | APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T056.md` |
| [APP-M2-T057](tasks/APP-M2.md#app-m2-t057) | 安全与合规事件 | planned | APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T057.md` |
| [APP-M2-T058](tasks/APP-M2.md#app-m2-t058) | 工具与设备 | planned | APP-M2-T047、APP-M2-T051 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T058.md` |
| [APP-M2-T059](tasks/APP-M2.md#app-m2-t059) | 附件库 | planned | APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T059.md` |
| [APP-M2-T060](tasks/APP-M2.md#app-m2-t060) | 人员列表 | planned | APP-M2-T047、APP-M2-T059 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T060.md` |
| [APP-M2-T061](tasks/APP-M2.md#app-m2-t061) | 人员详情（MaskedField） | planned | APP-M2-T047、APP-M2-T059、APP-M2-T017 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T061.md` |
| [APP-M2-T062](tasks/APP-M2.md#app-m2-t062) | 人员证书 | planned | APP-M2-T047、APP-M2-T059、APP-M2-T061、APP-M2-T052 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T062.md` |
| [APP-M2-T063](tasks/APP-M2.md#app-m2-t063) | 占用（R12）与离职提示 | planned | APP-M2-T047、APP-M2-T059、APP-M2-T060 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T063.md` |
| [APP-M2-T064](tasks/APP-M2.md#app-m2-t064) | 授权列表 | planned | APP-M2-T047、APP-M2-T051、APP-M2-T054 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T064.md` |
| [APP-M2-T065](tasks/APP-M2.md#app-m2-t065) | 授权详情 | planned | APP-M2-T047、APP-M2-T051、APP-M2-T054 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T065.md` |
| [APP-M2-T066](tasks/APP-M2.md#app-m2-t066) | 授权链图（不满足节点标红、上游未登记虚线） | planned | APP-M2-T047、APP-M2-T051、APP-M2-T054、APP-M2-T065 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T066.md` |
| [APP-M2-T067](tasks/APP-M2.md#app-m2-t067) | 业绩列表与详情 | planned | APP-M2-T047、APP-M2-T051 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T067.md` |
| [APP-M2-T068](tasks/APP-M2.md#app-m2-t068) | 业绩成员与产品 | planned | APP-M2-T047、APP-M2-T051、APP-M2-T067、APP-M2-T060 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T068.md` |
| [APP-M2-T069](tasks/APP-M2.md#app-m2-t069) | SLA 模板（等级、变量） | planned | APP-M2-T047、APP-M2-T051 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T069.md` |
| [APP-M2-T070](tasks/APP-M2.md#app-m2-t070) | 全局变量 | planned | APP-M2-T047、APP-M2-T051 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T070.md` |
| [APP-M2-T071](tasks/APP-M2.md#app-m2-t071) | 资料库首页健康度卡片 | planned | APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T071.md` |
| [APP-M2-T072](tasks/APP-M2.md#app-m2-t072) | Excel 批量导入与逐条 / 按批确认 | planned | APP-M2-T047、APP-M2-T046 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T072.md` |
| [APP-M2-T073](tasks/APP-M2.md#app-m2-t073) | 有效期提醒与 A-04 资料库设置 | planned | APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T073.md` |
| [APP-M2-T074](tasks/APP-M2.md#app-m2-t074) | 附件识别上传与进度 | planned | APP-M2-T047、APP-M2-T039 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T074.md` |
| [APP-M2-T075](tasks/APP-M2.md#app-m2-t075) | 识别结果核对（“待核对”标记） | planned | APP-M2-T047、APP-M2-T039、APP-M2-T074 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T075.md` |
| [APP-M2-T076](tasks/APP-M2.md#app-m2-t076) | 片段列表 | planned | APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T076.md` |
| [APP-M2-T077](tasks/APP-M2.md#app-m2-t077) | 片段编辑（变量校验） | planned | APP-M2-T047、APP-M2-T076、APP-M2-T070 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T077.md` |
| [APP-M2-T078](tasks/APP-M2.md#app-m2-t078) | 版本对比与发布（R31 拦截原因） | in-review | APP-M2-T047、APP-M2-T077、APP-M2-T238 | [ISSUE-022](../issues/ISSUE-022.md) | [交付](delivery/APP-M2-T078.md) |
| [APP-M2-T079](tasks/APP-M2.md#app-m2-t079) | 同步状态与重新同步 | planned | APP-M2-T047、APP-M2-T078 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T079.md` |
| [APP-M2-T080](tasks/APP-M2.md#app-m2-t080) | 历史标书单个 / 批量导入 | planned | APP-M2-T021 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T080.md` |
| [APP-M2-T081](tasks/APP-M2.md#app-m2-t081) | 入库状态派生显示与摘取为片段 | planned | APP-M2-T021、APP-M2-T080 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T081.md` |
| [APP-M2-T082](tasks/APP-M2.md#app-m2-t082) | 版本条（发布、回滚） | planned | APP-M2-T025 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T082.md` |
| [APP-M2-T083](tasks/APP-M2.md#app-m2-t083) | 章节模板 | planned | APP-M2-T025、APP-M2-T082 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T083.md` |
| [APP-M2-T084](tasks/APP-M2.md#app-m2-t084) | 叫法术语、语气称呼 | planned | APP-M2-T025、APP-M2-T082 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T084.md` |
| [APP-M2-T085](tasks/APP-M2.md#app-m2-t085) | 句式规则 | planned | APP-M2-T025、APP-M2-T082 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T085.md` |
| [APP-M2-T086](tasks/APP-M2.md#app-m2-t086) | Word 模板与导出命名 | planned | APP-M2-T025、APP-M2-T082 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T086.md` |
| [APP-M2-T087](tasks/APP-M2.md#app-m2-t087) | 预览抽屉 | planned | APP-M2-T025、APP-M2-T083、APP-M2-T084、APP-M2-T085 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T087.md` |
| [APP-M2-T088](tasks/APP-M2.md#app-m2-t088) | 任务卡列表与版本 | planned | APP-M2-T082 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T088.md` |
| [APP-M2-T089](tasks/APP-M2.md#app-m2-t089) | 提示词模板编辑与发布校验 | planned | APP-M2-T082、APP-M2-T088 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T089.md` |
| [APP-M2-T090](tasks/APP-M2.md#app-m2-t090) | 平台默认与公司覆盖对照 | planned | APP-M2-T082、APP-M2-T089 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T090.md` |
| [APP-M2-T091](tasks/APP-M2.md#app-m2-t091) | 审查清单 | planned | APP-M2-T082 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T091.md` |
| [APP-M2-T092](tasks/APP-M2.md#app-m2-t092) | 风格样例卡片墙（启用开关） | planned | APP-M2-T082、APP-M2-T081 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T092.md` |
| [APP-M2-T093](tasks/APP-M2.md#app-m2-t093) | 入库脱敏扫描结果展示 | planned | APP-M2-T082、APP-M2-T092、APP-M2-T230、APP-M2-T238、APP-M2-T243 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T093.md` |
| [APP-M2-T094](tasks/APP-M2.md#app-m2-t094) | ProjectHeader 摘要条与页签（无“资料匹配”） | planned | APP-M1-T14 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T094.md` |
| [APP-M2-T095](tasks/APP-M2.md#app-m2-t095) | 项目列表 | planned | APP-M1-T14 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T095.md` |
| [APP-M2-T096](tasks/APP-M2.md#app-m2-t096) | 新建项目与 R19 提示 | planned | APP-M1-T14、APP-M2-T224 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T096.md` |
| [APP-M2-T097](tasks/APP-M2.md#app-m2-t097) | 项目概览（待办、分册、状态操作） | planned | APP-M1-T14、APP-M2-T094 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T097.md` |
| [APP-M2-T098](tasks/APP-M2.md#app-m2-t098) | 项目基本字段和合作方协议（成员复用T14） | planned | APP-M1-T14、APP-M2-T054 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T098.md` |
| [APP-M2-T099](tasks/APP-M2.md#app-m2-t099) | 项目设置：拟派人员、SLA 取值、规则覆盖 | planned | APP-M1-T14、APP-M2-T060、APP-M2-T069 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T099.md` |
| [APP-M2-T100](tasks/APP-M2.md#app-m2-t100) | 分册格式、闭环及导出设置（分工复用T14） | planned | APP-M1-T14、APP-M2-T044、APP-M2-T045、APP-M2-T086 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T100.md` |
| [APP-M2-T101](tasks/APP-M2.md#app-m2-t101) | 招标文件上传与版本链 | planned | APP-M1-T02、APP-M2-T021 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T101.md` |
| [APP-M2-T102](tasks/APP-M2.md#app-m2-t102) | 解析进度页（JobProgress 接入） | planned | APP-M1-T02、APP-M2-T021、APP-M2-T101 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T102.md` |
| [APP-M2-T103](tasks/APP-M2.md#app-m2-t103) | PdfLocator（PDF.js 本地 Worker、跳页高亮） | planned | APP-M1-T02、APP-M2-T101 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T103.md` |
| [APP-M2-T104](tasks/APP-M2.md#app-m2-t104) | 解析结果三栏布局与分类树 | planned | APP-M1-T02、APP-M2-T103 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T104.md` |
| [APP-M2-T105](tasks/APP-M2.md#app-m2-t105) | 条目卡片编辑与逐条确认 | planned | APP-M1-T02、APP-M2-T104 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T105.md` |
| [APP-M2-T106](tasks/APP-M2.md#app-m2-t106) | 批量确认（星号 / 废标 / 资格禁用）与置信度高亮 | planned | APP-M1-T02、APP-M2-T105 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T106.md` |
| [APP-M2-T107](tasks/APP-M2.md#app-m2-t107) | 重抽不覆盖与补遗差异 | planned | APP-M1-T02、APP-M2-T105、APP-M2-T101 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T107.md` |
| [APP-M2-T108](tasks/APP-M2.md#app-m2-t108) | “确认解析结果”闸门（悬停列未满足项） | planned | APP-M1-T02、APP-M2-T106、APP-M2-T107、APP-M2-T109、APP-M2-T110、APP-M2-T111 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T108.md` |
| [APP-M2-T109](tasks/APP-M2.md#app-m2-t109) | 后处理条与合并条目（“已合并 N 条 · 拆分”、多位置切换） | planned | APP-M2-T104、APP-M2-T019 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T109.md` |
| [APP-M2-T110](tasks/APP-M2.md#app-m2-t110) | 冲突待选定页签（并列取值、理由必填） | planned | APP-M2-T104、APP-M2-T109 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T110.md` |
| [APP-M2-T111](tasks/APP-M2.md#app-m2-t111) | 疑似遗漏（无批量、排除须理由）与引用未解析页签 | planned | APP-M2-T104、APP-M2-T148、APP-M2-T109 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T111.md` |
| [APP-M2-T112](tasks/APP-M2.md#app-m2-t112) | 矩阵表格与筛选（风险提示） | planned | APP-M1-T03 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T112.md` |
| [APP-M2-T113](tasks/APP-M2.md#app-m2-t113) | 行编辑（响应方式、要点、负责人） | planned | APP-M1-T03、APP-M2-T112 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T113.md` |
| [APP-M2-T114](tasks/APP-M2.md#app-m2-t114) | EvidenceDrawer | planned | APP-M1-T03、APP-M2-T048、APP-M2-T204、APP-M2-T205 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T114.md` |
| [APP-M2-T115](tasks/APP-M2.md#app-m2-t115) | 批量智能匹配与逐行确认 | planned | APP-M1-T03、APP-M2-T118 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T115.md` |
| [APP-M2-T116](tasks/APP-M2.md#app-m2-t116) | P-18 分册分流确认 | planned | APP-M1-T03、APP-M1-T14 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T116.md` |
| [APP-M2-T117](tasks/APP-M2.md#app-m2-t117) | Excel 导出与确认闸门 | planned | APP-M1-T03、APP-M2-T113、APP-M2-T114、APP-M2-T116 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T117.md` |
| [APP-M2-T118](tasks/APP-M2.md#app-m2-t118) | 挂证据候选的三路显示（结构化规则匹配 / 片段检索 / 历史标书仅参考） | planned | APP-M2-T114、APP-M2-T078、APP-M2-T081 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T118.md` |
| [APP-M2-T119](tasks/APP-M2.md#app-m2-t119) | SLA 矩阵表与判定 | planned | APP-M1-T10、APP-M1-T12、APP-M2-T069 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T119.md` |
| [APP-M2-T120](tasks/APP-M2.md#app-m2-t120) | 模板取值与承诺函导出 | planned | APP-M1-T10、APP-M1-T12、APP-M2-T119 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T120.md` |
| [APP-M2-T121](tasks/APP-M2.md#app-m2-t121) | 项目事实表 | planned | APP-M1-T10、APP-M1-T12 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T121.md` |
| [APP-M2-T122](tasks/APP-M2.md#app-m2-t122) | “需复核”传播提示 | planned | APP-M1-T10、APP-M1-T12、APP-M2-T119、APP-M2-T121 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T122.md` |
| [APP-M2-T123](tasks/APP-M2.md#app-m2-t123) | 大纲排序、章节类型和增值理由（分工复用T15） | planned | APP-M1-T15、APP-M2-T116 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T123.md` |
| [APP-M2-T124](tasks/APP-M2.md#app-m2-t124) | 完整证据、片段及评分写作计划（确认复用T15） | blocked | APP-M1-T15已具备；APP-M2-T078 为 in-review 未 done，APP-M2-T114 仍 planned。三个 operationId 仅为草案 | [ISSUE-022](../issues/ISSUE-022.md) | [草案记录](delivery/APP-M2-T124.md) |
| [APP-M2-T125](tasks/APP-M2.md#app-m2-t125) | 招标原文预览联动与 R26 提示 | planned | APP-M1-T15、APP-M2-T123、APP-M2-T232 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T125.md` |
| [APP-M2-T126](tasks/APP-M2.md#app-m2-t126) | 按逐节确认结果启动生成（确认复用T15） | planned | APP-M1-T15、APP-M2-T124、APP-M2-T125 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T126.md` |
| [APP-M2-T127](tasks/APP-M2.md#app-m2-t127) | 五类系统生成章节预览 | planned | APP-M1-T04、APP-M2-T191、APP-M2-T192、APP-M2-T193、APP-M2-T194、APP-M2-T195 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T127.md` |
| [APP-M2-T128](tasks/APP-M2.md#app-m2-t128) | 锁定提示与“去数据源修改” | planned | APP-M1-T04、APP-M2-T127、APP-M2-T163 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T128.md` |
| [APP-M2-T129](tasks/APP-M2.md#app-m2-t129) | 章节列表（编辑台入口） | planned | APP-M2-T126、APP-M2-T021 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T129.md` |
| [APP-M2-T130](tasks/APP-M2.md#app-m2-t130) | 章节循环进度页 | planned | APP-M2-T126、APP-M2-T021、APP-M2-T044、APP-M2-T234、APP-M2-T237、APP-M2-T238、APP-M2-T254、APP-M2-T244、APP-M2-T245、APP-M2-T246、APP-M2-T247、APP-M2-T248、APP-M2-T249 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T130.md` |
| [APP-M2-T131](tasks/APP-M2.md#app-m2-t131) | 轮次时间线 | planned | APP-M2-T126、APP-M2-T021、APP-M2-T130 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T131.md` |
| [APP-M2-T132](tasks/APP-M2.md#app-m2-t132) | 版本对比（复用 DiffView） | planned | APP-M2-T126、APP-M2-T021、APP-M2-T175 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T132.md` |
| [APP-M2-T133](tasks/APP-M2.md#app-m2-t133) | 人工处理队列列表 | planned | APP-M2-T126、APP-M2-T021、APP-M2-T130 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T133.md` |
| [APP-M2-T134](tasks/APP-M2.md#app-m2-t134) | 队列详情单段编辑 | planned | APP-M2-T126、APP-M2-T021、APP-M2-T133、APP-M2-T174 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T134.md` |
| [APP-M2-T135](tasks/APP-M2.md#app-m2-t135) | 一键重新检查 | planned | APP-M2-T126、APP-M2-T021、APP-M2-T134 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T135.md` |
| [APP-M2-T136](tasks/APP-M2.md#app-m2-t136) | 异常中断与重试 | planned | APP-M2-T126、APP-M2-T021、APP-M2-T130 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T136.md` |
| [APP-M2-T137](tasks/APP-M2.md#app-m2-t137) | W-03 公司级写作观察统计 | planned | APP-M2-T131、APP-M2-T189 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T137.md` |
| [APP-M2-T138](tasks/APP-M2.md#app-m2-t138) | P-17 项目级折叠区 | planned | APP-M2-T131、APP-M2-T189 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T138.md` |
| [APP-M2-T139](tasks/APP-M2.md#app-m2-t139) | 图表组件（AntV G2，待技术确认） | planned | APP-M2-T131、APP-M2-T189 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T139.md` |
| [APP-M2-T140](tasks/APP-M2.md#app-m2-t140) | RuleIssueList | planned | APP-M1-T05 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T140.md` |
| [APP-M2-T141](tasks/APP-M2.md#app-m2-t141) | 合规检查页布局与结论条 | planned | APP-M1-T05、APP-M2-T140 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T141.md` |
| [APP-M2-T142](tasks/APP-M2.md#app-m2-t142) | 警告放行（理由必填，阻断无放行） | planned | APP-M1-T05、APP-M2-T140 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T142.md` |
| [APP-M2-T143](tasks/APP-M2.md#app-m2-t143) | R18 段落相似度并排对比 | planned | APP-M1-T05、APP-M2-T223 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T143.md` |
| [APP-M2-T144](tasks/APP-M2.md#app-m2-t144) | 分册检查 / 定稿 / 解锁 / 交叉复核 | planned | APP-M1-T05、APP-M2-T142、APP-M2-T228、APP-M2-T229、APP-M2-T250、APP-M2-T251、APP-M2-T252、APP-M2-T255、APP-M2-T256、APP-M2-T257、APP-M2-T258 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T144.md` |
| [APP-M2-T145](tasks/APP-M2.md#app-m2-t145) | 全文检查与“结果已过期”提示 | planned | APP-M1-T05、APP-M2-T144 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T145.md` |
| [APP-M2-T146](tasks/APP-M2.md#app-m2-t146) | 合规规则页签（不可关闭锁、R43 无阻断） | planned | APP-M2-T025 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T146.md` |
| [APP-M2-T147](tasks/APP-M2.md#app-m2-t147) | 规则参数、恢复平台默认、修改历史 | planned | APP-M2-T025、APP-M2-T146 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T147.md` |
| [APP-M2-T148](tasks/APP-M2.md#app-m2-t148) | 兜底扫描词表（草稿、试扫、发布） | planned | APP-M2-T025、APP-M2-T146 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T148.md` |
| [APP-M2-T149](tasks/APP-M2.md#app-m2-t149) | 导出前提检查 | planned | APP-M1-T05、APP-M2-T145 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T149.md` |
| [APP-M2-T150](tasks/APP-M2.md#app-m2-t150) | 导出类型、模板与命名 | planned | APP-M1-T05、APP-M2-T196、APP-M2-T197、APP-M2-T198 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T150.md` |
| [APP-M2-T151](tasks/APP-M2.md#app-m2-t151) | 导出历史与下载（`export_status` 含排队） | planned | APP-M1-T05、APP-M2-T202 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T151.md` |
| [APP-M2-T152](tasks/APP-M2.md#app-m2-t152) | 递交版：仅项目负责人可见、已确认完整值类别展示、内部稿掩码说明 | planned | APP-M2-T149、APP-M2-T100、APP-M2-T017、APP-M2-T196 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T152.md` |
| [APP-M2-T153](tasks/APP-M2.md#app-m2-t153) | 工作台 6 张统计卡（点击即筛选） | planned | APP-M2-T095 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T153.md` |
| [APP-M2-T154](tasks/APP-M2.md#app-m2-t154) | 概览底部折叠区 | planned | APP-M2-T095 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T154.md` |
| [APP-M2-T155](tasks/APP-M2.md#app-m2-t155) | 集团管理员公司切换与只读视图 | planned | APP-M2-T016 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T155.md` |
| [APP-M2-T156](tasks/APP-M2.md#app-m2-t156) | 集团统计 | planned | APP-M2-T016 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T156.md` |
| [APP-M2-T157](tasks/APP-M2.md#app-m2-t157) | A-06 审计日志页 | planned | APP-M2-T014 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T157.md` |
| [APP-M2-T158](tasks/APP-M2.md#app-m2-t158) | 云端调用审计展开 | planned | APP-M2-T014、APP-M2-T157、APP-M2-T037 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T158.md` |
| [APP-M2-T159](tasks/APP-M2.md#app-m2-t159) | 服务健康基础与 A-11（M1-J01a）对齐 | planned | APP-M2-T014、APP-M2-T042 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T159.md` |
| [APP-M2-T160](tasks/APP-M2.md#app-m2-t160) | 编辑台布局与三档断点（四栏 / 三栏 / 紧凑） | planned | APP-M1-T15 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T160.md` |
| [APP-M2-T161](tasks/APP-M2.md#app-m2-t161) | 章节加载与段落键 | planned | APP-M1-T15 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T161.md` |
| [APP-M2-T162](tasks/APP-M2.md#app-m2-t162) | SourceBar 来源标记 | planned | APP-M1-T15、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T162.md` |
| [APP-M2-T163](tasks/APP-M2.md#app-m2-t163) | 锁定内容 | planned | APP-M1-T15、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T163.md` |
| [APP-M2-T164](tasks/APP-M2.md#app-m2-t164) | 变量节点 | planned | APP-M1-T15、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T164.md` |
| [APP-M2-T165](tasks/APP-M2.md#app-m2-t165) | 证据节点与 `.cite` | planned | APP-M1-T15、APP-M2-T161、APP-M2-T048 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T165.md` |
| [APP-M2-T166](tasks/APP-M2.md#app-m2-t166) | 问题标注与侧栏联动 | planned | APP-M1-T15、APP-M2-T161、APP-M2-T140 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T166.md` |
| [APP-M2-T167](tasks/APP-M2.md#app-m2-t167) | 选区悬浮工具条 | planned | APP-M1-T15、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T167.md` |
| [APP-M2-T168](tasks/APP-M2.md#app-m2-t168) | 目录树与章节切换 | planned | APP-M1-T15、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T168.md` |
| [APP-M2-T169](tasks/APP-M2.md#app-m2-t169) | 工具栏紧凑模式（“格式”下拉） | planned | APP-M1-T15、APP-M2-T160 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T169.md` |
| [APP-M2-T170](tasks/APP-M2.md#app-m2-t170) | 只读态（他人编辑中） | planned | APP-M1-T15、APP-M2-T173 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T170.md` |
| [APP-M2-T171](tasks/APP-M2.md#app-m2-t171) | 长章节性能 | planned | APP-M1-T15、APP-M2-T161、APP-M2-T166、APP-M2-T167 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T171.md` |
| [APP-M2-T172](tasks/APP-M2.md#app-m2-t172) | 自动保存草稿 | planned | APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T172.md` |
| [APP-M2-T173](tasks/APP-M2.md#app-m2-t173) | EditLockBadge、心跳、超时提示、接管 | planned | APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T173.md` |
| [APP-M2-T174](tasks/APP-M2.md#app-m2-t174) | 提交版本与版本历史 | planned | APP-M2-T161、APP-M2-T172、APP-M2-T173 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T174.md` |
| [APP-M2-T175](tasks/APP-M2.md#app-m2-t175) | 版本对比与回退 | planned | APP-M2-T161、APP-M2-T174 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T175.md` |
| [APP-M2-T176](tasks/APP-M2.md#app-m2-t176) | 对话面板与会话列表 | planned | APP-M2-T167、APP-M2-T089 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T176.md` |
| [APP-M2-T177](tasks/APP-M2.md#app-m2-t177) | 流式输出、模型标识、降级提示 | planned | APP-M2-T167、APP-M2-T089、APP-M2-T176、APP-M2-T040 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T177.md` |
| [APP-M2-T178](tasks/APP-M2.md#app-m2-t178) | 建议卡片（写法、差异、来源、预检） | planned | APP-M2-T167、APP-M2-T089、APP-M2-T176、APP-M2-T242、APP-M2-T243、APP-M2-T244、APP-M2-T248 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T178.md` |
| [APP-M2-T179](tasks/APP-M2.md#app-m2-t179) | 自由问答（只“复制”） | planned | APP-M2-T167、APP-M2-T089、APP-M2-T181 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T179.md` |
| [APP-M2-T180](tasks/APP-M2.md#app-m2-t180) | 上下文与样例任务卡选择 | planned | APP-M2-T167、APP-M2-T089、APP-M2-T176、APP-M2-T124 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T180.md` |
| [APP-M2-T181](tasks/APP-M2.md#app-m2-t181) | 资料库与本项目数据答案卡 | planned | APP-M2-T176、APP-M2-T047、APP-M2-T112 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T181.md` |
| [APP-M2-T182](tasks/APP-M2.md#app-m2-t182) | 直查未命中与常规回答回退 | planned | APP-M2-T176、APP-M2-T047、APP-M2-T112、APP-M2-T181 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T182.md` |
| [APP-M2-T183](tasks/APP-M2.md#app-m2-t183) | 插入为引用：差异视图、写入、引用标记 | planned | APP-M2-T181、APP-M2-T185 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T183.md` |
| [APP-M2-T184](tasks/APP-M2.md#app-m2-t184) | 本项目招标文件轻量索引的检索结果展示 | planned | APP-M2-T181 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T184.md` |
| [APP-M2-T185](tasks/APP-M2.md#app-m2-t185) | 差异确认写入 | planned | APP-M2-T167、APP-M2-T178 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T185.md` |
| [APP-M2-T186](tasks/APP-M2.md#app-m2-t186) | “我已逐字核对”二次确认（星号 / 废标 / 偏离 / 披露） | planned | APP-M2-T167、APP-M2-T178、APP-M2-T185 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T186.md` |
| [APP-M2-T187](tasks/APP-M2.md#app-m2-t187) | 冲突校验与重新定位提示 | planned | APP-M2-T167、APP-M2-T178、APP-M2-T185 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T187.md` |
| [APP-M2-T188](tasks/APP-M2.md#app-m2-t188) | 粘贴识别 | planned | APP-M2-T167、APP-M2-T178、APP-M2-T185、APP-M2-T242、APP-M2-T243 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T188.md` |
| [APP-M2-T189](tasks/APP-M2.md#app-m2-t189) | 对话助手观察指标 | planned | APP-M2-T174、APP-M2-T185 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T189.md` |
| [APP-M2-T190](tasks/APP-M2.md#app-m2-t190) | 人工修改率分项 | planned | APP-M2-T174、APP-M2-T185 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T190.md` |
| [APP-M2-T191](tasks/APP-M2.md#app-m2-t191) | 点对点应答确定性章节 | planned | APP-M2-T113、APP-M2-T116 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T191.md` |
| [APP-M2-T192](tasks/APP-M2.md#app-m2-t192) | 评审索引确定性章节 | planned | APP-M2-T113、APP-M2-T123 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T192.md` |
| [APP-M2-T193](tasks/APP-M2.md#app-m2-t193) | 偏离表确定性章节 | planned | APP-M2-T113、APP-M2-T116 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T193.md` |
| [APP-M2-T194](tasks/APP-M2.md#app-m2-t194) | 年度服务计划确定性章节 | planned | APP-M2-T121、APP-M2-T113 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T194.md` |
| [APP-M2-T195](tasks/APP-M2.md#app-m2-t195) | 证明材料清单确定性章节 | planned | APP-M2-T114、APP-M2-T059、APP-M2-T099 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T195.md` |
| [APP-M2-T196](tasks/APP-M2.md#app-m2-t196) | Word模板与正文样式渲染 | planned | APP-M2-T086、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T196.md` |
| [APP-M2-T197](tasks/APP-M2.md#app-m2-t197) | 分册封面、目录与页码 | planned | APP-M2-T196、APP-M2-T100 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T197.md` |
| [APP-M2-T198](tasks/APP-M2.md#app-m2-t198) | 指定附件页与敏感水印 | planned | APP-M2-T196、APP-M2-T059 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T198.md` |
| [APP-M2-T199](tasks/APP-M2.md#app-m2-t199) | Word属性修订与批注清理 | planned | APP-M2-T196 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T199.md` |
| [APP-M2-T200](tasks/APP-M2.md#app-m2-t200) | 同批合标核对清单输出 | planned | APP-M2-T149、APP-M2-T197、APP-M2-T192、APP-M2-T193 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T200.md` |
| [APP-M2-T201](tasks/APP-M2.md#app-m2-t201) | 内部响应追溯Excel | planned | APP-M2-T117、APP-M2-T162、APP-M2-T165 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T201.md` |
| [APP-M2-T202](tasks/APP-M2.md#app-m2-t202) | 递交批次原子输出和历史快照 | planned | APP-M2-T152、APP-M2-T197、APP-M2-T198、APP-M2-T199、APP-M2-T200 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T202.md` |
| [APP-M2-T203](tasks/APP-M2.md#app-m2-t203) | R01 不可引用的资料禁止引用 | planned | APP-M2-T047、APP-M2-T077 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T203.md` |
| [APP-M2-T204](tasks/APP-M2.md#app-m2-t204) | R02 资料来源分级与投标主体一致 | planned | APP-M2-T054、APP-M2-T098 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T204.md` |
| [APP-M2-T205](tasks/APP-M2.md#app-m2-t205) | R03 有效期覆盖投标截止时间 | planned | APP-M2-T047、APP-M2-T099 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T205.md` |
| [APP-M2-T206](tasks/APP-M2.md#app-m2-t206) | R04 临期与复审提醒 | planned | APP-M2-T073、APP-M2-T031 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T206.md` |
| [APP-M2-T207](tasks/APP-M2.md#app-m2-t207) | R05 年审/监督审核有效 | planned | APP-M2-T056 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T207.md` |
| [APP-M2-T208](tasks/APP-M2.md#app-m2-t208) | R06 持证单位与主体名称一致 | planned | APP-M2-T056、APP-M2-T075 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T208.md` |
| [APP-M2-T209](tasks/APP-M2.md#app-m2-t209) | R07 原厂授权覆盖招标涉及的全部产品，授权链逐级有效，地域覆盖到地 | planned | APP-M2-T066、APP-M2-T051 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T209.md` |
| [APP-M2-T210](tasks/APP-M2.md#app-m2-t210) | R08 拟派人员持有招标涉及产品的有效原厂认证 | planned | APP-M2-T062、APP-M2-T099 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T210.md` |
| [APP-M2-T211](tasks/APP-M2.md#app-m2-t211) | R09 故障等级与服务时段 | planned | APP-M2-T119、APP-M2-T121、APP-M2-T069 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T211.md` |
| [APP-M2-T212](tasks/APP-M2.md#app-m2-t212) | R09 全类别SLA及能力比较 | planned | APP-M2-T119、APP-M2-T121、APP-M2-T069 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T212.md` |
| [APP-M2-T213](tasks/APP-M2.md#app-m2-t213) | R09 模板外承诺类事实 | planned | APP-M2-T119、APP-M2-T121、APP-M2-T069 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T213.md` |
| [APP-M2-T214](tasks/APP-M2.md#app-m2-t214) | R10 手写与自然表达全文承诺 | planned | APP-M2-T119、APP-M2-T164、APP-M2-T193 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T214.md` |
| [APP-M2-T215](tasks/APP-M2.md#app-m2-t215) | R10 结构节点及确定性输出 | planned | APP-M2-T119、APP-M2-T164、APP-M2-T193 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T215.md` |
| [APP-M2-T216](tasks/APP-M2.md#app-m2-t216) | R11 本单位人员与社保核对 | planned | APP-M2-T061、APP-M2-T099 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T216.md` |
| [APP-M2-T217](tasks/APP-M2.md#app-m2-t217) | R12 人员占用冲突 | planned | APP-M2-T063、APP-M2-T099 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T217.md` |
| [APP-M2-T218](tasks/APP-M2.md#app-m2-t218) | R13 业绩满足资格与评分条件 | planned | APP-M2-T067、APP-M2-T068 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T218.md` |
| [APP-M2-T219](tasks/APP-M2.md#app-m2-t219) | R14 必备附件齐全 | planned | APP-M2-T059、APP-M2-T195、APP-M2-T198 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T219.md` |
| [APP-M2-T220](tasks/APP-M2.md#app-m2-t220) | R15 占位符与【待补】清零 | planned | APP-M2-T164、APP-M2-T165 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T220.md` |
| [APP-M2-T221](tasks/APP-M2.md#app-m2-t221) | R16 主体基本资格与证明材料时效 | planned | APP-M2-T054、APP-M2-T055 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T221.md` |
| [APP-M2-T222](tasks/APP-M2.md#app-m2-t222) | R17 使用提示与保密项目提醒 | planned | APP-M2-T047、APP-M2-T100 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T222.md` |
| [APP-M2-T223](tasks/APP-M2.md#app-m2-t223) | R18 相似度检查 | planned | APP-M2-T095、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T223.md` |
| [APP-M2-T224](tasks/APP-M2.md#app-m2-t224) | R19 关联投标冲突 | planned | APP-M1-T01、APP-M2-T054 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T224.md` |
| [APP-M2-T225](tasks/APP-M2.md#app-m2-t225) | R20 同一编写人 | planned | APP-M2-T028、APP-M2-T174 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T225.md` |
| [APP-M2-T226](tasks/APP-M2.md#app-m2-t226) | R21 不同公司同一项目拟派人员为同一人 | planned | APP-M2-T061、APP-M2-T099 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T226.md` |
| [APP-M2-T227](tasks/APP-M2.md#app-m2-t227) | R22 不同公司同一项目的保证金转出账户相同 | planned | APP-M2-T054、APP-M2-T100 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T227.md` |
| [APP-M2-T228](tasks/APP-M2.md#app-m2-t228) | R23 星号条款、废标条款全部已确认响应 | planned | APP-M2-T105、APP-M2-T113 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T228.md` |
| [APP-M2-T229](tasks/APP-M2.md#app-m2-t229) | R24 格式要求 | planned | APP-M2-T191、APP-M2-T192、APP-M2-T193、APP-M2-T197 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T229.md` |
| [APP-M2-T230](tasks/APP-M2.md#app-m2-t230) | R25 名称机构残留 | planned | APP-M2-T161、APP-M2-T199 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T230.md` |
| [APP-M2-T231](tasks/APP-M2.md#app-m2-t231) | R25 Word元数据残留 | planned | APP-M2-T161、APP-M2-T199 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T231.md` |
| [APP-M2-T232](tasks/APP-M2.md#app-m2-t232) | R26 评分项覆盖度 | planned | APP-M2-T123、APP-M2-T113、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T232.md` |
| [APP-M2-T233](tasks/APP-M2.md#app-m2-t233) | R27 项目事实一致 | planned | APP-M2-T121、APP-M2-T164 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T233.md` |
| [APP-M2-T234](tasks/APP-M2.md#app-m2-t234) | R28 章节模型评审 | planned | APP-M2-T091、APP-M2-T089、APP-M2-T044、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T234.md` |
| [APP-M2-T235](tasks/APP-M2.md#app-m2-t235) | R29 本公司查重 | planned | APP-M2-T081、APP-M2-T078、APP-M2-T073、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T235.md` |
| [APP-M2-T236](tasks/APP-M2.md#app-m2-t236) | R30 无条款段落及范围外服务 | planned | APP-M2-T123、APP-M2-T121、APP-M2-T162 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T236.md` |
| [APP-M2-T237](tasks/APP-M2.md#app-m2-t237) | R30 额外数值承诺 | planned | APP-M2-T123、APP-M2-T121、APP-M2-T162 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T237.md` |
| [APP-M2-T238](tasks/APP-M2.md#app-m2-t238) | R31 正文敏感值与真实报告 | planned | APP-M2-T161、APP-M2-T059 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T238.md` |
| [APP-M2-T239](tasks/APP-M2.md#app-m2-t239) | R31 插图识别文字与报告附件 | planned | APP-M2-T161、APP-M2-T059 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T239.md` |
| [APP-M2-T240](tasks/APP-M2.md#app-m2-t240) | R32 产品范围一致 | planned | APP-M2-T051、APP-M2-T099、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T240.md` |
| [APP-M2-T241](tasks/APP-M2.md#app-m2-t241) | R33 拟派人员条件 | planned | APP-M2-T061、APP-M2-T062、APP-M2-T105、APP-M2-T099 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T241.md` |
| [APP-M2-T242](tasks/APP-M2.md#app-m2-t242) | R34 AI 痕迹与格式符号残留 | planned | APP-M2-T161、APP-M2-T089 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T242.md` |
| [APP-M2-T243](tasks/APP-M2.md#app-m2-t243) | R35 称呼一致 | planned | APP-M2-T084、APP-M2-T098、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T243.md` |
| [APP-M2-T244](tasks/APP-M2.md#app-m2-t244) | R43 套话空泛词密度 | planned | APP-M2-T084、APP-M2-T085、APP-M2-T092、APP-M2-T162 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T244.md` |
| [APP-M2-T245](tasks/APP-M2.md#app-m2-t245) | R43 七类句式及总结策略 | planned | APP-M2-T084、APP-M2-T085、APP-M2-T092、APP-M2-T162 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T245.md` |
| [APP-M2-T246](tasks/APP-M2.md#app-m2-t246) | R43 注入风格样例照抄 | planned | APP-M2-T084、APP-M2-T085、APP-M2-T092、APP-M2-T162 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T246.md` |
| [APP-M2-T247](tasks/APP-M2.md#app-m2-t247) | R44 得分要点事实密度 | planned | APP-M2-T124、APP-M2-T162、APP-M2-T165、APP-M1-T12 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T247.md` |
| [APP-M2-T248](tasks/APP-M2.md#app-m2-t248) | R44 逐事实锚点与段落归属 | planned | APP-M2-T124、APP-M2-T162、APP-M2-T165、APP-M1-T12 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T248.md` |
| [APP-M2-T249](tasks/APP-M2.md#app-m2-t249) | R44 未登记关键事实前后矛盾 | planned | APP-M2-T124、APP-M2-T162、APP-M2-T165、APP-M1-T12 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T249.md` |
| [APP-M2-T250](tasks/APP-M2.md#app-m2-t250) | R36 人员资质证明跨册一致 | planned | APP-M2-T195、APP-M2-T193、APP-M2-T099、APP-M2-T116 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T250.md` |
| [APP-M2-T251](tasks/APP-M2.md#app-m2-t251) | R36 偏离和证据版本跨册一致 | planned | APP-M2-T195、APP-M2-T193、APP-M2-T099、APP-M2-T116 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T251.md` |
| [APP-M2-T252](tasks/APP-M2.md#app-m2-t252) | R37 偏离表一致性 | planned | APP-M2-T193、APP-M2-T113 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T252.md` |
| [APP-M2-T253](tasks/APP-M2.md#app-m2-t253) | R38 证明材料与评分要点对应 | planned | APP-M2-T058、APP-M2-T059、APP-M2-T114、APP-M2-T075 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T253.md` |
| [APP-M2-T254](tasks/APP-M2.md#app-m2-t254) | R39 披露类条款 | planned | APP-M2-T057、APP-M2-T105、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T254.md` |
| [APP-M2-T255](tasks/APP-M2.md#app-m2-t255) | R40 评审索引表 | planned | APP-M2-T192、APP-M2-T123 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T255.md` |
| [APP-M2-T256](tasks/APP-M2.md#app-m2-t256) | R41 证明材料齐全与盖章 | planned | APP-M2-T195、APP-M2-T059、APP-M2-T099 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T256.md` |
| [APP-M2-T257](tasks/APP-M2.md#app-m2-t257) | R42 暗标正文节点 | planned | APP-M2-T197、APP-M2-T198、APP-M2-T199、APP-M2-T100 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T257.md` |
| [APP-M2-T258](tasks/APP-M2.md#app-m2-t258) | R42 暗标输出全部位置 | planned | APP-M2-T197、APP-M2-T198、APP-M2-T199、APP-M2-T100 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T258.md` |
| [APP-M2-T259](tasks/APP-M2.md#app-m2-t259) | 公司年度中小企业划型记录及声明取值 | planned | APP-M2-T053、APP-M2-T054、APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T259.md` |
| [AI-01](tasks/AI-M0.md#ai-01) | 登记模型、向量、业务库和内网访问待决项 | in-review | [FE-M0-T02](tasks/FE-M0.md#fe-m0-t02)；真实端点另计验收 | [ISSUE-010](../issues/ISSUE-010.md) | [登记交付](delivery/AI-01.md) |
| [AI-02](tasks/AI-M0.md#ai-02) | OpenAI 兼容对话适配器 | done | [BE-M0-T01](tasks/BE-M0.md#be-m0-t01) | [ISSUE-011](../issues/ISSUE-011.md) | [交付](delivery/AI-02.md) |
| [AI-03](tasks/AI-M0.md#ai-03) | 检索层内存骨架 | in-review | [BE-M0-T01](tasks/BE-M0.md#be-m0-t01) | [ISSUE-016](../issues/ISSUE-016.md) | [交付](delivery/AI-03.md) |
<!-- task-board:end -->

## 每次推进的同步顺序

1. 读取关联 Issue、任务卡、项目状态与当前版本；确认范围变化是否需要新需求/版本 Issue。
2. 确认任务依赖、API 和基线后转 ready，开工转 in-progress；阻塞时写具体原因和所需输入。
3. 完成实际变更与必要验证，先写 `docs/delivery/<TASK_ID>.md` 的结果、证据和限制；有代码修改时创建并链接 `docs/code/<TASK_ID>.md`，再转 in-review 等待验收。
4. 同步 PRD/ROADMAP/ARCHITECTURE 的受影响章节，或在交付中逐项记录无需修改的核对依据。
5. 更新 Issue、任务卡和本看板状态、PROJECT_STATUS 进度，最后登记 DOCUMENT_INDEX；检查链接/状态一致后转 done。
6. 把本地验收、合入、发布分别记录；功能只有真实接口联调通过才计生产完成。

当前优先：APP-M1按ICG示例实施和联调，来源差异同步核对；模型与向量库保留接口不阻止本地产品流程开发。ISSUE-010 已 closed：业务库为 MySQL 8，对话模型由配置页提供，嵌入与向量库用 RAGFlow 自带，生产生成仅内网。AI-01 为 in-review。AI-02已由项目经理于 10-12 12:10 在 QA 签署后确认为 done。AI-03 为 in-review，不连接 MySQL。ISSUE-005 保持 in-progress：错误体与幂等已由项目经理于 10-12 12:28 在 QA 签署后确认，后四张契约卡仍为 ready，该 Issue 不关闭。生产门禁继续验证，不能用主链路内部稿替代完整交付。
