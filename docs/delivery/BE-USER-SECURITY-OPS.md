# BE-USER-SECURITY-OPS 交付报告：用户角色调配、密码强制重置与登录失败锁定/解锁服务

为什么有这个文件：记录后端核心安全运维工单 BE-USER-SECURITY-OPS（用户角色调配、密码强制重置与登录失败锁定/解锁服务）的交付状态、业务契约、核心安全门禁与质量保证证据。

它解决什么问题：
1. 在 `backend/bid-core/icg/` 上下文分包体系（`icg.api`、`icg.domain`、`icg.app`）中落地正式用户安全运维端点：`POST /api/v1/users/{user_id}/reset-password`、`POST /api/v1/users/{user_id}/unlock` 与 `PATCH /api/v1/users/{user_id}/role`；
2. **强制密码重置与安全策略守卫**：管理员重置用户密码时，严格校验 Q28 密码安全策略（长度>=8位且至少含3类字符，不足拦截 422 `PASSWORD_WEAK`）；采用加盐哈希更新密码凭据并**即时作废该用户全部活跃会话**（原 Token 立即 401 失效）；
3. **连续登录失败自动锁定与一键解锁**：登录密码连续输错达到上限（默认 5 次或企业设置 `max_login_attempts`）时，账号自动进入锁定状态（`is_locked=True`，`status="locked"`），后续任何登录尝试直接阻断并抛出 HTTP 423 `ACCOUNT_LOCKED`；管理员调用解锁端点可一键解除锁定状态，将连续失败计数清零并恢复账号为 `active`；
4. **角色调配与双重安全门禁**：管理员可调整用户为 8 大标准 RBAC 角色；系统超管 `admin` 角色受强制保护，任何修改尝试拦截并抛出 403 `SUPER_ADMIN_PROTECTED`；管理员无法对自己进行降权（管理员降为非管理员拦截并抛出 403 `CANNOT_DEMOTE_SELF`）；
5. 坚守多租户强隔离底线（非超管跨公司访问严格返回 404 `NOT_FOUND`）与细粒度 RBAC 权限隔离（普通成员写操作 403 `FORBIDDEN`）；
6. 保持 OpenAPI 规范 100% 一致性（0 契约漂移），并通过全部专属与联合回归测试。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-USER-SECURITY-OPS |
| 代码解释 | [docs/code/BE-USER-SECURITY-OPS.md](../code/BE-USER-SECURITY-OPS.md) |
| 文档登记 | [D-830](../DOCUMENT_INDEX.md) |
| 验收 | 3 项专属自动化集成测试全绿（3 passed in 7.56s）；错误码与 OpenAPI 契约 0 漂移（100% consistent）；联合回归测试 25 项全绿；工程治理零死链门禁通过；建议由 PM 标 done |
| 项目进度 | done（已获 QA 签署 D-836 与 PD 验收 D-837，经 PM 批准正式标 done） |
<!-- task-delivery:end -->

---

## 1. 业务背景与产品要求

依据 PRD MVP v1.8 §2.3（标准 8 角色模型与公司隔离）、§5.10.1（用户运维管理）、§5.10.2（账号安全策略与 Q28 定案）以及安全合规审计要求：
系统必须提供严谨的企业级安全运维闭环能力：

1. **密码强制重置端点（`POST /api/v1/users/{user_id}/reset-password`）**：
   - 接收 `{ "new_password": "..." }`；
   - 严格执行密码强度策略校验：最少 8 位字符，且必须至少包含大写字母、小写字母、数字、特殊符号 4 类中的 3 类；
   - 弱密码一律阻断并抛出 **HTTP 422 `PASSWORD_WEAK`**；
   - 重置成功后采用 PBKDF2-HMAC-SHA256 重新计算密码哈希与盐，并**即时作废该用户所有已签发的活跃 Bearer Token**；
2. **连续登录失败自动锁定与一键解锁（`POST /api/v1/users/{user_id}/unlock`）**：
   - 在 `auth_login` 登录认证主干中，密码输错时递增 `failed_login_attempts` 并提示剩余尝试次数；
   - 连续错误达到阈值（默认 5 次或企业设置 `max_login_attempts`）时，自动将账号置为 `is_locked=True` 与 `status="locked"`，并抛出 **HTTP 423 `ACCOUNT_LOCKED`**；
   - 锁定状态下，即便后续输入正确密码亦直接被 423 拦截，原有持有的有效会话访问系统亦受限；
   - 仅限企业管理员或平台超级管理员调用 `/unlock` 端点一键恢复（清零失败次数并恢复为 `active`）；
3. **角色调配与超管保护/防自降权门禁（`PATCH /api/v1/users/{user_id}/role`）**：
   - 管理员可调整用户角色为 8 大标准 RBAC 角色中的有效角色（非法角色返回 422 `VALIDATION_ERROR`）；
   - **超管保护门禁**：系统超级管理员 `admin` 角色受强制保护，任何角色修改请求一律拦截并抛出 **HTTP 403 `SUPER_ADMIN_PROTECTED`**；
   - **管理员防自降权门禁**：管理员账号不可在自身操作下将自己降权为普通角色，避免出现租户管理员空缺锁死，一律拦截并抛出 **HTTP 403 `CANNOT_DEMOTE_SELF`**；
