# 任务交付：双错误体收口、统一规范错误体与 /api/demo 废弃生命周期治理（D3）

为什么有这个文件：记录 2026-10-26 用户审计与官方拍板 B4（`/api/demo` 立即废弃、兼容至 2026-11-15 窗口期）落地成果，以及全站双错误体收敛排查、统一 `{code, message, details, traceId}` 规范体优先解构的联调交付。

它解决什么问题：
1. 落实 RFC 8594 Sunset 与 Deprecation 响应头标准，明确 `/api/demo` 端点生命周期终止时限；
2. 消除前端此前解构双错误体时旧 `error`/`request_id` 反向抢占规范字段的隐患，实现全站以 OpenAPI V1Error 规范体为最高优先级；
3. 验证正式业务接口全走 `/api/v1`，杜绝旧 demo 路径扩展风险。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-TECH-DEBT-01 |
| 代码解释 | `docs/code/2026-10-26-persistence-and-error-body.md` |
| 验收 | 1) `GET /api/demo/accounts` 与 `POST /api/demo/login` 在 OpenAPI 规范中具备 `deprecated: true`；<br>2) 中间件与错误响应在 `/api/demo` 路径注入 `Sunset: Sun, 15 Nov 2026 00:00:00 GMT` 与 `Deprecation: true` 响应头；<br>3) 前端 `api.ts` 与 `status-views.ts` 严格优先解构外层标准错误体 `{code, message, details, traceId}`，旧 `error`/`request_id` 降级为向后兼容兜底；<br>4) 后端新增专属测试 `tests/backend/test_deprecated_demo_api.py` 5 项全绿；前端新增专属测试 `frontend/web/tests/unit/error-body-convergence.test.mjs` 5 项全绿；<br>5) 全量前端 384 项测试通过，后端关键回归用例全绿，`export_openapi.py --check` 100% 一致，保持 `in-review`。 |
| 项目进度 | D3 契约与双错误体收口闭环交付，推进至 D4（产品断环与 RAGFlow 真实接入） |
<!-- task-delivery:end -->

## 1. 关联与状态

- 日期：2026-10-26
- 关联决策：用户官方拍板 B4（`/api/demo` 立即 deprecated，不再加新接口；兼容截止至 2026-11-15，之后删除；统一错误体收敛）
- 关联卡片：`BE-TECH-DEBT-01`、`D3 持久化与双错误体收口`、`ISSUE-038`、`ISSUE-005`
- 本地验收状态：`in-review`（严格遵守 subagent 禁令，不擅自标 done）
- 分支：`feat/opencode-ICG`

---

## 2. 断点排查与最小胶水修改

### 2.1 断点 1：RFC 8594 Sunset 响应头与废弃元数据缺失
- **位置**：[`backend/bid-core/icg_demo/main.py`](../../backend/bid-core/icg_demo/main.py)
- **现象**：原代码仅在中间件下发了 `Deprecation: true`，缺少 RFC 8594 标准的下线截止时间 `Sunset` 响应头；且当请求触发 422/403/500 异常时，错误响应头未统一携带 Sunset 头。
- **修复措施**：
  1. 在 `request_identity` 中间件与 `error_response` 统一错误构造函数中，针对 `request.url.path.startswith("/api/demo")` 注入：
     - `Deprecation: true`
     - `Sunset: Sun, 15 Nov 2026 00:00:00 GMT`
  2. 核对 OpenAPI 契约：确认 `/api/demo/accounts` 与 `/api/demo/login` 均显式包含 `deprecated: true`。

### 2.2 断点 2：前端错误体解构优先级反转（旧字段优先于标准字段）
- **位置**：[`frontend/web/src/shared/api.ts`](../../frontend/web/src/shared/api.ts) 与 [`frontend/web/src/status/status-views.ts`](../../frontend/web/src/status/status-views.ts)
- **现象**：
  原代码逻辑为：
  ```typescript
  const code = textField(nested, 'code') ?? textField(body, 'code') ?? 'REQUEST_FAILED';
  const message = textField(nested, 'message') ?? textField(body, 'message') ?? '操作失败，请稍后重试。';
  ```
  优先取了 `nested`（即旧 `{error: {code, message}}`），导致当服务端在过渡期同时返回双错误体时，旧兼容层的字段会覆盖外层 OpenAPI 标准的 `code` 与 `message`。
