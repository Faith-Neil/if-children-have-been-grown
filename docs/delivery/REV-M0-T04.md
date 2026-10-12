为什么有这个文件：记录T06计划缺口1、3执行的交付。

它解决什么问题：说明贯通冒烟如何运行、Word渲染发现了什么，以及仍未完成的部分。

# REV-M0-T04：T06贯通冒烟与Word渲染交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | REV-M0-T04 |
| 代码解释 | [代码解释](../code/REV-M0-T04.md)；新增验收脚本`backend/bid-core/smoke_t06.py`，未改应用代码 |
| 验收 | smoke_t06 12/12通过、退出0；两册与SLA函LibreOffice渲染成功并留2张截图；发现W1～W4；见[记录](../testing/2026-10-12-t06-smoke-word-render.md) |
| 项目进度 | 340项16done、1in-review；APP-M1-T06仍in-progress |
<!-- task-delivery:end -->

## 关联与状态

- 2026-10-12；[ISSUE-015](../../issues/ISSUE-015.md)；[任务卡](../tasks/REV-M0.md#rev-m0-t04)；PR #3待合入，未发布。

## 完成内容与变更文件

`backend/bid-core/smoke_t06.py`；`docs/testing/2026-10-12-t06-smoke-word-render.md`；`docs/testing/assets/t06-word-technical-render.png`、`t06-word-sla-table-render.png`；同步ISSUE-015、issues/index、REV-M0任务卡、TASK_BOARD、PROJECT_STATUS、DOCUMENT_INDEX。未新增依赖，未使用ISSUE-016。

## 同步与剩余

PRD/ROADMAP/ARCHITECTURE无影响（未改需求、阶段、接口）。W1～W4待后端；Word/WPS实际打开、GUI驱动和其余计划缺口2、4～7未做。
