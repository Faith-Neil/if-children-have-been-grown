为什么有这个文件：记录 OpenAI 兼容适配器这次实际跑过的检查和没有覆盖的范围。

它解决什么问题：避免把假传输上的通过结果写成已经连通公司内网模型。

# 2026-10-12 OpenAI 兼容适配器验证

日期：2026-10-12。关联 [ISSUE-011](../../issues/ISSUE-011.md) / [AI-02](../tasks/AI-M0.md#ai-02)。ISSUE-010 没有运行选型验收，因为它仍等待用户决定。

## 命令和结果

| 检查 | 命令与结果 |
|---|---|
| 适配器契约 | `python3 -m pytest tests/backend/test_openai_compatible_model.py -q`：30 passed，1.47 秒 |
| 全后台 | `python3 -m pytest tests/backend -q`：292 passed，1 warning，78.03 秒 |
| 记录一致性 | `node scripts/check-project-governance.cjs`：通过。输出为「治理检查通过：138 份 Markdown、342 项任务、14 项 Issue。」检查程序未修改，因此未重跑治理测试 |

全后台 292 项包含原有 `tests/backend/test_reference_boundaries.py`。该文件本轮没有修改，敏感项目在未声明位置或非本地真实模型时仍返回 409，本地真实模型仍可生成。新增契约另用同一个 `create_app(model_provider=...)` 路径检查 `OpenAICompatibleModelProvider` 的 `is_local` 为 true 和 false。

既有警告一条：Starlette 提示 `httpx` 与 `TestClient` 的搭配将要弃用。它在本次改动前已经存在，本轮没有为它增加依赖。

## 契约覆盖

- 成功：POST `http://127.0.0.1:9/v1/chat/completions`，带模型名、指令、正文、`max_tokens` 和 `stream: false`，返回助手原文。
- 超时一次后成功，只采用第二次的真实文本。
- 超时或连接失败在重试耗尽后失败，异常文本不含密钥和提示词。
- 401/403/404 不重试。408/429/500/502/503/504 重试后仍失败，不回显响应体。
- 畸形 JSON、空内容、空白和非字符串内容失败，并且不因为配置了重试而再试。
- 302 不跟随。
- 没有密钥时不发送 Authorization。
- 500 经旧章节建议接口变成 502 `MODEL_UNAVAILABLE`，章节正文和版本不变，响应不含密钥。
- 敏感项目：`is_local=false` 时建议和生成都是 409，假传输收到 0 次请求；`is_local=true` 时建议返回适配器名称且 `is_real_model` 为 true，生成完成，共 3 次假请求。
- `create_app()` 在环境变量已设为真实适配器时仍是演示替身。显式开关才会启用；缺少 base URL 时失败，不退回替身。

样本全部是合成文本和 `synthetic-test-key`。假传输没有连接 `127.0.0.1:9`。

## 局限

没有调用公司内网，没有验证 Qwen 30B 的真实名称、上下文、认证和并发。没有测嵌入、重排、向量库或任何业务数据库。没有浏览器验收，因为这次没有改页面。治理检查只核对记录是否一致，不证明模型可用。本地通过不是 PR 合入，也不是发布。
