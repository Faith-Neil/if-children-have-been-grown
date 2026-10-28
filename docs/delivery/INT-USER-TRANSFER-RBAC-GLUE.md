# INT-USER-TRANSFER-RBAC-GLUE 交付报告：用户管理与账号停用资产交接端到端契约联调

为什么有这个文件：记录前后端联调工单 INT-USER-TRANSFER-RBAC-GLUE（用户管理与账号停用资产交接端到端契约联调）的交付状态、请求/响应报文、断点排查、胶水代码修改与质量门禁证据。

它解决什么问题：
1. 打通非演示模式（`VITE_DEMO=0`）下，用户管理全套 RESTful API 契约（`GET /api/v1/users`、`GET /api/v1/users/{user_id}`、`POST /api/v1/users`、`PATCH /api/v1/users/{user_id}`、`POST /api/v1/users/{user_id}/transfer`）；
2. 验证凭据脱敏红线：响应体中用户密码哈希（`password_hash`）与加盐（`salt`）完全剔除，超管与企管调阅均绝不泄露任何机密哈希；
3. 验证 PRD §5.10.2 / Q28 密码安全策略：密码长度不足 8 位或字符种类不足 3 类（大写、小写、数字、符号）时，统一拦截 HTTP 422 `PASSWORD_WEAK`；
4. 验证核心业务红线（PRD §5.10.1 / M1-P10-F2）：对在投未完结项目的负责人直接发起停用，严格阻断并返回 HTTP 409 `USER_TRANSFER_REQUIRED` 及未结清资产清单；
5. 验证平滑交接：传入有效同企业接收人（`successor_user_id`）后，在单一事务中原子转移项目负责人职责（`assembly_owner_id`、`owners`、`members`）并留痕（`handoffs`），随后将账号停用并销毁活跃会话；
6. 验证多租户强隔离（跨公司访问 404 `NOT_FOUND`，杜绝企业用户信息嗅探）与 RBAC 权限隔离（非管理员修改拦截 403 `FORBIDDEN`）；
7. 保持 OpenAPI 契约 100% 一致（0 漂移），并通过全量前端构建与单元测试。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | INT-USER-TRANSFER-RBAC-GLUE |
| 代码解释 | [docs/code/INT-USER-TRANSFER-RBAC-GLUE.md](../code/INT-USER-TRANSFER-RBAC-GLUE.md) |
| 文档登记 | [D-820](../DOCUMENT_INDEX.md) |
| 验收 | 6 项专属自动化集成测试全绿（6 passed in 7.40s）；OpenAPI 契约零漂移（100% consistent）；前端权威单元测试 445 passed 全绿；Vite 生产构建 1.08s 编译通过；工程治理零死链门禁通过；建议由 PM 标 done |
| 项目进度 | 本工单已完成全部端到端契约联调与权威测试验证，状态转为 in-review，建议由 PM 标 done |
<!-- task-delivery:end -->

---

## 1. 业务背景与契约联调目标

依据 PRD MVP v1.8 §5.10.1（账号状态与停用交接约束 M1-P10-F2）、§5.10.2（账号安全与密码策略 Q28 定案）、§6.9（RBAC 权限矩阵），前端已交付 `APP-M2-T027`（A-02 用户列表、新增与停用前转交安全表单）。本工单聚焦打通后端领域服务与前端 API 客户端的端到端契约胶水层：

1. **端点规范**：
   - `GET /api/v1/users`：分页与过滤查询用户列表；
   - `POST /api/v1/users`：新增企业用户并实施强密码校验；
   - `GET /api/v1/users/{user_id}`：查询单个用户详情（脱敏）；
   - `PATCH /api/v1/users/{user_id}`：更新用户状态/资料；停用时联动资产交接门禁；
   - `POST /api/v1/users/{user_id}/transfer`：独立批量划转在投项目与资产；
2. **多租户强隔离**：
   - 平台管理员（`platform_admin`）穿透跨租户管理；
   - 企业用户跨租户访问严格拦截 404 `NOT_FOUND`，杜绝攻击者探测其它企业租户的存在性；
3. **RBAC 角色权限矩阵**：
   - 企业管理员（`company_admin`）与平台管理员（`platform_admin`）享有用户管理权限；
   - 投标编写人（`bid_writer`）等业务角色仅允许只读查看本公司用户列表（用于项目指派选择器），写操作严格拦截 403 `FORBIDDEN`；
