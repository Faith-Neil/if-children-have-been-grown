为什么有这个文件：把模型、向量、业务库和内网访问的用户决定记在一处。

它解决什么问题：避免把配置页或 RAGFlow 的设计写成已经接通的生产服务。

# ISSUE-010：模型、向量库、业务库与内网访问

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-010 |
| 类型 | decision |
| 优先级 | P0 |
| 状态 | closed |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | model-choice-3 |
| 关联 Task | [AI-01](../docs/tasks/AI-M0.md#ai-01)；上游门禁 [ISSUE-005](ISSUE-005.md) / FE-M0-T04 |
| 关联 PR | 未创建 |
| 本地验收 | 决定已登记。真实端点未验收。见 [核对](../docs/testing/2026-10-12-issue-010-decisions.md) |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [AI-01 交付](../docs/delivery/AI-01.md) |
| 代码 / 流程解释 | 无运行代码。配置设计见 [ISSUE-028](ISSUE-028.md)，检索设计见 [ISSUE-029](ISSUE-029.md) |
| 验证记录 | [2026-10-12 决定核对](../docs/testing/2026-10-12-issue-010-decisions.md) |

## 现象与证据

生产门禁 [ISSUE-005](ISSUE-005.md) 仍是 in-progress。当前后台默认是内存仓库和演示模型替身。托管 CI 没有密钥，也不能访问内网。

2026-10-12，用户决定业务库为 MySQL 8（user decision, relayed by PM）。MySQL 8 没有向量检索，pgvector 不再作为同库选项。连接和空迁移已由项目经理在 QA 签署 `98c5129` 后确认，业务表仍未接入。

同日，用户继续决定（user decision, relayed by PM）：

1. 对话模型的部署形态、基址、模型名、上下文长度、最大输出和 API 密钥放在前端配置页。本地与云端可以切换。流式是默认。支持 JSON 模式。
2. 嵌入模型和向量库使用 RAGFlow 自带能力，在 RAGFlow 内配置。本仓库不另选向量库。检索层连接 RAGFlow。
3. 生产环境的生成服务只在内网。开发和测试可以使用互联网。

精确基址、模型名和上下文数字是配置页上的值，不写进仓库。重排产品没有出现在这三项里。[ISSUE-017](ISSUE-017.md) 的草案已说明这一点。检索设计提议重排留在 RAGFlow 的 `rerank_id`，该提议在 [ISSUE-029](ISSUE-029.md)，不另算一项已关闭的选型。

内网草案 [第 7 节](../docs/operations/intranet-deployment-plan.md) 先记下了放置方式，并写明当时不改本 Issue 正文。本记录是随后的基线同步。

## 已关闭的问题

| 问题 | 决定 |
|---|---|
| 对话端点、模型名、上下文、密钥放在哪里 | 配置页。值不入库 |
| 是否允许云端模型 | 允许切换。敏感项目不能用云端，见配置设计 |
| 嵌入与向量库 | RAGFlow 自带。不选 Milvus、Qdrant、Elasticsearch 或 pgvector |
| 业务库 | MySQL 8。2026-10-12，user decision, relayed by PM |
| 生产生成是否出网 | 生产不出网。开发与测试可以出网 |
| 密钥是否可进日志 | 不可以。只允许掩码出现在 GET、列表、错误、日志和堆栈 |

并发上限、知识库规模和 OCR 仍没有数字。它们不阻止本 Issue 关闭，也不由本记录假装已经选定。

## 后续设计

不在本 Issue 实现。

- [配置驱动的对话模型](../docs/architecture/model-config-provider.md)，[ISSUE-028](ISSUE-028.md)
- [RAGFlow 检索适配器](../docs/architecture/ragflow-retrieval-adapter.md)，[ISSUE-029](ISSUE-029.md)

敏感项目拒绝云端配置时，Provider 侧采用 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`。今天的 `require_allowed_model` 仍是 409 `LOCAL_MODEL_REQUIRED`。配置的存储、字段定义、API、加密、If-Match 和幂等归 ISSUE-024，字段提案已交后台，以 ISSUE-024 为准。详情现已登记，状态 new。ISSUE-027 已另有 Word 版式详情，本段不改它。OpenAPI 草案归后台，本轮不改 `spec/openapi/demo-v1.json`。

## 影响与分流

- 影响范围：生产模型、知识检索和已经决定的 MySQL 8。ISSUE-005 不因此关闭。FE-M0-T04 仍 blocked。
- 本轮不改运行代码，不加依赖。`httpx` 已在仓库。Fernet 使用 ISSUE-023 已批准的 `cryptography`，本轮不调用。
- AI-01 改为 in-review。真实端点验收未做，开发者不把 AI-01 标 done。
- [ISSUE-011](ISSUE-011.md) 已 closed。默认仍是演示替身。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| AI-01 | 记录用户决定并同步基线 | 本文件与两份设计 | 决定与真实端点验收分开 | in-review |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 选项覆盖对话模型、嵌入、重排、向量库、业务库和内网验证 | 已写入本文与 model-choice-2 的历史 |
| AC-02 | PostgreSQL 16 / pgvector 建议标明未采纳 | 用户决定的是 MySQL 8。向量库改为 RAGFlow 自带 |
| AC-03 | 用户确认端点放置、云端策略、嵌入、向量库和生产出网范围 | 2026-10-12 三项决定已登记。见 [核对](../docs/testing/2026-10-12-issue-010-decisions.md)。重排产品未选定 |
| AC-04 | 选定数据库之后才引入迁移工具 | 迁移工具已随 ISSUE-023 进入仓库。本 Issue 的关闭不新增依赖 |
| AC-05 | 业务库决定写明日期和来源 | 2026-10-12，user decision, relayed by PM。向量库决定另记于同日 |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。P030 已有「模型配置」页名。本轮不增加验收步骤，也不改任务计数 | `docs/PRD.md` | model-choice-3 / ISSUE-010 / 2026-10-12 | 已核对 |
| ROADMAP | 有影响。只改决定用词。任务计数留给 ISSUE-026，本轮不改数字 | `docs/ROADMAP.md` | model-choice-3 / ISSUE-010 / 2026-10-12 | 已核对 |
| ARCHITECTURE | 有影响。写明配置页与 RAGFlow，并标明尚未实现 | `docs/ARCHITECTURE.md` 当前实施段 | model-choice-3 / ISSUE-010 / 2026-10-12 | 已核对 |
| TASK_BOARD | 有影响。AI-01 改为 in-review | `docs/TASK_BOARD.md`、`docs/tasks/AI-M0.md` | model-choice-3 / ISSUE-010 / 2026-10-12 | 已核对 |
| PROJECT_STATUS | 有影响。进度改为决定已登记、端点未接通 | `docs/PROJECT_STATUS.md` | model-choice-3 / ISSUE-010 / 2026-10-12 | 已核对 |
| DOCUMENT_INDEX | 有影响。登记设计、核对和 ISSUE-028、ISSUE-029 | `docs/DOCUMENT_INDEX.md` | model-choice-3 / ISSUE-010 / 2026-10-12 | 已核对 |
| PROJECT_BRIEF | 有影响。只改「仍待决定」这句。任务计数不改 | `docs/PROJECT_BRIEF.md` 排期行 | model-choice-3 / ISSUE-010 / 2026-10-12 | 已核对 |

治理块保持 g1.1 / 2026-10-11 / ISSUE-007。`docs/reference/` 未改。

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | model-choice-1 / blocked | 已登记选项和建议。用户当时尚未决定 | 本文 |
| 2026-10-12 | model-choice-2 / blocked | 用户决定业务库为 MySQL 8。其余项当时仍待决 | 本文 |
| 2026-10-12 | model-choice-3 / closed | 用户决定配置页、RAGFlow 自带嵌入与向量库、生产生成仅内网。AI-01 改为 in-review。真实端点未验收 | [核对](../docs/testing/2026-10-12-issue-010-decisions.md) |

## 本地验收与后续合入发布

- 本地验收结论与日期：决定登记于 2026-10-12 完成。真实连接未执行。
- 验证方式：文档核对。没有连接内网或调用模型。
- 六份基线同步与互链复核：见上表和 [同步记录](../docs/governance/ISSUE-010-sync.md)。
- PR 状态：未创建。
- 合入提交与日期：未合入。
- 发布版本与日期：未发布。
