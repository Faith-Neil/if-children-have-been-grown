为什么有这个文件：集中登记文档位置、版本、更新日期和来源。

它解决什么问题：避免找错版本，或修改文件后找不到对应记录。

# 文档更新索引

维护版本：g1.1。更新日期：2026-10-10。当前实现关联：ISSUE-007 / APP-M1；范围评审：ISSUE-005 / FE-M0-T03。文档入口统一使用本文件，规则见 [WORKFLOW](governance/WORKFLOW.md)。历史交付维持当时版本与事实；整个ICG来源清单以D-050登记。

编号保持稳定。每次新增、修改、移动、归档文档更新路径、日期、版本、状态、关联 Issue/任务和说明；有替代文件时保留来源。治理版本与业务文档/软件版本独立，参考产品原文以文内版本为准。

| 编号 | 更新日期 | 文档 | 层级/模块 | 版本 | 状态 | 关联 Issue/任务 | 说明 |
|---|---|---|---|---|---|---|---|
| D-001 | 2026-10-10 | [项目状态](PROJECT_STATUS.md) | 项目 | g1.1 | 当前 | ISSUE-007 / APP-M1 | ICG完整目标、联调状态及历史验收分列 |
| D-002 | 2026-10-10 | [前端 PRD](PRD.md) | 前端需求 | 参考实施入口 / g1.1 | 实施中 | ISSUE-007 / APP-M1 | ICG PRD1.8/字典1.9为当前目标；旧视图保留来源 |
| D-003 | 2026-10-10 | [前端架构](ARCHITECTURE.md) | 前端架构 | 参考实施入口 / g1.1 | 实施中 | ISSUE-007 / APP-M1 | 正式前端与后台同源、共享存储和替换接口 |
| D-004 | 2026-10-10 | [前端路线图](ROADMAP.md) | 计划 | 参考实施入口 / g1.1 | 执行入口 | ISSUE-007 / APP-M1 | 先主链路再其余页面，旧Phase映射仍保留 |
| D-005 | 2026-10-09 | [UX 规范](design/ux.md) | 设计 | 原文 | 参考 | FE-M0-T01 | 从ui/ux.md迁移，无业务内容改写 |
| D-006 | 2026-10-09 | [产品 PRD v1.8](reference/product/prd-mvp-v1.8.md) | 产品参考 | v1.8 | 供评审 | FE-M0-T01 | 已脱敏原文，不受治理修订覆盖 |
| D-007 | 2026-10-09 | [资料库字典 v1.9](reference/product/kb-data-dictionary-v1.9.md) | 数据参考 | v1.9 | 供评审 | FE-M0-T01 | 逻辑字典，不是数据库迁移 |
| D-008 | 2026-10-10 | [目录方案](architecture/repository-layout.md) | 架构 | 当前骨架 / reference-1 | 当前方案 | ISSUE-007 / APP-M1 | 首轮快照与实际同源前后端结构分列 |
| D-009 | 2026-10-09 | [基线差异](decisions/baseline-gaps.md) | 决策 | 初版 | 待评审 | FE-M0-T01 | 16项版本、范围与选型差异 |
| D-010 | 2026-10-09 | [PR #1 评审](reviews/pr-1-integration.md) | 协作 | 初版 / g1.0后续记录 | 待整合 | ISSUE-001 / ISSUE-003 | 系统/前端分层及后续规则、索引整合提醒 |
| D-011 | 2026-10-09 | [原型说明](../prototypes/bidding-ux/README.md) | 原型 | 静态演示 | 当前 | ISSUE-002 / FE-M0-T01 | 离线打开、启动方法与模拟范围 |
| D-012 | 2026-10-10 | [Issue 看板](../issues/index.md) | 问题 | g1.1 | 当前 | ISSUE-007 / APP-M1 | 变更、版本、Bug、验收及合入分列 |
| D-013 | 2026-10-09 | [首轮测试](testing/2026-10-09-repository-foundation.md) | 验证 | 首轮快照 | 已验收 | ISSUE-002 / FE-M0-T01 | 编辑锁6项回归及当时链接校验 |
| D-014 | 2026-10-09 | [首轮交付](delivery/2026-10-09-repository-foundation.md) | 交付 | 首轮快照 | 历史证据 | FE-M0-T01 | 保留原交付事实；逐任务归档见D-030 |
| D-015 | 2026-10-10 | [协作流程](governance/WORKFLOW.md) | 治理 | g1.1 | 当前规则 | ISSUE-007 / APP-M1 | 同一任务核对页面、后台与业务证据 |
| D-016 | 2026-10-09 | [本次同步表](governance/ISSUE-003-sync.md) | 治理 | g1.0 | 本次记录 | ISSUE-003 / FE-M0-T02 | 四份基线及看板、进度、索引的影响评估 |
| D-017 | 2026-10-10 | [任务看板](TASK_BOARD.md) | 执行 | g1.1 | 当前 | ISSUE-007 / APP-M1 | APP产品联调与历史FE任务分列 |
| D-018 | 2026-10-10 | [FE-M0 任务卡](tasks/FE-M0.md) | 基线与基础 | g1.1 | 当前计划 | ISSUE-006 / BE-M0-T01 | 前置基线、治理、契约与基础 |
| D-019 | 2026-10-09 | [FE-M1 任务卡](tasks/FE-M1.md) | 项目主流程 | g1.0 | 当前计划 | FE-M1 | 项目、招标解析、矩阵、事实 |
| D-020 | 2026-10-09 | [FE-M2 任务卡](tasks/FE-M2.md) | 章节生成 | g1.0 | 当前计划 | FE-M2 | 方案确认、任务进度、修正与转人工 |
| D-021 | 2026-10-09 | [FE-M3 任务卡](tasks/FE-M3.md) | 编辑台 | g1.0 | 当前计划 | FE-M3 | 文档编辑、来源、助手、Diff、锁、版本 |
| D-022 | 2026-10-09 | [FE-M4 任务卡](tasks/FE-M4.md) | 检查导出 | g1.0 | 当前计划 | FE-M4 | 检查、定稿、导出与追溯 |
| D-023 | 2026-10-09 | [FE-M5 任务卡](tasks/FE-M5.md) | 资料写作管理 | g1.0 | 当前计划 | FE-M5 | 资料、写作配置与必要管理页面 |
| D-024 | 2026-10-09 | [FE-M6 任务卡](tasks/FE-M6.md) | 协作增强 | g1.0 | 可后置 | FE-M6 | 按评审范围实施协作能力 |
| D-025 | 2026-10-09 | [FE-M7 任务卡](tasks/FE-M7.md) | 效率增强 | g1.0 | 可后置 | FE-M7 | 按评审范围实施效率能力 |
| D-026 | 2026-10-09 | [FE-M8 任务卡](tasks/FE-M8.md) | 发布门禁 | g1.0 | 当前计划 | FE-M8 | 一期验收、内网部署和发布 |
| D-027 | 2026-10-10 | [任务卡模板](templates/task-card.md) | 模板 | g1.1 | 当前 | ISSUE-006 / BE-M0-T01 | 边界、依赖、步骤、验收和交付 |
| D-028 | 2026-10-10 | [交付模板](templates/task-delivery.md) | 模板 | g1.0 | 当前 | ISSUE-006 / BE-M0-T01 | 每任务交付、代码解释、进度及同步字段 |
| D-029 | 2026-10-10 | [代码解释模板](templates/code-explanation.md) | 模板 | g1.0 | 当前 | ISSUE-006 / BE-M0-T01 | 实际入口、状态、约束和验证 |
| D-030 | 2026-10-09 | [FE-M0-T01交付](delivery/FE-M0-T01.md) | 任务交付 | 任务快照 | 已本地验收 | ISSUE-002 / FE-M0-T01 | 首轮工作逐任务归档，合入另列 |
| D-031 | 2026-10-09 | [FE-M0-T02交付](delivery/FE-M0-T02.md) | 任务交付 | g1.0 | 已本地验收 | ISSUE-003 / FE-M0-T02 | 本轮治理、检查程序与进度 |
| D-032 | 2026-10-09 | [T01代码解释](code/FE-M0-T01.md) | 代码 | 首轮实现 | 当前 | ISSUE-002 / FE-M0-T01 | 原型编辑锁与实际事件回归 |
| D-033 | 2026-10-09 | [T02代码解释](code/FE-M0-T02.md) | 代码 | g1.0 | 当前 | ISSUE-003 / FE-M0-T02 | 文档结构检查入口、错误与边界 |
| D-034 | 2026-10-09 | [治理测试](testing/2026-10-09-project-governance.md) | 验证 | g1.0 | 已本地验收 | ISSUE-003 / FE-M0-T02 | 实际记录校验与失败场景回归 |
| D-035 | 2026-10-09 | [Issue管理](../issues/README.md) | 问题 | g1.0 | 当前规则 | ISSUE-003 | 类型、状态、前置流程及同步要求 |
| D-036 | 2026-10-10 | [Issue模板](../issues/template.md) | 模板 | g1.0 | 当前 | ISSUE-006 / BE-M0-T01 | 来源、影响、任务、验收、版本与同步 |
| D-037 | 2026-10-09 | [ISSUE-001](../issues/ISSUE-001.md) | 技术决策 | 外部分支跟踪 | 待整合 | ISSUE-001 | 不改变原外部分支关闭事实，本地仍有依赖 |
| D-038 | 2026-10-09 | [ISSUE-002](../issues/ISSUE-002.md) | Bug | 首轮修复 | 本地验收关闭 | FE-M0-T01 | 锁定后的AI写入保护 |
| D-039 | 2026-10-09 | [ISSUE-003](../issues/ISSUE-003.md) | 工作流 | g1.0 | 本地验收关闭 | FE-M0-T02 | 用户本轮四项治理要求 |
| D-040 | 2026-10-10 | [维护约定](../AGENTS.md) | 协作规则 | g1.1 | 当前 | ISSUE-006 / BE-M0-T01 | 合作开发每次开工与收尾的入口 |
| D-041 | 2026-10-10 | [检查程序](../scripts/check-project-governance.cjs) | 工程代码 | g1.1 | 当前 | BE-M0-T01 | 活动记录检查，排除历史来源、依赖和Python缓存 |
| D-042 | 2026-10-10 | [检查程序回归](../tests/governance/check-project-governance.test.cjs) | 验证代码 | g1.1 | 12项通过 | BE-M0-T01 | 失败/工作区边界及Python依赖排除回归 |
| D-043 | 2026-10-10 | [Cursor协作规则](../.cursor/rules/project-governance.mdc) | 合作执行 | g1.1 | 当前 | ISSUE-006 / BE-M0-T01 | 对合作开发端始终启用同一流程，不复制异项目模板 |

| D-044 | 2026-10-09 | [ISSUE-004](../issues/ISSUE-004.md) | 工作流 | g1.1 | 已本地验收 | OPS-M0-T01 / REV-M0-T01 | 用户全工作区范围、合同排除、接手审查 |
| D-045 | 2026-10-09 | [OPS任务](tasks/OPS-M0.md) | 运维 | g1.1 | 当前 | ISSUE-004 | 工作区同步与实际运行验收 |
| D-046 | 2026-10-09 | [REV任务](tasks/REV-M0.md) | 审查 | g1.1 | 当前 | ISSUE-004 | 目录/业务/技术与brief交付 |
| D-047 | 2026-10-09 | [业务审查](reviews/2026-10-09-business-readiness.md) | 业务 | review-1 | 待决定 | REV-M0-T01 / ISSUE-005 | 场景矩阵与12项设计/验收发现 |
| D-048 | 2026-10-09 | [技术审查](reviews/2026-10-09-technical-readiness.md) | 技术 | review-1 | 待决定 | REV-M0-T01 / ISSUE-005 | 6类契约缺口与图片目录对照 |
| D-049 | 2026-10-10 | [接手brief](PROJECT_BRIEF.md) | 接手 | brief-5 | 当前 | ISSUE-007 / APP-M1 | 项目范围、现状、分支、风险与下一步 |
| D-050 | 2026-10-09 | [工作区来源](source/WORKSPACE_MATERIALS.md) | 历史资料 | snapshot-1 | 已登记 | OPS-M0-T01 | 34份ICG资料、原路径与初次指纹 |
| D-051 | 2026-10-09 | [同步工具说明](../tools/workspace-sync/README.md) | 运维 | sync-1 | 当前 | OPS-M0-T01 | 自动WIP、分叉、凭据、外部状态 |
| D-052 | 2026-10-09 | [同步执行器](../tools/workspace-sync/sync.cjs) | 工程代码 | sync-1 | 回归通过 | OPS-M0-T01 | 单实例、双向Git、稳定期与出站检查 |
| D-053 | 2026-10-09 | [加密凭据启动器](../tools/workspace-sync/Start-WorkspaceSync.ps1) | 工程代码 | sync-1 | 语法通过 | OPS-M0-T01 | Windows用户DPAPI与子进程临时令牌 |
| D-054 | 2026-10-09 | [配置示例](../tools/workspace-sync/config.example.json) | 配置 | sync-1 | 示例 | OPS-M0-T01 | 无凭据；实际配置在工作区外 |
| D-055 | 2026-10-09 | [同步回归](../tests/workspace-sync/sync.test.cjs) | 验证代码 | sync-1 | 10项通过 | OPS-M0-T01 | 真实bare remote与保护边界 |
| D-056 | 2026-10-09 | [OPS交付](delivery/OPS-M0-T01.md) | 交付 | g1.1 | 已本地验收 | ISSUE-004 / OPS-M0-T01 | 工作区迁移、工具与实际启用 |
| D-057 | 2026-10-09 | [OPS代码解释](code/OPS-M0-T01.md) | 代码 | sync-1 | 当前 | OPS-M0-T01 | 入口、状态、认证及限制 |
| D-058 | 2026-10-09 | [REV交付](delivery/REV-M0-T01.md) | 交付 | review-1 | 已本地验收 | ISSUE-004 / REV-M0-T01 | 审查证据与文档逻辑 |
| D-059 | 2026-10-09 | [本轮验证](testing/2026-10-09-workspace-sync.md) | 验证 | g1.1 | 已本地验收 | OPS-M0-T01 / REV-M0-T01 | 回归、迁移与真实云端运行 |
| D-060 | 2026-10-09 | [004同步表](governance/ISSUE-004-sync.md) | 治理 | g1.1 | 本轮记录 | ISSUE-004 | 六份基线及其他影响/不影响依据 |
| D-061 | 2026-10-10 | [待决门禁](../issues/ISSUE-005.md) | 决策 | review-2 | blocked | ISSUE-005 / FE-M0-T03/04 | DG-01～06不因审查完成自动解决 |
| D-062 | 2026-10-09 | [工作区运行](operations/workspace-sync.md) | 运维 | sync-1 | 当前 | OPS-M0-T01 | 状态、启动、停止、登录与冲突 |

| D-063 | 2026-10-10 | [一期交付建议](decisions/phase-one-scope.md) | 范围 | scope-1 | 部分已确认 | ISSUE-005 / FE-M0-T03 | 技术/商务两册已确认，其他生产边界继续评审 |
| D-064 | 2026-10-10 | [后端demo事项](../issues/ISSUE-006.md) | 实现 | demo-1 | closed（本地验收） | BE-M0-T01 | 实际后端开发和演示验收 |
| D-065 | 2026-10-10 | [后端任务卡](tasks/BE-M0.md) | 后端 | demo-1 | done（本地验收） | ISSUE-006 / BE-M0-T01 | 最小真实后台链路 |
| D-066 | 2026-10-10 | [后端准备核对](architecture/backend-demo-readiness.md) | 架构 | demo-1 | 已核对 | BE-M0-T01 | 分支缺口、接口与生产限制 |
| D-067 | 2026-10-10 | [后端代码解释](code/BE-M0-T01.md) | 代码 | demo-1 | 当前 | BE-M0-T01 | 入口、事务、权限、接口与输出 |
| D-068 | 2026-10-10 | [后端验收](testing/2026-10-10-backend-demo.md) | 验证 | demo-1 | 已本地验收 | BE-M0-T01 | 后台31项、记录12项、真实HTTP、页面下载与截图 |
| D-069 | 2026-10-10 | [后端交付](delivery/BE-M0-T01.md) | 交付 | demo-1 | 已本地验收 | ISSUE-006 / BE-M0-T01 | 实际成果、验收、状态及后续 |
| D-070 | 2026-10-10 | [后端运行说明](../backend/bid-core/README.md) | 工程 | reference-1 | 当前 | ISSUE-007 / APP-M1 | 同一产品安装、真实主流程与未完成边界 |
| D-071 | 2026-10-10 | [API约定说明](../spec/openapi/README.md) | 接口 | reference-1 | 当前 | ISSUE-007 / APP-M1 | 生成当前主流程及章节约定的方法 |
| D-072 | 2026-10-10 | [启动器](../backend/bid-core/Start-Demo.ps1) | 工具 | reference-1 | 已执行构建 | ISSUE-007 / APP-M1 | 安装前后端依赖、构建页面及单进程启动 |
| D-073 | 2026-10-10 | [依赖锁定](../backend/bid-core/requirements.txt) | 环境 | reference-1 | 安装通过 | ISSUE-007 / APP-M1 | 加数字PDF解析，pip check通过 |
| D-074 | 2026-10-10 | [实际接口约定](../spec/openapi/demo-v1.json) | 接口 | reference-1 | 生成 | ISSUE-007 / APP-M1 | 当前业务契约从代码导出，不手改 |
| D-075 | 2026-10-10 | [后台入口](../backend/bid-core/icg_demo/main.py) | 代码 | reference-1 | 联调通过 | ISSUE-007 / APP-M1 | 同源页面、v1与旧章节入口、两代错误字段 |
| D-076 | 2026-10-10 | [后台测试](../tests/backend/test_demo.py) | 验证代码 | demo-1 | 31项通过 | BE-M0-T01 | 实际失败边界、并发与输出 |
| D-077 | 2026-10-10 | [HTTP验收入口](../backend/bid-core/smoke_demo.py) | 验证工具 | demo-1 | 通过 | BE-M0-T01 | 连接实际监听端口执行完整链路 |
| D-078 | 2026-10-10 | [接口生成器](../backend/bid-core/export_openapi.py) | 工具 | demo-1 | 通过 | BE-M0-T01 | 保持约定与实际代码同源 |
| D-079 | 2026-10-10 | [页面事件回归](../tests/backend/demo-page.test.cjs) | 验证代码 | demo-1 | 7项通过 | BE-M0-T01 | 直接执行页面代码，验证旧草稿、确认、恢复失败与会话锁 |
| D-080 | 2026-10-10 | [示例联调Issue](../issues/ISSUE-007.md) | 变更 | reference-writing-1 | in-progress | ISSUE-007 / APP-M1 | 同一产品逐页接通，完整目标不以小demo代替 |
| D-081 | 2026-10-10 | [示例任务卡](tasks/APP-M1.md) | 实施 | reference-sla-1 | 当前 | ISSUE-007 / APP-M1 | 核心流程、独立验收、后续拆分和完整审计 |
| D-082 | 2026-10-10 | [示例接口约定](architecture/icg-reference-contract.md) | 接口 | reference-sla-1 | 联调中 | ISSUE-007 / APP-M1 | 新增结构化SLA、事实只读、变量/承诺函与版本规则 |
| D-083 | 2026-10-10 | [示例差异记录](decisions/icg-reference-deviations.md) | 评审 | reference-1 | 持续维护 | ISSUE-007 / APP-M1 | 版本缺件、已取消页签和高级功能差异 |
| D-084 | 2026-10-10 | [产品页面说明](../frontend/web/README.md) | 工程 | reference-sla-1 | 构建通过 | ISSUE-007 / APP-M1 | JSON配置用途、启动与当前能力边界 |
| D-085 | 2026-10-10 | [独立主流程测试](../tests/backend/test_reference_flow.py) | 验证代码 | reference-1 | 21项通过 | ISSUE-007 / APP-M1-T06 | 两册真实内容、源页码、输入失效与权限，页面主流程另有阶段记录 |
| D-086 | 2026-10-10 | [完整示例覆盖清单](testing/icg-coverage.md) | 验收范围 | reference-sla-1 | 未完整交付 | ISSUE-007 / APP-M1-T07/T08 | 47组页面/44规则保留；数值SLA部分实现，完整规则未交付 |

| D-087 | 2026-10-10 | [截图来源](testing/assets/README.md) | 证据 | reference-1 | 来源已登记 | ISSUE-007 / APP-M1 | 图片来自实际合成项目，不能代替完整验收 |
| D-088 | 2026-10-10 | [示例阶段验证](testing/2026-10-10-icg-reference.md) | 验证 | reference-1 | 阶段通过 | ISSUE-007 / APP-M1 | 后台77、前端9、旧页7、治理12、实际HTTP和GUI；Word视觉待验收 |
| D-089 | 2026-10-10 | [007同步记录](governance/ISSUE-007-sync.md) | 治理 | reference-sla-1 | 已核对 | ISSUE-007 / APP-M1 | 三件套、73项看板与三项SLA数值子任务交付对齐 |
| D-090 | 2026-10-10 | [独立边界回归](../tests/backend/test_reference_boundaries.py) | 验证代码 | reference-1 | 25项通过 | ISSUE-007 / APP-M1 | 模型路由、坏上传恢复、时区、候选失效与证据重新确认 |
| D-091 | 2026-10-10 | [主流程HTTP工具](../backend/bid-core/smoke_reference.py) | 验证工具 | reference-1 | 实际端口通过 | ISSUE-007 / APP-M1 | 仅本机合成项目，两册内容与草稿准备 |
| D-092 | 2026-10-10 | [前端日期回归](../tests/frontend/project-form.test.mjs) | 验证代码 | reference-1 | 3项通过 | ISSUE-007 / APP-M1 | 北京时间、日边界、无效日期和空字段 |
| D-093 | 2026-10-10 | [前端恢复回归](../tests/frontend/editor-recovery.test.mjs) | 验证代码 | reference-1 | 3项通过 | ISSUE-007 / APP-M1 | 核对期间版本/草稿变化拒绝，新草稿顺序 |
| D-094 | 2026-10-10 | [前端接口回归](../tests/frontend/api.test.mjs) | 验证代码 | reference-1 | 3项通过 | ISSUE-007 / APP-M1 | 两代错误、失败任务版本详情和移除请求保护 |
| D-095 | 2026-10-10 | [输入摘要](../backend/bid-core/icg_demo/input_snapshot.py) | 代码 | reference-sla-1 | 边界通过 | ISSUE-007 / APP-M1 | 旧建议、新候选和检查使用同一已提交输入摘要 |
| D-096 | 2026-10-10 | [APP-M1-T01阶段交付](delivery/APP-M1-T01.md) | 交付 | reference-1 | 部分交付 / 进行中 | ISSUE-007 / APP-M1 | 实际结果与未完成范围，不关闭完整任务 |
| D-097 | 2026-10-10 | [APP-M1-T01代码解释](code/APP-M1-T01.md) | 代码说明 | reference-1 | 当前 | ISSUE-007 / APP-M1 | 页面、后台和失败保护的实际调用关系 |
| D-098 | 2026-10-10 | [APP-M1-T02阶段交付](delivery/APP-M1-T02.md) | 交付 | reference-1 | 部分交付 / 进行中 | ISSUE-007 / APP-M1 | 实际结果与未完成范围，不关闭完整任务 |
| D-099 | 2026-10-10 | [APP-M1-T02代码解释](code/APP-M1-T02.md) | 代码说明 | reference-1 | 当前 | ISSUE-007 / APP-M1 | 页面、后台和失败保护的实际调用关系 |
| D-100 | 2026-10-10 | [APP-M1-T03阶段交付](delivery/APP-M1-T03.md) | 交付 | reference-sla-1 | 部分交付 / 进行中 | ISSUE-007 / APP-M1 | 实际结果与未完成范围，不关闭完整任务 |
| D-101 | 2026-10-10 | [APP-M1-T03代码解释](code/APP-M1-T03.md) | 代码说明 | reference-sla-1 | 当前 | ISSUE-007 / APP-M1 | 页面、后台和失败保护的实际调用关系 |
| D-102 | 2026-10-10 | [APP-M1-T04阶段交付](delivery/APP-M1-T04.md) | 交付 | reference-sla-1 | 部分交付 / 进行中 | ISSUE-007 / APP-M1 | 实际结果与未完成范围，不关闭完整任务 |
| D-103 | 2026-10-10 | [APP-M1-T04代码解释](code/APP-M1-T04.md) | 代码说明 | reference-sla-1 | 当前 | ISSUE-007 / APP-M1 | 页面、后台和失败保护的实际调用关系 |
| D-104 | 2026-10-10 | [APP-M1-T05阶段交付](delivery/APP-M1-T05.md) | 交付 | reference-1 | 部分交付 / 进行中 | ISSUE-007 / APP-M1 | 实际结果与未完成范围，不关闭完整任务 |
| D-105 | 2026-10-10 | [APP-M1-T05代码解释](code/APP-M1-T05.md) | 代码说明 | reference-1 | 当前 | ISSUE-007 / APP-M1 | 页面、后台和失败保护的实际调用关系 |

| D-106 | 2026-10-10 | [服务承诺验收](testing/2026-10-10-sla.md) | 验证 | reference-sla-1 | 本地通过 | ISSUE-007 / APP-M1-T09～T11 | 后台119/前端13、真实HTTP与页面、Word内容；视觉版式未验收 |
| D-107 | 2026-10-10 | [T09交付](delivery/APP-M1-T09.md) | 交付 | reference-sla-1 | 本地done / 待合入 | ISSUE-007 / APP-M1-T09～T11 | 结构化模板与能力；完整故障等级治理另验收 |
| D-108 | 2026-10-10 | [T09代码解释](code/APP-M1-T09.md) | 代码说明 | reference-sla-1 | 当前 | ISSUE-007 / APP-M1-T09～T11 | 模板确认依据、公司隔离、项目失效 |
| D-109 | 2026-10-10 | [T10交付](delivery/APP-M1-T10.md) | 交付 | reference-sla-1 | 本地done / 待合入 | ISSUE-007 / APP-M1-T09～T11 | 三方数值对照、七类判定与只读事实 |
| D-110 | 2026-10-10 | [T10代码解释](code/APP-M1-T10.md) | 代码说明 | reference-sla-1 | 当前 | ISSUE-007 / APP-M1-T09～T11 | 按招标取值保护、当前风险核对及事实复核 |
| D-111 | 2026-10-10 | [T11交付](delivery/APP-M1-T11.md) | 交付 | reference-sla-1 | 本地done / 待合入 | ISSUE-007 / APP-M1-T09～T11 | 变量与明确检查子集、内部承诺函；正式Word版式未验收 |
| D-112 | 2026-10-10 | [T11代码解释](code/APP-M1-T11.md) | 代码说明 | reference-sla-1 | 当前 | ISSUE-007 / APP-M1-T09～T11 | 单位换算、同一取值、旧出口保护及下载失效 |
| D-113 | 2026-10-10 | [服务承诺核心](../backend/bid-core/icg_demo/sla.py) | 代码 | reference-sla-1 | 定向验收通过 | ISSUE-007 / APP-M1-T09～T11 | 模板、判定、批准、派生事实、变量与实际表格 |
| D-114 | 2026-10-10 | [服务承诺字段](../backend/bid-core/icg_demo/sla_schemas.py) | 接口代码 | reference-sla-1 | 字段核对通过 | ISSUE-007 / APP-M1-T09～T11 | 严格数值与公司模板/项目值结构 |
| D-115 | 2026-10-10 | [服务承诺页面](../frontend/web/src/SlaPages.tsx) | 页面代码 | reference-sla-1 | 真实操作通过 | ISSUE-007 / APP-M1-T09～T11 | 模板维护、数值矩阵和承诺函下载 |
| D-116 | 2026-10-10 | [服务承诺表单](../frontend/web/src/sla-form.ts) | 代码 | reference-sla-1 | 行为通过 | ISSUE-007 / APP-M1-T09～T11 | 空值/零、数值、完整变量和单位插入 |
| D-117 | 2026-10-10 | [服务承诺HTTP工具](../backend/bid-core/smoke_sla.py) | 验证工具 | reference-sla-1 | 最终服务通过 | ISSUE-007 / APP-M1-T09～T11 | 仅本机合成项目、能力/事实门禁和真实下载 |
| D-118 | 2026-10-10 | [服务承诺独立测试](../tests/backend/test_sla.py) | 验证代码 | reference-sla-1 | 42项通过 | ISSUE-007 / APP-M1-T09～T11 | 单位、权限、来源/模板、出口、实际Word及本次确认依据 |
| D-119 | 2026-10-10 | [服务承诺前端测试](../tests/frontend/sla-form.test.mjs) | 验证代码 | reference-sla-1 | 4项通过 | ISSUE-007 / APP-M1-T09～T11 | 输入与选区/冲突单位，前端合计13项 |

| D-120 | 2026-10-10 | [写作输入验收](testing/2026-10-10-writing-input.md) | 验证 | reference-writing-1 | 本地通过 | ISSUE-007 / APP-M1-T12、T13 | 真实HTTP、页面、变量Word、当前限制 |
| D-121 | 2026-10-10 | [T12交付](delivery/APP-M1-T12.md) | 交付 | reference-writing-1 | 已本地验收 | ISSUE-007 / APP-M1-T12、T13 | 本章事实输入与保护限定子集 |
| D-122 | 2026-10-10 | [T13交付](delivery/APP-M1-T13.md) | 交付 | reference-writing-1 | 已本地验收 | ISSUE-007 / APP-M1-T12、T13 | 本章方案与候选来源页面子集 |
| D-123 | 2026-10-10 | [T12代码解释](code/APP-M1-T12.md) | 代码 | reference-writing-1 | 当前 | ISSUE-007 / APP-M1-T12、T13 | 共享组装器、快照与变量 |
| D-124 | 2026-10-10 | [T13代码解释](code/APP-M1-T13.md) | 代码 | reference-writing-1 | 当前 | ISSUE-007 / APP-M1-T12、T13 | 方案/当前输入/历史快照与事实插入 |
| D-125 | 2026-10-10 | [实际写作输入](../backend/bid-core/icg_demo/generation_context.py) | 后端 | reference-writing-1 | 当前 | ISSUE-007 / APP-M1-T12、T13 | 来源当前性、选定事实、输出变量保护 |
| D-126 | 2026-10-10 | [写作HTTP验收](../backend/bid-core/smoke_writing.py) | 验证 | reference-writing-1 | 已执行 | ISSUE-007 / APP-M1-T12、T13 | 本机合成端口、快照/变量/两册/失效 |
| D-127 | 2026-10-10 | [独立写作回归](../tests/backend/test_generation_context.py) | 验证 | reference-writing-1 | 已执行 | ISSUE-007 / APP-M1-T12、T13 | 捕获入参、权限/来源/变量/并发反例 |
| D-128 | 2026-10-10 | [本章方案页面](../frontend/web/src/WritingPlanReview.tsx) | 前端 | reference-writing-1 | 当前 | ISSUE-007 / APP-M1-T12、T13 | 负责人事实选择、要点与字数确认 |
| D-129 | 2026-10-10 | [输入快照页面](../frontend/web/src/WritingInputPreview.tsx) | 前端 | reference-writing-1 | 当前 | ISSUE-007 / APP-M1-T12、T13 | 当前准备输入与历史来源分别显示 |
| D-130 | 2026-10-10 | [写作页面函数](../frontend/web/src/writing-input.ts) | 前端 | reference-writing-1 | 当前 | ISSUE-007 / APP-M1-T12、T13 | 方案恢复、失效与事实变量插入 |
| D-131 | 2026-10-10 | [写作函数回归](../frontend/web/tests/writing-input.test.mjs) | 验证 | reference-writing-1 | 已执行 | ISSUE-007 / APP-M1-T12、T13 | 4项实际函数回归 |
| D-132 | 2026-10-10 | [写入来源独立回归](../tests/backend/test_candidate_write_guard.py) | 验证 | reference-writing-1 | 已执行 | ISSUE-007 / APP-M1-T12、T13 | 候选采纳后/草稿源改、事务拒绝、幂等与旧demo兼容 |
| D-133 | 2026-10-10 | [编辑来源保护函数](../frontend/web/src/editing-source.ts) | 前端 | reference-writing-1 | 当前 | ISSUE-007 / APP-M1-T13 | 草稿/候选原基准、显式重新核对及恢复 |
| D-134 | 2026-10-10 | [编辑来源回归](../frontend/web/tests/editing-source.test.mjs) | 验证 | reference-writing-1 | 已执行 | ISSUE-007 / APP-M1-T13 | 5项加载、恢复、写入与期间变动保护 |

## 更新记录

| 日期 | 关联 | 更新 |
|---|---|---|
| 2026-10-09 | FE-M0-T01 | 建立初始D-001～D-014条目，整理目录与参考输入 |
| 2026-10-09 | ISSUE-003 / FE-M0-T02 | 增加版本、状态、更新日期和来源字段，登记逐任务治理资料 |
| 2026-10-09 | ISSUE-004 / OPS / REV | Git根提升、ICG来源、同步工具与运行、审查/brief及未决门禁；历史记录不回写 |

| 2026-10-10 | ISSUE-005 / ISSUE-006 | 技术/商务范围确认、后端准备、真实demo、接口约定与验收；既有规则版本保持 |

| 2026-10-10 | ISSUE-007 / APP-M1 | 同源产品、五类边界修复、逐卡阶段交付、主流程验证和真实未完成范围 |

| 2026-10-10 | ISSUE-007 / APP-M1-T09～T11 | 数值SLA、模板/事实/变量/承诺函、独立验收及真实未完成范围；治理版本保持g1.1 |

| 2026-10-10 | ISSUE-007 / APP-M1-T12、T13 | 本章方案、真实事实输入、候选快照与变量保护；独立回归、实际HTTP/GUI/两册内容证据 |

## 缺失输入

技术方案v1.4.2、设计规范v1.2与完整高保真原型包尚未取得；历史产品稿和真实投标原件未入库。缺件和适用性按 [基线差异](decisions/baseline-gaps.md)追踪，不能以索引登记代替取得或验收。
