为什么有这个文件：把配置页上的对话模型收成一份待复核的适配器设计。

它解决什么问题：避免在后台契约草案还没写的时候改运行代码或另造错误码。

# ISSUE-028：配置驱动的对话模型设计

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-028 |
| 类型 | change |
| 优先级 | P1 |
| 状态 | in-review |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | model-config-fixture-1 |
| 关联 Task | [AI-01](../docs/tasks/AI-M0.md#ai-01)；实现仍待后续卡。现有适配器是 [AI-02](../docs/tasks/AI-M0.md#ai-02) |
| 关联 PR | 未创建 |
| 本地验收 | 设计已写。CI 假服务已编码。配置读取和真实端点仍未接通。见 [假服务核对](../docs/testing/2026-10-12-issue-028-fake-openai.md) |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [AI-01 交付](../docs/delivery/AI-01.md) |
| 代码 / 流程解释 | 不改 `backend/bid-core`。假服务见 [代码解释](../docs/code/AI-01.md) 与 [配置设计](../docs/architecture/model-config-provider.md) |
| 验证记录 | [2026-10-12 假服务核对](../docs/testing/2026-10-12-issue-028-fake-openai.md)；[AC-02 QA签署](../docs/testing/2026-10-12-issue-028-ac02-qa-signoff.md)；[AC-03 证据](../docs/testing/2026-10-12-issue-028-ac03-evidence.md)；[AC-03 QA签署](../docs/testing/2026-10-12-issue-028-ac03-qa-signoff.md) |

## 现象与证据

[ISSUE-010](ISSUE-010.md) 已关闭：对话模型由配置页提供。今天的 `OpenAICompatibleModelProvider` 仍从环境变量读取，默认提供者仍是演示替身。

本 Issue 只写 Provider 侧如何按配置切换：读取配置、任务启动时快照、local/cloud 路由、敏感项目约束、流式与 JSON 模式、错误映射、`job.model_call` 字段。配置的存储、API、加密和 If-Match 归后端 [ISSUE-024](ISSUE-024.md)。字段以该 Issue 为准。本文件只链接 [`stream_enabled`](ISSUE-024.md) 与 [`json_mode_enabled`](ISSUE-024.md)，不重定义。

## 影响与分流

- 影响范围：下一次生成如何读取配置并路由。不改当前 409 `LOCAL_MODEL_REQUIRED`。
- 敏感项目使用云端配置时，调用前拒绝，设计采用 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`。不写入 `spec/openapi/demo-v1.json`。
- 保存、字段、接口、加密和乐观锁不在本 Issue。见 ISSUE-024。
- 不加依赖。不改 `backend/bid-core` 运行代码。CI 假服务只在测试里。默认提供者仍是演示替身。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| AI-01 | Provider 侧设计可复核 | `docs/architecture/model-config-provider.md` | 读取、快照、路由、敏感约束、流式/JSON、错误映射和 `job.model_call` 已写明。字段与 API 不在本文件 | in-review |

没有单独的实现任务。实现要等后台契约。开发者不把本 Issue 标 closed。

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | Provider 读取配置、启动快照、local/cloud 路由、敏感约束、流式/JSON、错误映射和 `job.model_call` 已写明。字段定义与 API 已从本设计删去，并注明以 ISSUE-024 为准 | 已写入设计。未实现 |
| AC-02 | CI 使用记录请求头和基址的假服务；真实连接默认跳过 | 假服务已编码。QA 于 `9e3fcdd` 签署通过（REV-M0-T29）：355 passed / 13 skipped；CI 38231417634。真实连接须 `ICG_RUN_REAL_MODEL_TESTS=1`，默认跳过。路径规范化 hold。见 [核对](../docs/testing/2026-10-12-issue-028-fake-openai.md) 与 [签署](../docs/testing/2026-10-12-issue-028-ac02-qa-signoff.md)。Issue 仍 in-review，不标 closed |
| AC-03 | 不改 OpenAPI 文件，不新增依赖 | QA 于 tip `be3ce98` 独立复跑签署通过（REV-M0-T30）：夹具 `9e3fcdd` 相对其父 OpenAPI/requirements/openai_model diff 为空；create_app 默认仍 DemoModelProvider；聚焦 34 passed / 1 skipped。tip OpenAPI 差异只来自 `af51151`（ISSUE-033），不计入本 AC。见 [证据](../docs/testing/2026-10-12-issue-028-ac03-evidence.md) 与 [签署](../docs/testing/2026-10-12-issue-028-ac03-qa-signoff.md)。Issue 仍 in-review，不标 closed |
| AC-04 | 实现时，敏感项目使用非本地模型返回 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`（由现在的 409 `LOCAL_MODEL_REQUIRED` 改为 403） | 未实现。已记入 [AI-01](../docs/tasks/AI-M0.md#ai-01) 未勾选验收。本轮不改运行代码 |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。不新增验收步骤，不改任务计数 | `docs/PRD.md` | model-config-design-2 / ISSUE-028 / 2026-10-12 | 已核对 |
| ROADMAP | 无任务计数变化。决定用词随 ISSUE-010 | `docs/ROADMAP.md` | model-config-design-2 / ISSUE-028 / 2026-10-12 | 已核对 |
| ARCHITECTURE | 有影响。指向本设计，并写明未实现。本轮不改该文件正文 | `docs/ARCHITECTURE.md` | model-config-design-2 / ISSUE-028 / 2026-10-12 | 已核对 |
| TASK_BOARD | 无新任务。不改任务计数。AI-01 仍 in-review | `docs/TASK_BOARD.md` | model-config-fixture-1 / ISSUE-028 / 2026-10-12 | 已核对 |
| PROJECT_STATUS | 无新计数。写明假服务已落地，真实端点仍未接通 | `docs/PROJECT_STATUS.md` | model-config-fixture-1 / ISSUE-028 / 2026-10-12 | 已核对 |
| DOCUMENT_INDEX | 有影响。登记假服务核对与代码解释 | `docs/DOCUMENT_INDEX.md` | model-config-fixture-1 / ISSUE-028 / 2026-10-12 | 已核对 |

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | model-config-design-1 / in-review | 设计已提交。等待复核。不标 closed | [设计](../docs/architecture/model-config-provider.md) |
| 2026-10-12 | model-config-design-2 / in-review | 按 PM 分工删去字段定义和 API。存储、字段、接口、加密、If-Match/幂等改引 ISSUE-024。不创建 ISSUE-024 文件。不改任务计数 | [设计](../docs/architecture/model-config-provider.md) |
| 2026-10-12 | model-config-design-2 / in-review | ISSUE-024 详情已登记，状态 new。本 Issue 仍只保留 Provider 侧，不把存储字段抄回来 | [ISSUE-024](ISSUE-024.md) |
| 2026-10-12 | model-config-design-2 / in-review | PM 批准 D-1 后，本文件只引用 ISSUE-024 的 `stream_enabled` 与 `json_mode_enabled`，不写默认值或含义。状态仍 in-review | [ISSUE-024](ISSUE-024.md) |
| 2026-10-12 | model-config-design-2 / in-review | QA P3（REV-M0-T17，f5af6db）：决定记录改为 ISSUE-024 已由后台建档并拥有模型配置字段。流式与 JSON 模式开关的字段名归 ISSUE-024（后台决定，D-1），本 Issue 只引用、不定义。AI-01 补未勾选验收：敏感项目使用非本地模型返回 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`（由 409 改为 403）。状态仍 in-review | [决定核对](../docs/testing/2026-10-12-issue-010-decisions.md) |
| 2026-10-12 | model-config-design-2 / in-review | 后台决定 D-1 已写在 ISSUE-024。本 Issue 引用 `stream_enabled` 与 `json_mode_enabled`。类型、默认值、`revision` 乐观锁和任务开始时的配置快照以该文件为准，不重定义。状态仍 in-review | [ISSUE-024](ISSUE-024.md) |
| 2026-10-12 | model-config-design-2 / in-review | `3e1445e` 已把 D-1 字段写进 ISSUE-024。本文件只链接 [`stream_enabled`](ISSUE-024.md) 与 [`json_mode_enabled`](ISSUE-024.md)，不抄定义。状态仍 in-review | [ISSUE-024](ISSUE-024.md) |
| 2026-10-12 | model-config-fixture-1 / in-review | AC-02 假服务已编码。记录请求头和实际 `base_url`。真实端点须 `ICG_RUN_REAL_MODEL_TESTS=1`，默认跳过。不改 `backend/bid-core`，不改 OpenAPI，不加依赖。配置运行时仍未接通。不标 closed | [核对](../docs/testing/2026-10-12-issue-028-fake-openai.md) |
| 2026-10-12 | model-config-fixture-1 / in-review | QA 签署 AC-02（REV-M0-T29）：夹具层通过；路径规范化 hold，不要求改适配器；配置运行时与真模型仍未接通。**不标 closed** | [签署](../docs/testing/2026-10-12-issue-028-ac02-qa-signoff.md) |
| 2026-10-12 | model-config-fixture-1 / in-review | AC-03 证据已备，待 QA 勾选。`9e3fcdd` 不改 OpenAPI 与依赖；尖端 `20f2b92` 的 OpenAPI 差异属于 `af51151`。ISSUE-024 与 AC-04 仍等待。路径规范化 hold，真模型冒烟另计。不标 closed，不标 done | [AC-03 证据](../docs/testing/2026-10-12-issue-028-ac03-evidence.md) |
| 2026-10-12 | model-config-fixture-1 / in-review | QA 签署 AC-03（REV-M0-T30）：独立复跑 `be3ce98` 证据通过；OpenAPI/依赖/演示替身三项过线。ISSUE-024 与 AC-04 仍等待。路径规范化 hold。**不标 closed** | [签署](../docs/testing/2026-10-12-issue-028-ac03-qa-signoff.md) |

## 本地验收与后续合入发布

- 本地验收：设计已写。CI 假服务已核对（AC-02，REV-M0-T29）。AC-03 已由 QA 签署（REV-M0-T30）。ISSUE-024 与 AC-04 仍等待。路径规范化 hold，真模型冒烟另计。不标 closed。
- PR：未创建。合入：未合入。发布：未发布。
