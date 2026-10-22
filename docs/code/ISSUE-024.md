为什么有这个文件：说明模型配置存储、Fernet 密钥加密、掩码与 API 接口的代码设计与实现细节。

它解决什么问题：详细记录模型配置的代码入口、数据流、加密掩码策略、乐观锁并发控制与两枚冻结错误码的行为边界。

# ISSUE-024：模型配置存储与 API 代码说明

- 对应 Issue：[ISSUE-024](../../issues/ISSUE-024.md)
- 交付文档：[ISSUE-024 交付](../delivery/ISSUE-024.md)
- 实现日期：2026-10-21
- 核心代码路径：
  - `backend/bid-core/icg_demo/model_config_storage.py`
  - `backend/bid-core/icg_demo/domain.py`
  - `backend/bid-core/icg_demo/database.py`
  - `backend/bid-core/icg_demo/recoverable_jobs.py`
  - `backend/bid-core/icg_demo/main.py`
  - `backend/bid-core/alembic/versions/0005_model_config.py`
  - `tests/backend/test_model_config_storage.py`

## 1. 代码入口与核心结构

1. **配置存储与业务服务 (`model_config_storage.py`)**：
   - 数据实体 `ModelConfig`：包含 `id`、`company_id`、`name`、`provider`、`base_url`、`model`、`encrypted_api_key`、`api_key_masked`、`is_local`、`allow_sensitive`、`stream_enabled`（默认 `True`）、`json_mode_enabled`（默认 `False`）、`revision`（乐观锁版本号）、`timeout_seconds`、`max_tokens`。
   - `ModelConfigService`：提供多租户隔离的增、删、改、查、连通性测试与项目绑定逻辑。
   - 路由挂载 `include_model_config_routes`：将 4 条配置路径及 2 条项目绑定路径注入 FastAPI 应用（所有 `operation_id` 均为规范 lowerCamelCase）。

2. **状态与持久化支持 (`domain.py` & `database.py`)**：
   - 在 `DemoState` 中新增 `model_configs: dict[str, Any]` 与 `project_model_configs: dict[str, str]`。未设置数据库连接串时使用 `MemoryRepository` 保证平滑降级与快速回归。
   - 在 `database.py` 的 `MysqlConnectionRepository` 中扩展 `_load_shared` 与 `_save_model_configs`，并在 `alembic/versions/0005_model_config.py` 登记 `demo_model_config` 和 `demo_project_model_config` 两张表的迁移。

3. **任务启动快照 (`recoverable_jobs.py`)**：
   - 在 `start` 创建任务时，通过 `state.project_model_configs` 查找项目绑定的模型配置（若未绑定则读取公司默认配置），将 `stream_enabled` 与 `json_mode_enabled` 记入 `model_snapshot`。
   - 保证任务创建后的生命周期内固定使用该快照，后续默认配置的修改不影响已进入队列和运行中的任务。

## 2. 密钥安全与掩码保护机制

1. **主密钥严格从环境变量读取**：
   - 加密与解密采用 `cryptography.fernet.Fernet`，密钥严格来自环境变量 `ICG_SECRET_KEY`。代码中绝不硬编码密钥，主密钥不进代码库与日志。
   - 当环境变量 `ICG_SECRET_KEY` 未配置或为空时，任何尝试保存新密钥或解密现有密钥的操作均抛出 `DomainError(503, "SECRET_KEY_UNAVAILABLE", ...)`。
   - 严格保证该 503 响应不携带 `Retry-After` 请求头，客户端不得自动重试。

2. **响应掩码与安全更新语义**：
   - 所有对外 API 响应（`ModelConfigResponse`）均过滤明文密钥与加密串，只返回 `has_api_key: bool` 与 `api_key_masked: str | None`（长度 > 8 显示前 3 后 4，其余为 `***`）。
   - 更新时的四项语义严格落地：
     - **省略字段（None）**：保留原密钥与掩码不改动；
     - **空字符串（""）**：清除现有密钥，`encrypted_api_key` 与 `api_key_masked` 置为 `None`，`has_api_key` 为 `False`；
     - **送回掩码**：检测到输入等于现有 `api_key_masked` 时视为不修改，不重新加密；
     - **新明文密钥**：使用 Fernet 加密后存储密文，并刷新掩码。

## 3. 乐观锁并发保护

1. **If-Match 与 revision 联动**：
   - 修改配置接口（`PUT /api/v1/model-configs/{id}`）强制校验 `If-Match` 请求头。
   - 缺少 `If-Match` 抛出 428 `IF_MATCH_REQUIRED`。
   - 传入版本与当前 `cfg.revision` 不一致时抛出 409 `REVISION_CONFLICT`，并在 `details` 中回传 `current_revision`。
   - 校验通过后递增 `revision`，并在响应头 `ETag` 回传新版本号。并发保护范围完整覆盖包括 `stream_enabled` 和 `json_mode_enabled` 在内的全部配置字段。

## 4. 敏感项目门禁与连通性测试

1. **敏感项目本地模型门禁 (403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`)**：
   - 当项目标记为敏感 (`project.sensitive == True`) 时，尝试绑定非本地模型 (`is_local == False`) 或未勾选敏感可用 (`allow_sensitive == False`) 的配置，或尝试以此类配置启动任务时，均被策略门禁拦截，返回 HTTP 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`。
   - 非敏感项目使用云端模型不受影响；敏感项目使用合规本地模型不受影响。

2. **连通性测试 API (`POST /api/v1/model-configs/{id}/test`)**：
   - 尝试解密密钥（若密钥存在但 `ICG_SECRET_KEY` 缺失则触发 503）。
   - 针对 `provider == "demo"` 返回即时模拟测试结果。
   - 针对 `openai-compatible` 发送测试探测（或对接测试夹具 `FakeOpenAIChat`），捕获异常与响应状态，返回 `ok: bool`、`provider: str`、`model: str` 与 `duration_ms: int`。

## 5. 多租户隔离

- 所有配置读写均依据当前鉴权用户所在的 `company_id` 过滤。试图通过 ID 访问或更新其他公司的配置均返回 404 `NOT_FOUND`，杜绝跨租户越权。
