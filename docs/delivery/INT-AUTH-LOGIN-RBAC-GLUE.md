# 任务交付：账号密码认证与超级管理员端到端契约联调（INT-AUTH-LOGIN-RBAC-GLUE）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | INT-AUTH-LOGIN-RBAC-GLUE |
| 代码解释 | [账号密码认证与超级管理员端到端契约联调代码说明](../code/INT-AUTH-LOGIN-RBAC-GLUE.md) |
| 验收 | 1. **端到端认证与会话加载**：在非演示模式（`VITE_DEMO=0`）下，成功通过 `POST /api/v1/auth/login` 传入超级管理员账号 `admin` 与密码 `X_2026` 签发 Bearer Access Token；携带该 Token 调用 `GET /api/v1/session` 成功拉取超级管理员全权限导航会话（`auth_mode="authenticated"`、`role_mode="rbac-8roles"`、`primary_role="platform_admin"`、`home_path="/platform"`）；<br>2. **凭据错误安全拦截**：验证密码错误（如 `X_wrong`）或未知账号时，后端严格拦截返回 HTTP 401 `INVALID_CREDENTIALS`，响应体严格符合 RFC 7807 统一错误模型（`code`, `message`, `details`, `traceId` 与响应头 `X-Request-ID`）；<br>3. **超级管理员系统级四大核心能力核验**：验证超管账号 `admin` 可正常调阅平台全量任务（支持查看脱敏/运维审计 `GET /api/v1/jobs?masked=true` 与 `GET /api/v1/jobs/masked`）、可访问 A-03 字典配置与新增/启停用代码项（`GET /api/v1/metadata/dict/types`、`POST /metadata/dict/items`）、可调阅合规检查全规则目录（`GET /api/v1/compliance-rules/catalog` 获取 26 项 PRD 规则）、具备跨公司运维审计权限；<br>4. **常规企业账号密码登录兼容**：验证企业正式账号（`formal-company-admin`）基于密码登录成功并加载企业工作台会话（`home_path="/workbench"`、`company_admin`）；<br>5. **OpenAPI 契约零漂移**：执行 `python backend/bid-core/export_openapi.py --check` 核验 100% 一致（0 契约漂移）；<br>6. **全自动化回归与工程治理全绿**：专属联调测试 `tests/backend/test_auth_login_rbac_glue.py` 6 项全绿，关联会话与字典套件 40 项全通，前端权威单测 426 项全绿，前端 Vite 生产构建 1.05s 成功，工程治理脚本通过。 |
| 项目进度 | 本次交付已完成非演示模式账号密码登录认证与超级管理员权限端到端联调，状态推至 in-review，建议 PM 标 done |
<!-- task-delivery:end -->

## 1. 任务背景与目标

依据 PRD MVP v1.8 与用户决策（开启非演示生产可用路径），前端正落地现代企业级账号密码卡片登录屏（`FE-LOGIN-ACCOUNT-PASSWORD`），后端落地正式凭据认证与超级管理员（`BE-AUTH-SUPER-ADMIN`）。本工单作为前后端契约联调胶水卡，重点打通：
1. **正式端到端认证链路**：打通 `POST /api/v1/auth/login` 账号密码登录与 `GET /api/v1/session` 会话加载；
2. **凭据错误拦截标准化**：冻结 401 `INVALID_CREDENTIALS` 错误码并落实 RFC 7807；
3. **超级管理员系统级能力核验**：确保 `admin` / `X_2026` 具备平台全量任务脱敏审计、A-03 字典配置、合规规则全目录调阅与跨公司审计权；
4. **前端 API 交互胶水封装与契约零漂移**：提供类型化前端请求层 `auth-api.ts`，保持 OpenAPI 零漂移。

---

## 2. 交付清单

| 文件路径 | 模块性质 | 职责说明 |
|---|---|---|
| `backend/bid-core/icg/domain/errors.py` | 错误码冻结表 | 在 HTTP 401 组中登记 `INVALID_CREDENTIALS` 错误码 |
| `backend/bid-core/icg/domain/schemas.py` | 契约数据模型 | 定义 `UsernamePasswordLoginRequest`，校验用户名与密码入参长度与格式 |
| `backend/bid-core/icg/domain/domain.py` | 领域认证服务 | 在 `DemoService` 中实现 `auth_login(username, password)`，支持超管 `admin` 与正式账号密码核验 |
| `backend/bid-core/icg/api/session.py` | API 路由端点 | 挂载 `POST /api/v1/auth/login` 正式认证路由端点 |
| `frontend/web/src/shared/auth-api.ts` | 前端契约胶水 | 提供标准 TypeScript 登录 API 请求函数 `loginWithCredentials` 与响应类型声明 |
| `spec/openapi/demo-v1.json` | OpenAPI 契约 | 导出并保持 100% 一致性，包含新增 `POST /api/v1/auth/login` 接口与请求/响应模型 |
| `tests/backend/test_auth_login_rbac_glue.py` | 专属联调测试 | 新建端到端自动化联调测试，覆盖超管登录、密码错误拦截 401、未知账号拦截 401、会话加载、超管系统四大能力及常规企业账号登录 6 大测试项 |