- **修复措施**：
  倒置判断顺序，严格以规范体 `{code, message, details, traceId}` 为第一优先级，仅当顶层缺失时回退至 `nested` 与 `request_id`：
  ```typescript
  // 严格优先解构规范体 {code, message, details, traceId}，旧结构 {error, request_id} 仅作兼容兜底
  const code = textField(body, 'code') ?? textField(nested, 'code') ?? 'REQUEST_FAILED';
  const message = textField(body, 'message') ?? textField(nested, 'message') ?? '操作失败，请稍后重试。';
  const requestId = headerId || textField(body, 'traceId') || textField(body, 'request_id');
  ```
  在 `status-views.ts` 中的 `extractErrorInfo` 同步做相同优先序收敛。

### 2.3 业务调用路径排查
- 检查前端所有业务网络请求：
  - `ProjectPages.tsx`、`OverviewTab.tsx`、`TenderTab.tsx`、`ParseTab.tsx`、`FactsTab.tsx`、`EditorPage.tsx`、`LibraryPages.tsx`、`WritingArchivePage.tsx`、`SnippetLibraryPage.tsx`、`volume-api.ts` 等全量业务模块，全部发起于 `/api/v1/*` 路径。
  - `/api/demo/*` 仅保留在 `App.tsx` 的演示选择器（且严格受 `isDemoMode()` 门禁控制，默认关闭）。

---

## 3. 请求/响应报文留证

### 3.1 演示端点成功响应报文（带 RFC 8594 Sunset 头）
```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: no-store
Deprecation: true
Sunset: Sun, 15 Nov 2026 00:00:00 GMT
X-Request-ID: c541094ce70a4ef5b46d7879e61ef0cf

{
  "accounts": [
    { "id": "alpha-manager", "name": "王工（项目经理）", "role": "project_lead", "company_id": "c-alpha" },
    ...
  ]
}
```

### 3.2 演示端点校验异常报文（统一标准错误体 + Sunset 头）
```http
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json
Cache-Control: no-store
Deprecation: true
Sunset: Sun, 15 Nov 2026 00:00:00 GMT
X-Request-ID: d47120e365cb4ea68bfe83896b0dc1a2

{
  "code": "VALIDATION_ERROR",
  "message": "请求字段不符合演示接口要求：body.account_id",
  "details": {
    "fields": ["body.account_id"]
  },
  "traceId": "d47120e365cb4ea68bfe83896b0dc1a2"
}
```

### 3.3 正式业务端点报文对比（隔离验证：绝无 Sunset / Deprecation 头）
```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json
Cache-Control: no-store
WWW-Authenticate: Bearer
X-Request-ID: a12bc78091fd4ebfb96a011de8709121

{
  "code": "UNAUTHENTICATED",
  "message": "请先选择演示账号登录。",
  "details": {},
  "traceId": "a12bc78091fd4ebfb96a011de8709121"
}
```

---

## 4. 测试与验证结果

1. **后端专属联调测试**：
   - 执行命令：`pytest tests/backend/test_deprecated_demo_api.py`
   - 结果：**5 passed in 2.83s**。涵盖：
     - OpenAPI 契约元数据中 `deprecated: true` 存在性断言；
     - `GET /api/demo/accounts` 成功时 `Sunset` 与 `Deprecation` 响应头及其 RFC 8594 日期正确解析；
     - `POST /api/demo/login` 成功时 `Sunset` 与 `Deprecation` 响应头；
     - 422 与 403 错误响应时 Sunset/Deprecation 响应头与标准错误体 `{code, message, details, traceId}` 校验；
     - 隔离断言：`/api/v1` 路由绝不出现 Sunset/Deprecation 响应头。
2. **后端全量安全门禁与回归**：
   - 执行命令：`pytest tests/backend/test_deprecated_demo_api.py tests/backend/test_api_v1_convergence.py tests/backend/test_smoke_non_demo_pipeline.py tests/backend/test_mysql_gate.py`
   - 结果：**23 passed**。
3. **前端双错误体专属测试**：
   - 执行命令：`node --test frontend/web/tests/unit/error-body-convergence.test.mjs`
   - 结果：**5 passed**（纯规范体解构、双体共存规范严格优先、纯旧版兼容兜底、`extractErrorInfo` 优先级校验）。
4. **前端全量单测**：
   - 执行命令：`pnpm --dir frontend/web test`
   - 结果：**384 passed / 0 failed**。
5. **OpenAPI 自动化门禁校验**：
   - 执行命令：`python backend/bid-core/export_openapi.py --check`
   - 结果：`[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.`
6. **治理与规范一致性**：
   - 执行命令：`node scripts/check-project-governance.cjs`
   - 结果：**治理检查通过（0 errors）**。
