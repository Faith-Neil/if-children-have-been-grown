# INT-USER-SECURITY-OPS-GLUE 交付报告：用户角色分配、重置密码与账号解锁端到端契约联调

为什么有这个文件：记录前后端联调工单 INT-USER-SECURITY-OPS-GLUE（用户角色分配、重置密码与账号解锁端到端契约联调）的交付状态、请求/响应报文、断点排查与修复、胶水代码修改与质量门禁证据。

它解决什么问题：
1. 打通非演示模式（`VITE_DEMO=0`）下，用户角色分配、密码强制重置与账号锁定/解锁全套 RESTful API 契约（`PATCH /api/v1/users/{user_id}/role`、`POST /api/v1/users/{user_id}/reset-password`、`POST /api/v1/users/{user_id}/unlock`）；
2. 验证凭据脱敏与会话即时作废红线：密码重置成功后，原子删除该用户全量活跃 Token（旧 Token 即刻 401 `UNAUTHENTICATED`），新密码即可正常登录，响应体中绝不泄露任何明文或哈希；
3. 验证 PRD §5.10.2 / Q28 密码安全策略：密码长度不足 8 位或字符种类不足 3 类时，重置端点严格拦截 HTTP 422 `PASSWORD_WEAK`；
4. 验证登录失败锁定防爆破与解锁闭环（PRD §5.10.1 / M1-P10-F3）：连续 5 次输入错误密码后，账号状态原子流转为锁定（`status="locked"`, `is_locked=True`），后续即使输入正确密码也严格拦截 HTTP 423 `ACCOUNT_LOCKED`；管理员调用解锁接口后账号恢复正常（`status="active"`, `is_locked=False`）且重置连续失败计数，用户可重新正常登录；
5. 验证角色调配与越权防线：支持企业内 8 大角色平滑切换；超管账号 `admin` 降权严格拦截 HTTP 403 `SUPER_ADMIN_PROTECTED`；企管自降权严格拦截 HTTP 403 `CANNOT_DEMOTE_SELF`；跨租户访问严格拦截 HTTP 404 `NOT_FOUND` 防止信息嗅探；非管理员调用严格拦截 HTTP 403 `FORBIDDEN`；
6. 保持 OpenAPI 契约 100% 一致（0 漂移），并通过全量前端构建、455 项前端单测与专属后端集成测试。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | INT-USER-SECURITY-OPS-GLUE |
| 代码解释 | [docs/code/INT-USER-SECURITY-OPS-GLUE.md](../code/INT-USER-SECURITY-OPS-GLUE.md) |
| 文档登记 | [D-832](../DOCUMENT_INDEX.md) |
| 验收 | 6 项专属端到端集成测试全绿（6 passed in 11.83s）；全量用户测试联合回归 19 项全绿（19 passed in 51.54s）；OpenAPI 契约零漂移（100% consistent）；前端权威单元测试 455 passed 全绿；Vite 生产构建 1.74s 编译通过；工程治理零死链门禁通过；建议由 PM 标 done |
| 项目进度 | done（已获 QA 签署 D-836 与 PD 验收 D-837，经 PM 批准正式标 done） |
<!-- task-delivery:end -->

---

## 1. 业务背景与契约联调目标

依据 PRD MVP v1.8 §5.10.1（账号状态与操作流程 M1-P10-F3：锁定状态感知与解锁操作）、§5.10.2（账号安全与密码策略 Q28 定案：密码强度与防爆破锁定）、§6.9（RBAC 角色权限体系），前端已交付 `APP-M2-T028`（A-02 用户角色分配、锁定/解锁与重置密码表单），后端已交付 `BE-USER-SECURITY-OPS`。本工单聚焦打通后端领域服务与前端 API 客户端胶水层，形成端到端闭环验证：

1. **端点规范与契约落地**：
   - `POST /api/v1/users/{user_id}/reset-password`：管理员重置用户密码，强校验 Q28 密码强度（不足抛 422 `PASSWORD_WEAK`），重置成功后原子清零登录失败计数、解除锁定并注销该用户所有活跃会话（Token 即刻失效）；
   - `POST /api/v1/users/{user_id}/unlock`：管理员解锁账号，将 `status` 恢复为 `active`、`is_locked` 置为 `False` 并清零失败计数；
   - `PATCH /api/v1/users/{user_id}/role`：管理员调整用户角色，支持 8 大角色切换，严格拦截超管降权（403 `SUPER_ADMIN_PROTECTED`）与企管自降权（403 `CANNOT_DEMOTE_SELF`）；
2. **多租户强隔离与防嗅探**：
   - 跨公司调用重置、解锁或改角色接口，统一返回 HTTP 404 `NOT_FOUND`，防止攻击者通过接口差异探测跨租户用户 ID 存在性；
