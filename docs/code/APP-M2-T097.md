# 代码说明：APP-M2-T097 项目概览（待办、分册、状态操作）

为什么有这个文件：说明 项目状态流转（递交、开标、结果、取消）、取消后只读、倒计时标红、导出页签按权限、概览待办在后台与前端的接线方式和规则所在位置。

它解决什么问题：以后改状态流转、设置校验或占用口径时，知道规则在哪个文件、前端哪里只是展示。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T097 |
| 交付文件 | `docs/delivery/APP-M2-T097.md` |
| 影响模块 | `backend/bid-core/icg/domain/project_lifecycle.py`（新）、`backend/bid-core/icg/domain/project_settings_groups.py`（新）、`backend/bid-core/icg/domain/workflow_orchestrator.py`、`icg/api/workflow.py`、`errors.py`、`frozen_error_codes.py`、`frontend/web/src/project/project-header-core.ts`（倒计时红色、`tabAllowedByPermissions`）、`ProjectSettingsGroups.tsx`（状态卡）、`OverviewTab.tsx`、`project-settings-core.ts`（新） |
<!-- code-explanation:end -->

## 接线
- `backend/bid-core/icg/domain/project_lifecycle.py`（新）：状态流转、取消只读守卫、占用冲突
- `backend/bid-core/icg/domain/project_settings_groups.py`（新）：待办 `project_todos`、设置读回 `project_settings`
- `backend/bid-core/icg/domain/workflow_orchestrator.py`：`_write` 加取消只读守卫；`workspace` 返回 `project_status`；阶段推导抽为 `workspace_stage`（仍为 336 行，上限 350）
- `icg/api/workflow.py`：`POST /api/v1/projects/{p}/status`（`transitionProjectStatus`）、`GET …/settings`（`getProjectSettings`）
- `errors.py`、`frozen_error_codes.py`：`INVALID_STATUS_TRANSITION`、`PROJECT_CANCELLED`（均 409）
- `frontend/web/src/project/project-header-core.ts`（倒计时红色、`tabAllowedByPermissions`）、`ProjectSettingsGroups.tsx`（状态卡）、`OverviewTab.tsx`、`project-settings-core.ts`（新）

## 约束
- 所有写入走 `WorkflowService._write`（Idempotency-Key、If-Match、审计）；动作名 `project.update:<组>`，在 `_authorize` 里按 `project.update` 要求项目负责人，编写人、只读成员被拒。
- 设置数据存在项目工作流（`status`、`basic_info`、`manual_edits`、`rule_overrides`、`volume_settings`、`submit_full_value`），不新增数据库列。
- `workflow_orchestrator.py` 只加取消只读守卫和阶段推导的调用，仍不超过 350 行；新逻辑在 `project_lifecycle.py`、`project_settings_groups.py`。
- 前端页面组件只展示与提交，规则在 `project-settings-core.ts`、`project-header-core.ts` 的纯函数里（可用 `node --test` 验证）；后台是最终裁决。`App.tsx` 未改动。

## 依赖与限制
无新依赖。限制见交付文档“未实现项与限制”。
