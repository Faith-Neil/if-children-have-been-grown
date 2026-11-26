# ADMIN-RBAC-PLATFORM-SPLIT 代码说明（进行中）

`domain/platform_security.py` 是平台安全策略唯一真相源；`api/platform.py` 只给平台管理员读写。登录成功记录会话签发时间，`authenticate` 按策略使过期会话失效。`api/audit.py` 从 `security_audit` 读取真实事件并按账号公司归属过滤。前端 `GlobalPagesContent` 按平台管理员/公司管理员渲染不同后台 Tab，`PlatformSecurityPage` 与精简后的 `CompanySettingsPage` 分别承担平台与公司配置。
