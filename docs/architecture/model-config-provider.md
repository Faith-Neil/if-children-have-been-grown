为什么有这个文件：说明对话适配器怎样按已有配置切换，而不再定义配置怎么存。

它解决什么问题：避免 Provider 设计继续携带字段、接口、加密和乐观锁，那些以 ISSUE-024 为准。

# 配置驱动的对话模型

日期：2026-10-12。关联 [ISSUE-010](../../issues/ISSUE-010.md)（closed）、[ISSUE-028](../../issues/ISSUE-028.md)（in-review）、[AI-01](../tasks/AI-M0.md#ai-01)、[AI-02](../tasks/AI-M0.md#ai-02)。本文件只设计 Provider 侧。不改 `backend/bid-core`，不改 `spec/openapi/demo-v1.json`，不加依赖。

配置的存储、字段定义、API、加密、If-Match 和幂等归后端 [ISSUE-024](../../issues/ISSUE-024.md)。先前写在这里的字段提案以该 Issue 为准。本文件不重复 `id`、`revision`、`allow_sensitive` 和密钥掩码规则。

## 决定

2026-10-12，user decision, relayed by PM：

- 部署形态、基址、模型名、上下文长度、最大输出和 API 密钥由配置页提供。本地与云端可以切换。流式是默认。支持 JSON 模式。
- 生产环境的生成服务只在内网。开发和测试可以出网。
- 嵌入和向量库不在本文件，见 [RAGFlow 适配器](ragflow-retrieval-adapter.md)。

这些值来自 ISSUE-024 将要保存的配置。本文件不把它们写成字段表，也不写成仓库常量。

## 读取配置

下一次生成读取该公司当前默认配置，而不是只读进程环境变量。未配置或仍是演示替身时，行为与今天相同。适配器不把配置写入存储。

`OpenAICompatibleModelProvider`（`backend/bid-core/icg_demo/openai_model.py`）已经用 httpx 调用 `POST {base_url}/v1/chat/completions`。`is_real_model` 为 true。`is_local` 来自被选中的配置。失败变成 502 `MODEL_UNAVAILABLE`。`create_app()` 的默认提供者仍是演示替身：`is_real_model` 为 false，`is_local` 为 true。实现时仍用已有的 `httpx==0.28.1`。

## 任务启动时快照

`startGeneration` 启动时记下当时读到的配置。已经开始的任务一直用这份快照。之后默认配置改变，不改进行中的任务。

## local 与 cloud

按配置上的本地或云端标记路由。本地配置走该配置给出的内网端点，云端配置走该配置给出的基址。两边都是同一套兼容调用。生产生成只在内网，是部署约束，不是本文件的存储规则。

## 敏感项目

敏感项目遇到云端配置时，在调用模型之前拒绝，返回 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`。这是策略拒绝，不是 502。今天的 `require_allowed_model` 仍是 409 `LOCAL_MODEL_REQUIRED`。实现配置读取时再改这一处映射。本轮不改 `domain.py`，也不把新码写进 `spec/openapi/demo-v1.json`。

## 流式与 JSON 模式

流式是默认：发往兼容接口的请求使用 `stream: true`。配置关闭流式时改为非流式。JSON 模式打开时，适配器打开兼容接口的 JSON 输出开关。开关的具体字段名以 ISSUE-024 的契约为准，本文件不另造请求体。

## 错误映射

| 情况 | 结果 |
|---|---|
| 地址或密钥导致这次调用失败 | 502 `MODEL_UNAVAILABLE`。正文和日志不含密钥 |
| 敏感项目使用云端配置 | 调用前 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL` |
| 今天的运行时 | 仍是 409 `LOCAL_MODEL_REQUIRED`，直到实现改映射 |

保存配置时缺主密钥的拒绝属于 ISSUE-024 的存储与加密，不是这次模型调用的映射。

## job.model_call

快照随事件发出。`job.model_call` 带上 `provider`、`model`，以及现有的 `is_real_model`、`is_local`、`duration_ms`、`error_code`。事件形态仍以大纲契约草案为准，本文件不改该草案。

## CI

托管 CI 没有密钥，也没有内网。测试用一个假的 OpenAI 兼容服务，记录它实际收到的请求头和 `base_url`。连真实地址的测试必须显式打开，默认跳过，CI 不跑。

## 本轮不做

不实现配置页，不改适配器，不改 OpenAPI 文件。不在本文件实现存储、字段定义、配置 API、加密或 If-Match。
