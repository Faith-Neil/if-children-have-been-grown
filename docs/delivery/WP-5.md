为什么有这个文件：记录质量整改路线图 WP-5（API 接口收敛、/api/demo 弃用、统一错误体与生产演示账号禁用门禁）的实际完成内容、测试验收与规范落实说明。

它解决什么问题：收敛前后端 API 路由至 /api/v1 标准路径，弃用历史 /api/demo 端点并增加 Deprecation: true 响应头，统一所有错误响应格式为 {code, message, details, traceId}，并在生产配置下阻断内置演示账号登录。

# WP-5：API 接口收敛与错误体规范化交付
> **历史快照（DOC-SYNC-1）：** 本文记录整改当时目标与验收；**现行**仓库结构与入口约定见 `docs/architecture/repository-layout.md` 与 `AGENTS.md`。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | WP-5 |
| 代码解释 | 将 /api/demo/accounts 与 /api/demo/login 标记为 deprecated 并通过中间件注入 Deprecation: true 响应头；同步更新 OpenAPI 契约；将前端 App.tsx 获取项目列表切换至 /api/v1/projects；内置合成账号标记 _DEMO_ONLY 并在生产配置（ICG_ALLOW_DEMO_LOGIN=0 / ICG_ENV=production）下阻断登录（403 FORBIDDEN）；详见本交付第 2、3 节。 |
| 验收 | 新增专项测试 tests/backend/test_api_v1_convergence.py 4 项全绿；OpenAPI 契约一致性测试与 demo 测试全绿（47 passed）；前端权威测试 344 项全绿；生产构建（tsc + vite build）通过（932ms，0 错误）；工程治理检查 486 份 Markdown 0 错误。 |
| 项目进度 | WP-5 顺利闭环；下一阶段进入 WP-6（去演示身份 + 八角色前端收口）。 |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-22
- 分支与提交：`feat/opencode-ICG`
- 关联规划：`docs/delivery/2026-10-22-quality-remediation-plan.md`（阶段 D 后半 / WP-5）
- 关联规则：`AGENTS.md`（质量整改与结构冻结规则 - API 接口收敛）
- 本地验收状态：已通过（后端 47 项收敛/测试全绿；前端 344 passed；构建绿灯；治理脚本通过）
- 合入 / 发布状态：分支持续演进，与远程保持同步

---

## 完成内容与变更文件

### 1. 后端路由与错误体治理

1. **`/api/demo/*` 废弃标记与响应头**：
   - 在 [`backend/bid-core/icg_demo/main.py`](file:///backend/bid-core/icg_demo/main.py) 中，将 `/api/demo/accounts` 和 `/api/demo/login` 路由装饰器显式添加 `deprecated=True`。
   - 在全局 HTTP 中间件 `request_identity` 和 `error_response` 中，针对所有 `/api/demo` 请求注入 `Deprecation: true` 响应头，向下兼容的同时明确告知调用方接口已弃用。
   - 同步在 [`spec/openapi/demo-v1.json`](file:///spec/openapi/demo-v1.json) 中为对应端点添加 `"deprecated": true`，保持契约校验严格通过。
2. **统一错误响应体格式**：
   - 所有异常与错误统一标准化为：`{"code": code, "message": message, "details": details or {}, "traceId": request_id}`。
   - 响应头统一注入 `X-Request-ID: <traceId>` 与 `Cache-Control: no-store`。
3. **演示账号隔离与生产门禁**：
   - 在 [`backend/bid-core/icg_demo/domain.py`](file:///backend/bid-core/icg_demo/domain.py) 中定义 `DEMO_ONLY_ACCOUNT_IDS` 集合，并在 `Account` 实体标注 `_DEMO_ONLY: bool = False`。
   - 在 `seed_state()`（[`backend/bid-core/icg/infra/memory_repository.py`](file:///backend/bid-core/icg/infra/memory_repository.py)）中为全部内置合成账号明确标注 `_DEMO_ONLY=True`。
   - 在 `DemoService.login` 中增加生产门禁：当 `ICG_ALLOW_DEMO_LOGIN=0`、`DEMO_ACCOUNTS_ENABLED=0` 或 `ICG_ENV=production` 时，严格抛出 `DomainError(403, "FORBIDDEN", "生产配置下禁用内置演示账号登录。")`，彻底杜绝生产环境未授权混用演示账号风险。

### 2. 前端请求与客户端对齐

1. **API 调用切换至 `/api/v1`**：
   - 在 [`frontend/web/src/app/App.tsx`](file:///frontend/web/src/app/App.tsx) 中，将项目列表读取从旧 `/api/projects` 平滑切换为 `/api/v1/projects`。
2. **错误解析与追踪号兼容**：
   - [`frontend/web/src/shared/api.ts`](file:///frontend/web/src/shared/api.ts) 中继续保持以 `traceId` 为权威来源，兼容回退至 `request_id`，统一包装为 `ApiError` 并向用户提供可排错追踪号提示。

---

## 验收结果

1. **后端收敛专项与契约测试**：
   - 命令：`pytest tests/backend/test_api_v1_convergence.py tests/backend/test_error_idempotency.py tests/backend/test_demo.py`
   - 结果：**47 passed in 20.85s**，包含：
     - `/api/demo/*` 响应头 `Deprecation: true` 校验通过；
     - 生产配置（`ICG_ALLOW_DEMO_LOGIN=0` / `ICG_ENV=production`）阻断演示登录校验通过；
     - OpenAPI 契约冻结校验通过；
     - 统一错误体格式 `{code, message, details, traceId}` 校验通过。
2. **前端权威测试与构建**：
   - 命令：`pnpm --dir frontend/web test` -> **344 passed, 0 failed**。
   - 命令：`pnpm --dir frontend/web build` -> **构建耗时 932ms，0 错误**。
3. **工程治理检查**：
   - 命令：`node scripts/check-project-governance.cjs`
   - 结果：**486 份 Markdown、399 项任务、37 项 Issue 100% 校验通过**。
