为什么有这个文件：记录公司知识库（RAGFlow）同步与检索链路的交付。

它解决什么问题：此前“知识库同步”只是一次性手动上传、片段同步结果是伪造的，生产检索从未接通；这里说明现在的真实能力、验证方式与未完成项。

# AI-KB-RAG-PIPELINE：公司知识库同步与检索交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | AI-KB-RAG-PIPELINE |
| 代码解释 | [代码说明](../code/AI-KB-RAG-PIPELINE.md) |
| 验收 | 进程内 RAGFlow 1.0 假服务 13 项通过；后端全量内存模式 879 passed；MySQL 下知识库用例通过；前端 289 pass、e2e 15/16（失败项为既有 ISSUE-042）。真实 RAGFlow 质量评测待隧道恢复（AI-KB-RAG-EVAL） |
| 项目进度 | in-review |
<!-- task-delivery:end -->

## 关联与状态

- 日期 2026-10-28；Issue [ISSUE-043](../../issues/ISSUE-043.md)、[ISSUE-037](../../issues/ISSUE-037.md)；任务卡 [AI-KB-RAG-PIPELINE](../tasks/AI-M0.md#ai-kb-rag-pipeline)
- 提交 `a6643f2`、`1640046`；[PR #6](https://github.com/Faith-Neil/if-children-have-been-grown/pull/6)
- 依据：PRD v1.8 原则 1（零虚构）、§5.7（证据挂接）、B5/B6（自建 RAGFlow、数据不出内网）

## 完成内容

1. **客户端对齐 RAGFlow 1.0**（实测 v1.0.0-rc2）：建库必须 `parse_type`；文档状态 `ingestion_status`；`?id=` 过滤；PATCH 元数据；DELETE 文档；检索支持 `document_ids`、阈值、关键词权重、`metadata_condition`；不走系统代理。
2. **同步（对账）**：每家公司一个数据集 `{company_id}::icg-library`。只同步“已确认且未过期”的资料（长期有效除外）和“已发布”片段；资料改版重传并删除旧文档；撤销确认、驳回、过期即删除；全量同步修复漂移（RAGFlow 里被手工删的重传、遗留文档清掉）；删除失败的旧文档记入待删并重试。资料保存、片段发布后自动后台同步，网络调用不在事务内，失败不影响保存。
3. **检索**：只在索引登记的当前文档里检索（`document_ids` 过滤），命中按资料聚合，并按 DemoState 实时复核公司、确认状态、版本、有效期和受限资料授权，任一不符即丢弃。历史标书与“仅供参考”资料只作参考；命中引用写 `[片:资料id]`，**不是** `[证]`，要成为证据仍须人挂到响应矩阵。
4. **接入**：章节生成上下文（路径 B/C 候选）、问答卡、编辑器 AI 依据、方案片段匹配（语义分只抬不压）。
5. **不再伪造**：片段 `/sync` 只有在知识库确认解析完成才返回 synced；未配置 RAGFlow 时 `synced=false`。生产代码中的 `[[sync-fail]]` 测试钩子已删除。
6. **接口与界面**：`GET /api/v1/knowledge-base/status`、`POST .../sync`、`POST .../search`；资料库页新增知识库面板（覆盖率、失败原因、立即同步、刷新解析状态）；片段页“同步失败”筛选值与后端统一为 `failed`。
7. **评测工具**：`scripts/rag_eval.py` + 合成金标集 `tests/rag_eval/golden_v1.json`（21 篇、32 条查询：字面、同义改写、负例），扫描阈值与关键词权重，输出 recall@k、MRR、负例误召回。

## 验收结果

| 验收点 | 结果 | 证据 |
|---|---|---|
| 确认资料入库、可按资料 id 检索、元数据正确 | 通过 | `test_confirmed_library_item_is_synced_and_retrievable_by_source_id` |
| 待审资料不入库；过期不入库、长期有效入库、他司隔离 | 通过 | `test_pending_items_never_enter_the_knowledge_base`、`test_expired_items_are_not_indexed` |
| 改版替换文档，旧版本不被召回 | 通过 | `test_revision_change_replaces_document_and_old_version_is_not_recalled` |
| 撤销确认后删除；索引滞后时实时复核过滤；删除失败重试 | 通过 | `test_unconfirmed_item_is_removed_and_stale_index_is_filtered_live` |
| 历史标书仅参考；受限资料需授权 | 通过 | `test_history_items_are_reference_only`、`test_restricted_items_need_permission` |
| 异步解析、解析失败、上传失败与重试 | 通过 | `test_async_parsing_reports_parsing_until_refresh`、`test_parse_failure_and_upload_failure_are_recorded_and_retried` |
| 漂移修复 | 通过 | `test_full_sync_repairs_drift_between_index_and_ragflow` |
| 片段同步状态真实 | 通过 | `test_snippet_publish_sync_reflects_real_status`、`test_sync_without_knowledge_base_never_claims_synced` |
| 生成上下文拿到 [片] 候选而非 [证] | 通过 | `test_generation_context_gets_knowledge_candidates_as_pian_not_zheng` |
| 真实 RAGFlow 往返 | 待执行 | `test_live_ragflow_sync_and_search_round_trip`（需 `ICG_RUN_REAL_RAGFLOW_TESTS=1`）；隧道 2026-10-28 19:00 起不可达（Cloudflare 1033） |

## 风险与后续

- **检索质量未在真实 RAGFlow 上量化**（AI-KB-RAG-EVAL）：阈值 0.2、关键词权重 0.7 为暂定值；之前实测表格类分块相似度约 0.21，阈值可能偏高，需评测后定。
- 生成上下文目前用“章节标题 + 写作要点 + 条款”拼成一条查询，条款多时会稀释；评测后再决定是否按条款多路查询。
- 文档解析排队：RAGFlow 单 worker 时大文件会阻塞小文档解析，面板会显示“解析中”。
- 多进程部署时同步锁只在进程内，漂移修复可能误删另一进程刚上传的文档（下次对账会自愈）；生产建议单个同步进程。
- 嵌入模型：开发期使用云端 gemini-embedding-001（用户已认可）；生产须改内网嵌入模型并全量重建数据集。
