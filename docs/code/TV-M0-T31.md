为什么有这个文件：解释 TV-M0-T31 条款清洗与假负偏离加固的代码入口、调用顺序和边界。

# TV-M0-T31 代码说明

## 入口与调用顺序

1. `backend/bid-core/icg/domain/technical_digest.py::build_digest` 在生成 T/S/R 三张清单前调用 `clean_technical_requirements`。
2. `backend/bid-core/icg/domain/technical_clause_cleaning.py` 对每条 `technical_clause` 做幂等清洗：
   - `fragment_signals` 识别悬空标点、未闭合括号、残缺词尾、表格噪声、短无动作、标题序号；
   - `source_truncation_signals` 对照所在页紧凑原文识别缺头/缺尾；
   - `complete_fragment_text` 先quote同源行、后页内锚定补全，`_valid_completion` 拒绝交叉引用、合同空白、未闭合或不完整候选；
   - `row_non_tech_category/non_tech_category` 将资格、商务、付款、限价、格式、合同模板等条款分到 `non_technical`；
   - 无法恢复且不完整的条款标 `fragment_filtered`，不删除，审计样本写入 `workflow['technical_clause_cleaning']`。
3. `technical_digest._rows`、`technical_outline`、`technical_response_plan`、`technical_matrix`、`technical_volume` 与 `matrix` 统一排除 `EXCLUDED_SCOPES`。

## 假负偏离清理

`clear_stale_judgment_fields` 只清理系统来源（`history/retrieval_failed/draft_failed/no_evidence` 或空）的响应和偏离字段；人工编辑或已确认行保留。这样历史矩阵链路残留在残句/格式条款上的假「负偏离」不会继续阻断导出，同时不覆盖人工判断。

## 边界

- 不删除条款行，过滤与分流都可审计。
- 页内补全只拼接原文，不让模型补句子。
- 序号标题独占一行时不跨行拼接；标题与正文同一行且有冒号时才允许行内补全。
- 规则分流保持保守，服务期、SLA、巡检、培训、运维能力仍按技术条款处理。

## PR #57 Review 修复轮补充

- 残句补全增加锚点数字完整性校验，剥条款编号只在确认的条款边界发生；`0.5小时`、`2小时` 等正文时限不会被误裁。
- 非技术分流规则收敛到投标人/供应商/资格语境，`跨行支付清算接口`、真实 SLA 与合同履行过程中的技术义务不再被单词误伤；评分表元数据有效的短语评分点不按短残句过滤。
- R09 服务期核验消费同一份范围判定，跳过已分流付款条款；偏离表优先使用源文本校验后的补全条款。
- 覆盖视图新增 `filtered_clause_rows` 只读契约，前端底部默认折叠展示非技术与残句过滤原因。
