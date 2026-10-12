为什么有这个文件：集中登记文档位置、版本、更新日期和来源。

它解决什么问题：避免找错版本，或修改文件后找不到对应记录。

# 文档更新索引

维护版本：g1.1。更新日期：2026-10-12。当前实现关联：ISSUE-007 / APP-M1；离线检查：ISSUE-012 / APP-M2-T008；范围评审：ISSUE-005 / FE-M0-T03；模型待决：ISSUE-010 / AI-01（业务库已定为 MySQL 8）；兼容适配器：ISSUE-011 / AI-02（done）；检索骨架：ISSUE-016 / AI-03（in-review，仅内存）。文档入口统一使用本文件，规则见 [WORKFLOW](governance/WORKFLOW.md)。历史交付维持当时版本与事实；整个ICG来源清单以D-050登记。

编号保持稳定。每次新增、修改、移动、归档文档更新路径、日期、版本、状态、关联 Issue/任务和说明；有替代文件时保留来源。治理版本与业务文档/软件版本独立，参考产品原文以文内版本为准。

| 编号 | 更新日期 | 文档 | 层级/模块 | 版本 | 状态 | 关联 Issue/任务 | 说明 |
|---|---|---|---|---|---|---|---|
| D-001 | 2026-10-12 | [项目状态](PROJECT_STATUS.md) | 项目 | g1.1 | 当前 | ISSUE-007 / APP-M1；ISSUE-009 / T001；ISSUE-012 / T008；ISSUE-010 / AI-01；ISSUE-016 / AI-03 | 会话阶段、QA复跑、离线CI、MySQL 8 决定；AI-02 已 done，内存检索为 in-review |
| D-002 | 2026-10-11 | [前端 PRD](PRD.md) | 前端需求 | 参考实施入口 / g1.1 | 实施中 | ISSUE-007 / APP-M1 | ICG PRD1.8/字典1.9为当前目标；旧视图保留来源 |
| D-003 | 2026-10-12 | [前端架构](ARCHITECTURE.md) | 前端架构 | 参考实施入口 / g1.1 | 实施中 | ISSUE-007 / APP-M1；ISSUE-010 / AI-01；ISSUE-011 / AI-02；ISSUE-016 / AI-03 | 同源存储和替换接口；业务库为 MySQL 8，向量库未选定；检索口仅内存 |
| D-004 | 2026-10-12 | [前端路线图](ROADMAP.md) | 计划 | 参考实施入口 / g1.1 | 执行入口 | ISSUE-007 / APP-M1；ISSUE-010 / AI-01；ISSUE-012 / T008；ISSUE-016 / AI-03；ISSUE-022 / T124 | 354项21done、7in-review、265planned、50blocked；T124 blocked |
| D-005 | 2026-10-09 | [UX 规范](design/ux.md) | 设计 | 原文 | 参考 | FE-M0-T01 | 从ui/ux.md迁移，无业务内容改写 |
| D-006 | 2026-10-09 | [产品 PRD v1.8](reference/product/prd-mvp-v1.8.md) | 产品参考 | v1.8 | 供评审 | FE-M0-T01 | 已脱敏原文，不受治理修订覆盖 |
| D-007 | 2026-10-09 | [资料库字典 v1.9](reference/product/kb-data-dictionary-v1.9.md) | 数据参考 | v1.9 | 供评审 | FE-M0-T01 | 逻辑字典，不是数据库迁移 |
| D-008 | 2026-10-10 | [目录方案](architecture/repository-layout.md) | 架构 | 当前骨架 / reference-1 | 当前方案 | ISSUE-007 / APP-M1 | 首轮快照与实际同源前后端结构分列 |
| D-009 | 2026-10-09 | [基线差异](decisions/baseline-gaps.md) | 决策 | 初版 | 待评审 | FE-M0-T01 | 16项版本、范围与选型差异 |
| D-010 | 2026-10-09 | [PR #1 评审](reviews/pr-1-integration.md) | 协作 | 初版 / g1.0后续记录 | 待整合 | ISSUE-001 / ISSUE-003 | 系统/前端分层及后续规则、索引整合提醒 |
| D-011 | 2026-10-09 | [原型说明](../prototypes/bidding-ux/README.md) | 原型 | 静态演示 | 当前 | ISSUE-002 / FE-M0-T01 | 离线打开、启动方法与模拟范围 |
| D-012 | 2026-10-12 | [Issue 看板](../issues/index.md) | 问题 | g1.1 | 当前 | ISSUE-007 / APP-M1；ISSUE-005；ISSUE-010；ISSUE-011；ISSUE-012；ISSUE-013；ISSUE-014；ISSUE-015；ISSUE-016；ISSUE-017；ISSUE-020 | 010整体仍blocked；011与012已closed；005、009、014、016、017与020为in-review |
| D-013 | 2026-10-09 | [首轮测试](testing/2026-10-09-repository-foundation.md) | 验证 | 首轮快照 | 已验收 | ISSUE-002 / FE-M0-T01 | 编辑锁6项回归及当时链接校验 |
| D-014 | 2026-10-09 | [首轮交付](delivery/2026-10-09-repository-foundation.md) | 交付 | 首轮快照 | 历史证据 | FE-M0-T01 | 保留原交付事实；逐任务归档见D-030 |
| D-015 | 2026-10-12 | [协作流程](governance/WORKFLOW.md) | 治理 | g1.1 | 当前规则 | ISSUE-007 / APP-M1；ISSUE-012 | 同一任务核对页面、后台与业务证据；开发者只标 in-review，治理块不升版 |
| D-016 | 2026-10-09 | [本次同步表](governance/ISSUE-003-sync.md) | 治理 | g1.0 | 本次记录 | ISSUE-003 / FE-M0-T02 | 四份基线及看板、进度、索引的影响评估 |
| D-017 | 2026-10-12 | [任务看板](TASK_BOARD.md) | 执行 | g1.1 | 当前 | ISSUE-007 / APP-M1；ISSUE-012 / T008；ISSUE-010 / AI-01；ISSUE-011 / AI-02；ISSUE-016 / AI-03；ISSUE-022 / T124 | 354项21done、7in-review、265planned、50blocked；T124 blocked |
| D-018 | 2026-10-12 | [FE-M0 任务卡](tasks/FE-M0.md) | 基线与基础 | g1.1 | 当前计划 | ISSUE-006 / BE-M0-T01；ISSUE-010 | 前置基线、治理、契约与基础；T04仍待ISSUE-010 |
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
| D-045 | 2026-10-12 | [OPS任务](tasks/OPS-M0.md) | 运维 | g1.1 | 当前 | ISSUE-004；ISSUE-017 / OPS-M0-T02 | 工作区同步已验收；内网部署草案 in-review |
| D-046 | 2026-10-09 | [REV任务](tasks/REV-M0.md) | 审查 | g1.1 | 当前 | ISSUE-004 | 目录/业务/技术与brief交付 |
| D-047 | 2026-10-09 | [业务审查](reviews/2026-10-09-business-readiness.md) | 业务 | review-1 | 待决定 | REV-M0-T01 / ISSUE-005 | 场景矩阵与12项设计/验收发现 |
| D-048 | 2026-10-09 | [技术审查](reviews/2026-10-09-technical-readiness.md) | 技术 | review-1 | 待决定 | REV-M0-T01 / ISSUE-005 | 6类契约缺口与图片目录对照 |
| D-049 | 2026-10-12 | [接手brief](PROJECT_BRIEF.md) | 接手 | brief-8 | 当前 | ISSUE-007 / APP-M1；ISSUE-008 / T16；ISSUE-009 / T001；ISSUE-012；ISSUE-010；ISSUE-011；ISSUE-016；ISSUE-022 | 排期为354项、265planned、50blocked；T124 blocked |
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
| D-061 | 2026-10-12 | [待决门禁](../issues/ISSUE-005.md) | 决策 | review-2 | blocked | ISSUE-005 / FE-M0-T03/04；ISSUE-010 | DG-01～06不因 MySQL 8 决定或模型登记而关闭 |
| D-062 | 2026-10-09 | [工作区运行](operations/workspace-sync.md) | 运维 | sync-1 | 当前 | OPS-M0-T01 | 状态、启动、停止、登录与冲突 |
| D-063 | 2026-10-10 | [一期交付建议](decisions/phase-one-scope.md) | 范围 | scope-1 | 部分已确认 | ISSUE-005 / FE-M0-T03 | 技术/商务两册已确认，其他生产边界继续评审 |
| D-064 | 2026-10-10 | [后端demo事项](../issues/ISSUE-006.md) | 实现 | demo-1 | closed（本地验收） | BE-M0-T01 | 实际后端开发和演示验收 |
| D-065 | 2026-10-10 | [后端任务卡](tasks/BE-M0.md) | 后端 | demo-1 | done（本地验收） | ISSUE-006 / BE-M0-T01 | 最小真实后台链路 |
| D-066 | 2026-10-10 | [后端准备核对](architecture/backend-demo-readiness.md) | 架构 | demo-1 | 已核对 | BE-M0-T01 | 分支缺口、接口与生产限制 |
| D-067 | 2026-10-10 | [后端代码解释](code/BE-M0-T01.md) | 代码 | demo-1 | 当前 | BE-M0-T01 | 入口、事务、权限、接口与输出 |
| D-068 | 2026-10-10 | [后端验收](testing/2026-10-10-backend-demo.md) | 验证 | demo-1 | 已本地验收 | BE-M0-T01 | 后台31项、记录12项、真实HTTP、页面下载与截图 |
| D-069 | 2026-10-10 | [后端交付](delivery/BE-M0-T01.md) | 交付 | demo-1 | 已本地验收 | ISSUE-006 / BE-M0-T01 | 实际成果、验收、状态及后续 |
| D-070 | 2026-10-12 | [后端运行说明](../backend/bid-core/README.md) | 工程 | reference-1 / application-foundation-1 | 当前 | ISSUE-007 / APP-M1；ISSUE-009 / T001；ISSUE-011 / AI-02；ISSUE-016 / AI-03 | 同产品运行、可信会话、可选兼容模型；MySQL 8 已决定但未连接，检索口仅内存 |
| D-071 | 2026-10-11 | [API约定说明](../spec/openapi/README.md) | 接口 | reference-1 | 当前 | ISSUE-007 / APP-M1 | 生成当前主流程及章节约定的方法 |
| D-072 | 2026-10-10 | [启动器](../backend/bid-core/Start-Demo.ps1) | 工具 | reference-1 | 已执行构建 | ISSUE-007 / APP-M1 | 安装前后端依赖、构建页面及单进程启动 |
| D-073 | 2026-10-10 | [依赖锁定](../backend/bid-core/requirements.txt) | 环境 | reference-1 | 安装通过 | ISSUE-007 / APP-M1 | 加数字PDF解析，pip check通过 |
| D-074 | 2026-10-11 | [实际接口约定](../spec/openapi/demo-v1.json) | 接口 | reference-1 / application-foundation-1 | 生成 | ISSUE-007 / APP-M1；ISSUE-009 / T001 | 49路径57操作及getSession从代码导出，不手改 |
| D-075 | 2026-10-12 | [后台入口](../backend/bid-core/icg_demo/main.py) | 代码 | reference-1 | 联调通过 | ISSUE-007 / APP-M1；ISSUE-011 / AI-02 | 同源页面、两代错误字段；显式配置才启用兼容模型 |
| D-076 | 2026-10-11 | [后台测试](../tests/backend/test_demo.py) | 验证代码 | demo-1 | 31项通过 | BE-M0-T01 | 实际失败边界、并发与输出 |
| D-077 | 2026-10-11 | [HTTP验收入口](../backend/bid-core/smoke_demo.py) | 验证工具 | demo-1 | 通过 | BE-M0-T01 | 连接实际监听端口执行完整链路 |
| D-078 | 2026-10-10 | [接口生成器](../backend/bid-core/export_openapi.py) | 工具 | demo-1 | 通过 | BE-M0-T01 | 保持约定与实际代码同源 |
| D-079 | 2026-10-10 | [页面事件回归](../tests/backend/demo-page.test.cjs) | 验证代码 | demo-1 | 7项通过 | BE-M0-T01 | 直接执行页面代码，验证旧草稿、确认、恢复失败与会话锁 |
| D-080 | 2026-10-11 | [示例联调Issue](../issues/ISSUE-007.md) | 变更 | reference-members-1 | in-progress | ISSUE-007 / APP-M1 | 同一产品逐页接通，T07/T14/T15本地验收，完整目标继续 |
| D-081 | 2026-10-11 | [示例任务卡](tasks/APP-M1.md) | 实施 | reference-members-1 / library-basis-1 | 当前 | ISSUE-007 / APP-M1；ISSUE-008 / T16 | 16项，T07/T09～16本地done；资料及模板保护验收，完整父任务继续 |
| D-082 | 2026-10-11 | [示例接口约定](architecture/icg-reference-contract.md) | 接口 | reference-members-1 | 实际契约 | ISSUE-007 / APP-M1 | 项目成员、分册/本节分工、逐章确认、已读依据和交接保护 |
| D-083 | 2026-10-11 | [示例差异记录](decisions/icg-reference-deviations.md) | 评审 | reference-1 | 持续维护 | ISSUE-007 / APP-M1 | 版本缺件、已取消页签和高级功能差异 |
| D-084 | 2026-10-11 | [产品页面说明](../frontend/web/README.md) | 工程 | application-foundation-1 | 构建通过 | ISSUE-007 / APP-M1；ISSUE-008 / T16；ISSUE-009 / T001 | 72前端、可信会话守卫和真实页面；完整底座未完成 |
| D-085 | 2026-10-11 | [独立主流程测试](../tests/backend/test_reference_flow.py) | 验证代码 | reference-1 | 21项通过 | ISSUE-007 / APP-M1-T06 | 两册真实内容、源页码、输入失效与权限，页面主流程另有阶段记录 |
| D-086 | 2026-10-11 | [完整示例覆盖清单](testing/icg-coverage.md) | 验收范围 | reference-members-1 / library-basis-1 | 未完整交付 | ISSUE-007 / APP-M1；ISSUE-008 / T16 | 成员及逐章确认更新，完整资料治理和业务规则仍缺 |
| D-087 | 2026-10-11 | [截图来源](testing/assets/README.md) | 证据 | reference-1 / library-basis-1 | 来源已登记 | ISSUE-007 / APP-M1；ISSUE-008 / T16 | 合成项目截图；新增资料/模板6张，不能代替完整验收 |
| D-088 | 2026-10-10 | [示例阶段验证](testing/2026-10-10-icg-reference.md) | 验证 | reference-1 | 阶段通过 | ISSUE-007 / APP-M1 | 后台77、前端9、旧页7、治理12、实际HTTP和GUI；Word视觉待验收 |
| D-089 | 2026-10-11 | [007同步记录](governance/ISSUE-007-sync.md) | 治理 | reference-members-1 | 已核对 | ISSUE-007 / APP-M1 | 三件套、337项看板、T07/T14～16和真实未完成范围对齐 |
| D-090 | 2026-10-10 | [独立边界回归](../tests/backend/test_reference_boundaries.py) | 验证代码 | reference-1 | 25项通过 | ISSUE-007 / APP-M1 | 模型路由、坏上传恢复、时区、候选失效与证据重新确认 |
| D-091 | 2026-10-11 | [主流程HTTP工具](../backend/bid-core/smoke_reference.py) | 验证工具 | reference-1 | 实际端口通过 | ISSUE-007 / APP-M1 | 仅本机合成项目，两册内容与草稿准备 |
| D-092 | 2026-10-11 | [前端日期回归](../tests/frontend/project-form.test.mjs) | 验证代码 | reference-members-1 | 4项通过 | ISSUE-007 / APP-M1 | 北京时间边界、空字段与旧基本表单已读依据 |
| D-093 | 2026-10-10 | [前端恢复回归](../tests/frontend/editor-recovery.test.mjs) | 验证代码 | reference-1 | 3项通过 | ISSUE-007 / APP-M1 | 核对期间版本/草稿变化拒绝，新草稿顺序 |
| D-094 | 2026-10-10 | [前端接口回归](../tests/frontend/api.test.mjs) | 验证代码 | reference-1 | 3项通过 | ISSUE-007 / APP-M1 | 两代错误、失败任务版本详情和移除请求保护 |
| D-095 | 2026-10-11 | [输入摘要](../backend/bid-core/icg_demo/input_snapshot.py) | 代码 | reference-sla-1 | 边界通过 | ISSUE-007 / APP-M1 | 旧建议、新候选和检查使用同一已提交输入摘要 |
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
| D-115 | 2026-10-11 | [服务承诺页面](../frontend/web/src/SlaPages.tsx) | 页面代码 | reference-sla-1 | 真实操作通过 | ISSUE-007 / APP-M1-T09～T11 | 模板维护、数值矩阵和承诺函下载 |
| D-116 | 2026-10-10 | [服务承诺表单](../frontend/web/src/sla-form.ts) | 代码 | reference-sla-1 | 行为通过 | ISSUE-007 / APP-M1-T09～T11 | 空值/零、数值、完整变量和单位插入 |
| D-117 | 2026-10-10 | [服务承诺HTTP工具](../backend/bid-core/smoke_sla.py) | 验证工具 | reference-sla-1 | 最终服务通过 | ISSUE-007 / APP-M1-T09～T11 | 仅本机合成项目、能力/事实门禁和真实下载 |
| D-118 | 2026-10-10 | [服务承诺独立测试](../tests/backend/test_sla.py) | 验证代码 | reference-sla-1 | 42项通过 | ISSUE-007 / APP-M1-T09～T11 | 单位、权限、来源/模板、出口、实际Word及本次确认依据 |
| D-119 | 2026-10-10 | [服务承诺前端测试](../tests/frontend/sla-form.test.mjs) | 验证代码 | reference-sla-1 | 4项通过 | ISSUE-007 / APP-M1-T09～T11 | 输入与选区/冲突单位，前端合计13项 |
| D-120 | 2026-10-10 | [写作输入验收](testing/2026-10-10-writing-input.md) | 验证 | reference-writing-1 | 本地通过 | ISSUE-007 / APP-M1-T12、T13 | 真实HTTP、页面、变量Word、当前限制 |
| D-121 | 2026-10-10 | [T12交付](delivery/APP-M1-T12.md) | 交付 | reference-writing-1 | 已本地验收 | ISSUE-007 / APP-M1-T12、T13 | 本章事实输入与保护限定子集 |
| D-122 | 2026-10-10 | [T13交付](delivery/APP-M1-T13.md) | 交付 | reference-writing-1 | 已本地验收 | ISSUE-007 / APP-M1-T12、T13 | 本章方案与候选来源页面子集 |
| D-123 | 2026-10-10 | [T12代码解释](code/APP-M1-T12.md) | 代码 | reference-writing-1 | 当前 | ISSUE-007 / APP-M1-T12、T13 | 共享组装器、快照与变量 |
| D-124 | 2026-10-10 | [T13代码解释](code/APP-M1-T13.md) | 代码 | reference-writing-1 | 当前 | ISSUE-007 / APP-M1-T12、T13 | 方案/当前输入/历史快照与事实插入 |
| D-125 | 2026-10-11 | [实际写作输入](../backend/bid-core/icg_demo/generation_context.py) | 后端 | reference-writing-1 | 当前 | ISSUE-007 / APP-M1-T12、T13 | 来源当前性、选定事实、输出变量保护 |
| D-126 | 2026-10-10 | [写作HTTP验收](../backend/bid-core/smoke_writing.py) | 验证 | reference-writing-1 | 已执行 | ISSUE-007 / APP-M1-T12、T13 | 本机合成端口、快照/变量/两册/失效 |
| D-127 | 2026-10-11 | [独立写作回归](../tests/backend/test_generation_context.py) | 验证 | reference-writing-1 | 已执行 | ISSUE-007 / APP-M1-T12、T13 | 捕获入参、权限/来源/变量/并发反例 |
| D-128 | 2026-10-11 | [本章方案页面](../frontend/web/src/WritingPlanReview.tsx) | 前端 | reference-writing-1 | 当前 | ISSUE-007 / APP-M1-T12、T13 | 负责人事实选择、要点与字数确认 |
| D-129 | 2026-10-11 | [输入快照页面](../frontend/web/src/WritingInputPreview.tsx) | 前端 | reference-writing-1 | 当前 | ISSUE-007 / APP-M1-T12、T13 | 当前准备输入与历史来源分别显示 |
| D-130 | 2026-10-11 | [写作页面函数](../frontend/web/src/writing-input.ts) | 前端 | reference-writing-1 | 当前 | ISSUE-007 / APP-M1-T12、T13 | 方案恢复、失效与事实变量插入 |
| D-131 | 2026-10-11 | [写作函数回归](../frontend/web/tests/writing-input.test.mjs) | 验证 | reference-members-1 | 9项通过 | ISSUE-007 / APP-M1-T12、T13 | 本章输入、独立确认、逐行/范围旧表单和依赖变化反例 |
| D-132 | 2026-10-10 | [写入来源独立回归](../tests/backend/test_candidate_write_guard.py) | 验证 | reference-writing-1 | 已执行 | ISSUE-007 / APP-M1-T12、T13 | 候选采纳后/草稿源改、事务拒绝、幂等与旧demo兼容 |
| D-133 | 2026-10-10 | [编辑来源保护函数](../frontend/web/src/editing-source.ts) | 前端 | reference-writing-1 | 当前 | ISSUE-007 / APP-M1-T13 | 草稿/候选原基准、显式重新核对及恢复 |
| D-134 | 2026-10-10 | [编辑来源回归](../frontend/web/tests/editing-source.test.mjs) | 验证 | reference-writing-1 | 已执行 | ISSUE-007 / APP-M1-T13 | 5项加载、恢复、写入与期间变动保护 |
| D-135 | 2026-10-11 | [成员分工验收](testing/2026-10-10-project-assignments.md) | 验证 | reference-members-1 | 限定任务本地验收 | ISSUE-007 / APP-M1-T14、T15 | 210后台、36前端、真实HTTP/GUI及最终两册内容；正式版式未验收 |

| D-136 | 2026-10-11 | [任务拆分交付](delivery/APP-M1-T07.md) | 交付 | icg-task-plan-1 | 本地done | ISSUE-007 / APP-M1-T07 | 259后续卡planned，直接原WBS/页面/规则映射核对 |
| D-137 | 2026-10-11 | [成员分工交付](delivery/APP-M1-T14.md) | 交付 | reference-members-1 | 本地done | ISSUE-007 / APP-M1-T14 | 真实人员范围、团队冲突和交接 |
| D-138 | 2026-10-11 | [成员代码解释](code/APP-M1-T14.md) | 说明 | reference-members-1 | 当前 | ISSUE-007 / APP-M1-T14 | 设置页面、角色范围、事务保存、草稿私有 |
| D-139 | 2026-10-11 | [逐章确认交付](delivery/APP-M1-T15.md) | 交付 | reference-members-1 | 本地done | ISSUE-007 / APP-M1-T15 | 独立方案/权限、真实旧表单核对和两册 |
| D-140 | 2026-10-11 | [逐章代码解释](code/APP-M1-T15.md) | 说明 | reference-members-1 | 当前 | ISSUE-007 / APP-M1-T15 | 单章确认依赖、逐次生成权限和旧行保护 |
| D-141 | 2026-10-12 | [完整后续任务](tasks/APP-M2.md) | 实施计划 | icg-task-plan-1 | T008 in-review，其余按卡 | ISSUE-007 / APP-M1-T07 / APP-M2；ISSUE-012 | 每卡来源/接口核对/权限失败/依赖验收与交付；T008本轮只记离线CI |
| D-142 | 2026-10-12 | [逐页逐规则映射](testing/icg-task-mapping.md) | 范围核对 | icg-task-map-1 | 已核对范围，功能未完成 | ISSUE-007 / APP-M1-T07；ISSUE-012 | 190原M1～M6 WBS、47组/44规则；T008状态改为 in-review |
| D-143 | 2026-10-11 | [项目范围核对](../backend/bid-core/icg_demo/project_access.py) | 代码 | reference-members-1 | 回归通过 | ISSUE-007 / APP-M1-T14 | 公司操作角色与项目成员/分册/本节共同判定 |
| D-144 | 2026-10-11 | [团队交接](../backend/bid-core/icg_demo/project_team.py) | 代码 | reference-members-1 | 回归通过 | ISSUE-007 / APP-M1-T14、T15 | 分工资格、交接理由、旧锁撤销和每人草稿保留 |
| D-145 | 2026-10-11 | [真实成员HTTP](../backend/bid-core/smoke_members.py) | 验证工具 | reference-members-1 | 实际端口通过 | ISSUE-007 / APP-M1-T14、T15 | 合成多账号独立确认/交接/私有稿与两册真实下载 |
| D-146 | 2026-10-11 | [成员权限独立回归](../tests/backend/test_project_assignments.py) | 验证 | reference-members-1 | 42项通过 | ISSUE-007 / APP-M1-T14、T15 | 范围、调用中撤权、缓存请求和单章确认相关依赖 |
| D-147 | 2026-10-11 | [项目设置页面](../frontend/web/src/ProjectSettingsPage.tsx) | 前端 | reference-members-1 | 实际页面通过 | ISSUE-007 / APP-M1-T14 | 示例左锚点、分工和基本/团队旧表单分别保护 |
| D-148 | 2026-10-11 | [页面分工函数](../frontend/web/src/project-team.ts) | 前端 | reference-members-1 | 当前 | ISSUE-007 / APP-M1-T14、T15 | 明确后台权限、分工资格、范围与团队已读依据 |
| D-149 | 2026-10-11 | [分工页面回归](../tests/frontend/project-team.test.mjs) | 验证 | reference-members-1 | 8项通过 | ISSUE-007 / APP-M1-T14、T15 | 角色范围、可空参与、旧团队表单和撤权保留 |
| D-150 | 2026-10-11 | [资料旧表单缺陷](../issues/ISSUE-008.md) | Bug | library-basis-1 | closed（本地验收） | ISSUE-008 / APP-M1-T16 | 绑定已读依据、冲突保留、明确核对载入 |
| D-151 | 2026-10-11 | [资料及模板保护交付](delivery/APP-M1-T16.md) | 交付 | library-basis-1 | 本地done | ISSUE-008 / APP-M1-T16 | 限定保护通过，完整C01/C06仍待实现 |
| D-152 | 2026-10-11 | [资料及模板代码解释](code/APP-M1-T16.md) | 说明 | library-basis-1 | 当前 | ISSUE-008 / APP-M1-T16 | 原依据、对应集合版本、真实重读及公司身份 |
| D-153 | 2026-10-11 | [资料及模板验证](testing/2026-10-11-library-basis.md) | 验证 | library-basis-1 | 本地通过 | ISSUE-008 / APP-M1-T16 | 后台229、前端58、构建、实际GUI与6截图；局限分列 |
| D-154 | 2026-10-11 | [资料依据函数](../frontend/web/src/library-review.ts) | 前端 | library-basis-1 | 回归通过 | ISSUE-008 / APP-M1-T16 | 真正已读依据、成对读取及公司/账号会话 |
| D-155 | 2026-10-11 | [模板依据函数](../frontend/web/src/template-review.ts) | 前端 | library-basis-1 | 回归通过 | ISSUE-008 / APP-M1-T16 | 完整指标数组与核对提案真实再读 |
| D-156 | 2026-10-11 | [资料页面函数回归](../frontend/web/tests/library-review.test.mjs) | 验证 | library-basis-1 | 12项通过 | ISSUE-008 / APP-M1-T16 | 旧依据、搜索、删除、读取失败与迟到旧公司响应 |
| D-157 | 2026-10-11 | [模板页面函数回归](../frontend/web/tests/template-review.test.mjs) | 验证 | library-basis-1 | 10项通过 | ISSUE-008 / APP-M1-T16 | 指标变化、二次读取、版本配对与切公司 |
| D-158 | 2026-10-11 | [资料真实HTTP回归](../tests/backend/test_library_basis.py) | 验证 | library-basis-1 | 13项通过 | ISSUE-008 / APP-M1-T16 | 原版本/重试/幂等/权限及完整仓储无副作用 |
| D-159 | 2026-10-11 | [模板真实HTTP回归](../tests/backend/test_sla_template_basis.py) | 验证 | library-basis-1 | 6项通过 | ISSUE-008 / APP-M1-T16 | 旧指标数组不能覆盖，明确核对后的请求成功 |
| D-160 | 2026-10-12 | [共同底座Issue](../issues/ISSUE-009.md) | 实施 | layout-review-1 | in-review | ISSUE-009 / APP-M2-T001 | 布局/路由/离开保护已提交复核；done 留给项目经理 |
| D-161 | 2026-10-11 | [可信会话与导航契约](architecture/application-session-contract.md) | 契约 | application-foundation-1 | 当前实施 | ISSUE-009 / APP-M2-T001 | 后台身份/资源读取与三演示角色兼容边界 |
| D-162 | 2026-10-12 | [共同底座阶段交付](delivery/APP-M2-T001.md) | 交付 | layout-review-1 | in-review | ISSUE-009 / APP-M2-T001 | 会话阶段保留；布局切片提交复核，未标 done |
| D-163 | 2026-10-12 | [会话与守卫代码解释](code/APP-M2-T001.md) | 说明 | layout-review-1 | in-review | ISSUE-009 / APP-M2-T001 | 会话读取顺序，以及 ProLayout、地址和离开保护 |
| D-164 | 2026-10-11 | [共同底座阶段验证](testing/2026-10-11-application-session.md) | 验证 | application-foundation-1 | 阶段通过 | ISSUE-009 / APP-M2-T001 | 后台262、前端72、真实会话16、GUI/两册内容；独立复核通过 |
| D-165 | 2026-10-11 | [后台会话权限](../backend/bid-core/icg_demo/session_navigation.py) | 后台 | application-foundation-1 | 阶段实现 | ISSUE-009 / APP-M2-T001 | 当前仓储身份、八角色定义及最小项目权限 |
| D-166 | 2026-10-11 | [后台会话专项](../tests/backend/test_application_session.py) | 验证 | application-foundation-1 | 33项通过 | ISSUE-009 / APP-M2-T001 | 身份重读、参数拒绝、项目边界及无正文 |
| D-167 | 2026-10-11 | [页面授权读取函数](../frontend/web/src/session-navigation.ts) | 前端 | application-foundation-1 | 阶段实现 | ISSUE-009 / APP-M2-T001 | 服务端导航/动作与项目读取先后 |
| D-168 | 2026-10-11 | [页面会话专项](../frontend/web/tests/application-session.test.mjs) | 验证 | application-foundation-1 | 14项通过 | ISSUE-009 / APP-M2-T001 | 未授权零业务读取、集合成对、撤权/拒绝/旧响应保护 |
| D-169 | 2026-10-11 | [同后台项目截图](testing/assets/icg-session-product-overview.jpg) | 证据 | application-foundation-1 | 实际GUI | ISSUE-009 / APP-M2-T001 | 合成项目确认、两册提交及内部稿，原图见ICG来源 |
| D-170 | 2026-10-11 | [两册导出页截图](testing/assets/icg-session-two-volume-export.jpg) | 证据 | application-foundation-1 | 实际GUI | ISSUE-009 / APP-M2-T001 | 有效/过期记录，实际内部Word尚未正式版式验收 |
| D-171 | 2026-10-11 | [只读导航截图](testing/assets/icg-session-readonly-navigation.jpg) | 证据 | application-foundation-1 | 实际GUI | ISSUE-009 / APP-M2-T001 | 同项目只读，无写作/管理/导出入口 |
| D-172 | 2026-10-11 | [无权快捷入口截图](testing/assets/icg-session-readonly-denied.jpg) | 证据 | application-foundation-1 | 实际GUI | ISSUE-009 / APP-M2-T001 | 403保留原内容并暂停写入，不误称整个项目不可见 |
| D-173 | 2026-10-12 | [QA复跑Issue](../issues/ISSUE-013.md) | 审查 | qa-rerun-1 | closed | ISSUE-013 / REV-M0-T02 | 会话实时HTTP入库与独立复跑 |
| D-174 | 2026-10-12 | [QA独立复跑记录](testing/2026-10-12-qa-rerun.md) | 验证 | qa-rerun-1 | 本地通过 | ISSUE-013 / REV-M0-T02 | 262/72/构建/冒烟/会话15，Node 24要求与局限 |
| D-175 | 2026-10-12 | [QA复跑交付](delivery/REV-M0-T02.md) | 交付 | qa-rerun-1 | 已本地验收 | ISSUE-013 / REV-M0-T02 | 实际文件、验证与剩余 |
| D-176 | 2026-10-12 | [会话脚本代码解释](code/REV-M0-T02.md) | 说明 | qa-rerun-1 | 已本地验收 | ISSUE-013 / REV-M0-T02 | 启动顺序、检查项与限制 |
| D-177 | 2026-10-12 | [会话实时HTTP脚本](../tests/backend/session_live_http.py) | 验证 | qa-rerun-1 | 15项通过 | ISSUE-013 / REV-M0-T02 | 自启空闲端口，合成数据，默认pytest不收集 |
| D-178 | 2026-10-12 | [T06验收计划Issue](../issues/ISSUE-015.md) | 审查 | t06-plan-2 | in-progress | ISSUE-015 / REV-M0-T03 | 计划编制，T06未验收 |
| D-179 | 2026-10-12 | [APP-M1-T06验收计划](testing/2026-10-12-app-m1-t06-acceptance-plan.md) | 验证 | t06-plan-1 | 待评审 | ISSUE-015 / REV-M0-T03 | 端到端/Word/角色/权限/过期映射与缺口；已评审 |
| D-180 | 2026-10-12 | [T06计划交付](delivery/REV-M0-T03.md) | 交付 | t06-plan-1 | 已本地验收 | ISSUE-015 / REV-M0-T03 | 无代码；缺口汇总 |
| D-181 | 2026-10-12 | [T06贯通冒烟与渲染记录](testing/2026-10-12-t06-smoke-word-render.md) | 验证 | t06-plan-2 | 本地通过 | ISSUE-015 / REV-M0-T04 | smoke_t06 12/12、Word结构与LibreOffice渲染、W1～W4 |
| D-182 | 2026-10-12 | [贯通冒烟交付](delivery/REV-M0-T04.md) | 交付 | t06-plan-2 | 已本地验收 | ISSUE-015 / REV-M0-T04 | 实际文件与剩余缺口 |
| D-183 | 2026-10-12 | [贯通冒烟代码解释](code/REV-M0-T04.md) | 说明 | t06-plan-2 | 已本地验收 | ISSUE-015 / REV-M0-T04 | 启动顺序、核对项与局限 |
| D-184 | 2026-10-12 | [T06贯通冒烟脚本](../backend/bid-core/smoke_t06.py) | 验证 | t06-plan-2 | 12项通过 | ISSUE-015 / REV-M0-T04 | 自启空闲端口，合成数据，退出0/1 |
| D-185 | 2026-10-12 | [技术册渲染截图](testing/assets/t06-word-technical-render.png) | 证据 | t06-plan-2 | LibreOffice渲染 | ISSUE-015 / REV-M0-T04 | 内部稿首页，无标题样式 |
| D-186 | 2026-10-12 | [SLA表格渲染截图](testing/assets/t06-word-sla-table-render.png) | 证据 | t06-plan-2 | LibreOffice渲染 | ISSUE-015 / REV-M0-T04 | 表格不越界，表头无区分 |
| D-187 | 2026-10-12 | [离线CI Issue](../issues/ISSUE-012.md) | 工作流 | offline-ci-1 | in-review | ISSUE-012 / APP-M2-T008 | 三个并行作业在 cf2c2a1 通过；QA已签署，done待项目经理 |
| D-188 | 2026-10-12 | [离线CI交付](delivery/APP-M2-T008.md) | 交付 | offline-ci-1 | in-review | ISSUE-012 / APP-M2-T008 | 实际作业、计数和 buildTheme 未执行；done待项目经理 |
| D-189 | 2026-10-12 | [离线CI代码解释](code/APP-M2-T008.md) | 说明 | offline-ci-1 | 当前 | ISSUE-012 / APP-M2-T008 | 作业顺序、缓存、会话脚本与smoke_t06分步 |
| D-190 | 2026-10-12 | [离线CI验证](testing/2026-10-12-offline-ci.md) | 验证 | offline-ci-1 | 本地通过 | ISSUE-012 / APP-M2-T008 | 运行 38200746746：262/15/12/72/35；不含soffice |
| D-191 | 2026-10-12 | [离线CI同步](governance/ISSUE-012-sync.md) | 治理 | offline-ci-1 | 已核对 | ISSUE-012 / APP-M2-T008 | 补 PROJECT_BRIEF 的日期与计数；T008 改回 in-review |
| D-192 | 2026-10-12 | [离线CI工作流](../.github/workflows/offline-check.yml) | 工程 | offline-ci-1 | in-review | ISSUE-012 / APP-M2-T008 | ubuntu-24.04；checkout/setup-node/setup-python v7，pnpm/action-setup v6；无密钥 |
| D-193 | 2026-10-12 | [模型与数据库待决](../issues/ISSUE-010.md) | 决策 | model-choice-2 | blocked | ISSUE-010 / AI-01 | 业务库已决定为 MySQL 8；向量库和模型仍待决 |
| D-194 | 2026-10-12 | [兼容适配器事项](../issues/ISSUE-011.md) | 变更 | openai-adapter-3 | closed | ISSUE-011 / AI-02 | 项目经理于 10-12 12:10 在 QA 签署后确认；未合入 |
| D-195 | 2026-10-12 | [模型准备任务](tasks/AI-M0.md) | 实施 | retrieval-skeleton-1 | 当前 | ISSUE-010 / AI-01；ISSUE-011 / AI-02；ISSUE-016 / AI-03 | AI-01 blocked，AI-02为done，AI-03为in-review |
| D-196 | 2026-10-12 | [待决登记交付](delivery/AI-01.md) | 交付 | model-choice-1 | blocked | ISSUE-010 / AI-01 | 只登记选项，不把建议写成决定 |
| D-197 | 2026-10-12 | [适配器交付](delivery/AI-02.md) | 交付 | openai-adapter-3 | done | ISSUE-011 / AI-02 | 项目经理已确认；真实端点仍未接通 |
| D-198 | 2026-10-12 | [适配器代码解释](code/AI-02.md) | 说明 | openai-adapter-1 | 当前 | ISSUE-011 / AI-02 | 环境变量、请求、重试和敏感门禁 |
| D-199 | 2026-10-12 | [适配器验证](testing/2026-10-12-openai-compatible-model.md) | 验证 | openai-adapter-1 | 本地通过 | ISSUE-011 / AI-02 | 契约30项；全后台回归通过；无真实端点 |
| D-200 | 2026-10-12 | [010同步记录](governance/ISSUE-010-sync.md) | 治理 | model-choice-2 | 已核对 | ISSUE-010 / AI-01 | 补登 PROJECT_BRIEF；业务库决定为 MySQL 8 |
| D-201 | 2026-10-12 | [011同步记录](governance/ISSUE-011-sync.md) | 治理 | openai-adapter-3 | 已核对 | ISSUE-011 / AI-02 | 补登 PROJECT_BRIEF；项目经理确认后为 done / closed |
| D-202 | 2026-10-12 | [兼容模型适配器](../backend/bid-core/icg_demo/openai_model.py) | 后台 | openai-adapter-1 | 契约通过 | ISSUE-011 / AI-02 | 显式启用的 chat completions，失败不伪装成功 |
| D-203 | 2026-10-12 | [适配器契约测试](../tests/backend/test_openai_compatible_model.py) | 验证 | openai-adapter-1 | 31项通过 | ISSUE-011 / AI-02；ISSUE-016 旁路 | 假传输覆盖成功、失败和敏感门禁；v1 生成失败为冻结错误体 |
| D-204 | 2026-10-12 | [QA签署复核](testing/2026-10-12-qa-signoff.md) | 验证 | qa-rerun-2 | 本地通过 | ISSUE-013 / REV-M0-T05 | T008与AI-02签署：Actions三次成功、本地292/30/72/35，S1～S5 |
| D-205 | 2026-10-12 | [签署复核交付](delivery/REV-M0-T05.md) | 交付 | qa-rerun-2 | 已本地验收 | ISSUE-013 / REV-M0-T05 | 无代码；结论与缺口 |
| D-206 | 2026-10-12 | [ProLayout依赖Issue](../issues/ISSUE-014.md) | 版本 | pro-layout-7.22.7 | in-review | ISSUE-014 / APP-M2-T001 | 只增加 pro-layout 7.22.7；1334.42 kB 到 1564.53 kB |
| D-207 | 2026-10-12 | [布局地址复核](testing/2026-10-12-prolayout-routes.md) | 验证 | layout-review-1 | in-review | ISSUE-009 / ISSUE-014 / APP-M2-T001 | 前端77、后台293、构建体积；无三断点截图 |
| D-208 | 2026-10-12 | [014同步记录](governance/ISSUE-014-sync.md) | 治理 | pro-layout-7.22.7 | 已核对 | ISSUE-014 / APP-M2-T001 | 基线未改的句子和 in-review 计数 |
| D-209 | 2026-10-12 | [产品外壳](../frontend/web/src/AppShell.tsx) | 前端 | pro-layout-7.22.7 | in-review | ISSUE-009 / APP-M2-T001 | ProLayout 侧栏、顶栏和菜单链接 |
| D-210 | 2026-10-12 | [页面地址](../frontend/web/src/app-route.ts) | 前端 | layout-review-1 | in-review | ISSUE-009 / APP-M2-T001 | 全局路径、项目页签和登录回原地址 |
| D-211 | 2026-10-12 | [离开保护](../frontend/web/src/leave-guard.ts) | 前端 | layout-review-1 | in-review | ISSUE-009 / APP-M2-T001 | 未保存时保留地址；取消不离开 |
| D-212 | 2026-10-12 | [地址与离开测试](../frontend/web/tests/app-navigation.test.mjs) | 验证 | layout-review-1 | 5项通过 | ISSUE-009 / APP-M2-T001 | 需 Node 22.18+ 或 Node 24；本轮用 24.21.0 |
| D-213 | 2026-10-12 | [检索骨架事项](../issues/ISSUE-016.md) | 变更 | retrieval-skeleton-1 | in-review | ISSUE-016 / AI-03 | 内存检索口与三条证据候选；不连接 MySQL |
| D-214 | 2026-10-12 | [检索骨架交付](delivery/AI-03.md) | 交付 | retrieval-skeleton-1 | in-review | ISSUE-016 / AI-03 | 契约与全后台结果；开发者不标 done |
| D-215 | 2026-10-12 | [检索骨架代码解释](code/AI-03.md) | 说明 | retrieval-skeleton-1 | 当前 | ISSUE-016 / AI-03 | 三条路径、公司过滤和失败原因不含正文 |
| D-216 | 2026-10-12 | [检索骨架验证](testing/2026-10-12-evidence-candidates.md) | 验证 | retrieval-skeleton-1 | 本地通过 | ISSUE-016 / AI-03 | 契约7项；全后台309项；v1失败体已核对；无新错误码 |
| D-217 | 2026-10-12 | [016同步记录](governance/ISSUE-016-sync.md) | 治理 | retrieval-skeleton-1 | 已核对 | ISSUE-016 / AI-03 | 344项20done、2in-review、7in-progress；PROJECT_BRIEF已登记 |
| D-218 | 2026-10-12 | [检索实现](../backend/bid-core/icg_demo/retrieval.py) | 后台 | retrieval-skeleton-1 | 契约通过 | ISSUE-016 / AI-03 | 内存嵌入、重排、向量表和证据候选 |
| D-219 | 2026-10-12 | [证据候选测试](../tests/backend/test_evidence_candidates.py) | 验证 | retrieval-skeleton-1 | 7项通过 | ISSUE-016 / AI-03 | 合成数据覆盖公司隔离和历史不可附着 |
| D-220 | 2026-10-12 | [检索协议](../backend/bid-core/icg_demo/ports.py) | 后台 | retrieval-skeleton-1 | 当前 | ISSUE-016 / AI-03 | 增加嵌入、重排和向量检索协议 |
| D-221 | 2026-10-12 | [错误体交付](delivery/BE-M0-T02.md) | 交付 | contract-1 | in-review | ISSUE-005 / BE-M0-T02 | v1错误体、一对一状态和两处收口；done待QA签收 |
| D-222 | 2026-10-12 | [错误体代码解释](code/BE-M0-T02.md) | 说明 | contract-1 | 当前 | ISSUE-005 / BE-M0-T02 | 状态表、追踪头和解析失败的原状态 |
| D-223 | 2026-10-12 | [幂等交付](delivery/BE-M0-T03.md) | 交付 | contract-1 | in-review | ISSUE-005 / BE-M0-T03 | 24小时回执、失败不保存和旧正文字段 |
| D-224 | 2026-10-12 | [幂等代码解释](code/BE-M0-T03.md) | 说明 | contract-1 | 当前 | ISSUE-005 / BE-M0-T03 | 范围、指纹、过期和2048条上限 |
| D-225 | 2026-10-12 | [错误体与幂等验证](testing/2026-10-12-error-idempotency.md) | 验证 | contract-1 | 已执行 | ISSUE-005 / BE-M0-T02、T03 | 后台回归和141个code的冻结表；含MODEL_UNAVAILABLE=502 |
| D-226 | 2026-10-12 | [005同步表](governance/ISSUE-005-sync.md) | 治理 | g1.1 | 本轮记录 | ISSUE-005 | 基线逐行记录；PRD、ROADMAP、ARCHITECTURE未改 |
| D-227 | 2026-10-12 | [错误状态表](../backend/bid-core/icg_demo/errors.py) | 后台 | contract-1 | 当前 | ISSUE-005 / BE-M0-T02 | 141个code的唯一HTTP状态及OpenAPI补充 |
| D-228 | 2026-10-12 | [幂等回执](../backend/bid-core/icg_demo/idempotency.py) | 后台 | contract-1 | 当前 | ISSUE-005 / BE-M0-T03 | 24小时、上限和失败不登记 |
| D-229 | 2026-10-12 | [错误与幂等回归](../tests/backend/test_error_idempotency.py) | 验证 | contract-1 | 当前 | ISSUE-005 / BE-M0-T02、T03 | 错误体、重放、冲突、过期、导出一致和v1模型失败 |
| D-230 | 2026-10-12 | [路由分包Issue](../issues/ISSUE-020.md) | 变更 | route-chunks-1 | in-review | ISSUE-020 / APP-M2-T001 | 首屏主块 315.94 kB，低于 1334.42 kB；未标 done |
| D-231 | 2026-10-12 | [路由分包复核](testing/2026-10-12-route-chunks.md) | 验证 | route-chunks-1 | in-review | ISSUE-020 / APP-M2-T001 | 全部分包前后体积；前端 78 pass、0 fail |
| D-232 | 2026-10-12 | [020同步记录](governance/ISSUE-020-sync.md) | 治理 | route-chunks-1 | 已核对 | ISSUE-020 / APP-M2-T001 | 基线未改；不新增任务 |
| D-233 | 2026-10-12 | [路由分包交付](delivery/ISSUE-020.md) | 交付 | route-chunks-1 | in-review | ISSUE-020 / APP-M2-T001 | 动态 import 与 Suspense；后台未改 |
| D-234 | 2026-10-12 | [路由分包代码解释](code/ISSUE-020.md) | 说明 | route-chunks-1 | in-review | ISSUE-020 / APP-M2-T001 | 加载顺序和离开保护仍在 App |
| D-235 | 2026-10-12 | [路由加载器](../frontend/web/src/route-loaders.ts) | 前端 | route-chunks-1 | in-review | ISSUE-020 / APP-M2-T001 | 动态 import 并缓存进行中的请求 |
| D-236 | 2026-10-12 | [懒加载页面](../frontend/web/src/lazy-routes.tsx) | 前端 | route-chunks-1 | in-review | ISSUE-020 / APP-M2-T001 | React.lazy 外壳和各页 |
| D-237 | 2026-10-12 | [分包约束测试](../frontend/web/tests/route-chunks.test.mjs) | 验证 | route-chunks-1 | 1项通过 | ISSUE-020 / APP-M2-T001 | 入口不再静态引入外壳和页面 |
| D-238 | 2026-10-12 | [内网部署草案](operations/intranet-deployment-plan.md) | 运维 | intranet-plan-1 | in-review | ISSUE-017 / OPS-M0-T02 | MySQL 8；单 worker 单副本，多副本 blocked 在 ISSUE-018 |
| D-239 | 2026-10-12 | [内网部署 Issue](../issues/ISSUE-017.md) | 决策 | intranet-plan-1 | in-review | ISSUE-017 / OPS-M0-T02 | 草案复核中；done 待项目经理 |
| D-240 | 2026-10-12 | [内网部署交付](delivery/OPS-M0-T02.md) | 交付 | intranet-plan-1 | in-review | ISSUE-017 / OPS-M0-T02 | 无代码；未创建环境 |
| D-241 | 2026-10-12 | [内网部署核对](testing/2026-10-12-intranet-deploy-plan.md) | 验证 | intranet-plan-1 | 文档核对 | ISSUE-017 / OPS-M0-T02 | 对照现有入口；未连接 MySQL 或内网 |
| D-243 | 2026-10-12 | [BE-M0-T02/T03签署复核](testing/2026-10-12-be-m0-t02-t03-signoff.md) | 验证 | qa-signoff-be | 本地通过 | ISSUE-013 / REV-M0-T07 | 308/15/12/77/35、探针47/47、Actions 38203448527成功 |
| D-244 | 2026-10-12 | [BE签署复核交付](delivery/REV-M0-T07.md) | 交付 | qa-signoff-be | 已本地验收 | ISSUE-013 / REV-M0-T07 | 仅QA探针脚本；结论与Q1缺口 |
| D-245 | 2026-10-12 | [E2E Issue](../issues/ISSUE-019.md) | 审查 | e2e-1 | in-review | ISSUE-019 / REV-M0-T06 | Playwright仅测试依赖 |
| D-246 | 2026-10-12 | [E2E与T001签署](testing/2026-10-12-e2e-t001-signoff.md) | 验证 | e2e-1 | 本地执行 | ISSUE-019 / REV-M0-T06；ISSUE-013 / REV-M0-T08 | 11项E2E、T001签署不通过与D1～D6、CI建议 |
| D-247 | 2026-10-12 | [E2E交付](delivery/REV-M0-T06.md) | 交付 | e2e-1 | in-review | ISSUE-019 / REV-M0-T06 | 命令、覆盖与剩余 |
| D-248 | 2026-10-12 | [E2E代码解释](code/REV-M0-T06.md) | 说明 | e2e-1 | in-review | ISSUE-019 / REV-M0-T06 | 启动顺序与用例思路 |
| D-249 | 2026-10-12 | [T001签署交付](delivery/REV-M0-T08.md) | 交付 | qa-rerun-3 | in-review | ISSUE-013 / REV-M0-T08 | 签署结论与缺陷 |
| D-250 | 2026-10-12 | [E2E配置](../frontend/web/e2e/playwright.config.ts) | 验证 | e2e-1 | in-review | ISSUE-019 / REV-M0-T06 | Chromium、自启内存后台 |
| D-251 | 2026-10-12 | [E2E用例](../frontend/web/e2e/app-shell.spec.ts) | 验证 | e2e-1 | 11项按预期 | ISSUE-019 / REV-M0-T06 | 断点截图、离开确认、前进后退、已知缺陷 |
| D-252 | 2026-10-12 | [工作台1680截图](testing/assets/e2e-workbench-1680.png) | 证据 | e2e-1 | E2E截图 | ISSUE-019 / REV-M0-T06 | D3卡片不可读、D4顶栏落入侧栏 |
| D-253 | 2026-10-12 | [编辑台1280截图](testing/assets/e2e-editor-1280.png) | 证据 | e2e-1 | E2E截图 | ISSUE-019 / REV-M0-T06 | 编辑台三栏与暗色控件 |
| D-254 | 2026-10-12 | [概览1440截图](testing/assets/e2e-overview-1440.png) | 证据 | e2e-1 | E2E截图 | ISSUE-019 / REV-M0-T06 | 项目概览布局 |
| D-242 | 2026-10-12 | [017同步记录](governance/ISSUE-017-sync.md) | 治理 | intranet-plan-1 | 已核对 | ISSUE-017 / OPS-M0-T02 | 三件套与 brief 不改正文；过时的 T008 用词留给项目经理下一次基线同步 |
| D-250 | 2026-10-12 | [T124阻塞事项](../issues/ISSUE-022.md) | 变更 | t124-blocked-1 | blocked | ISSUE-022 / APP-M2-T124 | 依赖未满足，不改模型输入 |
| D-251 | 2026-10-12 | [T124阻塞交付](delivery/APP-M2-T124.md) | 交付 | t124-blocked-1 | blocked | ISSUE-022 / APP-M2-T124 | 无产品代码；不标 done |
| D-252 | 2026-10-12 | [T124无代码说明](code/APP-M2-T124.md) | 说明 | t124-blocked-1 | 当前 | ISSUE-022 / APP-M2-T124 | 整章输入保持；REF-08 仍适用 |
| D-253 | 2026-10-12 | [T124依赖核对](testing/2026-10-12-t124-dependencies.md) | 验证 | t124-blocked-1 | 只读 | ISSUE-022 / APP-M2-T124 | T15 具备；T078、T114 和三个 operationId 不具备 |
| D-254 | 2026-10-12 | [022同步记录](governance/ISSUE-022-sync.md) | 治理 | t124-blocked-1 | 已核对 | ISSUE-022 / APP-M2-T124 | 354项265planned、50blocked；PRD 与 ARCHITECTURE 未改 |

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
| 2026-10-10 | ISSUE-007 / APP-M1-T14、T15 | 登记成员/分册/章节分工、独立确认实施与待执行验收，未计完成 |

| 2026-10-11 | ISSUE-007 / APP-M1-T07、T14、T15 | 259后续卡、成员与逐章确认本地交付、210/36真实验证和6截图、旧表单保护；336项状态对齐 |

| 2026-10-11 | ISSUE-008 / APP-M1-T16 | 资料及公司模板旧表单保护本地交付，后台229/前端58、实际页面和6截图；337项14done/7in-progress；完整示例继续 |
| 2026-10-11 | ISSUE-009 / APP-M2-T001 | 开始共同底座可信会话与页面守卫阶段；原完整布局/路由卡进行中，337项14done/8in-progress，后续258卡planned |
| 2026-10-12 | ISSUE-013 / REV-M0-T02 | QA独立复跑、会话实时HTTP脚本入库及交付/说明；338项15done |
| 2026-10-12 | ISSUE-015 / REV-M0-T03 | APP-M1-T06验收计划in-review；339项15done/1in-review |
| 2026-10-12 | ISSUE-015 / REV-M0-T03、T04 | 计划评审通过；smoke_t06、Word渲染记录、2截图；340项17done |
| 2026-10-12 | ISSUE-012 / APP-M2-T008 | 离线CI在 cf2c2a1 三作业通过；T008本地done，340项18done、8in-progress、266planned；未合入、未发布 |
| 2026-10-12 | ISSUE-010 / AI-01；ISSUE-011 / AI-02 | 登记模型、向量、业务库和内网待决项；兼容适配器本地验收。与上述记录合并后342项19done、8in-progress、266planned、49blocked。未选库，未连真实端点 |
| 2026-10-12 | ISSUE-013 / REV-M0-T05 | QA签署APP-M2-T008与AI-02；当时看板为343项20done |
| 2026-10-12 | ISSUE-012 / APP-M2-T008 | 按QA的S1/S3/S4/S5改回 in-review，补PROJECT_BRIEF同步，运行器ubuntu-24.04，动作升到Node 24主版本；当时343项19done、1in-review |
| 2026-10-12 | ISSUE-010 / AI-01；ISSUE-011 / AI-02 | 补登 PROJECT_BRIEF 排期行，不回退。AI-02 改回 in-review，T008 保持 in-review。合并后 343 项 18 done、2 in-review。用户决定业务库为 MySQL 8；向量库仍待决，ISSUE-010 仍 blocked |
| 2026-10-12 | ISSUE-009 / ISSUE-014 / APP-M2-T001 | ProLayout、浏览器地址和编辑台离开保护提交 in-review。343项18done、3in-review、7in-progress、266planned、49blocked。未改 PRD、ROADMAP、ARCHITECTURE、PROJECT_BRIEF。未标 done，未合入 |
| 2026-10-12 | ISSUE-011 / AI-02 | 项目经理于 10-12 12:10 在 QA 签署后确认。AI-02 为 done，ISSUE-011 为 closed。当时 343 项 19 done、2 in-review、7 in-progress |
| 2026-10-12 | ISSUE-016 / AI-03 | 内存检索口与三条证据候选，状态 in-review。与 T008 的 done 合并后为 344 项 20 done、2 in-review、7 in-progress。不连接 MySQL，不选定向量库。ISSUE-010 未改 |
| 2026-10-12 | ISSUE-005 / BE-M0-T02、T03 | 错误体与24小时幂等提交为in-review。350项20done、4in-review、7in-progress、4ready。业务库决定为MySQL 8，本轮无驱动或迁移。PRD、ROADMAP、ARCHITECTURE未改 |
| 2026-10-12 | ISSUE-020 / APP-M2-T001 | 路由级分包提交 in-review。首屏主块 1564.53 kB 降至 315.94 kB。不新增任务，350项20done、4in-review、7in-progress、266planned、49blocked、4ready保持不变。未改基线正文，未改后台，未标 done |
| 2026-10-12 | ISSUE-017 / OPS-M0-T02 | 内网部署草案 in-review；业务库按已登记的 MySQL 8 书写，向量与模型仍待决；351项20done、5in-review、4ready。未部署。未改 PRD、ROADMAP、ARCHITECTURE、PROJECT_BRIEF |
| 2026-10-12 | ISSUE-017 / OPS-M0-T02 | 按 QA 补约束：会话和幂等回执为进程内内存。ISSUE-018 落地前只能一个 uvicorn worker、一个副本；重启丢失这两类状态。多 worker 和多副本 blocked 在尚未建档的 ISSUE-018。任务仍为 in-review |
| 2026-10-12 | ISSUE-013 / REV-M0-T07 | QA签署BE-M0-T02与BE-M0-T03（两卡仍in-review待项目经理标done）；352项21done |
| 2026-10-12 | ISSUE-016 / AI-03 | 旁路核对：适配器在 /api/v1 生成失败已是冻结错误体，只加一条测试。不新增错误码，不改码表，状态仍 in-review。不改 PRD、ROADMAP、ARCHITECTURE、TASK_BOARD、PROJECT_STATUS、PROJECT_BRIEF |
| 2026-10-12 | ISSUE-019 / REV-M0-T06；ISSUE-013 / REV-M0-T08 | Playwright E2E与T001签署（不通过）；354项7in-review |
| 2026-10-12 | ISSUE-022 / APP-M2-T124 | 依赖未满足，T124 改为 blocked。354项仍为 21 done、7 in-review、7 in-progress，planned 改为 265，blocked 改为 50。不改产品代码。适用 REF-08 |

## 缺失输入

技术方案v1.4.2、设计规范v1.2与完整高保真原型包尚未取得；历史产品稿和真实投标原件未入库。缺件和适用性按 [基线差异](decisions/baseline-gaps.md)追踪，不能以索引登记代替取得或验收。