4. **停用资产交接安全门禁**：
   - 当用户在未归档的在投项目中担任标段负责人、分册负责人或编写人时，直接停用严格返回 409 `USER_TRANSFER_REQUIRED`；
   - 提供有效同企业 `successor_user_id` 后在同一事务中完成全量交接并停用账号。

---

## 2. 请求与响应报文范例（RFC 7807 统一错误体）

### 2.1 用户列表查询成功（HTTP 200 OK，密码绝对脱敏）

**请求报文**：
```http
GET /api/v1/users?company_id=alpha HTTP/1.1
Host: localhost:8000
Authorization: Bearer <alpha_admin_token>
```

**响应报文**：
```json
{
  "total": 3,
  "items": [
    {
      "id": "formal-alpha-admin",
      "name": "Alpha 企业管理员",
      "display_name": "Alpha 企管",
      "company_id": "alpha",
      "role": "company_admin",
      "status": "active",
      "created_at": 1729900000.0,
      "updated_at": 1729900000.0
    },
    {
      "id": "formal-alpha-writer",
      "name": "Alpha 标书编写人",
      "display_name": "Alpha 标书编写人",
      "company_id": "alpha",
      "role": "bid_writer",
      "status": "active",
      "created_at": 1729900000.0,
      "updated_at": 1729900000.0
    }
  ]
}
```

### 2.2 弱密码拦截响应（HTTP 422 PASSWORD_WEAK）

**请求报文**：
```http
POST /api/v1/users HTTP/1.1
Host: localhost:8000
Authorization: Bearer <alpha_admin_token>
Content-Type: application/json

{
  "username": "weak_pwd_user",
  "name": "弱密码用户",
  "company_id": "alpha",
  "role": "bid_writer",
  "password": "simplepassword"
}
```

**响应报文**：
```json
{
  "code": "PASSWORD_WEAK",
  "message": "密码强度不足：密码必须至少包含大写字母、小写字母、数字、特殊符号中的 3 类字符（当前满足 1 类）。",
  "details": {
    "field": "password"
  },
  "traceId": "req-9b817cfa2"
}
```

### 2.3 停用未交接资产阻断拦截（HTTP 409 USER_TRANSFER_REQUIRED）

**请求报文**：
```http
PATCH /api/v1/users/transfer-target-lead HTTP/1.1
Host: localhost:8000
Authorization: Bearer <alpha_admin_token>
Content-Type: application/json

{
  "status": "disabled"
}
```

**响应报文**：
```json
{
  "code": "USER_TRANSFER_REQUIRED",
  "message": "用户 transfer-target-lead 仍作为项目负责人或章节编写人绑定在 1 个未完结在投项目及 0 个进行中章节，停用前必须转交名下资产。",
  "details": {
    "user_id": "transfer-target-lead",
    "untransferred_projects": [
      {
        "project_id": "project-alpha-active-1",
        "project_name": "Alpha 智慧政务在投标段",
        "role_in_project": "lead"
      }
    ],
    "untransferred_chapters": [],
    "required_action": "请指定 successor_user_id 执行资产交接后再停用"
  },
  "traceId": "req-3fa829ef1"
}
```

### 2.4 附带交接人平滑停用成功（HTTP 200 OK）

**请求报文**：
```http
PATCH /api/v1/users/transfer-target-lead HTTP/1.1
Host: localhost:8000
Authorization: Bearer <alpha_admin_token>
Content-Type: application/json

{
  "status": "disabled",
  "successor_user_id": "formal-alpha-admin",
  "reason": "人员工作调动交接"
}
```

**响应报文**：
```json
{
  "id": "transfer-target-lead",
  "name": "待交接项目经理",
  "display_name": "待交接经理",
  "company_id": "alpha",
  "role": "project_lead",
  "status": "disabled",
  "created_at": 1729900000.0,
  "updated_at": 1729900120.0
}
```

---

## 3. 断点排查与最小胶水修改记录

| 断点编号 | 断点位置 | 现象描述 | 修复方案与最小胶水代码 |
|---|---|---|---|
| BP-1 | `backend/bid-core/icg/domain/user_management.py` | 访问 `self.repository.state` 报 `AttributeError: 'MemoryRepository' object has no attribute 'state'` | 依从系统规范调用 `self.repository.read()` 获取当前状态，并在 `MemoryRepository` 中添加 `@property def state(self): return self.read()` 兼容别名 |
| BP-2 | `backend/bid-core/icg/domain/frozen_error_codes.py` | 缺少冻结错误码 `PASSWORD_WEAK` 与 `USER_TRANSFER_REQUIRED` | 在 `icg/domain/errors.py` 与 `icg/domain/frozen_error_codes.py` 中严格按字母序补齐登记两项错误码 |
| BP-3 | `backend/bid-core/icg/infra/memory_repository.py` | `Account` 实体缺少 `status`、`created_at`、`updated_at` 字段 | 在 `Account` 实体定义中扩充默认值 `status: str = "active"` 与时间戳字段，确保双仓储同构 |
| BP-4 | `tests/backend/test_user_transfer_rbac_glue.py` | 测试用例在同一进程中依赖前一用例创建的测试项目，隔离执行时项目不存在 | 抽离 `_seed_lead_and_project` 独立夹具，保证各个测试用例自包含、幂等且可重复执行 |

