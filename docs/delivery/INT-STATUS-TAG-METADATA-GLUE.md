# 任务交付：状态注册表与元数据接口端到端契约联调（INT-STATUS-TAG-METADATA-GLUE）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | INT-STATUS-TAG-METADATA-GLUE |
| 代码解释 | [状态注册表与元数据接口端到端契约联调代码说明](../code/INT-STATUS-TAG-METADATA-GLUE.md) |
| 验收 | 1. **6 大核心业务状态枚举全覆盖与对齐**：验证后端 6 大状态枚举（ProjectStatus、ChapterStatus、JobStatus、CheckStatus、ExportStatus、LockStatus）在 `GET /api/v1/metadata/fields/status`、`GET /api/v1/metadata/fields/statuses` 及各专用接口（`/chapter`, `/job`, `/check`, `/export`, `/lock`）返回中的选项值域，与前端 `StatusTag` / `status-registry.ts` 规范完全对齐；前端通过扩展别名表（如 `opened`, `confirmed`, `queued`, `generating`, `expired`, `locked`, `taken_over`）实现所有合法业务状态无缝映射，严禁出现未知状态裸显英文或色值丢失；<br>2. **全量元数据聚合接口支持**：支持 `GET /api/v1/metadata/fields/all`，一次性聚合拉取跨全分类（项目、招标、资料、SLA、章节、任务、检查、导出、租约）字段元数据字典，返回标准 `FieldMetadataListResponse` 结构；<br>3. **多租户与 8 大标准 RBAC 角色字段编辑权限自适应**：在非演示模式（`VITE_DEMO=0`）下，根据当前 JWT 会话中的账户角色动态计算字段字典中的 `editable` 标记：只读系统角色（`viewer`, `auditor`, `platform_admin`, `group_admin`）调阅元数据时，所有字段严格封退为 `editable=False`；写作者角色（`project_lead`, `bid_writer`, `company_admin`, `data_admin`）调阅时，保留字段原生定义的编辑资质；<br>4. **未知状态优雅降级与 RFC 7807 统一错误响应**：前端提供包含 neutral 灰色令牌与 `QuestionCircleOutlined` 图标的永不崩溃回退对象；后端对未知分类请求返回 404 `NOT_FOUND`，未登录或非法 Token 拦截 401 `UNAUTHENTICATED`，均符合 RFC 7807 标准；<br>5. **OpenAPI 契约零漂移**：`backend/bid-core/export_openapi.py --check` 核验 100% 一致（0 契约漂移）；<br>6. **全自动化回归与工程治理全绿**：专属联调测试 `tests/backend/test_status_tag_metadata_glue.py` 4 项全绿，元数据相关套件 10 项全通，前端权威单测 414 项全绿，前端 Vite 生产构建 1.50s 成功，工程治理检查通过。 |
| 项目进度 | 本次交付已完成状态注册表与元数据接口端到端契约打通与自动化回归验证，代码与测试全绿，状态推至 in-review，建议 PM 标 done |
<!-- task-delivery:end -->

## 1. 任务背景与目标

依据 PRD MVP v1.8 §5.10.3、§6.9 及数据字典 v1.9 §4.16 规范，系统规范了六大业务状态码表（项目状态、章节状态、长任务状态、合规检查状态、导出交付状态、编辑租约锁状态），前端已落地 `StatusTag` 与 `status-registry.ts` 纯逻辑状态注册表（APP-M2-T023）。本卡负责打通：
1. **前后端业务状态枚举与代码表完全对齐**：打通后端 `/api/v1/metadata/fields/status` 与各领域专用元数据接口，确保每个业务状态均具备中文显示名、规范语义类型与 WCAG AA 4.5:1 对比度配色，杜绝出现前端回退至未知或裸显英文代码；
2. **全量聚合查询支持**：支持 `GET /api/v1/metadata/fields/all`，便于前端表格/表单一次性完成元数据冷启动预热；
3. **8 大标准 RBAC 角色字段编辑权限自适应**：落实「只读身份不可编辑」安全基线，后端在返回字段元数据时依据用户角色自适应计算 `editable` 属性；
4. **统一错误体与契约零漂移**：遵循 RFC 7807 统一错误响应，维持 OpenAPI 契约 0 漂移。

---

## 2. 交付清单

