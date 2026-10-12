为什么有这个文件：把对话模型的配置页决定写成适配器设计，供后台起草契约时对照。

它解决什么问题：避免再发明一套错误码或密钥字段，也避免在没有契约草案时改运行代码。

# 配置驱动的对话模型

日期：2026-10-12。关联 [ISSUE-010](../../issues/ISSUE-010.md)（closed）、[ISSUE-028](../../issues/ISSUE-028.md)（in-review）、[AI-01](../tasks/AI-M0.md#ai-01)、[AI-02](../tasks/AI-M0.md#ai-02)。本文件只设计。不改 `backend/bid-core`，不改 `spec/openapi/demo-v1.json`，不加依赖。模型配置的 OpenAPI 草案由后台编写。ISSUE-024 留给那张契约卡，ISSUE-027 留给 Word 样式卡；本仓库不建立这两份详情。

## 决定

2026-10-12，user decision, relayed by PM：

- 部署形态、基址、模型名、上下文长度、最大输出和 API 密钥放在前端配置页。本地与云端可以切换。流式是默认。支持 JSON 模式。
- 生产环境的生成服务只在内网。开发和测试可以出网。
- 嵌入和向量库不在本文件选型，见 [RAGFlow 适配器](ragflow-retrieval-adapter.md)。

精确的基址、模型名和上下文数字是配置页上的值，不是写进仓库的常量。

## 接在现有适配器上

`OpenAICompatibleModelProvider`（`backend/bid-core/icg_demo/openai_model.py`）已经用 httpx 调用 `POST {base_url}/v1/chat/completions`。`is_real_model` 为 true。`is_local` 来自配置。密钥在调用时从命名环境变量读取，不放在对象上。失败变成 502 `MODEL_UNAVAILABLE`。`create_app()` 的默认提供者仍是演示替身：`is_real_model` 为 false，`is_local` 为 true。

本设计让下一次生成读取该公司当前默认配置，而不是只读进程环境变量。未配置或仍是演示替身时，行为与今天相同。实现时仍用已有的 `httpx==0.28.1`。流式对应请求里的 `stream: true`。JSON 模式对应兼容接口的 JSON 输出开关；具体字段名等后台契约，本文件不另造请求体。

## 字段提案

后台拥有路径和 schema。这里只提案字段。配置按公司存放，一家公司可以有多条，其中一条 `is_default`。`company_id` 来自会话，客户端不能改。

| 字段 | 方向 | 说明 |
|---|---|---|
| `id` | 读 | 服务器分配 |
| `revision` | 读 | 乐观锁。写操作的 If-Match 对它 |
| `company_id` | 读 | 来自会话 |
| `provider_type` | 读写 | `local` 或 `cloud` |
| `base_url` | 读写 | 不含密钥 |
| `model` | 读写 | 模型名 |
| `context_length` | 读写 | 上下文长度 |
| `max_tokens` | 读写 | 最大输出 |
| `api_key` | 只写 | 响应里不出现 |
| `has_api_key` | 读 | 布尔 |
| `api_key_masked` | 读 | 唯一允许出现的密钥形态 |
| `stream` | 读写 | 默认 true |
| `json_mode` | 读写 | 是否要求 JSON 输出 |
| `timeout` | 读写 | 秒 |
| `is_default` | 读写 | 同一公司仅一条为 true |
| `allow_sensitive` | 读 | 由 `provider_type` 派生。`local` 为 true，`cloud` 为 false。客户端不能单独改 |

写操作要求 `If-Match` 和 `Idempotency-Key`。缺头或坏键沿用已冻结的 428 `IF_MATCH_REQUIRED` / `IDEMPOTENCY_KEY_REQUIRED`。版本不符为 409 `VERSION_CONFLICT`。同一键不同指纹为 409 `IDEMPOTENCY_CONFLICT`。这些码已经在冻结表里，本设计不新增它们。

更新时：请求体没有 `api_key` 字段，保留原密钥；空字符串清除密钥；把读到的掩码原样送回，也视为未改密钥。

## 密钥

保存的 API 密钥用 Fernet 加密。主密钥来自环境变量 `ICG_SECRET_KEY`。`cryptography` 已由 [ISSUE-023](../../issues/ISSUE-023.md) 批准并写入 `requirements.txt`，本轮不新增依赖，也不调用它。

主密钥缺失时拒绝保存，返回 503 `SECRET_KEY_UNAVAILABLE`。这是后台草案里的码，本轮不写进 `spec/openapi/demo-v1.json`。

更换主密钥时保留上一把，直到已存的 API 密钥用新主密钥重新加密，然后停用旧主密钥。两把主密钥都不进 Git。

GET、列表、错误体、日志和堆栈只允许出现掩码。错误体仍是 `{code, message, details, traceId}`，`traceId` 等于 `X-Request-ID`。

## 测试连接

`POST .../model-configs/{id}/test`。

成功正文：`ok`、`provider`、`model`、`duration_ms`。

失败使用统一错误体，带 `traceId`。地址或密钥错误是 502 `MODEL_UNAVAILABLE`，正文和日志都不含密钥。

请求体省略 `api_key` 时，用已保存的密钥探测，并且不改存储。这与更新接口的“省略即保留”同一规则。测试连接本身不写入配置。

## 切换与敏感项目

下一次生成读取当时的默认配置。已经开始的任务保留 `startGeneration` 时的快照，并在 `job.model_call` 里带上 `provider`、`model`，以及现有的 `is_real_model`、`is_local`、`duration_ms`、`error_code`。

敏感项目改用云端配置时，在调用模型之前拒绝，返回 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`。这是策略拒绝，所以不是 502。今天的代码在 `domain.py` 的 `require_allowed_model` 里仍是 409 `LOCAL_MODEL_REQUIRED`。实现配置接口时再改映射。本轮不改这段代码，也不把新码写进冻结码表。

## CI

托管 CI 没有密钥，也没有内网。测试用一个假的 OpenAI 兼容服务，记录它实际收到的请求头和 `base_url`。连真实地址的测试必须显式打开，默认跳过，CI 不跑。

## 本轮不做

不实现配置页，不改适配器，不改 OpenAPI 文件，不把 403 与 503 两个新码登记进运行中的码表。
