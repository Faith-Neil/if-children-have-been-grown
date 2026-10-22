为什么有这个文件：记录配置驱动的对话模型运行时接入（ISSUE-028）的交付内容、测试证据与验收结论。

它解决什么问题：汇总代码变更、自动化测试覆盖证据、AC-01～AC-04 条件达成状态，供主 Agent 与 QA 团队复核。

# ISSUE-028：配置驱动的对话模型运行时接入交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| Issue ID | ISSUE-028 |
| 代码解释 | [ISSUE-028 代码解释](../code/ISSUE-028.md) |
| 关联任务 | [AI-01](../tasks/AI-M0.md#ai-01) |
| 验收条目 | AC-01～AC-04 全部达成并通过自动化测试 |
| 测试结果 | 针对本 Issue 的专属测试集 `tests/backend/test_model_config_provider.py` 11 passed, 1 skipped；全量相关回归测试 90 passed, 2 skipped (0 failed) |
| 当前状态 | in-review（待 QA / 主 Agent 复核，不私自标 done，不私自关闭 Issue） |
<!-- task-delivery:end -->

## 1. 交付目标达成情况

| 验收编号 | 验收条目要求 | 交付情况与证据 |
|---|---|---|
| AC-01 | Provider 读取配置、启动快照、local/cloud 路由、敏感约束、流式/JSON、错误映射和 `job.model_call` 已写明并实现 | 已完成。`provider_from_model_config` 动态解析配置与流式/JSON 参数；`start` 阶段抓取完整快照；执行时基于快照还原；上游 500 映射为 502 `MODEL_UNAVAILABLE` 并触发 `job.model_call` 事件。详见 `test_provider_from_model_config_openai_compatible_parameters` 与 `test_recoverable_job_advances_with_model_snapshot` |
| AC-02 | CI 使用记录请求头和基址的假服务；真实连接默认跳过 | 已完成。测试套件使用 `FakeOpenAIChat` 模拟真实端点并捕获全部调用请求体与头信息；`test_real_model_probe_skipped_by_default` 默认跳过，仅在 `ICG_RUN_REAL_MODEL_TESTS=1` 时执行 |
| AC-03 | 不改 OpenAPI 文件，不新增依赖 | 已完成。本功能纯运行时逻辑适配与内部异常码映射，不改动已有公开 OpenAPI 规范，未引入任何第三方新依赖 |
| AC-04 | 敏感项目使用非本地模型返回 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`（由 409 改为 403） | 已完成。`require_allowed_model` 严格落地：敏感项目配置为 `is_local=False` 或 `allow_sensitive=False` 时，章节建议接口与生成作业启动接口在调用模型前均阻断并抛出 HTTP 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`。通过 `test_sensitive_project_blocks_cloud_model_with_403_ac04` 与 `test_sensitive_project_allows_local_model` 严格验证 |

## 2. 变更文件清单

- **核心实现代码**：
  - `backend/bid-core/icg_demo/openai_model.py`：扩展 `stream_enabled`、`json_mode_enabled` 与 API Key 组装，支持 SSE 事件流聚合解析。
  - `backend/bid-core/icg_demo/model_config_storage.py`：实现 `provider_from_model_config` 与 `provider_from_model_snapshot`，完善默认配置自动初始化更新。
  - `backend/bid-core/icg_demo/domain.py`：实现 `resolve_model_provider`、`resolve_provider_from_snapshot` 与 AC-04 核心安全门禁 `require_allowed_model`（403 阻断）。
  - `backend/bid-core/icg_demo/workflow.py`：生成流程按项目动态获取 provider 并应用安全门禁。
  - `backend/bid-core/icg_demo/recoverable_jobs.py`：可恢复任务启动时冻结完整模型快照，并在执行时按快照还原 provider，处理模型故障。
  - `backend/bid-core/icg_demo/main.py`：支持透传 `model_transport` 以便测试与运行时适配。
- **测试夹具与测试集**：
  - `tests/backend/fake_openai_chat.py`：增强请求 body 记录、`.json` 解析与故障注入。
  - `tests/backend/test_model_config_provider.py`：新增 12 项专属契约测试用例。
- **文档与状态追踪**：
  - `docs/code/ISSUE-028.md`：详细代码实现与架构流程文档。
  - `docs/delivery/ISSUE-028.md`：本交付报告。
  - `issues/ISSUE-028.md`：更新 revision、补充交付索引与 AC-04 完成记录。
  - `docs/tasks/AI-M0.md`：更新 AI-01 任务卡验收勾选项。

## 3. 自动化测试执行结果

针对 ISSUE-028 核心测试套件：
```text
============================= test session starts =============================
platform win32 -- Python 3.12.9, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\徐佳馨\if-children-have-been-grown
configfile: pytest.ini
plugins: anyio-4.14.2
collected 12 items

tests/backend/test_model_config_provider.py::test_provider_from_model_config_openai_compatible_parameters PASSED [  8%]
tests/backend/test_model_config_provider.py::test_provider_from_model_config_stream_disabled_and_json_mode_disabled PASSED [ 16%]
tests/backend/test_model_config_provider.py::test_provider_from_model_snapshot PASSED [ 25%]
tests/backend/test_model_config_provider.py::test_runtime_switch_project_bound_config PASSED [ 33%]
tests/backend/test_model_config_provider.py::test_runtime_switch_company_default_config PASSED [ 41%]
tests/backend/test_recoverable_jobs.py::test_recoverable_job_advances_with_model_snapshot PASSED [ 50%]
tests/backend/test_recoverable_jobs.py::test_recoverable_job_uses_snapshot_even_if_config_changes_later PASSED [ 58%]
tests/backend/test_model_config_provider.py::test_sensitive_project_blocks_cloud_model_with_403_ac04 PASSED [ 66%]
tests/backend/test_model_config_provider.py::test_sensitive_project_allows_local_model PASSED [ 75%]
tests/backend/test_model_config_provider.py::test_model_call_failure_maps_to_502_model_unavailable PASSED [ 83%]
tests/backend/test_model_config_provider.py::test_secret_key_unavailable_in_generation_raises_503_without_retry_after PASSED [ 91%]
tests/backend/test_model_config_provider.py::test_real_model_probe_skipped_by_default SKIPPED [100%]

======================= 11 passed, 1 skipped in 19.71s ========================
```

关联模块全量回归（模型存储、OpenAI 适配器、可恢复任务、RAGFlow 证据候选、参考边界）：
```text
================== 90 passed, 2 skipped in 61.32s ===================
```

## 4. 边界与限制说明

1. **离线 CI 纯洁性**：单元测试绝不直连外部网络或真实模型，契约由 `fake_openai_chat` 保证。仅当环境变量显式声明 `ICG_RUN_REAL_MODEL_TESTS=1` 时才执行真实端点连通探测。
2. **错误响应兼容性**：敏感项目阻断 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL` 在旧版 `/api/chapters/...` 路由下包装为 `{"error": {"code": ...}}`，在 `/api/v1/...` 规范路由下直接返回 `{"code": ...}`，完全契合两套 API 的历史与新规范。
3. **工作流规范**：本 Issue 状态调整为 `in-review`，绝不私自标记为 `done` 或关闭 Issue，等待 QA 与主 Agent 进行最终审阅与验收。
