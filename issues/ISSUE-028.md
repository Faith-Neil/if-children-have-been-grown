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
| revision | model-config-design-2 |
| 关联 Task | [AI-01](../docs/tasks/AI-M0.md#ai-01)；实现仍待后续卡。现有适配器是 [AI-02](../docs/tasks/AI-M0.md#ai-02) |
| 关联 PR | 未创建 |
| 本地验收 | 设计已写。没有运行时。见 [核对](../docs/testing/2026-10-12-issue-010-decisions.md) |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [AI-01 交付](../docs/delivery/AI-01.md) |
| 代码 / 流程解释 | 无运行代码。设计见 [配置设计](../docs/architecture/model-config-provider.md) |
| 验证记录 | [2026-10-12 决定核对](../docs/testing/2026-10-12-issue-010-decisions.md) |

## 现象与证据

[ISSUE-010](ISSUE-010.md) 已关闭：对话模型由配置页提供。今天的 `OpenAICompatibleModelProvider` 仍从环境变量读取，默认提供者仍是演示替身。

本 Issue 只写 Provider 侧如何按配置切换：读取配置、任务启动时快照、local/cloud 路由、敏感项目约束、流式与 JSON 模式、错误映射、`job.model_call` 字段。配置的存储、字段定义、API、加密、If-Match 和幂等归后端 ISSUE-024。字段提案已交后台，以 ISSUE-024 为准。本仓库没有 ISSUE-024 的详情文件，因此只从本 Issue 和设计文档引用该编号，不创建该文件。

## 影响与分流

- 影响范围：下一次生成如何读取配置并路由。不改当前 409 `LOCAL_MODEL_REQUIRED`。
- 敏感项目使用云端配置时，调用前拒绝，设计采用 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`。不写入 `spec/openapi/demo-v1.json`。
- 保存、字段、接口、加密和乐观锁不在本 Issue。见 ISSUE-024。
- 不加依赖。不改运行代码。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| AI-01 | Provider 侧设计可复核 | `docs/architecture/model-config-provider.md` | 读取、快照、路由、敏感约束、流式/JSON、错误映射和 `job.model_call` 已写明。字段与 API 不在本文件 | in-review |

没有单独的实现任务。实现要等后台契约。开发者不把本 Issue 标 closed。

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | Provider 读取配置、启动快照、local/cloud 路由、敏感约束、流式/JSON、错误映射和 `job.model_call` 已写明。字段定义与 API 已从本设计删去，并注明以 ISSUE-024 为准 | 已写入设计。未实现 |
| AC-02 | CI 使用记录请求头和基址的假服务；真实连接默认跳过 | 已写入设计。假服务未编码 |
| AC-03 | 不改 OpenAPI 文件，不新增依赖 | 本轮 diff 不含 `spec/openapi/demo-v1.json` 与 `requirements.txt` |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。不新增验收步骤，不改任务计数 | `docs/PRD.md` | model-config-design-2 / ISSUE-028 / 2026-10-12 | 已核对 |
| ROADMAP | 无任务计数变化。决定用词随 ISSUE-010 | `docs/ROADMAP.md` | model-config-design-2 / ISSUE-028 / 2026-10-12 | 已核对 |
| ARCHITECTURE | 有影响。指向本设计，并写明未实现。本轮不改该文件正文 | `docs/ARCHITECTURE.md` | model-config-design-2 / ISSUE-028 / 2026-10-12 | 已核对 |
| TASK_BOARD | 无新任务。不改任务计数 | `docs/TASK_BOARD.md` | model-config-design-2 / ISSUE-028 / 2026-10-12 | 已核对 |
| PROJECT_STATUS | 无新计数。设计范围改在 ISSUE-028，端点仍未接通 | `docs/PROJECT_STATUS.md` | model-config-design-2 / ISSUE-028 / 2026-10-12 | 已核对 |
| DOCUMENT_INDEX | 有影响。本设计的说明改为 Provider 侧 | `docs/DOCUMENT_INDEX.md` | model-config-design-2 / ISSUE-028 / 2026-10-12 | 已核对 |

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | model-config-design-1 / in-review | 设计已提交。等待复核。不标 closed | [设计](../docs/architecture/model-config-provider.md) |
| 2026-10-12 | model-config-design-2 / in-review | 按 PM 分工删去字段定义和 API。存储、字段、接口、加密、If-Match/幂等改引 ISSUE-024。不创建 ISSUE-024 文件。不改任务计数 | [设计](../docs/architecture/model-config-provider.md) |

## 本地验收与后续合入发布

- 本地验收：设计核对完成，运行时未做。
- PR：未创建。合入：未合入。发布：未发布。
