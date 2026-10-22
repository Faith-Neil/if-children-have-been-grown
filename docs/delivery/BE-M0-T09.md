为什么有这个文件：记录 BE-M0-T09 旧 /api 统一错误体与幂等规范的实际交付事实、测试证据与变更清单。

它解决什么问题：作为质量门禁依据，证明旧接口错误格式统一、变动接口支持幂等回执与冲突保护、以及 E2E-D5 缺陷修复已完成，状态流转为 in-review。

# BE-M0-T09：旧 /api 统一错误体与幂等规范交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-M0-T09 |
| 代码解释 | [BE-M0-T09](../code/BE-M0-T09.md) |
| 验收 | 2026-10-22：旧 /api 错误响应格式完全统一为 {code, message, details, traceId}，traceId 与 X-Request-ID 一致；旧变动接口支持 Idempotency-Key 重放与冲突校验；E2E-D5 修复完成，/API 与 /Api/... 统一返回 JSON 404；本地自动化测试与治理检查全部通过 |
| 项目进度 | 任务看板是准绳。本卡从 planned 改为 in-review。看板状态保持 0 错误，严禁私自标 done，等待项目经理复审 |
<!-- task-delivery:end -->

## 关联与状态
- **关联 Issue**：[ISSUE-021](../../issues/ISSUE-021.md)、[ISSUE-006](../../issues/ISSUE-006.md)
- **关联任务**：[BE-M0-T09](../tasks/BE-M0.md#be-m0-t09)
- **状态流转**：从 `planned` 流转为 `in-review`。遵循协作规范，严禁私自将任务标为 `done` 或私自关闭 Issue，等待主 Agent / 项目经理进行复审验收。

## 完成内容与变更清单
1. **旧 /api 错误响应格式统一**：
   - 全局异常拦截器与 `error_response` 移除 `/api/v1/` 分支限制，对全量路由统一返回标准结构：
     `{"code": "...", "message": "...", "details": {}, "traceId": "..."}`。
   - 响应头一律返回 32 位十六进制 `X-Request-ID`，与内部 `traceId` 严格一致。
   - 废除已过期的 `{error: {code, message}, request_id}` 遗留响应。
2. **变动操作请求头幂等支持 (Idempotency-Key)**：
   - 旧变动路由（`POST /api/projects`、`POST /api/chapters/{id}/lock`、`lock/renew`、`lock/release`、`PUT /api/chapters/{id}/draft`、`DELETE /api/chapters/{id}/draft`、`POST /api/chapters/{id}/checks`、`POST /api/chapters/{id}/exports`）显式挂载 `Idempotency-Key` 请求头。
   - 支持 24 小时幂等缓存回执：同键同指纹安全返回首次成功数据并附带响应头 `Idempotent-Replayed: true`；同键不同指纹触发 409 `IDEMPOTENCY_CONFLICT` 且杜绝二次写入。未传头时向下兼容原有流程。
3. **大小写不敏感 SPA 兜底路由 (QA 200a105 E2E-D5 修复)**：
   - 修复前端兜底路由 `product_page` 对 API 前缀的判断逻辑，采用 `full_path.lower()` 统一判断 `api` 与 `api/`。
   - `/API`、`/Api/v1/...`、`/api/nonexistent` 统一返回 JSON 404，杜绝返回 SPA index.html 网页骨架。
4. **OpenAPI 规范与契约维护**：
   - 维护更新 `spec/openapi/demo-v1.json`，全量错误响应挂载 `V1Error` 引用及 `X-Request-ID` 头；保持 143 个冻结错误码及冻结草案不变；所有 operationId 维持标准 lowerCamelCase 且全局唯一。

## 变更文件清单
- `backend/bid-core/icg_demo/main.py`: 统一错误响应、挂载 Idempotency-Key 头、修复 E2E-D5 大小写不敏感 404。
- `backend/bid-core/icg_demo/errors.py`: 统一错误体描述、更新 OpenAPI 增强逻辑覆盖全量路由。
- `backend/bid-core/icg_demo/domain.py`: 注入统一幂等校验、指纹比对、缓存命中重放与回执保存。
- `spec/openapi/demo-v1.json`: 同步更新统一错误体引用与接口参数说明。
- `tests/backend/test_error_idempotency.py`: 增加全量错误体、大小写不敏感 404 与旧接口幂等重放自动化测试用例。
- `docs/code/BE-M0-T09.md`: 代码结构与实现细节说明。
- `docs/delivery/BE-M0-T09.md`: 本交付文档。

## 验收结果
- `pytest tests/backend/test_error_idempotency.py`: 12 个测试全部通过（100% Passed）。
- `pytest tests/backend/test_operation_ids.py`: 5 个测试全部通过（100% Passed）。
- `node scripts/check-project-governance.cjs`: 检查通过（0 错误）。

## 限制与未完成事项
- 遵循工作规范，本卡状态置为 `in-review`，绝不私自标记 `done`。
- ISSUE-021 保持跟进状态，待项目经理确认后关闭。
