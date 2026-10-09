# FE-M0-T02：治理检查程序代码解释

关联：[任务卡](../tasks/FE-M0.md#fe-m0-t02)、[ISSUE-003](../../issues/ISSUE-003.md)、[任务交付](../delivery/FE-M0-T02.md)。日期：2026-10-09。当前变更随PR #3提交。

## 改了什么

新增 `scripts/check-project-governance.cjs`，把协作记录的可机械核对部分纳入无依赖检查。运行它读取仓库文件，输出结构错误；不修改文档、任务或Issue，也不调用业务接口。

## 入口和读取顺序

命令入口执行 `node scripts/check-project-governance.cjs`。程序提供 `checkProjectGovernance(root)`，回归测试调用同一实际实现，在临时仓库修改证据后验证错误能被检出。

当前治理基线取 `docs/governance/WORKFLOW.md` 的 `governance-baseline` 区块，核对PRD、ROADMAP、ARCHITECTURE及Issue看板的治理版本、更新日期、关联Issue。只比较工程治理块，不修改历史业务版本。

任务表从 `task-board` 区块读取；`done` 任务必须有真实交付文件、正确任务ID、代码解释、验收、项目进度字段，并在DOCUMENT_INDEX登记。Issue表从 `issue-board` 区块读取；`closed` 项必须有验收证据，合入状态单独记录。

程序还检查本地Markdown链接、关键文档与维护文件的索引登记。模板占位内容不当作真实任务交付，供评审产品原文不要求工程治理头。

## 错误与状态边界

缺交付、治理版本不一致、坏链接等返回明确错误，命令以非零状态退出，供协作者在提交前纠正。检查成功仅说明结构记录满足约束；它不能确认业务范围、需求与代码语义一致，也不能判断PR是否已合入或部署是否成功。

## 验证与限制

实际记录检查及失败场景回归见 [本轮验证](../testing/2026-10-09-project-governance.md)。原型和正式业务代码本轮未改；无运行时模型、数据库或接口行为变化。
