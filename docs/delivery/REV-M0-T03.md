为什么有这个文件：记录APP-M1-T06验收计划的交付。

它解决什么问题：说明计划覆盖范围与发现的缺口，避免把计划当作T06已验收。

# REV-M0-T03：APP-M1-T06端到端验收计划交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | REV-M0-T03 |
| 代码解释 | 无代码变更；仅新增计划文档，目的为统一T06验收步骤和证据 |
| 验收 | 计划已编制、治理检查通过；项目经理已评审通过。T06本身未执行验收 |
| 项目进度 | 340项17done；APP-M1-T06仍in-progress |
<!-- task-delivery:end -->

## 关联与状态

- 日期2026-10-12；[ISSUE-015](../../issues/ISSUE-015.md)；[任务卡](../tasks/REV-M0.md#rev-m0-t03)。
- 分支`codex/repository-foundation`，PR #3；in-review，未合入、未发布。

## 完成内容与变更文件

[验收计划](../testing/2026-10-12-app-m1-t06-acceptance-plan.md)覆盖端到端E1～E7、Word版式、8角色、权限反例、过期数据，逐项映射现有测试。同步`issues/ISSUE-015.md`、`issues/index.md`、`docs/tasks/REV-M0.md`、`docs/TASK_BOARD.md`、`docs/PROJECT_STATUS.md`、`docs/DOCUMENT_INDEX.md`。

## 发现的缺口

无单一贯通脚本；Word无标题样式/编号/目录/页眉页脚，页面设置与字体无断言，视觉渲染未留证；四个基准页截图比对缺；浏览器直接URL权限依赖T001；8角色中5个仅验拒绝；GUI过期提示无自动化。

## 同步

PRD/ROADMAP/ARCHITECTURE无影响（未改需求、阶段、接口）。
