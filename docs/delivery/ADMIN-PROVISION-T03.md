为什么有这个文件：记录 ADMIN-PROVISION-T03 实际交付。

它解决什么问题：避免把公司详情深链写成已端到端浏览器验收。

# ADMIN-PROVISION-T03：公司详情路由与加人

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | ADMIN-PROVISION-T03 |
| 代码解释 | [代码说明](../code/ADMIN-PROVISION-T03.md) |
| 验收 | 路由单测与 `pnpm --dir frontend/web lint` 通过。未做浏览器深链冒烟 |
| 项目进度 | in-review。建议 PM 待 QA/PD 后标 done |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-11-09。Issue：[ISSUE-052](../../issues/ISSUE-052.md)。
- 合入 / 发布：未合入，未发布。

## 完成内容

`/admin/companies/:companyId` 解析与守卫；`CompanyDetailPage` 列表/加人；`App` / `GlobalPagesContent` 接线。
