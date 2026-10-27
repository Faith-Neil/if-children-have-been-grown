# 任务交付：路由分层与平台管理员脱敏长任务全链路联调（INT-APP-SLIM-ROUTING）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | INT-APP-SLIM-ROUTING |
| 代码解释 | [路由分层与平台管理员脱敏长任务全链路联调代码说明](../code/INT-APP-SLIM-ROUTING.md) |
| 验收 | 1. **平台管理员脱敏任务视图（listJobsMasked）**：支持 `GET /api/v1/jobs?masked=true` 与 `GET /api/v1/jobs/masked`（或平台管理员 `platform_admin` 角色登录访问 `GET /api/v1/jobs`）。返回任务类型、企业标识脱敏（如 `al***`）、耗时毫秒、状态、错误码与脱敏摘要，隐藏敏感项目名称（统一替换为 `prj-***`）与原始招标文件名称，不暴露任务操作权限（`allowed_actions` 为空）；<br>2. **平台运维安全隔离与防嗅探**：平台管理员仅具备运维审计视图，严禁返回项目业务正文或密钥；直调普通项目业务接口（如 `/workspace`、`/generation/start`）或长任务详情/取消/重试接口时，严格触发多租户防嗅探机制返回 404 `NOT_FOUND`（而非 403，杜绝跨租户资源探测）；<br>3. **长任务取消与失败重试端到端鉴权**：项目负责人可执行 retry（`POST /api/v1/jobs/{job_id}/retry` -> 200），普通写作者与负责人可执行 cancel（200）；普通写作者/只读角色越权 retry 拦截 403 `PROJECT_LEAD_REQUIRED`；只读角色越权 cancel 拦截 403 `PROJECT_WRITER_REQUIRED`；非终态任务触发重试拦截 409 `VERSION_CONFLICT`；<br>4. **前端控制器胶水对接**：`useAppController.ts` 中的 `handleRetryJob` 修复为先向后端发起 `POST /api/v1/jobs/${encodeURIComponent(jobId)}/retry` 成功后再触发前端任务列表刷新；<br>5. **RFC 7807 统一错误响应**：所有 400/403/404/409 异常均返回标准 RFC 7807 Problem Details 结构（含 `type`, `title`, `status`, `detail`, `instance`），契约严格对齐；<br>6. **OpenAPI 契约零漂移**：`backend/bid-core/export_openapi.py --check` 核验 100% 一致（0 漂移）；<br>7. **全自动化回归与工程治理全绿**：专属联调测试 `tests/backend/test_app_routing_and_masked_jobs.py` 4 项全绿，长任务套件回归全绿，前端单元测试 403 passed，工程治理检查通过。 |
| 项目进度 | 本次交付已完成全链路前后端契约打通与自动化回归验证，代码与测试全绿，状态推至 in-review，建议 PM 标 done |
<!-- task-delivery:end -->

## 1. 任务背景与目标

依据 PRD MVP v1.8 §2.3（8 大标准 RBAC 角色体系）与 §5.12.4（长任务中心与平台运维脱敏审计），以及任务卡 `APP-M2-T022` 规范：
1. **平台管理员（`platform_admin`）脱敏审计**：平台运维管理员仅负责查看系统整体长任务吞吐、失败步骤与系统健康度，严禁接触客户敏感项目名称、招标文件正文与企业数据。长任务列表支持脱敏查询（`masked=true` 或平台管理员角色自动生效），企业标识掩码化（`al***`）、项目名替换为 `prj-***`、清空操作动作权限；
2. **多租户防嗅探安全边界**：平台管理员属于 `system` 域账号，无特定公司业务租户权限。其直接请求具体租户项目业务接口时，系统严格执行多租户隔离防嗅探策略返回 404 `NOT_FOUND`，杜绝横向越权嗅探资源是否存在；
3. **细粒度长任务操作权限**：打通 `POST /api/v1/jobs/{job_id}/retry` 与 `POST /api/v1/jobs/{job_id}/cancel`，严格遵循项目负责人（Lead）可重试、项目成员（Writer）可取消、只读观察员（Viewer）不可操作的权限矩阵；
4. **前端胶水联动**：完善前端控制器 `useAppController.ts` 的 `handleRetryJob`，打通后端真实重试 HTTP 调用；
5. **规范收敛**：新接口统一注册在 `/api/v1`，全量响应满足 RFC 7807，OpenAPI 契约保证 0 漂移。

