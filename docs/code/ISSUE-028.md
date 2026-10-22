为什么有这个文件：说明配置驱动的对话模型运行时接入（ISSUE-028）的代码架构、调用流程与实现细节。

它解决什么问题：详细记录从静态环境变量提供者迁移为项目/租户配置驱动提供者的完整调用链、快照隔离、流式/JSON模式透传、敏感项目 403 门禁拦截及上游故障映射机制。

# ISSUE-028：配置驱动的对话模型运行时接入代码说明

- 对应 Issue：[ISSUE-028](../../issues/ISSUE-028.md)
- 交付文档：[ISSUE-028 交付](../delivery/ISSUE-028.md)
- 设计文档：[模型配置提供者架构设计](../architecture/model-config-provider.md)
- 实现日期：2026-10-21
- 核心代码路径：
  - `backend/bid-core/icg_demo/openai_model.py`
  - `backend/bid-core/icg_demo/model_config_storage.py`
  - `backend/bid-core/icg_demo/domain.py`
  - `backend/bid-core/icg_demo/workflow.py`
  - `backend/bid-core/icg_demo/recoverable_jobs.py`
  - `backend/bid-core/icg_demo/main.py`
  - `tests/backend/fake_openai_chat.py`
  - `tests/backend/test_model_config_provider.py`

## 1. 架构总览与运行时解析流程

系统在处理章节建议生成（`POST /api/chapters/{chapter_id}/suggestions`）与可恢复章节正文生成（`POST /api/v1/projects/{project_id}/generation/start`）时，摒弃了早期的单一全局环境变量读取机制，升级为两级动态配置路由体系：

```
                [请求到达: suggest / generation/start]
                                 │
                                 ▼
                     [解析项目归属 project_id]
                                 │
            ┌────────────────────┴────────────────────┐
            ▼                                         ▼
   已显式绑定配置 ID ?                          未绑定项目级配置
            │                                         │
            ▼                                         ▼
   读取 Project Model Config                读取 Company Default Config
            │                                         │
            └────────────────────┬────────────────────┘
                                 │
                                 ▼
                   [构造/还原运行时 ModelProvider]
                     (provider_from_model_config)
                                 │
                                 ▼
                   [敏感项目安全门禁检查 AC-04]
            (require_allowed_model(project, provider, state))
              项目敏感 & 非本地/敏感禁用 ──► 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL
                                 │ (通过)
                                 ▼
                      [组装 Payload 发起调用]
                      - stream_enabled 透传
                      - json_mode_enabled 透传
                      - 注入解密后的 API Key
                                 │
            ┌────────────────────┴────────────────────┐
            ▼                                         ▼
        调用成功                                 上游故障/超时
            │                                         │
            ▼                                         ▼
       返回生成文本                           映射为 502 MODEL_UNAVAILABLE
                                        (任务记录 failed 并记录 error 事件)
```

## 2. 核心模块与实现细节

### 2.1 适配器参数扩展与流式/JSON 模式支持 (`openai_model.py`)
- **配置数据结构 `OpenAICompatibleConfig`**：
  新增 `stream_enabled: bool = False`、`json_mode_enabled: bool = False` 与 `api_key: str | None = None` 字段。
- **请求 Payload 组装**：
  在 `OpenAICompatibleModelProvider._once()` 中：
  - 若 `self.stream_enabled` 为真，请求体加入 `"stream": True`；
  - 若 `self.json_mode_enabled` 为真，请求体加入 `"response_format": {"type": "json_object"}`；
  - 若配置了 `self.api_key`，自动在请求头附加 `Authorization: Bearer <plain_key>`。
- **SSE 事件流解析增强**：
  在 `_assistant_text()` 中，除支持标准 JSON `choices[0].message.content` 外，增加对 `text/event-stream` 数据格式（多行 `data: {...}`）的流式 chunk 聚合解析，提取 `choices[0].delta.content`，确保流式开启时响应能正确拼接。

### 2.2 配置转换工厂与快照还原 (`model_config_storage.py`)
- **`provider_from_model_config(config: ModelConfig, default_provider=None)`**：
  - 若 `config.provider == "demo"`，直接复用传入的 `default_provider`；
  - 若为 `openai-compatible`，通过 `decrypt_api_key(config.encrypted_api_key)` 解密密钥（若密文存在但环境变量 `ICG_SECRET_KEY` 缺失，抛出 503 `SECRET_KEY_UNAVAILABLE` 且不包含 `Retry-After` 头）；
  - 构造包含 `stream_enabled`、`json_mode_enabled`、`is_local`、`allow_sensitive` 的 `OpenAICompatibleModelProvider` 实例。
