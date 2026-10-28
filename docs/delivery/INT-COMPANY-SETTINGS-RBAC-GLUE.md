# INT-COMPANY-SETTINGS-RBAC-GLUE 交付报告：企业设置与安全策略/租户隔离端到端契约联调

为什么有这个文件：记录前後端联调工单 INT-COMPANY-SETTINGS-RBAC-GLUE（企业设置与安全策略/租户隔离端到端契约联调）的交付状态、请求/响应报文、断点排查、胶水代码修改与质量门禁证据。

它解决什么问题：
1. 打通非演示模式（`VITE_DEMO=0`）下，企业设置与安全策略的完整端到端契约（`GET /api/v1/companies/{company_id}/settings` 与 `PATCH /api/v1/companies/{company_id}/settings`）；
2. 验证多租户强隔离底线（非超管跨企业访问严格返回 404 `NOT_FOUND`，杜绝企业存在性嗅探与越权）；
3. 验证标准 8 角色 RBAC 细粒度权限控制（超管可管理任意企业，企管仅可管理本企业，企业内普通编写人与只读角色仅允许只读查看本企业设置，修改严格拦截 403 `FORBIDDEN`）；
4. 严格贯彻“**企业设置只能调严不能调宽**”基线安全策略与规范 9.11 编辑锁三元数学约束（密码长度 < 8、字符种类 < 3、连续失败锁定 > 5、锁超时 > 60、自动保存 > 心跳、心跳×10 > 锁超时等一律拦截 422 `SETTING_VALUE_OUT_OF_BOUNDS` 并返回 RFC 7807 统一错误体）；
5. 保持 OpenAPI 规范 100% 一致性（0 契约漂移），并通过全量前端构建与单元测试。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | INT-COMPANY-SETTINGS-RBAC-GLUE |
| 代码解释 | [docs/code/INT-COMPANY-SETTINGS-RBAC-GLUE.md](../code/INT-COMPANY-SETTINGS-RBAC-GLUE.md) |
| 文档登记 | [D-810](../DOCUMENT_INDEX.md) |
| 验收 | 6 项专属自动化集成测试全绿（6 passed in 7.32s）；OpenAPI 契约零漂移（100% consistent）；前端权威单元测试 435 passed 全绿；Vite 生产构建 984ms 编译通过；工程治理零死链门禁通过；建议由 PM 标 done |
| 项目进度 | 本工单已完成全部端到端契约联调与权威测试验证，状态转为 in-review，建议由 PM 标 done |
<!-- task-delivery:end -->

---

## 1. 业务背景与契约联调目标

依据 PRD MVP v1.8 §5.10.2（账号安全设置与 Q28 定案）、§5.11.9（编辑锁与自动保存心跳）、§6.9（配置项与平台默认值/上限）、数据字典 v1.9 §4.10 与 §4.17，前端已交付 `APP-M2-T025`（扩展字段与公司设置键表单框架）。本工单聚焦打通后端领域服务与前端 API 客户端的契约胶水层：

1. **端点规范**：
   - `GET /api/v1/companies/{company_id}/settings`：获取企业配置与安全策略；
   - `PATCH /api/v1/companies/{company_id}/settings`：增量安全更新企业配置与安全策略；
2. **多租户强隔离**：
   - 平台管理员（`platform_admin`）穿透跨租户管理；
   - 企业用户跨租户访问严格拦截 404 `NOT_FOUND`，防止攻击者通过 403 探测其它企业租户的存在性；
3. **RBAC 角色权限矩阵**：
   - 企业管理员（`company_admin`）拥有本公司读写权限；
   - 投标编写人（`bid_writer`）、项目负责人（`project_lead`）、只读成员（`viewer`）等仅可读本公司设置（用于界面规则展示与前端协同），修改请求拦截 403 `FORBIDDEN`；
