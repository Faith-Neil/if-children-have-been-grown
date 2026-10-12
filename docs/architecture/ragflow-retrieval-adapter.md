为什么有这个文件：把检索接到 RAGFlow 的官方 HTTP 接口，而不是再选一个向量库。

它解决什么问题：避免把内存检索骨架写成已经连通，也避免在设计里发明 RAGFlow 没有的路径。

# RAGFlow 检索适配器

日期：2026-10-12。关联 [ISSUE-010](../../issues/ISSUE-010.md)（closed）、[ISSUE-029](../../issues/ISSUE-029.md)（closed）、[ISSUE-016](../../issues/ISSUE-016.md)（closed）/ [AI-03](../tasks/AI-M0.md#ai-03)（done）。依据是公开发布的 HTTP API：<https://ragflow.io/docs/http_api_reference>。按该页正文及其 “Migrate to 1.0” 说明书写，不钉某次 Git 提交。1.0 正在迁到 Go 后端；下表用迁移说明之后仍然列出的路径。

本文件只设计。不新增依赖。HTTP 使用仓库里已有的 `httpx==0.28.1`。不改 `EvidenceCandidateService` 的代码。内网放置已写在 [部署草案](../operations/intranet-deployment-plan.md)：基址 `ICG_RAGFLOW_BASE_URL`，密钥 `ICG_RAGFLOW_API_KEY`，只从环境注入。浏览器不直连 RAGFlow。

## 决定落到哪一层

嵌入模型和向量库存放、切块都在 RAGFlow 内部配置。本仓库不选 Milvus、Qdrant、Elasticsearch 或 pgvector，也不保存切块向量。检索层以后实现一个适配器，放在 ISSUE-016 已有的 `EvidenceCandidateService` 后面。

`EmbeddingProvider`、`RerankProvider`、`VectorStore` 仍是进程内替换口。AI-03 的内存实现已为 done，仍不进入 `create_app`。适配器尚未实现。

重排已决定：使用 RAGFlow 自带的重排器，重排模型在 RAGFlow 内配置（用户 10-12 14:34 确认）。检索调用 `POST /api/v1/retrieval` 上的 `rerank_id`。本仓库不增加重排依赖。ISSUE-029 已 closed。适配器仍未实现。

## 认证与错误

请求头 `Authorization: Bearer <API_KEY>`。RAGFlow 正文里 `code: 0` 表示它自己的成功。这不是本仓库的 `V1Error`。适配器要把连接失败、非成功业务码和超时变成检索失败原因，不能把空列表说成检索成功。密钥不进日志、错误体或堆栈。

同一公司的文档必须使用同一个嵌入模型，否则不能放进同一次检索。公司隔离靠我们保存的 dataset id：RAGFlow 的令牌不是我们的 `company_id`。适配器只把该公司名下的 dataset id 放进 `dataset_ids`。

## 官方路径

下列路径均相对于 RAGFlow 基址。

| 用途 | 方法与路径 | 要点 |
|---|---|---|
| 创建数据集 | `POST /api/v1/datasets` | 正文含 `name`、`embedding_model` 等。1.0 用 `parser_id`，不再用旧的 `chunk_method` |
| 列出数据集 | `GET /api/v1/datasets` | 带查询参数 |
| 上传文档 | `POST /api/v1/datasets/{dataset_id}/documents` | 查询 `type=local`（默认，multipart `file`）、`type=web` 或 `type=empty`。响应 `run: UNSTART` |
| 列出文档与状态 | `GET /api/v1/datasets/{dataset_id}/documents` | 可带 `run`。`run` 取 `UNSTART`/`0`、`RUNNING`、`CANCEL`、`DONE`/`3`、`FAIL`/`4`、`SCHEDULE`。另有 `progress`，0 到 1 |
| 解析（内置流水线） | `POST /api/v1/datasets/{dataset_id}/chunks` | 必填 `document_ids`，可选 `user_id`。成功正文 `{"code":0}` |
| 摄入流水线 | `POST /api/v1/documents/ingest` | 数据集走摄入流水线时用这条，不用上一行。正文 `doc_ids`，`run` 为 `"1"` 开始、`"2"` 取消 |
| 停止解析 | `DELETE /api/v1/datasets/{dataset_id}/chunks` | |
| 检索 | `POST /api/v1/retrieval` | 必填 `question`、`dataset_ids`。可选见下节 |
| 健康 | `GET /api/v1/system/healthz` | 迁移表中的新路径。旧的 `GET /v1/system/healthz` 在 Go 后端已去掉 |

检索可选字段，按该文档的默认值：`document_ids`，`page`，`page_size`（默认 30），`similarity_threshold`（默认 0.2），`keywords_similarity_weight`（默认 0.7，向量权重是 1 减该值），旧名 `vector_similarity_weight`（两者都传时必须加起来为 1），`knn_top_k`（默认 1024；`top_k` 是已废弃的别名），`knn_num_candidates`（只对 Elasticsearch 生效），`rerank_candidates_count`（默认 64），`rerank_id`，`keyword`，`highlight`，`metadata_condition`，`use_kg`，`include_knowledge_compilation`。

## 与 T078 同步状态

T078 的 `kb_sync_status` 取值是 `unsynced`、`synced`、`failed`、`blocked`。建议映射：

| RAGFlow `run` | `kb_sync_status` |
|---|---|
| `UNSTART`、`SCHEDULE` | `unsynced` |
| `RUNNING` | `unsynced`。不写成已同步 |
| `DONE` | `synced` |
| `FAIL` | `failed` |
| `CANCEL` | `failed` |

`CANCEL` 不映射成 `blocked`。T078 的 blocked 发布是另一条路径：返回 200，响应里带原因，且不改已存状态。RAGFlow 解析被取消或失败是之后的同步状态，不是那条 200。把取消映射成 `blocked` 会把这两种含义混在一起。

## 证据候选

路径 A 仍是已确认的资料规则，不经过 RAGFlow。路径 B 改为调用检索接口，再按公司过滤我们保存的 dataset。路径 C 的历史投标同样只查该公司的 dataset，且仍不可附着。ISSUE-016 QA P3：当前路径 C 不按查询词过滤，实现 RAGFlow 适配器时再改。B 或 C 失败时保留 A 并记录原因，与现在的 `EvidenceCandidateService` 一致。知识库关闭时也不调用 RAGFlow。本轮不改检索代码。

## CI 与风险

CI 使用假的 RAGFlow 服务，记录实际收到的 `Authorization` 和 `base_url`。连真实内网 RAGFlow 的测试必须显式打开，默认跳过。

风险：Go 与旧 Python 路径不一致时以发布文档的迁移说明为准；`parser_id` 与 `chunk_method` 不能混用；`knn_num_candidates` 只适用于 Elasticsearch，而 Elasticsearch 不是我们的选型；我们不拥有切块向量，不能在 MySQL 里复原它们；公司隔离若只依赖 RAGFlow 令牌就会串公司，所以 dataset id 必须记在我们这边。
