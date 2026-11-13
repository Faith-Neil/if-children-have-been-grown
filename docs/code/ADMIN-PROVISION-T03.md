为什么有这个文件：解释公司详情路由与页面。

它解决什么问题：接手者能从 path 跟到组件。

# ADMIN-PROVISION-T03 代码说明

- `app/app-route.ts`：`company_detail` 与 `companyDetailPath`。
- `shell/route-guard.ts`：须能进 `admin.rules`；公司管理员仅本公司。
- `app/App.tsx`：`loadCompanyDetail`；`companyDetailId` 状态。
- `admin/CompanyDetailPage.tsx`：`GET /users?company_id=`、`POST /users`。