4. **“只能调严不能调宽”安全策略红线**：
   - 密码最少长度只能 >= 平台下限 8 位，上限 32 位；
   - 密码字符种类数只能 >= 平台下限 3 类（大写、小写、数字、符号四类中的任意几类），上限 4 类；
   - 连续登录失败锁定次数只能 <= 平台上限 5 次（下限 1 次）；
   - 编辑锁超时时间只能 <= 平台上限 60 分钟，且必须大于释放提醒阈值 5 分钟（下限 6 分钟）；
   - 编辑锁心跳间隔在 15～120 秒之间，自动保存间隔在 5～60 秒之间；
   - 关联约束一：自动保存间隔必须 <= 心跳间隔；
   - 关联约束二：心跳间隔 × 10 必须 <= 锁超时总时长（秒）；
   - 章节生成最大循环轮数只能 <= 平台上限 5 轮（下限 1 轮）；
   - 修改样例条数必须在 3～5 条之间；
   - 越界统一抛出 422 `SETTING_VALUE_OUT_OF_BOUNDS`。

---

## 2. 请求与响应报文范例（RFC 7807 统一错误体）

### 2.1 调阅企业设置成功响应（HTTP 200 OK）

**请求报文**：
```http
GET /api/v1/companies/alpha/settings HTTP/1.1
Host: localhost:8000
Authorization: Bearer <alpha_admin_token>
```

**响应报文**：
```json
{
  "company_id": "alpha",
  "company_name": "Alpha 科技",
  "password_min_length": 8,
  "password_min_char_classes": 3,
  "max_login_attempts": 5,
  "session_timeout_minutes": 120,
  "edit_lock_timeout_minutes": 30,
  "edit_lock_heartbeat_seconds": 60,
  "editor_autosave_seconds": 10,
  "loop_max_rounds": 3,
  "assistant_suggestion_count": 3,
  "assistant_enabled": true,
  "assistant_kb_default": true,
  "assistant_allow_kb_off": true,
  "model_review_enabled": true,
  "dup_min_chars": 8,
  "dup_history_months": 24,
  "updated_at": null,
  "updated_by": null,
  "custom_settings": {}
}
```

---

### 2.2 调严企业安全策略成功（HTTP 200 OK）

**请求报文**：
```http
PATCH /api/v1/companies/alpha/settings HTTP/1.1
Host: localhost:8000
Authorization: Bearer <alpha_admin_token>
Content-Type: application/json

{
  "password_min_length": 12,
  "password_min_char_classes": 4,
  "max_login_attempts": 3,
  "edit_lock_timeout_minutes": 45,
  "edit_lock_heartbeat_seconds": 60,
  "editor_autosave_seconds": 15
}
```

**响应报文**：
```json
{
  "company_id": "alpha",
  "company_name": "Alpha 科技",
  "password_min_length": 12,
  "password_min_char_classes": 4,
  "max_login_attempts": 3,
  "session_timeout_minutes": 120,
  "edit_lock_timeout_minutes": 45,
  "edit_lock_heartbeat_seconds": 60,
  "editor_autosave_seconds": 15,
  "loop_max_rounds": 3,
  "assistant_suggestion_count": 3,
  "assistant_enabled": true,
  "assistant_kb_default": true,
  "assistant_allow_kb_off": true,
  "model_review_enabled": true,
  "dup_min_chars": 8,
  "dup_history_months": 24,
  "updated_at": "2026-10-27T10:21:40.123456+00:00",
  "updated_by": "formal-alpha-admin",
  "custom_settings": {}
}
```

---

### 2.3 调宽尝试拦截响应（HTTP 422 SETTING_VALUE_OUT_OF_BOUNDS）

**请求报文（试图设置低于平台下限的密码长度）**：
```http
PATCH /api/v1/companies/alpha/settings HTTP/1.1
Host: localhost:8000
Authorization: Bearer <alpha_admin_token>
Content-Type: application/json

{
  "password_min_length": 6
}
```

**响应报文（符合 RFC 7807 统一错误体）**：
```json
{
  "code": "SETTING_VALUE_OUT_OF_BOUNDS",
  "message": "密码最少位数只能调严，不能低于平台下限 8 位。",
  "details": {
    "field": "password_min_length",
    "min": 8,
    "value": 6
  },
  "traceId": "req-7f89b1c2-3e4d"
}
```

---

### 2.4 跨租户越权访问拦截响应（HTTP 404 NOT_FOUND）

**请求报文（Alpha 企管试图访问 Beta 设置）**：
```http
GET /api/v1/companies/beta/settings HTTP/1.1
Host: localhost:8000
Authorization: Bearer <alpha_admin_token>
```

