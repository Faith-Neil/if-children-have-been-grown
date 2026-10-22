为什么有这个文件：记录QA对ISSUE-028 / REV-M0-T46（配置驱动对话模型运行时接入）的独立复验与签署结论。

它解决什么问题：不轻信自报结果，亲手执行对话模型运行时契约测试与后端全量回归，核查 AC-01～AC-04 核心要求：动态配置装配与 Provider 路由、AC-04 敏感项目安全门禁（云端模型在调用前拦截并返回 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL）、任务快照隔离与按快照还原、故障注入与优雅降级（500 映射为 502 MODEL_UNAVAILABLE、503 SECRET_KEY_UNAVAILABLE 无 Retry-After）、离线纯洁性守卫（ICG_RUN_REAL_MODEL_TESTS=1 默认跳过）。

# ISSUE-028 配置驱动对话模型运行时接入独立复测与 QA 签署（REV-M0-T46）

- 被验任务：[ISSUE-028](../../issues/ISSUE-028.md) / [AI-01](../tasks/AI-M0.md#ai-01) · 配置驱动对话模型运行时接入
- 关联审查任务：REV-M0-T46
- 关联交付：[ISSUE-028 交付](../delivery/ISSUE-028.md)、[代码解释](../code/ISSUE-028.md)
- 被验核心文件：`backend/bid-core/icg_demo/openai_model.py`、`backend/bid-core/icg_demo/recoverable_jobs.py`、`backend/bid-core/icg_demo/domain.py`、`backend/bid-core/icg_demo/model_config_storage.py`、`tests/backend/test_model_config_provider.py`
- 复验环境：Windows, Python 3.12.9, pytest 8.4.2
- 结论：**通过 (PASS)**。**ISSUE-028 / AI-01 保持 in-review，严禁标 done**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 动态配置装配与 Provider 路由 | 通过 | `test_provider_from_model_config_openai_compatible_parameters`：根据 ModelConfig 动态装配 OpenAICompatibleModelProvider，正确注入解密后的 API Key，透传 `stream_enabled`、`json_mode_enabled`、`max_tokens` 与端点；支持继承公司默认与项目专属配置动态切换 |
| AC-02 任务快照隔离与推进保真 | 通过 | `test_recoverable_job_advances_with_model_snapshot` 与 `test_recoverable_job_uses_snapshot_even_if_config_changes_later`：可恢复任务在 202 启动时冻结完整模型快照（包含密文与参数）；任务推进与执行时严格从快照恢复 Provider，后续修改配置不影响已排队任务，`job.model_call` 完备记录耗时与模型标识 |
| AC-03 故障注入与优雅降级 | 通过 | `test_model_call_failure_maps_to_502_model_unavailable`：上游模型端点故障（HTTP 500）时，建议接口安全映射为 502 `MODEL_UNAVAILABLE`，可恢复任务置为 failed 终态；`test_secret_key_unavailable_in_generation_raises_503_without_retry_after`：配置含密钥但缺失 `ICG_SECRET_KEY` 时阻断并返回 503 `SECRET_KEY_UNAVAILABLE` 且**无** `Retry-After` 头 |
| AC-04 敏感项目安全门禁强拦截 | 通过 | `test_sensitive_project_blocks_cloud_model_with_403_ac04`：当项目标记为敏感项目（`sensitive=true`）且绑定云端/非本地模型时，在 `/api/chapters/{chapter_id}/suggestions` 与 `/api/v1/projects/{project_id}/generation/start` 调用前强制阻断，抛出 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`，端点实际调用为 0 次；`test_sensitive_project_allows_local_model`：绑定本地合规模型放行调用 |
| AC-05 离线纯洁性与外网守卫 | 通过 | `test_real_model_probe_skipped_by_default`：真实外部模型探测严格受 `ICG_RUN_REAL_MODEL_TESTS=1` 守卫，离线环境下默认安全跳过，假端点与录制回放全链路自包含 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 对话模型运行时契约测试 | `python -m pytest tests/backend/test_model_config_provider.py -v -rs` | **11 passed, 1 skipped** (外网跳过) | 10.37s |
| OpenAI 兼容适配器回归 | `python -m pytest tests/backend/test_openai_compatible_model.py -v -rs` | **34 passed, 1 skipped** | 2.12s |
| 可恢复任务回归 | `python -m pytest tests/backend/test_recoverable_jobs.py -v -rs` | **5 passed, 0 failed** | 1.84s |
| 后端全量回归 (离线) | `python -m pytest tests/backend/ -m "not mysql" -rs` | **468 passed, 5 skipped, 12 deselected** (0 failure) | 331.14s |

## 观察项与边界提示

1. **AC-04 门禁双重拦截机制**：系统不仅在项目绑定模型配置时校验敏感约束，而且在实际建议生成与批量生成启动（`/generation/start`）的调用前夕再次实施二次守卫，即使通过直接修改数据库逃逸了绑定校验，在调用瞬间仍会被前置拦截，防护极为严密。
2. **快照保真机制可靠**：生成作业将模型配置与密文原样固化进作业快照，从快照还原 Provider 时能够完全隔离运行时的动态配置漂移，彻底保障长时间运行的生成任务重试一致性。

## 签署状态

ISSUE-028 / AI-01 保持 **in-review**，**严禁标 done**。