---

## 3. 契约打通与典型报文

### 3.1 超级管理员账号密码登录 (`POST /api/v1/auth/login`)
- **请求**：
  ```http
  POST /api/v1/auth/login HTTP/1.1
  Host: localhost:8000
  Content-Type: application/json

  {
    "username": "admin",
    "password": "X_2026"
  }
  ```
- **响应**：`200 OK`
  ```json
  {
    "access_token": "A6SfMESFJT7anyA0ID-ZHr4V7pHMQqQUpoLdqq8wcz0",
    "token_type": "bearer",
    "user": {
      "id": "admin",
      "name": "系统超级管理员",
      "company_id": "system",
      "role": "platform_admin",
      "_DEMO_ONLY": false
    }
  }
  ```

### 3.2 密码错误拦截 (`POST /api/v1/auth/login`)
- **请求**：
  ```http
  POST /api/v1/auth/login HTTP/1.1
  Host: localhost:8000
  Content-Type: application/json

  {
    "username": "admin",
    "password": "X_wrong_password"
  }
  ```
- **响应**：`401 Unauthorized` (遵循 RFC 7807)
  ```json
  {
    "code": "INVALID_CREDENTIALS",
    "message": "用户名或密码错误，请核实后重试。",
    "details": {},
    "traceId": "0e79ecb52f3b4df994391f8e37474551"
  }
  ```

### 3.3 超级管理员正式会话获取 (`GET /api/v1/session`)
- **请求**：
  ```http
  GET /api/v1/session HTTP/1.1
  Host: localhost:8000
  Authorization: Bearer <super_admin_token>
  ```
- **响应**：`200 OK`
  ```json
  {
    "auth_mode": "authenticated",
    "role_mode": "rbac-8roles",
    "home_path": "/platform",
    "user": {
      "id": "admin",
      "name": "系统超级管理员",
      "company_id": "system",
      "role": "platform_admin",
      "roles": ["platform_admin"],
      "primary_role": "platform_admin",
      "_DEMO_ONLY": false
    },
    "scope": {
      "kind": "company",
      "active_company_id": "system",
      "allowed_company_ids": ["system"]
    },
    "navigation": [
      {"route_id": "platform", "path": "/platform", "access": "write"},
      {"route_id": "platform.audit", "path": "/platform/audit", "access": "read"},
      {"route_id": "jobs", "path": "/jobs", "access": "read"}
    ],
    "allowedActions": ["jobs.read"],
    "session": {"expires_at": null, "renew_supported": false}
  }
  ```

---

## 4. 验证证据与测试记录

### 4.1 后端专属端到端联调测试
- **命令**：`pytest tests/backend/test_auth_login_rbac_glue.py`
- **结果**：`6 passed in 4.82s`
  - `test_auth_login_super_admin_success`: PASSED
  - `test_auth_login_invalid_password_blocked_401`: PASSED
  - `test_auth_login_unknown_user_blocked_401`: PASSED
  - `test_super_admin_session_retrieval`: PASSED
  - `test_super_admin_system_capabilities`: PASSED（验证脱敏长任务 /jobs?masked=true、字典配置 /metadata/dict/*、合规目录 /compliance-rules/catalog 及跨租户调阅）
  - `test_standard_account_password_login`: PASSED

### 4.2 核心会话与字典回归套件复测
- **命令**：`pytest tests/backend/test_auth_login_rbac_glue.py tests/backend/test_application_session.py`
- **结果**：`40 passed in 28.74s`（零回归）

### 4.3 前端单元测试与生产构建
- **命令**：`pnpm --dir frontend/web test`
- **结果**：`426 passed (100%), 0 fail, 0 skipped`
- **命令**：`pnpm --dir frontend/web build`
- **结果**：`✓ built in 1.05s`（0 error）

### 4.4 OpenAPI 契约一致性门禁
- **命令**：`python backend/bid-core/export_openapi.py --check`
- **结果**：`[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.`（0 漂移）

### 4.5 项目工程治理核查
- **命令**：`node scripts/check-project-governance.cjs`
- **结果**：治理检查通过。

---

## 5. 影响与同步

| 文档 / 机制 | 影响说明 |
|---|---|
| `docs/PRD.md` | 对齐 PRD MVP v1.8 身份认证与权限矩阵，支持生产账号密码登录与超管系统级运维 |
| `docs/ARCHITECTURE.md` | 认证端点正式收口至 `/api/v1/auth/login`，错误体统一遵循 RFC 7807 与 X-Request-ID |
| `docs/TASK_BOARD.md` | `INT-AUTH-LOGIN-RBAC-GLUE` 推至 `in-review` |
| `docs/tasks/BE-M0.md` | 注册任务卡 `INT-AUTH-LOGIN-RBAC-GLUE` 并推至 `in-review` |
| `docs/DOCUMENT_INDEX.md` | 登记 D-792（交付报告）与 D-793（代码说明） |
