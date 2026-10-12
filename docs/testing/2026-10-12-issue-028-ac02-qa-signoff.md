为什么有这个文件：记录QA对ISSUE-028 AC-02假端点夹具（9e3fcdd）的独立签署。

它解决什么问题：确认CI假服务、默认跳过真实端点、不改生产适配器，并写明不标done。

# ISSUE-028 AC-02 假端点夹具 QA签署（REV-M0-T29）

- 被验提交：`9e3fcdd`（test: ISSUE-028 fake OpenAI-compatible fixture for CI）；复核基线：`5e4a627`（含该提交）；关联 ISSUE-028 / AI-01；数据：仅合成数据。
- 结论：**通过**（夹具层）。**ISSUE-028 / AI-01 / 本卡均不标 done / closed**，等项目经理设置。路径规范化按用户 hold，不要求改适配器。

## 验收对照

| 检查 | 结果 | 证据 |
|---|---|---|
| AC-02 假服务 + fixture | 通过 | `tests/backend/fake_openai_chat.py`（`FakeOpenAIChat`、`real_model_skip_reason`）；`conftest.py` 提供 `fake_openai_chat`；成功/网关前缀用例记录 `Authorization`、`Content-Type`、`Accept` 与有效 `base_url` |
| 真实端点默认跳过 | 通过 | `@pytest.mark.live_model`；仅 `ICG_RUN_REAL_MODEL_TESTS=1` 时运行；未设旗时 skip 原因为 `real model endpoint tests require ICG_RUN_REAL_MODEL_TESTS=1`；`true` 等非 `1` 值仍跳过 |
| CI 不设该旗 | 通过 | `.github/workflows/offline-check.yml` 与 `.github/` 全文无 `ICG_RUN_REAL_MODEL_TESTS` |
| 不改生产适配器 / OpenAPI / 错误码 / 依赖 | 通过 | `9e3fcdd` diff 不含 `backend/`、`spec/openapi/`、`requirements.txt`；`create_app()` 默认仍为 `DemoModelProvider` |
| 全后台回归 | 通过 | 未设真模型旗：`pytest tests/backend -q -rs` → **355 passed, 13 skipped**（12× `ICG_DATABASE_URL is unset` + 1× 真模型旗） |
| 聚焦套件 | 通过 | `pytest tests/backend/test_openai_compatible_model.py -q -rs` → **34 passed, 1 skipped** |
| 治理 | 通过 | `node scripts/check-project-governance.cjs`（签署前基线：296 Markdown、384 任务、34 Issue；签署提交后加本卡再跑） |
| 路径规范化 | 不要求 | 用户 hold；本签只验夹具层，不要求改适配器 |

## 套件与 CI

- 被验提交 CI [run 38231417634](https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/38231417634)（head `9e3fcdd`）：success。
- 本机复跑日志：`/workspace/qa-logs/issue028-model-tests.txt`、`issue028-backend-full.txt`、`issue028-governance.txt`（box 侧，不入库）。

## 观察项

- O-1：配置页读取、任务快照、敏感项目 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL` 仍未实现；今日门禁仍是 409 `LOCAL_MODEL_REQUIRED`。
- O-2：未调用公司内网真实模型；真模型验收另计。
- O-3：ISSUE-028 / AI-01 / REV-M0-T29 保持 in-review，**不标 done**。
