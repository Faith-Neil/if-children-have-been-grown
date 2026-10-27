# 任务交付：正式账号密码认证机制与全系统超级管理员内置（BE-AUTH-SUPER-ADMIN）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-AUTH-SUPER-ADMIN |
| 代码解释 | [正式账号密码认证与全系统超级管理员代码说明](../code/BE-AUTH-SUPER-ADMIN.md) |
| 验收 | 1. 密码加盐哈希与常量时间核验：在 `backend/bid-core/icg/domain/auth_service.py` 完整实现 PBKDF2-HMAC-SHA256（100,000次迭代 + 账号随机16字节盐），使用 `hmac.compare_digest` 彻底防御时序侧信道攻击，杜绝任何明文密码存储与泄露；<br>2. 认证端点注册与防缓存规范：在 `backend/bid-core/icg/api/session.py` 注册 `POST /api/v1/auth/login`，接受 `{username, password}` 换取 Bearer Access Token 及用户信息，响应强制注入 `Cache-Control: no-store, no-cache, must-revalidate` 与 `Pragma: no-cache` 凭据防缓存响应头；<br>3. 凭据错误安全拦截：用户名不存在或密码错误统一返回 HTTP 401 `INVALID_CREDENTIALS`，严格遵循 RFC 7807 统一错误体格式，空凭据由 Pydantic 层拦截为 422 `VALIDATION_ERROR`；<br>4. 超级管理员系统级全权限内置：内置系统超级管理员 `admin`（初始密码 `X_2026`，角色 `platform_admin`，公司 `system`），在 `backend/bid-core/icg/domain/project_access.py` 与 `session_navigation.py` 穿透公司多租户隔离边界，赋予全路由（11条业务与运维路由）写入权限、全套项目管理权限（manage_team/project/structure/sla/facts/export_internal/check_all）以及双卷（technical/business）导出资格；<br>5. 生产关演示可用：在关闭演示账号登录（`ICG_ALLOW_DEMO_LOGIN=0` / `ICG_ENV=production`）下，旧 `/api/demo/login` 被严格阻断（403 FORBIDDEN），而正式账号密码登录通畅可用；<br>6. 自动化测试套件：专属测试套件 `tests/backend/test_auth_super_admin.py` 8 项测试全部通过，核心与关联套件 36 项全部通过；OpenAPI 契约零漂移；工程治理检查 100% 通过。 |
| 项目进度 | 本卡实现完成并通过全部专项测试、安全与权限回归测试及治理门禁，状态推至 in-review，建议 PM 标 done |
<!-- task-delivery:end -->

## 1. 任务背景与目标

为支撑从合成演示模式（Synthetic Demo）向生产级安全运行架构的演进，落实 PRD v1.8 身份认证与权限规范，本任务彻底构建系统后端正式认证体系与超级管理员基座能力：
1. **正式账号密码认证**：告别单靠 demo 账号下拉直登，建立符合行业安全标准的「账号 + 密码」凭据认证链路；
2. **PBKDF2 加盐安全哈希**：采用 Python 标准库 `hashlib.pbkdf2_hmac`（100,000 轮 SHA-256）配合账号独立高熵随机盐，比对使用 `hmac.compare_digest` 常量时间判定，杜绝彩虹表攻击与侧信道泄露；在所有响应与会话对象中严格擦除 `password_hash` 与 `salt`；
3. **内置系统超级管理员（admin / X_2026）**：系统级超级管理员账号具备全局无阻断的管理与运维权限，突破项目与公司所属边界，拥有全路由可写视角与双卷导出资格；
4. **防缓存与 RFC 7807 统一错误体**：认证端点必须严格注入防缓存响应头，认证失败严格返回 401 `INVALID_CREDENTIALS`。

---

## 2. 核心架构与分包清单

所有改动严格遵守 `AGENTS.md` 规范，新逻辑全部划分至 `backend/bid-core/icg/domain/`、`backend/bid-core/icg/api/` 与 `backend/bid-core/icg/infra/`，未向旧 `icg_demo` 增加任何新业务实现：

