# OPS-M0-T01：全工作区云端同步交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | OPS-M0-T01 |
| 代码解释 | [同步入口、状态与边界](../code/OPS-M0-T01.md) |
| 验收 | 单一Git根与合同排除已验证；同步工具回归和真实运行收尾验证中 |
| 项目进度 | FE59项中2done；新增OPS/REV两项，项目61项，本任务当前in-progress |
<!-- task-delivery:end -->

日期：2026-10-09。关联：[ISSUE-004](../../issues/ISSUE-004.md)、[任务](../tasks/OPS-M0.md#ops-m0-t01)、[PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3)。本地验收尚待真实服务运行验证，未合入/未发布。

## 已落实内容

- 原仓库12个顶层入口（包含.git）提升到X:\ICG CO，原相对路径、提交历史和分支保持，未建立父子两套Git；ICG34份资料原目录保留并登记初次指纹。
- 用户明确排除的两个银行合同根由.gitignore和工具路径拦截共同保留在本地；令牌、配置、状态与日志放工作区外。
- 新增tools/workspace-sync的Node执行器、PowerShell加密凭据启动器、示例配置和说明；新增真实bare remote回归。
- 治理检查新增历史来源/客户根边界及回归；活动来源清单与新文档仍登记索引。
- 根维护规则、Cursor、PRD/ROADMAP/ARCHITECTURE、任务/Issue/项目进度、运行说明与索引同步。

## 实际验证与未完成项

运行结果在 [验证记录](../testing/2026-10-09-workspace-sync.md)持续收尾。真实GitHub推送、远端更新获取与隐藏持续进程尚待最终验证；验证通过后才标done。

## 解释与后续

WIP提交用于备份进行中的项目文件，不代替每任务交付、需求/技术决定、PR合入和发布。网络失败保留本地提交；分叉或人工索引暂停。后续生产基线仍由FE-M0-T03/04及ISSUE-005处理，详见 [本轮同步表](../governance/ISSUE-004-sync.md)。
