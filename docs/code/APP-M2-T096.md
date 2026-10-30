# 代码说明：APP-M2-T096 R19 关联投标冲突

为什么有这个文件：说明冲突的匹配口径、拦截点、确认记录的作用范围与检查规则。

它解决什么问题：以后补集团归属、标段字段或改匹配规则时，知道该改哪里，哪些信息绝不能返回给另一家公司。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T096 |
| 交付文件 | `docs/delivery/APP-M2-T096.md` |
| 影响模块 | `icg/domain/related_bids.py`、`icg/domain/workflow_orchestrator.py`、`icg/domain/workflow_schemas.py`、`icg/api/workflow.py`、`icg/domain/compliance_rules.py`、`icg/domain/input_snapshot.py`、`frontend/web/src/project/related-bid-core.ts`、`RelatedBidPrompt.tsx`、`app/App.tsx`、`project/ProjectSettingsPage.tsx` |
<!-- code-explanation:end -->

## 匹配
`project_keys(state, project)`：招标编号取项目字段 `tender_number`，没有时取事实表“招标编号/项目编号/采购编号”（已确认的优先）；标段取事实“标段/标段编号/包号/采购包”；招标人取事实“采购人/招标人”；项目名称取项目名称。全部经 `normalize`（NFKC 全角转半角、小写、去掉空白与标点）。

`match(a, b)`：双方都有编号时，编号不同即不冲突；编号相同且标段相同（包括都没有）为 `exact`；编号相同、一方缺标段为 `approximate`；标段不同不冲突。任一方没有编号时，招标人与项目名称都相同才算 `approximate`；只有项目名称相同不算。

`conflicts(state, project)`：遍历平台内其他公司（排除本公司与 `system`）未删除、未归档的项目，返回 `{match, companies: [{company_id, company_name, match}]}`，公司名称取 `company_display_name`。返回给页面的 `public_details` 只有匹配方式、公司名称、提示语与法规依据，没有对方项目的任何字段。

## 拦截与确认
- `patch_project`：载荷含 `tender_number` 或 `name` 时，在同一事务里改完字段后调 `require_ack`。有冲突且现有确认不覆盖全部冲突公司：载荷没有 `related_bid_reason` 或少于 5 个字 → 409 RELATED_BID_CONFLICT，事务回滚，字段不保存；有说明 → `record_ack`。
- `record_ack`：只有项目负责人或公司管理员（403 PROJECT_LEAD_REQUIRED）；写 `workflow.related_bid_ack`（公司编号与名称、匹配方式、说明、确认人、时间），并追加到 `related_bid_history`；通知全部启用的集团管理员（提醒类型 `related_bid_conflict`），正文只含双方公司名称与说明。请求本身经 `_write`，审计记 `project.update` 或 `related_bid.ack`。
- `acknowledged(workflow, found)`：确认记录覆盖当前全部冲突公司才算有效；出现新的冲突公司须重新确认。
- `GET …/related-bids`：项目成员可读；`POST …/related-bids/ack`：用于解析后才出现的冲突，没有冲突时 409 VERSION_CONFLICT。

## 检查
`ComplianceRulesEngine.check_r19`：有冲突且未确认时出一条警告（`RELATED_BID_CONFLICT`，消息只含公司名称）；警告可按原机制由负责人放行，但正确做法是在项目设置填写说明。`related_bid_ack` 写入输入指纹（`project_input_fingerprint`），确认后旧检查与导出过期。

原 `check_r19`（绿色采购）改名 `check_ext_green`，结果与问题的 `rule_id` 为 `EXT-GREEN`，仍在 P5 批次里运行。

## 前端
`relatedBidConflict(error)` 只认 409 `RELATED_BID_CONFLICT`。`askRelatedBidReason(modal, details)` 弹出确认框，按钮为“确认无上述关系并继续”“取消”，说明不足 5 个字时 `onOk` 抛错使弹窗不关闭；返回说明或 `null`。新建项目：建项后保存基本信息遇到冲突即弹框，取消则走原有“项目已经建立，基本信息未全部保存”的路径并打开项目设置。项目设置：保存基本信息遇到冲突弹框，取消则保留表单不保存；`RelatedBidBanner` 读取状态，未确认时显示提示与“填写说明”，已确认时显示确认人与说明。

## 依赖与限制
无新依赖。集团归属、控股关系与单位负责人数据尚未建模，见交付文档。
