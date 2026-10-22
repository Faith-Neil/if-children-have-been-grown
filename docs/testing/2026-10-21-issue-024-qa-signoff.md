为什么有这个文件：记录QA对ISSUE-024（模型配置存储、Fernet对称加密、掩码保护、乐观锁与敏感门禁）的独立复验与签署结论。

它解决什么问题：不轻信自报结果，亲手独立执行专项自动化测试、核验 Fernet 对称加密、无主密钥时 503 且绝无 Retry-After、API Key 掩码与更新四态语义、If-Match revision 乐观锁并发保护、敏感项目本地模型门禁 403，以及 OpenAPI 规范 7 个端点规范性与 143 个错误码完整性。

# ISSUE-024 模型配置存储与 API 独立复验与 QA 签署（REV-M0-T43）

- 被验任务：[ISSUE-024](../../issues/ISSUE-024.md) · 模型配置存储与 API 实现
- 关联架构设计：[模型服务与配置架构](../../docs/architecture/model-config-provider.md)（ISSUE-010 / ISSUE-028）
- 关联交付：[ISSUE-024 交付](../delivery/ISSUE-024.md)、[代码解释](../code/ISSUE-024.md)
- 被验核心文件：`backend/bid-core/icg_demo/model_config_storage.py`、`backend/bid-core/alembic/versions/0005_model_config.py`、`spec/openapi/demo-v1.json`、`tests/backend/test_model_config_storage.py`
- 复验环境：Windows, Python 3.12.9
- 结论：**通过 (PASS)**。**ISSUE-024 保持 in-review / in-progress，严禁标 done / closed**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 Fernet 密钥加解密隔离 | 通过 | `test_fernet_encryption_and_decryption`：明文存储前经 Fernet 对称加密，密文以 `gAAAAA` 开头，密文与明文严格隔离；仅在必要解密时恢复 |
| AC-02 主密钥缺失 503 且无 Retry-After | 通过 | `test_secret_key_unavailable_when_env_unset` 与 `test_secret_key_unavailable_503_has_no_retry_after`：未设置 `ICG_SECRET_KEY` 环境变量时，保存/连通测试均严格抛出 503 `SECRET_KEY_UNAVAILABLE`，断言响应头绝无 `Retry-After`，杜绝客户端无意义重试 |
| AC-03 API Key 掩码与明文绝不出库 | 通过 | `test_api_key_masking` 与 `test_api_response_masks_keys_and_never_returns_plaintext`：`mask_api_key` 保留前 3 后 4（短密钥全打码）；GET 与 POST 响应绝不包含 `api_key` 明文字段，只暴露 `has_api_key: true` 与 `api_key_masked: "sk-***cdef"` |
| AC-04 更新规则四态语义 | 通过 | `test_update_rules_omit_clear_and_mask`：① 请求体省略 `api_key` 保留原密钥；② 传回掩码（如 `sk-***3456`）代表不修改保留原密钥；③ 传入空字符串 `""` 代表清除密钥；④ 传入新明文正常更新并重新加密 |
| AC-05 If-Match revision 乐观锁并发保护 | 通过 | `test_optimistic_locking_via_if_match_and_revision`：PUT 请求缺少 `If-Match` 拦截 428 `IF_MATCH_REQUIRED`；版本不一致拦截 409 `REVISION_CONFLICT`（附带 `current_revision`）；版本匹配成功递增 revision；旧 revision 重放严格冲突 |
| AC-06 敏感项目本地模型门禁 403 | 通过 | `test_sensitive_project_requires_local_model`：标记为敏感项目（`sensitive=true`）后，尝试绑定云端公网模型或未标记 `allow_sensitive=true` 的本地模型，严格返回 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL` |
| AC-07 连通性测试接口与错误兜底 | 通过 | `test_connectivity_api` 与 `test_connectivity_fails_with_503_without_retry_after_when_secret_key_lost`：`POST /api/v1/model-configs/{id}/test` 正常返回耗时与连通状态；无法连通返回 `ok: false`；密钥丢失返回 503 无 Retry-After |
| AC-08 生成长任务快照流式与 JSON 开关 | 通过 | `test_job_start_snapshots_stream_and_json_mode_enabled`：可恢复任务启动时完整快照模型配置的 `stream_enabled` 与 `json_mode_enabled` 标志位 |
| AC-09 多租户公司隔离 | 通过 | `test_company_multi_tenant_isolation`：跨公司模型配置列表与获取严格隔离，跨公司访问返回 404 `MODEL_CONFIG_NOT_FOUND` |

## OpenAPI 规范与错误码核对

| 检查项 | 实测结果 | 证据与详细说明 |
|---|---|---|
| 新增 7 个端点规范性 | **7 个端点全部合规** | 涵盖 `GET /api/v1/model-configs` (`listModelConfigs`), `POST /api/v1/model-configs` (`createModelConfig`), `GET /api/v1/model-configs/{id}` (`getModelConfig`), `PUT /api/v1/model-configs/{id}` (`updateModelConfig`), `POST /api/v1/model-configs/{id}/test` (`testModelConfig`), `POST /api/v1/projects/{project_id}/model-config` (`bindProjectModelConfig`), `GET /api/v1/projects/{project_id}/model-config` (`getProjectModelConfig`)，全部遵循 lowerCamelCase |
| 143 个冻结错误码完整性 | **143 个枚举全部匹配** | `tests/backend/test_error_idempotency.py` 9 passed；`SECRET_KEY_UNAVAILABLE`、`SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`、`REVISION_CONFLICT`、`IF_MATCH_REQUIRED` 等核心错误码均在既有契约枚举内复用 |
| 全局 operationId 校验 | **5 passed** | `tests/backend/test_operation_ids.py` 全部通过，全量契约与运行态契约严格全等，无 `_api_` 冗余前缀 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| ISSUE-024 专项测试 | `python -m pytest tests/backend/test_model_config_storage.py -v -rs` | **12 passed** | 9.73s |
| 契约错误码与幂等测试 | `python -m pytest tests/backend/test_error_idempotency.py -v -rs` | **9 passed** (143 个冻结错误码全绿) | 5.38s |
| 全局 operationId 契约测试 | `python -m pytest tests/backend/test_operation_ids.py -v -rs` | **5 passed** | 3.47s |
| 治理一致性核查 | `node scripts/check-project-governance.cjs` | **检查通过** (359 份 Markdown、397 项任务、37 项 Issue) | 0.8s |

## 观察项与边界提示

1. **Alembic 迁移支持**：`0005_model_config.py` 迁移脚本结构规范，包含了对 SQLite / MySQL 的 `server_default` 兼容与 `op.batch_alter_table` 安全降级。
2. **机密零明文出境**：无论接口发生何种异常、回显或日志打印，解密后的明文只在内存网络请求阶段瞬间存在，响应 JSON 中绝对不包含 `api_key` 明文。
3. **503 错误重试防范**：`SECRET_KEY_UNAVAILABLE` 属于服务端运维配置缺失故障，非临时网络抖动，不输出 `Retry-After` 头，有效避免前端请求层无意义死循环重试。

## 签署状态

ISSUE-024 保持 **in-review / in-progress**，**严禁标 done / closed**。
