为什么有这个文件：记录 ISSUE-028 AC-02 假服务实际跑过的检查，以及真实端点为什么没有跑。

它解决什么问题：避免把本机假端点的通过写成已经连通公司模型。

# 2026-10-12 ISSUE-028 假 OpenAI 兼容服务

日期：2026-10-12。关联 [ISSUE-028](../../issues/ISSUE-028.md) / [AI-01](../tasks/AI-M0.md#ai-01)。ISSUE-010 仍 closed。ISSUE-028 与 AI-01 仍 in-review。

## 怎么打开真实端点

默认不跑。需要同时满足：

```text
ICG_RUN_REAL_MODEL_TESTS=1
ICG_MODEL_PROVIDER=openai-compatible
ICG_MODEL_BASE_URL=<绝对 http(s) 源地址>
ICG_MODEL_NAME=<模型名>
ICG_MODEL_IS_LOCAL=true 或 false
ICG_MODEL_API_KEY=<密钥>
python3 -m pytest tests/backend/test_openai_compatible_model.py::test_real_openai_compatible_endpoint_when_opted_in -q
```

密钥变量名可以用 `ICG_MODEL_API_KEY_ENV` 改指别的变量。未设置 `ICG_RUN_REAL_MODEL_TESTS=1` 时，该测试跳过，原因是 `real model endpoint tests require ICG_RUN_REAL_MODEL_TESTS=1`。

## 命令和结果

| 检查 | 命令与结果 |
|---|---|
| 适配器与假服务 | `python3 -m pytest tests/backend/test_openai_compatible_model.py -q -rs`：34 passed，1 skipped，1 warning。跳过的是 `test_real_openai_compatible_endpoint_when_opted_in`，原因见上 |
| 全后台 | `python3 -m pytest tests/backend -q -rs`：355 passed，13 skipped，1 warning。12 项跳过是 `ICG_DATABASE_URL is unset`。1 项跳过是 `real model endpoint tests require ICG_RUN_REAL_MODEL_TESTS=1` |
| 记录一致性 | `node scripts/check-project-governance.cjs` 通过，输出为「治理检查通过：296 份 Markdown、383 项任务、34 项 Issue。」检查程序未修改 |

假服务绑定 `127.0.0.1` 的临时端口。成功用例核对 `Authorization: Bearer synthetic-test-key`、`Content-Type`、`Accept`，以及记录下的 `base_url` 等于提供者配置的地址。带 `/gateway` 前缀时，记录的 `base_url` 保留该前缀。没有访问外网。

## 局限

没有调用公司内网，没有验证真实模型名、上下文、认证和并发。配置页读取、任务快照和敏感项目 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL` 仍未实现。今天的敏感门禁仍是 409 `LOCAL_MODEL_REQUIRED`。不加依赖。不改 OpenAPI，不改错误码名单。治理检查只核对记录是否一致。本地通过不是合入，也不是发布。