---

## 2. 交付清单

| 文件路径 | 模块性质 | 职责说明 |
|---|---|---|
| `backend/bid-core/icg/api/workflow.py` | 后端 API 层 | 端点 `/api/v1/jobs` 增加 `masked: bool = Query(default=False)` 支持；显式挂载 `/api/v1/jobs/masked`（`operationId="listJobsMasked"`），打通平台管理员脱敏查询契约 |
| `backend/bid-core/icg/domain/workflow_orchestrator.py` | 后端编排层 | `WorkflowService.jobs()` 实现：平台管理员角色或 `masked=true` 参数下聚合全量任务并脱敏处理（企业代码掩码 `al***`、项目 ID 掩码 `prj-***`、耗时计算、清空 `allowed_actions`）；非脱敏严格保留企业租户强隔离 |
| `backend/bid-core/icg/domain/workflow_schemas.py` | 后端契约定义 | 补充长任务脱敏字段 `duration_ms`, `masked_company`, `masked_summary`, `is_masked`, `error_code`，严格保持 `recoverable: Literal[False] = False` 维持 OpenAPI schema 中 `const: false` 契约定义 |
| `backend/bid-core/icg/domain/domain.py` | 后端领域模型 | 将内置演示运维账号 `"platform-admin"` 纳入 `DEMO_ONLY_ACCOUNT_IDS` 集合 |
| `backend/bid-core/icg/infra/memory_repository.py` | 后端基础设施 | 在内置演示账号池中植入 `platform-admin`（平台运维管理员，角色 `platform_admin`，公司 `system`） |
| `backend/bid-core/icg/domain/session_navigation.py` | 后端会话模型 | 修正 `ROLE_NAVIGATION["platform_admin"]`，赋予其 `/jobs` 菜单与 `("jobs", "read")` 权限 |
| `frontend/web/src/app/useAppController.ts` | 前端应用控制器 | 修复 `handleRetryJob`，确保显式调用后端 `POST /api/v1/jobs/${encodeURIComponent(jobId)}/retry`，支持真实后端长任务从失败步骤重试 |
| `spec/openapi/demo-v1.json` | 契约基线 | 导出更新最新契约，通过 `export_openapi.py --check` 核验 100% 一致（0 契约漂移） |
| `tests/backend/test_app_routing_and_masked_jobs.py` | 专属联调测试 | 包含脱敏任务视图、平台管理员安全防线、长任务取消/重试 RBAC 权限矩阵、RFC 7807 统一错误体 4 组端到端测试 |

---

## 3. 契约打通与典型报文

### 3.1 平台管理员脱敏长任务查询
- **请求**：
  ```http
  GET /api/v1/jobs?masked=true HTTP/1.1
  Host: localhost:8000
  Authorization: Bearer <platform-admin-token>
  ```
- **响应**：`200 OK`
  ```json
  [
    {
      "id": "job-f1",
      "type": "chapter_generation",
      "status": "failed",
      "progress": 35,
      "company_id": "al***",
      "masked_company": "al***",
      "summary": "[任务] prj-*** 章节生成",
      "masked_summary": "[任务] prj-*** 章节生成",
      "is_masked": true,
      "duration_ms": 3500,
      "error_code": "MODEL_TIMEOUT",
      "allowed_actions": [],
      "allowedActions": [],
      "recoverable": false
    }
  ]
  ```
  *特点*：项目真实名称隐藏为 `prj-***`，公司 ID 脱敏为 `al***`，`allowed_actions` 为空数组（运维不可直接越权操作业务任务）。

### 3.2 越权重试拦截（编写人越权重试仅负责人可执行的任务）
- **请求**：
  ```http
  POST /api/v1/jobs/job-f1/retry HTTP/1.1
  Host: localhost:8000
  Authorization: Bearer <writer-token>
  ```
- **响应**：`403 Forbidden`（RFC 7807 统一错误体）
  ```json
  {
    "type": "https://api.icg.example.com/errors/PROJECT_LEAD_REQUIRED",
    "title": "Forbidden",
    "status": 403,
    "detail": "只有项目负责人或管理员可以重试失败任务",
    "instance": "/api/v1/jobs/job-f1/retry"
  }
  ```