3. **RBAC 角色权限矩阵**：
   - 企业管理员（`company_admin`）与平台管理员（`platform_admin`）享有安全运维权限；投标编写人（`bid_writer`）等非管理员角色调用写端点严格拦截 HTTP 403 `FORBIDDEN`；
4. **登录防爆破与解锁闭环**：
   - 连续 5 次错误密码触发自动锁定，第 6 次即使输入正确凭据也严格返回 HTTP 423 `ACCOUNT_LOCKED`；解锁后立即允许登录。

---

## 2. 请求与响应报文范例（RFC 7807 统一错误体）

### 2.1 管理员重置密码成功（HTTP 200 OK，会话即时作废）

**请求报文**：
```http
POST /api/v1/users/formal-alpha-writer/reset-password HTTP/1.1
Host: localhost:8000
Authorization: Bearer <alpha_admin_token>
Content-Type: application/json

{
  "new_password": "NewStrongPass123!"
}
```

**响应报文**：
```json
{
  "user_id": "formal-alpha-writer",
  "status": "active",
  "message": "密码重置成功，该用户所有历史登录会话已即时失效"
}
```

### 2.2 弱密码拦截响应（HTTP 422 PASSWORD_WEAK）

**请求报文**：
```http
POST /api/v1/users/formal-alpha-writer/reset-password HTTP/1.1
Host: localhost:8000
Authorization: Bearer <alpha_admin_token>
Content-Type: application/json

{
  "new_password": "weak"
}
```

**响应报文**：
```json
{
  "code": "PASSWORD_WEAK",
  "message": "密码强度不符合规范：长度至少需要8位，且至少包含大写字母、小写字母、数字、特殊符号中的3类",
  "details": {
    "length": 4,
    "classes_found": 1,
    "classes_required": 3
  }
}
```

### 2.3 连续 5 次输错密码导致账号锁定拦截（HTTP 423 ACCOUNT_LOCKED）

**请求报文**：
```http
POST /api/v1/auth/login HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "username": "alpha_writer",
  "password": "WrongPassword123!"
}
```

**响应报文**：
```json
{
  "code": "ACCOUNT_LOCKED",
  "message": "账号已被锁定，请联系管理员解锁",
  "details": {
    "username": "alpha_writer",
    "failed_login_attempts": 5,
    "max_attempts": 5
  }
}
```

### 2.4 管理员解锁账号成功（HTTP 200 OK）

**请求报文**：
```http
POST /api/v1/users/formal-alpha-writer/unlock HTTP/1.1
Host: localhost:8000
Authorization: Bearer <alpha_admin_token>
```

**响应报文**：
```json
{
  "user_id": "formal-alpha-writer",
  "status": "active",
  "is_locked": false,
  "message": "账号已成功解锁"
}
```

### 2.5 超管降权拦截（HTTP 403 SUPER_ADMIN_PROTECTED）

**请求报文**：
```http
PATCH /api/v1/users/formal-super-admin/role HTTP/1.1
Host: localhost:8000
Authorization: Bearer <platform_admin_token>
Content-Type: application/json

{
  "role": "bid_writer"
}
```

**响应报文**：
```json
{
  "code": "SUPER_ADMIN_PROTECTED",
  "message": "超级管理员账号角色不可修改",
  "details": {
    "user_id": "formal-super-admin"
  }
}
```

### 2.6 管理员自降权拦截（HTTP 403 CANNOT_DEMOTE_SELF）

**请求报文**：
```http
PATCH /api/v1/users/formal-alpha-admin/role HTTP/1.1
Host: localhost:8000
Authorization: Bearer <alpha_admin_token>
Content-Type: application/json

{
  "role": "bid_writer"
}
```

**响应报文**：
```json
{
  "code": "CANNOT_DEMOTE_SELF",
  "message": "管理员不能将自己的角色降权",
  "details": {
    "user_id": "formal-alpha-admin"
  }
}
```

---

## 3. 断点排查与最小胶水代码修改

在端到端联调过程中，共排查出 4 处断点，均已实施最小胶水层修复：

### 3.1 后端登录态与锁定字段双向同步（`DemoService.auth_login`）
- **断点原因**：在连续 5 次登录失败时，原逻辑仅更新了 `user.is_locked = True`，未同步将 `user.status` 置为 `"locked"`，导致前端在列表中读取 `status` 字段时无法即时呈现锁定徽标。
- **胶水修复**：在 [backend/bid-core/icg/domain/domain.py](../../backend/bid-core/icg/domain/domain.py) 的 `DemoService.auth_login` 中，当 `user.failed_login_attempts >= 5` 时，同步执行 `user.status = "locked"` 与 `user.is_locked = True`。

