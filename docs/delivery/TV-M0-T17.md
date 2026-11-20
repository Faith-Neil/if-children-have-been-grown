为什么有这个文件：记录技术服务方案精简主路径 A 组（后端）交付。

# TV-M0-T17 交付

| 项 | 内容 |
|---|---|
| 状态 | in-review。建议 PM 在 QA/PD 签署后再标 done |
| Issue | [ISSUE-053](../../issues/ISSUE-053.md) |
| 代码 | [TV-M0-T17](../code/TV-M0-T17.md) |

## 实际变更

- 模型读标改为输出技术需求、评分规则（评分项、分值、评分标准、得分要点）、废标三张清单；旧 `items` 格式照收。
- 新增 `tender_digest`：T-01 / S-01（要点 S-01-1）/ R-01 编号，原文与页码可追溯，要求行回写 `digest_id`。
- 有本地模型时一次调用拟 1～4 级目录并挂要点；漏挂要求补入「其他服务承诺」；模型两次失败或挂载不足一半时回落旧规则目录并标 `rule_fallback`。
- 正文提示新增「评分标准」与「废标清单（全文不得违反）」；检索词追加至多 2 条挂载要点；历史标书与资料库照旧都检索。

## 验收

- `python3 -m pytest tests/backend/test_technical_digest.py`：9 passed（含评审修复：重复条目合并评分信息、畸形目录回落、回落不再调模型、废标清单不截断）。
- `pytest tests/backend -k "technical or tender or outline or volume or coverage"`：313 passed，4 failed；同 4 例在改动前的分支上同样失败（`test_technical_sources.py` 旧主题目录断言），非本次引入。
- 限制：只用假模型；真实内网 Qwen / RAGFlow 未验证。

## 同步记录

| 文档 | 处理 |
|---|---|
| PRD / ROADMAP / ARCHITECTURE | 无改动：产品范围已由仅技术标决策收窄，本次只换技术分册内部编排 |
| TASK_BOARD / 任务卡 / Issue | 新增 TV-M0-T17、ISSUE-053 |
| DOCUMENT_INDEX | 登记 Issue、设计、审计、交付、代码说明 |
| PROJECT_STATUS | 追加一行进度 |
