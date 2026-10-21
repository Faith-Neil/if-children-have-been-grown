为什么有这个文件：把 RAGFlow 检索适配器的实现从已关闭的设计里拆出来。

它解决什么问题：避免把 ISSUE-029 的设计确认写成客户端已经接通，也避免零命中被记成一次成功的空检索。

# ISSUE-037：RAGFlow 检索适配器实现

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-037 |
| 类型 | change |
| 优先级 | P1 |
| 状态 | in-progress |
| 登记日期 | 2026-10-13 |
| 最后更新日期 | 2026-10-16 |
| revision | ragflow-client-1 |
| 关联 Task | [AI-04](../docs/tasks/AI-M0.md#ai-04)、[AI-05](../docs/tasks/AI-M0.md#ai-05)、[AI-06](../docs/tasks/AI-M0.md#ai-06) |
| 关联 PR | 未创建 |
| 本地验收 | AI-04 夹具已跑。AI-05 客户端单测 25 项已跑通。真实 RAGFlow 未连接。Issue 不标 closed |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [AI-04 交付](../docs/delivery/AI-04.md)、[AI-05 交付](../docs/delivery/AI-05.md)。AI-06 尚未建立交付 |
| 代码 / 流程解释 | [AI-04 代码解释](../docs/code/AI-04.md)、[AI-05 代码解释](../docs/code/AI-05.md) |
| 验证记录 | [假 RAGFlow 核对](../docs/testing/2026-10-13-issue-037-fake-ragflow.md) |

## 现象与证据

[ISSUE-029](ISSUE-029.md) 已 closed。设计在 [RAGFlow 检索适配器](../docs/architecture/ragflow-retrieval-adapter.md)。内存口是 [AI-03](../docs/tasks/AI-M0.md#ai-03) / [ISSUE-016](ISSUE-016.md)，已 done。AI-04 夹具已完成，AI-05 只读检索客户端已实现，`retrieval.py` 尚未接入客户端。

本 Issue 只做实现。设计不重开。路径、字段和健康检查以该设计和公开发布的 HTTP API 为准：<https://ragflow.io/docs/http_api_reference>。产品字段以 [PRD v1.8](../docs/reference/product/prd-mvp-v1.8.md) 与 [字典 v1.9](../docs/reference/product/kb-data-dictionary-v1.9.md) 为准，不另造字段。HTTP 使用已有的 `httpx==0.28.1`。不加依赖。

重排使用 RAGFlow 自带的重排器，调用检索接口的 `rerank_id`。重排模型在 RAGFlow 内配置。本仓库不增加重排依赖。

数据集的创建、上传、解析和 `kb_sync` 不在本 Issue。适配器只消费调用方注入的 `dataset_ids`。公司隔离靠我们保存的 dataset id，不靠 RAGFlow 令牌。

零命中不是成功的空列表。`code` 为 0 且 `data.chunks` 为空时，后续客户端必须把该路径记为跳过。

## 影响与分流

- 影响范围：以后的路径 B/C。路径 A 仍不经过 RAGFlow。B 或 C 失败，或零命中时，保留 A 并记录跳过原因。
- AI-04 CI 假 RAGFlow 夹具已为 in-review。
- AI-05 只读检索客户端已实现为 in-review，位于 `backend/bid-core/icg_demo/ragflow_client.py`，不改动 `retrieval.py`。
- AI-06 接到 `EvidenceCandidateService`，当前为 planned。
- 知识库关闭时不调用 RAGFlow。该行为留在 AI-06，与现在的内存口一致。
- 依赖：设计 ISSUE-029 已 closed。内存口 AI-03 已 done。无新依赖。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| AI-04 | CI 假 RAGFlow，记录 Authorization 与实际 base_url | `tests/backend/fake_ragflow.py` | AC-01、AC-02、AC-03 | in-review |
| AI-05 | 只读检索客户端，消费注入的 dataset_ids 与 rerank_id | `backend/bid-core/icg_demo/ragflow_client.py` | AC-04、AC-05、AC-06 | in-review |
| AI-06 | 路径 B/C 改走客户端；零命中记为跳过 | `backend/bid-core/icg_demo/retrieval.py` | AC-06、AC-07 | planned |

本 Issue 为 in-progress。AI-04 与 AI-05 为 in-review。不标 closed。未合入，未发布。

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | CI 假服务监听 `127.0.0.1` 临时端口，接受 `POST /api/v1/retrieval`，可选 `GET /api/v1/system/healthz`，并记下 `Authorization: Bearer` 与实际 `base_url` | 已实现。见 [核对](../docs/testing/2026-10-13-issue-037-fake-ragflow.md) |
| AC-02 | 夹具能返回带 chunks 的 `{"code":0,"data":...}`、空 chunks、非 0 业务 `code` 和 HTTP 错误。空 chunks 仍是 `code` 0 的官方信封 | 已实现。产品映射不在本夹具 |
| AC-03 | 真实连接默认跳过，只有 `ICG_RUN_REAL_RAGFLOW_TESTS=1` 才运行。不加依赖，不改 `backend/bid-core` | 已实现。默认 1 项跳过。`requirements.txt` 与 `retrieval.py` 未改 |
| AC-04 | 零命中（`code` 0 且 chunks 为空）记为跳过，不记为成功的空候选列表 | 已实现。`RagflowRetrievalClient` 映射为 `skipped=True`、`skip_reason='zero hits'`。见 [AI-05 交付](../docs/delivery/AI-05.md) |
| AC-05 | `RagflowRetrievalClient` 用已有 httpx 调用检索接口，只传入注入的 `dataset_ids` 与 `rerank_id`。不建数据集，不改 `kb_sync` | 已实现。见 [AI-05 代码解释](../docs/code/AI-05.md) |
| AC-06 | 非 0 业务码、HTTP 错误和超时变成检索失败，不能当成命中 | 已实现。映射为 `RagflowBusinessError`、`RagflowHttpError`、`RagflowTimeoutError`。见 [AI-05 交付](../docs/delivery/AI-05.md) |
| AC-07 | 路径 B/C 改走客户端。失败或零命中时保留路径 A 并记录原因。路径 C 仍不可附着，并按查询词过滤。知识库关闭时不调用 RAGFlow | 未实现。AI-06 planned。本轮不改 `retrieval.py` |

未完成的 AC-07 不能写成通过。

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。不新增页面验收，不改任务计数 | `docs/PRD.md` | ragflow-client-1 / ISSUE-037 / 2026-10-16 | 已核对，未改 |
| ROADMAP | 无影响。不改任务计数，不改里程碑快照 | `docs/ROADMAP.md` | ragflow-client-1 / ISSUE-037 / 2026-10-16 | 已核对，未改 |
| ARCHITECTURE | 无影响。运行时模块未变，适配器接线在 AI-06 | `docs/ARCHITECTURE.md` | ragflow-client-1 / ISSUE-037 / 2026-10-16 | 已核对，未改 |
| TASK_BOARD | 有影响。AI-05 更新为 in-review | `docs/TASK_BOARD.md`、`docs/tasks/AI-M0.md` | ragflow-client-1 / ISSUE-037 / 2026-10-16 | 已核对 |
| PROJECT_STATUS | 有影响。写明客户端已提交 in-review，接线留待 AI-06 | `docs/PROJECT_STATUS.md` | ragflow-client-1 / ISSUE-037 / 2026-10-16 | 已核对 |
| DOCUMENT_INDEX | 有影响。登记 AI-05 交付与代码解释 | `docs/DOCUMENT_INDEX.md` | ragflow-client-1 / ISSUE-037 / 2026-10-16 | 已核对 |
| PROJECT_BRIEF | 无影响。不改任务计数 | `docs/PROJECT_BRIEF.md` | ragflow-client-1 / ISSUE-037 / 2026-10-16 | 已核对，未改 |

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-13 | ragflow-fixture-1 / in-progress | AI-04 夹具已提交 in-review。AI-05、AI-06 为 planned。不标 closed。不改运行代码 | [核对](../docs/testing/2026-10-13-issue-037-fake-ragflow.md) |
| 2026-10-16 | ragflow-client-1 / in-progress | AI-05 客户端已完成并提交 in-review，单测 25 passed 1 skipped。AI-06 为 planned。不标 closed | [AI-05 交付](../docs/delivery/AI-05.md) / AI & RAG Specialist |

## 本地验收与后续合入发布

- 本地验收：假服务 9 项通过，客户端单测 25 项通过，真实健康检查默认跳过。没有连接内网 RAGFlow。
- 未覆盖：真实数据集检索、路径 B/C 接线（留待 AI-06）。
- 六份基线已按上表核对。PRD、ROADMAP、PROJECT_BRIEF 的任务计数未改。
- PR：未创建。合入：未合入。发布：未发布。
