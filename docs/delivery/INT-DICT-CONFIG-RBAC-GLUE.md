# 任务交付：字典配置与元数据停用/角色权限端到端契约联调（INT-DICT-CONFIG-RBAC-GLUE）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | INT-DICT-CONFIG-RBAC-GLUE |
| 代码解释 | [字典配置与元数据停用/角色权限端到端契约联调代码说明](../code/INT-DICT-CONFIG-RBAC-GLUE.md) |
| 验收 | 1. **角色权限门禁端到端核验**：验证平台管理员（`platform_admin`）与公司管理员（`company_admin`）具备数据字典与代码表配置的完整操作权（新建字典项、修改标签、排序权重以及切换启用/停用）；普通编写人（`bid_writer`）、项目负责人（`project_lead`）、合规审计员（`auditor`）、只读观察员（`viewer`）等非管理角色发起写操作（POST / PATCH / DELETE）统一被严格拦截 403 `FORBIDDEN`，满足 RFC 7807 统一错误响应；<br>2. **核心安全红线门禁端到端落地**：严格落实 PRD v1.8 §5.10.3 与 §6.9 “已在生产业务中使用的字典代码只能停用，严禁物理硬删除”红线。尝试物理删除系统内置核心代码（`is_builtin=true`）或已在业务中引用的代码（`in_use=true`，如 `check_status/blocker`、`project_status/draft`）时，后端统一拦截抛出 409 `DICT_ITEM_IN_USE`，杜绝历史标书快照与审计数据断链损坏；仅允许未被引用的自定义代码执行安全物理删除；<br>3. **同分类代码唯一性约束**：在同字典分类下尝试创建重复的 `item_code` 时，后端精确校验拦截并抛出 409 `DICT_CODE_DUPLICATED`，返回统一错误体；<br>4. **启停用正常生命周期与查询过滤**：正常支持管理员通过 `PATCH` 切换 `is_disabled: true / false`；查询代码项接口 `GET /api/v1/metadata/dict/types/{type_code}/items` 支持 `include_disabled=false` 过滤剔除已停用项；<br>5. **公司多租户强隔离**：公司自定义代码项强绑定 `company_id`，Alpha 公司自定义项对 Beta 公司严格不可见，平台管理员具备全局跨租户调阅与管理能力；<br>6. **OpenAPI 契约零漂移**：执行 `python backend/bid-core/export_openapi.py --check` 核验 100% 一致（0 契约漂移）；<br>7. **全自动化回归与工程治理全绿**：专属联调测试 `tests/backend/test_dict_config_rbac_glue.py` 7 项全绿，关联回归套件 25 项全通，前端单测 420 项全绿，前端 Vite 生产构建 910ms 成功，工程治理脚本通过。 |
| 项目进度 | 本次交付已完成数据字典配置端到端契约打通、安全红线拦截门禁与 8 角色权限核验，状态推至 in-review，建议 PM 标 done |
<!-- task-delivery:end -->

## 1. 任务背景与目标

依据 PRD MVP v1.8 §5.10.3、§6.9 与前端 A-03 字典配置页（APP-M2-T024）规范，系统集中纳管项目、章节、长任务、合规检查、导出交付、编辑租约 6 大状态码表及需求分类、信源层级、SLA 指标等核心业务字典。本卡作为前后端联调工单，核心职责是打通 `/api/v1/metadata/dict/*` 契约胶水层：
1. **统一错误码冻结与响应规范**：在 `icg/domain/errors.py` 中登记 409 状态下的 `DICT_ITEM_IN_USE` 与 `DICT_CODE_DUPLICATED`，统一遵循 RFC 7807（`code`, `message`, `details`, `traceId`）；
2. **角色权限门禁核验（RBAC）**：贯彻管理员可管、写作者与审计员只读的严格权限隔离；
3. **安全红线端到端贯通**：落实在用与内置代码防硬删除门禁（`DICT_ITEM_IN_USE`）与重复代码门禁（`DICT_CODE_DUPLICATED`）；
4. **前端 API 胶水封装与多租户隔离**：提供类型化前端交互层 `dict-config-api.ts`，保障租户隔离与 OpenAPI 零漂移。

---

## 2. 交付清单

| 文件路径 | 模块性质 | 职责说明 |
|---|---|---|
| `backend/bid-core/icg/domain/errors.py` | 错误码冻结表 | 在 HTTP 409 组中登记 `DICT_ITEM_IN_USE` 与 `DICT_CODE_DUPLICATED` 错误码 |
| `backend/bid-core/icg/domain/dict_config.py` | 字典领域服务 | 新建 `DictConfigService`，提供字典类型与代码项查询、代码重复校验、在用与内置代码防硬删除安全红线、启停用切换以及租户数据隔离 |
| `backend/bid-core/icg/api/field_metadata.py` | API 路由端点 | 注册 `/api/v1/metadata/dict/types`、`/api/v1/metadata/dict/types/{type_code}/items`、`POST /api/v1/metadata/dict/items`、`PATCH /api/v1/metadata/dict/items/{type_code}/{item_code}` 与 `DELETE /api/v1/metadata/dict/items/{type_code}/{item_code}` 5 大标准 RESTful 接口 |
| `frontend/web/src/admin/dict-config-api.ts` | 前端契约胶水 | 提供标准 TypeScript API 客户端函数与响应类型声明，封装统一错误捕获与请求构造 |
| `spec/openapi/demo-v1.json` | OpenAPI 契约 | 导出并保持 100% 一致性，包含新增接口与错误模型定义 |
| `tests/backend/test_dict_config_rbac_glue.py` | 专属联调测试 | 新建端到端自动化联调测试，覆盖类型查询、代码增改、重复代码 409、在用删除 409、RBAC 403 越权拦截、401 未认证与租户数据隔离 7 大测试项 |