| 文件路径 | 模块性质 | 职责说明 |
|---|---|---|
| `backend/bid-core/icg/domain/field_metadata.py` | 后端核心业务域 | 扩充 `chapter`, `job`, `check`, `export`, `lock`, `status` 领域分类定义；支持 `all` 全量字段聚合；依据请求 Principal 角色实现只读角色的 `editable=False` 动态封退；扩充分类别名映射 |
| `frontend/web/src/shared/status-registry.ts` | 前端状态注册表 | 补充 `STATUS_ALIASES` 兼容映射（覆盖 `opened`, `planning`, `confirmed`, `queued`, `generating`, `expired`, `locked`, `taken_over` 等全量合法业务代码），确保与后端选项 100% 映射 |
| `backend/bid-core/icg/domain/domain.py` | 后端领域模型 | 补充 `alpha-auditor`, `alpha-group-admin` 演示账号 ID，完善 8 大角色全量会话测试覆盖 |
| `backend/bid-core/icg/infra/memory_repository.py` | 后端基础设施 | 在内置演示账号池中植入 `alpha-auditor`（审核人，角色 `auditor`）与 `alpha-group-admin`（集团管理员，角色 `group_admin`） |
| `tests/backend/test_status_tag_metadata_glue.py` | 专属联调测试 | 新建端到端专属联调测试，覆盖 `all` 全量聚合、6 大状态码表映射完整性、8 角色 `editable` 权限自适应矩阵、401/404 安全拦截与 RFC 7807 统一错误体合规性 |

---

## 3. 契约打通与典型报文

### 3.1 6 大业务状态码表获取 (`GET /api/v1/metadata/fields/status`)
- **请求**：
  ```http
  GET /api/v1/metadata/fields/status HTTP/1.1
  Host: localhost:8000
  Authorization: Bearer <token>
  ```
- **响应**：`200 OK`
  ```json
  {
    "category": "status",
    "category_name": "六大业务状态注册表",
    "total": 6,
    "fields": [
      {
        "field_key": "project_status",
        "label": "项目状态",
        "data_type": "string",
        "render_type": "tag",
        "editable": false,
        "options": [
          {"value": "draft", "label": "草稿"},
          {"value": "parsing", "label": "解析中"},
          {"value": "pending_confirm", "label": "待确认"},
          {"value": "in_progress", "label": "编写中"},
          {"value": "checking", "label": "检查中"},
          {"value": "exportable", "label": "可导出"},
          {"value": "exported", "label": "已导出"},
          {"value": "submitted", "label": "已递交"},
          {"value": "opened", "label": "已开标"},
          {"value": "closed", "label": "已结束"},
          {"value": "cancelled", "label": "已取消"}
        ]
      },
      {
        "field_key": "chapter_status",
        "label": "章节状态",
        "data_type": "string",
        "render_type": "tag",
        "editable": false,
        "options": [
          {"value": "not_started", "label": "未开始"},
          {"value": "generating", "label": "生成中"},
          {"value": "draft", "label": "草稿"},
          {"value": "reviewed", "label": "已复核"},
          {"value": "approved", "label": "已定稿"},
          {"value": "locked", "label": "已锁定"},
          {"value": "stale", "label": "已失效"}
        ]
      },
      {
        "field_key": "job_status",
        "label": "长任务状态",
        "data_type": "string",
        "render_type": "tag",
        "editable": false,
        "options": [
          {"value": "queued", "label": "排队中"},
          {"value": "running", "label": "进行中"},
          {"value": "completed", "label": "已完成"},
          {"value": "failed", "label": "异常失败"},
          {"value": "cancelled", "label": "已取消"}
        ]
      },
      {
        "field_key": "check_status",
        "label": "合规检查状态",
        "data_type": "string",
        "render_type": "tag",
        "editable": false,
        "options": [
          {"value": "passed", "label": "合规通过"},
          {"value": "warning", "label": "合规提醒"},
          {"value": "blocker", "label": "废标阻断"}
        ]
      },
      {
        "field_key": "export_status",
        "label": "导出交付状态",
        "data_type": "string",
        "render_type": "tag",
        "editable": false,
        "options": [
          {"value": "idle", "label": "待导出"},
          {"value": "processing", "label": "排版中"},
          {"value": "completed", "label": "已生成"},
          {"value": "failed", "label": "导出失败"}
        ]
      },
      {
        "field_key": "lock_status",
        "label": "编辑租约状态",
        "data_type": "string",
        "render_type": "tag",
        "editable": false,
        "options": [
          {"value": "unlocked", "label": "空闲可编辑"},
          {"value": "locked_self", "label": "本人编辑中"},
          {"value": "locked_other", "label": "他人占用"},
          {"value": "expired", "label": "租约过期"}
        ]
      }
    ],
    "items": [...]
  }
  ```

### 3.2 只读角色请求元数据自适应封退 (`editable=False`)
- **请求**：
  ```http
  GET /api/v1/metadata/fields/project HTTP/1.1
  Host: localhost:8000
  Authorization: Bearer <viewer-or-auditor-token>
  ```