- **`provider_from_model_snapshot(snapshot: dict[str, Any], default_provider=None)`**：
  从任务持久化快照中解构参数，重构运行时 provider，保证排队与执行生命周期中的模型确定性。
- **更新默认配置兜底**：
  在 `ModelConfigService.update()` 中补充了 `_ensure_default_config()`，若租户尚未入库默认配置记录，直接就地初始化默认配置后再执行更新。

### 2.3 动态解析与门禁阻断 (`domain.py` & `workflow.py`)
- **`DemoService.resolve_model_provider()`**：
  按 `项目绑定配置 -> 公司默认配置 -> 系统初始注入提供者` 顺序平滑回落。
- **敏感项目安全门禁 `require_allowed_model()` (AC-04 闭环)**：
  - 判定条件：当 `project.sensitive is True` 时，检查生效的模型配置或 provider。
  - 规则：如果 `provider.is_local` 为 `False` 或配置声明 `allow_sensitive` 为 `False`，在实际调用模型端点前立即拒绝，抛出 `DomainError(403, "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL", "敏感项目必须使用本地内网部署的大模型")`。
  - 对于未绑定新配置的旧式静态演示环境，仍回落至原有的 409 `LOCAL_MODEL_REQUIRED`，保障向前兼容。
- **章节建议接口 (`DemoService.suggest`)**：
  调用前按 `resolve_model_provider` 取得该项目生效 provider，传入 `require_allowed_model`，并使用该 provider 完成提词推理。
- **同步生成 (`WorkflowEngine.generate`)**：
  在执行阶段按项目获取生效 provider 并执行门禁，杜绝敏感项目泄漏至云端模型。

### 2.4 可恢复任务快照冻结与执行闭环 (`recoverable_jobs.py`)
- **任务启动快照冻结 (`start`)**：
  在创建任务时解析该项目当前生效的模型配置，抓取包括 `provider`、`base_url`、`model`、`is_local`、`is_real_model`、`timeout_seconds`、`max_tokens`、`encrypted_api_key`、`stream_enabled`、`json_mode_enabled` 在内的完整快照并持久化于 `job.model_snapshot`。
- **推进执行 (`_advance`)**：
  执行时调用 `resolve_provider_from_snapshot()`，固定使用快照中的端点与模型进行建议生成，不受任务排队期间外界修改配置的影响。
- **异常捕获与失败事件**：
  当调用上游模型发生 `DomainError`（如 502、503）或其他网络异常时，将任务状态置为 `failed`，写入 `MODEL_UNAVAILABLE` 错误体并派发 `job.model_call` 故障事件。

## 3. 测试夹具与测试设计 (`test_model_config_provider.py`)

- **假服务增强 (`fake_openai_chat.py`)**：
  在现有 `FakeOpenAIChat` 上扩展 `RecordedChatCall.body` 与 `.json` 属性，新增 `status_code` 与 `response_body` 可注入属性，支持精确断言发送至上游模型的 payload（如 `stream`、`response_format`）与模拟上游 500 故障。
- **测试矩阵**：
  1. `test_provider_from_model_config_openai_compatible_parameters`：验证参数解构、密钥解密、流式与 JSON 模式透传。
  2. `test_provider_from_model_config_stream_disabled_and_json_mode_disabled`：验证开关关闭时 payload 不含相关字段。
  3. `test_provider_from_model_snapshot`：验证从快照无损还原 provider。
  4. `test_runtime_switch_project_bound_config`：验证项目绑定配置优先于租户默认配置生效。
  5. `test_runtime_switch_company_default_config`：验证租户级默认配置全局回落生效。
  6. `test_recoverable_job_advances_with_model_snapshot`：验证异步可恢复任务使用快照正确推进并触发 `job.model_call`。
  7. `test_recoverable_job_uses_snapshot_even_if_config_changes_later`：验证启动后更新配置不影响已有任务的模型选择。
  8. `test_sensitive_project_blocks_cloud_model_with_403_ac04`：闭环 AC-04，验证敏感项目调用云端模型在 suggest 与可恢复任务中均返回 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`，且上游端点未被调用。
  9. `test_sensitive_project_allows_local_model`：验证敏感项目使用本地合规模型放行调用。
  10. `test_model_call_failure_maps_to_502_model_unavailable`：验证上游 500 映射为 502 `MODEL_UNAVAILABLE`。
  11. `test_secret_key_unavailable_in_generation_raises_503_without_retry_after`：验证主密钥丢失时返回 503 且无 `Retry-After`。
  12. `test_real_model_probe_skipped_by_default`：保证离线 CI 纯洁性，未显式声明时默认跳过真实探测。
