为什么有这个文件：说明 APP-M2-T026 公司与租户管理页的具体实现、状态流转、合规门禁与权限设计。

它解决什么问题：阐述基于 PRD v1.8 §5.10.1、§5.10.2、§6.9、§7.1 的企业租户管理核心架构，实现多租户基本信息维护、资料库空间与 RAGFlow 空间隔离状态、高敏脱敏强合规不可关闭防线、涉密本地模型强制约束、密码安全策略（只能调严绝不低于平台基线）、编辑锁与自动保存心跳三元校验、集团管理员/公司管理员权限感知按钮隐匿与停用二次确认保护。

# APP-M2-T026：代码解释

- 对应任务：[APP-M2-T026](../tasks/APP-M2.md#app-m2-t026) · A-01 公司管理
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 交付文档：[APP-M2-T026 交付](../delivery/APP-M2-T026.md)
- 日期：2026-10-22
- 实际代码路径：
  - [company-manage-core.ts](../../frontend/web/src/admin/company-manage-core.ts)
  - [CompanyManagePage.tsx](../../frontend/web/src/admin/CompanyManagePage.tsx)
  - [lazy-routes.tsx](../../frontend/web/src/app/lazy-routes.tsx)
  - [route-loaders.ts](../../frontend/web/src/app/route-loaders.ts)
  - [App.tsx](../../frontend/web/src/app/App.tsx)
  - [audit-company-pages.test.mjs](../../tests/frontend/audit-company-pages.test.mjs)

---

## 核心实现说明

详见 [APP-M2-T157 代码解释文档](APP-M2-T157.md)，本任务与 APP-M2-T157 协同交付，聚焦于：
1. `validateCompanyComplianceSettings`: 落实密码长度 >= 8、字符类数 >= 3、`autosave <= heartbeat` 且 `heartbeat * 10 <= timeout * 60` 且 `timeout > 5`、`mask_strict_mode_enabled === true` 强校验；
2. `canManageCompanySettings`: 针对 `group_admin` 隐藏编辑与敏感管理按钮，向用户展示全局监管只读提示；
3. `CompanyManagePage`: 提供基本信息展示、四项合规配置页签与停用二次确认弹窗。