- **响应**：`200 OK`
  ```json
  {
    "category": "project",
    "category_name": "投标项目",
    "total": 12,
    "fields": [
      {
        "field_key": "project_name",
        "label": "项目名称",
        "data_type": "string",
        "required": true,
        "editable": false,
        "render_type": "text"
      }
    ]
  }
  ```
  *说明*：原本设计上可由项目负责人修改的 `project_name` 字段，在只读系统角色（`viewer`, `auditor`, `platform_admin`, `group_admin`）调阅时，由后端自适应输出 `editable: false`，保障前端表单自动置灰或渲染为只读纯文本模式。

### 3.3 未知元数据分类拦截
- **请求**：
  ```http
  GET /api/v1/metadata/fields/non_existent_category_foo HTTP/1.1
  Host: localhost:8000
  Authorization: Bearer <token>
  ```
- **响应**：`404 Not Found`（符合统一错误体标准）
  ```json
  {
    "code": "NOT_FOUND",
    "message": "未找到该分类的字段元数据：non_existent_category_foo。",
    "traceId": "trace-xxxx-xxxx"
  }
  ```

---

## 4. 验收执行证据

### 4.1 专属全链路前后端联调测试通过
```powershell
pytest tests/backend/test_status_tag_metadata_glue.py -v
```
输出证据：
```
tests/backend/test_status_tag_metadata_glue.py::test_get_field_metadata_all_category PASSED              [ 25%]
tests/backend/test_status_tag_metadata_glue.py::test_six_status_domains_metadata_mapping_complete PASSED [ 50%]
tests/backend/test_status_tag_metadata_glue.py::test_rbac_editable_permission_matrix_across_8_roles PASSED [ 75%]
tests/backend/test_status_tag_metadata_glue.py::test_field_metadata_security_and_rfc7807_error_compliance PASSED [100%]
============================== 4 passed in 3.78s ==============================
```

### 4.2 字段元数据完整套件回归
```powershell
pytest tests/backend/test_status_tag_metadata_glue.py tests/backend/test_field_metadata.py
```
输出证据：
```
============================= 10 passed in 9.96s ==============================
```

### 4.3 OpenAPI 零契约漂移核验
```powershell
python backend/bid-core/export_openapi.py --check
```
输出证据：
```
[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.
```

### 4.4 前端权威单测全量通过
```powershell
pnpm --dir frontend/web test
```
输出证据：
```
ℹ tests 414, pass 414, fail 0, cancelled 0, skipped 0, todo 0
✔ test run finished (5.01s)
```

### 4.5 前端生产构建无警告
```powershell
pnpm --dir frontend/web build
```
输出证据：
```
✓ 3412 modules transformed.
dist/index.html                                1.56 kB │ gzip:   0.69 kB
dist/assets/index-B_vkuLbS.css                35.23 kB │ gzip:   7.71 kB
dist/assets/index-Crbx3Ir1.js                491.59 kB │ gzip: 153.83 kB
✓ built in 1.50s
```

### 4.6 工程治理脚本检查
```powershell
node scripts/check-project-governance.cjs
```
输出证据：
```
治理检查通过：570 份 Markdown、421 项任务、38 项 Issue。
```

---

## 5. 主 Agent 业务验收五条金标准对照

| 金标准 | 判定 | 对照说明与依据 |
|---|---|---|
| 1. 主路径推进 | **达成** | 彻底打通项目、章节、长任务、检查、导出与租约 6 大业务域的状态标签与字段字典元数据，杜绝未知状态裸显英文或色值丢失，有力支撑全链路状态呈现。 |
| 2. 安全与隔离底线 | **达成** | 严格贯彻多租户与角色权限底线：只读系统角色（`viewer`, `auditor`, `platform_admin`, `group_admin`）调阅元数据时所有字段被自适应封退为只读（`editable=False`），防范越权误导。 |
| 3. 关演示正式可用 | **达成** | 机制基于标准 RBAC 8 角色模型与标准 `/api/v1` 契约，支持真实 JWT 会话下的全量字段字典解析与多分类别名容错，在 `VITE_DEMO=0` 下完全自洽。 |
| 4. 诚实记录阻断门禁 | **达成** | 对未知分类严格返回 404 `NOT_FOUND`，未登录拦截 401 `UNAUTHENTICATED`；前端设置带有 WCAG 4.5:1 对比度兜底对象的安全回退机制，保障业务健壮性。 |
| 5. 拒绝空壳冒充交付 | **达成** | 拒绝静态 mock；真实打通 FastAPI `/api/v1/metadata/fields/{category}`、领域层动态权限过滤与前端 `StatusTag` / `status-registry.ts` 纯逻辑映射。 |

---

## 6. 局限性与后续推进

1. 当前 6 大状态已通过 `/api/v1/metadata/fields/status` 与 `/api/v1/metadata/fields/{domain}` 提供标准代码表，前端已实现全量对齐；后续可结合 A-03 字典配置页（APP-M2-T024）进一步支持企业自定义扩展状态展示别名；
2. 建议人类 PM 审核本卡后标为 `done`。
