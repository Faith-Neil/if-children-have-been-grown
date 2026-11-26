# ADMIN-RBAC-PLATFORM-SPLIT 交付说明（进行中）

## 实际修改
- 新增 `/api/v1/platform/security-settings`，平台管理员读写全局密码、锁定、会话策略；公司管理员 403。
- 新增 `/api/v1/audit-logs` 真实审计查询；平台管理员全局，公司管理员强制本公司。
- 后台管理页按角色分家，移除 A 编号与字典配置入口；审计页改读真实 API。
- 安全策略接入登录、改密、用户创建/重置与会话鉴权；密码规则 scope 统一为 platform。

## 验证
- `pytest tests/backend/test_admin_rbac_security_cleanup.py -q`：2 passed。
- `pnpm --dir frontend/web exec tsc -b --noEmit`：通过。
- `ICG_ALLOW_MEMORY=1 python backend/bid-core/export_openapi.py --check`：通过。

## 未完成/限制
- 本交付为进行中证据，不建议 PM 标 done；模型配置假开关清理与任务中心完整回归仍需继续。
