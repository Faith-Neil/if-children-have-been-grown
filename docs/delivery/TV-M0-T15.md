为什么有这个文件：记录 ISSUE-051 后端两层矩阵与实质生成交付。

# TV-M0-T15 交付

| 项 | 内容 |
|---|---|
| 状态 | in-review。建议 PM 在 QA/PD 签署后再标 done |
| Issue | [ISSUE-051](../../issues/ISSUE-051.md) |
| 代码 | [TV-M0-T15](../code/TV-M0-T15.md) |

## 实际变更

- `technical_response_plan.py`：Requirement enrich、ResponseTask 合并主题、短标题目录、计划校验。
- `apply_technical_outline` 改为任务驱动主题目录。
- `write_volume` / `section_query`：按任务+要求+检索目标生成；无 RAG 标待确认，不再因 writable=0 整节空「待补」。

## 证据

- `pytest tests/backend/test_technical_response_plan.py tests/backend/test_technical_rag.py tests/backend/test_technical_quality.py`
