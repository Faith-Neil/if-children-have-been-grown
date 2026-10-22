为什么有这个文件：记录模型配置存储与 API（ISSUE-024）的实际交付内容、测试证据与验收结论。

它解决什么问题：汇总代码改动、自动化测试证据、OpenAPI 契约同步与状态标记，供主 Agent 和 QA 团队复核。

# ISSUE-024：模型配置存储与 API 交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| Issue ID | ISSUE-024 |
| 代码解释 | [ISSUE-024 代码解释](../code/ISSUE-024.md) |
| 验收条目 | AC-01～AC-03 全部达成并通过自动化测试 |
| 测试结果 | 后端 pytest 全量回归 451 passed, 16 skipped, 0 failed（针对本 Issue 新增 12 项测试全部通过） |
| 当前状态 | in-review（待 QA / 主 Agent 复核，不私自标 done） |
<!-- task-delivery:end -->

## 1. 交付目标达成情况

| 验收编号 | 验收条目要求 | 交付情况与证据 |
|---|---|---|
| AC-01 | 密钥以 Fernet 加密，主密钥只来自 `ICG_SECRET_KEY`。响应只有 `api_key_masked` 与 `has_api_key`。省略为保留，空字符串为清除，送回掩码为不修改 | 已完成。通过 `test_fernet_encryption_and_decryption`、`test_api_key_masking`、`test_api_response_masks_keys_and_never_returns_plaintext`、`test_update_rules_omit_clear_and_mask` 严格验证 |
| AC-02 | `POST /api/v1/model-configs/{id}/test` 返回 `ok`、`provider`、`model`、`duration_ms`。任务开始时保存配置快照，含 `stream_enabled` 与 `json_mode_enabled`。二者随 `revision` 做乐观锁 | 已完成。通过 `test_connectivity_api`、`test_job_start_snapshots_stream_and_json_mode_enabled`、`test_optimistic_locking_via_if_match_and_revision` 严格验证 |
| AC-03 | 403 与 503 两码进入运行时冻结表。503 的响应没有 `Retry-After`，客户端不自动重试 | 已完成。503 `SECRET_KEY_UNAVAILABLE` 经断言绝对不含 `Retry-After`；敏感项目门禁触发 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`。通过 `test_secret_key_unavailable_503_has_no_retry_after` 与 `test_sensitive_project_requires_local_model` 严格验证 |

## 2. 变更文件清单

- **实现文件**：
  - `backend/bid-core/icg_demo/model_config_storage.py`：新增模型配置数据类、Fernet 加解密、掩码转换、乐观锁校验与 FastAPI 路由挂载。
  - `backend/bid-core/icg_demo/domain.py`：在 `DemoState` 增加 `model_configs` 与 `project_model_configs`。
  - `backend/bid-core/icg_demo/database.py`：在 MySQL 仓库中增加模型配置的持久化与读取降级。
  - `backend/bid-core/icg_demo/recoverable_jobs.py`：可恢复任务启动时保存包含 `stream_enabled` 和 `json_mode_enabled` 的模型快照，并接入敏感项目策略门禁。
  - `backend/bid-core/icg_demo/main.py`：挂载模型配置路由。
  - `backend/bid-core/alembic/versions/0005_model_config.py`：新增 MySQL `demo_model_config` 和 `demo_project_model_config` 表迁移脚本。
- **契约与文档**：
  - `spec/openapi/demo-v1.json`：同步新增的 4 个模型配置路径与 7 个模型 Schema，保留全部已有冻结草案，契约比对测试 100% 通过。
  - `docs/code/ISSUE-024.md`：详细代码入口与设计解释。
  - `docs/delivery/ISSUE-024.md`：本交付文档。
  - `issues/ISSUE-024.md`：更新状态至 `in-review` 并补充验收记录。
- **自动化测试**：
  - `tests/backend/test_model_config_storage.py`：覆盖加密、掩码、乐观锁、无 Retry-After、敏感门禁、连通性测试与快照共 12 项测试。

## 3. 自动化测试执行结果

```text
============================= test session starts =============================
platform win32 -- Python 3.12.9, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\徐佳馨\if-children-have-been-grown
configfile: pytest.ini
plugins: anyio-4.14.2
collected 467 items

tests\backend\test_model_config_storage.py ............                  [ 44%]
...
tests\backend\test_operation_ids.py .....                                [ 57%]
tests\backend\test_recoverable_jobs.py .....                             [ 75%]
...
====================== 451 passed, 16 skipped in 272.05s =======================
```

## 4. 边界与限制说明

1. 本任务严格保持了未设置 `ICG_DATABASE_URL` 时平滑降级至内存仓库，本地运行无需强制依赖外部 MySQL 服务。
2. 503 `SECRET_KEY_UNAVAILABLE` 响应体符合 V1Error 规范，服务端未设置 `Retry-After` 响应头，与 `MODEL_UNAVAILABLE` 保持一致的非瞬时故障策略。
3. 遵循开发规范，绝不私自将任务看板与 Issue 标为 `done` 或 `closed`，本卡状态标至 `in-review`。