---

## 3. 契约打通与典型报文

### 3.1 调阅所有字典分类 (`GET /api/v1/metadata/dict/types`)
- **请求**：
  ```http
  GET /api/v1/metadata/dict/types HTTP/1.1
  Host: localhost:8000
  Authorization: Bearer <company_admin_token>
  ```
- **响应**：`200 OK`
  ```json
  {
    "total": 12,
    "items": [
      {
        "type_code": "project_status",
        "type_name": "项目状态",
        "scope": "system",
        "description": "标书编制全流程项目生命周期状态",
        "total_items": 8,
        "active_items": 8
      },
      {
        "type_code": "check_status",
        "type_name": "合规检查状态",
        "scope": "system",
        "description": "合规排查通过/警告/废标阻断状态",
        "total_items": 3,
        "active_items": 3
      },
      {
        "type_code": "requirement_category",
        "type_name": "需求分类",
        "scope": "business",
        "description": "招标文件解析需求条目分类",
        "total_items": 5,
        "active_items": 5
      }
    ]
  }
  ```

### 3.2 尝试物理删除在用或内置代码（规则红线拦截 409）
- **请求**：
  ```http
  DELETE /api/v1/metadata/dict/items/check_status/blocker HTTP/1.1
  Host: localhost:8000
  Authorization: Bearer <company_admin_token>
  ```
- **响应**：`409 Conflict` (遵循 RFC 7807)
  ```json
  {
    "code": "DICT_ITEM_IN_USE",
    "message": "字典代码【blocker】属于系统内置核心代码，严禁物理硬删除；如需禁用请执行停用操作（is_disabled=true）。",
    "details": {
      "type_code": "check_status",
      "item_code": "blocker",
      "is_builtin": true
    },
    "traceId": "9b12a3487c64e019f2a412803b9f481c"
  }
  ```

### 3.3 尝试新增重复代码（唯一性约束拦截 409）
- **请求**：
  ```http
  POST /api/v1/metadata/dict/items HTTP/1.1
  Host: localhost:8000
  Authorization: Bearer <company_admin_token>
  Content-Type: application/json

  {
    "type_code": "requirement_category",
    "item_code": "qualification",
    "label": "重复的资质要求"
  }
  ```
- **响应**：`409 Conflict` (遵循 RFC 7807)
  ```json
  {
    "code": "DICT_CODE_DUPLICATED",
    "message": "字典分类【requirement_category】下已存在代码【qualification】，禁止重复创建。",
    "details": {
      "type_code": "requirement_category",
      "item_code": "qualification"
    },
    "traceId": "c83fe1892a0134bc5719ef84a298dcba"
  }
  ```

### 3.4 非管理员角色越权写操作（RBAC 门禁拦截 403）
- **请求**：
  ```http
  POST /api/v1/metadata/dict/items HTTP/1.1
  Host: localhost:8000
  Authorization: Bearer <bid_writer_token>
  Content-Type: application/json

  {
    "type_code": "requirement_category",
    "item_code": "unauthorized_test",
    "label": "越权代码"
  }
  ```
- **响应**：`403 Forbidden` (遵循 RFC 7807)
  ```json
  {
    "code": "FORBIDDEN",
    "message": "当前用户身份为【bid_writer】，仅拥有字典配置调阅权限；新建、修改、启停用与删除操作仅限平台管理员或公司管理员执行。",
    "details": {},
    "traceId": "61a8ef10927cba8432194857efcb9102"
  }
  ```

---

## 4. 验证证据与测试记录

### 4.1 后端专属端到端联调测试
- **命令**：`pytest tests/backend/test_dict_config_rbac_glue.py`
- **结果**：`7 passed in 6.48s`
  - `test_list_dict_types_and_items`: PASSED
  - `test_admin_create_and_toggle_disable_dict_item`: PASSED
  - `test_duplicate_dict_code_blocked_409`: PASSED
  - `test_delete_in_use_or_builtin_dict_item_blocked_409`: PASSED
  - `test_role_rbac_write_forbidden_403`: PASSED (涵盖 bid_writer / project_lead / viewer / auditor / group_admin / data_admin)
  - `test_unauthenticated_request_blocked_401`: PASSED
  - `test_tenant_isolation_dict_items`: PASSED (Alpha 专有项对 Beta 隔离，平台管理员全局可见)

### 4.2 核心回归套件复测
- **命令**：`pytest tests/backend/test_status_tag_metadata_glue.py tests/backend/test_reference_flow.py`
- **结果**：`25 passed in 24.91s`

### 4.3 前端单元测试与生产构建
- **命令**：`pnpm --dir frontend/web test`
- **结果**：`420 passed (100%), 0 fail, 0 skipped`
- **命令**：`pnpm --dir frontend/web build`
- **结果**：`✓ built in 910ms`（0 error，0 warning）

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
| `docs/PRD.md` | 对齐 PRD MVP v1.8 §5.10.3（状态注册表）与 §6.9（数据字典与代码表管理），规则红线“已使用代码只能停用不可硬删除”在服务端强制拦截闭环 |
| `docs/ARCHITECTURE.md` | 接口规范严格收口至 `/api/v1/metadata/dict/*`，禁止写入废弃 demo 接口，错误体统一遵循 RFC 7807 与 X-Request-ID |
| `docs/TASK_BOARD.md` | `INT-DICT-CONFIG-RBAC-GLUE` 推至 `in-review` |
| `docs/tasks/BE-M0.md` | 注册任务卡 `INT-DICT-CONFIG-RBAC-GLUE` 并推至 `in-review` |
| `docs/DOCUMENT_INDEX.md` | 登记 D-790（交付报告）与 D-791（代码说明） |