| 文件路径 | 模块性质 | 职责说明 |
|---|---|---|
| `backend/bid-core/icg/domain/auth_service.py` | 认证核心服务 | 新增模块。实现 `hash_password`、`verify_password`、`is_super_admin` 及系统级默认超级管理员常量定义 |
| `backend/bid-core/icg/domain/domain.py` | 领域模型与服务 | `Account` 实体增加 `password_hash`、`salt`、`display_name`；`DemoService.auth_login` 接入正式核验、会话签发与脱敏清洗；`_project` 与 `_writer` 注入超管穿透能力 |
| `backend/bid-core/icg/domain/schemas.py` | API 数据模式 | `AccountResponse` 增加 `username`、`display_name`；`SessionScopeResponse.kind` 支持 `company` 与 `system` 联合枚举 |
| `backend/bid-core/icg/domain/frozen_error_codes.py` | 错误码冻结表 | 登记并冻结 `"INVALID_CREDENTIALS"`，确保 100% 契约零漂移 |
| `backend/bid-core/icg/domain/errors.py` | 错误映射表 | 将 `INVALID_CREDENTIALS` 绑定为固定 HTTP 401 状态 |
| `backend/bid-core/icg/api/session.py` | API 路由控制 | `POST /api/v1/auth/login` 端点注入 `Cache-Control: no-store, no-cache, must-revalidate` 与 `Pragma: no-cache` 凭据安全头 |
| `backend/bid-core/icg/domain/project_access.py` | 权限控制守卫 | `writable`、`lead`、`volume_owner`、`chapter_edit`、`chapter_structure`、`require_same_company` 等权限守卫全面支持 `is_super_admin` 系统级穿透 |
| `backend/bid-core/icg/domain/session_navigation.py` | 会话导航构建 | 超管会话赋予全 11 项路由写入权限、全量 `allowedActions`、`/workbench` 首页路径与 `system` 级 scope 范围 |
| `backend/bid-core/icg/infra/memory_repository.py` | 内存仓储种子 | 内置 `admin` 超级管理员账号，并为内置默认账号预置 PBKDF2 加盐密文 |
| `tests/backend/test_auth_super_admin.py` | 专属单测 | 覆盖 PBKDF2 哈希与常量比对、超管正向登录、防缓存响应头、401/422 反向案例、跨公司项目穿透、生产关演示可用性等 8 大核心场景 |

---

## 3. 验收命令与执行证据

### 3.1 专属单元测试
运行专属自动化测试：
```powershell
pytest tests/backend/test_auth_super_admin.py -v
```

执行证据：
```text
============================= test session starts =============================
platform win32 -- Python 3.12.9, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\徐佳馨\if-children-have-been-grown
configfile: pytest.ini
plugins: anyio-4.14.2
collected 8 items

tests/backend/test_auth_super_admin.py::test_password_hashing_and_constant_time_verification PASSED [ 12%]
tests/backend/test_auth_super_admin.py::test_is_super_admin_helper PASSED [ 25%]
tests/backend/test_auth_super_admin.py::test_super_admin_positive_login PASSED [ 37%]
tests/backend/test_auth_super_admin.py::test_super_admin_session_navigation_and_permissions PASSED [ 50%]
tests/backend/test_auth_super_admin.py::test_super_admin_negative_credentials PASSED [ 62%]
tests/backend/test_auth_super_admin.py::test_normal_account_password_login PASSED [ 75%]
tests/backend/test_auth_super_admin.py::test_super_admin_cross_company_access PASSED [ 87%]
tests/backend/test_auth_super_admin.py::test_super_admin_in_production_mode PASSED [100%]

============================== 8 passed in 4.37s ==============================
```

### 3.2 联合回归测试
运行关联核心套件（错误体幂等、八角色访问矩阵、联调胶水与超管专属）：
```powershell
pytest tests/backend/test_error_idempotency.py tests/backend/test_eight_roles_access.py tests/backend/test_auth_login_rbac_glue.py tests/backend/test_auth_super_admin.py -v
```

执行证据：
```text
============================= 36 passed in 25.98s =============================
```

### 3.3 OpenAPI 契约零漂移核验
```powershell
python backend/bid-core/export_openapi.py --check
```
执行证据：
```text
[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.
```

### 3.4 工程治理门禁检查
```powershell
node scripts/check-project-governance.cjs
node --test tests/governance/*.test.cjs
```
执行证据：
```text
治理检查通过：594 份 Markdown、430 项任务、38 项 Issue。
✔ 当前治理资料可通过，历史业务版本和模板无需套用当前交付字段 (51.9768ms)
...
ℹ pass 12
ℹ fail 0
```

---

## 4. 业务底线与安全审查说明

1. **零明文存储与防侧信道**：所有账户在仓储中仅保存 `pbkdf2:sha256:100000$<salt>$<hash>`，无论登录、会话获取或列表查询，响应对象均执行 `pop("password_hash", None)` 和 `pop("salt", None)`，严禁敏感信息回显；
2. **多租户隔离与超管边界清晰**：普通公司业务账号（如 `alpha-manager`）的会话 scope 依旧严格限制在 `kind: "company"` 且仅包含本公司，跨公司操作坚决拦截 403 `FORBIDDEN`；仅账号 ID 为 `admin` 的系统级超级管理员才被赋予全局穿透与运维权限；
3. **状态建议**：本卡实现完整，测试与治理全部通过，状态推至 `in-review`，建议 PM 标 `done`。
