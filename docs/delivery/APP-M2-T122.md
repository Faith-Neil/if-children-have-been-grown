为什么有这个文件：记录 APP-M2-T122 “需复核”传播提示的实际交付和测试证据。

它解决什么问题：说明做到什么、没做什么，避免把未运行的测试或尚未做的子范围当作已验收。

# APP-M2-T122：“需复核”传播提示

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T122 |
| 代码解释 | [APP-M2-T122](../code/APP-M2-T122.md) |
| 验收 | 2026-11-02：新增只读 `GET /api/v1/projects/{project_id}/sla/propagation`（`getSlaPropagation`），与 `public_sla`、`sla_issues` 同源：逐个指标给出复核原因（模板已变化 TEMPLATE_STALE、招标来源变化 SOURCE_STALE、取值/来源/模板变更后未重新确认 NEEDS_REVIEW、尚未确认 UNCONFIRMED、未填写或不满足招标 VALUE_INVALID、风险未说明 RISK_UNREVIEWED）和引用该指标变量的章节；汇总七类判定数量、需复核、未确认、风险未说明、无效项、过期承诺函和受影响章节数；章节里手写数字与变量不一致、变量未确认等问题按章节列出。未选用模板时返回 selected=false 的空汇总。他公司项目 404。服务承诺矩阵页顶部新增传播面板（刷新随项目版本自动重读），点章节名跳编辑台。该接口只读，不放行任何导出或承诺函门禁。 验证见 [验证记录](../testing/2026-11-02-wp5-batch2-sla-queue-edit.md) |
| 项目进度 | 看板与任务卡改为 in-review，等待 QA 与项目经理复审；不标 done。T119 同批增加判定汇总，仍为 in-progress（缺口见下） |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T122](../tasks/APP-M2.md#app-m2-t122)、[APP-M2-T119](../tasks/APP-M2.md#app-m2-t119)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 依据：PRD v1.8 §5.3.2、5.7.8

## 实际文件
- `sla_propagation.py`：`sla_propagation`（原因、章节引用、汇总）；`sla.py`：`SlaService.propagation`
- `sla_schemas.py`：`SlaPropagation` 及子模型；`api/workflow.py`：路由 `getSlaPropagation`
- 前端：`admin/sla-propagation.ts`、`admin/SlaPropagationPanel.tsx`、`admin/SlaPages.tsx`、`shared/types.ts`

## 测试证据
- `tests/backend/test_sla_propagation.py`：未选模板为空、未确认/需复核/确认后原因随事实状态变化、取值变更后列出引用章节、模板变更标 TEMPLATE_STALE、取值变更后承诺函计为过期、手写数字不一致按章节报告、跨公司 404
- `frontend/web/tests/unit/sla-propagation.test.mjs`：标题文案、提醒级别、接线
- `frontend/web/e2e/sla-propagation.spec.ts`：选用模板后面板显示“1 项尚未确认”并与接口一致

## 未实现项与限制
- T122 只做 SLA 指标的传播；项目事实表（非 SLA 事实）变化对章节的“需复核”传播沿用既有输入指纹机制，本卡没有新增。
- 章节引用只统计正文中的 `{{sla:变量}}`，不统计写作方案、草稿或候选里的引用。
- T119 仍缺：故障等级、服务时段与服务类别的三方值模型（模板仍是“分组 + 单位 + 单值”，没有等级×时段的矩阵维度）、时段不可比交人工的专门判定、权限按分册/章节细分（目前写操作仅项目负责人）。因此 T119 保持 in-progress，T211～T213 未动。
- T120 承诺函导出已有实现（导出、下载、过期校验），本批只在汇总里显示过期承诺函数，未改导出本身，状态不变。
- 本机没有运行 pytest、tsc、pnpm 构建与 Playwright，后端和 e2e 用例只在 CI 执行；结果以 CI 为准。`spec/openapi/demo-v1.json` 未手改，新增 `getSlaPropagation` 由 CI 产物更新。
