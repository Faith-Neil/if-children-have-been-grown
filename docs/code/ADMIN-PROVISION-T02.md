为什么有这个文件：解释 ADMIN-PROVISION-T02 前端入口。

它解决什么问题：定位顶栏与开通弹窗改动。

# ADMIN-PROVISION-T02 代码说明

- `admin/company-provision-core.ts`：可见性与表单校验、`createCompany`。
- `shell/AppHeaderActions.tsx`：按角色决定是否渲染 `.company-label`。
- `admin/CompanyManagePage.tsx`：新建公司 Modal；`data-testid=company-create-*`。
