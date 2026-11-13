为什么有这个文件：记录 ADMIN-PROVISION-T02 实际交付。

它解决什么问题：避免把顶栏与新建弹窗写成已浏览器验收通过。

# ADMIN-PROVISION-T02：顶栏去公司名与新建公司弹窗

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | ADMIN-PROVISION-T02 |
| 代码解释 | [代码说明](../code/ADMIN-PROVISION-T02.md) |
| 验收 | `node --test tests/unit/company-provisioning.test.mjs` 通过；`pnpm --dir frontend/web lint` 通过。未做浏览器点选 |
| 项目进度 | in-review。建议 PM 待 QA/PD 后标 done |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-11-09。Issue：[ISSUE-052](../../issues/ISSUE-052.md)。
- 合入 / 发布：未合入，未发布。

## 完成内容

`shouldShowCompanyLabel`；`AppHeaderActions` 对 `platform_admin` 隐藏公司名；`CompanyManagePage` 新建公司弹窗调用 `POST /api/v1/companies`。
