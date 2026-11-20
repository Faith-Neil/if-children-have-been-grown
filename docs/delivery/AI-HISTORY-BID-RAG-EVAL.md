为什么有这个文件：记录历史标书 Recall@5 / MRR@10 真机大盘的交付事实。

它解决什么问题：把五份脱敏金标、评测脚本与真实 RAGFlow 指标写清，避免假服务或仅切块验收冒充检索质量。

# AI-HISTORY-BID-RAG-EVAL：历史标书 Recall@5 / MRR@10 大盘

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | AI-HISTORY-BID-RAG-EVAL |
| 代码解释 | [docs/code/AI-HISTORY-BID-RAG-EVAL.md](../code/AI-HISTORY-BID-RAG-EVAL.md) |
| 验收 | 真机 `python scripts/rag_eval_history_bid.py --live` 退出 0；报告 [rag-eval-history-bid-v1.md](../testing/rag-eval-history-bid-v1.md)；5/5 解析成功 |
| 项目进度 | 卡 in-review；建议 QA/PD 后 PM done；不自动改默认阈值 |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-11-06；Issue：[ISSUE-050](../../issues/ISSUE-050.md)
- 本地验收：真机跑盘完成；合入/发布未做；**不标 done**

## 完成内容

- 金标五份：`tests/backend/fixtures/history-bid-golden/`（乐山、甘肃、泸天化、贵阳银行 2025/2024）
- 查询集：`tests/rag_eval/golden_history_bid_v1.json`（37 条：字面/同义/负例）
- 脚本：`scripts/rag_eval_history_bid.py`（history_bid 二进制摄入；一次检索算 Recall@5 与 MRR@10）
- 报告：`docs/testing/rag-eval-history-bid-v1.md`

## 真机摘要

| 阈值 | 关键词权重 | literal R@5 | literal MRR@10 | paraphrase R@5 | paraphrase MRR@10 | 负例误召回 |
|---|---|---|---|---|---|---|
| 0.45 | 0.3 | 1.0 | 0.932 | 1.0 | 0.883 | 0.8 |
| 0.45 | 0.5 | 0.909 | 0.886 | 0.4 | 0.35 | 0.0 |

写作侧更看重召回时优先参考 0.45/0.3；要压负例误召回可看 0.45/0.5。本轮**不改写**公司默认阈值。

## 同步

- PRD/ROADMAP/ARCHITECTURE：无正文改动（评测报告不改产品叙述）
- TASK_BOARD / ISSUE-050 / PROJECT_STATUS / DOCUMENT_INDEX：已更新
