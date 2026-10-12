为什么有这个文件：把模型选型和兼容适配器分成可单独验收的任务。

它解决什么问题：避免在端点和数据库还没决定时，把演示替身或一个适配器说成生产模型已经接入。

# AI-M0：模型接入准备

日期：2026-10-12。AI 表示模型接入任务，独立于前端 FE 计划和 APP 页面计划。

<a id="ai-01"></a>

## AI-01 · 登记模型、向量、业务库和内网访问待决项

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 记录选项本身不依赖外部接口；用户决定的等待时间不计入实现 |
| 关联 Issue | [ISSUE-010](../../issues/ISSUE-010.md)，并回链 [ISSUE-005](../../issues/ISSUE-005.md) |
| 依赖 | [FE-M0-T02](FE-M0.md#fe-m0-t02)。不依赖尚未选定的端点或数据库 |
| PRD / 架构出处 | [前端架构](../ARCHITECTURE.md) 当前实施段；[ISSUE-005](../../issues/ISSUE-005.md) DG-06 |
| 完成时交付 | [登记交付](../delivery/AI-01.md) |
| 代码解释 | 不改 `backend/bid-core`。假服务见 [代码解释](../code/AI-01.md) |

范围：列出对话模型、嵌入、重排、向量库、业务库和内网验证的可选项，以及需要用户回答的问题。项目经理对 PostgreSQL 16 与 pgvector 的意见只记为建议，用户没有采纳。

当前条件：2026-10-12 用户决定业务库为 MySQL 8，对话模型由配置页提供，嵌入与向量库用 RAGFlow 自带能力，生产生成只在内网（user decision, relayed by PM）。ISSUE-010 已 closed。本卡为 in-review。托管 CI 不能访问公司内网。不改 `backend/bid-core`。CI 使用测试目录里的假对话服务；连真实地址须 `ICG_RUN_REAL_MODEL_TESTS=1`，默认跳过。配置读取仍未实现。

可验证验收：

- [x] 选项和未决问题已写入 ISSUE-010，建议与决定分开。
- [x] 用户已作出选择，路线图和架构的决定用词已更新。PRD 不新增验收。PRD、路线图和 brief 的任务计数未改。
- [x] CI 使用假的 OpenAI 兼容服务，记录请求头和实际 `base_url`。连真实地址的测试须 `ICG_RUN_REAL_MODEL_TESTS=1`，默认跳过。
- [ ] 选定后的真实端点或库有独立验收，不由本登记代替。
- [ ] 敏感项目使用非本地模型返回 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`（由 409 改为 403）。

<a id="ai-02"></a>

## AI-02 · OpenAI 兼容对话适配器

| 字段 | 内容 |
|---|---|
| 状态 | done |
| 估算 | 在现有模型和 HTTP 库上增加一个适配器 |
| 关联 Issue | [ISSUE-011](../../issues/ISSUE-011.md) |
| 依赖 | [BE-M0-T01](BE-M0.md#be-m0-t01) 的 `ModelProvider`。不依赖 ISSUE-010 的最终端点 |
| PRD / 架构出处 | [前端架构](../ARCHITECTURE.md) 模型替换口；敏感项目本地门禁保持原行为 |
| 完成时交付 | [交付](../delivery/AI-02.md) |
| 代码解释 | [代码解释](../code/AI-02.md) |

范围：实现 `OpenAICompatibleModelProvider`。`name` 为 `openai-compatible`，`is_real_model` 为 true，`is_local` 来自配置。`suggest` 调用 `POST {base_url}/v1/chat/completions`。配置来自环境变量。演示替身仍是 `create_app()` 的默认实现；只有显式打开配置开关才选择真实适配器。

当前条件：不连接真实端点。密钥不入库。不新增依赖。

可验证验收：

- [x] 假 HTTP 覆盖成功、超时、非 200、畸形 JSON，以及 `is_local` 真假与敏感项目门禁。
- [x] 失败走现有 502 `MODEL_UNAVAILABLE`，不返回假成功，不改已提交正文。
- [x] `tests/backend/test_reference_boundaries.py` 包含在全后台回归中。
- [x] 交付、代码解释、验证记录和基线同步已登记。真实内网调用不在本卡。

项目经理于 10-12 12:10 在 QA 签署后确认。状态为 done。合入和发布仍未发生。ISSUE-010 已 closed，真实端点仍未验收。

<a id="ai-03"></a>

## AI-03 · 检索层内存骨架

| 字段 | 内容 |
|---|---|
| 状态 | done |
| 估算 | 在现有协议旁增加内存检索口，不接外部服务 |
| 关联 Issue | [ISSUE-016](../../issues/ISSUE-016.md) |
| 依赖 | [BE-M0-T01](BE-M0.md#be-m0-t01) 的替换口。向量库已定为 RAGFlow 自带，本卡仍不连接它 |
| PRD / 架构出处 | [前端架构](../ARCHITECTURE.md) 当前实施段。业务库为 MySQL 8，本卡不连接它 |
| 完成时交付 | [交付](../delivery/AI-03.md) |
| 代码解释 | [代码解释](../code/AI-03.md) |

范围：定义 `EmbeddingProvider.embed`、`RerankProvider.rerank` 和 `VectorStore.upsert/search`。搜索按 `company_id`、`status` 和 `type` 过滤。三者都只提供内存实现。`EvidenceCandidateService` 产出路径 A（已确认资料上的规则）、路径 B（嵌入、按公司检索、重排）和路径 C（历史投标，仅供参考且不可附着）。B 或 C 失败，或知识库关闭时，保留 A 并记录跳过原因。

当前条件：不连接 MySQL，不连接 RAGFlow，不新增依赖，不挂到 `create_app`。向量库选型已在 ISSUE-010 关闭，不由本卡实现。

可验证验收：

- [x] 三个协议和内存实现可用，搜索必须同时给出公司、状态和类型。
- [x] 合成数据覆盖跨公司隔离，历史投标不可附着，失败或知识库关闭时回退到 A。
- [x] `tests/backend/test_reference_boundaries.py` 包含在全后台回归中。
- [x] 交付、代码解释、验证记录和基线同步已登记。真实库不在本卡。

项目经理依据 QA 签署 2fe6198（REV-M0-T16）确认。状态为 done。ISSUE-016 为 closed。合入和发布仍未发生。真实库不在本卡。
