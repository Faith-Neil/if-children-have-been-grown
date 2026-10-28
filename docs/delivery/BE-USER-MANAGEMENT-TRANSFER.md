# BE-USER-MANAGEMENT-TRANSFER 交付报告：用户管理与账号停用前业务资产强制交接服务

为什么有这个文件：记录后端核心能力工单 BE-USER-MANAGEMENT-TRANSFER（用户管理与账号停用前业务资产强制交接服务）的交付状态、业务契约、核心业务红线门禁与质量保证证据。

它解决什么问题：
1. 在 `backend/bid-core/icg/` 分包体系中落地正式用户增删改查与密码策略服务，支持 `GET /api/v1/users`、`POST /api/v1/users`、`GET /api/v1/users/{user_id}`、`PATCH /api/v1/users/{user_id}` 与 `PATCH /api/v1/users/{user_id}/status`；
2. 严格贯彻 Q28 定案密码强度校验（最少 8 位且至少包含大写、小写、数字、符号中的三类，不足拦截 422 `PASSWORD_WEAK`），新增用户强制采用 PBKDF2-HMAC-SHA256 加盐哈希加密存储与严格脱敏输出；
3. **落地核心业务红线：停用前强制转交资产（M1-P10-F2）**：当停用（`status="disabled"`）某用户时，若该用户仍作为项目负责人（`project_lead`）或章节编写人（`bid_writer`）绑定在未归档（`is_archived=False`）的项目或正在编辑锁定的章节中，且未指定合法接交人（`successor_user_id`），严格拦截并抛出 **HTTP 409 `USER_TRANSFER_REQUIRED`**；
4. 若指定了合法接交人，则在单一数据库事务中原子性完成项目负责人、分册负责人、章节编写人字段变更，安全释放持有编辑锁，记录审计日志，并作废待停用用户的全部活跃会话；
5. 坚守多租户强隔离底线（非超管跨公司访问严格返回 404 `NOT_FOUND`）与细粒度 RBAC 权限隔离（普通成员写操作 403 `FORBIDDEN`，超管 admin 保护免受停用）；
6. 保持 OpenAPI 规范 100% 一致性（0 契约漂移），并通过全部专属与联合回归测试。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-USER-MANAGEMENT-TRANSFER |
| 代码解释 | [docs/code/BE-USER-MANAGEMENT-TRANSFER.md](../code/BE-USER-MANAGEMENT-TRANSFER.md) |
| 文档登记 | [D-822](../DOCUMENT_INDEX.md) |
| 验收 | 7 项专属自动化集成测试全绿（7 passed in 8.73s）；错误码与 OpenAPI 契约 0 漂移（100% consistent）；联合回归测试 24 项全绿；工程治理零死链门禁通过；建议由 PM 标 done |
| 项目进度 | 本工单已完成全部用户 CRUD、密码策略校验、停用前资产强制交接门禁与原子转交服务开发，状态转为 in-review，建议由 PM 标 done |
<!-- task-delivery:end -->

---

## 1. 业务背景与产品要求

依据 PRD MVP v1.8 §2.3（标准 8 角色模型与公司隔离）、§5.10.1（用户列表与交接）、§5.10.2（账号安全策略与 Q28 定案）以及原型 §6.2 M1-P10-F2：
前端正在推进 `APP-M2-T027`（A-02 用户列表与转交），后端必须在上下文子包（`icg.api` 与 `icg.domain`）中提供正式可用、多租户强隔离、且具备资产交接门禁的微服务层：

1. **用户增删改查端点**：
   - `GET /api/v1/users`：调阅用户列表，支持租户、角色、状态与关键字检索；
   - `POST /api/v1/users`：新增用户，强制执行密码策略校验与 PBKDF2 加盐哈希；
   - `GET /api/v1/users/{user_id}`：获取单个用户详情（密码哈希与盐严格脱敏）；
   - `PATCH /api/v1/users/{user_id}` 与 `PATCH /api/v1/users/{user_id}/status`：更新用户信息或更新账号状态；
   - `POST /api/v1/users/{user_id}/transfer`：独立在投项目与资产转交端点；
2. **Q28 定案密码强度策略**：
   - 密码长度下限 8 位；
   - 至少包含大写英文字母、小写英文字母、数字、特殊符号 4 类字符中的 3 类；
   - 校验不足拦截抛出 422 `PASSWORD_WEAK`；
3. **M1-P10-F2 停用前业务资产强制交接门禁**：
   - 待停用用户若在未归档（`is_archived=False`）项目中担任项目负责人（`assembly_owner_id`）、分册负责人（`owners`）、团队编写人，或在未归档项目中被指定为章节编写人（`assignee_id`）、或当前持有章节编辑锁（`lock`）；
   - 若未提供 `successor_user_id`，严格抛出 **HTTP 409 `USER_TRANSFER_REQUIRED`**，并在 details 中返回未结清资产列表；
   - 若提供 `successor_user_id`，校验接收人合法性（必须存在、同企业、非本人、未停用），原子完成职责转移与编辑锁安全释放；
4. **多租户与权限隔离**：
   - 平台超级管理员（`admin`）具备全平台跨租户运维权限；
   - 企业管理员只能管理所属企业用户（跨企业访问严格返回 404 `NOT_FOUND`）；
   - 普通成员角色（`bid_writer`, `viewer`, `auditor` 等）发起写操作严格拦截 403 `FORBIDDEN`；
   - 保护全系统超级管理员 `admin` 账号不可被停用（拦截 403 `FORBIDDEN`）。

---

## 2. 接口报文与状态码规范

### 2.1 新增用户密码强度不达标（HTTP 422 PASSWORD_WEAK）

