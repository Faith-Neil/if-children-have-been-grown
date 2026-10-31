# 代码说明：APP-M2-T099 项目设置：拟派人员、SLA 取值、规则覆盖

为什么有这个文件：说明 拟派人员跨项目占用提示、SLA 取值摘要、项目级规则覆盖在后台与前端的接线方式和规则所在位置。

它解决什么问题：以后改状态流转、设置校验或占用口径时，知道规则在哪个文件、前端哪里只是展示。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T099 |
| 交付文件 | `docs/delivery/APP-M2-T099.md` |
| 影响模块 | `project_lifecycle.py`、`project_settings_groups.py`、`frontend/web/src/project/ProposedStaffCard.tsx`、`proposed-staff-core.ts`（`occupancyMessages`）、`ProjectSettingsGroups.tsx`（`SlaSummaryCard`、`RuleOverridesCard`） |
<!-- code-explanation:end -->

## 接线
- `project_lifecycle.py`：`occupancy_conflicts`；`staff_proof_rules.py`：拟派人员读写返回 `occupancy`
- `project_settings_groups.py`：`validate_rule_overrides`、`save_rule_overrides`（`PUT …/rule-overrides`，`updateRuleOverrides`）、设置读回的 `sla` 摘要
- `frontend/web/src/project/ProposedStaffCard.tsx`、`proposed-staff-core.ts`（`occupancyMessages`）、`ProjectSettingsGroups.tsx`（`SlaSummaryCard`、`RuleOverridesCard`）

## 约束
- 所有写入走 `WorkflowService._write`（Idempotency-Key、If-Match、审计）；动作名 `project.update:<组>`，在 `_authorize` 里按 `project.update` 要求项目负责人，编写人、只读成员被拒。
- 设置数据存在项目工作流（`status`、`basic_info`、`manual_edits`、`rule_overrides`、`volume_settings`、`submit_full_value`），不新增数据库列。
- `workflow_orchestrator.py` 只加取消只读守卫和阶段推导的调用，仍不超过 350 行；新逻辑在 `project_lifecycle.py`、`project_settings_groups.py`。
- 前端页面组件只展示与提交，规则在 `project-settings-core.ts`、`project-header-core.ts` 的纯函数里（可用 `node --test` 验证）；后台是最终裁决。`App.tsx` 未改动。

## 依赖与限制
无新依赖。限制见交付文档“未实现项与限制”。
