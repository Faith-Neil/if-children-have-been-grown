为什么有这个文件：解释历史标书检索大盘脚本入口。

它解决什么问题：接手者能从金标夹具、history_bid 摄入到 Recall@5/MRR@10 报告一路跟通。

# AI-HISTORY-BID-RAG-EVAL 代码说明

## 入口

| 路径 | 职责 |
|---|---|
| `scripts/rag_eval_history_bid.py` | 真机/离线评测；`--live` 上传五份 docx 绑 `history_bid` |
| `tests/rag_eval/golden_history_bid_v1.json` | 文档 id 与查询金标 |
| `tests/backend/fixtures/history-bid-golden/` | 脱敏原件 + `manifest.json` |

## 指标

一次 `retrieve` 取文档去重排名；`recall@5` 看前 5，`mrr@10` 看前 10。负例 `relevant=[]`，统计误召回率。

## 约束

- 离线模式用短合成正文冒烟，**不算质量验收**
- 密钥仅环境变量；临时数据集默认删除（`--keep` 可留）