**响应报文**：
```json
{
  "code": "NOT_FOUND",
  "message": "未找到指定企业 beta 或当前账号无权访问。",
  "details": {},
  "traceId": "req-9c88a4b1-2e1f"
}
```

---

### 2.5 企业内非管理员尝试修改拦截响应（HTTP 403 FORBIDDEN）

**请求报文（Alpha 标书编写人试图修改公司设置）**：
```http
PATCH /api/v1/companies/alpha/settings HTTP/1.1
Host: localhost:8000
Authorization: Bearer <alpha_writer_token>
Content-Type: application/json

{
  "password_min_length": 10
}
```

**响应报文**：
```json
{
  "code": "FORBIDDEN",
  "message": "只有企业管理员或平台超级管理员可修改企业设置与安全策略。",
  "details": {},
  "traceId": "req-1a2b3c4d-5e6f"
}
```

---

## 3. 契约胶水层修改清单

1. **错误码冻结与绑定**：
   - `backend/bid-core/icg/domain/errors.py`：在 HTTP 422 状态下登记冻结错误码 `"SETTING_VALUE_OUT_OF_BOUNDS"`；
   - `backend/bid-core/icg/domain/frozen_error_codes.py`：按严格字母序插入 `"SETTING_VALUE_OUT_OF_BOUNDS"`。
2. **后端领域模型与服务**：
   - 新建 `backend/bid-core/icg/domain/company_settings.py`，实现 `CompanySettingsModel`、`UpdateCompanySettingsRequest` 与 `CompanySettingsService`；
   - 内置“只能调严不能调宽”安全基线核验器与规范 9.11 编辑锁三元关系校验；
   - 落实多租户强隔离（跨公司 404 `NOT_FOUND`）与 RBAC 权限核验（非管理员写操作 403 `FORBIDDEN`，超管穿透跨租户管理）。
3. **API 端点注册与装配**：
   - 新建 `backend/bid-core/icg/api/companies.py`，注册 `GET` 与 `PATCH` 路由端点；
   - 更新 `backend/bid-core/icg/api/__init__.py` 导出 `include_company_routes`；
   - 更新 `backend/bid-core/icg/app/main.py` 挂载 `include_company_routes(application, service, current_user)`。
4. **前端类型化客户端契约胶水**：
   - 新建 `frontend/web/src/admin/company-settings-api.ts`，导出 `fetchCompanySettings` 与 `updateCompanySettings`；
   - 对齐后端 `CompanySettingsModel` 与 `UpdateCompanySettingsRequest` 数据模型；
   - 统一处理 Bearer Token 传递与 RFC 7807 统一错误响应解析。
5. **自动化测试套件**：
   - 新建 `tests/backend/test_company_settings_rbac_glue.py`（6 项集成测试用例，覆盖未认证 401、超管全权限跨租户调阅与修改、企业管理员管理本企业、跨租户 404 隔离拦截、同企业非管理员 403 拦截、只能调严不能调宽 10 维越界拦截）；
   - 新建 `frontend/web/tests/unit/company-settings-api.test.mjs`（2 项前端单元测试用例，验证函数导出契约与 AST 静态路由断言）。

---

## 4. 验证与质量门禁审计结果

| 验证项 | 执行命令 | 结果 | 结论 |
|---|---|---|---|
| 后端联调集成测试 | `pytest tests/backend/test_company_settings_rbac_glue.py` | 6 passed in 7.32s | 全部通过 |
| 会话与认证回归 | `pytest tests/backend/test_auth_login_rbac_glue.py` | 6 passed in 4.89s | 全部通过 |
| OpenAPI 契约一致性 | `python backend/bid-core/export_openapi.py --check` | 100% consistent (0 漂移) | 契约零漂移 |
| 前端权威单元测试 | `pnpm --dir frontend/web test` | 435 passed (0 failed) | 全部通过 |
| 前端生产构建编译 | `pnpm --dir frontend/web build` | 984ms built (0 errors) | 成功构建 |
| 工程治理规范核验 | `node scripts/check-project-governance.cjs` | 零死链、零漏登 | 检查通过 |

---

## 5. 项目状态与流转建议

- 当前任务卡：`INT-COMPANY-SETTINGS-RBAC-GLUE`
- 建议状态：**`in-review`**
- 终验建议：经 QA 终验签署与 PD 产品验收核准后，建议由 PM 将看板与任务卡正式推至 `done`。
