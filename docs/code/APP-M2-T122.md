# 代码说明：APP-M2-T122 “需复核”传播提示

为什么有这个文件：说明服务承诺传播提示的计算方式和前端接线。

它解决什么问题：以后改复核原因或面板时，知道规则在后台哪个文件、前端哪里只是展示。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T122（同批含 APP-M2-T119 判定汇总） |
| 交付文件 | `docs/delivery/APP-M2-T122.md` |
| 影响模块 | `sla_propagation.py`、`sla.py`、`sla_schemas.py`、`api/workflow.py`、`frontend/web/src/admin/sla-propagation.ts`、`SlaPropagationPanel.tsx`、`SlaPages.tsx`、`shared/types.ts` |
<!-- code-explanation:end -->

## 接线
- `sla_propagation` 不保存状态：读取 `public_sla` 的每行事实状态、来源是否过期和判定，生成原因列表；`sla_issues` 里带 `chapter_id` 的问题按章节归类；正文中的 `{{sla:变量}}` 用于找引用章节。
- 原因编码：TEMPLATE_STALE、SOURCE_STALE、NEEDS_REVIEW 算“需复核”；UNCONFIRMED、VALUE_INVALID、RISK_UNREVIEWED 单独计数，不并入需复核。
- 读权限为本公司项目可见（`demo._project`），不放宽跨公司。
- 面板在矩阵页 SLA 视图顶部，随 `workspace.revision` 重读；文案由 `propagationHeadline` 按后台计数拼出，没有待处理时只写“没有待处理的复核项”，不下“通过”结论。

## 约束
- 响应模型为 extra=allow 的严格响应；operationId `getSlaPropagation` 全局唯一；未新增错误码。

## 依赖与限制
无新依赖。限制见交付文档“未实现项与限制”。
