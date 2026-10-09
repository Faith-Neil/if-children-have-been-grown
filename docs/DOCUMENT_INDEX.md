为什么有这个文件：集中登记文档位置、版本、更新日期和来源。

它解决什么问题：避免找错版本，或修改文件后找不到对应记录。

# 文档更新索引

维护版本：g1.1。更新日期：2026-10-10。当前实现关联：ISSUE-006 / BE-M0-T01；范围评审：ISSUE-005 / FE-M0-T03。文档入口统一使用本文件，规则见 [WORKFLOW](governance/WORKFLOW.md)。历史交付维持当时版本与事实；整个ICG来源清单以D-050登记。

编号保持稳定。每次新增、修改、移动、归档文档更新路径、日期、版本、状态、关联 Issue/任务和说明；有替代文件时保留来源。治理版本与业务文档/软件版本独立，参考产品原文以文内版本为准。

| 编号 | 更新日期 | 文档 | 层级/模块 | 版本 | 状态 | 关联 Issue/任务 | 说明 |
|---|---|---|---|---|---|---|---|
| D-001 | 2026-10-10 | [项目状态](PROJECT_STATUS.md) | 项目 | g1.1 | 当前 | ISSUE-006 / BE-M0-T01 | 按任务事实汇总进度、阻塞与下一任务 |
| D-002 | 2026-10-10 | [前端 PRD](PRD.md) | 前端需求 | 旧业务视图 / g1.1 | 待业务对齐 | ISSUE-006 / BE-M0-T01 | 基于PRD v1.4/字典v1.5，新增工程验收；业务差异未自动关闭 |
| D-003 | 2026-10-10 | [前端架构](ARCHITECTURE.md) | 前端架构 | 旧业务视图 / g1.1 | 待业务对齐 | ISSUE-006 / BE-M0-T01 | 记录实际后台入口；生产架构未冻结 |
| D-004 | 2026-10-10 | [前端路线图](ROADMAP.md) | 计划 | 原阶段计划 / g1.1 | 执行入口 | ISSUE-006 / BE-M0-T01 | Phase/发布Milestone映射FE任务里程碑 |
| D-005 | 2026-10-09 | [UX 规范](design/ux.md) | 设计 | 原文 | 参考 | FE-M0-T01 | 从ui/ux.md迁移，无业务内容改写 |
| D-006 | 2026-10-09 | [产品 PRD v1.8](reference/product/prd-mvp-v1.8.md) | 产品参考 | v1.8 | 供评审 | FE-M0-T01 | 已脱敏原文，不受治理修订覆盖 |
| D-007 | 2026-10-09 | [资料库字典 v1.9](reference/product/kb-data-dictionary-v1.9.md) | 数据参考 | v1.9 | 供评审 | FE-M0-T01 | 逻辑字典，不是数据库迁移 |
| D-008 | 2026-10-10 | [目录方案](architecture/repository-layout.md) | 架构 | 初版 / g1.1导航 | 当前方案 | ISSUE-006 / BE-M0-T01 | 首轮快照、目标骨架与后续治理导航 |
| D-009 | 2026-10-09 | [基线差异](decisions/baseline-gaps.md) | 决策 | 初版 | 待评审 | FE-M0-T01 | 16项版本、范围与选型差异 |
| D-010 | 2026-10-09 | [PR #1 评审](reviews/pr-1-integration.md) | 协作 | 初版 / g1.0后续记录 | 待整合 | ISSUE-001 / ISSUE-003 | 系统/前端分层及后续规则、索引整合提醒 |
| D-011 | 2026-10-09 | [原型说明](../prototypes/bidding-ux/README.md) | 原型 | 静态演示 | 当前 | ISSUE-002 / FE-M0-T01 | 离线打开、启动方法与模拟范围 |
| D-012 | 2026-10-10 | [Issue 看板](../issues/index.md) | 问题 | g1.1 | 当前 | ISSUE-006 / BE-M0-T01 | 变更、版本、Bug、验收及合入分列 |
| D-013 | 2026-10-09 | [首轮测试](testing/2026-10-09-repository-foundation.md) | 验证 | 首轮快照 | 已验收 | ISSUE-002 / FE-M0-T01 | 编辑锁6项回归及当时链接校验 |
| D-014 | 2026-10-09 | [首轮交付](delivery/2026-10-09-repository-foundation.md) | 交付 | 首轮快照 | 历史证据 | FE-M0-T01 | 保留原交付事实；逐任务归档见D-030 |
| D-015 | 2026-10-10 | [协作流程](governance/WORKFLOW.md) | 治理 | g1.1 | 当前规则 | ISSUE-006 / BE-M0-T01 | Issue前置、任务推进、交付和文档同步 |
| D-016 | 2026-10-09 | [本次同步表](governance/ISSUE-003-sync.md) | 治理 | g1.0 | 本次记录 | ISSUE-003 / FE-M0-T02 | 四份基线及看板、进度、索引的影响评估 |
| D-017 | 2026-10-10 | [任务看板](TASK_BOARD.md) | 执行 | g1.1 | 当前 | ISSUE-006 / BE-M0-T01 | FE里程碑、任务、依赖、状态与交付 |
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
| D-049 | 2026-10-10 | [接手brief](PROJECT_BRIEF.md) | 接手 | brief-2 | 当前 | ISSUE-006 / BE-M0-T01 | 项目范围、现状、分支、风险与下一步 |
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
| D-070 | 2026-10-10 | [后端运行说明](../backend/bid-core/README.md) | 工程 | demo-1 | 当前 | BE-M0-T01 | 安装、接口、权限和演示边界 |
| D-071 | 2026-10-10 | [API约定说明](../spec/openapi/README.md) | 接口 | demo-1 | 当前 | BE-M0-T01 | 生成接口文件的用途及更新方法 |
| D-072 | 2026-10-10 | [启动器](../backend/bid-core/Start-Demo.ps1) | 工具 | demo-1 | 语法通过 | BE-M0-T01 | 本机安装及单进程启动 |
| D-073 | 2026-10-10 | [依赖锁定](../backend/bid-core/requirements.txt) | 环境 | demo-1 | 安装通过 | BE-M0-T01 | 实际运行/测试组合，pip check通过 |
| D-074 | 2026-10-10 | [实际接口约定](../spec/openapi/demo-v1.json) | 接口 | demo-1 | 生成 | BE-M0-T01 | 从可运行代码导出，不手改 |
| D-075 | 2026-10-10 | [后台入口](../backend/bid-core/icg_demo/main.py) | 代码 | demo-1 | 通过 | BE-M0-T01 | HTTP、认证、错误和明确响应字段 |
| D-076 | 2026-10-10 | [后台测试](../tests/backend/test_demo.py) | 验证代码 | demo-1 | 31项通过 | BE-M0-T01 | 实际失败边界、并发与输出 |
| D-077 | 2026-10-10 | [HTTP验收入口](../backend/bid-core/smoke_demo.py) | 验证工具 | demo-1 | 通过 | BE-M0-T01 | 连接实际监听端口执行完整链路 |
| D-078 | 2026-10-10 | [接口生成器](../backend/bid-core/export_openapi.py) | 工具 | demo-1 | 通过 | BE-M0-T01 | 保持约定与实际代码同源 |
| D-079 | 2026-10-10 | [页面事件回归](../tests/backend/demo-page.test.cjs) | 验证代码 | demo-1 | 7项通过 | BE-M0-T01 | 直接执行页面代码，验证旧草稿、确认、恢复失败与会话锁 |

## 更新记录

| 日期 | 关联 | 更新 |
|---|---|---|
| 2026-10-09 | FE-M0-T01 | 建立初始D-001～D-014条目，整理目录与参考输入 |
| 2026-10-09 | ISSUE-003 / FE-M0-T02 | 增加版本、状态、更新日期和来源字段，登记逐任务治理资料 |
| 2026-10-09 | ISSUE-004 / OPS / REV | Git根提升、ICG来源、同步工具与运行、审查/brief及未决门禁；历史记录不回写 |

| 2026-10-10 | ISSUE-005 / ISSUE-006 | 技术/商务范围确认、后端准备、真实demo、接口约定与验收；既有规则版本保持 |

## 缺失输入

技术方案v1.4.2、设计规范v1.2与完整高保真原型包尚未取得；历史产品稿和真实投标原件未入库。缺件和适用性按 [基线差异](decisions/baseline-gaps.md)追踪，不能以索引登记代替取得或验收。