**请求报文**：
```http
POST /api/v1/users HTTP/1.1
Host: localhost:8000
Authorization: Bearer <alpha_admin_token>
Content-Type: application/json

{
  "username": "weak-user",
  "name": "弱密码用户",
  "company_id": "alpha",
  "role": "bid_writer",
  "password": "simplepassword1"
}
```

**响应报文**：
```http
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json

{
  "code": "PASSWORD_WEAK",
  "message": "密码强度不足：须包含大写字母、小写字母、数字、符号中的至少 3 类。",
  "details": {
    "field": "password"
  },
  "traceId": "7f8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d"
}
```

### 2.2 停用持有在投资产用户未指定接交人（HTTP 409 USER_TRANSFER_REQUIRED）

**请求报文**：
```http
PATCH /api/v1/users/alpha-lead-user/status HTTP/1.1
Host: localhost:8000
Authorization: Bearer <alpha_admin_token>
Content-Type: application/json

{
  "status": "disabled"
}
```

**响应报文**：
```http
HTTP/1.1 409 Conflict
Content-Type: application/json

{
  "code": "USER_TRANSFER_REQUIRED",
  "message": "用户 alpha-lead-user 仍作为项目负责人或章节编写人绑定在 1 个未完结在投项目及 1 个进行中章节，停用前必须转交名下资产。",
  "details": {
    "user_id": "alpha-lead-user",
    "untransferred_projects": [
      {
        "project_id": "test-proj-transfer-block-1",
        "project_name": "在投重大通信枢纽项目",
        "role_in_project": "lead"
      }
    ],
    "untransferred_chapters": [
      {
        "chapter_id": "test-chap-transfer-block-1",
        "project_id": "test-proj-transfer-block-1",
        "title": "技术方案与网络拓扑",
        "volume": "technical",
        "is_assigned": true,
        "is_locked": true
      }
    ],
    "required_action": "请指定 successor_user_id 执行资产交接后再停用"
  },
  "traceId": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d"
}
```

### 2.3 附带合法接交人平滑停用（HTTP 200 OK）

**请求报文**：
```http
PATCH /api/v1/users/alpha-lead-user/status HTTP/1.1
Host: localhost:8000
Authorization: Bearer <alpha_admin_token>
Content-Type: application/json

{
  "status": "disabled",
  "successor_user_id": "alpha-successor-user",
  "reason": "员工转岗离任资产平滑交接"
}
```

**响应报文**：
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "alpha-lead-user",
  "name": "Alpha 原负责人",
  "display_name": "Alpha 原负责人",
  "company_id": "alpha",
  "role": "project_lead",
  "status": "disabled",
  "created_at": "2026-10-28T05:00:00Z",
  "updated_at": "2026-10-28T05:01:00Z"
}
```

---

## 3. 自动化测试与验证证据

### 3.1 专属单测执行结果
```bash
pytest tests/backend/test_user_management_transfer.py -v
```
**输出证据**：
```
tests/backend/test_user_management_transfer.py::test_user_crud_and_password_policy PASSED [ 14%]
tests/backend/test_user_management_transfer.py::test_multi_tenant_and_rbac_isolation PASSED [ 28%]
tests/backend/test_user_management_transfer.py::test_disable_user_without_transfer_blocked_by_user_transfer_required PASSED [ 42%]
tests/backend/test_user_management_transfer.py::test_disable_user_with_invalid_successor_rejected PASSED [ 57%]
tests/backend/test_user_management_transfer.py::test_disable_user_with_valid_successor_atomic_handoff PASSED [ 71%]
tests/backend/test_user_management_transfer.py::test_archived_project_does_not_block_deactivation PASSED [ 85%]
tests/backend/test_user_management_transfer.py::test_independent_transfer_endpoint PASSED [100%]

============================== 7 passed in 8.73s ==============================
```

### 3.2 错误码与联合回归执行结果
```bash
pytest tests/backend/test_error_idempotency.py tests/backend/test_company_settings_rbac_glue.py tests/backend/test_compliance_rules_p5.py -v
```
**输出证据**：
```
============================= 24 passed in 20.55s =============================
```

### 3.3 OpenAPI 契约一致性核验
```bash
python backend/bid-core/export_openapi.py --check
```
**输出证据**：
```
[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.
```

---

## 4. 交付文件与架构拓扑

1. **领域服务实现**：
   - [`backend/bid-core/icg/domain/user_management.py`](../../backend/bid-core/icg/domain/user_management.py)：实现 `UserManagementService`，涵盖用户脱敏实体、密码强度校验、未结清资产探测（项目负责人、编写人、编辑锁）与原子转交逻辑。
   - [`backend/bid-core/icg/domain/domain.py`](../../backend/bid-core/icg/domain/domain.py)：在 `Account` 实体增加 `status` 字段支持，并在 `auth_login` 与 `authenticate` 中加入停用账号拦截。
2. **API 路由与契约**：
   - [`backend/bid-core/icg/api/users.py`](../../backend/bid-core/icg/api/users.py)：暴露 `/api/v1/users` 相关端点与 `PATCH /api/v1/users/{user_id}/status`。
   - [`backend/bid-core/icg/app/main.py`](../../backend/bid-core/icg/app/main.py)：注册路由装配。
3. **OpenAPI 规范契约**：
   - [`spec/openapi/demo-v1.json`](../../spec/openapi/demo-v1.json)：冻结更新，包含 `listUsers`、`createUser`、`getUser`、`updateUser`、`updateUserStatus`、`transferUserAssets` 等端点与 `USER_TRANSFER_REQUIRED` 错误状态。
4. **测试套件**：
   - [`tests/backend/test_user_management_transfer.py`](../../tests/backend/test_user_management_transfer.py)：7 项专属端到端自动化测试用例。
