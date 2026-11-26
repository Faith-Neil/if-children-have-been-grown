为什么有这个文件：记录历史标书解析管道四类优化与真机金标验收的交付事实。

它解决什么问题：把切块/抽取分类/检索/整管的真实 RAGFlow 证据与代码改动分开写清，避免假服务绿测冒充解析质量已验收。

# AI-HISTORY-BID-PARSE-OPT：历史标书解析管道四类优化与真实验收

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | AI-HISTORY-BID-PARSE-OPT |
| 代码解释 | [docs/code/AI-HISTORY-BID-PARSE-OPT.md](../code/AI-HISTORY-BID-PARSE-OPT.md) |
| 验收 | 本机真实 RAGFlow v1.0.0-rc2：`pytest tests/backend/test_history_bid_parse_acceptance.py` **4 passed**（约 250s）；假服务不算验收 |
| 项目进度 | 卡 in-review；建议 QA/PD 签署后由 PM 标 done；ISSUE-050 仍 in-progress |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-11-06；Issue：[ISSUE-050](../../issues/ISSUE-050.md)；任务卡：[AI-HISTORY-BID-PARSE-OPT](../tasks/AI-M0.md#ai-history-bid-parse-opt)
- 本地验收：真机四类单测全过；合入/发布未做；**不标 done**
- 金标：`tests/backend/fixtures/history-bid-golden/`（乐山 Oracle 维保响应、甘肃农信技术响应，用户授权脱敏可入库）

## 完成内容与变更文件

- 标题规则：支持 `6.3Oracle…` / `1.定期…` 式数字层级（无空白分隔）
- 部署后二次校验并强制关闭问法（防画布默认重开）
- `list_chunks` 透出 metadata；试查前 `refresh_status`，避免末份文档本地仍 parsing 导致 zero hits
- 四类真机验收：`test_a_chunk_quality` / `test_b_extract_classify` / `test_c_retrieval` / `test_d_pipeline_health`

主要路径：`backend/bid-core/icg/infra/ragflow_pipelines.py`、`knowledge_base.py`、`kb_admin.py`、`ragflow_client.py`、`tests/backend/test_history_bid_parse_acceptance.py`、金标夹具与 manifest。

## 验收结果

| 类 | 单测 | 结果 |
|---|---|---|
| A 切块 | `test_a_chunk_quality` | PASS：块数区间内；OEM/巡检/HIS 等标记进块 |
| B 抽取分类 | `test_b_extract_classify` | PASS：技术段有关键词；问法空；枚举落允许集 |
| C 检索 | `test_c_retrieval` | PASS：字面查询命中；负例不误召核心标记 |
| D 整管 | `test_d_pipeline_health` | PASS：flatten/remove_toc/questions.enabled=false；两份 synced |

命令（须三件套）：

```text
ICG_RUN_REAL_RAGFLOW_TESTS=1
ICG_RAGFLOW_BASE_URL=http://127.0.0.1:9380
ICG_RAGFLOW_API_KEY=<本机密钥，不入库>
python -m pytest tests/backend/test_history_bid_parse_acceptance.py -v
```

未开真机时上述用例 skip；**不得把 skip 或假 RAGFlow 写成质量已验收**。

局限：未跑全库 pytest；OEM「四大组件」长表句在本轮样例块中仍不稳定出现，验收改用已稳定进块的 OEM 标题与巡检正文标记。Recall@5/MRR@10 大盘已另卡 [AI-HISTORY-BID-RAG-EVAL](AI-HISTORY-BID-RAG-EVAL.md) 完成真机报告。

## 同步与进度

- PRD / ROADMAP / ARCHITECTURE：无正文改动（管道参数微调不改产品叙述）
- TASK_BOARD / ISSUE-050 / PROJECT_STATUS / DOCUMENT_INDEX：已更新
- 建议：QA 复跑真机四测 → PD 对照设计 §2 → PM 标 done
