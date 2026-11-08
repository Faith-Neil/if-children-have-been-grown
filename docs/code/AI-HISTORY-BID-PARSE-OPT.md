为什么有这个文件：解释历史标书解析优化相关代码入口与约束。

它解决什么问题：接手者能从管道 DSL、部署二次校验、分块元数据与试查对账一路跟到真机验收单测。

# AI-HISTORY-BID-PARSE-OPT 代码说明

## 入口

| 模块 | 路径 | 职责 |
|---|---|---|
| 管道 DSL | `backend/bid-core/icg/infra/ragflow_pipelines.py` | `SCHEME_HEADING_GROUP`、`history_bid` profile、`build_dsl`（flatten/remove_toc、questions.enabled=false） |
| 部署 | `backend/bid-core/icg/domain/knowledge_base.py` `ensure_pipeline` | 指纹不一致则升级；history/materials 再读远端，问法仍开则强制重写 DSL |
| 试查 | `backend/bid-core/icg/domain/kb_admin.py` `retrieval_test` | 检索前 `refresh_status`，避免本地 parsing 挡检索 |
| 分块 API | `backend/bid-core/icg/infra/ragflow_client.py` `list_chunks` | 统一 content/keywords/questions，并透出 metadata |
| 验收 | `tests/backend/test_history_bid_parse_acceptance.py` | 真机门控；金标 `fixtures/history-bid-golden/` |

## 数据流

上传 history 原件 → RAGFlow Parser（表格并入正文）→ Title Chunker → Extractor（关键词+分类，无问法）→ Indexer → 本地索引 refresh → kb-admin 试查 / 写作检索。

## 约束

- 真机三件套未齐时验收用例 skip；密钥不入库
- `materials` 与 `tender` 行为本轮仅共用工具函数修复（问法二次关闭、heading 组）
- 最高状态 in-review；done 由 PM 标
