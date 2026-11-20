为什么有这个文件：登记 Requirement/ResponseTask 两层矩阵与分析三步改造。

它解决什么问题：与 ISSUE-047 最短路径衔接，避免再按「一条要求=一节原文标题」交付。

# ISSUE-051：两层响应矩阵与实质生成

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-051 |
| 类型 | change |
| 优先级 | P0 |
| 状态 | in-progress |
| 登记日期 | 2026-11-05 |
| 最后更新日期 | 2026-11-05 |
| revision | req-task-1 |
| 关联 Task | [TV-M0-T15](../docs/tasks/TV-M0.md#tv-m0-t15)、[TV-M0-T16](../docs/tasks/TV-M0.md#tv-m0-t16) |
| 关联 PR | 不合入 main；产品线 `feat/iss-047-technical-volume-mvp` |
| 本地验收 | 进行中 |
| 合入 | 不合入 main |
| 发布 | 未发布 |
| 交付说明 | 见各卡 delivery |
| 代码 / 流程解释 | [决定](../docs/decisions/2026-11-05-requirement-response-task.md) |

## 现象与证据

E2E：目录标题照搬条款原文；覆盖视图仍含归属分册/证据等两册字段；分析页堆事实/冲突；生成因 retrieval_failed 整篇待补。

## 实施任务

| Task ID | 目标 | 状态 |
|---|---|---|
| TV-M0-T15 | 后端两层矩阵、主题目录、计划校验、实质生成 | in-progress |
| TV-M0-T16 | 前端覆盖视图五列、去事实/冲突、壳层紧凑 | in-progress |

## 六份基线

| 基线 | impact |
|---|---|
| PRD | 有影响：矩阵两层与生成节奏 |
| ROADMAP | 有影响：TV-M0 续卡 |
| ARCHITECTURE | 有影响：Requirement/ResponseTask |
| TASK_BOARD / PROJECT_STATUS / DOCUMENT_INDEX | 本轮同步 |
