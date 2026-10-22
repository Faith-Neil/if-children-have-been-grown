为什么有这个文件：说明旧 /api 错误响应统一为 143 错误码契约规范，以及变动操作挂载 Idempotency-Key 幂等与页面兜底大小写不敏感路由的代码实现细节。

它解决什么问题：解决旧端点返回遗留格式 {error, request_id} 导致前端异常处理分化、旧端点重复提交无法安全重放、以及 QA 200a105 E2E-D5 报告的 /API 页面兜底未返回 JSON 404 的缺陷。

# BE-M0-T09：旧 /api 统一错误体与幂等规范代码说明

## 1. 业务上下文与改动背景
在系统早期演进中，`/api/v1` 确立了统一的错误响应体结构 `{code, message, details, traceId}`、`X-Request-ID` 追踪头及 24 小时 `Idempotency-Key` 幂等回执机制（BE-M0-T02、BE-M0-T03），而历史 `/api` 路径（如项目创建、章节锁定、草稿保存、合规检查、文档导出等）仍残留 `{error: {code, message}, request_id}` 格式，且写操作缺少请求头幂等支持。此外，QA 在 `200a105` 签署的 E2E-D5 明确指出：SPA 兜底路由仅排查了精确小写的 `api`，导致 `/API` 或 `/Api/v1/...` 命中前端 HTML 页面壳而非 JSON 404。

本任务（关联 ISSUE-021、ISSUE-006）在不删除旧端点、不破坏既有前端兼容性的前提下，实现全系统全链路统一规范。

## 2. 核心代码变更与入口

### 2.1 统一错误响应体与全局异常处理
- **代码文件**：`backend/bid-core/icg_demo/main.py`、`backend/bid-core/icg_demo/errors.py`
- **实现细节**：
  - `error_response(request, status, code, message, details)` 移除对 `/api/v1/` 路径前缀的条件判断，所有 HTTP 4xx/5xx 与 DomainError 统一生成结构体：
    ```json
    {
      "code": "...",
      "message": "...",
      "details": {},
      "traceId": "..."
    }
    ```
  - 响应头一律返回 `X-Request-ID: <traceId>`，与错误体内部 `traceId` 保持 1:1 严格对齐。
  - `error_responses(*statuses)` 统一使用 `V1Error` 响应模型。
  - `errors.py` 的 `enrich_openapi` 函数遍历全量路径与操作，将所有 `ErrorResponse` 引用重定向到 `#/components/schemas/V1Error`，并将全局 143 个冻结错误码写入 OpenAPI 规范。

### 2.2 变动操作请求头幂等支持 (Idempotency-Key)
- **代码文件**：`backend/bid-core/icg_demo/main.py`、`backend/bid-core/icg_demo/domain.py`
- **支持端点**：
  - `POST /api/projects`
  - `POST /api/chapters/{chapter_id}/lock`
  - `POST /api/chapters/{chapter_id}/lock/renew`
  - `POST /api/chapters/{chapter_id}/lock/release`
  - `PUT /api/chapters/{chapter_id}/draft`
  - `DELETE /api/chapters/{chapter_id}/draft`
  - `POST /api/chapters/{chapter_id}/checks`
  - `POST /api/chapters/{chapter_id}/exports`
- **处理流程**：
  1. 端点声明 `idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None`，在 OpenAPI 中标注 `Idempotency-Key` 头参数并声明响应头 `Idempotent-Replayed`。
  2. 若客户端传入该请求头，先经 `validate_key` 格式校验（8~120 字符 ASCII）。未传入时向下兼容正常执行业务。
  3. 通过 `fingerprint(action, payload, if_match)` 计算请求指纹。
  4. 事务开始前通过 `lookup(state, scope_id, user_id, key, fingerprint, now)` 检索回执缓存：
     - 若命中同键同指纹，直接返回首次执行成功的缓存结果，并由中间件/视图标记 `Idempotent-Replayed: true`；
     - 若命中同键不同指纹，抛出 409 `IDEMPOTENCY_CONFLICT`，且不执行任何数据库或状态写入；
     - 若未命中，执行实际业务逻辑，并在成功完成后调用 `remember(...)` 写入回执缓存（TTL 为 24 小时）。失败操作绝不登记回执。

### 2.3 大小写不敏感 SPA 兜底路由 (E2E-D5 修复)
- **代码文件**：`backend/bid-core/icg_demo/main.py` -> `product_page`
- **实现细节**：
  ```python
  normalized = full_path.lower()
  if (".." in full_path.split("/")
          or normalized == "api"
          or normalized.startswith("api/")
          or full_path.startswith(("static/", "assets/"))):
      raise HTTPException(status_code=404)
  ```
  对路径进行规范化小写转换后判断 `api` 或 `api/` 前缀。无论客户端请求 `/API`、`/Api/v1/session` 还是 `/api/v1/projects`，若未匹配到路由，统一抛出 404 HTTPException，由全局异常处理器拦截并返回 JSON 错误体，杜绝返回 SPA index.html 网页骨架。

## 3. OpenAPI 规范同步
- **规范文件**：`spec/openapi/demo-v1.json`
- **契约一致性**：同步最新的接口定义与错误模型，维持 143 个冻结错误码、81 个 lowerCamelCase 全局唯一 operationId，保留冻结草案与重试指引说明（`WRITES_WITHOUT_IDEMPOTENCY_KEY`）。

## 4. 自动化测试覆盖
- `tests/backend/test_error_idempotency.py`:
  - `test_v1_error_body_matches_request_header_and_legacy_shape_stays`: 断言 `/api/projects` 等旧接口错误体统一为 `{"code", "message", "details", "traceId"}`。
  - `test_case_insensitive_api_prefix_returns_json_404`: 验证 `/API`、`/Api/v1/session` 等返回 JSON 404 及标准 `NOT_FOUND` 错误体。
  - `test_legacy_endpoints_support_idempotency_key_replay`: 覆盖项目、章节锁、续期、释放、草稿保存与丢弃的全流程同键同指纹重放与冲突断言。
- `tests/backend/test_operation_ids.py`: 验证契约规范与运行中服务 100% 对齐。