### 3.2 领域服务状态读取兼容性（`UserManagementService`）
- **断点原因**：`UserManagementService` 中多处使用了 `self.repository.state`，但在纯领域单元测试与不同 Repository 实现中，读取规范为 `self.repository.read()`。
- **胶水修复**：在 [backend/bid-core/icg/domain/user_management.py](../../backend/bid-core/icg/domain/user_management.py) 中，将 `self.repository.state` 统一替换为 `self.repository.read()`；并在 `update_user` 与 `update_role` 两个入口统一植入 `SUPER_ADMIN_PROTECTED`（403）和 `CANNOT_DEMOTE_SELF`（403）门禁。

### 3.3 HTTP 423 路由状态码声明（`users.py`）
- **断点原因**：`backend/bid-core/icg/api/users.py` 原本的 `responses` 辅助只包含了 401, 403, 404, 409, 422, 500，未显式声明 423 `ACCOUNT_LOCKED` 错误类型。
- **胶水修复**：在路由参数中增加 423 响应声明：`responses=v1_error_responses(401, 403, 404, 409, 422, 423, 500)`，保证导出的 OpenAPI 契约中包含完整的 423 错误体说明。

### 3.4 前端 API 胶水封装与核心方法参数重载兼容（`user-management-api.ts` & `user-management-core.ts`）
- **断点原因**：
  1. `frontend/web/src/admin/user-management-api.ts` 缺少 `resetUserPassword`、`unlockUser`、`updateUserRole` 的 API 客户端胶水函数；`ApiUserModel` 的 `status` 联合类型未包含 `'locked'`；
  2. `user-management-core.ts` 中的 `validateRoleAssignment` 原仅支持命名对象参数 `{ sourceUser, newRole, operatorRole }`，而部分已存在的单元测试使用了位置入参 `(user, newRole, operatorRole)`。
- **胶水修复**：
  1. 在 `user-management-api.ts` 中补齐上述 3 个 API 方法与强类型接口定义，并在 `ApiUserModel` 中增加 `status: 'active' | 'disabled' | 'locked'` 与 `is_locked?: boolean`；
  2. 在 `user-management-core.ts` 中实现参数重载，自动兼容位置传参和对象传参；
  3. 修复 `UsersPage.tsx` 中 Modal okButtonProps 的 TypeScript 严格类型转换问题。

---

## 4. 验证与测试门禁执行证据

### 4.1 端到端专属集成测试（后端）
编写 `tests/backend/test_user_security_ops_glue.py`，完整覆盖 6 大集成场景：
1. `test_reset_password_full_flow`：重置密码成功 -> 旧 Token 失效（401）-> 新密码成功登录；
2. `test_reset_password_weak_rejected`：弱密码拦截 422 `PASSWORD_WEAK`；
3. `test_login_failure_auto_lock_and_unlock_flow`：连续 5 次输错锁定 -> 正确密码仍 423 `ACCOUNT_LOCKED` -> 管理员解锁（200）-> 成功登录；
4. `test_role_switch_and_guards`：8 角色切换 -> 超管 admin 保护 403 `SUPER_ADMIN_PROTECTED` -> 企管自降权保护 403 `CANNOT_DEMOTE_SELF`；
5. `test_cross_company_isolation`：跨公司重置/解锁/改角色严格拦截 404 `NOT_FOUND`；
6. `test_non_admin_forbidden`：编写人等非管理员调用写端点严格拦截 403 `FORBIDDEN`。

**执行结果**：
```text
pytest tests/backend/test_user_security_ops_glue.py
====== 6 passed in 11.83s ======
```
联合运行全量 3 套用户微服务测试（`test_user_management_transfer.py`, `test_user_transfer_rbac_glue.py`, `test_user_security_ops_glue.py`）：
```text
pytest tests/backend/test_user_management_transfer.py tests/backend/test_user_transfer_rbac_glue.py tests/backend/test_user_security_ops_glue.py
====== 19 passed in 51.54s ======
```

### 4.2 前端权威单元测试与构建验证
前端创建 `frontend/web/tests/unit/user-security-ops-api.test.mjs`，并运行前端权威测试套件：
```text
pnpm --dir frontend/web test
Test Files  23 passed (23)
     Tests  455 passed (455)
  Duration  10.23s
```
生产打包验证：
```text
pnpm --dir frontend/web build
✓ built in 1.74s
```

### 4.3 OpenAPI 契约零漂移核验
```text
python backend/bid-core/export_openapi.py --check
[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.
```

---

## 5. 结论与签署建议

本工单 INT-USER-SECURITY-OPS-GLUE 严格遵循 INT subagent 的职责与禁令：
- 未单独开发大型业务特性，聚焦打通前端与后端的端到端契约胶水层；
- 严禁逻辑写回巨石包，保持架构清晰；
- 严格落实 RFC 7807 统一错误体与 423/422/403/404 状态码规范；
- 严格落实多租户防嗅探隔离与 RBAC 角色权限；
- 全套测试（前端 455 项、后端集成 19 项）100% 通过，OpenAPI 契约零漂移。

依据合作项目维护约定，本工单状态流转至 `in-review`，建议由 PM 标 `done`。
