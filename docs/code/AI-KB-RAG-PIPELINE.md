为什么有这个文件：解释公司知识库同步与检索的代码结构和调用顺序。

它解决什么问题：让后续调参、换嵌入模型或拆同步进程的人知道索引在哪、谁触发同步、检索结果怎么被过滤。

# AI-KB-RAG-PIPELINE：代码解释

- 任务 AI-KB-RAG-PIPELINE；交付 [交付](../delivery/AI-KB-RAG-PIPELINE.md)；提交 `a6643f2`、`1640046`

## 模块

| 文件 | 职责 |
|---|---|
| `icg/infra/ragflow_client.py` | RAGFlow 1.0 HTTP 客户端 |
| `icg/domain/knowledge_base.py` | `desired_documents`（应入库清单）、`KnowledgeBaseService`（对账、状态、检索）、`KnowledgeEvidenceService`（适配证据候选 `collect` 与问答 `search`） |
| `icg/api/knowledge_base.py` | `/api/v1/knowledge-base/status|sync|search` |
| `icg/domain/library_orchestrator.py`、`snippet_publication.py` | 事务提交后调用 `knowledge_base.schedule` |
| `icg/domain/snippet_retrieval.py`、`infra/retrieval.py` | 片段匹配融合语义分 |
| `frontend/web/src/library/KnowledgeBasePanel.tsx`、`knowledge-base-core.ts` | 资料库页知识库面板 |

## 索引

`state.service_stores["kb_index"][company_id] = {dataset_id, entries, last_sync_at, last_error, pending_deletes}`；`entries[key]`，key 为 `library:<id>` 或 `snippet:<id>`，记录 `revision`、`content_hash`、`document_id`、`status`（parsing/synced/failed）、`chunk_count`、`message`。随 BE-WORKFLOW-DURABILITY 持久化。

## 同步顺序（`sync_company`）

1. 读状态，取客户端（公司配置启用且有 API Key；否则读 `ICG_RAGFLOW_BASE_URL` + `ICG_RAGFLOW_API_KEY`；都没有即空操作）。
2. 确保数据集；全量时列举远端文档做漂移修复。
3. 对 `desired_documents` 中新增、内容哈希变化或上次失败的条目：上传 Markdown（标题 + 类别/有效期 + 正文）→ PATCH 元数据 → 触发解析；旧文档进待删。
4. 不再需要的条目：删除文档、移出索引。
5. 一次仓储事务写回索引和片段 `kb_sync_status`；随后 `refresh_status` 查询解析中的文档。

## 检索顺序（`search`）

1. 只取索引中 `synced` 且类别匹配的文档 id，作为 `document_ids` 传给 `/api/v1/retrieval`（阈值 `ICG_KB_SIMILARITY_THRESHOLD`，关键词权重 `ICG_KB_KEYWORDS_WEIGHT`，可选 `ICG_KB_RERANK_ID`）。
2. 分块 → 索引条目；丢弃不在索引中、数据集不符的分块。
3. `_live` 实时复核资料/片段（公司、确认、版本、有效期、受限授权）。
4. 按资料聚合，每条最多两段，按最高相似度排序。

## 测试

`tests/backend/fake_ragflow_v1.py` 按实测 1.0 行为实现进程内假服务（`httpx.MockTransport`），可切换异步解析、上传/删除/检索失败；`tests/backend/test_knowledge_base.py` 13 项 + 1 项真实联调（默认跳过）。
