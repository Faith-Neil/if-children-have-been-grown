为什么有这个文件：记录检索层内存骨架这次实际跑过的检查和没有覆盖的范围。

它解决什么问题：避免把合成数据上的通过结果写成已经接通 MySQL 或向量库。

# 2026-10-12 证据候选验证

日期：2026-10-12。关联 [ISSUE-016](../../issues/ISSUE-016.md) / [AI-03](../tasks/AI-M0.md#ai-03)。业务库决定为 MySQL 8，本验证没有连接它。向量库仍未选定。

## 命令和结果

| 检查 | 命令与结果 |
|---|---|
| 证据候选契约 | `python3 -m pytest tests/backend/test_evidence_candidates.py -q`：7 passed，0.03 秒 |
| v1 模型失败体 | `python3 -m pytest tests/backend/test_openai_compatible_model.py::test_v1_generate_failure_returns_frozen_error_body tests/backend/test_evidence_candidates.py -q`：8 passed，1 warning，0.87 秒。其中失败体 1 项。假传输返回 HTTP 500，不调用真实端点 |
| 全后台 | `python3 -m pytest tests/backend -q`：309 passed，1 warning，89.51 秒。加入本条测试前、已含 `cba6282` 时为 308 passed，1 warning，87.64 秒 |
| 记录一致性 | `node scripts/check-project-governance.cjs`：通过。rebase 到 ISSUE-017、ISSUE-020 与 REV-M0-T07 之后为「治理检查通过：166 份 Markdown、352 项任务、18 项 Issue。」检查程序未修改，因此未重跑治理测试 |

全后台包含原有 `tests/backend/test_reference_boundaries.py`。该文件本轮没有修改。证据候选 7 项使用合成公司 `company-alpha` 与 `company-beta`。rebase 之后 `python3 -m pytest tests/backend --collect-only -q` 仍是 309 tests collected。`tests/backend/qa_error_idempotency_live_http.py` 不在这次收集里。

## 错误体旁路核对

`cba6282` 冻结的 `/api/v1` 错误体是 `{code, message, details, traceId}`，`MODEL_UNAVAILABLE` 对应 502，`traceId` 必须等于响应头 `X-Request-ID`。

用 `OpenAICompatibleModelProvider` 和假传输让上游返回 HTTP 500，再请求 `POST /api/v1/projects/{id}/generate`。结果是 502，字段只有这四项，`code` 为 `MODEL_UNAVAILABLE`，`message` 为「候选生成失败，正式正文没有修改。」，`details` 为 `{}`，`traceId` 与 `X-Request-ID` 相同且为 32 位十六进制。响应里没有旧的 `error` / `request_id`，也没有上游正文 `synthetic-upstream`。适配器被调用 1 次。

因此只在 `tests/backend/test_openai_compatible_model.py` 增加 `test_v1_generate_failure_returns_frozen_error_body`。不修改错误实现。ISSUE-016 没有新的 HTTP 错误码，所以没有改 `spec/openapi/demo-v1.json` 的码表。检索服务仍然不挂到 HTTP。

既有警告一条：Starlette 提示 `httpx` 与 `TestClient` 的搭配将要弃用。它在本次改动前已经存在，本轮没有为它增加依赖。

## 契约覆盖

- 路径 A 只返回本公司已确认且不是历史类型的资料，并可附着。
- 路径 B 把更接近查询的片段排在前面，并排除其他公司、未确认和其他类型。
- 路径 C 只返回本公司历史投标，`attachable` 为 false，`reference_only` 为 true。
- 搜索缺少公司时拒绝。同一 id 再次 upsert 会覆盖旧文本。
- 知识库关闭时只有路径 A，嵌入函数未被调用。
- 路径 B 失败时保留 A 和 C，原因是 `B failed: RuntimeError`，不含查询里的“机房”。
- 路径 C 的迭代失败时保留 A 和 B。

## 局限

没有连接 MySQL 8，没有调用嵌入模型、重排模型或向量库。服务没有挂到 HTTP，因此没有浏览器或接口验收。治理检查只核对记录是否一致，不证明检索可用。本地通过不是 PR 合入，也不是发布。