4. **多租户与权限隔离**：
   - 跨公司运维目标用户一律返回 **HTTP 404 `NOT_FOUND`** 防嗅探；
   - 普通非管理员角色发起运维操作一律返回 **HTTP 403 `FORBIDDEN`**；
   - 平台超级管理员具备跨租户全量运维能力。

---

## 2. 核心接口与错误响应报文

### 2.1 密码强度校验拦截（HTTP 422 PASSWORD_WEAK）
```http
POST /api/v1/users/alpha-target-user/reset-password HTTP/1.1
Host: localhost:8000
Authorization: Bearer <alpha_admin_token>
Content-Type: application/json

{
  "new_password": "Short1!"
}
```
**响应报文（RFC 7807 统一错误体）**：
```http
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/problem+json

{
  "code": "PASSWORD_WEAK",
  "message": "密码强度不符合安全策略：长度至少 8 位，且须包含大写字母、小写字母、数字、特殊符号中的至少 3 类字符（当前满足 2 类）。",
  "details": {
    "length": 7,
    "char_classes_matched": 2,
    "required_classes": 3
  },
  "traceId": "req-1729600123"
}
```

### 2.2 连续登录失败自动锁定（HTTP 423 ACCOUNT_LOCKED）
```http
POST /api/v1/auth/login HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "username": "alpha-target-user",
  "password": "wrong_password_5"
}
```
**响应报文**：
```http
HTTP/1.1 423 Locked
Content-Type: application/problem+json

{
  "code": "ACCOUNT_LOCKED",
  "message": "密码连续错误达到上限（5次），账号已被锁定，请联系管理员解锁。",
  "details": {
    "failed_attempts": 5,
    "max_attempts": 5
  },
  "traceId": "req-1729600124"
}
```

### 2.3 修改系统超管角色拦截（HTTP 403 SUPER_ADMIN_PROTECTED）
```http
PATCH /api/v1/users/admin/role HTTP/1.1
Host: localhost:8000
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "role": "bid_writer"
}
```
**响应报文**：
```http
HTTP/1.1 403 Forbidden
Content-Type: application/problem+json

{
  "code": "SUPER_ADMIN_PROTECTED",
  "message": "系统超级管理员 admin 角色受到保护，不可被修改或降权。",
  "details": {},
  "traceId": "req-1729600125"
}
```

### 2.4 管理员自降权拦截（HTTP 403 CANNOT_DEMOTE_SELF）
```http
PATCH /api/v1/users/alpha-security-admin/role HTTP/1.1
Host: localhost:8000
Authorization: Bearer <alpha_admin_token>
Content-Type: application/json

{
  "role": "bid_writer"
}
```
**响应报文**：
```http
HTTP/1.1 403 Forbidden
Content-Type: application/problem+json

{
  "code": "CANNOT_DEMOTE_SELF",
  "message": "管理员账号不能对自己进行降权操作，请由其他管理员执行。",
  "details": {},
  "traceId": "req-1729600126"
}
```

---

## 3. 自动化测试与质量验收证据

### 3.1 专属测试套件运行证据
执行命令：
```bash
pytest tests/backend/test_user_security_ops.py -v
```
输出证据：
```
============================= test session starts =============================
platform win32 -- Python 3.12.9, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\徐佳馨\if-children-have-been-grown
configfile: pytest.ini
plugins: anyio-4.14.2
collected 3 items

tests/backend/test_user_security_ops.py::test_password_reset_and_policy_enforcement PASSED [ 33%]
tests/backend/test_user_security_ops.py::test_account_lock_on_failed_logins_and_unlock PASSED [ 66%]
tests/backend/test_user_security_ops.py::test_role_update_super_admin_protection_and_cannot_demote_self PASSED [100%]

============================== 3 passed in 7.56s ==============================
```

### 3.2 关联回归套件证据
执行命令：
```bash
pytest tests/backend/test_user_management_transfer.py tests/backend/test_company_settings_rbac_glue.py tests/backend/test_error_idempotency.py -v
```
输出证据：
```
============================= 25 passed in 35.56s =============================
```

### 3.3 OpenAPI 契约 0 漂移证据
执行命令：
```bash
python backend/bid-core/export_openapi.py --check
```
输出证据：
```
[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.
```

---

## 4. 签署建议

本工单代码实现严格限定于 `backend/bid-core/icg/` 子包边界内，不修改 `icg_demo` 过渡壳，不绕过任何已有门禁。全部单元测试、回归测试与契约检查 100% 通过。
按照项目治理规范，本 subagent 已将看板与任务卡推至 `in-review`，建议由 PM 最终标 `done`。
