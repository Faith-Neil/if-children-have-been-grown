为什么有这个文件：记录QA对AI-05（RAGFlow 检索客户端实现）的独立复验与签署结论。

它解决什么问题：不轻信自测汇报，独立复跑客户端单元测试与前后向联合回归，核查异常分类、零命中标记、网关前缀及密钥防泄露机制。

# AI-05 RAGFlow 检索客户端独立复验与 QA 签署（REV-M0-T38）

- 被验任务：[AI-05](../tasks/AI-M0.md#ai-05) · RAGFlow 检索客户端
- 关联 Issue：[ISSUE-037](../../issues/ISSUE-037.md)
- 关联交付：[AI-05 交付](../delivery/AI-05.md)、[代码解释](../code/AI-05.md)
- 被验核心文件：`backend/bid-core/icg_demo/ragflow_client.py`、`tests/backend/test_ragflow_client.py`
- 复验环境：Windows, Python 3.12.9; 未设 `ICG_RUN_REAL_RAGFLOW_TESTS`（离线安全运行）
- 结论：**通过 (PASS)**。**AI-05、ISSUE-037 均保持 in-review / in-progress，严禁标 done / closed**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 检索调用与解析 | 通过 | `test_success_retrieval_parses_chunks_and_records_request`：`POST {base_url}/api/v1/retrieval` 携带 `Authorization: Bearer <key>`，成功解析 `RagflowChunk` 列表及元数据 |
| AC-02 网关前缀与基址清洗 | 通过 | `test_base_url_trailing_slash_and_gateway_prefix`：`/gateway` 路径前缀完整保留，尾部斜杠自动去除，非法协议或带查询参数严格抛出 `ValueError` |
| AC-03 零命中显式标记跳过 | 通过 | `test_empty_chunks_is_marked_as_skipped`：官方 `code: 0` 且 chunks 为空时，返回 `skipped=True`、`skip_reason="zero hits"`，避免上层误判为有效空结果 |
| AC-04 业务非零错误码转异常 | 通过 | `test_business_error_raises_ragflow_business_error`：`code != 0` 显式转换为 `RagflowBusinessError`，携带原始 code 与 message |
| AC-05 HTTP 状态码异常分类 | 通过 | `test_http_500_raises_ragflow_http_error` 与 `test_http_error_codes_handled`：400/401/403/404/500/502/503 均精准转换为 `RagflowHttpError` |
| AC-06 超时与网络中断处理 | 通过 | `test_timeout_raises_ragflow_timeout_error` 与 `test_connection_error_raises_ragflow_connection_error`：分别精确转换为 `RagflowTimeoutError` 与 `RagflowConnectionError` |
| AC-07 响应畸变防护 | 通过 | `test_malformed_responses_raise_response_error`：覆盖非 JSON、非字典、缺失 code、缺失 data、chunks 非列表及 chunk 非字典等 6 种畸变场景，转为 `RagflowResponseError` |
| AC-08 健康检查端点规范 | 通过 | `test_health_check_succeeds_without_authorization` 与 `test_health_check_failures`：`GET /api/v1/system/healthz` 严格按照规范不带 Authorization 头，状态异常时抛错 |
| AC-09 可选参数与入参校验 | 通过 | `test_optional_rerank_id_omitted_when_none` 与 `test_input_validation`：`rerank_id` 为空时不入参，空 question 或空 dataset_ids 提前拦截 |
| AC-10 密钥隔离与防泄露 | 通过 | `test_api_key_never_leaked_in_exceptions`：模拟各类异常，全链路断言异常文本与 repr 中绝不包含真实 API Key |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| AI-05 客户端专项 | `python -m pytest tests/backend/test_ragflow_client.py -v -rs` | **25 passed, 1 skipped** (跳过真实端点探测) | 10.31s |
| RAGFlow 与证据联合回归 | `python -m pytest tests/backend/test_ragflow_client.py tests/backend/test_fake_ragflow.py tests/backend/test_evidence_candidates.py -v -rs` | **41 passed, 2 skipped** (联合回归全绿) | 14.67s |
| 治理一致性核查 | `node scripts/check-project-governance.cjs` | **检查通过** (344 份 Markdown、397 项任务、37 项 Issue) | 0.8s |

## 观察项与边界提示

1. **未改动运行时主链路**：`RagflowRetrievalClient` 为独立的客户端封装类，目前尚未挂载到 `retrieval.py` 或 `EvidenceCandidateService`，当前业务运行路径依然安全保留在内存模式。
2. **AI-06 接线要求明确**：后续在 AI-06 中将路径 B（公司知识库）与路径 C（历史投标库）改走该客户端时，须严格消费各公司保存的 `dataset_id`，且在遇到 `skipped=True` 或异常时，安全回退到路径 A。
3. **真实端点隔离有效**：`test_real_ragflow_retrieval_when_opted_in` 依旧被 `ICG_RUN_REAL_RAGFLOW_TESTS=1` 门禁隔离，离线 CI 纯洁性未被破坏。

## 签署状态

AI-05、ISSUE-037 均保持 **in-review / in-progress**，**严禁标 done / closed**。