### 3.3 跨租户嗅探探测拦截（平台管理员直调项目业务接口）
- **请求**：
  ```http
  GET /api/v1/projects/prj-alpha-001/workspace HTTP/1.1
  Host: localhost:8000
  Authorization: Bearer <platform-admin-token>
  ```
- **响应**：`404 Not Found`（RFC 7807 统一错误体）
  ```json
  {
    "type": "https://api.icg.example.com/errors/NOT_FOUND",
    "title": "Not Found",
    "status": 404,
    "detail": "项目不存在或无权访问",
    "instance": "/api/v1/projects/prj-alpha-001/workspace"
  }
  ```

---

## 4. 验收执行证据

### 4.1 专属全链路前后端联调测试通过
```powershell
pytest tests/backend/test_app_routing_and_masked_jobs.py -v
```
输出证据：
```
tests/backend/test_app_routing_and_masked_jobs.py::test_platform_admin_masked_jobs_view PASSED           [ 25%]
tests/backend/test_app_routing_and_masked_jobs.py::test_platform_admin_security_rbac_boundary PASSED     [ 50%]
tests/backend/test_app_routing_and_masked_jobs.py::test_long_task_retry_and_cancel_role_rbac_matrix PASSED [ 75%]
tests/backend/test_app_routing_and_masked_jobs.py::test_rfc7807_unified_error_format_compliance PASSED   [100%]
============================== 4 passed in 2.84s ==============================
```

### 4.2 任务中心与可恢复任务关联套件回归
```powershell
pytest tests/backend/test_recoverable_jobs.py tests/backend/test_task_center_glue.py
```
输出证据：
```
============================== 12 passed in 10.63s ==============================
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
ℹ tests 403, pass 403, fail 0, cancelled 0, skipped 0, todo 0
✔ test run finished (5.00s)
```

### 4.5 前端生产构建无警告
```powershell
pnpm --dir frontend/web build
```
输出证据：
```
vite v5.4.19 building for production...
✓ 45 modules transformed.
dist/index.html                   0.56 kB │ gzip:  0.34 kB
dist/assets/index-D_8f2uB1.css   33.72 kB │ gzip:  6.41 kB
dist/assets/index-CWV245vM.js   346.72 kB │ gzip: 88.75 kB
✓ built in 1.68s
```

### 4.6 工程治理脚本检查
```powershell
node scripts/check-project-governance.cjs
```
输出证据：
```
治理检查通过
```

---

## 5. 主 Agent 业务验收五条金标准对照

| 金标准 | 判定 | 对照说明与依据 |
|---|---|---|
| 1. 主路径推进 | **达成** | 实质性打通了长任务中心在前端控制器下的真实 HTTP 重试动作与平台运维脱敏长任务审计视角，补全了任务状态机全生命周期（启动 → SSE推流 → 取消 → 重试）闭环。 |
| 2. 安全与隔离底线 | **达成** | 平台管理员脱敏查询严格掩码企业 ID（`al***`）与项目 ID（`prj-***`），清空操作权限；直调业务接口严格返回 404 `NOT_FOUND` 防嗅探；写作者越权重试严格 403 `PROJECT_LEAD_REQUIRED` 拦截。 |
| 3. 关演示正式可用 | **达成** | 机制基于标准 RBAC 角色（`platform_admin`, `project_lead`, `writer`, `viewer`）与标准 `/api/v1` 端点构建，在非演示模式（`VITE_DEMO=0`）下使用真实 Access Token 会话完全正常运转。 |
| 4. 诚实记录阻断门禁 | **达成** | 针对未处于终态的长任务触发重试，系统如实拦截 409 `VERSION_CONFLICT`；对只读角色取消长任务拦截 403 `PROJECT_WRITER_REQUIRED`，所有边界门禁忠实执行。 |
| 5. 拒绝空壳冒充交付 | **达成** | 拒绝静态 mock 数据伪装；端到端打通 API 路由、领域层聚合脱敏、前端控制器调用，并配备包含真实 HTTP 会话的端到端自动化测试。 |

---

## 6. 局限性与后续推进

1. 当前平台管理员长任务列表支持通过 `/api/v1/jobs?masked=true` 及 `/api/v1/jobs/masked` 获取；前端平台运维界面已接入基础呈现，后续可进一步丰富平台级失败任务分类聚合图表；
2. 建议人类 PM 审核本卡后标为 `done`。
