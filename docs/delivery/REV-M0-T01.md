# REV-M0-T01：目录、业务与技术审查及接手brief

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | REV-M0-T01 |
| 代码解释 | 无运行时代码改动；本任务交付方案/证据/验收文档，解释见下文 |
| 验收 | 业务12项发现、技术6类契约缺口与图片逐路径核对完成；链接与索引收尾复核中 |
| 项目进度 | 新增独立审查任务；FE59项仍2done，当前审查完成材料待收尾，不等于发现已解决 |
<!-- task-delivery:end -->

日期：2026-10-09。关联：[ISSUE-004](../../issues/ISSUE-004.md)、[任务](../tasks/REV-M0.md#rev-m0-t01)、[PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3)。未合入/未发布。

## 交付文件

- [PROJECT_BRIEF](../PROJECT_BRIEF.md)：业务目标、实际实现、分支、风险、未定细节与下一步。
- [业务报告](../reviews/2026-10-09-business-readiness.md)：场景覆盖矩阵与12个发现，每项有触发、后果、章节证据和可验证建议。
- [技术报告](../reviews/2026-10-09-technical-readiness.md)：6类前后端契约、服务端一致性与恢复/授权/输出验收，并逐组比较用户图片目录。
- [目录方案](../architecture/repository-layout.md)：保留已有快照、更新本轮工作区与渐进骨架，避免空服务拆分。
- [ISSUE-005](../../issues/ISSUE-005.md)：登记范围、完整性、权限/SLA、依赖失效、API及选型门禁；关联FE-M0-T03/04，保持未决。

## 文档逻辑与验证边界

无业务运行代码变更。审查以实际文件、原型脚本、Git快照和最新提供的参考输入为依据；分成“文档冲突”“设计未细化”“功能未实现”，不把建议当已批准选型，不把静态提示当真实功能。根维护者刷新main/xqr/PR状态，并核对报告与brief没有误报完成；活跃链接和索引通过治理检查后收尾。

本任务完成的是审查交付，16项原有BG差异及新增门禁仍需共同确认、真实实现和验收。PRD/ROADMAP/ARCHITECTURE本轮只加入治理与审查入口；业务正文不擅自改变，原因见 [同步记录](../governance/ISSUE-004-sync.md)。
