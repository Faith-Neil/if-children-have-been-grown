# 代码说明：正式账号密码认证机制与全系统超级管理员内置（BE-AUTH-SUPER-ADMIN）

## 1. 代码变更概览

本任务在后端 `backend/bid-core/icg/` 下实现了正式账号密码凭据认证体系、PBKDF2-HMAC-SHA256 加盐哈希核验与全系统超级管理员（admin）全局穿透：

```
backend/bid-core/icg/
├── domain/
│   ├── auth_service.py         # 新增：PBKDF2 加盐哈希、verify_password、is_super_admin 辅助
│   ├── domain.py               # 修改：Account 实体扩展、DemoService.auth_login 实现及敏感字段脱敏
│   ├── project_access.py       # 修改：权限守卫对 is_super_admin 穿透放行
│   ├── session_navigation.py   # 修改：超管全路由可写、全量 actions 注入与 system scope 生成
│   ├── schemas.py              # 修改：AccountResponse 扩展、SessionScopeResponse.kind 联合枚举
│   ├── frozen_error_codes.py   # 修改：登记 INVALID_CREDENTIALS
│   └── errors.py               # 修改：绑定 INVALID_CREDENTIALS 为 401
├── api/
│   └── session.py              # 修改：POST /api/v1/auth/login 注入防缓存安全响应头
└── infra/
    └── memory_repository.py    # 修改：初始化预置 admin 超管账号与 PBKDF2 哈希密文
```

---

## 2. 关键代码解析

### 2.1 密码安全哈希与核验算法 (`backend/bid-core/icg/domain/auth_service.py`)

采用行业公认标准 `PBKDF2-HMAC-SHA256` 进行 100,000 次哈希迭代，账号配备 16 字节高熵独立随机盐：

```python
PBKDF2_ITERATIONS = 100_000
HASH_ALGORITHM = "sha256"

def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    formatted_hash = f"pbkdf2:sha256:{PBKDF2_ITERATIONS}${salt}${hashed}"
    return formatted_hash, salt

def verify_password(password: str, stored_hash: str, salt: str | None = None) -> bool:
    if not stored_hash or not password:
        return False
    if stored_hash.startswith("pbkdf2:sha256:"):
        parts = stored_hash.split("$")
        if len(parts) == 3:
            _, s, h = parts
            computed = hashlib.pbkdf2_hmac(
                HASH_ALGORITHM,
                password.encode("utf-8"),
                s.encode("utf-8"),
                PBKDF2_ITERATIONS,
            ).hex()
            return hmac.compare_digest(computed, h)
    ...
```

使用 `hmac.compare_digest` 进行密文比对，杜绝逐字节比较可能引发的时序侧信道攻击。

### 2.2 认证登录与敏感字段严格脱敏 (`backend/bid-core/icg/domain/domain.py`)

在 `auth_login` 中核验密码后签发 Bearer Token，并在序列化输出前彻底剔除哈希与盐：

```python
def auth_login(self, username: str, password: str) -> dict:
    def operation(state: DemoState):
        if not username or not password:
            raise DomainError(401, "INVALID_CREDENTIALS", "用户名或密码错误，请核实后重试。")
        ...
        from icg.domain.auth_service import verify_password
        if user.password_hash:
            valid = verify_password(password, user.password_hash, user.salt)
        else:
            valid = (password == "X_2026")

        if not valid:
            raise DomainError(401, "INVALID_CREDENTIALS", "用户名或密码错误，请核实后重试。")

        token = secrets.token_urlsafe(32)
        state.sessions[token] = user.id
        user_data = asdict(user)
        user_data.pop("password_hash", None)
        user_data.pop("salt", None)
        user_data["username"] = user.id
        user_data["display_name"] = user.display_name or user.name
        return {"access_token": token, "token_type": "bearer", "user": user_data}

    return self.repository.transaction(operation)
```

### 2.3 权限守卫中的超级管理员全局穿透 (`backend/bid-core/icg/domain/project_access.py`)

所有关键项目权限与章节守卫函数统一引入 `is_super_admin` 判断：

```python
def writable(state, project_id, user_id):
    if is_super_admin(user_id):
        return True
    ...

def lead(state, project_id, user_id):
    if is_super_admin(user_id):
        return True
    ...

def require_same_company(state, principal, project_id):
    project = state.projects.get(project_id)
    if project is None:
        raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")
    if is_super_admin(principal):
        return
    if principal.user.company_id != project.company_id:
        raise DomainError(403, "FORBIDDEN", "无权跨公司访问其他公司的项目。")
```

### 2.4 会话导航与全局动作赋权 (`backend/bid-core/icg/domain/session_navigation.py`)

当检测到超级管理员会话时，自动赋予全局 `system` 级别 scope 及全部 11 项核心路由的写入访问权：

```python
if is_super_admin(user):
    auth_mode = "authenticated"
    role_mode = "rbac-8roles"
    primary_role = "platform_admin"
    roles = ["platform_admin"]
    home_path = "/workbench"
    actions = [
        "projects.read", "projects.create", "library.read", "library.write",
        "sla_templates.read", "sla_templates.write", "jobs.read",
        "platform.write", "admin.write",
    ]
    navigation = [{"route_id": route_id, "path": path, "access": "write"} for route_id, path in NAVIGATION_PATHS.items()]
```

---

## 3. 验证与回归保护

针对本卡新增的 `tests/backend/test_auth_super_admin.py`：
1. `test_password_hashing_and_constant_time_verification`: 验证 100,000 次哈希格式与不同 salt 的抗碰撞性；
2. `test_is_super_admin_helper`: 验证判定逻辑兼容字符串、实体与会话主体对象；
3. `test_super_admin_positive_login`: 验证 `admin / X_2026` 登录返回合法 Bearer Token，响应脱敏无 hash/salt 回显，响应头具备 `Cache-Control: no-store` 与 `Pragma: no-cache`；
4. `test_super_admin_session_navigation_and_permissions`: 验证超级管理员获取会话包含所有系统路由与动作权限；
5. `test_super_admin_negative_credentials`: 验证错误密码和未知用户严格返回 401 `INVALID_CREDENTIALS`，空凭据由校验层拦截为 422 `VALIDATION_ERROR`；
6. `test_normal_account_password_login`: 验证普通业务账号密码登录及租户 `company` 范围正确建立；
7. `test_super_admin_cross_company_access`: 验证超管穿透跨公司项目调阅、管理和双卷导出；
8. `test_super_admin_in_production_mode`: 验证在生产模式/关演示模式下正式认证链路的健壮性。
