为什么有这个文件：集中登记文档位置、版本、更新日期和来源。

它解决什么问题：避免找错版本，或修改文件后找不到对应记录。

# 文档更新索引

维护版本：g1.1。更新日期：2026-10-12。当前实现关联：ISSUE-007 / APP-M1；离线检查：ISSUE-012 / APP-M2-T008；范围评审：ISSUE-005 / FE-M0-T03；模型决定：ISSUE-010 / AI-01（closed / in-review；业务库为 MySQL 8，嵌入与向量库为 RAGFlow）；兼容适配器：ISSUE-011 / AI-02（done）；检索骨架：ISSUE-016 / AI-03（closed / done，仅内存）。文档入口统一使用本文件，规则见 [WORKFLOW](governance/WORKFLOW.md)。历史交付维持当时版本与事实；整个ICG来源清单以D-050登记。

编号保持稳定。每次新增、修改、移动、归档文档更新路径、日期、版本、状态、关联 Issue/任务和说明；有替代文件时保留来源。治理版本与业务文档/软件版本独立，参考产品原文以文内版本为准。

| 编号 | 更新日期 | 文档 | 层级/模块 | 版本 | 状态 | 关联 Issue/任务 | 说明 |
|---|---|---|---|---|---|---|---|
| D-001 | 2026-10-12 | [项目状态](PROJECT_STATUS.md) | 项目 | g1.1 | 当前 | ISSUE-007 / APP-M1；ISSUE-026；ISSUE-025 / BE-M0-T14；ISSUE-027 / BE-M0-T15；ISSUE-010 / AI-01；ISSUE-009 / APP-M2-T001；ISSUE-017 / OPS-M0-T02；ISSUE-018 / BE-M0-T12；ISSUE-031 / BE-M0-T16 | 387项51done、11in-review、7in-progress、265planned、48blocked、5ready。T001、T002、T12、T13、T14、T15、T078、T114、OPS-M0-T02 与 AI-03 为 done。ISSUE-009、014、016、017、020、022、026、027、029、031 已 closed。未部署。T11、T16 与 T18 仍 in-review。T13 与 REV-M0-T23 已依据 QA ae38ec3，PM 17:16 确认 done。T15 已由项目经理于 18:01 确认 done。用户已在 Word/WPS 目视确认。ISSUE-027 已 closed。T17 与 T19 为 planned。T114 与 REV-M0-T22 已依据 QA f521950，PM 17:13 确认 done。T078 与 REV-M0-T24 已依据 QA 19c4862，PM 17:20 确认 done。T124 为 ready，本轮不实现。ISSUE-033 为 in-review，不关闭。ISSUE-035 为 new。ISSUE-036 为 in-review |
| D-002 | 2026-10-12 | [前端 PRD](PRD.md) | 前端需求 | 参考实施入口 / g1.1 | 实施中 | ISSUE-007 / APP-M1；ISSUE-026；ISSUE-025；ISSUE-027 / BE-M0-T15 | 第19行为里程碑快照 as of 3bb311a：366项32done、6in-review、其余255卡planned。第27行改为依据 PRD v1.8 与字典 v1.9 |
| D-003 | 2026-10-12 | [前端架构](ARCHITECTURE.md) | 前端架构 | 参考实施入口 / g1.1 | 实施中 | ISSUE-007 / APP-M1；ISSUE-010 / AI-01；ISSUE-011 / AI-02；ISSUE-016 / AI-03；ISSUE-017 / OPS-M0-T02 | 同源存储和替换接口；业务库为 MySQL 8，嵌入、向量库与重排定为 RAGFlow 自带，适配器未实现 |
| D-004 | 2026-10-12 | [前端路线图](ROADMAP.md) | 计划 | 参考实施入口 / g1.1 | 执行入口 | ISSUE-007 / APP-M1；ISSUE-026；ISSUE-025 / BE-M0-T14；ISSUE-027 / BE-M0-T15 | 里程碑快照 as of 3bb311a：366项32done、6in-review。任务看板是准绳。T124 为 ready，本轮不实现 |
| D-005 | 2026-10-09 | [UX 规范](design/ux.md) | 设计 | 原文 | 参考 | FE-M0-T01 | 从ui/ux.md迁移，无业务内容改写 |
| D-006 | 2026-10-09 | [产品 PRD v1.8](reference/product/prd-mvp-v1.8.md) | 产品参考 | v1.8 | 供评审 | FE-M0-T01 | 已脱敏原文，不受治理修订覆盖 |
| D-007 | 2026-10-09 | [资料库字典 v1.9](reference/product/kb-data-dictionary-v1.9.md) | 数据参考 | v1.9 | 供评审 | FE-M0-T01 | 逻辑字典，不是数据库迁移 |
| D-008 | 2026-10-10 | [目录方案](architecture/repository-layout.md) | 架构 | 当前骨架 / reference-1 | 当前方案 | ISSUE-007 / APP-M1 | 首轮快照与实际同源前后端结构分列 |
| D-009 | 2026-10-09 | [基线差异](decisions/baseline-gaps.md) | 决策 | 初版 | 待评审 | FE-M0-T01 | 16项版本、范围与选型差异 |
| D-010 | 2026-10-09 | [PR #1 评审](reviews/pr-1-integration.md) | 协作 | 初版 / g1.0后续记录 | 待整合 | ISSUE-001 / ISSUE-003 | 系统/前端分层及后续规则、索引整合提醒 |
| D-011 | 2026-10-09 | [原型说明](../prototypes/bidding-ux/README.md) | 原型 | 静态演示 | 当前 | ISSUE-002 / FE-M0-T01 | 离线打开、启动方法与模拟范围 |
| D-012 | 2026-10-12 | [Issue 看板](../issues/index.md) | 问题 | g1.1 | 当前 | ISSUE-007 / APP-M1；ISSUE-026；ISSUE-025 / BE-M0-T14；ISSUE-027 / BE-M0-T15；ISSUE-010；ISSUE-017；ISSUE-024；ISSUE-031 | 017已closed，未部署；024、032、035为new；033、036为in-review；009、014、016、020、022、025、026、027、029、031已closed；028、030为in-review；010与023已closed |
| D-013 | 2026-10-09 | [首轮测试](testing/2026-10-09-repository-foundation.md) | 验证 | 首轮快照 | 已验收 | ISSUE-002 / FE-M0-T01 | 编辑锁6项回归及当时链接校验 |
| D-014 | 2026-10-09 | [首轮交付](delivery/2026-10-09-repository-foundation.md) | 交付 | 首轮快照 | 历史证据 | FE-M0-T01 | 保留原交付事实；逐任务归档见D-030 |
| D-015 | 2026-10-12 | [协作流程](governance/WORKFLOW.md) | 治理 | g1.1 | 当前规则 | ISSUE-007 / APP-M1；ISSUE-026 | 第4节：三份基线计数是里程碑快照。治理块仍为 g1.1，不升版 |
| D-016 | 2026-10-09 | [本次同步表](governance/ISSUE-003-sync.md) | 治理 | g1.0 | 本次记录 | ISSUE-003 / FE-M0-T02 | 四份基线及看板、进度、索引的影响评估 |
| D-017 | 2026-10-12 | [任务看板](TASK_BOARD.md) | 执行 | g1.1 | 当前 | ISSUE-007 / APP-M1；ISSUE-010 / AI-01；ISSUE-026；ISSUE-025 / BE-M0-T14；ISSUE-027 / BE-M0-T15；ISSUE-022 / T124；ISSUE-017 / OPS-M0-T02；ISSUE-018 / BE-M0-T12；ISSUE-031 / BE-M0-T16；ISSUE-036 | 387项51done、11in-review、7in-progress、265planned、48blocked、5ready。T11、T16、T18为in-review，T12已依据 QA ae6fd10，PM 15:32 确认 done，T13与REV-M0-T23已依据 QA ae38ec3，PM 17:16 确认 done，T15已由项目经理于 18:01 确认 done，用户已在 Word/WPS 目视确认，ISSUE-027 已 closed，T17与T19为planned，T078与REV-M0-T24已依据 QA 19c4862，PM 17:20 确认 done，T114与REV-M0-T22已依据 QA f521950，PM 17:13 确认 done，T001、T002、T14、OPS-M0-T02 与 AI-03 为 done，T124为ready，本轮不实现 |
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
| D-045 | 2026-10-12 | [OPS任务](tasks/OPS-M0.md) | 运维 | g1.1 | 当前 | ISSUE-004；ISSUE-017 / OPS-M0-T02 | 工作区同步已验收；内网部署草案 done，未部署 |
| D-046 | 2026-10-09 | [REV任务](tasks/REV-M0.md) | 审查 | g1.1 | 当前 | ISSUE-004 | 目录/业务/技术与brief交付 |
| D-047 | 2026-10-09 | [业务审查](reviews/2026-10-09-business-readiness.md) | 业务 | review-1 | 待决定 | REV-M0-T01 / ISSUE-005 | 场景矩阵与12项设计/验收发现 |
| D-048 | 2026-10-09 | [技术审查](reviews/2026-10-09-technical-readiness.md) | 技术 | review-1 | 待决定 | REV-M0-T01 / ISSUE-005 | 6类契约缺口与图片目录对照 |
| D-049 | 2026-10-12 | [接手brief](PROJECT_BRIEF.md) | 接手 | brief-9 | 当前 | ISSUE-007 / APP-M1；ISSUE-026；ISSUE-025 / BE-M0-T14；ISSUE-027 / BE-M0-T15；ISSUE-009 / T001；ISSUE-022 | 排期为里程碑快照 as of 3bb311a：366项32done、6in-review。T14 为 done。T124 为 ready，本轮不实现 |
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
| D-071 | 2026-10-12 | [API约定说明](../spec/openapi/README.md) | 接口 | frozen-names-1 | 当前 | ISSUE-031 / BE-M0-T16；ISSUE-022 | 增删错误码必须在同一提交更新 FROZEN_NAMES。重新导出前须保住草案操作和 deprecated 标注，脚本以后再改。502/503 自动重试说明含 N7：MODEL_UNAVAILABLE 与 SECRET_KEY_UNAVAILABLE 不自动重试 |
| D-072 | 2026-10-10 | [启动器](../backend/bid-core/Start-Demo.ps1) | 工具 | reference-1 | 已执行构建 | ISSUE-007 / APP-M1 | 安装前后端依赖、构建页面及单进程启动 |
| D-073 | 2026-10-10 | [依赖锁定](../backend/bid-core/requirements.txt) | 环境 | reference-1 | 安装通过 | ISSUE-007 / APP-M1 | 加数字PDF解析，pip check通过 |
| D-074 | 2026-10-12 | [实际接口约定](../spec/openapi/demo-v1.json) | 接口 | reference-1 / outline-contract-frozen-1 | 生成加冻结文本 | ISSUE-007 / APP-M1；ISSUE-022 / T124；ISSUE-033 / BE-M0-T18 | 已实现路径仍从代码导出。x-idempotency.retry 另写没有 Idempotency-Key 的写入不自动重试。大纲路径仍 frozen。EvidenceMountFields 记录挂证据字段 |
| D-075 | 2026-10-12 | [后台入口](../backend/bid-core/icg_demo/main.py) | 代码 | reference-1 | 联调通过 | ISSUE-007 / APP-M1；ISSUE-011 / AI-02 | 同源页面、两代错误字段；显式配置才启用兼容模型 |
| D-076 | 2026-10-11 | [后台测试](../tests/backend/test_demo.py) | 验证代码 | demo-1 | 31项通过 | BE-M0-T01 | 实际失败边界、并发与输出 |
| D-077 | 2026-10-11 | [HTTP验收入口](../backend/bid-core/smoke_demo.py) | 验证工具 | demo-1 | 通过 | BE-M0-T01 | 连接实际监听端口执行完整链路 |
| D-078 | 2026-10-10 | [接口生成器](../backend/bid-core/export_openapi.py) | 工具 | demo-1 | 通过 | BE-M0-T01 | 保持约定与实际代码同源 |
| D-079 | 2026-10-10 | [页面事件回归](../tests/backend/demo-page.test.cjs) | 验证代码 | demo-1 | 7项通过 | BE-M0-T01 | 直接执行页面代码，验证旧草稿、确认、恢复失败与会话锁 |
| D-080 | 2026-10-11 | [示例联调Issue](../issues/ISSUE-007.md) | 变更 | reference-members-1 | in-progress | ISSUE-007 / APP-M1 | 同一产品逐页接通，T07/T14/T15本地验收，完整目标继续 |
| D-081 | 2026-10-11 | [示例任务卡](tasks/APP-M1.md) | 实施 | reference-members-1 / library-basis-1 | 当前 | ISSUE-007 / APP-M1；ISSUE-008 / T16 | 16项，T07/T09～16本地done；资料及模板保护验收，完整父任务继续 |
| D-082 | 2026-10-11 | [示例接口约定](architecture/icg-reference-contract.md) | 接口 | reference-members-1 | 实际契约 | ISSUE-007 / APP-M1；ISSUE-022 | 项目成员、分册/本节分工、逐章确认、已读依据和交接保护。502/503 自动重试含 N7：MODEL_UNAVAILABLE 与 SECRET_KEY_UNAVAILABLE 不自动重试 |
| D-083 | 2026-10-11 | [示例差异记录](decisions/icg-reference-deviations.md) | 评审 | reference-1 | 持续维护 | ISSUE-007 / APP-M1 | 版本缺件、已取消页签和高级功能差异 |
| D-084 | 2026-10-12 | [产品页面说明](../frontend/web/README.md) | 工程 | request-layer-2 | 构建通过 | ISSUE-009 / APP-M2-T001；APP-M2-T002 | 没有幂等键的写入不重试；GET 与有键写入仍复用同一把键 |
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
| D-141 | 2026-10-12 | [完整后续任务](tasks/APP-M2.md) | 实施计划 | icg-task-plan-1 | T001、T002、T008 done | ISSUE-007 / APP-M1-T07 / APP-M2；ISSUE-009 / APP-M2-T002 | 项目经理在群里确认 QA 签署后，T001 与 T002 标为 done |
| D-142 | 2026-10-12 | [逐页逐规则映射](testing/icg-task-mapping.md) | 范围核对 | icg-task-map-1 | 已核对范围，功能未完成 | ISSUE-007 / APP-M1-T07；ISSUE-009 / APP-M2-T002 | 190原M1～M6 WBS、47组/44规则；T002 改为 in-review |
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
| D-160 | 2026-10-12 | [共同底座Issue](../issues/ISSUE-009.md) | 实施 | layout-review-1 | closed | ISSUE-009 / APP-M2-T001 | 项目经理在 QA 签署 d55d507 后确认 closed。T001 与 T002 已 done |
| D-161 | 2026-10-11 | [可信会话与导航契约](architecture/application-session-contract.md) | 契约 | application-foundation-1 | 当前实施 | ISSUE-009 / APP-M2-T001 | 后台身份/资源读取与三演示角色兼容边界 |
| D-162 | 2026-10-12 | [共同底座阶段交付](delivery/APP-M2-T001.md) | 交付 | layout-review-1 | done | ISSUE-009 / APP-M2-T001 | QA REV-M0-T11 签署通过后，项目经理在群里确认，本卡 done |
| D-163 | 2026-10-12 | [会话与守卫代码解释](code/APP-M2-T001.md) | 说明 | layout-review-1 | in-review | ISSUE-009 / APP-M2-T001 | 顶栏按侧栏宽度留白，展开按钮不再被 logo 挡住 |
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
| D-192 | 2026-10-12 | [离线CI工作流](../.github/workflows/offline-check.yml) | 工程 | mysql-ci-1 | 当前 | ISSUE-012 / APP-M2-T008；ISSUE-025 / BE-M0-T14；ISSUE-019 / REV-M0-T06 | ubuntu-24.04；backend-mysql 任一跳过即失败；e2e 失败阻断工作流；不导出 ICG_MYSQL_PASSWORD |
| D-193 | 2026-10-12 | [模型与数据库决定](../issues/ISSUE-010.md) | 决策 | model-choice-3 | closed | ISSUE-010 / AI-01 | 配置页、RAGFlow、生产仅内网；真实端点未验收 |
| D-194 | 2026-10-12 | [兼容适配器事项](../issues/ISSUE-011.md) | 变更 | openai-adapter-3 | closed | ISSUE-011 / AI-02 | 项目经理于 10-12 12:10 在 QA 签署后确认；未合入 |
| D-195 | 2026-10-12 | [模型准备任务](tasks/AI-M0.md) | 实施 | model-config-fixture-1 | 当前 | ISSUE-010 / AI-01；ISSUE-011 / AI-02；ISSUE-016 / AI-03 | AI-01为in-review。CI 假服务已勾选。真实端点未验收 |
| D-196 | 2026-10-12 | [决定登记交付](delivery/AI-01.md) | 交付 | model-config-fixture-1 | in-review | ISSUE-010 / AI-01；ISSUE-028 | 决定已登记。AC-02 假服务已核对。不标 done |
| D-197 | 2026-10-12 | [适配器交付](delivery/AI-02.md) | 交付 | openai-adapter-3 | done | ISSUE-011 / AI-02 | 项目经理已确认；真实端点仍未接通 |
| D-198 | 2026-10-12 | [适配器代码解释](code/AI-02.md) | 说明 | openai-adapter-1 | 当前 | ISSUE-011 / AI-02 | 环境变量、请求、重试和敏感门禁 |
| D-199 | 2026-10-12 | [适配器验证](testing/2026-10-12-openai-compatible-model.md) | 验证 | openai-adapter-1 | 本地通过 | ISSUE-011 / AI-02 | 契约30项；全后台回归通过；无真实端点 |
| D-200 | 2026-10-12 | [010同步记录](governance/ISSUE-010-sync.md) | 治理 | model-choice-3 | 已核对 | ISSUE-010 / AI-01 | 关闭决定。不改 PRD、ROADMAP、PROJECT_BRIEF 的任务计数 |
| D-201 | 2026-10-12 | [011同步记录](governance/ISSUE-011-sync.md) | 治理 | openai-adapter-3 | 已核对 | ISSUE-011 / AI-02 | 补登 PROJECT_BRIEF；项目经理确认后为 done / closed |
| D-202 | 2026-10-12 | [兼容模型适配器](../backend/bid-core/icg_demo/openai_model.py) | 后台 | openai-adapter-1 | 契约通过 | ISSUE-011 / AI-02 | 显式启用的 chat completions，失败不伪装成功 |
| D-203 | 2026-10-12 | [适配器契约测试](../tests/backend/test_openai_compatible_model.py) | 验证 | openai-adapter-1 | 31项通过 | ISSUE-011 / AI-02；ISSUE-016 旁路 | 假传输覆盖成功、失败和敏感门禁；v1 生成失败为冻结错误体 |
| D-204 | 2026-10-12 | [QA签署复核](testing/2026-10-12-qa-signoff.md) | 验证 | qa-rerun-2 | 本地通过 | ISSUE-013 / REV-M0-T05 | T008与AI-02签署：Actions三次成功、本地292/30/72/35，S1～S5 |
| D-205 | 2026-10-12 | [签署复核交付](delivery/REV-M0-T05.md) | 交付 | qa-rerun-2 | 已本地验收 | ISSUE-013 / REV-M0-T05 | 无代码；结论与缺口 |
| D-206 | 2026-10-12 | [ProLayout依赖Issue](../issues/ISSUE-014.md) | 版本 | pro-layout-7.22.7 | closed | ISSUE-014 / APP-M2-T001 | 项目经理在 QA 签署 173c39f 后确认 closed。关联卡 T001 已 done |
| D-207 | 2026-10-12 | [布局地址复核](testing/2026-10-12-prolayout-routes.md) | 验证 | layout-review-1 | in-review | ISSUE-009 / ISSUE-014 / APP-M2-T001 | 前端77、后台293、构建体积；无三断点截图 |
| D-208 | 2026-10-12 | [014同步记录](governance/ISSUE-014-sync.md) | 治理 | pro-layout-7.22.7 | 已核对 | ISSUE-014 / APP-M2-T001 | 基线未改的句子和 in-review 计数 |
| D-209 | 2026-10-12 | [产品外壳](../frontend/web/src/AppShell.tsx) | 前端 | pro-layout-7.22.7 | in-review | ISSUE-009 / APP-M2-T001 | 收起侧栏时顶栏按钮从 64px 右侧开始 |
| D-210 | 2026-10-12 | [页面地址](../frontend/web/src/app-route.ts) | 前端 | layout-review-1 | in-review | ISSUE-009 / APP-M2-T001 | 全局路径、项目页签和登录回原地址 |
| D-211 | 2026-10-12 | [离开保护](../frontend/web/src/leave-guard.ts) | 前端 | layout-review-1 | in-review | ISSUE-009 / APP-M2-T001 | 未保存时保留地址；取消不离开 |
| D-212 | 2026-10-12 | [地址与离开测试](../frontend/web/tests/app-navigation.test.mjs) | 验证 | layout-review-1 | 5项通过 | ISSUE-009 / APP-M2-T001 | 需 Node 22.18+ 或 Node 24；本轮用 24.21.0 |
| D-213 | 2026-10-12 | [检索骨架事项](../issues/ISSUE-016.md) | 变更 | retrieval-skeleton-1 | closed | ISSUE-016 / AI-03 | 依据 QA 签署 2fe6198（REV-M0-T16）关闭。内存实现。不连接 MySQL |
| D-214 | 2026-10-12 | [检索骨架交付](delivery/AI-03.md) | 交付 | retrieval-skeleton-1 | done | ISSUE-016 / AI-03 | 依据 QA 签署 2fe6198（REV-M0-T16）。未合入，未发布 |
| D-215 | 2026-10-12 | [检索骨架代码解释](code/AI-03.md) | 说明 | retrieval-skeleton-1 | 当前 | ISSUE-016 / AI-03 | 三条路径、公司过滤和失败原因不含正文 |
| D-216 | 2026-10-12 | [检索骨架验证](testing/2026-10-12-evidence-candidates.md) | 验证 | retrieval-skeleton-1 | 本地通过 | ISSUE-016 / AI-03 | 契约7项；全后台309项；v1失败体已核对；无新错误码 |
| D-217 | 2026-10-12 | [016同步记录](governance/ISSUE-016-sync.md) | 治理 | retrieval-skeleton-1 | 已核对 | ISSUE-016 / AI-03 | QA 签署 2fe6198 后 ISSUE-016 closed、AI-03 done。不改里程碑计数 |
| D-218 | 2026-10-12 | [检索实现](../backend/bid-core/icg_demo/retrieval.py) | 后台 | retrieval-skeleton-1 | 契约通过 | ISSUE-016 / AI-03 | 内存嵌入、重排、向量表和证据候选 |
| D-219 | 2026-10-12 | [证据候选测试](../tests/backend/test_evidence_candidates.py) | 验证 | retrieval-skeleton-1 | 7项通过 | ISSUE-016 / AI-03 | 合成数据覆盖公司隔离和历史不可附着 |
| D-220 | 2026-10-12 | [检索协议](../backend/bid-core/icg_demo/ports.py) | 后台 | retrieval-skeleton-1 | 当前 | ISSUE-016 / AI-03 | 增加嵌入、重排和向量检索协议 |
| D-221 | 2026-10-12 | [错误体交付](delivery/BE-M0-T02.md) | 交付 | contract-1 | done | ISSUE-005 / BE-M0-T02 | 项目经理于 10-12 12:28 在 QA 签署后确认 |
| D-222 | 2026-10-12 | [错误体代码解释](code/BE-M0-T02.md) | 说明 | contract-1 | 当前 | ISSUE-005 / BE-M0-T02 | 状态表、追踪头和解析失败的原状态 |
| D-223 | 2026-10-12 | [幂等交付](delivery/BE-M0-T03.md) | 交付 | contract-1 | done | ISSUE-005 / BE-M0-T03 | 项目经理于 10-12 12:28 在 QA 签署后确认 |
| D-224 | 2026-10-12 | [幂等代码解释](code/BE-M0-T03.md) | 说明 | contract-1 | 当前 | ISSUE-005 / BE-M0-T03 | 范围、指纹、过期和2048条上限 |
| D-225 | 2026-10-12 | [错误体与幂等验证](testing/2026-10-12-error-idempotency.md) | 验证 | contract-1 | 已执行 | ISSUE-005 / BE-M0-T02、T03 | 后台回归和141个code的冻结表；含MODEL_UNAVAILABLE=502 |
| D-226 | 2026-10-12 | [005同步表](governance/ISSUE-005-sync.md) | 治理 | g1.1 | 本轮记录 | ISSUE-005 | 基线逐行记录；已补 ARCHITECTURE 一句；PRD 与 ROADMAP 未改 |
| D-227 | 2026-10-12 | [错误状态表](../backend/bid-core/icg_demo/errors.py) | 后台 | contract-1 | 当前 | ISSUE-005 / BE-M0-T02 | 141个code的唯一HTTP状态及OpenAPI补充 |
| D-228 | 2026-10-12 | [幂等回执](../backend/bid-core/icg_demo/idempotency.py) | 后台 | contract-1 | 当前 | ISSUE-005 / BE-M0-T03 | 24小时、上限和失败不登记 |
| D-229 | 2026-10-12 | [错误与幂等回归](../tests/backend/test_error_idempotency.py) | 验证 | contract-1 | 当前 | ISSUE-005 / BE-M0-T02、T03 | 错误体、重放、冲突、过期、导出一致和v1模型失败 |
| D-230 | 2026-10-12 | [路由分包Issue](../issues/ISSUE-020.md) | 变更 | route-chunks-1 | closed | ISSUE-020 / APP-M2-T001 | 项目经理在 QA 签署 dcca509 后确认 closed。关联卡 T001 已 done |
| D-231 | 2026-10-12 | [路由分包复核](testing/2026-10-12-route-chunks.md) | 验证 | route-chunks-1 | in-review | ISSUE-020 / APP-M2-T001 | 全部分包前后体积；前端 78 pass、0 fail |
| D-232 | 2026-10-12 | [020同步记录](governance/ISSUE-020-sync.md) | 治理 | route-chunks-1 | 已核对 | ISSUE-020 / APP-M2-T001 | 基线未改；不新增任务 |
| D-233 | 2026-10-12 | [路由分包交付](delivery/ISSUE-020.md) | 交付 | route-chunks-1 | in-review | ISSUE-020 / APP-M2-T001 | 动态 import 与 Suspense；后台未改 |
| D-234 | 2026-10-12 | [路由分包代码解释](code/ISSUE-020.md) | 说明 | route-chunks-1 | in-review | ISSUE-020 / APP-M2-T001 | 加载顺序和离开保护仍在 App |
| D-235 | 2026-10-12 | [路由加载器](../frontend/web/src/route-loaders.ts) | 前端 | route-chunks-1 | in-review | ISSUE-020 / APP-M2-T001 | 动态 import 并缓存进行中的请求 |
| D-236 | 2026-10-12 | [懒加载页面](../frontend/web/src/lazy-routes.tsx) | 前端 | route-chunks-1 | in-review | ISSUE-020 / APP-M2-T001 | React.lazy 外壳和各页 |
| D-237 | 2026-10-12 | [分包约束测试](../frontend/web/tests/route-chunks.test.mjs) | 验证 | route-chunks-1 | 1项通过 | ISSUE-020 / APP-M2-T001 | 入口不再静态引入外壳和页面 |
| D-238 | 2026-10-12 | [内网部署草案](operations/intranet-deployment-plan.md) | 运维 | intranet-plan-1 | done | ISSUE-017 / OPS-M0-T02 | 用户 10-12 14:34 确认。重排为 RAGFlow 自带。未部署。单 worker 单副本，多副本 blocked 在 ISSUE-018 |
| D-239 | 2026-10-12 | [内网部署 Issue](../issues/ISSUE-017.md) | 决策 | intranet-plan-1 | closed | ISSUE-017 / OPS-M0-T02 | 用户 10-12 14:34 确认。未部署 |
| D-240 | 2026-10-12 | [内网部署交付](delivery/OPS-M0-T02.md) | 交付 | intranet-plan-1 | done | ISSUE-017 / OPS-M0-T02 | 无代码；未创建环境。用户 10-12 14:34 确认 |
| D-241 | 2026-10-12 | [内网部署核对](testing/2026-10-12-intranet-deploy-plan.md) | 验证 | intranet-plan-1 | 文档核对 | ISSUE-017 / OPS-M0-T02 | 用户 10-12 14:34 确认。未连接 MySQL、RAGFlow 或内网 |
| D-243 | 2026-10-12 | [BE-M0-T02/T03签署复核](testing/2026-10-12-be-m0-t02-t03-signoff.md) | 验证 | qa-signoff-be | 本地通过 | ISSUE-013 / REV-M0-T07 | 308/15/12/77/35、探针47/47、Actions 38203448527成功 |
| D-244 | 2026-10-12 | [BE签署复核交付](delivery/REV-M0-T07.md) | 交付 | qa-signoff-be | 已本地验收 | ISSUE-013 / REV-M0-T07 | 仅QA探针脚本；结论与Q1缺口 |
| D-245 | 2026-10-12 | [E2E Issue](../issues/ISSUE-019.md) | 审查 | e2e-1 | in-review | ISSUE-019 / REV-M0-T06 | Playwright仅测试依赖 |
| D-246 | 2026-10-12 | [E2E与T001签署](testing/2026-10-12-e2e-t001-signoff.md) | 验证 | e2e-1 | 本地执行 | ISSUE-019 / REV-M0-T06；ISSUE-013 / REV-M0-T08 | 11项E2E。用户与项目经理确认后 e2e 改为必需。ISSUE-019 仍 in-review |
| D-247 | 2026-10-12 | [E2E交付](delivery/REV-M0-T06.md) | 交付 | e2e-1 | in-review | ISSUE-019 / REV-M0-T06 | 命令、覆盖与剩余 |
| D-248 | 2026-10-12 | [E2E代码解释](code/REV-M0-T06.md) | 说明 | e2e-1 | in-review | ISSUE-019 / REV-M0-T06 | 启动顺序与用例思路 |
| D-249 | 2026-10-12 | [T001签署交付](delivery/REV-M0-T08.md) | 交付 | qa-rerun-3 | in-review | ISSUE-013 / REV-M0-T08 | 签署结论与缺陷 |
| D-250 | 2026-10-12 | [E2E配置](../frontend/web/e2e/playwright.config.ts) | 验证 | e2e-1 | in-review | ISSUE-019 / REV-M0-T06 | Chromium、自启内存后台 |
| D-251 | 2026-10-12 | [E2E用例](../frontend/web/e2e/app-shell.spec.ts) | 验证 | e2e-1 | 11项通过 | ISSUE-019 / REV-M0-T06；ISSUE-009 | 断点截图、离开确认、前进后退；D1–D4 标记已去掉 |
| D-252 | 2026-10-12 | [工作台1680截图](testing/assets/e2e-workbench-1680.png) | 证据 | e2e-1 | E2E截图 | ISSUE-019 / REV-M0-T06 | D3卡片不可读、D4顶栏落入侧栏 |
| D-253 | 2026-10-12 | [编辑台1280截图](testing/assets/e2e-editor-1280.png) | 证据 | e2e-1 | E2E截图 | ISSUE-019 / REV-M0-T06 | 编辑台三栏与暗色控件 |
| D-254 | 2026-10-12 | [概览1440截图](testing/assets/e2e-overview-1440.png) | 证据 | e2e-1 | E2E截图 | ISSUE-019 / REV-M0-T06 | 项目概览布局 |
| D-242 | 2026-10-12 | [017同步记录](governance/ISSUE-017-sync.md) | 治理 | intranet-plan-1 | 已核对 | ISSUE-017 / OPS-M0-T02 | ISSUE-017 已 closed。重排定为 RAGFlow 自带。不改 ISSUE-029。未部署 |
| D-255 | 2026-10-12 | [T124契约事项](../issues/ISSUE-022.md) | 变更 | outline-contract-frozen-1 | closed | ISSUE-022 / APP-M2-T124 | QA 0254102，PM 15:36 确认 closed。契约已冻结。T124 为 ready，本轮不实现。T078 已 done（QA 19c4862，PM 17:20 确认）。T114 已 done（QA f521950，PM 17:13 确认） |
| D-256 | 2026-10-12 | [T124草案交付](delivery/APP-M2-T124.md) | 交付 | outline-contract-frozen-1 | ready | ISSUE-022 / APP-M2-T124 | 契约已冻结；无运行时；卡片为 ready，本轮不实现，不标 done |
| D-257 | 2026-10-12 | [T124契约说明](code/APP-M2-T124.md) | 说明 | outline-contract-frozen-1 | 当前 | ISSUE-022 / APP-M2-T124 | 状态 frozen；423/503 不列重放头；整章输入保持 |
| D-258 | 2026-10-12 | [T124契约核对](testing/2026-10-12-t124-dependencies.md) | 验证 | outline-contract-frozen-1 | 契约测试 | ISSUE-022 / APP-M2-T124 | 冻结状态、N7 重试例外、无键写入不自动重试；不调用新路由 |
| D-259 | 2026-10-12 | [022同步记录](governance/ISSUE-022-sync.md) | 治理 | outline-contract-frozen-1 | 已核对 | ISSUE-022 / APP-M2-T124 | ISSUE-022 已 closed。T078 已 done（QA 19c4862，PM 17:20 确认）。T124 为 ready，本轮不实现。不改三份基线计数 |
| D-260 | 2026-10-12 | [MySQL 8 持久化方案](architecture/mysql-8-persistence-plan.md) | 架构 | impl-4 | in-review | ISSUE-018 / BE-M0-T13 | 项目聚合已依据 QA ae38ec3，PM 17:16 确认 done。第 6 节有字典 v1.9 对照。章节及其他聚合仍在内存 |
| D-261 | 2026-10-12 | [ISSUE-018](../issues/ISSUE-018.md) | 变更 | impl-4 | in-progress | ISSUE-018 / BE-M0-T13 | 回执与会话为 in-review。编辑租约与项目聚合已 done。不关闭 |
| D-262 | 2026-10-12 | [方案交付](delivery/BE-M0-T08.md) | 交付 | plan-1 | in-review | ISSUE-018 / BE-M0-T08 | 无运行时代码 |
| D-263 | 2026-10-12 | [方案无代码说明](code/BE-M0-T08.md) | 说明 | plan-1 | 当前 | ISSUE-018 / BE-M0-T08 | 未改仓库和依赖 |
| D-264 | 2026-10-12 | [018同步表](governance/ISSUE-018-sync.md) | 治理 | impl-1 | 已核对 | ISSUE-018 / BE-M0-T10 | 方案轮次未改基线；实施轮次仍不改 PRD、ROADMAP、ARCHITECTURE |
| D-265 | 2026-10-12 | [ISSUE-021](../issues/ISSUE-021.md) | 变更 | queue-1 | blocked | ISSUE-021 / BE-M0-T09 | 旧接口、幂等和 E2E-D5；任务 planned；本轮不实施 |
| D-266 | 2026-10-12 | [T078内存方案](governance/ISSUE-022-t078-plan.md) | 计划 | t078-memory-1 | done | ISSUE-022 / APP-M2-T078 | 内存发布层已 done（QA 19c4862，PM 17:20 确认）。页面未做，不挡住 done。GET 的 ETag 与拦截回执仍有效 |
| D-267 | 2026-10-12 | [T001布局历史修复](testing/2026-10-12-t001-layout-history.md) | 验证 | layout-fix-1 | in-review | ISSUE-009 / APP-M2-T001 | E2E-D8：次要文字至少 4.5:1；Playwright 13 passed |
| D-268 | 2026-10-12 | [T001布局修复同步](governance/APP-M2-T001-layout-sync.md) | 治理 | layout-fix-1 | 已核对 | ISSUE-009 / APP-M2-T001 | 基线未改；QA 不通过记录保留 |
| D-269 | 2026-10-12 | [修复后工作台1680](testing/assets/t001-fixed-workbench-1680.png) | 证据 | layout-fix-1 | 修复截图 | ISSUE-009 / APP-M2-T001 | 深色侧栏、白顶栏、浅色卡片 |
| D-270 | 2026-10-12 | [修复后编辑台1280](testing/assets/t001-fixed-editor-1280.png) | 证据 | layout-fix-1 | 修复截图 | ISSUE-009 / APP-M2-T001 | 编辑台三栏与浅色正文 |
| D-271 | 2026-10-12 | [修复后概览1440](testing/assets/t001-fixed-overview-1440.png) | 证据 | layout-fix-1 | 修复截图 | ISSUE-009 / APP-M2-T001 | 项目概览与顶栏 |
| D-276 | 2026-10-12 | [ISSUE-023](../issues/ISSUE-023.md) | 变更 | deps-2 | closed | ISSUE-023 / BE-M0-T10 | 项目经理在 QA 签署 16cf971 后确认；未合入、未发布 |
| D-275 | 2026-10-12 | [连接交付](delivery/BE-M0-T10.md) | 交付 | deps-1 | done | ISSUE-023 / BE-M0-T10 | 连接和空迁移；项目经理在 QA 签署 98c5129 后确认 |
| D-272 | 2026-10-12 | [连接代码说明](code/BE-M0-T10.md) | 说明 | deps-1 | 当前 | ISSUE-023 / BE-M0-T10 | 环境变量决定仓库；业务读写仍在内存 |
| D-273 | 2026-10-12 | [连接与迁移验证](testing/2026-10-12-mysql-connection.md) | 验证 | deps-1 | 已执行 | ISSUE-023 / BE-M0-T10 | mysql:8.4；含运维命令和 uvicorn 结果 |
| D-274 | 2026-10-12 | [023同步表](governance/ISSUE-023-sync.md) | 治理 | deps-1 | 已核对 | ISSUE-023 / BE-M0-T10 | PRD、ROADMAP、ARCHITECTURE 未改 |
| D-277 | 2026-10-12 | [请求层交付](delivery/APP-M2-T002.md) | 交付 | request-layer-2 | done | ISSUE-009 / APP-M2-T002 | QA REV-M0-T11 签署通过后，项目经理在群里确认，本卡 done |
| D-278 | 2026-10-12 | [请求层代码说明](code/APP-M2-T002.md) | 说明 | request-layer-2 | 当前 | ISSUE-009 / APP-M2-T002 | 只对 GET 和有键写入重试；MODEL_UNAVAILABLE 仍只发一次 |
| D-279 | 2026-10-12 | [请求层验证](testing/2026-10-12-request-layer.md) | 验证 | request-layer-2 | 已执行 | ISSUE-009 / APP-M2-T002 | 前端 92 项通过；旧 lock 的 503 只发一次 |
| D-280 | 2026-10-12 | [请求层同步](governance/APP-M2-T002-sync.md) | 治理 | request-layer-2 | 已核对 | ISSUE-009 / APP-M2-T002 | 不改计数和 OpenAPI；ISSUE-021 补键后解除没键不重试 |
| D-281 | 2026-10-12 | [BE-M0-T08/T10 MySQL签署复核](testing/2026-10-12-be-m0-t10-mysql-signoff.md) | 验证 | qa-signoff-mysql | 本地通过 | ISSUE-013 / REV-M0-T09 | 真实MySQL 8.4.6迁移往返、mysql 2/2、320+2skip |
| D-282 | 2026-10-12 | [MySQL签署复核交付](delivery/REV-M0-T09.md) | 交付 | qa-signoff-mysql | 已本地验收 | ISSUE-013 / REV-M0-T09 | 无代码；结论与Q1～Q3 |
| D-283 | 2026-10-12 | [ISSUE-026](../issues/ISSUE-026.md) | 变更 | count-sync-4 | closed | ISSUE-026 | 项目经理在 QA 签署 9bcde17 后确认 closed。不新增任务卡 |
| D-284 | 2026-10-12 | [计数对齐交付](delivery/ISSUE-026.md) | 交付 | count-sync-4 | closed | ISSUE-026 | 快照保持 366项32done。Issue 已 closed |
| D-285 | 2026-10-12 | [计数对齐说明](code/ISSUE-026.md) | 说明 | count-sync-4 | 当前 | ISSUE-026 | 无应用代码；检查程序未改 |
| D-286 | 2026-10-12 | [计数核对](testing/2026-10-12-issue-026-counts.md) | 验证 | count-sync-1 | 已执行 | ISSUE-026 | 当时看板 361 项与三份正文一致 |
| D-287 | 2026-10-12 | [026同步表](governance/ISSUE-026-sync.md) | 治理 | count-sync-4 | 已核对 | ISSUE-026 | 里程碑快照规则写入 WORKFLOW 第4节 |
| D-288 | 2026-10-12 | [ISSUE-025](../issues/ISSUE-025.md) | 流程 | mysql-ci-1 | closed | ISSUE-025 / BE-M0-T14 | 依据 b20b844 关闭；ISSUE-024 不建档 |
| D-289 | 2026-10-12 | [MySQL CI 交付](delivery/BE-M0-T14.md) | 交付 | mysql-ci-1 | done | ISSUE-025 / BE-M0-T14 | 计数是截至 3bb311a 的快照；任务看板为准；不建业务表 |
| D-290 | 2026-10-12 | [MySQL CI 说明](code/BE-M0-T14.md) | 说明 | mysql-ci-1 | 当前 | ISSUE-025 / BE-M0-T14 | 不导出 ICG_MYSQL_PASSWORD；任一跳过即失败 |
| D-291 | 2026-10-12 | [MySQL CI 核对](testing/2026-10-12-backend-mysql-ci.md) | 验证 | mysql-ci-1 | 已核对 | ISSUE-025 / BE-M0-T14 | run 38207508936：2 passed、320 deselected；密码不进仓库 |
| D-292 | 2026-10-12 | [025同步表](governance/ISSUE-025-sync.md) | 治理 | mysql-ci-1 | 已核对 | ISSUE-025 / BE-M0-T14 | T14 done、Issue closed；PRD/ROADMAP 计数字句未改 |
| D-293 | 2026-10-12 | [配置驱动的对话模型](architecture/model-config-provider.md) | 架构 | model-config-fixture-1 | in-review | ISSUE-028 / AI-01 | Provider 切换仍是设计。CI 假服务已落地。不改 OpenAPI |
| D-294 | 2026-10-12 | [RAGFlow 检索适配器](architecture/ragflow-retrieval-adapter.md) | 架构 | ragflow-adapter-design-1 | closed | ISSUE-029 / AI-03 | 重排定为 RAGFlow 自带。路径 C 查询词过滤留到适配器实现。无客户端 |
| D-295 | 2026-10-12 | [ISSUE-010 决定核对](testing/2026-10-12-issue-010-decisions.md) | 验证 | model-choice-3 | 文档核对 | ISSUE-010 / AI-01 | 无内网调用。只链接 ISSUE-024 的 stream_enabled 与 json_mode_enabled |
| D-296 | 2026-10-12 | [ISSUE-028](../issues/ISSUE-028.md) | 变更 | model-config-fixture-1 | in-review | ISSUE-028 / AI-01 | AC-02 已由 REV-M0-T29 签署。AC-03 已由 REV-M0-T30 签署。不标 closed |
| D-297 | 2026-10-12 | [ISSUE-029](../issues/ISSUE-029.md) | 变更 | ragflow-adapter-design-1 | closed | ISSUE-029 / AI-03 | 用户 10-12 14:34 确认。重排定为 RAGFlow 自带。适配器未实现 |
| D-298 | 2026-10-12 | [028同步记录](governance/ISSUE-028-sync.md) | 治理 | model-config-fixture-1 | 已核对 | ISSUE-028 / AI-01 | AC-02 假服务已核对。不改任务计数。不改 OpenAPI |
| D-299 | 2026-10-12 | [029同步记录](governance/ISSUE-029-sync.md) | 治理 | ragflow-adapter-design-1 | 已核对 | ISSUE-029 / AI-03 | ISSUE-029 已 closed。路径 C 查询词过滤留到适配器实现。不改检索代码 |
| D-300 | 2026-10-12 | [T001重签与T002探测](testing/2026-10-12-qa-t001-t002-t020-recheck.md) | 验证 | qa-rerun-4 | 本地执行 | ISSUE-013 / REV-M0-T08 | T001因E2E-D7不通过；T002待修复提交；ISSUE-020通过 |
| D-301 | 2026-10-12 | [ISSUE-027](../issues/ISSUE-027.md) | 变更 | style-1 | closed | ISSUE-027 / BE-M0-T15 | Word 默认版式；用户 Word/WPS 目视 OK，PM 18:01 确认 closed。BE-M0-T15 为 done |
| D-302 | 2026-10-12 | [版式交付](delivery/BE-M0-T15.md) | 交付 | style-1 | done | ISSUE-027 / BE-M0-T15 | 合成 docx 的默认版式；PM 18:01 确认 done |
| D-303 | 2026-10-12 | [版式代码说明](code/BE-M0-T15.md) | 说明 | style-1 | 当前 | ISSUE-027 / BE-M0-T15 | 默认样式可被单个投标覆盖 |
| D-304 | 2026-10-12 | [版式核对](testing/2026-10-12-be-m0-t15-word-style.md) | 验证 | style-1 | 已执行 | ISSUE-027 / BE-M0-T15 | 打开合成 docx |
| D-305 | 2026-10-12 | [027同步表](governance/ISSUE-027-sync.md) | 治理 | style-1 | 已核对 | ISSUE-027 / BE-M0-T15 | 原提交改计数为 363 项。本跟进 ISSUE-027 为 closed，看板 387 项 51 done、11 in-review |
| D-306 | 2026-10-12 | [Word 默认版式](standards/word-default-style.md) | 标准 | style-1 | 当前 | ISSUE-027 / BE-M0-T15 | 用户确认原文。封面标题不把黑体当作拉丁回退 |
| D-307 | 2026-10-12 | [BE-M0-T15 Word版式签署复核](testing/2026-10-12-be-m0-t15-word-style-signoff.md) | 验证 | qa-signoff-word | XML核对通过 | ISSUE-013 / REV-M0-T10 | 四份导出全过；仅LibreOffice渲染。用户已 Word/WPS 目视 OK，PM 18:01 确认 T15 done |
| D-308 | 2026-10-12 | [Word版式签署交付](delivery/REV-M0-T10.md) | 交付 | qa-signoff-word | 已本地验收 | ISSUE-013 / REV-M0-T10 | 检查器与样张；Q1～Q3 |
| D-309 | 2026-10-12 | [026基线复核](testing/2026-10-12-issue-026-baseline-count-check.md) | 验证 | count-sync-4 | 已执行 | ISSUE-026 | 3bb311a 重数后快照为 366项32done；检查程序不比较活看板 |
| D-310 | 2026-10-12 | [T001/T002复验签署](testing/2026-10-12-qa-t001-t002-signoff.md) | 验证 | qa-rerun-5 | 本地通过 | ISSUE-013 / REV-M0-T11 | 92/35、E2E 13/13、探针27/27、对比度≥5.66 |
| D-311 | 2026-10-12 | [T001/T002签署交付](delivery/REV-M0-T11.md) | 交付 | qa-rerun-5 | 已本地验收 | ISSUE-013 / REV-M0-T11 | 无代码；结论与O1 |
| D-312 | 2026-10-12 | [T14 MySQL CI签署](testing/2026-10-12-be-m0-t14-mysql-ci-signoff.md) | 验证 | qa-signoff-mysql-ci | 本地通过 | ISSUE-013 / REV-M0-T12 | AC-01～04通过；本地往返、337 passed；M1～M3 P3 |
| D-313 | 2026-10-12 | [T14签署交付](delivery/REV-M0-T12.md) | 交付 | qa-signoff-mysql-ci | 已本地验收 | ISSUE-013 / REV-M0-T12 | 无代码；结论与观察项 |
| D-314 | 2026-10-12 | [MySQL 守卫核对](testing/2026-10-12-backend-mysql-guard.md) | 验证 | mysql-ci-1 | 已执行 | ISSUE-025 / BE-M0-T14 | 任一跳过、0 条、缺失均失败；不启动 MySQL |
| D-315 | 2026-10-12 | [T078片段发布交付](delivery/APP-M2-T078.md) | 交付 | t078-memory-1 | done | ISSUE-022 / APP-M2-T078 | QA 19c4862，PM 17:20 确认 done。页面未做，不挡住 done |
| D-316 | 2026-10-12 | [T078片段发布说明](code/APP-M2-T078.md) | 说明 | t078-memory-1 | 当前 | ISSUE-022 / APP-M2-T078 | 独立字典；回执仍用 library 作用域 |
| D-317 | 2026-10-12 | [T078片段发布核对](testing/2026-10-12-t078-snippet-publications.md) | 验证 | t078-memory-1 | 已执行 | ISSUE-022 / APP-M2-T078 | 后台 346 passed、2 skipped |
| D-318 | 2026-10-12 | [回执与会话交付](delivery/BE-M0-T11.md) | 交付 | sessions-1 | in-review | ISSUE-018 / BE-M0-T11 | 回执和登录会话入库；不标 done |
| D-319 | 2026-10-12 | [回执与会话代码说明](code/BE-M0-T11.md) | 说明 | sessions-1 | 当前 | ISSUE-018 / BE-M0-T11 | 导入时不连接；差量保存会话和回执 |
| D-320 | 2026-10-12 | [回执与会话核对](testing/2026-10-12-be-m0-t11-sessions-receipts.md) | 验证 | sessions-1 | 已执行 | ISSUE-018 / BE-M0-T11 | 无库、mysql:8.4、不可达地址；含 downgrade base |
| D-321 | 2026-10-12 | [ISSUE-026快照规则签署](testing/2026-10-12-issue-026-snapshot-signoff.md) | 验证 | qa-rerun-8 | 本地通过 | ISSUE-013 / REV-M0-T13 | 366项32done快照一致；模拟签收通过；CI全绿 |
| D-322 | 2026-10-12 | [REV-M0-T13签署交付](delivery/REV-M0-T13.md) | 交付 | qa-rerun-8 | 已本地验收 | ISSUE-013 / REV-M0-T13 | 无代码；结论与观察项 |
| D-323 | 2026-10-12 | [ISSUE-014 ProLayout签署](testing/2026-10-12-issue-014-prolayout-signoff.md) | 验证 | qa-rerun-9 | 本地通过 | ISSUE-013 / REV-M0-T14 | 仅新增pro-layout；体积逐字复现 |
| D-324 | 2026-10-12 | [REV-M0-T14签署交付](delivery/REV-M0-T14.md) | 交付 | qa-rerun-9 | 已本地验收 | ISSUE-013 / REV-M0-T14 | 无代码；结论与观察项 |
| D-325 | 2026-10-12 | [ISSUE-020路由分包签署](testing/2026-10-12-issue-020-route-split-signoff.md) | 验证 | qa-rerun-10 | 本地通过 | ISSUE-013 / REV-M0-T15 | 入口317.71 kB；92/92；E2E 13 |
| D-326 | 2026-10-12 | [REV-M0-T15签署交付](delivery/REV-M0-T15.md) | 交付 | qa-rerun-10 | 已本地验收 | ISSUE-013 / REV-M0-T15 | 无代码；结论与观察项 |
| D-327 | 2026-10-12 | [ISSUE-024](../issues/ISSUE-024.md) | 变更 | model-config-storage-1 | new | ISSUE-024 | 存储与 API。状态 new，负责人 backend。不改运行时 |
| D-328 | 2026-10-12 | [024同步记录](governance/ISSUE-024-sync.md) | 治理 | model-config-storage-1 | 已核对 | ISSUE-024 | 两码只登记在 Issue 表。不改三份基线 |
| D-329 | 2026-10-12 | [022后台复审](governance/ISSUE-022-backend-rereview.md) | 治理 | outline-contract-draft-3 | 已核对 | ISSUE-022 | 含 c6948c0 第三轮。文末附 B2、B3 |
| D-330 | 2026-10-12 | [ISSUE-016检索骨架签署](testing/2026-10-12-issue-016-retrieval-signoff.md) | 验证 | qa-rerun-11 | 本地通过 | ISSUE-013 / REV-M0-T16 | AC-01～05通过；O-1 P3 |
| D-331 | 2026-10-12 | [REV-M0-T16签署交付](delivery/REV-M0-T16.md) | 交付 | qa-rerun-11 | 已本地验收 | ISSUE-013 / REV-M0-T16 | 无代码；结论与观察项 |
| D-332 | 2026-10-12 | [ISSUE-028模型配置设计签署](testing/2026-10-12-issue-028-model-config-signoff.md) | 验证 | qa-rerun-12 | 本地通过 | ISSUE-013 / REV-M0-T17 | AC通过；D-1 P2；O-1/O-2 P3 |
| D-333 | 2026-10-12 | [REV-M0-T17签署交付](delivery/REV-M0-T17.md) | 交付 | qa-rerun-12 | 已本地验收 | ISSUE-013 / REV-M0-T17 | 无代码；结论与观察项 |
| D-334 | 2026-10-12 | [编辑租约交付](delivery/BE-M0-T12.md) | 交付 | lease-1 | in-review | ISSUE-018 / BE-M0-T12 | 120 秒租约入库；不标 done |
| D-335 | 2026-10-12 | [编辑租约代码说明](code/BE-M0-T12.md) | 说明 | lease-1 | 当前 | ISSUE-018 / BE-M0-T12 | 差量保存 chapter_lease；导入时不连接 |
| D-336 | 2026-10-12 | [编辑租约核对](testing/2026-10-12-be-m0-t12-leases.md) | 验证 | lease-1 | 已执行 | ISSUE-018 / BE-M0-T12 | 无库仍走内存；mysql 续期与过期接管 |
| D-337 | 2026-10-12 | [ISSUE-030](../issues/ISSUE-030.md) | 变更 | retry-n7-1 | in-review | ISSUE-030 / APP-M2-T002 | 503 SECRET_KEY_UNAVAILABLE 不重试。T002 仍 done。不标 closed |
| D-338 | 2026-10-12 | [密钥不可用交付](delivery/ISSUE-030.md) | 交付 | retry-n7-1 | in-review | ISSUE-030 / APP-M2-T002 | 只改 canRetryStatus。不改后台 |
| D-339 | 2026-10-12 | [密钥不可用说明](code/ISSUE-030.md) | 说明 | retry-n7-1 | 当前 | ISSUE-030 / APP-M2-T002 | 503 仅在该 code 时停止 |
| D-340 | 2026-10-12 | [密钥不可用核对](testing/2026-10-12-issue-030-secret-key-retry.md) | 验证 | retry-n7-1 | 已执行 | ISSUE-030 / APP-M2-T002 | 两码各 1 次；普通 503 与裸 502 仍重试 |
| D-341 | 2026-10-12 | [030同步表](governance/ISSUE-030-sync.md) | 治理 | retry-n7-1 | 已核对 | ISSUE-030 / APP-M2-T002 | 不改任务计数，不改冻结 JSON |
| D-342 | 2026-10-12 | [ISSUE-031](../issues/ISSUE-031.md) | 变更 | frozen-names-1 | closed | ISSUE-031 / BE-M0-T16 | QA ae6fd10，PM 15:32 确认 closed。BE-M0-T16 仍 in-review |
| D-343 | 2026-10-12 | [031同步记录](governance/ISSUE-031-sync.md) | 治理 | frozen-names-1 | 已核对 | ISSUE-031 / BE-M0-T16 | 不改三份基线快照。不改 docs/reference |
| D-344 | 2026-10-12 | [错误码名字交付](delivery/BE-M0-T16.md) | 交付 | frozen-names-1 | in-review | ISSUE-031 / BE-M0-T16 | 名单与运行时表对照；不标 done |
| D-345 | 2026-10-12 | [错误码名字代码说明](code/BE-M0-T16.md) | 说明 | frozen-names-1 | 当前 | ISSUE-031 / BE-M0-T16 | 导出不改写 FROZEN_NAMES |
| D-346 | 2026-10-12 | [错误码名字核对](testing/2026-10-12-issue-031-frozen-error-codes.md) | 验证 | frozen-names-1 | 已执行 | ISSUE-031 / BE-M0-T16 | 换码再导出后对照失败，已还原 |
| D-347 | 2026-10-12 | [错误码名字名单](../backend/bid-core/icg_demo/frozen_error_codes.py) | 后台 | frozen-names-1 | 当前 | ISSUE-031 / BE-M0-T16 | 143 个名字。导出 OpenAPI 不改写本文件 |
| D-348 | 2026-10-12 | [ISSUE-031错误码名单冻结签署](testing/2026-10-12-issue-031-frozen-names-signoff.md) | 验证 | qa-rerun-14 | 本地通过 | ISSUE-013 / REV-M0-T18 | 通过；O-1/O-2 P3 |
| D-349 | 2026-10-12 | [REV-M0-T18签署交付](delivery/REV-M0-T18.md) | 交付 | qa-rerun-14 | 已本地验收 | ISSUE-013 / REV-M0-T18 | 无代码；结论与观察项 |
| D-350 | 2026-10-12 | [BE-M0-T12编辑租约入库签署](testing/2026-10-12-be-m0-t12-lease-signoff.md) | 验证 | qa-rerun-15 | 本地通过 | ISSUE-013 / REV-M0-T19 | 通过；O-1/O-2 P3 |
| D-351 | 2026-10-12 | [REV-M0-T19签署交付](delivery/REV-M0-T19.md) | 交付 | qa-rerun-15 | 已本地验收 | ISSUE-013 / REV-M0-T19 | 无代码；结论与观察项 |
| D-352 | 2026-10-12 | [挂证据抽屉交付](delivery/APP-M2-T114.md) | 交付 | t114-drawer-3 | done | ISSUE-007 / APP-M2-T114 | QA f521950，PM 17:13 确认 done。T124 为 ready，本轮不实现。ISSUE-033 不关闭 |
| D-353 | 2026-10-12 | [挂证据抽屉说明](code/APP-M2-T114.md) | 说明 | t114-drawer-3 | 当前 | ISSUE-007 / APP-M2-T114 | 冲突刷新与过期刷新共用 reload，不另发 PATCH |
| D-354 | 2026-10-12 | [挂证据抽屉核对](testing/2026-10-12-app-m2-t114-evidence-drawer.md) | 验证 | t114-drawer-3 | 已执行 | ISSUE-007 / APP-M2-T114 | 单测 98；浏览器 14。含冲突后刷新再保存 |
| D-355 | 2026-10-12 | [T114同步表](governance/APP-M2-T114-sync.md) | 治理 | t114-drawer-3 | 已核对 | ISSUE-007 / APP-M2-T114 | QA f521950，PM 17:13 确认。随后看板为 381 项：49 done、7 in-review、7 in-progress、265 planned、48 blocked、5 ready |
| D-356 | 2026-10-12 | [ISSUE-022契约冻结复签](testing/2026-10-12-issue-022-freeze-signoff.md) | 验证 | qa-rerun-16 | 本地通过 | ISSUE-013 / REV-M0-T20 | 通过；O-1 P3 |
| D-357 | 2026-10-12 | [REV-M0-T20签署交付](delivery/REV-M0-T20.md) | 交付 | qa-rerun-16 | 已本地验收 | ISSUE-013 / REV-M0-T20 | 无代码；结论与观察项 |
| D-358 | 2026-10-12 | [项目聚合交付](delivery/BE-M0-T13.md) | 交付 | impl-4 | in-review | ISSUE-018 / BE-M0-T13 | 项目与分工入库；不标 done |
| D-359 | 2026-10-12 | [项目聚合代码说明](code/BE-M0-T13.md) | 说明 | impl-4 | 当前 | ISSUE-018 / BE-M0-T13 | 差量保存 demo_project；种子项目不插入 |
| D-360 | 2026-10-12 | [项目聚合核对](testing/2026-10-12-be-m0-t13-projects.md) | 验证 | impl-4 | 已执行 | ISSUE-018 / BE-M0-T13 | 无库仍跳过；mysql 跨进程与回滚 |
| D-361 | 2026-10-12 | [项目聚合迁移](../backend/bid-core/alembic/versions/0004_demo_project.py) | 后台 | impl-4 | 当前 | ISSUE-018 / BE-M0-T13 | demo_project 与 demo_project_team。可降回基线 |
| D-362 | 2026-10-12 | [编辑锁对齐](../issues/ISSUE-032.md) | 变更 | edit-lock-align-1 | new | ISSUE-032 / BE-M0-T17 | 有条件批准后对齐 edit_lock。负责人 backend。不删历史锁行 |
| D-363 | 2026-10-12 | [ISSUE-032同步](governance/ISSUE-032-sync.md) | 治理 | edit-lock-align-1 | 已核对 | ISSUE-032 / BE-M0-T17 | 新增 planned 卡。不改表 |
| D-364 | 2026-10-12 | [0a5b655重试修复签署](testing/2026-10-12-0a5b655-retry-signoff.md) | 验证 | qa-rerun-17 | 本地通过 | ISSUE-013 / REV-M0-T21 | 通过；无观察项 |
| D-365 | 2026-10-12 | [REV-M0-T21签署交付](delivery/REV-M0-T21.md) | 交付 | qa-rerun-17 | 已本地验收 | ISSUE-013 / REV-M0-T21 | 无代码；结论与观察项 |
| D-366 | 2026-10-12 | [挂证据规则](../issues/ISSUE-033.md) | 变更 | evidence-mount-2 | in-review | ISSUE-033 / BE-M0-T18 | 沿用已有错误码拒绝过期、仅供参考、缺协议和无权受限资料 |
| D-367 | 2026-10-12 | [ISSUE-033同步](governance/ISSUE-033-sync.md) | 治理 | evidence-mount-2 | 已核对 | ISSUE-033 / BE-M0-T18 | 卡片改为 in-review。冻结字段名仍在。不新增错误码 |
| D-368 | 2026-10-12 | [T114 e691405冲突刷新复签](testing/2026-10-12-app-m2-t114-e691405-signoff.md) | 验证 | qa-rerun-18 | 本地通过 | ISSUE-013 / REV-M0-T22 | 通过；缺协议/受限依赖 ISSUE-033 |
| D-369 | 2026-10-12 | [REV-M0-T22签署交付](delivery/REV-M0-T22.md) | 交付 | qa-rerun-18 | done | ISSUE-013 / REV-M0-T22 | QA f521950，PM 17:13 确认 done。观察项仍挂 ISSUE-033 |
| D-370 | 2026-10-12 | [BE-M0-T13项目聚合签署](testing/2026-10-12-be-m0-t13-signoff.md) | 验证 | qa-rerun-19 | 本地通过 | ISSUE-013 / REV-M0-T23 | 通过；O-1 P3 待 ISSUE-035 批准句 |
| D-371 | 2026-10-12 | [REV-M0-T23签署交付](delivery/REV-M0-T23.md) | 交付 | qa-rerun-19 | 已本地验收 | ISSUE-013 / REV-M0-T23 | 无代码；演示表待 ISSUE-035，不标 done |
| D-372 | 2026-10-12 | [T078内存片段发布签署](testing/2026-10-12-t078-snippet-signoff.md) | 验证 | qa-rerun-20 | done | ISSUE-013 / REV-M0-T24 | QA 19c4862，PM 17:20 确认 done。页面未做，不挡住 done。CI 38212117391 |
| D-373 | 2026-10-12 | [REV-M0-T24签署交付](delivery/REV-M0-T24.md) | 交付 | qa-rerun-20 | done | ISSUE-013 / REV-M0-T24 | QA 19c4862，PM 17:20 确认 done。无代码。页面未做，不挡住 done |
| D-374 | 2026-10-12 | [橙色标签对比](../issues/ISSUE-036.md) | 变更 | orange-tag-contrast-1 | in-review | ISSUE-036 | 前端橙色、金色和 warning 标签。P3。不新增任务卡。不标 closed |
| D-375 | 2026-10-12 | [橙色标签对比交付](delivery/ISSUE-036.md) | 交付 | orange-tag-contrast-1 | in-review | ISSUE-036 | 文字色改为 #9a5608。未合入 |
| D-376 | 2026-10-12 | [橙色标签对比说明](code/ISSUE-036.md) | 说明 | orange-tag-contrast-1 | 当前 | ISSUE-036 | 只改标签文字色。浅底保留 |
| D-377 | 2026-10-12 | [橙色标签对比核对](testing/2026-10-12-issue-036-orange-contrast.md) | 验证 | orange-tag-contrast-1 | 已执行 | ISSUE-036 | 改后 5.31:1 与 5.45:1。概览页可见橙色标签纳入 4.5:1 检查 |
| D-378 | 2026-10-12 | [ISSUE-036同步](governance/ISSUE-036-sync.md) | 治理 | orange-tag-contrast-1 | 已核对 | ISSUE-036 | 不新增任务卡。不改三份基线快照 |
| D-379 | 2026-10-12 | [T124依赖核对（含解除）](testing/2026-10-12-t124-dependencies.md) | 验证 | t124-ready-1 | 依赖解除 | ISSUE-022 / APP-M2-T124 | T124 为 ready，本轮不实现。T078 已 done（QA 19c4862，PM 17:20 确认）。运行时未接通 |
| D-380 | 2026-10-12 | [ISSUE-036橙色标签对比签署](testing/2026-10-12-issue-036-qa-signoff.md) | 验证 | qa-rerun-21 | 本地通过 | ISSUE-013 / REV-M0-T25 | 通过；ISSUE-036 不标 done |
| D-381 | 2026-10-12 | [REV-M0-T25签署交付](delivery/REV-M0-T25.md) | 交付 | qa-rerun-21 | 已本地验收 | ISSUE-013 / REV-M0-T25 | 无代码；结论与观察项 |
| D-382 | 2026-10-12 | [ISSUE-033规格复签](testing/2026-10-12-issue-033-spec-resign.md) | 验证 | qa-rerun-22 | 本地通过 | ISSUE-013 / REV-M0-T26 | 规格通过；运行时待后端 |
| D-383 | 2026-10-12 | [REV-M0-T26签署交付](delivery/REV-M0-T26.md) | 交付 | qa-rerun-22 | 已本地验收 | ISSUE-013 / REV-M0-T26 | 无代码；结论与观察项 |
| D-384 | 2026-10-12 | [ISSUE-028假服务核对](testing/2026-10-12-issue-028-fake-openai.md) | 验证 | model-config-fixture-1 | 已执行 | ISSUE-028 / AI-01 | 假端点记录请求头和 base_url。真实端点默认跳过 |
| D-385 | 2026-10-12 | [AI-01假服务说明](code/AI-01.md) | 说明 | model-config-fixture-1 | 当前 | ISSUE-028 / AI-01 | 只加测试夹具。不改 backend/bid-core。不标 done |
| D-386 | 2026-10-12 | [BE-M0-T11回执会话签署](testing/2026-10-12-be-m0-t11-qa-signoff.md) | 验证 | qa-rerun-23 | 本地通过 | ISSUE-013 / REV-M0-T28 | 通过；BE-M0-T11 / ISSUE-018 不标 done；T27 预留 |
| D-387 | 2026-10-12 | [REV-M0-T28签署交付](delivery/REV-M0-T28.md) | 交付 | qa-rerun-23 | 已本地验收 | ISSUE-013 / REV-M0-T28 | 无代码；结论与观察项 |
| D-388 | 2026-10-12 | [ISSUE-028 AC-02假端点签署](testing/2026-10-12-issue-028-ac02-qa-signoff.md) | 验证 | qa-rerun-24 | 本地通过 | ISSUE-013 / REV-M0-T29 | 通过；ISSUE-028 / AI-01 不标 done；路径规范化 hold |
| D-389 | 2026-10-12 | [REV-M0-T29签署交付](delivery/REV-M0-T29.md) | 交付 | qa-rerun-24 | 已本地验收 | ISSUE-013 / REV-M0-T29 | 无代码；结论与观察项 |
| D-390 | 2026-10-12 | [项目表对齐](../issues/ISSUE-035.md) | 变更 | bid-project-align-1 | new | ISSUE-035 / BE-M0-T19 | 有条件批准后对齐 bid_project。负责人 backend。不删历史行 |
| D-391 | 2026-10-12 | [ISSUE-035同步](governance/ISSUE-035-sync.md) | 治理 | bid-project-align-1 | 已核对 | ISSUE-035 / BE-M0-T19 | 新增 planned 卡。不改表 |
| D-392 | 2026-10-12 | [挂证据交付](delivery/BE-M0-T18.md) | 交付 | evidence-mount-2 | in-review | ISSUE-033 / BE-M0-T18 | 不标 done。不新增错误码 |
| D-393 | 2026-10-12 | [挂证据代码说明](code/BE-M0-T18.md) | 说明 | evidence-mount-2 | 当前 | ISSUE-033 / BE-M0-T18 | 协议有无从合作方附件推导。授权行不进资料对象 |
| D-394 | 2026-10-12 | [挂证据核对](testing/2026-10-12-be-m0-t18-evidence-mount.md) | 验证 | evidence-mount-2 | 已执行 | ISSUE-033 / BE-M0-T18 | 无库后台测试。不新增错误码 |
| D-395 | 2026-10-12 | [挂证据测试](../tests/backend/test_evidence_mount.py) | 验证代码 | evidence-mount-2 | 4项通过 | ISSUE-033 / BE-M0-T18 | 过期、缺协议、仅供参考和受限资料 |
| D-396 | 2026-10-12 | [ISSUE-028 AC-03证据](testing/2026-10-12-issue-028-ac03-evidence.md) | 验证 | model-config-fixture-1 | 已由 QA 勾选 | ISSUE-028 / AI-01 | 夹具提交不改 OpenAPI 与依赖。尖端 OpenAPI 差异属于 af51151；见 REV-M0-T30 |
| D-397 | 2026-10-12 | [ISSUE-028 AC-03签署](testing/2026-10-12-issue-028-ac03-qa-signoff.md) | 验证 | qa-rerun-25 | 本地通过 | ISSUE-013 / REV-M0-T30 | 通过；ISSUE-028 / AI-01 不标 done；AC-04 仍等待 |
| D-398 | 2026-10-12 | [REV-M0-T30签署交付](delivery/REV-M0-T30.md) | 交付 | qa-rerun-25 | 已本地验收 | ISSUE-013 / REV-M0-T30 | 无代码；结论与观察项 |

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
| 2026-10-12 | ISSUE-005 | ARCHITECTURE 补一句：v1 错误体和 24 小时幂等回执已提交复查，无驱动、迁移或表，测试仍用内存仓库。接口约定补登到同步表。T02 与 T03 由项目经理于 10-12 12:28 在 QA 签署后确认；Issue 保持 in-progress |
| 2026-10-12 | ISSUE-018 / BE-M0-T08；ISSUE-021 / BE-M0-T09 | MySQL 8 方案 in-review，要求回执和会话跨进程且重启后仍在。旧接口任务 planned，并登记 E2E-D5。与 T124 的 blocked 合并后为 356项23done、6in-review、7in-progress、266planned、50blocked、4ready。未加依赖，未改 PRD 与 ROADMAP |
| 2026-10-12 | ISSUE-019 / REV-M0-T06 | 离线检查增加并行 e2e 作业，continue-on-error，不阻断其他作业。计划 2026-10-19 再评估改为必需。未改用例，ISSUE-019 仍为 in-review |
| 2026-10-12 | ISSUE-022 / APP-M2-T124 | 大纲契约草案为 draft, pending backend review，Issue 改为 in-review。T124 仍 blocked，任务计数保持 356项23done、6in-review、7in-progress、266planned、50blocked、4ready。startGeneration 对齐尚未实现的 BE-M0-T06。T078 只记录独立存储计划 |
| 2026-10-12 | ISSUE-009 / APP-M2-T001 | QA退回后的浅色内容、顶栏和前进/后退修复，重新提交 in-review。356项计数不变。未改基线正文，未改后台，未标 done |
| 2026-10-12 | ISSUE-023 / BE-M0-T10；ISSUE-018 | 项目经理批准四项依赖。连接与空基线为 in-review，T11～T13 planned。360项23done、7in-review、7in-progress、269planned、50blocked、4ready。未改 PRD、ROADMAP、ARCHITECTURE，未改公网 CI |
| 2026-10-12 | ISSUE-009 / APP-M2-T002 | 请求层提交 in-review。章节版本的 Idempotency-Key 与正文 idempotency_key 相同。360项23done、8in-review、7in-progress、268planned、50blocked、4ready。未改 PRD、ROADMAP、ARCHITECTURE、PROJECT_BRIEF，未改后台，未标 done |
| 2026-10-12 | ISSUE-013 / REV-M0-T09 | QA签署BE-M0-T08与BE-M0-T10（两卡仍in-review待项目经理标done）；361项24done |
| 2026-10-12 | ISSUE-022 / APP-M2-T124 | 按后台复核改草案：独立 JobStatus、SSE 与 cancelJob、按操作列错误、ETag。三个旧 POST 在说明里标 deprecated。T078 路径改为 snippet-publications。仍无运行时。并入 b364cd1 后任务计数仍为 361项24done、8in-review、7in-progress、268planned、50blocked、4ready。未改 PRD、ROADMAP、PROJECT_BRIEF 的任务计数 |
| 2026-10-12 | ISSUE-026 | PRD、ROADMAP、PROJECT_BRIEF 的任务计数改为 361项26done、6in-review、7in-progress、268planned、50blocked、4ready。APP-M2 其余 255 张 planned。并入 b465316 后 T08 与 T10 为 done。不新增任务，不改请求层重试，不改后台。Issue 为 in-review |
| 2026-10-12 | ISSUE-025 / BE-M0-T14 | 增加 backend-mysql。运行时密码，mysql:8.4，utf8mb4 / utf8mb4_unicode_ci。新增一卡后为 362项26done、7in-review、7in-progress、268planned、50blocked、4ready，三份计数字句跟着改。ISSUE-018 与 ISSUE-026 仍不关闭 |
| 2026-10-12 | ISSUE-010 / AI-01；ISSUE-028；ISSUE-029 | 用户决定配置页对话模型、RAGFlow 自带嵌入与向量库、生产生成仅内网。ISSUE-010 改为 closed，AI-01 改为 in-review。看板改为 362项26done、8in-review、7in-progress、268planned、49blocked、4ready。不改 PRD、ROADMAP、PROJECT_BRIEF 里 ISSUE-025 写下的 362 项、7 in-review、50 blocked。不改运行代码，不加依赖，不改 OpenAPI |
| 2026-10-12 | ISSUE-025 / BE-M0-T14 | 核对记录补记 `b91d331` 的作业 https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/38207508936 ：backend-mysql 成功，pytest 2 passed、320 deselected，junit tests=2 skipped=0 failures=0 errors=0。状态仍 in-review。不改任务计数 |
| 2026-10-12 | ISSUE-009 / APP-M2-T002 | 带 MODEL_UNAVAILABLE 的 502 不自动重试，立刻显示追踪号。裸网关 502、503 和网络错误仍复用同一把 Idempotency-Key。前端 90 项通过。看板仍为 362项26done、8in-review、7in-progress、268planned、49blocked、4ready。三份基线仍是 7in-review、50blocked。未改 OpenAPI、后台和三份基线正文。仍为 in-review |
| 2026-10-12 | ISSUE-026 | AI-01 进入 in-review 后，PRD、ROADMAP、PROJECT_BRIEF 改为 362项26done、8in-review、7in-progress、268planned、49blocked、4ready。不新增任务，不改 api.ts，不改后台。Issue 仍为 in-review |
| 2026-10-12 | ISSUE-027 / BE-M0-T15；ISSUE-023 | Word 默认版式提交 in-review。BE-M0-T14 仍是托管 MySQL 作业。任务计数改为 363项26done、9in-review、7in-progress、268planned、49blocked、4ready。ISSUE-023 由项目经理在 QA 签署 16cf971 后确认，状态为 closed。未改 ARCHITECTURE，未改 docs/reference |
| 2026-10-12 | ISSUE-028 | Provider 侧保留读取配置、启动快照、local/cloud 路由、敏感约束、流式/JSON、错误映射和 `job.model_call`。存储、字段定义、API、加密、If-Match/幂等改引 ISSUE-024，字段提案以 ISSUE-024 为准。不创建 ISSUE-024 文件。不改任务计数，仍为 363项26done、9in-review、7in-progress、268planned、49blocked、4ready |
| 2026-10-12 | ISSUE-009 / APP-M2-T001 | E2E-D7：收起侧栏时展开按钮移到 logo 右侧。1280/1440/1680、浅色和深色点击后菜单可见。Playwright 12 passed。仍 in-review，不改后台，不改任务计数 |
| 2026-10-12 | ISSUE-009 / APP-M2-T002 | T002-F1：没有 Idempotency-Key 的写入不自动重试。GET 和有键写入仍重试；MODEL_UNAVAILABLE 仍只发一次。ISSUE-021 给旧接口补键后这条限制解除。前端 92 项通过。仍 in-review，不改后台，不改任务计数 |
| 2026-10-12 | ISSUE-027 / BE-M0-T15 | 封面下一页分节、无标题正文不重复封面标题、目录标题与占位文字、承诺函封面项目名称、封面标题三种属性都是方正小标宋。规格记入 standards/word-default-style.md。不改任务计数 |
| 2026-10-12 | ISSUE-009 / APP-M2-T001 | E2E-D8：次要文字改为 #4e5969，待办圆圈改为 #9a5608，对比度至少 4.5:1。Playwright 13 passed。仍 in-review，不改后台，不改任务计数 |
| 2026-10-12 | ISSUE-013 / REV-M0-T10 | QA签署BE-M0-T15 Word默认版式XML核对（T15仍in-review待用户确认）；364项27done |
| 2026-10-12 | ISSUE-026 | 在 84a3fca 重数：看板 364项27done、9in-review、7in-progress、268planned、49blocked、4ready。PRD、ROADMAP、PROJECT_BRIEF 从 363项26done 改成同一组。不新增任务，不改 api.ts，不改后台，不改 docs/reference。Issue 仍为 in-review |
| 2026-10-12 | ISSUE-022 / APP-M2-T124 | 复审补充草案：startGeneration 引用 403 与 503，503 不自动重试；确认与启动列 423；JobEvent 增加状态、进度、终态；JobStatus 增加 recoverable；cancelJob 不强制 Location；getJob 与 SSE 去掉 403。状态仍是 draft, pending backend review。ISSUE-022 仍 in-review，T124 仍 blocked。不改 PRD、ROADMAP、PROJECT_BRIEF 的任务计数，不改运行代码 |
| 2026-10-12 | ISSUE-013 / REV-M0-T11 | QA复验签署APP-M2-T001与APP-M2-T002通过（两卡仍in-review待项目经理标done）；365项28done |
| 2026-10-12 | ISSUE-013 / REV-M0-T12 | QA签署BE-M0-T14托管MySQL CI通过（T14与ISSUE-025仍in-review待项目经理标done）；366项29done |
| 2026-10-12 | ISSUE-022 / APP-M2-T078 | 方案补两句：GET 返回 ETag，供 If-Match 使用；被拦截的发布仍算成功，必须记下幂等回执。仍不写代码。T078 仍 planned，T124 仍 blocked。不改任务计数 |
| 2026-10-12 | ISSUE-027 / BE-M0-T15 | Q1 正文首行缩进补 firstLine=560；Q2 无标题时不写目录和 TOC 域；Q3 规格改为中文：docx 不能指定缺失字体的替换字体，由 Word 或 WPS 决定，要保证效果需安装方正小标宋。不新增任务，不改变卡片状态。PRD、ROADMAP、ARCHITECTURE、PROJECT_BRIEF 未改 |
| 2026-10-12 | ISSUE-013 / REV-M0-T10 | QA复核BE-M0-T15 Q1～Q3（034b184/f989af7）通过，检查器补三项，样张覆盖；不新增任务、不改卡片状态 |
| 2026-10-12 | ISSUE-013 / REV-M0-T13 | QA签署：ISSUE-026快照规则签署，通过（被验卡/Issue状态不变，待项目经理设置） |
| 2026-10-12 | ISSUE-013 / REV-M0-T14 | QA签署：ISSUE-014 ProLayout签署，通过（被验卡/Issue状态不变，待项目经理设置） |
| 2026-10-12 | ISSUE-013 / REV-M0-T15 | QA签署：ISSUE-020路由分包签署，通过（被验卡/Issue状态不变，待项目经理设置） |
| 2026-10-12 | ISSUE-013 / REV-M0-T16 | QA签署：ISSUE-016检索骨架签署，通过（被验卡/Issue状态不变，待项目经理设置） |
| 2026-10-12 | ISSUE-013 / REV-M0-T17 | QA签署：ISSUE-028模型配置设计签署，通过（附P2）（被验卡/Issue状态不变，待项目经理设置） |
| 2026-10-12 | ISSUE-013 / REV-M0-T18 | QA签署：ISSUE-031错误码名单冻结签署，通过（被验卡/Issue状态不变，待项目经理设置） |
| 2026-10-12 | ISSUE-013 / REV-M0-T19 | QA签署：BE-M0-T12编辑租约入库签署，通过（被验卡/Issue状态不变，待项目经理设置） |
| 2026-10-12 | ISSUE-013 / REV-M0-T20 | QA签署：ISSUE-022契约冻结复签，通过（被验卡/Issue状态不变，待项目经理设置） |
| 2026-10-12 | ISSUE-013 / REV-M0-T21 | QA签署：0a5b655重试修复签署，通过（被验卡/Issue状态不变，待项目经理设置） |
| 2026-10-12 | ISSUE-013 / REV-M0-T22 | QA签署：APP-M2-T114 e691405 冲突刷新复签，通过（缺协议、受限依赖 ISSUE-033；被验卡/本卡不标 done，待项目经理设置） |
| 2026-10-12 | ISSUE-025 / BE-M0-T14 | 依据 QA 签署 b20b844 将 BE-M0-T14 标为 done、ISSUE-025 标为 closed。守卫改为任一跳过即失败。不再导出 ICG_MYSQL_PASSWORD。BE-M0-T11 记下业务表出现后的 downgrade 再 upgrade。看板改为 366项30done、8in-review、7in-progress、268planned、49blocked、4ready。PRD、ROADMAP 计数字句不改 |
| 2026-10-12 | ISSUE-025 / BE-M0-T14 | 交付里的任务计数改为截至提交 3bb311a 的快照，并写明之后以任务看板为准。不改看板，不改卡片状态 |
| 2026-10-12 | ISSUE-026 | 在 3bb311a 重数：看板 366项30done、8in-review。项目经理在群里确认后，APP-M2-T001 与 APP-M2-T002 标为 done，成为 366项32done、6in-review、7in-progress、268planned、49blocked、4ready。PRD、ROADMAP、PROJECT_BRIEF 改为 as of commit 3bb311a 的里程碑快照，并写明任务看板是准绳、只在里程碑更新。规则写入 WORKFLOW 第4节。检查程序不比较快照与活看板，未改脚本。Issue 仍为 in-review。不改 docs/reference |
| 2026-10-12 | ISSUE-022 / APP-M2-T078 | 按方案实现进程内片段发布。T078 改为 in-review，未标 done。并入 c9a3cd5 后看板改为 366项32done、7in-review、7in-progress、267planned、49blocked、4ready。不改 PRD、ROADMAP、PROJECT_BRIEF 的里程碑快照。T124 仍 blocked。pytest 346 passed、2 skipped |
| 2026-10-12 | ISSUE-018 / BE-M0-T11 | 回执和登录会话入库，状态 in-review。含 downgrade base 再 upgrade head。看板在 e6215d4 的 32 done、7 in-review、267 planned 上改为 366项32done、8in-review、7in-progress、266planned、49blocked、4ready。不改 PRD、ROADMAP、PROJECT_BRIEF 的里程碑快照，不改 .github。ISSUE-018 仍 in-progress。BE-M0-T15 仍 in-review |
| 2026-10-12 | ISSUE-024；ISSUE-022 | 登记 ISSUE-024，状态 new，负责人 backend。冻结表增加 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL` 与 503 `SECRET_KEY_UNAVAILABLE`（非瞬时，无 Retry-After）。不写入 errors.py 与 OpenAPI。复审附件原文未随队列送达，B2 与 B3 记在复审记录末尾。不改任务计数。ISSUE-028 仍 in-review |
| 2026-10-12 | ISSUE-022 | 把 046f8e5/fe9582c 的后台复审原文写入 ISSUE-022-backend-rereview.md，文末附上项目经理对 B2、B3 的决定。403 与 503 仍只在 ISSUE-024 的冻结表里。不改 OpenAPI，不改任务计数 |
| 2026-10-12 | ISSUE-022；ISSUE-024 | 复审原文换成含 c6948c0 第三轮的版本。两码写入 V1Error.code 枚举和 x-error-status，使 403/503 响应体可通过校验。不改 ISSUE-022 的操作说明，不改任务计数 |
| 2026-10-12 | ISSUE-024 | PM 批准 D-1。ISSUE-024 拥有 `stream_enabled`（布尔，默认 true）和 `json_mode_enabled`（布尔，默认 false）。二者纳入 `revision` 乐观锁，并在任务开始时随配置快照。ISSUE-028 只引用这两个名字，不重定义。不再把这两个开关的字段名交给 ISSUE-028。不改运行代码，不改任务计数 |
| 2026-10-12 | ISSUE-009 / ISSUE-014 / ISSUE-020 / ISSUE-026 | 项目经理在 QA 签署后确认关闭：ISSUE-009（d55d507，REV-M0-T11）、ISSUE-014（173c39f，REV-M0-T14）、ISSUE-020（dcca509，REV-M0-T15）、ISSUE-026（9bcde17，REV-M0-T13）。关联卡 APP-M2-T001 与 APP-M2-T002 已为 done，不改其他卡片。看板手写摘要改为 371项37done、8in-review、7in-progress、266planned、49blocked、4ready。不改 PRD、ROADMAP、PROJECT_BRIEF 的里程碑快照。不改 ISSUE-013、ISSUE-016、ISSUE-028 与 AI-03 |
| 2026-10-12 | ISSUE-022 / APP-M2-T124 | 第三轮复审后把大纲与任务契约标为 frozen。全局重试说明和 Idempotency-Key 说明排除 502 MODEL_UNAVAILABLE 与 503 SECRET_KEY_UNAVAILABLE。新增 423 与 503 不列 Idempotent-Replayed。N8 留到 BE-M0-T06。保留已写入枚举的两码。ISSUE-022 仍 in-review，T124 仍 blocked。不改 PRD、ROADMAP、PROJECT_BRIEF |
| 2026-10-12 | ISSUE-017 / OPS-M0-T02 | 用户 10-12 14:34 确认。ISSUE-017 改为 closed，OPS-M0-T02 改为 done。重排定为 RAGFlow 自带的重排器，重排模型在 RAGFlow 内配置。截至 73fde1e 为 371项37done、8in-review；本提交后看板为 371项38done、7in-review、7in-progress、266planned、49blocked、4ready。之后以任务看板为准。未部署。不改 ISSUE-029，不改 ISSUE-010 正文 |
| 2026-10-12 | ISSUE-028 / AI-01；ISSUE-029 | QA P3（REV-M0-T17，f5af6db）：决定记录改为 ISSUE-024 已由后台建档并拥有模型配置字段。流式与 JSON 模式开关的字段名归 ISSUE-024（后台决定，D-1），028 只引用、不定义。AI-01 补未勾选验收：敏感项目使用非本地模型返回 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`（由 409 改为 403）。RAGFlow 适配器设计记下 ISSUE-016 QA P3：路径 C 不按查询词过滤，实现适配器时再改。不改代码，不改任务计数。ISSUE-028 仍 in-review |
| 2026-10-12 | ISSUE-028 | 决定记录与 ISSUE-028 改为引用 ISSUE-024 已定义的 `stream_enabled`（布尔，默认 true）和 `json_mode_enabled`（布尔，默认 false）。二者纳入 `revision` 乐观锁，并在任务开始时随配置快照。028 不重定义。不改 ISSUE-024 正文，不改代码，不改任务计数。ISSUE-028 仍 in-review |
| 2026-10-12 | ISSUE-016 / AI-03；ISSUE-029 | 依据 QA 签署 2fe6198（REV-M0-T16）将 ISSUE-016 标为 closed、AI-03 标为 done。用户 10-12 14:34 确认后将 ISSUE-029 标为 closed，重排定为 RAGFlow 自带的重排器，重排模型在 RAGFlow 内配置。看板改为 371项39done、6in-review、7in-progress、266planned、49blocked、4ready。不改 PRD、ROADMAP、PROJECT_BRIEF 的里程碑快照。不改 ISSUE-017 与 OPS-M0-T02。不改检索代码。ISSUE-028 仍 in-review |
| 2026-10-12 | ISSUE-028 | `3e1445e` 已把 D-1 字段写进 ISSUE-024。ISSUE-028 文档只链接 `stream_enabled` 与 `json_mode_enabled`，不抄定义。不改 ISSUE-024 正文，不改代码，不改任务计数。ISSUE-028 仍 in-review |
| 2026-10-12 | 前端 PRD 开头 | 项目经理规定后续开发以 `docs/reference/product/prd-mvp-v1.8.md` 与 `kb-data-dictionary-v1.9.md` 为准。`docs/PRD.md` 第27行改为链接这两份，不再写 PRD v1.4 与字典 v1.5。不新开 Issue。不改第19行里程碑计数，不改治理块，不改 `docs/reference/`，不改其他 v1.4 / v1.5 句子 |
| 2026-10-12 | ISSUE-018 / BE-M0-T12 | 编辑租约入库，状态 in-review。续期后占用者不变，过期后其他会话可以接管。方案第 5 节增加字典 v1.9 字段对照表，偏差需要项目经理批准。看板从 371项39done、6in-review、266planned 改为 371项39done、7in-review、7in-progress、265planned、49blocked、4ready。不改 PRD、ROADMAP、PROJECT_BRIEF，不改 docs/reference，不改 .github。ISSUE-018 仍 in-progress。T13 仍 planned |
| 2026-10-12 | ISSUE-030 / APP-M2-T002 | `canRetryStatus` 对 503 `SECRET_KEY_UNAVAILABLE` 返回 false，与 502 `MODEL_UNAVAILABLE` 一样只发一次。普通 503 和裸 502 仍重试。T002 仍为 done。不改任务计数，不改后台，不改冻结 JSON，不改 `docs/reference/`。ISSUE-030 为 in-review |
| 2026-10-12 | ISSUE-031 / BE-M0-T16 | 冻结 143 个错误码名字。`set(ERROR_STATUS)` 与 spec 枚举都必须等于 `FROZEN_NAMES`。增删错误码必须在同一提交更新名单。看板从 371项39done、7in-review 改为 372项39done、8in-review、7in-progress、265planned、49blocked、4ready。不改 PRD、ROADMAP、PROJECT_BRIEF，不改 docs/reference，不改 .github。ISSUE-030 仍为 in-review。ISSUE-031 与 BE-M0-T16 为 in-review |
| 2026-10-12 | ISSUE-022 | QA：`spec/openapi/README.md` 的 502/503 自动重试说明补上 N7，502 MODEL_UNAVAILABLE 与 503 SECRET_KEY_UNAVAILABLE 不自动重试。`x-idempotency.retry` 追加没有 Idempotency-Key 的写入不自动重试。不改错误码计数，不改 errors.py，不改 PRD、ROADMAP、PROJECT_BRIEF 的任务计数。ISSUE-022 仍 in-review |
| 2026-10-12 | ISSUE-007 / APP-M2-T114 | 挂证据抽屉改为 in-review。分组、拦截和保存接到响应矩阵。接口仍是 `73fde1e` 的条款 `evidence_ids`。并入 BE-M0-T16 与 REV-M0-T18、T19 后看板为 374 项、41 done、9 in-review、264 planned。T124 仍 blocked。不改后台，不改冻结 JSON，不改 `docs/reference/`，不改三份基线快照。不标 done |
| 2026-10-12 | ISSUE-022 | 依据 QA 0254102（REV-M0-T20），PM 15:36 确认，ISSUE-022 标为 closed。示例接口约定第 45 行的 502/503 自动重试补上 N7：502 MODEL_UNAVAILABLE 与 503 SECRET_KEY_UNAVAILABLE 不自动重试。T124 仍 blocked。T114 仍 in-review。不改其他卡片状态，不改 PRD、ROADMAP、PROJECT_BRIEF 的任务计数 |
| 2026-10-12 | ISSUE-018 / BE-M0-T13 | 项目聚合入库，状态 in-review。另一个进程能看见已提交项目，看不见其新章节。方案第 6 节增加字典 v1.9 字段对照表，偏差需要项目经理批准。重数后看板为 375 项：42 done、9 in-review、7 in-progress、264 planned、49 blocked、4 ready。本提交把 T13 改为 in-review 后为 375 项：42 done、10 in-review、7 in-progress、263 planned、49 blocked、4 ready。不改 PRD、ROADMAP、PROJECT_BRIEF，不改 docs/reference，不改 .github。ISSUE-018 仍 in-progress。章节及其他聚合仍在内存 |
| 2026-10-12 | ISSUE-007 / APP-M2-T114 | QA 复查：过期挂接在抽屉已挂列表显示“证据失效”，并提供刷新，重新读取资料候选和本行已挂编号。并入 T13 后看板为 375 项、42 done、10 in-review、263 planned、49 blocked、4 ready。REV 20 项中 18 项已本地验收。缺协议字段、智能匹配和规则 2 端到端记在交付后续，引用后台 ISSUE-033，不新建。T114 仍 in-review。T124 仍 blocked。不改后台，不改冻结 JSON，不改三份基线快照 |
| 2026-10-12 | ISSUE-032 / BE-M0-T17 | 项目经理有条件批准方案第 5 节偏差。登记 ISSUE-032，负责人 backend，状态 new。新增 BE-M0-T17，状态 planned，排在 T13 之后，且要等 `bid_outline_node`、`sys_user`、`company` 存在。迁移须保留历史锁行。对照表下补上「偏差已获 PM 有条件批准，待 ISSUE-032 对齐」。看板改为 376 项：42 done、10 in-review、7 in-progress、264 planned、49 blocked、4 ready。不改表，不改 PRD、ROADMAP、PROJECT_BRIEF，不改 docs/reference，不改 .github。T12 与 T13 仍 in-review。T114 仍 in-review |
| 2026-10-12 | ISSUE-018 / BE-M0-T12；ISSUE-031 | 依据 QA ae6fd10，PM 15:32 确认，BE-M0-T12 标为 done，ISSUE-031 标为 closed。BE-M0-T16 仍 in-review。补 mysql 标记的释放测试：释放后行删除，另一个会话可以再取得。相对签署时的 8 条，这一条是 8→9；并入 T13 的 3 条项目测试后，backend-mysql 为 12 passed、skipped=0。未设连接串时 351 passed、12 skipped。`export_openapi.py` 重跑前须保住草案操作和 deprecated 标注，脚本本轮不改。并入 REV-M0-T21 后看板为 377 项：44 done、9 in-review、7 in-progress、264 planned、49 blocked、4 ready。不改 PRD、ROADMAP、PROJECT_BRIEF，不改 docs/reference，不改 .github。T13 仍 in-review。ISSUE-018 仍 in-progress |
| 2026-10-12 | ISSUE-033 / BE-M0-T18 | 登记挂证据规则。负责人 backend，状态 new。新增 BE-M0-T18，状态 planned，排在 T13 之后。项目经理暂停后撤下字典对照和错误码建议，不改接口。规格增量由 AI bot 另交，实现后 QA 重签。看板为 378 项：44 done、9 in-review、7 in-progress、265 planned、49 blocked、4 ready。不改 PRD、ROADMAP、PROJECT_BRIEF，不改 docs/reference，不改 .github。T13 仍 in-review。T114 仍 in-review |
| 2026-10-12 | ISSUE-013 / REV-M0-T21 | 依据 QA 3e91aee，PM 恢复确认，REV-M0-T21 标为 done。看板计数不变：该卡已是 done。ISSUE-030 仍 in-review。APP-M2-T002 仍 done。不改 PRD、ROADMAP、PROJECT_BRIEF，不改接口 |
| 2026-10-12 | ISSUE-007 / APP-M2-T114 | QA 验收②：冲突提示“本行已被他人修改，请刷新后再保存”旁边补刷新。刷新重读本行后可以再保存。浏览器覆盖另一会话先保存、出现冲突、刷新、再保存成功。不新开 Issue。不改 ISSUE-033。T114 仍 in-review。看板计数不改，仍是 378 项、44 done、9 in-review、265 planned |
| 2026-10-12 | ISSUE-033 / BE-M0-T18 | 按字典 v1.9 把挂证据字段写入冻结契约：`source_tier`、`is_restricted`、派生的 `agreement_present`，以及对照 `bid_deadline_at` 的 `valid_to` / `is_long_term`。挂接拒绝复用 409 `EVIDENCE_EXPIRED`、409 `EVIDENCE_NOT_USABLE`、403 `FORBIDDEN`。不新增错误码，错误码仍是 143。ISSUE-033 改为 in-progress。BE-M0-T18 仍 planned。不改后台应用代码，不改 PRD、ROADMAP、PROJECT_BRIEF 的任务计数。不标 closed |
| 2026-10-12 | ISSUE-013 / REV-M0-T23 | QA签署：BE-M0-T13项目聚合行为验收，通过（演示表待 ISSUE-035；被验卡/Issue 状态不变） |
| 2026-10-12 | ISSUE-013 / REV-M0-T24 | QA签署：APP-M2-T078内存片段发布，通过（页面未做；被验卡/本卡不标 done） |
| 2026-10-12 | ISSUE-013 / REV-M0-T25 | QA签署：ISSUE-036橙色标签对比，通过（被验 Issue 不标 done，待项目经理设置） |
| 2026-10-12 | ISSUE-013 / REV-M0-T26 | QA签署：ISSUE-033规格增量契约复签，通过（运行时待后端；ISSUE-033 不标 closed） |
| 2026-10-12 | ISSUE-007 / APP-M2-T114；ISSUE-013 / REV-M0-T22；ISSUE-036 | 项目经理确认 APP-M2-T114 与 REV-M0-T22 为 done，依据是 QA f521950，PM 17:13 确认。并入 REV-M0-T23、T24 后看板为 381 项。本提交改为 381 项：47 done、9 in-review、7 in-progress、265 planned、49 blocked、4 ready。T124 仍 blocked，因为 T078 仍 in-review 未 done。缺协议、受限、智能匹配和规则 2 端到端仍挂 ISSUE-033，不关闭。另登记 ISSUE-036，把橙色、金色和 warning 标签文字改为 #9a5608，状态 in-review，不新增任务卡。不改 PRD、ROADMAP、PROJECT_BRIEF 的里程碑快照，不改 docs/reference，不改后台 |
| 2026-10-12 | ISSUE-022 / APP-M2-T124 | PM 17:20：T078 与 T114 均 done 后，T124 解除 blocked 改为 ready。看板 381 项：47 done、9 in-review、7 in-progress、265 planned、48 blocked、5 ready。本提交不改 T078/REV-M0-T24 状态行（由前端提交；T114/REV-M0-T22 已 done）。不改运行时，不改模型输入，不改 PRD、ROADMAP、PROJECT_BRIEF 里程碑快照 |
| 2026-10-12 | ISSUE-022 / APP-M2-T078；ISSUE-013 / REV-M0-T24 | 项目经理确认 APP-M2-T078 与 REV-M0-T24 为 done，依据是 QA 19c4862，PM 17:20 确认。范围只含内存片段发布层。页面未做，不挡住 done。T124 改为 ready，本轮不实现。看板改为 381 项：49 done、7 in-review、7 in-progress、265 planned、48 blocked、5 ready。ISSUE-022 保持 closed。ISSUE-033 不关闭。不改 PRD、ROADMAP、PROJECT_BRIEF 的里程碑快照，不改 docs/reference，不改产品代码 |
| 2026-10-12 | ISSUE-028 / AI-01 | AC-02 假 OpenAI 兼容服务已编码。它记录请求头，并从路径还原实际 `base_url`。真实端点须 `ICG_RUN_REAL_MODEL_TESTS=1`，默认跳过。不改 `backend/bid-core`，不改 OpenAPI，不加依赖，不改错误码名单。ISSUE-028 与 AI-01 仍 in-review。ISSUE-010 仍 closed。不改 PRD、ROADMAP、PROJECT_BRIEF 的任务计数。不标 closed |
| 2026-10-12 | ISSUE-013 / REV-M0-T28 | QA签署：BE-M0-T11回执与会话入库，通过（被验卡/ISSUE-018 不标 done；T27 预留给 PR #4） |
| 2026-10-12 | ISSUE-013 / REV-M0-T29 | QA签署：ISSUE-028 AC-02假端点夹具，通过（ISSUE-028 / AI-01 不标 done；路径规范化 hold） |
| 2026-10-12 | ISSUE-033 / BE-M0-T18；ISSUE-035 / BE-M0-T19 | 项目经理批准挂证据沿用已有错误码，并有条件批准方案第 6 节偏差。BE-M0-T18 改为 in-review：过期为 409 EVIDENCE_EXPIRED，仅供参考和缺协议为 409 EVIDENCE_NOT_USABLE 且说明不同，无权受限资料为 403 FORBIDDEN。字段名是 is_restricted，与冻结的 EvidenceMountFields 一致。不新增错误码。登记 ISSUE-035，状态 new，BE-M0-T19 为 planned，等正式项目表和成员表存在后再迁移，保留历史行。对照表下补上「偏差已获 PM 有条件批准，待 ISSUE-035 对齐」。看板为 386 项：49 done、12 in-review、7 in-progress、265 planned、48 blocked、5 ready。不改 PRD、ROADMAP、PROJECT_BRIEF，不改 docs/reference，不改 .github。T13 仍 in-review。T078 与 T114 保持上游 done。T124 保持 ready。不另开 ISSUE-034。ISSUE-036 保持上游 in-review |
| 2026-10-12 | ISSUE-018 / BE-M0-T13；ISSUE-013 / REV-M0-T23 | 项目经理确认 BE-M0-T13 与 REV-M0-T23 为 done，依据是 QA ae38ec3，PM 17:16 确认。ISSUE-018 仍为 in-progress。ISSUE-035 仍为 new，BE-M0-T19 仍为 planned。ISSUE-033 与 BE-M0-T18 仍为 in-review。看板为 386 项：50 done、11 in-review、7 in-progress、265 planned、48 blocked、5 ready。BE-M0 为 8/19 done。不改 PRD、ROADMAP、PROJECT_BRIEF，不改 docs/reference，不改 .github |
| 2026-10-12 | ISSUE-028 / AI-01 | AC-03 证据已备，待 QA 勾选。夹具提交 `9e3fcdd` 不改 `spec/openapi/demo-v1.json` 与 `backend/bid-core/requirements.txt`。尖端 `20f2b92` 上这两份依赖与 `openai_model.py` 的 blob 仍相同；OpenAPI 差异只来自 `af51151`。ISSUE-024 与 AC-04 仍等待。路径规范化 hold，真模型冒烟另计。不改任务计数。ISSUE-028 与 AI-01 仍 in-review。不标 closed |
| 2026-10-12 | ISSUE-019 / REV-M0-T06 | 用户与项目经理确认后，offline-check 的 e2e 作业去掉 continue-on-error，失败会阻断工作流。依据是 D3/D4 已修复，用例已无 test.fail()，运行 38205346950 为 11 passed。超时、权限和产物上传不变。不改任务计数。ISSUE-019 与 REV-M0-T06 仍 in-review。不改 PRD、ROADMAP、ARCHITECTURE、PROJECT_BRIEF |
| 2026-10-12 | ISSUE-013 / REV-M0-T30 | QA签署：ISSUE-028 AC-03 OpenAPI/依赖/演示替身，通过（独立复跑 be3ce98；ISSUE-028 / AI-01 不标 done；AC-04 仍等待） |
| 2026-10-12 | ISSUE-027 / BE-M0-T15 | 项目经理确认 BE-M0-T15 为 done，依据是用户已在 Word/WPS 目视 OK，PM 18:01 确认。ISSUE-027 标为 closed。看板为 387 项：51 done、11 in-review、7 in-progress、265 planned、48 blocked、5 ready。BE-M0 为 9/19 done。不改 PRD、ROADMAP、PROJECT_BRIEF，不改 docs/reference，不改 .github，不改产品代码 |

## 缺失输入

技术方案v1.4.2、设计规范v1.2与完整高保真原型包尚未取得；历史产品稿和真实投标原件未入库。缺件和适用性按 [基线差异](decisions/baseline-gaps.md)追踪，不能以索引登记代替取得或验收。