---

## 4. 验证与测试证据

### 4.1 后端自动化专属集成测试（6 项全绿）

运行命令：
```bash
pytest tests/backend/test_user_transfer_rbac_glue.py -v
```

执行结果：
```text
============================= test session starts =============================
rootdir: C:\Users\徐佳馨\if-children-have-been-grown
configfile: pytest.ini
collected 6 items

tests/backend/test_user_transfer_rbac_glue.py::test_unauthenticated_user_api_blocked_401 PASSED [ 16%]
tests/backend/test_user_transfer_rbac_glue.py::test_user_list_retrieval_and_sanitization PASSED [ 33%]
tests/backend/test_user_transfer_rbac_glue.py::test_password_strength_validation_422 PASSED [ 50%]
tests/backend/test_user_transfer_rbac_glue.py::test_deactivation_without_transfer_blocked_409 PASSED [ 66%]
tests/backend/test_user_transfer_rbac_glue.py::test_deactivation_with_successor_transfer_success PASSED [ 83%]
tests/backend/test_user_transfer_rbac_glue.py::test_tenant_and_rbac_isolation PASSED [100%]

============================== 6 passed in 7.40s ==============================
```

### 4.2 OpenAPI 契约一致性校验（0 漂移）

运行命令：
```bash
python backend/bid-core/export_openapi.py --check
```

执行结果：
```text
[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.
```

### 4.3 前端单元测试权威校验（445 项全绿）

运行命令：
```bash
pnpm --dir frontend/web test
```

执行结果：
```text
✔ 1. 用户管理 API 函数导出与签名验证 (0.8278ms)
✔ 2. 静态 AST 与契约断言：对齐 /api/v1/users 端点 (14.7617ms)
✔ 1. 用户初始数据集与业务资产统计完整性 (1.2886ms)
✔ 2. “公司设置只能调严不能调宽”密码策略合规校验 (1.3221ms)
✔ 3. 密码强度与字符类别动态核验算法 (0.5468ms)
✔ 4. 新增用户表单校验与查重防线 (0.429ms)
✔ 5. 停用前业务资产强制交接合规红线校验（M1-P10-F2） (0.3372ms)
✔ 6. 执行资产交接与状态停用领域逻辑断言 (2.5447ms)
✔ 7. 8 角色 RBAC 细粒度权限感知与多租户隔离过滤 (0.8259ms)
✔ 8. UsersPage.tsx 与 GlobalPagesContent.tsx AST 静态契约断言 (1.292ms)
...
ℹ tests 445
ℹ suites 0
ℹ pass 445
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ duration_ms 5156.1592
```

### 4.4 前端生产构建

运行命令：
```bash
pnpm --dir frontend/web build
```

执行结果：
```text
$ tsc -b && vite build
✓ built in 1.08s
```

---

## 5. 项目进度与治理同步

| 对象 | 同步状态与说明 |
|---|---|
| PRD | 核对 §5.10.1、§5.10.2 与 §6.9，契约完全对齐，无冲突 |
| ROADMAP | M1 / Phase 2 账号安全与交接能力推进，符合既定里程碑 |
| ARCHITECTURE | 用户管理划分至 `icg/api/users.py` 与 `icg/domain/user_management.py`，保持 DDD 限界上下文分包 |
| TASK_BOARD | 注册 `INT-USER-TRANSFER-RBAC-GLUE`，状态推至 `in-review`，建议由 PM 标 done |
| DOCUMENT_INDEX | 登记 D-820 交付报告与 D-821 代码说明 |

---

## 6. 风险与后续建议

1. **交接历史调阅前端可视化**：当前项目团队中已将交接记录（`handoffs`）落盘并持久化，后续在标段详情项目成员面板中可增加交接日志展示抽屉；
2. **账号批量停用与离职交接**：当前 API 支持单用户停用交接与独立批量转交资产，后续若有批量人员转岗需求，可直接复用底层 `_execute_asset_transfer` 领域方法。
